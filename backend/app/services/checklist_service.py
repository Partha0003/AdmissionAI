from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.admission import AdmissionApplication
from app.models.student import Student
from app.models.document import DocumentType, DocumentRule, Document, DocumentVersion
from app.models.document_processing import DocumentProcessingJob
from app.schemas.document import ChecklistItemResponse


class ChecklistService:
    @staticmethod
    async def get_checklist_for_application(
        db: AsyncSession, application: AdmissionApplication, student: Optional[Student] = None
    ) -> List[ChecklistItemResponse]:
        """
        Dynamically evaluates checklist requirements based on the student's
        community, quota flags, income, state, and allotment details.
        """
        # Fetch all active document types ordered by sort_order
        stmt = (
            select(DocumentType)
            .where(DocumentType.is_active == True)
            .order_by(DocumentType.sort_order.asc())
        )
        res = await db.execute(stmt)
        doc_types = res.scalars().all()

        # Fetch existing uploaded documents for this application
        doc_stmt = (
            select(Document)
            .options(selectinload(Document.versions))
            .where(Document.application_id == application.id)
        )
        doc_res = await db.execute(doc_stmt)
        existing_docs = {d.document_type_id: d for d in doc_res.scalars().all()}
        doc_ids = [d.id for d in existing_docs.values()]

        # Fetch latest classification, preprocessing, OCR, and field extraction jobs for each document
        doc_latest_clf_jobs = {}
        doc_latest_prep_jobs = {}
        doc_latest_ocr_jobs = {}
        doc_latest_ext_jobs = {}
        if doc_ids:
            job_stmt = (
                select(DocumentProcessingJob)
                .options(
                    selectinload(DocumentProcessingJob.classification_result),
                    selectinload(DocumentProcessingJob.preprocessing_result),
                    selectinload(DocumentProcessingJob.ocr_result),
                    selectinload(DocumentProcessingJob.extraction_result),
                )
                .where(DocumentProcessingJob.document_id.in_(doc_ids))
                .order_by(DocumentProcessingJob.created_at.desc())
            )
            job_res = await db.execute(job_stmt)
            for j in job_res.scalars().all():
                if j.processing_type == "DOCUMENT_CLASSIFICATION" and j.document_id not in doc_latest_clf_jobs:
                    doc_latest_clf_jobs[j.document_id] = j
                elif j.processing_type == "IMAGE_PREPROCESSING" and j.document_id not in doc_latest_prep_jobs:
                    doc_latest_prep_jobs[j.document_id] = j
                elif j.processing_type == "OCR" and j.document_id not in doc_latest_ocr_jobs:
                    doc_latest_ocr_jobs[j.document_id] = j
                elif j.processing_type == "FIELD_EXTRACTION" and j.document_id not in doc_latest_ext_jobs:
                    doc_latest_ext_jobs[j.document_id] = j


        # Student community and quota
        comm = (application.caste or (student.community if student else "") or "").upper()
        quota = ((student.quota if student else "") or application.allotment_quota or "").upper()
        income = application.annual_family_income or 0.0
        state = (application.state or "Tamil Nadu").strip().lower()

        checklist_items: List[ChecklistItemResponse] = []

        for dt in doc_types:
            # Evaluate mandatory conditions
            is_mandatory = False
            mandatory_reason: Optional[str] = None

            for rule in dt.rules:
                if not rule.is_active:
                    continue
                conds = rule.applicable_conditions

                if conds.get("always") is True:
                    is_mandatory = True
                    mandatory_reason = "Mandatory for all candidates"
                    break

                if "community" in conds:
                    allowed_comms = [c.upper() for c in conds["community"]]
                    if comm in allowed_comms:
                        is_mandatory = True
                        mandatory_reason = f"Mandatory for {comm} category candidates"
                        break

                if conds.get("is_first_graduate") is True:
                    if application.is_first_graduate or "FIRST GRADUATE" in quota:
                        is_mandatory = True
                        mandatory_reason = "Required to claim First Graduate fee concession"
                        break

                if conds.get("is_pmss_scholarship") is True:
                    if application.is_pmss_scholarship or "PMSS" in quota:
                        is_mandatory = True
                        mandatory_reason = "Required for Post-Matric Scholarship / PMSS"
                        break

                if conds.get("income_under_250k") is True:
                    if income > 0 and income <= 250000:
                        is_mandatory = True
                        mandatory_reason = "Required for annual family income ≤ ₹2,50,000"
                        break

                if conds.get("is_7_5_govt_quota") is True:
                    if application.is_7_5_govt_quota or "7.5" in quota:
                        is_mandatory = True
                        mandatory_reason = "Required for 7.5% Government School Quota verification"
                        break

                if conds.get("non_tn_resident") is True:
                    if state != "tamil nadu":
                        is_mandatory = True
                        mandatory_reason = "Required for candidates outside Tamil Nadu"
                        break

            # Look up uploaded document state
            doc_record = existing_docs.get(dt.id)
            doc_status = "NOT_UPLOADED"
            doc_id = None
            active_version = None
            orig_filename = None
            uploaded_at = None
            file_size_bytes = None

            proc_status = "NOT_PROCESSED"
            pred_type = None
            pred_type_name = None
            heur_conf = None
            clf_name = None
            clf_ver = None
            prep_status = "NOT_PROCESSED"
            has_prep_img = False
            ocr_status = "NOT_PROCESSED"
            has_ocr_res = False
            ext_status = "NOT_PROCESSED"
            has_ext_fields = False

            if doc_record:
                doc_id = doc_record.id
                doc_status = doc_record.status
                if doc_record.versions:
                    # latest version
                    latest_v = doc_record.versions[0]  # versions ordered desc
                    active_version = latest_v.version_number
                    orig_filename = latest_v.original_filename
                    uploaded_at = latest_v.uploaded_at
                    file_size_bytes = latest_v.file_size
                
                latest_clf = doc_latest_clf_jobs.get(doc_id)
                if latest_clf:
                    proc_status = latest_clf.status
                    clf_name = latest_clf.engine_name
                    clf_ver = latest_clf.engine_version
                    if latest_clf.classification_result:
                        pred_type = latest_clf.classification_result.predicted_document_type
                        pred_type_name = latest_clf.classification_result.predicted_document_type_name
                        heur_conf = latest_clf.classification_result.confidence

                latest_prep = doc_latest_prep_jobs.get(doc_id)
                if latest_prep:
                    prep_status = latest_prep.status
                    if latest_prep.preprocessing_result and latest_prep.status == "COMPLETED":
                        has_prep_img = True

                latest_ocr = doc_latest_ocr_jobs.get(doc_id)
                if latest_ocr:
                    ocr_status = latest_ocr.status
                    if latest_ocr.ocr_result and latest_ocr.status == "COMPLETED":
                        has_ocr_res = True

                latest_ext = doc_latest_ext_jobs.get(doc_id)
                if latest_ext:
                    ext_status = latest_ext.status
                    if latest_ext.extraction_result and latest_ext.status == "COMPLETED":
                        has_ext_fields = True

            checklist_items.append(
                ChecklistItemResponse(
                    document_type_id=dt.id,
                    code=dt.code,
                    name=dt.name,
                    description=dt.description,
                    is_mandatory=is_mandatory,
                    mandatory_reason=mandatory_reason,
                    allowed_extensions=dt.allowed_extensions,
                    max_file_size_mb=dt.max_size_mb,
                    document_id=doc_id,
                    document_status=doc_status,
                    active_version=active_version,
                    rejection_reason=None,
                    original_filename=orig_filename,
                    uploaded_at=uploaded_at,
                    file_size_bytes=file_size_bytes,
                    processing_status=proc_status,
                    predicted_document_type=pred_type,
                    predicted_document_type_name=pred_type_name,
                    heuristic_confidence=heur_conf,
                    classifier_name=clf_name,
                    classifier_version=clf_ver,
                    preprocessing_status=prep_status,
                    has_preprocessed_image=has_prep_img,
                    ocr_status=ocr_status,
                    has_ocr_result=has_ocr_res,
                    extraction_status=ext_status,
                    has_extracted_fields=has_ext_fields,
                )
            )

        return checklist_items

