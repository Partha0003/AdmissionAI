from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class StudentBase(BaseModel):
    tnea_application_number: str
    full_name: str
    date_of_birth: date
    email: str
    mobile: str
    community: Optional[str] = None
    allotted_branch: Optional[str] = None
    quota: Optional[str] = None
    status: str


class StudentResponse(StudentBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    institution_id: str
    created_at: datetime
    updated_at: datetime


class StudentMeResponse(StudentResponse):
    model_config = ConfigDict(from_attributes=True)

    institution_name: str
    institution_code: str
    academic_year: str
    admission_application_id: Optional[str] = None
    admission_status: Optional[str] = None
    completion_percentage: Optional[int] = 0
