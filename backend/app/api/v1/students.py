from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.schemas.student import StudentMeResponse
from app.schemas.admission import AdmissionApplicationResponse
from app.schemas.tnea import TNEAAllotmentResponse
from app.models.student import Student
from app.models.user import User
from app.api.deps import get_current_student, require_roles
from app.services.admission_service import get_admission_by_student_id
from app.services.tnea_service import get_tnea_allotment_by_student_id
from app.core.config import settings

router = APIRouter(prefix="/students", tags=["Students"])


@router.get("/me", response_model=StudentMeResponse)
async def get_my_student_profile(
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns the authenticated student's profile details along with active admission status.
    """
    admission = await get_admission_by_student_id(db, student.id)
    
    return StudentMeResponse(
        id=student.id,
        user_id=student.user_id,
        institution_id=student.institution_id,
        tnea_application_number=student.tnea_application_number,
        full_name=student.full_name,
        date_of_birth=student.date_of_birth,
        email=student.email,
        mobile=student.mobile,
        community=student.community,
        allotted_branch=student.allotted_branch,
        quota=student.quota,
        status=student.status,
        created_at=student.created_at,
        updated_at=student.updated_at,
        institution_name=settings.INSTITUTION_NAME,
        institution_code=settings.INSTITUTION_CODE,
        academic_year=settings.ACADEMIC_YEAR,
        admission_application_id=admission.id if admission else None,
        admission_status=admission.status if admission else student.status,
        completion_percentage=admission.completion_percentage if admission else 0
    )


@router.get("/me/admission", response_model=AdmissionApplicationResponse)
async def get_my_admission(
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns the student's admission application record, including timeline status history.
    """
    admission = await get_admission_by_student_id(db, student.id)
    if not admission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admission record not found for this student"
        )
    
    return AdmissionApplicationResponse(
        id=admission.id,
        student_id=admission.student_id,
        status=admission.status,
        completion_percentage=admission.completion_percentage,
        personal_data=admission.personal_data,
        academic_data=admission.academic_data,
        parent_data=admission.parent_data,
        created_at=admission.created_at,
        updated_at=admission.updated_at,
        status_history=admission.status_history,
        student_name=student.full_name,
        tnea_application_number=student.tnea_application_number,
        allotted_branch=student.allotted_branch
    )


@router.get("/me/allotment", response_model=TNEAAllotmentResponse)
async def get_my_allotment(
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns the authenticated student's TNEA allotment order details.
    Enforces scoped IDOR protection.
    """
    allotment = await get_tnea_allotment_by_student_id(db, student.id)
    if not allotment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="TNEA Allotment order record not found for this student."
        )
    return TNEAAllotmentResponse(**allotment)
