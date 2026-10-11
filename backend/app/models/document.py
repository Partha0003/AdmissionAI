import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Boolean, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base


class DocumentType(Base):
    __tablename__ = "document_types"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    code: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(
        String(50), default="ACADEMIC", nullable=False
    )  # ACADEMIC, ALLOTMENT, IDENTITY_CATEGORY, FINANCIAL, OTHER
    allowed_extensions: Mapped[list] = mapped_column(
        JSON, default=lambda: ["pdf", "png", "jpg", "jpeg"], nullable=False
    )
    max_size_mb: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    rules = relationship(
        "DocumentRule", back_populates="document_type", cascade="all, delete-orphan", lazy="selectin"
    )
    documents = relationship(
        "Document", back_populates="document_type", lazy="selectin"
    )

    @property
    def max_file_size_mb(self) -> int:
        return self.max_size_mb

    @property
    def display_order(self) -> int:
        return self.sort_order

    @property
    def is_mandatory_default(self) -> bool:
        return False


class DocumentRule(Base):
    __tablename__ = "document_rules"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    document_type_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("document_types.id"), nullable=False, index=True
    )
    required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # JSON condition criteria: e.g. {"community": ["BC", "MBC", "SC", "ST"]}, {"quota": ["FIRST_GRADUATE"]}, {"always": true}
    applicable_conditions: Mapped[dict] = mapped_column(
        JSON, default=dict, nullable=False
    )
    priority: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    academic_year: Mapped[str] = mapped_column(String(20), default="2026-27", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    document_type = relationship("DocumentType", back_populates="rules", lazy="selectin")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    application_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("admission_applications.id"), nullable=False, index=True
    )
    document_type_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("document_types.id"), nullable=False, index=True
    )
    current_version_id: Mapped[str] = mapped_column(
        String(36), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(50), default="UPLOADED", nullable=False
    )  # NOT_UPLOADED, UPLOADED, CORRECTION_REQUIRED, RESUBMISSION_REQUIRED

    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    application = relationship("AdmissionApplication", back_populates="documents", lazy="selectin")
    document_type = relationship("DocumentType", back_populates="documents", lazy="selectin")
    versions = relationship(
        "DocumentVersion",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentVersion.version_number.desc()",
        lazy="selectin"
    )
    processing_jobs = relationship(
        "DocumentProcessingJob",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentProcessingJob.created_at.desc()",
        lazy="selectin"
    )


class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)  # in bytes
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # SHA-256
    uploaded_by: Mapped[str] = mapped_column(String(150), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    document = relationship("Document", back_populates="versions", lazy="selectin")

    @property
    def file_size_bytes(self) -> int:
        return self.file_size

    @property
    def file_hash_sha256(self) -> str:
        return self.file_hash
