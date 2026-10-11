import uuid
from datetime import datetime, date, timezone
from sqlalchemy import String, Integer, Float, Date, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base


class TNEAAllotment(Base):
    __tablename__ = "tnea_allotments"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    student_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("students.id"), unique=True, nullable=True
    )
    tnea_application_number: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False
    )
    allotment_number: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False
    )
    college_code: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    college_name: Mapped[str] = mapped_column(String(200), nullable=False)
    branch_code: Mapped[str] = mapped_column(String(20), nullable=True)
    branch_name: Mapped[str] = mapped_column(String(100), nullable=False)
    community: Mapped[str] = mapped_column(String(20), nullable=True)
    quota: Mapped[str] = mapped_column(String(50), nullable=True)
    cutoff_mark: Mapped[float] = mapped_column(Float, nullable=True)
    allotment_date: Mapped[date] = mapped_column(Date, nullable=False)
    joining_deadline: Mapped[date] = mapped_column(Date, nullable=False)
    allotment_status: Mapped[str] = mapped_column(
        String(50), default="ALLOTTED", nullable=False
    )
    source: Mapped[str] = mapped_column(
        String(100), default="MOCK_TNEA_IMPORT", nullable=False
    )
    raw_data: Mapped[dict] = mapped_column(JSON, nullable=True, default=dict)
    
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    student = relationship("Student", back_populates="tnea_allotment", lazy="selectin")


class TNEAImportBatch(Base):
    __tablename__ = "tnea_import_batches"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    source: Mapped[str] = mapped_column(String(100), default="MOCK_TNEA", nullable=False)
    filename_or_reference: Mapped[str] = mapped_column(String(255), nullable=True)
    record_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    successful_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duplicate_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    imported_by: Mapped[str] = mapped_column(String(150), nullable=False)
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    status: Mapped[str] = mapped_column(
        String(50), default="STARTED", nullable=False
    )  # STARTED, COMPLETED, PARTIAL, FAILED
    errors_summary: Mapped[dict] = mapped_column(JSON, nullable=True, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
