from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.schemas.admission import (
    AdmissionApplicationResponse,
    AdmissionStatusResponse,
    AdmissionTransitionRequest,
)
from app.models.user import User
from app.api.deps import get_current_user
from app.services.admission_service import (
    get_admission_by_id,
    transition_admission_state,
)
from app.core.state_machine import (
    AdmissionState,
    VALID_TRANSITIONS,
    InvalidStateTransitionError,
    UnauthorizedTransitionError,
)

router = APIRouter(prefix="/admissions", tags=["Admissions"])


def check_admission_access(admission, current_user: User):
    """IDOR Protection: Ensures STUDENT users can only access their own admission records."""
    user_role = current_user.role.name if current_user.role else "STUDENT"
    if user_role == "STUDENT":
        if not admission.student or admission.student.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: You are not authorized to view this admission record"
            )


@router.get("/{admission_id}", response_model=AdmissionApplicationResponse)
async def get_admission_details(
    admission_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieves full details of an admission application.
    Enforces IDOR checks so students cannot view another student's file.
    """
    admission = await get_admission_by_id(db, admission_id)
    if not admission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Admission record with ID '{admission_id}' not found"
        )
    
    check_admission_access(admission, current_user)
    
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
        student_name=admission.student.full_name if admission.student else None,
        tnea_application_number=admission.student.tnea_application_number if admission.student else None,
        allotted_branch=admission.student.allotted_branch if admission.student else None,
    )


@router.get("/{admission_id}/status", response_model=AdmissionStatusResponse)
async def get_admission_status_info(
    admission_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns current admission state, calculated allowed next states, and status history.
    """
    admission = await get_admission_by_id(db, admission_id)
    if not admission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Admission record with ID '{admission_id}' not found"
        )
    
    check_admission_access(admission, current_user)
    
    try:
        curr_enum = AdmissionState(admission.status)
        allowed_next = [s.value for s in VALID_TRANSITIONS.get(curr_enum, set())]
    except ValueError:
        allowed_next = []
        
    return AdmissionStatusResponse(
        admission_id=admission.id,
        student_id=admission.student_id,
        student_name=admission.student.full_name if admission.student else "",
        tnea_application_number=admission.student.tnea_application_number if admission.student else "",
        allotted_branch=admission.student.allotted_branch if admission.student else None,
        current_status=admission.status,
        completion_percentage=admission.completion_percentage,
        allowed_next_states=allowed_next,
        recent_history=admission.status_history[:10]
    )


@router.post("/{admission_id}/transition", response_model=AdmissionApplicationResponse)
async def transition_state(
    admission_id: str,
    payload: AdmissionTransitionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Executes a formal lifecycle state transition through the Admission State Machine.
    Validates state graph reachability, role authority, and records an immutable audit log.
    """
    admission = await get_admission_by_id(db, admission_id)
    if not admission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Admission record with ID '{admission_id}' not found"
        )
    
    check_admission_access(admission, current_user)
    user_role = current_user.role.name if current_user.role else "STUDENT"

    try:
        updated_admission = await transition_admission_state(
            db=db,
            admission_id=admission.id,
            requested_state_str=payload.target_state,
            actor_email=current_user.email,
            actor_role_str=user_role,
            reason=payload.reason,
            metadata_info=payload.metadata
        )
        return AdmissionApplicationResponse(
            id=updated_admission.id,
            student_id=updated_admission.student_id,
            status=updated_admission.status,
            completion_percentage=updated_admission.completion_percentage,
            personal_data=updated_admission.personal_data,
            academic_data=updated_admission.academic_data,
            parent_data=updated_admission.parent_data,
            created_at=updated_admission.created_at,
            updated_at=updated_admission.updated_at,
            status_history=updated_admission.status_history,
            student_name=updated_admission.student.full_name if updated_admission.student else None,
            tnea_application_number=updated_admission.student.tnea_application_number if updated_admission.student else None,
            allotted_branch=updated_admission.student.allotted_branch if updated_admission.student else None,
        )
    except InvalidStateTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )
    except UnauthorizedTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message
        )
