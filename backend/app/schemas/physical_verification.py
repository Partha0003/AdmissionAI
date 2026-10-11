from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field

from app.models.physical_verification import (
    AppointmentStatus,
    PhysicalSessionStatus,
    PhysicalVerificationDecision,
    PhysicalDocDecision,
    PhysicalCorrectionReason,
    PhysicalVerificationAction,
)


class AppointmentCreateRequest(BaseModel):
    appointment_date: date
    start_time: str = Field(..., description="e.g. '09:30 AM'")
    end_time: str = Field(..., description="e.g. '10:00 AM'")
    location: Optional[str] = "XYZ Main Campus — Central Admission Hall"
    counter_desk: Optional[str] = "Verification Desk 1"
    notes: Optional[str] = None


class AppointmentRescheduleRequest(BaseModel):
    appointment_date: date
    start_time: str
    end_time: str
    reason: Optional[str] = None


class AppointmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    application_id: str
    appointment_date: date
    start_time: str
    end_time: str
    token_number: str
    checkin_token: str
    location: str
    counter_desk: Optional[str] = None
    appointment_status: str
    notes: Optional[str] = None
    created_by_id: Optional[str] = None
    checked_in_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class AvailableSlotResponse(BaseModel):
    slot_date: date
    start_time: str
    end_time: str
    available_capacity: int
    location: str
    counter_desk: str


class CheckInRequest(BaseModel):
    token_number: Optional[str] = None
    checkin_token: Optional[str] = None
    counter_desk: Optional[str] = None


class CheckInResponse(BaseModel):
    message: str
    appointment_id: str
    token_number: str
    application_id: str
    candidate_name: str
    allotted_branch: Optional[str] = None
    checked_in_at: datetime
    counter_desk: Optional[str] = None


class PhysicalChecklistChecks(BaseModel):
    original_presented: bool = False
    document_legible: bool = True
    name_matches: bool = True
    dob_matches: Optional[bool] = None
    id_matches: Optional[bool] = None
    photo_check_done: Optional[bool] = None
    custom_checks: Optional[Dict[str, Any]] = None


class DocumentVerifyRequest(BaseModel):
    officer_decision: str = Field(..., description="VERIFIED, NOT_VERIFIED, CORRECTION_REQUIRED, NOT_APPLICABLE, PENDING")
    verification_notes: Optional[str] = None
    discrepancy_reason: Optional[str] = None
    checklist_checks: Optional[Dict[str, Any]] = None


class DocumentCorrectionRequest(BaseModel):
    discrepancy_reason: str = Field(..., description="Enum value from PhysicalCorrectionReason")
    verification_notes: Optional[str] = None
    checklist_checks: Optional[Dict[str, Any]] = None


class SessionStartRequest(BaseModel):
    appointment_id: Optional[str] = None
    counter_desk: Optional[str] = None
    officer_notes: Optional[str] = None


class SessionCompleteRequest(BaseModel):
    overall_decision: str = Field(..., description="VERIFIED, PARTIALLY_VERIFIED, CORRECTION_REQUIRED, REJECTED, PENDING")
    officer_notes: Optional[str] = None


class SessionReopenRequest(BaseModel):
    reason: str = Field(..., min_length=3, description="Justification for reopening completed physical verification session")


class PhysicalDocumentVerificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    document_id: str
    document_version_id: Optional[str] = None
    document_type_id: Optional[str] = None
    document_type_code: Optional[str] = None
    document_type_name: Optional[str] = None
    version_number: Optional[int] = None
    officer_decision: str
    verification_notes: Optional[str] = None
    discrepancy_reason: Optional[str] = None
    checklist_checks: Optional[Dict[str, Any]] = None
    verified_by_id: Optional[str] = None
    verified_by_name: Optional[str] = None
    verified_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class PhysicalSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    application_id: str
    appointment_id: Optional[str] = None
    officer_id: Optional[str] = None
    officer_name: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    session_status: str
    overall_decision: str
    officer_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    document_verifications: List[PhysicalDocumentVerificationResponse] = []


class PhysicalVerificationAuditResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    application_id: str
    appointment_id: Optional[str] = None
    session_id: Optional[str] = None
    actor_id: Optional[str] = None
    actor_name: Optional[str] = None
    actor_role: Optional[str] = None
    action: str
    details: Optional[Dict[str, Any]] = None
    created_at: datetime


class PhysicalVerificationDeskSummary(BaseModel):
    application_id: str
    application_number: str
    candidate_name: str
    student_email: str
    student_phone: Optional[str] = None
    allotted_branch: Optional[str] = None
    allotted_category: Optional[str] = None
    appointment: Optional[AppointmentResponse] = None
    active_session: Optional[PhysicalSessionResponse] = None
    scrutiny_status: Optional[str] = None
    reconciliation_status: Optional[str] = None
