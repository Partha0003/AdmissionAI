import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Boolean, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base


class ReviewStatus(str, enum.Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_REVIEW = "IN_REVIEW"
    CORRECTION_REQUIRED = "CORRECTION_REQUIRED"
    RESUBMISSION_PENDING = "RESUBMISSION_PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class ReviewDecision(str, enum.Enum):
    VERIFIED = "VERIFIED"
    CORRECTION_REQUIRED = "CORRECTION_REQUIRED"
    REJECTED = "REJECTED"


class FieldReviewDecision(str, enum.Enum):
    CONFIRMED = "CONFIRMED"
    REQUIRES_CORRECTION = "REQUIRES_CORRECTION"
    ACCEPTED_WITH_REVIEW = "ACCEPTED_WITH_REVIEW"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class CorrectionReason(str, enum.Enum):
    MISSING_DOCUMENT = "MISSING_DOCUMENT"
    ILLEGIBLE_DOCUMENT = "ILLEGIBLE_DOCUMENT"
    FIELD_MISMATCH = "FIELD_MISMATCH"
    INCORRECT_INFORMATION = "INCORRECT_INFORMATION"
    WRONG_DOCUMENT_TYPE = "WRONG_DOCUMENT_TYPE"
    EXPIRED_OR_OUTDATED_DOCUMENT = "EXPIRED_OR_OUTDATED_DOCUMENT"
    ADDITIONAL_INFORMATION_REQUIRED = "ADDITIONAL_INFORMATION_REQUIRED"
    OTHER = "OTHER"


class ScrutinyAction(str, enum.Enum):
    REVIEW_STARTED = "REVIEW_STARTED"
    DOCUMENT_REVIEWED = "DOCUMENT_REVIEWED"
    FIELD_CONFIRMED = "FIELD_CONFIRMED"
    FIELD_FLAGGED = "FIELD_FLAGGED"
    CORRECTION_REQUESTED = "CORRECTION_REQUESTED"
    RESUBMISSION_RECEIVED = "RESUBMISSION_RECEIVED"
    REVIEW_COMPLETED = "REVIEW_COMPLETED"
    REVIEW_REOPENED = "REVIEW_REOPENED"


class AdmissionReview(Base):
    __tablename__ = "admission_reviews"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    application_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("admission_applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reviewer_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(
        String(50), default=ReviewStatus.NOT_STARTED.value, nullable=False, index=True
    )
    decision: Mapped[str] = mapped_column(String(50), nullable=True)
    overall_comments: Mapped[str] = mapped_column(Text, nullable=True)
    correction_reason: Mapped[str] = mapped_column(String(100), nullable=True)
    correction_instructions: Mapped[str] = mapped_column(Text, nullable=True)
    
    # Snapshot of document versions and reconciliation analyzed at review time
    reviewed_document_versions: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    reviewed_reconciliation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("cross_document_reconciliations.id", ondelete="SET NULL"), nullable=True
    )

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    application = relationship("AdmissionApplication", lazy="selectin")
    reviewer = relationship("User", foreign_keys=[reviewer_id], lazy="selectin")
    reconciliation = relationship("CrossDocumentReconciliation", foreign_keys=[reviewed_reconciliation_id], lazy="selectin")
    document_reviews = relationship(
        "DocumentReviewItem",
        back_populates="review",
        cascade="all, delete-orphan",
        order_by="DocumentReviewItem.reviewed_at.desc()",
        lazy="selectin"
    )
    field_reviews = relationship(
        "FieldReviewItem",
        back_populates="review",
        cascade="all, delete-orphan",
        order_by="FieldReviewItem.reviewed_at.desc()",
        lazy="selectin"
    )
    audit_logs = relationship(
        "ScrutinyAuditLog",
        back_populates="review",
        cascade="all, delete-orphan",
        order_by="ScrutinyAuditLog.created_at.desc()",
        lazy="selectin"
    )


class DocumentReviewItem(Base):
    __tablename__ = "document_review_items"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    review_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("admission_reviews.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("document_versions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(
        String(50), default="PENDING", nullable=False
    )  # PENDING, CONFIRMED, CORRECTION_REQUIRED, REJECTED
    correction_reason: Mapped[str] = mapped_column(String(100), nullable=True)
    reviewer_comments: Mapped[str] = mapped_column(Text, nullable=True)
    reviewed_by_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    review = relationship("AdmissionReview", back_populates="document_reviews", lazy="selectin")
    document = relationship("Document", lazy="selectin")
    document_version = relationship("DocumentVersion", lazy="selectin")
    reviewed_by = relationship("User", lazy="selectin")


class FieldReviewItem(Base):
    __tablename__ = "field_review_items"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    review_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("admission_reviews.id", ondelete="CASCADE"), nullable=False, index=True
    )
    field_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    declared_value: Mapped[str] = mapped_column(String(255), nullable=True)
    extracted_value: Mapped[str] = mapped_column(String(255), nullable=True)
    reconciliation_status: Mapped[str] = mapped_column(String(50), nullable=True)
    decision: Mapped[str] = mapped_column(
        String(50), default=FieldReviewDecision.CONFIRMED.value, nullable=False
    )
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    document_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("document_versions.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_by_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    review = relationship("AdmissionReview", back_populates="field_reviews", lazy="selectin")
    document = relationship("Document", lazy="selectin")
    document_version = relationship("DocumentVersion", lazy="selectin")
    reviewed_by = relationship("User", lazy="selectin")


class ScrutinyAuditLog(Base):
    __tablename__ = "scrutiny_audit_logs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    review_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("admission_reviews.id", ondelete="SET NULL"), nullable=True, index=True
    )
    application_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("admission_applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    user_name: Mapped[str] = mapped_column(String(150), nullable=True)
    user_role: Mapped[str] = mapped_column(String(50), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    previous_status: Mapped[str] = mapped_column(String(50), nullable=True)
    new_status: Mapped[str] = mapped_column(String(50), nullable=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )

    # Relationships
    review = relationship("AdmissionReview", back_populates="audit_logs", lazy="selectin")
    user = relationship("User", lazy="selectin")
