from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.models.user import User
from app.models.student import Student
from app.api.deps import get_current_user, get_current_student, require_roles
from app.services.scrutiny_service import ScrutinyService
from app.schemas.scrutiny import (
    StartReviewRequest,
    DocumentReviewRequest,
    FieldReviewRequest,
    CorrectionRequestPayload,
    CompleteReviewRequest,
    ReopenReviewRequest,
    AdmissionReviewResponse,
    DocumentReviewItemResponse,
    FieldReviewItemResponse,
    ScrutinyAuditLogResponse,
    StudentCorrectionSummaryResponse,
)

router = APIRouter(prefix="/scrutiny", tags=["Human-in-the-Loop Scrutiny"])

admin_staff_check = require_roles(["ADMIN_VERIFIER", "ADMISSION_HEAD", "SUPER_ADMIN", "FINANCE_OFFICER"])
lead_admin_check = require_roles(["ADMISSION_HEAD", "SUPER_ADMIN"])


def build_review_response(review) -> AdmissionReviewResponse:
    doc_reviews = [
        DocumentReviewItemResponse(
            id=item.id,
            review_id=item.review_id,
            document_id=item.document_id,
            document_version_id=item.document_version_id,
            status=item.status,
            correction_reason=item.correction_reason,
            reviewer_comments=item.reviewer_comments,
            reviewed_by_id=item.reviewed_by_id,
            reviewed_at=item.reviewed_at,
        )
        for item in (review.document_reviews or [])
    ]

    field_reviews = [
        FieldReviewItemResponse(
            id=item.id,
            review_id=item.review_id,
            field_key=item.field_key,
            declared_value=item.declared_value,
            extracted_value=item.extracted_value,
            reconciliation_status=item.reconciliation_status,
            decision=item.decision,
            notes=item.notes,
            document_id=item.document_id,
            document_version_id=item.document_version_id,
            reviewed_by_id=item.reviewed_by_id,
            reviewed_at=item.reviewed_at,
        )
        for item in (review.field_reviews or [])
    ]

    audit_logs = [
        ScrutinyAuditLogResponse(
            id=log.id,
            review_id=log.review_id,
            application_id=log.application_id,
            user_id=log.user_id,
            user_name=log.user_name,
            user_role=log.user_role,
            action=log.action,
            previous_status=log.previous_status,
            new_status=log.new_status,
            details=log.details or {},
            created_at=log.created_at,
        )
        for log in (review.audit_logs or [])
    ]

    return AdmissionReviewResponse(
        id=review.id,
        application_id=review.application_id,
        reviewer_id=review.reviewer_id,
        reviewer_name=review.reviewer.email if review.reviewer else None,
        reviewer_email=review.reviewer.email if review.reviewer else None,
        status=review.status,
        decision=review.decision,
        overall_comments=review.overall_comments,
        correction_reason=review.correction_reason,
        correction_instructions=review.correction_instructions,
        reviewed_document_versions=review.reviewed_document_versions or {},
        reviewed_reconciliation_id=review.reviewed_reconciliation_id,
        started_at=review.started_at,
        completed_at=review.completed_at,
        created_at=review.created_at,
        updated_at=review.updated_at,
        document_reviews=doc_reviews,
        field_reviews=field_reviews,
        audit_logs=audit_logs,
    )


@router.post("/applications/{application_id}/start", response_model=AdmissionReviewResponse)
async def start_admission_review(
    application_id: str,
    payload: Optional[StartReviewRequest] = None,
    current_user: User = Depends(admin_staff_check),
    db: AsyncSession = Depends(get_db),
):
    """
    Initializes or transitions scrutiny review session to IN_REVIEW.
    Captures snapshot of participating document versions and latest reconciliation.
    """
    notes = payload.notes if payload else None
    review = await ScrutinyService.start_review(
        db=db,
        application_id=application_id,
        current_user=current_user,
        notes=notes,
    )
    return build_review_response(review)


@router.get("/applications/{application_id}/current", response_model=AdmissionReviewResponse)
async def get_current_admission_review(
    application_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves the active scrutiny review state, document decisions, field decisions, and audit log.
    Enforces Anti-IDOR for student callers.
    """
    review = await ScrutinyService.get_current_review(
        db=db,
        application_id=application_id,
        current_user=current_user,
    )
    return build_review_response(review)


@router.get("/applications/{application_id}/history", response_model=List[AdmissionReviewResponse])
async def get_admission_review_history(
    application_id: str,
    current_user: User = Depends(admin_staff_check),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves complete historical scrutiny review records for an application.
    """
    reviews = await ScrutinyService.get_review_history(
        db=db,
        application_id=application_id,
        current_user=current_user,
    )
    return [build_review_response(r) for r in reviews]


@router.post("/applications/{application_id}/documents/review", response_model=DocumentReviewItemResponse)
async def record_document_review(
    application_id: str,
    payload: DocumentReviewRequest,
    current_user: User = Depends(admin_staff_check),
    db: AsyncSession = Depends(get_db),
):
    """
    Records human scrutiny decision for a specific uploaded document.
    """
    item = await ScrutinyService.record_document_review(
        db=db,
        application_id=application_id,
        payload=payload,
        current_user=current_user,
    )
    return DocumentReviewItemResponse(
        id=item.id,
        review_id=item.review_id,
        document_id=item.document_id,
        document_version_id=item.document_version_id,
        status=item.status,
        correction_reason=item.correction_reason,
        reviewer_comments=item.reviewer_comments,
        reviewed_by_id=item.reviewed_by_id,
        reviewed_at=item.reviewed_at,
    )


@router.post("/applications/{application_id}/fields/review", response_model=FieldReviewItemResponse)
async def record_field_review(
    application_id: str,
    payload: FieldReviewRequest,
    current_user: User = Depends(admin_staff_check),
    db: AsyncSession = Depends(get_db),
):
    """
    Records human scrutiny decision on an individual extracted entity/field.
    """
    item = await ScrutinyService.record_field_review(
        db=db,
        application_id=application_id,
        payload=payload,
        current_user=current_user,
    )
    return FieldReviewItemResponse(
        id=item.id,
        review_id=item.review_id,
        field_key=item.field_key,
        declared_value=item.declared_value,
        extracted_value=item.extracted_value,
        reconciliation_status=item.reconciliation_status,
        decision=item.decision,
        notes=item.notes,
        document_id=item.document_id,
        document_version_id=item.document_version_id,
        reviewed_by_id=item.reviewed_by_id,
        reviewed_at=item.reviewed_at,
    )


@router.post("/applications/{application_id}/request-correction", response_model=AdmissionReviewResponse)
async def request_candidate_correction(
    application_id: str,
    payload: CorrectionRequestPayload,
    current_user: User = Depends(admin_staff_check),
    db: AsyncSession = Depends(get_db),
):
    """
    Issues a formal correction request to the candidate with structured reasons and guidance.
    Transitions review and application state to CORRECTION_REQUIRED.
    """
    review = await ScrutinyService.request_correction(
        db=db,
        application_id=application_id,
        payload=payload,
        current_user=current_user,
    )
    return build_review_response(review)


@router.post("/applications/{application_id}/complete", response_model=AdmissionReviewResponse)
async def complete_admission_review(
    application_id: str,
    payload: CompleteReviewRequest,
    current_user: User = Depends(admin_staff_check),
    db: AsyncSession = Depends(get_db),
):
    """
    Records final human verification decision (VERIFIED / REJECTED / CORRECTION_REQUIRED).
    Preserves document version snapshot and immutable audit log.
    """
    review = await ScrutinyService.complete_review(
        db=db,
        application_id=application_id,
        payload=payload,
        current_user=current_user,
    )
    return build_review_response(review)


@router.post("/applications/{application_id}/reopen", response_model=AdmissionReviewResponse)
async def reopen_admission_review(
    application_id: str,
    payload: ReopenReviewRequest,
    current_user: User = Depends(lead_admin_check),
    db: AsyncSession = Depends(get_db),
):
    """
    Reopens a finalized scrutiny review for further examination.
    RBAC: Strictly restricted to ADMISSION_HEAD and SUPER_ADMIN.
    """
    review = await ScrutinyService.reopen_review(
        db=db,
        application_id=application_id,
        payload=payload,
        current_user=current_user,
    )
    return build_review_response(review)


@router.get("/applications/{application_id}/audit-logs", response_model=List[ScrutinyAuditLogResponse])
async def get_scrutiny_audit_logs(
    application_id: str,
    current_user: User = Depends(admin_staff_check),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves complete audit trail of scrutiny actions performed on this application.
    """
    review = await ScrutinyService.get_current_review(
        db=db,
        application_id=application_id,
        current_user=current_user,
    )
    return [
        ScrutinyAuditLogResponse(
            id=log.id,
            review_id=log.review_id,
            application_id=log.application_id,
            user_id=log.user_id,
            user_name=log.user_name,
            user_role=log.user_role,
            action=log.action,
            previous_status=log.previous_status,
            new_status=log.new_status,
            details=log.details or {},
            created_at=log.created_at,
        )
        for log in (review.audit_logs or [])
    ]


@router.get("/me/corrections", response_model=StudentCorrectionSummaryResponse)
async def get_my_corrections(
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """
    Student-facing endpoint: Retrieves active correction instructions, reasons, and affected documents.
    """
    summary = await ScrutinyService.get_student_corrections(
        db=db,
        student=student,
    )
    return StudentCorrectionSummaryResponse(**summary)
