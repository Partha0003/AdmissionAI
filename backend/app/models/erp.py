from datetime import datetime, timezone
import enum
import uuid
from sqlalchemy import (
    Column,
    String,
    DateTime,
    ForeignKey,
    Integer,
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


class ERPRecordStatus(str, enum.Enum):
    NOT_READY = "NOT_READY"
    READY_FOR_STAGING = "READY_FOR_STAGING"
    STAGED = "STAGED"
    SYNC_PENDING = "SYNC_PENDING"
    SYNCING = "SYNCING"
    SYNCED = "SYNCED"
    SYNC_FAILED = "SYNC_FAILED"
    RETRY_PENDING = "RETRY_PENDING"
    CANCELLED = "CANCELLED"


class ERPIntegrationStatus(str, enum.Enum):
    INITIATED = "INITIATED"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    RETRY = "RETRY"


class ERPAdmissionRecord(Base):
    """
    Represents an ERP-ready staging admission record for mock enterprise synchronization.
    Strictly isolated from business lifecycle states; sync failures never mutate admission status.
    """
    __tablename__ = "erp_admission_records"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    application_id = Column(String(36), ForeignKey("admission_applications.id", ondelete="CASCADE"), unique=True, nullable=False)
    staging_reference = Column(String(64), unique=True, nullable=False)
    
    payload = Column(JSON, nullable=False)
    payload_hash = Column(String(64), nullable=False)
    payload_version = Column(Integer, default=1, nullable=False)
    
    status = Column(String(50), nullable=False, default=ERPRecordStatus.READY_FOR_STAGING.value)
    validation_errors = Column(JSON, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    last_error = Column(Text, nullable=True)
    
    staged_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    synced_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    application = relationship("AdmissionApplication", backref="erp_record", lazy="selectin")
    integration_events = relationship("ERPIntegrationEvent", back_populates="erp_record", cascade="all, delete-orphan", lazy="selectin")

    __table_args__ = (
        Index("ix_erp_records_app_id", "application_id"),
        Index("ix_erp_records_staging_ref", "staging_reference"),
        Index("ix_erp_records_status", "status"),
    )


class ERPIntegrationEvent(Base):
    """
    Append-only audit log of sync attempts, responses, and errors from the Mock ERP adapter.
    """
    __tablename__ = "erp_integration_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    erp_record_id = Column(String(36), ForeignKey("erp_admission_records.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String(64), nullable=False)
    adapter_name = Column(String(64), nullable=False, default="MockERPAdapter")
    
    request_reference = Column(String(64), nullable=True)
    response_reference = Column(String(64), nullable=True)
    status = Column(String(50), nullable=False)
    error_summary = Column(Text, nullable=True)
    details = Column(JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    erp_record = relationship("ERPAdmissionRecord", back_populates="integration_events", lazy="selectin")

    __table_args__ = (
        Index("ix_erp_events_record_id", "erp_record_id"),
        Index("ix_erp_events_event_type", "event_type"),
        Index("ix_erp_events_created_at", "created_at"),
    )
