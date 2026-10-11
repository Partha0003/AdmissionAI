from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from app.models.onboarding import (
    StudentType,
    StudentTypeStatus,
    OnboardingStatus,
    ParentLinkStatus,
)


class StudentTypeRequest(BaseModel):
    student_type: StudentType


class StudentTypeConfirmRequest(BaseModel):
    student_type: StudentType


class ChecklistItemResponse(BaseModel):
    id: str
    item_key: str
    title: str
    category: str
    student_type_scope: str
    is_mandatory: bool
    is_acknowledged: bool
    acknowledged_at: Optional[datetime] = None
    source_reference: str
    sort_order: int

    class Config:
        from_attributes = True


class OnboardingProfileResponse(BaseModel):
    id: str
    student_id: str
    application_id: str
    academic_year: str
    student_type: StudentType
    student_type_status: StudentTypeStatus
    onboarding_status: OnboardingStatus
    overall_completion_percentage: int
    checklist_items: List[ChecklistItemResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ParentInvitationCreate(BaseModel):
    parent_name: str = Field(..., min_length=2, max_length=150)
    phone: str = Field(..., min_length=10, max_length=20)
    email: Optional[str] = None
    relationship: str = Field("GUARDIAN", max_length=50)


class ParentInvitationResponse(BaseModel):
    link_id: str
    invite_token: str  # Raw token returned only on generation
    relationship: str
    expires_at: str
    status: str


class ParentRedeemRequest(BaseModel):
    invite_token: str = Field(..., min_length=10)
    parent_name: str = Field(..., min_length=2, max_length=150)
    phone: str = Field(..., min_length=10, max_length=20)
    email: Optional[str] = None


class ParentRedeemResponse(BaseModel):
    success: bool
    message: str
    link_id: str
    student_id: str
    relationship: str
    status: str


class GuidanceCardResponse(BaseModel):
    category: str
    title: str
    source_reference: str
    attribution: Optional[str] = None
    data: Dict[str, Any]


class InaugurationEventResponse(BaseModel):
    id: str
    academic_year: str
    event_name: str
    event_date: str
    reporting_time: str
    ceremony_time: str
    venue: str
    instructions_student: str
    instructions_parent: str
    event_status: str  # UPCOMING, TODAY, PAST


class TransportConfigResponse(BaseModel):
    is_configured: bool
    college_code: str
    message: Optional[str] = None
    routes: List[Dict[str, Any]] = []
    general_instructions: Optional[str] = None


class OnboardingAuditLogResponse(BaseModel):
    id: str
    actor_id: str
    actor_role: str
    action: str
    profile_id: Optional[str] = None
    student_id: Optional[str] = None
    details_json: Dict[str, Any] = {}
    created_at: datetime

    class Config:
        from_attributes = True
