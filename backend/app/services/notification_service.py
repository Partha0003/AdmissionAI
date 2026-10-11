import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, update
from fastapi import HTTPException, status

from app.models.user import User
from app.models.notification import (
    Notification,
    NotificationType,
    NotificationSeverity,
    NotificationChannel,
    NotificationStatus,
)
from app.adapters.notification_adapter import mock_notification_service


class NotificationService:
    @classmethod
    async def send_notification(
        cls,
        db: AsyncSession,
        user_id: str,
        notification_type: str,
        title: str,
        message: str,
        application_id: Optional[str] = None,
        severity: str = NotificationSeverity.INFO.value,
        channel: str = NotificationChannel.IN_APP.value,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Notification:
        """
        Creates an in-app notification record and simulates mock channel delivery.
        """
        stmt_user = select(User).where(User.id == user_id)
        res_user = await db.execute(stmt_user)
        user = res_user.scalar_one_or_none()
        target = user.email if user else "student@demo.local"

        # Dispatch through mock communication adapter
        mock_notification_service.dispatch_alert(
            channel=channel,
            recipient_target=target,
            title=title,
            message=message,
            notification_type=notification_type,
        )

        notification = Notification(
            id=str(uuid.uuid4()),
            user_id=user_id,
            application_id=application_id,
            type=notification_type,
            title=title,
            message=message,
            severity=severity,
            channel=channel,
            status=NotificationStatus.DELIVERED.value,
            metadata_json=metadata,
            created_at=datetime.now(timezone.utc),
        )
        db.add(notification)
        await db.commit()
        await db.refresh(notification)
        return notification

    @classmethod
    async def get_user_notifications(
        cls, db: AsyncSession, user: User, limit: int = 50
    ) -> Dict[str, Any]:
        """
        Fetches notifications for the authenticated user only.
        """
        stmt = (
            select(Notification)
            .where(Notification.user_id == user.id)
            .order_by(desc(Notification.created_at))
            .limit(limit)
        )
        res = await db.execute(stmt)
        notifications = res.scalars().all()
        
        stmt_unread = (
            select(func.count(Notification.id))
            .where(
                Notification.user_id == user.id,
                Notification.status != NotificationStatus.READ.value,
                Notification.read_at == None,
            )
        )
        res_unread = await db.execute(stmt_unread)
        unread_count = res_unread.scalar() or 0

        return {
            "unread_count": unread_count,
            "total_count": len(notifications),
            "notifications": notifications,
        }

    @classmethod
    async def mark_as_read(cls, db: AsyncSession, user: User, notification_id: str) -> Notification:
        """
        Marks a specific notification as read. Enforces Anti-IDOR ownership.
        """
        stmt = select(Notification).where(Notification.id == notification_id)
        res = await db.execute(stmt)
        notification = res.scalar_one_or_none()
        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found.",
            )

        if notification.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Cannot modify another user's notification.",
            )

        notification.status = NotificationStatus.READ.value
        notification.read_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(notification)
        return notification

    @classmethod
    async def mark_all_as_read(cls, db: AsyncSession, user: User) -> int:
        """
        Marks all notifications as read for the authenticated user.
        """
        now = datetime.now(timezone.utc)
        stmt = (
            update(Notification)
            .where(
                Notification.user_id == user.id,
                Notification.read_at == None,
            )
            .values(
                status=NotificationStatus.READ.value,
                read_at=now,
            )
        )
        res = await db.execute(stmt)
        await db.commit()
        return res.rowcount
