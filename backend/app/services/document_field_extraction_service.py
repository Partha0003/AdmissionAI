from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from fastapi import HTTPException, status
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.document import Document, DocumentVersion, DocumentType
from app.models.document_processing import (
    DocumentProcessingJob,
    DocumentExtractionResult,
    OCRResult,
    ProcessingStatus,
    ProcessingType,
)
from app.models.student import Student
from app.models.user import User
from app.schemas.processing import RunFieldExtractionRequest
from app.services.extractors import FieldExtractorFactory, ExtractionResultData

logger = logging.getLogger(__name__)


class DocumentFieldExtractionService:
    """
    Orchestration service for Phase 4D Structured Field Extraction.
    Maintains document version integrity, strict Anti-IDOR enforcement,
    and strict read-only execution without mutating application or verification state.
    """

    @classmethod
    async def process_document_field_extraction(
        cls,
        db: AsyncSession,
        document_id: str,
        current_user: User,
        request_options: Optional[RunFieldExtractionRequest] = None,
    ) -> DocumentProcessingJob:
        """
        Execute structured field extraction for a document using its Phase 4C OCR result.
        """
        options = request_options or RunFieldExtractionRequest()

        # 1. Fetch document and verify existence
        stmt = (
            select(Document)
            .options(
                selectinload(Document.versions),
                selectinload(Document.application),
                selectinload(Document.document_type),
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
                    detail="Access denied: You can only extract fields on your own documents",
                )

        # 3. Check for active document version
        if not doc.versions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Document has no uploaded file versions to process",
            )
        active_version: DocumentVersion = doc.versions[0]  # Ordered DESC

        # 4. Enforce strict Phase 4C OCR Dependency
        ocr_job_stmt = (
            select(DocumentProcessingJob)
            .options(selectinload(DocumentProcessingJob.ocr_result))
            .where(
                DocumentProcessingJob.document_id == doc.id,
                DocumentProcessingJob.document_version_id == active_version.id,
                DocumentProcessingJob.processing_type == ProcessingType.OCR.value,
                DocumentProcessingJob.status == ProcessingStatus.COMPLETED.value,
            )
            .order_by(DocumentProcessingJob.created_at.desc())
        )
        ocr_job_res = await db.execute(ocr_job_stmt)
        ocr_job = ocr_job_res.scalar_one_or_none()

        if not ocr_job or not ocr_job.ocr_result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OCR text recognition is required before structured field extraction. Please run OCR first.",
            )

        ocr_result: OCRResult = ocr_job.ocr_result

        # 5. Select specialized extractor based on document type code
        doc_type_code = doc.document_type.code if doc.document_type else "GENERIC"
        extractor = FieldExtractorFactory.get_extractor(doc_type_code)

        # 6. Create processing job record
        job = DocumentProcessingJob(
            document_id=doc.id,
            document_version_id=active_version.id,
            processing_type=ProcessingType.FIELD_EXTRACTION.value,
            status=ProcessingStatus.PROCESSING.value,
            requested_by=current_user.email,
            engine_name=extractor.name,
            engine_version=extractor.version,
            started_at=datetime.now(timezone.utc),
        )
        db.add(job)
        await db.flush()

        # 7. Execute Field Extraction
        start_time = time.perf_counter()
        try:
            extraction_context = {
                "document_version": active_version.version_number,
                "document_type_code": doc_type_code,
            }
            raw_text = ocr_result.full_text or ""
            blocks = ocr_result.blocks or []

            result_data: ExtractionResultData = extractor.extract(
                raw_text=raw_text,
                blocks=blocks,
                context=extraction_context,
            )

            duration_ms = max(1, int((time.perf_counter() - start_time) * 1000))

            extraction_record = DocumentExtractionResult(
                job_id=job.id,
                document_id=doc.id,
                document_version_id=active_version.id,
                ocr_result_id=ocr_result.id,
                document_type_code=doc_type_code,
                extractor_name=extractor.name,
                extractor_version=extractor.version,
                overall_confidence=result_data.overall_confidence,
                requires_human_review=result_data.requires_human_review,
                fields={k: v.to_dict() for k, v in result_data.fields.items()},
                raw_metadata=result_data.metadata,
                extraction_time_ms=duration_ms,
                created_at=datetime.now(timezone.utc),
            )
            db.add(extraction_record)

            job.status = ProcessingStatus.COMPLETED.value
            job.completed_at = datetime.now(timezone.utc)
            job.processing_time_ms = duration_ms
            job.engine_name = extractor.name
            job.engine_version = extractor.version

            # READ-ONLY GUARANTEE: Never mutate doc.status, AdmissionApplication, Student, or TNEA records
            await db.commit()
            await db.refresh(job)
            return job

        except Exception as e:
            await db.rollback()
            duration_ms = max(1, int((time.perf_counter() - start_time) * 1000))
            logger.error(f"Field extraction error for document {document_id}: {type(e).__name__}")

            failed_job = DocumentProcessingJob(
                document_id=doc.id,
                document_version_id=active_version.id,
                processing_type=ProcessingType.FIELD_EXTRACTION.value,
                status=ProcessingStatus.FAILED.value,
                requested_by=current_user.email,
                engine_name=extractor.name,
                engine_version=extractor.version,
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
                processing_time_ms=duration_ms,
                error_code="FIELD_EXTRACTION_FAILED",
                error_message="A technical error occurred during structured field extraction.",
            )
            db.add(failed_job)
            await db.commit()
            await db.refresh(failed_job)
            return failed_job

    @classmethod
    async def get_latest_extraction_result(
        cls,
        db: AsyncSession,
        document_id: str,
        current_user: User,
    ) -> Optional[DocumentExtractionResult]:
        """
        Retrieves the latest structured field extraction result for a document's active version.
        Enforces Anti-IDOR for students and authorized role checks for staff.
        """
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

        if current_user.role.name == "STUDENT":
            student_stmt = select(Student).where(Student.user_id == current_user.id)
            student_res = await db.execute(student_stmt)
            student = student_res.scalar_one_or_none()
            if not student or doc.application.student_id != student.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: You can only view extraction results for your own documents",
                )

        if not doc.versions:
            return None
        active_version = doc.versions[0]

        ext_stmt = (
            select(DocumentExtractionResult)
            .where(
                DocumentExtractionResult.document_id == doc.id,
                DocumentExtractionResult.document_version_id == active_version.id,
            )
            .order_by(DocumentExtractionResult.created_at.desc())
        )
        ext_res = await db.execute(ext_stmt)
        return ext_res.scalar_one_or_none()

    @classmethod
    async def get_admin_extraction_result(
        cls,
        db: AsyncSession,
        document_id: str,
    ) -> Optional[DocumentExtractionResult]:
        """
        Administrative retrieval of structured field extraction result.
        """
        stmt = (
            select(Document)
            .options(selectinload(Document.versions))
            .where(Document.id == document_id)
        )
        res = await db.execute(stmt)
        doc = res.scalar_one_or_none()
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found",
            )

        if not doc.versions:
            return None
        active_version = doc.versions[0]

        ext_stmt = (
            select(DocumentExtractionResult)
            .where(
                DocumentExtractionResult.document_id == doc.id,
                DocumentExtractionResult.document_version_id == active_version.id,
            )
            .order_by(DocumentExtractionResult.created_at.desc())
        )
        ext_res = await db.execute(ext_stmt)
        return ext_res.scalar_one_or_none()
