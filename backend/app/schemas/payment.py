from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class FeeRequirementResponse(BaseModel):
    id: str
    academic_year: str
    category: str
    quota: str
    amount: float
    currency: str
    description: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True


class DemandDraftSubmissionRequest(BaseModel):
    dd_number: str = Field(..., min_length=3, max_length=64)
    dd_date: str = Field(..., min_length=8, max_length=20)
    bank_name: str = Field(..., min_length=2, max_length=128)
    branch_name: Optional[str] = Field(None, max_length=128)
    amount: float = Field(..., gt=0)
    supporting_document_id: Optional[str] = None
    supporting_document_version_id: Optional[str] = None


class DemandDraftResponse(BaseModel):
    id: str
    payment_id: str
    dd_number: str
    dd_date: str
    bank_name: str
    branch_name: Optional[str] = None
    amount: float
    supporting_document_id: Optional[str] = None
    supporting_document_version_id: Optional[str] = None
    supporting_document_version_number: Optional[int] = None
    submitted_at: datetime
    finance_verified_at: Optional[datetime] = None
    finance_notes: Optional[str] = None

    class Config:
        from_attributes = True


class PaymentInitiateRequest(BaseModel):
    payment_method: str = Field(..., pattern="^(DEMO_ONLINE_PAYMENT|DEMAND_DRAFT)$")
    amount: Optional[float] = None
    notes: Optional[str] = None


class OnlinePaymentSimulationRequest(BaseModel):
    simulate_failure: bool = False
    notes: Optional[str] = None


class PaymentTransactionResponse(BaseModel):
    id: str
    application_id: str
    application_number: Optional[str] = None
    candidate_name: Optional[str] = None
    allotted_branch: Optional[str] = None
    payment_reference: str
    payment_method: str
    amount: float
    currency: str
    status: str
    initiated_at: datetime
    submitted_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None
    verified_by_id: Optional[str] = None
    rejection_reason: Optional[str] = None
    notes: Optional[str] = None
    fee_requirement: Optional[FeeRequirementResponse] = None
    dd_submission: Optional[DemandDraftResponse] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FinanceReviewActionRequest(BaseModel):
    decision: str = Field(..., pattern="^(VERIFIED|REJECTED|CORRECTION_REQUIRED)$")
    reason: Optional[str] = None
    notes: Optional[str] = None


class PaymentAuditLogResponse(BaseModel):
    id: str
    application_id: str
    payment_id: str
    actor_id: Optional[str] = None
    actor_name: Optional[str] = None
    actor_role: Optional[str] = None
    action: str
    details: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class StudentPaymentSummaryResponse(BaseModel):
    application_id: str
    application_number: str
    has_active_payment: bool
    fee_requirement: Optional[FeeRequirementResponse] = None
    active_payment: Optional[PaymentTransactionResponse] = None
    payment_status: str
    is_payment_verified: bool
    has_correction_required: bool
    correction_reason: Optional[str] = None
    correction_instructions: Optional[str] = None
    duplicate_warning: Optional[str] = None
