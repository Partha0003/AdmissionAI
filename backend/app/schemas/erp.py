from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class ERPReadinessValidationResponse(BaseModel):
    application_id: str
    is_ready: bool
    status: str
    validation_errors: List[str]
    readiness_checks: Dict[str, bool]


class ERPAdmissionRecordResponse(BaseModel):
    id: str
    application_id: str
    application_number: Optional[str] = None
    candidate_name: Optional[str] = None
    allotted_branch: Optional[str] = None
    staging_reference: str
    payload: Dict[str, Any]
    payload_hash: str
    payload_version: int
    status: str
    validation_errors: Optional[List[str]] = None
    retry_count: int
    last_error: Optional[str] = None
    staged_at: datetime
    synced_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ERPSyncRequest(BaseModel):
    simulate_failure: bool = False
    failure_reason: Optional[str] = None


class ERPIntegrationEventResponse(BaseModel):
    id: str
    erp_record_id: str
    event_type: str
    adapter_name: str
    request_reference: Optional[str] = None
    response_reference: Optional[str] = None
    status: str
    error_summary: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True
