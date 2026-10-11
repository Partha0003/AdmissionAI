from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.schemas.auth import LoginRequest, Token
from app.schemas.user import UserMeResponse
from app.schemas.activation import StudentActivationRequest, StudentActivationResponse
from app.models.user import User
from app.services.auth_service import (
    authenticate_user,
    get_student_by_user_id,
    activate_student_account,
)
from app.core.security import create_access_token
from app.core.config import settings
from app.api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/activate", response_model=StudentActivationResponse)
async def activate_account(
    data: StudentActivationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Public student account activation endpoint.
    Validates the one-time activation token, sets candidate password, and transitions status to ACTIVATED.
    """
    try:
        result = await activate_student_account(
            db=db,
            raw_token=data.activation_token,
            new_password=data.password,
        )
        return StudentActivationResponse(**result)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/login", response_model=Token)
async def login(
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticates a user with email and password, returning a signed JWT access token and user role.
    """
    user = await authenticate_user(db, email=login_data.email, password=login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    role_name = user.role.name if user.role else "STUDENT"
    access_token = create_access_token(
        subject=user.id,
        role=role_name,
        claims={"email": user.email}
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        role=role_name,
        user_id=user.id,
        email=user.email
    )


@router.get("/me", response_model=UserMeResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieves information about the currently authenticated user including active institution metadata.
    """
    student_id = None
    if current_user.role and current_user.role.name == "STUDENT":
        student = await get_student_by_user_id(db, current_user.id)
        if student:
            student_id = student.id

    return UserMeResponse(
        id=current_user.id,
        email=current_user.email,
        role=current_user.role.name if current_user.role else "STUDENT",
        is_active=current_user.is_active,
        student_id=student_id,
        institution_name=settings.INSTITUTION_NAME,
        institution_code=settings.INSTITUTION_CODE,
        academic_year=settings.ACADEMIC_YEAR
    )
