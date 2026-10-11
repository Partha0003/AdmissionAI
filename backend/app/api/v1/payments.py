from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.api.deps import get_current_user, require_roles
from app.models.user import User
from app.schemas.payment import (
    PaymentInitiateRequest,
    DemandDraftSubmissionRequest,
    OnlinePaymentSimulationRequest,
    FinanceReviewActionRequest,
    PaymentTransactionResponse,
    PaymentAuditLogResponse,
    StudentPaymentSummaryResponse,
)
from app.services.payment_service import PaymentService

router = APIRouter(tags=["Phase 6 - Payment & DD Reconciliation"])


# ================= Student Endpoints =================

@router.get("/me", response_model=StudentPaymentSummaryResponse)
async def get_my_payment_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns active fee requirement and payment status for the logged-in student.
    """
    return await PaymentService.get_student_payment_summary(db, current_user)


@router.post("/initiate", response_model=PaymentTransactionResponse, status_code=status.HTTP_201_CREATED)
async def initiate_payment(
    payload: PaymentInitiateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Student initiates payment method selection (Online or DD).
    """
    return await PaymentService.initiate_payment(
        db=db,
        user=current_user,
        payment_method=payload.payment_method,
        notes=payload.notes,
    )


@router.post("/{payment_id}/submit-dd", response_model=PaymentTransactionResponse)
async def submit_demand_draft(
    payment_id: str,
    payload: DemandDraftSubmissionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Student submits DD details with supporting document version pinning.
    """
    return await PaymentService.submit_demand_draft(
        db=db,
        user=current_user,
        payment_id=payment_id,
        dd_number=payload.dd_number,
        dd_date=payload.dd_date,
        bank_name=payload.bank_name,
        branch_name=payload.branch_name,
        amount=payload.amount,
        supporting_document_id=payload.supporting_document_id,
        supporting_document_version_id=payload.supporting_document_version_id,
    )


@router.post("/{payment_id}/simulate-online", response_model=PaymentTransactionResponse)
async def simulate_online_payment(
    payment_id: str,
    payload: OnlinePaymentSimulationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Student executes simulated online payment via MockPaymentAdapter.
    """
    return await PaymentService.simulate_online_payment(
        db=db,
        user=current_user,
        payment_id=payment_id,
        simulate_failure=payload.simulate_failure,
        notes=payload.notes,
    )


# ================= Admin / Finance Desk Endpoints =================

@router.get("/admin/list", response_model=List[PaymentTransactionResponse])
async def list_admin_payments(
    status: Optional[str] = Query(None),
    method: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(["FINANCE_OFFICER", "ADMISSION_HEAD", "SUPER_ADMIN"])),
):
    """
    Finance Officer lists payments in queue.
    """
    return await PaymentService.list_admin_payments(
        db=db,
        status_filter=status,
        method_filter=method,
        search=search,
    )


@router.get("/admin/{payment_id}", response_model=PaymentTransactionResponse)
async def get_admin_payment_detail(
    payment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(["FINANCE_OFFICER", "ADMISSION_HEAD", "SUPER_ADMIN"])),
):
    """
    Finance Officer inspects payment transaction and DD submission evidence.
    """
    return await PaymentService.get_payment_by_id(db, payment_id)


@router.post("/admin/{payment_id}/review", response_model=PaymentTransactionResponse)
async def review_payment(
    payment_id: str,
    payload: FinanceReviewActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(["FINANCE_OFFICER", "ADMISSION_HEAD", "SUPER_ADMIN"])),
):
    """
    Finance Officer records VERIFIED, REJECTED, or CORRECTION_REQUIRED decision.
    """
    return await PaymentService.finance_review_payment(
        db=db,
        officer=current_user,
        payment_id=payment_id,
        decision=payload.decision,
        reason=payload.reason,
        notes=payload.notes,
    )


@router.get("/admin/{payment_id}/audit", response_model=List[PaymentAuditLogResponse])
async def get_payment_audit_logs(
    payment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(["FINANCE_OFFICER", "ADMISSION_HEAD", "SUPER_ADMIN"])),
):
    """
    Returns audit trail for payment transaction.
    """
    return await PaymentService.get_payment_audit_logs(db, payment_id)
