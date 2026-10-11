from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class UserBase(BaseModel):
    email: str
    is_active: bool = True


class UserCreate(UserBase):
    password: str
    role_id: int


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    role_id: int
    role_name: Optional[str] = None
    created_at: datetime


class UserMeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    role: str
    is_active: bool
    student_id: Optional[str] = None
    institution_name: str
    institution_code: str
    academic_year: str
