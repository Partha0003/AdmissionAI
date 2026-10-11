from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.admission import AdmissionApplication, AdmissionStatusHistory
from app.models.student import Student
from app.models.institution import Institution
from app.core.state_machine import (
    AdmissionState,
    UserRole,
    validate_and_transition,
    VALID_TRANSITIONS,
    InvalidStateTransitionError,
    UnauthorizedTransitionError,
)
from app.core.config import settings


async def get_admission_by_student_id(
    db: AsyncSession, student_id: str
) -> Optional[AdmissionApplication]:
    query = (
        select(AdmissionApplication)
        .where(AdmissionApplication.student_id == student_id)
        .options(
            selectinload(AdmissionApplication.status_history),
            selectinload(AdmissionApplication.student)
        )
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_admission_by_id(
    db: AsyncSession, admission_id: str
) -> Optional[AdmissionApplication]:
    query = (
        select(AdmissionApplication)
        .where(AdmissionApplication.id == admission_id)
        .options(
            selectinload(AdmissionApplication.status_history),
            selectinload(AdmissionApplication.student)
        )
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def transition_admission_state(
    db: AsyncSession,
    admission_id: str,
    requested_state_str: str,
    actor_email: str,
    actor_role_str: str,
    reason: Optional[str] = None,
    metadata_info: Optional[Dict[str, Any]] = None,
) -> AdmissionApplication:
    admission = await get_admission_by_id(db, admission_id)
    if not admission:
        raise ValueError(f"Admission application with ID '{admission_id}' not found.")

    try:
        current_state = AdmissionState(admission.status)
    except ValueError:
        current_state = AdmissionState.ALLOTTED

    try:
        target_state = AdmissionState(requested_state_str)
    except ValueError:
        raise InvalidStateTransitionError(
            f"'{requested_state_str}' is not a recognized admission state.",
            current_state=admission.status,
            requested_state=requested_state_str
        )

    try:
        actor_role = UserRole(actor_role_str)
    except ValueError:
        raise UnauthorizedTransitionError(
            f"Unrecognized role '{actor_role_str}'.",
            current_state=admission.status,
            requested_state=requested_state_str
        )

    # Validate transition via FSM
    new_state = validate_and_transition(
        current_state=current_state,
        requested_state=target_state,
        actor_role=actor_role
    )

    # Record history log and append to relationship
    history_entry = AdmissionStatusHistory(
        admission_application_id=admission.id,
        previous_status=current_state.value,
        new_status=new_state.value,
        changed_by=actor_email,
        actor_role=actor_role.value,
        reason=reason or f"Transitioned to {new_state.value} by {actor_role.value}",
        metadata_info=metadata_info or {}
    )
    admission.status_history.insert(0, history_entry)

    # Update application & student state
    admission.status = new_state.value
    if admission.student:
        admission.student.status = new_state.value

    await db.commit()
    return admission


async def get_dashboard_metrics(db: AsyncSession) -> Dict[str, Any]:
    # Query aggregated status counts
    query = (
        select(AdmissionApplication.status, func.count(AdmissionApplication.id))
        .group_by(AdmissionApplication.status)
    )
    result = await db.execute(query)
    status_counts = dict(result.fetchall())

    total_query = select(func.count(Student.id))
    total_res = await db.execute(total_query)
    total_students = total_res.scalar_one() or 0

    return {
        "institution_name": settings.INSTITUTION_NAME,
        "institution_code": settings.INSTITUTION_CODE,
        "academic_year": settings.ACADEMIC_YEAR,
        "total_allotted": total_students,
        "activation_pending": status_counts.get("ACTIVATION_PENDING", 0) + status_counts.get("ALLOTTED", 0),
        "activated": status_counts.get("ACTIVATED", 0),
        "applications_in_progress": status_counts.get("APPLICATION_IN_PROGRESS", 0),
        "applications_submitted": status_counts.get("APPLICATION_SUBMITTED", 0),
        "document_review": status_counts.get("DOCUMENT_REVIEW", 0) + status_counts.get("DOCUMENT_PROCESSING", 0),
        "documents_verified": status_counts.get("DOCUMENTS_VERIFIED", 0),
        "admission_confirmed": status_counts.get("ADMISSION_CONFIRMED", 0) + status_counts.get("ACTIVE_STUDENT", 0),
    }


async def list_students_with_admissions(
    db: AsyncSession,
    status_filter: Optional[str] = None,
    branch_filter: Optional[str] = None,
    search: Optional[str] = None,
) -> List[Dict[str, Any]]:
    query = (
        select(Student, AdmissionApplication)
        .join(AdmissionApplication, Student.id == AdmissionApplication.student_id)
        .order_by(Student.tnea_application_number)
    )

    if status_filter:
        query = query.where(AdmissionApplication.status == status_filter)
    if branch_filter:
        query = query.where(Student.allotted_branch == branch_filter)
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            (Student.full_name.ilike(search_pattern)) |
            (Student.tnea_application_number.ilike(search_pattern)) |
            (Student.email.ilike(search_pattern))
        )

    result = await db.execute(query)
    rows = result.all()

    items = []
    for student, app in rows:
        items.append({
            "student_id": student.id,
            "admission_id": app.id,
            "full_name": student.full_name,
            "tnea_application_number": student.tnea_application_number,
            "allotted_branch": student.allotted_branch,
            "community": student.community,
            "status": app.status,
            "completion_percentage": app.completion_percentage,
            "updated_at": app.updated_at,
        })
    return items
