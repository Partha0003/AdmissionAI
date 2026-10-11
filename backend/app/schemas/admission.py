from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict


class AdmissionStatusHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    admission_application_id: str
    previous_status: Optional[str] = None
    new_status: str
    changed_by: str
    actor_role: str
    reason: Optional[str] = None
    metadata_info: Optional[Dict[str, Any]] = None
    created_at: datetime


class AdmissionApplicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    student_id: str
    status: str
    completion_percentage: int
    personal_data: Optional[Dict[str, Any]] = None
    academic_data: Optional[Dict[str, Any]] = None
    parent_data: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    status_history: List[AdmissionStatusHistoryResponse] = []

    # Student summary
    student_name: Optional[str] = None
    tnea_application_number: Optional[str] = None
    allotted_branch: Optional[str] = None


class AdmissionStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    admission_id: str
    student_id: str
    student_name: str
    tnea_application_number: str
    allotted_branch: Optional[str] = None
    current_status: str
    completion_percentage: int
    allowed_next_states: List[str]
    recent_history: List[AdmissionStatusHistoryResponse] = []


class AdmissionTransitionRequest(BaseModel):
    target_state: str
    reason: Optional[str] = "State transition via administrative action"
    metadata: Optional[Dict[str, Any]] = None


class AdminDashboardMetricsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    institution_name: str
    institution_code: str
    academic_year: str
    total_allotted: int
    activation_pending: int
    activated: int
    applications_in_progress: int
    applications_submitted: int
    document_review: int
    documents_verified: int
    admission_confirmed: int


class AdminStudentListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    student_id: str
    admission_id: str
    full_name: str
    tnea_application_number: str
    allotted_branch: Optional[str] = None
    community: Optional[str] = None
    status: str
    completion_percentage: int
    updated_at: datetime
