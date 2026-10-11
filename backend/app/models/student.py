import uuid
from datetime import datetime, date, timezone
from sqlalchemy import String, Date, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base


class Student(Base):
    __tablename__ = "students"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), unique=True, nullable=False
    )
    institution_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("institutions.id"), nullable=False
    )
    tnea_application_number: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False
    )
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    email: Mapped[str] = mapped_column(String(150), index=True, nullable=False)
    mobile: Mapped[str] = mapped_column(String(20), nullable=False)
    community: Mapped[str] = mapped_column(String(20), nullable=True)
    allotted_branch: Mapped[str] = mapped_column(String(100), nullable=True)
    quota: Mapped[str] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="ACTIVATION_PENDING", nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    user = relationship("User", back_populates="student", lazy="selectin")
    institution = relationship("Institution", back_populates="students", lazy="selectin")
    admission_application = relationship(
        "AdmissionApplication", back_populates="student", uselist=False, cascade="all, delete-orphan", lazy="selectin"
    )
    tnea_allotment = relationship(
        "TNEAAllotment", back_populates="student", uselist=False, cascade="all, delete-orphan", lazy="selectin"
    )
    activation_token = relationship(
        "StudentActivationToken", back_populates="student", uselist=False, cascade="all, delete-orphan", lazy="selectin"
    )
