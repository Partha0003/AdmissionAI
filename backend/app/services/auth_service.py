import hashlib
from datetime import datetime, timezone
from typing import Optional, Tuple, Dict, Any
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.models.role import Role
from app.models.student import Student
from app.models.institution import Institution
from app.models.activation_token import StudentActivationToken
from app.models.admission import AdmissionApplication
from app.core.security import verify_password, get_password_hash
from app.services.admission_service import transition_admission_state


async def get_user_by_identifier(db: AsyncSession, identifier: str) -> Optional[User]:
    cleaned = identifier.strip()
    # 1. Try matching user email (case-insensitive)
    query = (
        select(User)
        .where(func.lower(User.email) == cleaned.lower())
        .options(selectinload(User.role), selectinload(User.student))
    )
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    if user:
        return user

    # 2. Try matching TNEA application number from Student profile
    student_query = (
        select(Student)
        .where(func.lower(Student.tnea_application_number) == cleaned.lower())
        .options(selectinload(Student.user))
    )
    student_res = await db.execute(student_query)
    student = student_res.scalar_one_or_none()
    if student and student.user_id:
        return await get_user_by_id(db, student.user_id)

    return None


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    return await get_user_by_identifier(db, email)


async def get_user_by_id(db: AsyncSession, user_id: str) -> Optional[User]:
    query = select(User).where(User.id == user_id).options(selectinload(User.role), selectinload(User.student))
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def authenticate_user(
    db: AsyncSession, email: str, password: str
) -> Optional[User]:
    user = await get_user_by_identifier(db, email)
    if not user:
        return None
    if not user.is_active:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def get_student_by_user_id(db: AsyncSession, user_id: str) -> Optional[Student]:
    query = (
        select(Student)
        .where(Student.user_id == user_id)
        .options(
            selectinload(Student.institution),
            selectinload(Student.admission_application)
        )
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def activate_student_account(
    db: AsyncSession,
    raw_token: str,
    new_password: str
) -> Dict[str, Any]:
    """
    Validates a single-use activation token, sets the student password, marks account active,
    invalidates the token, and transitions state from ACTIVATION_PENDING to ACTIVATED.
    """
    token_cleaned = raw_token.strip()
    if not token_cleaned:
        raise ValueError("Activation token is required")

    t_hash = hashlib.sha256(token_cleaned.encode("utf-8")).hexdigest()

    token_query = (
        select(StudentActivationToken)
        .where(StudentActivationToken.token_hash == t_hash)
        .options(selectinload(StudentActivationToken.student))
    )
    res = await db.execute(token_query)
    token_record = res.scalar_one_or_none()

    if not token_record:
        raise ValueError("Invalid activation token.")

    if token_record.is_used:
        raise ValueError("This activation token has already been used.")

    now_utc = datetime.now(timezone.utc)
    expires_at = (
        token_record.expires_at.replace(tzinfo=timezone.utc)
        if token_record.expires_at.tzinfo is None
        else token_record.expires_at
    )
    if expires_at < now_utc:
        raise ValueError("This activation token has expired. Please contact the admission office.")

    student = token_record.student
    if not student:
        raise ValueError("Associated student record not found.")

    # Fetch User
    user_query = select(User).where(User.id == student.user_id)
    user_res = await db.execute(user_query)
    user = user_res.scalar_one_or_none()
    if not user:
        raise ValueError("Associated user account not found.")

    # 1. Update user password and activate
    user.hashed_password = get_password_hash(new_password)
    user.is_active = True

    # 2. Mark token used
    token_record.is_used = True
    token_record.used_at = now_utc

    # 3. Transition Admission State
    app_query = select(AdmissionApplication).where(AdmissionApplication.student_id == student.id)
    app_res = await db.execute(app_query)
    app = app_res.scalar_one_or_none()

    if app:
        await transition_admission_state(
            db=db,
            admission_id=app.id,
            requested_state_str="ACTIVATED",
            actor_email=student.email,
            actor_role_str="STUDENT",
            reason="Candidate successfully completed secure account activation with one-time token.",
            metadata_info={"activation_timestamp": now_utc.isoformat()}
        )
    else:
        student.status = "ACTIVATED"
        await db.commit()

    return {
        "success": True,
        "message": "Account successfully activated. You can now sign in using your credentials.",
        "student_id": student.id,
        "student_name": student.full_name,
        "tnea_application_number": student.tnea_application_number,
        "email": student.email,
        "new_status": "ACTIVATED",
    }
