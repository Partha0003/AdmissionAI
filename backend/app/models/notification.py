from datetime import datetime, timezone
import enum
import uuid
from sqlalchemy import (
    Column,
    String,
    DateTime,
    ForeignKey,
    Text,
    JSON,
    Index,
)
from sqlalchemy.orm import relationship
from app.database.base import Base


def utc_now():
    return datetime.now(timezone.utc)


def generate_uuid():
    return str(uuid.uuid4())


class NotificationType(str, enum.Enum):
    ALLOTMENT_RECEIVED = "ALLOTMENT_RECEIVED"
    ACTIVATION_REQUIRED = "ACTIVATION_REQUIRED"
    APPLICATION_SUBMITTED = "APPLICATION_SUBMITTED"
    DOCUMENT_CORRECTION_REQUIRED = "DOCUMENT_CORRECTION_REQUIRED"
    DOCUMENT_REVIEW_COMPLETED = "DOCUMENT_REVIEW_COMPLETED"
    PHYSICAL_APPOINTMENT_CREATED = "PHYSICAL_APPOINTMENT_CREATED"
    PHYSICAL_APPOINTMENT_REMINDER = "PHYSICAL_APPOINTMENT_REMINDER"
    PHYSICAL_CORRECTION_REQUIRED = "PHYSICAL_CORRECTION_REQUIRED"
    PAYMENT_REQUIRED = "PAYMENT_REQUIRED"
    PAYMENT_SUBMITTED = "PAYMENT_SUBMITTED"
    PAYMENT_CORRECTION_REQUIRED = "PAYMENT_CORRECTION_REQUIRED"
    PAYMENT_VERIFIED = "PAYMENT_VERIFIED"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    ERP_STAGED = "ERP_STAGED"
    ERP_SYNC_FAILED = "ERP_SYNC_FAILED"
    ERP_SYNCED = "ERP_SYNCED"


class NotificationSeverity(str, enum.Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"


class NotificationChannel(str, enum.Enum):
    IN_APP = "IN_APP"
    EMAIL_MOCK = "EMAIL_MOCK"
    SMS_MOCK = "SMS_MOCK"


class NotificationStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    SENT = "SENT"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    READ = "READ"


class Notification(Base):
    """
    Centralized communication record.
    Strictly informative; notifications never drive or mutate business lifecycle state.
    """
    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    application_id = Column(String(36), ForeignKey("admission_applications.id", ondelete="SET NULL"), nullable=True)
    
    type = Column(String(64), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    severity = Column(String(20), nullable=False, default=NotificationSeverity.INFO.value)
    channel = Column(String(20), nullable=False, default=NotificationChannel.IN_APP.value)
    status = Column(String(20), nullable=False, default=NotificationStatus.DELIVERED.value)
    
    read_at = Column(DateTime(timezone=True), nullable=True)
    metadata_json = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    user = relationship("User", backref="notifications", lazy="selectin")
    application = relationship("AdmissionApplication", lazy="selectin")

    __table_args__ = (
        Index("ix_notifications_user_id", "user_id"),
        Index("ix_notifications_status", "status"),
        Index("ix_notifications_created_at", "created_at"),
    )
