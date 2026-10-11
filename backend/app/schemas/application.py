from datetime import date, datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict
from .document import ChecklistItemResponse


class ApplicationDraftUpdate(BaseModel):
    # Personal & Identity Details
    gender: Optional[str] = None
    blood_group: Optional[str] = None
    nationality: Optional[str] = None
    religion: Optional[str] = None
    caste: Optional[str] = None
    mother_tongue: Optional[str] = None
    aadhaar_number: Optional[str] = None
    
    # Contact & Address
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    emergency_contact_relation: Optional[str] = None
    
    # Parents / Guardian Details
    father_name: Optional[str] = None
    father_occupation: Optional[str] = None
    father_mobile: Optional[str] = None
    father_email: Optional[str] = None
    mother_name: Optional[str] = None
    mother_occupation: Optional[str] = None
    mother_mobile: Optional[str] = None
    mother_email: Optional[str] = None
    guardian_name: Optional[str] = None
    guardian_occupation: Optional[str] = None
    guardian_mobile: Optional[str] = None
    guardian_relation: Optional[str] = None
    annual_family_income: Optional[float] = None
    
    # Academic Qualifications - 10th
    tenth_school_name: Optional[str] = None
    tenth_board: Optional[str] = None
    tenth_year_of_passing: Optional[int] = None
    tenth_registration_number: Optional[str] = None
    tenth_total_marks: Optional[float] = None
    tenth_max_marks: Optional[float] = None
    tenth_percentage: Optional[float] = None
    
    # Academic Qualifications - 12th
    twelfth_school_name: Optional[str] = None
    twelfth_board: Optional[str] = None
    twelfth_year_of_passing: Optional[int] = None
    twelfth_registration_number: Optional[str] = None
    twelfth_total_marks: Optional[float] = None
    twelfth_max_marks: Optional[float] = None
    twelfth_percentage: Optional[float] = None
    twelfth_maths_marks: Optional[float] = None
    twelfth_physics_marks: Optional[float] = None
    twelfth_chemistry_marks: Optional[float] = None
    twelfth_cutoff_marks: Optional[float] = None
    
    # Category / Special Quota Flags
    is_first_graduate: Optional[bool] = None
    is_pmss_scholarship: Optional[bool] = None
    is_7_5_govt_quota: Optional[bool] = None
    is_hostel_required: Optional[bool] = None
    is_transport_required: Optional[bool] = None
    
    # Declaration
    declaration_accepted: Optional[bool] = None


class SectionCompletion(BaseModel):
    completed: bool
    fields_filled: int
    fields_total: int
    missing_fields: List[str] = []


class ApplicationCompletionResponse(BaseModel):
    overall_percentage: int
    sections: Dict[str, SectionCompletion]
    documents_uploaded: int
    mandatory_documents_total: int
    mandatory_documents_uploaded: int
    can_submit: bool
    blockers: List[str] = []


class ApplicationDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    application_number: Optional[str] = None
    student_id: str
    status: str
    completion_percentage: int
    
    # Student Account Context (Read-only summary)
    student_name: str
    student_dob: date
    student_email: str
    student_mobile: str
    tnea_application_number: str
    allotted_branch: Optional[str] = None
    community: Optional[str] = None
    quota: Optional[str] = None
    
    # Read-only TNEA Allotment Context
    allotment_order_number: Optional[str] = None
    allotment_quota: Optional[str] = None
    allotted_category: Optional[str] = None
    allotted_college_code: Optional[str] = None
    allotted_branch_name: Optional[str] = None
    
    # Form Details
    gender: Optional[str] = None
    blood_group: Optional[str] = None
    nationality: Optional[str] = "Indian"
    religion: Optional[str] = None
    caste: Optional[str] = None
    mother_tongue: Optional[str] = None
    aadhaar_number: Optional[str] = None
    
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = "Tamil Nadu"
    pincode: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    emergency_contact_relation: Optional[str] = None
    
    father_name: Optional[str] = None
    father_occupation: Optional[str] = None
    father_mobile: Optional[str] = None
    father_email: Optional[str] = None
    mother_name: Optional[str] = None
    mother_occupation: Optional[str] = None
    mother_mobile: Optional[str] = None
    mother_email: Optional[str] = None
    guardian_name: Optional[str] = None
    guardian_occupation: Optional[str] = None
    guardian_mobile: Optional[str] = None
    guardian_relation: Optional[str] = None
    annual_family_income: Optional[float] = None
    
    tenth_school_name: Optional[str] = None
    tenth_board: Optional[str] = None
    tenth_year_of_passing: Optional[int] = None
    tenth_registration_number: Optional[str] = None
    tenth_total_marks: Optional[float] = None
    tenth_max_marks: Optional[float] = None
    tenth_percentage: Optional[float] = None
    
    twelfth_school_name: Optional[str] = None
    twelfth_board: Optional[str] = None
    twelfth_year_of_passing: Optional[int] = None
    twelfth_registration_number: Optional[str] = None
    twelfth_total_marks: Optional[float] = None
    twelfth_max_marks: Optional[float] = None
    twelfth_percentage: Optional[float] = None
    twelfth_maths_marks: Optional[float] = None
    twelfth_physics_marks: Optional[float] = None
    twelfth_chemistry_marks: Optional[float] = None
    twelfth_cutoff_marks: Optional[float] = None
    
    is_first_graduate: bool = False
    is_pmss_scholarship: bool = False
    is_7_5_govt_quota: bool = False
    is_hostel_required: bool = False
    is_transport_required: bool = False
    
    declaration_accepted: bool = False
    declaration_accepted_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    # Dynamic Checklist
    checklist: List[ChecklistItemResponse] = []


class ApplicationSubmissionRequest(BaseModel):
    declaration_accepted: bool


class ApplicationSubmissionResponse(BaseModel):
    admission_id: str
    application_number: str
    status: str
    submitted_at: datetime
    message: str


class AdminApplicationListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    application_id: str
    application_number: Optional[str] = None
    student_id: str
    student_name: str
    tnea_application_number: str
    allotted_branch: Optional[str] = None
    community: Optional[str] = None
    quota: Optional[str] = None
    status: str
    completion_percentage: int
    submitted_at: Optional[datetime] = None
    updated_at: datetime
