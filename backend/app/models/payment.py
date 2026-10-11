from datetime import datetime, timezone
import enum
import uuid
from sqlalchemy import (
    Column,
    String,
    DateTime,
    ForeignKey,
    Numeric,
    Text,
    Boolean,
    Enum,
    JSON,
    Index,
)
from sqlalchemy.orm import relationship
from app.database.base import Base


def utc_now():
    return datetime.now(timezone.utc)


def generate_uuid():
    return str(uuid.uuid4())


class PaymentMethod(str, enum.Enum):
    DEMO_ONLINE_PAYMENT = "DEMO_ONLINE_PAYMENT"
    DEMAND_DRAFT = "DEMAND_DRAFT"


class PaymentStatus(str, enum.Enum):
    INITIATED = "INITIATED"
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    CORRECTION_REQUIRED = "CORRECTION_REQUIRED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class PaymentCorrectionReason(str, enum.Enum):
    INVALID_DD_DETAILS = "INVALID_DD_DETAILS"
    AMOUNT_MISMATCH = "AMOUNT_MISMATCH"
    MISSING_SUPPORTING_DOCUMENT = "MISSING_SUPPORTING_DOCUMENT"
    ILLEGIBLE_DOCUMENT = "ILLEGIBLE_DOCUMENT"
    OUTDATED_DOCUMENT = "OUTDATED_DOCUMENT"
    INCORRECT_REFERENCE = "INCORRECT_REFERENCE"
    DUPLICATE_PAYMENT_REFERENCE = "DUPLICATE_PAYMENT_REFERENCE"
    OTHER = "OTHER"


class PaymentAuditAction(str, enum.Enum):
    PAYMENT_INITIATED = "PAYMENT_INITIATED"
    PAYMENT_SUBMITTED = "PAYMENT_SUBMITTED"
    DD_SUBMITTED = "DD_SUBMITTED"
    PAYMENT_REVIEW_STARTED = "PAYMENT_REVIEW_STARTED"
    PAYMENT_VERIFIED = "PAYMENT_VERIFIED"
    PAYMENT_REJECTED = "PAYMENT_REJECTED"
    PAYMENT_CORRECTION_REQUESTED = "PAYMENT_CORRECTION_REQUESTED"
    PAYMENT_CORRECTION_RECEIVED = "PAYMENT_CORRECTION_RECEIVED"
    PAYMENT_FAILED = "PAYMENT_FAILED"


class FeeRequirement(Base):
    """
    Authoritative server-side fee requirement configuration for XYZ Engineering College.
    Prevents client-side arbitrary fee submission tampering.
    """
    __tablename__ = "fee_requirements"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    academic_year = Column(String(20), nullable=False, default="2026-27")
    category = Column(String(50), nullable=False, default="GENERAL")
    quota = Column(String(50), nullable=False, default="GOVERNMENT")
    amount = Column(Numeric(10, 2), nullable=False, default=50000.00)
    currency = Column(String(10), nullable=False, default="INR")
    description = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class PaymentTransaction(Base):
    """
    Represents an admission fee payment transaction.
    Independent domain record that does not mutate admission/document status.
    """
    __tablename__ = "payment_transactions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    application_id = Column(String(36), ForeignKey("admission_applications.id", ondelete="CASCADE"), nullable=False)
    payment_reference = Column(String(64), unique=True, nullable=False)
    payment_method = Column(String(50), nullable=False, default=PaymentMethod.DEMAND_DRAFT.value)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(10), nullable=False, default="INR")
    status = Column(String(50), nullable=False, default=PaymentStatus.INITIATED.value)
    
    initiated_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    verified_by_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    
    rejection_reason = Column(String(64), nullable=True)
    notes = Column(Text, nullable=True)
    fee_requirement_id = Column(String(36), ForeignKey("fee_requirements.id"), nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    application = relationship("AdmissionApplication", backref="payments", lazy="selectin")
    verified_by = relationship("User", foreign_keys=[verified_by_id], lazy="selectin")
    fee_requirement = relationship("FeeRequirement", lazy="selectin")
    dd_submission = relationship("DemandDraftSubmission", back_populates="payment", uselist=False, cascade="all, delete-orphan", lazy="selectin")
    audit_logs = relationship("PaymentAuditLog", back_populates="payment", cascade="all, delete-orphan", lazy="selectin")

    __table_args__ = (
        Index("ix_payment_transactions_app_id", "application_id"),
        Index("ix_payment_transactions_status", "status"),
        Index("ix_payment_transactions_ref", "payment_reference"),
    )


class DemandDraftSubmission(Base):
    """
    Stores Demand Draft details and pins the exact document version inspected by Finance.
    """
    __tablename__ = "demand_draft_submissions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    payment_id = Column(String(36), ForeignKey("payment_transactions.id", ondelete="CASCADE"), unique=True, nullable=False)
    dd_number = Column(String(64), nullable=False)
    dd_date = Column(String(20), nullable=False)
    bank_name = Column(String(128), nullable=False)
    branch_name = Column(String(128), nullable=True)
    amount = Column(Numeric(10, 2), nullable=False)
    
    # Version pinning: exact document and document version reviewed
    supporting_document_id = Column(String(36), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    supporting_document_version_id = Column(String(36), ForeignKey("document_versions.id", ondelete="SET NULL"), nullable=True)
    
    submitted_by_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    submitted_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    
    finance_verified_by_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    finance_verified_at = Column(DateTime(timezone=True), nullable=True)
    finance_notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    payment = relationship("PaymentTransaction", back_populates="dd_submission", lazy="selectin")
    supporting_document = relationship("Document", foreign_keys=[supporting_document_id], lazy="selectin")
    supporting_document_version = relationship("DocumentVersion", foreign_keys=[supporting_document_version_id], lazy="selectin")
    submitted_by = relationship("User", foreign_keys=[submitted_by_id], lazy="selectin")
    finance_verified_by = relationship("User", foreign_keys=[finance_verified_by_id], lazy="selectin")

    __table_args__ = (
        Index("ix_dd_submissions_payment_id", "payment_id"),
        Index("ix_dd_submissions_dd_number", "dd_number"),
        Index("ix_dd_submissions_bank_name", "bank_name"),
    )


class PaymentAuditLog(Base):
    """
    Append-only audit trail for finance and payment operations.
    """
    __tablename__ = "payment_audit_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    application_id = Column(String(36), ForeignKey("admission_applications.id", ondelete="CASCADE"), nullable=False)
    payment_id = Column(String(36), ForeignKey("payment_transactions.id", ondelete="CASCADE"), nullable=False)
    actor_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    actor_name = Column(String(128), nullable=True)
    actor_role = Column(String(50), nullable=False, default="FINANCE_OFFICER")
    action = Column(String(64), nullable=False)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    payment = relationship("PaymentTransaction", back_populates="audit_logs", lazy="selectin")
    application = relationship("AdmissionApplication", lazy="selectin")
    actor = relationship("User", lazy="selectin")

    __table_args__ = (
        Index("ix_payment_audit_app_id", "application_id"),
        Index("ix_payment_audit_pay_id", "payment_id"),
        Index("ix_payment_audit_action", "action"),
        Index("ix_payment_audit_created_at", "created_at"),
    )
