import time
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.document import Document, DocumentVersion, DocumentType
from app.models.admission import AdmissionApplication
from app.models.user import User
from app.models.document_processing import (
    DocumentProcessingJob,
    ClassificationResult,
    ProcessingStatus,
    ProcessingType,
)
from app.services.classifiers.base import (
    DocumentClassifier,
    DocumentClassificationContext,
    ClassificationResultData,
)
from app.services.classifiers.rule_based import RuleBasedDocumentClassifier
from app.schemas.processing import (
    DocumentProcessingJobResponse,
    ClassificationResultResponse,
    DocumentProcessingHistoryResponse,
)


class DocumentProcessingService:
    """
    Service responsible for document AI processing lifecycle, orchestration,
    and classification persistence.
    """

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
                    detail="Access denied: You do not have permission to access processing for this document."
                )

        return doc

    @classmethod
    async def process_document(
        cls,
        db: AsyncSession,
        document_id: str,
        current_user: User,
        processing_type: str = ProcessingType.DOCUMENT_CLASSIFICATION.value,
        force_reprocess: bool = False,
        classifier: Optional[DocumentClassifier] = None,
    ) -> DocumentProcessingJob:
        """
        Executes document classification processing on the document's latest uploaded version.
        
        Lifecycle state machine:
        NOT_PROCESSED -> QUEUED -> PROCESSING -> COMPLETED (or FAILED)
        
        Each processing request generates a new chronological DocumentProcessingJob history record.
        """
        doc = await cls.get_document_with_authorization(db, document_id, current_user)

        # Validate that document has at least one uploaded version
        if not doc.versions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot process document: No uploaded file version exists for this document."
            )

        latest_version = doc.versions[0]  # Ordered desc by version_number

        # Use default rule-based prototype classifier if none provided
        active_classifier = classifier or RuleBasedDocumentClassifier()

        # Step 1: Create processing job in QUEUED state
        job = DocumentProcessingJob(
            document_id=doc.id,
            document_version_id=latest_version.id,
            processing_type=processing_type,
            status=ProcessingStatus.QUEUED.value,
            requested_by=current_user.email,
            engine_name=active_classifier.name,
            engine_version=active_classifier.version,
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
            # Build classification context
            context = DocumentClassificationContext(
                document_id=doc.id,
                document_version_id=latest_version.id,
                original_filename=latest_version.original_filename,
                declared_document_type_code=doc.document_type.code,
                declared_document_type_name=doc.document_type.name,
                mime_type=latest_version.mime_type,
                file_size=latest_version.file_size,
                extra_metadata={
                    "version_number": latest_version.version_number,
                    "file_hash_sha256": latest_version.file_hash,
                }
            )

            # Step 3: Run classification
            result_data: ClassificationResultData = await active_classifier.classify(context)
            elapsed_ms = int((time.perf_counter() - start_perf) * 1000)

            # Step 4: Persist classification result
            classification_result = ClassificationResult(
                job_id=job.id,
                predicted_document_type=result_data.predicted_document_type,
                predicted_document_type_name=result_data.predicted_document_type_name,
                confidence=result_data.confidence,
                confidence_type=result_data.confidence_type,
                classifier_name=result_data.classifier_name,
                classifier_version=result_data.classifier_version,
                rule_used=result_data.rule_used,
                reasoning=result_data.reasoning,
                raw_metadata=result_data.raw_metadata,
                processed_at=datetime.now(timezone.utc),
            )
            db.add(classification_result)

            # Step 5: Transition to COMPLETED
            job.status = ProcessingStatus.COMPLETED.value
            job.completed_at = datetime.now(timezone.utc)
            job.processing_time_ms = max(1, elapsed_ms)
            job.updated_at = datetime.now(timezone.utc)

            await db.commit()
            await db.refresh(job)
            return job

        except Exception as e:
            elapsed_ms = int((time.perf_counter() - start_perf) * 1000)
            # Step 5 (Fail branch): Transition to FAILED without leaking stack trace
            job.status = ProcessingStatus.FAILED.value
            job.completed_at = datetime.now(timezone.utc)
            job.processing_time_ms = max(1, elapsed_ms)
            job.error_code = "PROCESSING_EXECUTION_ERROR"
            job.error_message = "Automated prototype document classification encountered an error. Please retry or submit for manual verification."
            job.updated_at = datetime.now(timezone.utc)
            await db.commit()
            await db.refresh(job)
            return job

    @classmethod
    async def get_processing_history(
        cls,
        db: AsyncSession,
        document_id: str,
        current_user: User,
        require_admin: bool = False
    ) -> DocumentProcessingHistoryResponse:
        """
        Returns full processing history and latest job results for a document.
        """
        doc = await cls.get_document_with_authorization(db, document_id, current_user, require_admin=require_admin)

        stmt = (
            select(DocumentProcessingJob)
            .where(DocumentProcessingJob.document_id == doc.id)
            .order_by(DocumentProcessingJob.created_at.desc())
        )
        res = await db.execute(stmt)
        jobs = res.scalars().all()

        job_responses: List[DocumentProcessingJobResponse] = []
        for j in jobs:
            result_resp = None
            if j.classification_result:
                cr = j.classification_result
                result_resp = ClassificationResultResponse(
                    id=cr.id,
                    job_id=cr.job_id,
                    predicted_document_type=cr.predicted_document_type,
                    predicted_document_type_name=cr.predicted_document_type_name,
                    confidence=cr.confidence,
                    confidence_type=cr.confidence_type,
                    classifier_name=cr.classifier_name,
                    classifier_version=cr.classifier_version,
                    rule_used=cr.rule_used,
                    reasoning=cr.reasoning,
                    raw_metadata=cr.raw_metadata,
                    processed_at=cr.processed_at,
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
                    classification_result=result_resp,
                )
            )

        latest = job_responses[0] if job_responses else None

        return DocumentProcessingHistoryResponse(
            document_id=doc.id,
            total_jobs=len(job_responses),
            latest_job=latest,
            jobs=job_responses,
        )
