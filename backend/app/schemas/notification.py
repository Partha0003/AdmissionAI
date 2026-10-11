from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel


class NotificationResponse(BaseModel):
    id: str
    user_id: str
    application_id: Optional[str] = None
    type: str
    title: str
    message: str
    severity: str
    channel: str
    status: str
    read_at: Optional[datetime] = None
    metadata_json: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationSummaryResponse(BaseModel):
    unread_count: int
    total_count: int
    notifications: List[NotificationResponse]
