from datetime import date, datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class TNEARecordPayload(BaseModel):
    tnea_application_number: str = Field(..., description="Unique TNEA application ID (e.g. XYZ2026001)")
    allotment_number: str = Field(..., description="Unique allotment order ID (e.g. XYZALT2026001)")
    student_name: str = Field(..., description="Full name of allotted candidate")
    date_of_birth: Optional[date] = Field(None, description="Date of birth YYYY-MM-DD")
    email: Optional[str] = Field(None, description="Candidate contact email")
    mobile: Optional[str] = Field(None, description="Candidate mobile number")
    college_code: str = Field(..., description="Target college code (e.g. XYZ)")
    college_name: str = Field(..., description="Target institution name")
    branch_code: Optional[str] = Field(None, description="Department branch code (e.g. CS)")
    branch_name: str = Field(..., description="Branch title (e.g. Computer Science and Engineering)")
    community: Optional[str] = Field(None, description="Category (OC, BC, MBC, SC, ST)")
    quota: Optional[str] = Field(None, description="Allotment quota (e.g. GOVT, MANAGEMENT)")
    cutoff_mark: Optional[float] = Field(None, description="TNEA normalised cutoff mark")
    allotment_date: date = Field(..., description="Date of allotment order issuance")
    joining_deadline: date = Field(..., description="Prescribed reporting / joining deadline")
    allotment_status: str = Field(default="ALLOTTED", description="TNEA status")


class TNEAImportRequest(BaseModel):
    source: str = Field(default="MOCK_TNEA", description="Source descriptor")
    filename_or_reference: Optional[str] = Field(None, description="Reference batch name or uploaded filename")
    records: List[TNEARecordPayload] = Field(..., description="List of synthetic allotment records to import")


class TNEARecordResult(BaseModel):
    tnea_application_number: str
    student_name: str
    branch_name: str
    allotment_number: str
    status: str  # "CREATED", "EXISTING_UPDATED", "SKIPPED_DUPLICATE", "REJECTED_WRONG_INSTITUTION", "FAILED_VALIDATION"
    message: str
    raw_activation_token: Optional[str] = None  # Returned ONLY in demo/admin batch response for testing


class TNEAImportResponse(BaseModel):
    batch_id: str
    source: str
    total_records: int
    successful_records: int
    duplicate_records: int
    skipped_records: int
    failed_records: int
    status: str  # "COMPLETED", "PARTIAL", "FAILED"
    results: List[TNEARecordResult]
    dispatched_notifications_count: int


class TNEAImportBatchListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source: str
    filename_or_reference: Optional[str]
    record_count: int
    successful_count: int
    failed_count: int
    duplicate_count: int
    skipped_count: int
    imported_by: str
    imported_at: datetime
    status: str


class TNEAAllotmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    student_id: Optional[str]
    tnea_application_number: str
    allotment_number: str
    college_code: str
    college_name: str
    branch_code: Optional[str]
    branch_name: str
    community: Optional[str]
    quota: Optional[str]
    cutoff_mark: Optional[float]
    allotment_date: date
    joining_deadline: date
    allotment_status: str
    source: str
    imported_at: datetime
    student_name: Optional[str] = None
    admission_status: Optional[str] = None
