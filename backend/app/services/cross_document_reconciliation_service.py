from __future__ import annotations

import logging
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from app.models.admission import AdmissionApplication
from app.models.student import Student
from app.models.document import Document, DocumentVersion
from app.models.document_processing import DocumentExtractionResult, CrossDocumentReconciliation
from app.services.reconciliation import CrossDocumentReconciler

logger = logging.getLogger(__name__)


class CrossDocumentReconciliationService:
    """
    Application service managing deterministic cross-document consistency reconciliation runs.
    Maintains read-only guarantees and versioned snapshot persistence.
    """

    def __init__(self, reconciler: Optional[CrossDocumentReconciler] = None):
        self.reconciler = reconciler or CrossDocumentReconciler()

    async def run_reconciliation(
        self,
        db: AsyncSession,
        application_id: str,
    ) -> CrossDocumentReconciliation:
        """
        Executes a deterministic cross-document reconciliation run for the given admission application.
        Does NOT alter application status, student data, or document verification state.
        """
        # 1. Fetch application with student and documents
        stmt = (
            select(AdmissionApplication)
            .options(
                selectinload(AdmissionApplication.student).selectinload(Student.tnea_allotment),
                selectinload(AdmissionApplication.documents).selectinload(Document.document_type),
                selectinload(AdmissionApplication.documents).selectinload(Document.versions),
            )
            .where(AdmissionApplication.id == application_id)
        )
        res = await db.execute(stmt)
        application = res.scalar_one_or_none()
        if not application:
            raise ValueError(f"AdmissionApplication '{application_id}' not found.")

        # 2. Build application form data dict
        app_data = {
            "application_id": application.id,
            "application_number": application.application_number,
            "student_name": application.student.full_name if application.student else None,
            "tnea_application_number": application.student.tnea_application_number if application.student else None,
            "community": application.caste or (application.student.community if application.student else None),
            "caste": application.caste,
            "father_name": application.father_name,
            "mother_name": application.mother_name,
            "annual_family_income": application.annual_family_income,
            "is_first_graduate": application.is_first_graduate,
            "tenth_registration_number": application.tenth_registration_number,
            "tenth_total_marks": application.tenth_total_marks,
            "tenth_max_marks": application.tenth_max_marks,
            "twelfth_registration_number": application.twelfth_registration_number,
            "twelfth_maths_marks": application.twelfth_maths_marks,
            "twelfth_physics_marks": application.twelfth_physics_marks,
            "twelfth_chemistry_marks": application.twelfth_chemistry_marks,
            "twelfth_cutoff_marks": application.twelfth_cutoff_marks,
            "twelfth_total_marks": application.twelfth_total_marks,
        }

        # 3. Build stored TNEA allotment baseline dict
        allotment_baseline = None
        allotment = application.student.tnea_allotment if application.student else None
        if allotment:
            allotment_baseline = {
                "tnea_application_number": allotment.tnea_application_number,
                "candidate_name": allotment.student_name,
                "allotted_branch": allotment.allotted_branch,
                "allotted_category": allotment.allotted_quota or allotment.community,
                "quota": allotment.allotted_quota,
                "community": allotment.community,
                "general_rank": allotment.general_rank,
                "community_rank": allotment.community_rank,
                "college_code": allotment.allotted_institution_code,
            }

        # 4. Gather active document extractions
        extractions: Dict[str, Dict[str, Any]] = {}
        participating_versions: Dict[str, Any] = {}

        for doc in application.documents:
            doc_type_code = doc.document_type.code if doc.document_type else None
            if not doc_type_code:
                continue

            active_ver = doc.active_version or 1
            # Find active version record
            ver_record = next((v for v in doc.versions if v.version_number == active_ver), None)

            # Find latest DocumentExtractionResult for this document and active version
            ext_stmt = (
                select(DocumentExtractionResult)
                .where(
                    DocumentExtractionResult.document_id == doc.id,
                    DocumentExtractionResult.document_version_id == (ver_record.id if ver_record else None),
                )
                .order_by(desc(DocumentExtractionResult.created_at))
            )
            ext_res = await db.execute(ext_stmt)
            extraction_result = ext_res.scalar_one_or_none()

            # If no version-matched extraction, check document-level extraction
            if not extraction_result:
                fallback_stmt = (
                    select(DocumentExtractionResult)
                    .where(DocumentExtractionResult.document_id == doc.id)
                    .order_by(desc(DocumentExtractionResult.created_at))
                )
                fallback_res = await db.execute(fallback_stmt)
                extraction_result = fallback_res.scalar_one_or_none()

            if extraction_result:
                extractions[doc_type_code] = {
                    "fields": extraction_result.fields or {},
                    "calculated_fields": extraction_result.fields.get("calculated_cutoff_marks")
                    if extraction_result.fields
                    else {},
                    "meta": {
                        "document_id": doc.id,
                        "document_version": active_ver,
                        "extraction_result_id": extraction_result.id,
                        "extractor_name": extraction_result.extractor_name,
                        "document_type_code": doc_type_code,
                    },
                }
                participating_versions[doc_type_code] = {
                    "document_id": doc.id,
                    "version_number": active_ver,
                    "extraction_result_id": extraction_result.id,
                }

        # 5. Run deterministic CrossDocumentReconciler
        recon_result = self.reconciler.reconcile(
            application_data=app_data,
            allotment_baseline=allotment_baseline,
            extractions=extractions,
            participating_versions=participating_versions,
        )

        # 6. Persist versioned snapshot record
        reconciliation_entity = CrossDocumentReconciliation(
            application_id=application.id,
            overall_status=recon_result["overall_status"],
            participating_document_versions=recon_result["participating_document_versions"],
            total_rules_evaluated=recon_result["total_rules_evaluated"],
            passed_rules_count=recon_result["passed_rules_count"],
            discrepancy_count=recon_result["discrepancy_count"],
            pending_scrutiny_count=recon_result["pending_scrutiny_count"],
            incomplete_count=recon_result["incomplete_count"],
            findings=recon_result["findings"],
            discrepancy_summary=recon_result["discrepancy_summary"],
            requires_human_review=recon_result["requires_human_review"],
            reconciliation_time_ms=recon_result["reconciliation_time_ms"],
        )
        db.add(reconciliation_entity)
        await db.commit()
        await db.refresh(reconciliation_entity)

        logger.info(
            f"Cross-document reconciliation completed for app {application_id}: "
            f"status={reconciliation_entity.overall_status}, discrepancies={reconciliation_entity.discrepancy_count}"
        )
        return reconciliation_entity

    async def get_latest_reconciliation(
        self,
        db: AsyncSession,
        application_id: str,
    ) -> Optional[CrossDocumentReconciliation]:
        """Fetches the latest reconciliation snapshot for an admission application."""
        stmt = (
            select(CrossDocumentReconciliation)
            .where(CrossDocumentReconciliation.application_id == application_id)
            .order_by(desc(CrossDocumentReconciliation.created_at))
        )
        res = await db.execute(stmt)
        return res.scalars().first()
