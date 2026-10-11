from typing import Optional
from pydantic import BaseModel, Field


class StudentActivationRequest(BaseModel):
    activation_token: str = Field(..., description="One-time cryptographically generated activation token")
    password: str = Field(..., min_length=6, description="New secure password for student login")


class StudentActivationResponse(BaseModel):
    success: bool
    message: str
    student_id: str
    student_name: str
    tnea_application_number: str
    email: str
    new_status: str
