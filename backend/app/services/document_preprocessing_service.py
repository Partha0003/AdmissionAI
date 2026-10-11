import os
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List, Tuple
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.document import Document, DocumentVersion, DocumentType
from app.models.admission import AdmissionApplication
from app.models.user import User
from app.models.document_processing import (
    DocumentProcessingJob,
    PreprocessingResult,
    ProcessingStatus,
    ProcessingType,
)
from app.services.preprocessors.base import (
    DocumentPreprocessor,
    PreprocessingContext,
    PreprocessingResultData,
    PreprocessingOptions,
)
from app.services.preprocessors.opencv_preprocessor import OpenCVDocumentPreprocessor
from app.schemas.processing import (
    DocumentProcessingJobResponse,
    PreprocessingResultResponse,
    DocumentProcessingHistoryResponse,
)


class DocumentPreprocessingService:
    """
    Service responsible for document image preprocessing lifecycle,
    OpenCV transformation pipeline execution, private artifact storage,
    and Anti-IDOR security.
    """

    @classmethod
    def get_processed_storage_dir(cls, application_id: str, document_id: str) -> Path:
        """
        Returns private directory for storing preprocessed image artifacts.
        Never exposed directly to client HTTP responses.
        """
        base_dir = Path(__file__).resolve().parent.parent.parent / "storage" / "processed"
        target_dir = base_dir / application_id / document_id
        target_dir.mkdir(parents=True, exist_ok=True)
        return target_dir

    @classmethod
    async def get_document_with_authorization(
        cls,
        db: AsyncSession,
        document_id: str,
        current_user: User,
        require_admin: bool = False
    ) -> Document:
        """
        Retrieves document by ID with strict Anti-IDOR permission enforcement.
        """
        stmt = (
            select(Document)
            .options(
                selectinload(Document.versions),
                selectinload(Document.application),
                selectinload(Document.document_type),
            )
            .join(AdmissionApplication, Document.application_id == AdmissionApplication.id)
            .where(Document.id == document_id)
        )
        res = await db.execute(stmt)
        doc = res.scalar_one_or_none()

        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found."
            )

        user_role = current_user.role.name if current_user.role else ""

        if require_admin:
            if user_role not in ["ADMIN_VERIFIER", "ADMISSION_HEAD", "SUPER_ADMIN", "FINANCE_OFFICER"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Administrative privileges required."
                )
            return doc

        # Anti-IDOR check for student
        if user_role == "STUDENT":
            if not current_user.student or current_user.student.id != doc.application.student_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: You do not have permission to access preprocessing for this document."
                )

        return doc

    @classmethod
    async def preprocess_document(
        cls,
        db: AsyncSession,
        document_id: str,
        current_user: User,
        options: Optional[PreprocessingOptions] = None,
        preprocessor: Optional[DocumentPreprocessor] = None,
    ) -> DocumentProcessingJob:
        """
        Executes OpenCV image preprocessing on the latest uploaded version of a document.
        Preserves the original uploaded file without mutation.
        """
        doc = await cls.get_document_with_authorization(db, document_id, current_user)

        if not doc.versions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot preprocess document: No uploaded file version exists."
            )

        latest_version = doc.versions[0]
        original_file_path = latest_version.storage_path

        if not os.path.exists(original_file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Source document file not found on disk storage."
            )

        active_preprocessor = preprocessor or OpenCVDocumentPreprocessor()
        pipeline_options = options or PreprocessingOptions()

        # Step 1: Create processing job in QUEUED state
        job = DocumentProcessingJob(
            document_id=doc.id,
            document_version_id=latest_version.id,
            processing_type=ProcessingType.IMAGE_PREPROCESSING.value,
            status=ProcessingStatus.QUEUED.value,
            requested_by=current_user.email,
            engine_name=active_preprocessor.name,
            engine_version=active_preprocessor.version,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(job)
        await db.flush()

        # Step 2: Transition to PROCESSING state
        job.status = ProcessingStatus.PROCESSING.value
        job.started_at = datetime.now(timezone.utc)
        job.updated_at = datetime.now(timezone.utc)
        await db.flush()

        start_perf = time.perf_counter()

        try:
            # Build preprocessing context
            context = PreprocessingContext(
                document_id=doc.id,
                document_version_id=latest_version.id,
                file_path=original_file_path,
                mime_type=latest_version.mime_type,
                original_filename=latest_version.original_filename,
                options=pipeline_options,
            )

            # Step 3: Execute preprocessing pipeline
            result_data: PreprocessingResultData = await active_preprocessor.preprocess(context)
            elapsed_ms = int((time.perf_counter() - start_perf) * 1000)

            # Step 4: Persist processed image to private storage (never overwriting original)
            storage_dir = cls.get_processed_storage_dir(doc.application_id, doc.id)
            output_filename = f"v{latest_version.version_number}_preprocessed.png"
            processed_file_path = storage_dir / output_filename

            with open(processed_file_path, "wb") as f:
                f.write(result_data.output_image_bytes)

            file_size_bytes = len(result_data.output_image_bytes)

            # Step 5: Persist PreprocessingResult metadata
            preprocessing_result = PreprocessingResult(
                job_id=job.id,
                document_id=doc.id,
                document_version_id=latest_version.id,
                engine_name=result_data.engine_name,
                engine_version=result_data.engine_version,
                input_dimensions=result_data.input_dimensions,
                output_dimensions=result_data.output_dimensions,
                operations_applied=result_data.operations_applied,
                deskew_angle_deg=result_data.deskew_angle_deg,
                storage_path=str(processed_file_path),
                output_filename=output_filename,
                output_mime_type=result_data.output_mime_type,
                output_file_size=file_size_bytes,
                processing_time_ms=max(1, elapsed_ms),
                created_at=datetime.now(timezone.utc),
            )
            db.add(preprocessing_result)

            # Step 6: Transition to COMPLETED
            job.status = ProcessingStatus.COMPLETED.value
            job.completed_at = datetime.now(timezone.utc)
            job.processing_time_ms = max(1, elapsed_ms)
            job.updated_at = datetime.now(timezone.utc)

            await db.commit()
            await db.refresh(job)
            return job

        except Exception as e:
            elapsed_ms = int((time.perf_counter() - start_perf) * 1000)
            # Step 6 (Fail branch): Transition to FAILED with sanitized error message
            job.status = ProcessingStatus.FAILED.value
            job.completed_at = datetime.now(timezone.utc)
            job.processing_time_ms = max(1, elapsed_ms)
            job.error_code = "IMAGE_PREPROCESSING_ERROR"
            # Sanitize error message to prevent leaking internal stack trace details
            error_str = str(e)
            if "Corrupted" in error_str or "empty" in error_str or "dimensions" in error_str:
                clean_err = error_str
            else:
                clean_err = "Document image preprocessing encountered an error during image decoding or transformation."
            job.error_message = clean_err
            job.updated_at = datetime.now(timezone.utc)

            await db.commit()
            await db.refresh(job)
            return job

    @classmethod
    async def get_preprocessed_file(
        cls,
        db: AsyncSession,
        document_id: str,
        current_user: User,
    ) -> Tuple[str, str, str]:
        """
        Returns (file_path, filename, mime_type) for the preprocessed document image.
        Strictly enforces Anti-IDOR authorization.
        """
        doc = await cls.get_document_with_authorization(db, document_id, current_user)

        stmt = (
            select(PreprocessingResult)
            .where(PreprocessingResult.document_id == doc.id)
            .order_by(PreprocessingResult.created_at.desc())
        )
        res = await db.execute(stmt)
        result = res.scalars().first()

        if not result or not os.path.exists(result.storage_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Preprocessed image artifact not found for this document. Please run preprocessing first."
            )

        return result.storage_path, result.output_filename, result.output_mime_type

    @classmethod
    async def get_preprocessing_history(
        cls,
        db: AsyncSession,
        document_id: str,
        current_user: User,
        require_admin: bool = False
    ) -> DocumentProcessingHistoryResponse:
        """
        Returns processing job history and preprocessing results for a document.
        """
        doc = await cls.get_document_with_authorization(db, document_id, current_user, require_admin=require_admin)

        stmt = (
            select(DocumentProcessingJob)
            .options(selectinload(DocumentProcessingJob.preprocessing_result))
            .where(
                DocumentProcessingJob.document_id == doc.id,
                DocumentProcessingJob.processing_type == ProcessingType.IMAGE_PREPROCESSING.value
            )
            .order_by(DocumentProcessingJob.created_at.desc())
        )
        res = await db.execute(stmt)
        jobs = res.scalars().all()

        job_responses: List[DocumentProcessingJobResponse] = []
        for j in jobs:
            prep_resp = None
            if j.preprocessing_result:
                pr = j.preprocessing_result
                prep_resp = PreprocessingResultResponse(
                    id=pr.id,
                    job_id=pr.job_id,
                    document_id=pr.document_id,
                    document_version_id=pr.document_version_id,
                    engine_name=pr.engine_name,
                    engine_version=pr.engine_version,
                    input_dimensions=pr.input_dimensions,
                    output_dimensions=pr.output_dimensions,
                    operations_applied=pr.operations_applied,
                    deskew_angle_deg=pr.deskew_angle_deg,
                    output_filename=pr.output_filename,
                    output_mime_type=pr.output_mime_type,
                    output_file_size=pr.output_file_size,
                    processing_time_ms=pr.processing_time_ms,
                    created_at=pr.created_at,
                )

            job_responses.append(
                DocumentProcessingJobResponse(
                    id=j.id,
                    document_id=j.document_id,
                    document_version_id=j.document_version_id,
                    processing_type=j.processing_type,
                    status=j.status,
                    requested_by=j.requested_by,
                    started_at=j.started_at,
                    completed_at=j.completed_at,
                    processing_time_ms=j.processing_time_ms,
                    engine_name=j.engine_name,
                    engine_version=j.engine_version,
                    error_code=j.error_code,
                    error_message=j.error_message,
                    created_at=j.created_at,
                    updated_at=j.updated_at,
                    preprocessing_result=prep_resp,
                )
            )

        latest = job_responses[0] if job_responses else None

        return DocumentProcessingHistoryResponse(
            document_id=doc.id,
            total_jobs=len(job_responses),
            latest_job=latest,
            jobs=job_responses,
        )
