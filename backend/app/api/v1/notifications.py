from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.notification import (
    NotificationResponse,
    NotificationSummaryResponse,
)
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Phase 8 - Centralized Notifications"])


@router.get("/me", response_model=NotificationSummaryResponse)
async def get_my_notifications(
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns unread count and notification feed for the authenticated user.
    """
    return await NotificationService.get_user_notifications(db, current_user, limit=limit)


@router.post("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_as_read(
    notification_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Marks an in-app notification as read.
    """
    return await NotificationService.mark_as_read(db, current_user, notification_id)


@router.post("/read-all", response_model=dict)
async def mark_all_notifications_as_read(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Marks all notifications as read for the authenticated user.
    """
    count = await NotificationService.mark_all_as_read(db, current_user)
    return {"message": f"{count} notifications marked as read."}
