import hashlib
import os
import time
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.document import Document, DocumentVersion
from app.models.document_processing import (
    DocumentProcessingJob,
    PreprocessingResult,
    OCRResult,
    ProcessingStatus,
    ProcessingType,
)
from app.models.student import Student
from app.models.user import User
from app.schemas.processing import RunOCRRequest
from app.services.ocr import (
    get_ocr_engine,
    OCREngine,
    OCRResultData,
    OCREngineUnavailableException,
    OCRProcessingException,
)


class DocumentOCRService:
    """
    Orchestration service for Phase 4C OCR machine-readable text extraction.
    Maintains document version integrity, preprocessed image hash tracing,
    and strict read-only execution without mutating verification state.
    """

    @classmethod
    async def process_document_ocr(
        cls,
        db: AsyncSession,
        document_id: str,
        current_user: User,
        request_options: Optional[RunOCRRequest] = None,
        custom_engine: Optional[OCREngine] = None,
    ) -> DocumentProcessingJob:
        """
        Execute OCR text extraction for a document using its Phase 4B preprocessed image.
        Strict Anti-IDOR enforcement.
        """
        options = request_options or RunOCRRequest()

        # 1. Fetch document and verify existence
        stmt = (
            select(Document)
            .options(
                selectinload(Document.versions),
                selectinload(Document.application),
            )
            .where(Document.id == document_id)
        )
        res = await db.execute(stmt)
        doc = res.scalar_one_or_none()
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found",
            )

        # 2. Anti-IDOR check for students
        if current_user.role.name == "STUDENT":
            student_stmt = select(Student).where(Student.user_id == current_user.id)
            student_res = await db.execute(student_stmt)
            student = student_res.scalar_one_or_none()
            if not student or doc.application.student_id != student.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: You can only run OCR on your own documents",
                )

        # 3. Check for active document version
        if not doc.versions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Document has no uploaded file versions to process",
            )
        active_version: DocumentVersion = doc.versions[0]  # Ordered DESC by version_number

        # 4. Enforce strict Phase 4B Preprocessing Dependency
        prep_job_stmt = (
            select(DocumentProcessingJob)
            .options(selectinload(DocumentProcessingJob.preprocessing_result))
            .where(
                DocumentProcessingJob.document_id == doc.id,
                DocumentProcessingJob.document_version_id == active_version.id,
                DocumentProcessingJob.processing_type == ProcessingType.IMAGE_PREPROCESSING.value,
                DocumentProcessingJob.status == ProcessingStatus.COMPLETED.value,
            )
            .order_by(DocumentProcessingJob.created_at.desc())
        )
        prep_job_res = await db.execute(prep_job_stmt)
        prep_job = prep_job_res.scalar_one_or_none()

        if not prep_job or not prep_job.preprocessing_result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Document preprocessing is required before OCR.",
            )

        prep_result: PreprocessingResult = prep_job.preprocessing_result
        if not os.path.exists(prep_result.storage_path):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Preprocessed image file is missing from private storage. Preprocessing must be re-run.",
            )

        # 5. Read preprocessed image and verify integrity (SHA-256)
        try:
            with open(prep_result.storage_path, "rb") as f:
                image_bytes = f.read()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to read preprocessed image from private storage",
            )

        image_sha256 = hashlib.sha256(image_bytes).hexdigest()

        # 6. Select OCR Engine
        if custom_engine:
            engine = custom_engine
        else:
            try:
                engine = get_ocr_engine(options.engine_name)
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e),
                )

        target_language = options.language or settings.OCR_LANGUAGE

        # 7. Create processing job record
        job = DocumentProcessingJob(
            document_id=doc.id,
            document_version_id=active_version.id,
            processing_type=ProcessingType.OCR.value,
            status=ProcessingStatus.PROCESSING.value,
            requested_by=current_user.email,
            engine_name=engine.name,
            engine_version=engine.version,
            started_at=datetime.now(timezone.utc),
        )
        db.add(job)
        await db.flush()

        # 8. Execute OCR extraction
        start_time = time.perf_counter()
        try:
            ocr_data: OCRResultData = engine.extract(image_bytes, language=target_language)
            duration_ms = max(1, int((time.perf_counter() - start_time) * 1000))

            ocr_record = OCRResult(
                job_id=job.id,
                document_id=doc.id,
                document_version_id=active_version.id,
                preprocessing_result_id=prep_result.id,
                engine_name=ocr_data.engine_name,
                engine_version=ocr_data.engine_version,
                language=ocr_data.language,
                image_sha256=ocr_data.image_sha256 or image_sha256,
                ocr_confidence=ocr_data.ocr_confidence,
                full_text=ocr_data.full_text,
                blocks=[b.to_dict() for b in ocr_data.blocks],
                processing_time_ms=duration_ms,
                error_message=None,
            )
            db.add(ocr_record)

            job.status = ProcessingStatus.COMPLETED.value
            job.completed_at = datetime.now(timezone.utc)
            job.processing_time_ms = duration_ms

            await db.commit()
            await db.refresh(job)
            return job

        except OCREngineUnavailableException as e:
            duration_ms = max(1, int((time.perf_counter() - start_time) * 1000))
            job.status = ProcessingStatus.FAILED.value
            job.error_code = "OCR_ENGINE_UNAVAILABLE"
            job.error_message = str(e)
            job.completed_at = datetime.now(timezone.utc)
            job.processing_time_ms = duration_ms
            await db.commit()
            await db.refresh(job)
            return job

        except Exception as e:
            duration_ms = max(1, int((time.perf_counter() - start_time) * 1000))
            job.status = ProcessingStatus.FAILED.value
            job.error_code = "OCR_EXTRACTION_FAILED"
            # Never leak sensitive text or internal paths
            job.error_message = f"OCR text extraction failed for document {doc.id}"
            job.completed_at = datetime.now(timezone.utc)
            job.processing_time_ms = duration_ms
            await db.commit()
            await db.refresh(job)
            return job

    @classmethod
    async def get_latest_ocr_result(
        cls,
        db: AsyncSession,
        document_id: str,
        current_user: User,
    ) -> Optional[OCRResult]:
        """
        Fetch the latest completed OCRResult for a document.
        Anti-IDOR protected.
        """
        # Fetch document
        stmt = (
            select(Document)
            .options(selectinload(Document.application))
            .where(Document.id == document_id)
        )
        res = await db.execute(stmt)
        doc = res.scalar_one_or_none()
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found",
            )

        # Anti-IDOR check for students
        if current_user.role.name == "STUDENT":
            student_stmt = select(Student).where(Student.user_id == current_user.id)
            student_res = await db.execute(student_stmt)
            student = student_res.scalar_one_or_none()
            if not student or doc.application.student_id != student.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: You can only view OCR results for your own documents",
                )

        ocr_stmt = (
            select(OCRResult)
            .where(OCRResult.document_id == document_id)
            .order_by(OCRResult.created_at.desc())
        )
        ocr_res = await db.execute(ocr_stmt)
        return ocr_res.scalar_one_or_none()
