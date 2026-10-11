import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Float, Boolean, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base


class AdmissionApplication(Base):
    __tablename__ = "admission_applications"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    student_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("students.id"), unique=True, nullable=False
    )
    application_number: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(50), default="ALLOTTED", index=True, nullable=False
    )
    completion_percentage: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # 1. Personal & Identity Details
    gender: Mapped[str] = mapped_column(String(20), nullable=True)
    blood_group: Mapped[str] = mapped_column(String(10), nullable=True)
    nationality: Mapped[str] = mapped_column(String(50), default="Indian", nullable=True)
    religion: Mapped[str] = mapped_column(String(50), nullable=True)
    caste: Mapped[str] = mapped_column(String(100), nullable=True)
    mother_tongue: Mapped[str] = mapped_column(String(50), default="Tamil", nullable=True)
    aadhaar_number: Mapped[str] = mapped_column(String(20), nullable=True)

    # 2. Contact & Address
    address_line1: Mapped[str] = mapped_column(String(255), nullable=True)
    address_line2: Mapped[str] = mapped_column(String(255), nullable=True)
    city: Mapped[str] = mapped_column(String(100), nullable=True)
    district: Mapped[str] = mapped_column(String(100), nullable=True)
    state: Mapped[str] = mapped_column(String(100), default="Tamil Nadu", nullable=True)
    pincode: Mapped[str] = mapped_column(String(20), nullable=True)
    emergency_contact_name: Mapped[str] = mapped_column(String(150), nullable=True)
    emergency_contact_phone: Mapped[str] = mapped_column(String(20), nullable=True)
    emergency_contact_relation: Mapped[str] = mapped_column(String(50), nullable=True)

    # 3. Parents / Guardian Details
    father_name: Mapped[str] = mapped_column(String(150), nullable=True)
    father_occupation: Mapped[str] = mapped_column(String(100), nullable=True)
    father_mobile: Mapped[str] = mapped_column(String(20), nullable=True)
    father_email: Mapped[str] = mapped_column(String(150), nullable=True)
    mother_name: Mapped[str] = mapped_column(String(150), nullable=True)
    mother_occupation: Mapped[str] = mapped_column(String(100), nullable=True)
    mother_mobile: Mapped[str] = mapped_column(String(20), nullable=True)
    mother_email: Mapped[str] = mapped_column(String(150), nullable=True)
    guardian_name: Mapped[str] = mapped_column(String(150), nullable=True)
    guardian_occupation: Mapped[str] = mapped_column(String(100), nullable=True)
    guardian_mobile: Mapped[str] = mapped_column(String(20), nullable=True)
    guardian_relation: Mapped[str] = mapped_column(String(50), nullable=True)
    annual_family_income: Mapped[float] = mapped_column(Float, nullable=True)

    # 4. Academic Marks - 10th
    tenth_school_name: Mapped[str] = mapped_column(String(200), nullable=True)
    tenth_board: Mapped[str] = mapped_column(String(100), nullable=True)
    tenth_year_of_passing: Mapped[int] = mapped_column(Integer, nullable=True)
    tenth_registration_number: Mapped[str] = mapped_column(String(50), nullable=True)
    tenth_total_marks: Mapped[float] = mapped_column(Float, nullable=True)
    tenth_max_marks: Mapped[float] = mapped_column(Float, default=500.0, nullable=True)
    tenth_percentage: Mapped[float] = mapped_column(Float, nullable=True)

    # 5. Academic Marks - 12th
    twelfth_school_name: Mapped[str] = mapped_column(String(200), nullable=True)
    twelfth_board: Mapped[str] = mapped_column(String(100), nullable=True)
    twelfth_year_of_passing: Mapped[int] = mapped_column(Integer, nullable=True)
    twelfth_registration_number: Mapped[str] = mapped_column(String(50), nullable=True)
    twelfth_total_marks: Mapped[float] = mapped_column(Float, nullable=True)
    twelfth_max_marks: Mapped[float] = mapped_column(Float, default=600.0, nullable=True)
    twelfth_percentage: Mapped[float] = mapped_column(Float, nullable=True)
    twelfth_maths_marks: Mapped[float] = mapped_column(Float, nullable=True)
    twelfth_physics_marks: Mapped[float] = mapped_column(Float, nullable=True)
    twelfth_chemistry_marks: Mapped[float] = mapped_column(Float, nullable=True)
    twelfth_cutoff_marks: Mapped[float] = mapped_column(Float, nullable=True)

    # 6. Read-Only Allotment Provenance Cache (Locked from TNEA Allotment)
    allotment_order_number: Mapped[str] = mapped_column(String(50), nullable=True)
    allotment_quota: Mapped[str] = mapped_column(String(50), nullable=True)
    allotted_category: Mapped[str] = mapped_column(String(50), nullable=True)
    allotted_college_code: Mapped[str] = mapped_column(String(20), nullable=True)
    allotted_branch_name: Mapped[str] = mapped_column(String(100), nullable=True)

    # 7. Category & Special Quota Flags
    is_first_graduate: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_pmss_scholarship: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_7_5_govt_quota: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_hostel_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_transport_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # 8. Declaration & Final Submission
    declaration_accepted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    declaration_accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    # JSON buckets for flexible backwards-compatibility
    personal_data: Mapped[dict] = mapped_column(JSON, nullable=True, default=dict)
    academic_data: Mapped[dict] = mapped_column(JSON, nullable=True, default=dict)
    parent_data: Mapped[dict] = mapped_column(JSON, nullable=True, default=dict)
    extra_data: Mapped[dict] = mapped_column(JSON, nullable=True, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships (lazy="selectin" for async compatibility)
    student = relationship("Student", back_populates="admission_application", lazy="selectin")
    status_history = relationship(
        "AdmissionStatusHistory",
        back_populates="admission_application",
        cascade="all, delete-orphan",
        order_by="AdmissionStatusHistory.created_at.desc()",
        lazy="selectin"
    )
    documents = relationship(
        "Document",
        back_populates="application",
        cascade="all, delete-orphan",
        lazy="selectin"
    )


class AdmissionStatusHistory(Base):
    __tablename__ = "admission_status_history"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    admission_application_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("admission_applications.id"), nullable=False, index=True
    )
    previous_status: Mapped[str] = mapped_column(String(50), nullable=True)
    new_status: Mapped[str] = mapped_column(String(50), nullable=False)
    changed_by: Mapped[str] = mapped_column(String(100), nullable=False)
    actor_role: Mapped[str] = mapped_column(String(50), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=True)
    metadata_info: Mapped[dict] = mapped_column(JSON, nullable=True, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    admission_application = relationship("AdmissionApplication", back_populates="status_history", lazy="selectin")
