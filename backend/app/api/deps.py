from typing import List, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.core.security import decode_access_token
from app.models.user import User
from app.models.student import Student
from app.services.auth_service import get_user_by_id, get_student_by_user_id

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials or token expired",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    user_id: Optional[str] = payload.get("sub")
    if user_id is None:
        raise credentials_exception
        
    user = await get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        raise credentials_exception
    return user


def require_roles(allowed_roles: List[str]):
    """RBAC Dependency: Ensures the authenticated user has one of the allowed roles."""
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        user_role = current_user.role.name if current_user.role else ""
        if user_role not in allowed_roles and user_role != "SUPER_ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: requires one of roles {allowed_roles}, your role is '{user_role}'"
            )
        return current_user
    return role_checker


async def get_current_student(
    current_user: User = Depends(require_roles(["STUDENT"])),
    db: AsyncSession = Depends(get_db)
) -> Student:
    """Retrieves the Student record linked to the authenticated STUDENT user."""
    student = await get_student_by_user_id(db, current_user.id)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student profile not found for this account"
        )
    return student
