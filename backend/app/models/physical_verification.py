import uuid
from datetime import datetime, timezone, date
from enum import Enum
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    Column,
    String,
    DateTime,
    Date,
    Text,
    ForeignKey,
    JSON,
    Boolean,
    Index,
)
from sqlalchemy.orm import relationship

from app.database.base import Base


class AppointmentStatus(str, Enum):
    SCHEDULED = "SCHEDULED"
    CONFIRMED = "CONFIRMED"
    CHECKED_IN = "CHECKED_IN"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    MISSED = "MISSED"
    CANCELLED = "CANCELLED"
    RESCHEDULED = "RESCHEDULED"


class PhysicalSessionStatus(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    REOPENED = "REOPENED"


class PhysicalVerificationDecision(str, Enum):
    VERIFIED = "VERIFIED"
    PARTIALLY_VERIFIED = "PARTIALLY_VERIFIED"
    CORRECTION_REQUIRED = "CORRECTION_REQUIRED"
    REJECTED = "REJECTED"
    PENDING = "PENDING"


class PhysicalDocDecision(str, Enum):
    VERIFIED = "VERIFIED"
    NOT_VERIFIED = "NOT_VERIFIED"
    CORRECTION_REQUIRED = "CORRECTION_REQUIRED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    PENDING = "PENDING"


class PhysicalCorrectionReason(str, Enum):
    ORIGINAL_NOT_PRESENT = "ORIGINAL_NOT_PRESENT"
    ORIGINAL_ILLEGIBLE = "ORIGINAL_ILLEGIBLE"
    INFORMATION_MISMATCH = "INFORMATION_MISMATCH"
    WRONG_DOCUMENT = "WRONG_DOCUMENT"
    OUTDATED_DOCUMENT = "OUTDATED_DOCUMENT"
    MISSING_REQUIRED_DOCUMENT = "MISSING_REQUIRED_DOCUMENT"
    ADDITIONAL_DOCUMENT_REQUIRED = "ADDITIONAL_DOCUMENT_REQUIRED"
    OTHER = "OTHER"


class PhysicalVerificationAction(str, Enum):
    APPOINTMENT_CREATED = "APPOINTMENT_CREATED"
    APPOINTMENT_CONFIRMED = "APPOINTMENT_CONFIRMED"
    APPOINTMENT_RESCHEDULED = "APPOINTMENT_RESCHEDULED"
    APPOINTMENT_CANCELLED = "APPOINTMENT_CANCELLED"
    APPOINTMENT_REMINDER = "APPOINTMENT_REMINDER"
    STUDENT_CHECKED_IN = "STUDENT_CHECKED_IN"
    SESSION_STARTED = "SESSION_STARTED"
    DOCUMENT_INSPECTION_STARTED = "DOCUMENT_INSPECTION_STARTED"
    DOCUMENT_VERIFIED = "DOCUMENT_VERIFIED"
    DOCUMENT_NOT_VERIFIED = "DOCUMENT_NOT_VERIFIED"
    CORRECTION_REQUESTED = "CORRECTION_REQUESTED"
    SESSION_COMPLETED = "SESSION_COMPLETED"
    SESSION_REOPENED = "SESSION_REOPENED"


class PhysicalVerificationAppointment(Base):
    __tablename__ = "physical_verification_appointments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    application_id = Column(String(36), ForeignKey("admission_applications.id", ondelete="CASCADE"), nullable=False, index=True)
    appointment_date = Column(Date, nullable=False, index=True)
    start_time = Column(String(20), nullable=False)  # e.g., "09:30 AM"
    end_time = Column(String(20), nullable=False)    # e.g., "10:00 AM"
    token_number = Column(String(50), nullable=False, unique=True, index=True)
    checkin_token = Column(String(64), nullable=False, unique=True, index=True, default=lambda: uuid.uuid4().hex)
    location = Column(String(100), nullable=False, default="XYZ Main Campus — Central Admission Hall")
    counter_desk = Column(String(50), nullable=True, default="Verification Desk 1")
    appointment_status = Column(String(50), nullable=False, default=AppointmentStatus.SCHEDULED.value, index=True)
    notes = Column(Text, nullable=True)
    created_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    checked_in_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    application = relationship("AdmissionApplication", backref="physical_appointments")
    created_by = relationship("User", foreign_keys=[created_by_id])
    sessions = relationship("PhysicalVerificationSession", back_populates="appointment", cascade="all, delete-orphan")


class PhysicalVerificationSession(Base):
    __tablename__ = "physical_verification_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    application_id = Column(String(36), ForeignKey("admission_applications.id", ondelete="CASCADE"), nullable=False, index=True)
    appointment_id = Column(String(36), ForeignKey("physical_verification_appointments.id", ondelete="SET NULL"), nullable=True, index=True)
    officer_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    session_status = Column(String(50), nullable=False, default=PhysicalSessionStatus.NOT_STARTED.value, index=True)
    overall_decision = Column(String(50), nullable=False, default=PhysicalVerificationDecision.PENDING.value)
    officer_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    application = relationship("AdmissionApplication", backref="physical_sessions")
    appointment = relationship("PhysicalVerificationAppointment", back_populates="sessions")
    officer = relationship("User", foreign_keys=[officer_id])
    document_verifications = relationship("PhysicalDocumentVerification", back_populates="session", cascade="all, delete-orphan")


class PhysicalDocumentVerification(Base):
    __tablename__ = "physical_document_verifications"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("physical_verification_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    document_version_id = Column(String(36), ForeignKey("document_versions.id", ondelete="SET NULL"), nullable=True)
    document_type_id = Column(String(36), ForeignKey("document_types.id", ondelete="SET NULL"), nullable=True)
    officer_decision = Column(String(50), nullable=False, default=PhysicalDocDecision.PENDING.value)
    verification_notes = Column(Text, nullable=True)
    discrepancy_reason = Column(String(100), nullable=True)
    checklist_checks = Column(JSON, nullable=True, default=dict)
    verified_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    session = relationship("PhysicalVerificationSession", back_populates="document_verifications")
    document = relationship("Document")
    document_version = relationship("DocumentVersion")
    document_type = relationship("DocumentType")
    verified_by = relationship("User", foreign_keys=[verified_by_id])


class PhysicalVerificationAuditLog(Base):
    __tablename__ = "physical_verification_audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    application_id = Column(String(36), ForeignKey("admission_applications.id", ondelete="CASCADE"), nullable=False, index=True)
    appointment_id = Column(String(36), nullable=True, index=True)
    session_id = Column(String(36), nullable=True, index=True)
    actor_id = Column(String(36), nullable=True)
    actor_name = Column(String(100), nullable=True)
    actor_role = Column(String(50), nullable=True)
    action = Column(String(50), nullable=False, index=True)
    details = Column(JSON, nullable=True, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    application = relationship("AdmissionApplication", backref="physical_audit_logs")
