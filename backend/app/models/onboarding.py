import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Boolean,
    Integer,
    Text,
    DateTime,
    ForeignKey,
    Enum,
    JSON,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship as orm_relationship, backref
from app.database.base import Base


class StudentType(str, enum.Enum):
    UNSPECIFIED = "UNSPECIFIED"
    DAY_SCHOLAR = "DAY_SCHOLAR"
    HOSTELLER = "HOSTELLER"


class StudentTypeStatus(str, enum.Enum):
    UNSPECIFIED = "UNSPECIFIED"
    STUDENT_REQUESTED = "STUDENT_REQUESTED"
    ADMIN_CONFIRMED = "ADMIN_CONFIRMED"


class OnboardingStatus(str, enum.Enum):
    ONBOARDING_NOT_STARTED = "ONBOARDING_NOT_STARTED"
    ONBOARDING_PROFILE_PENDING = "ONBOARDING_PROFILE_PENDING"
    ONBOARDING_IN_PROGRESS = "ONBOARDING_IN_PROGRESS"
    ONBOARDING_CHECKLIST_ACTIVE = "ONBOARDING_CHECKLIST_ACTIVE"
    INDUCTION_READY = "INDUCTION_READY"
    FIRST_YEAR_ACTIVE = "FIRST_YEAR_ACTIVE"
    ONBOARDING_BLOCKED = "ONBOARDING_BLOCKED"
    WITHDRAWN = "WITHDRAWN"


class ParentLinkStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"


class ChecklistCategory(str, enum.Enum):
    GENERAL = "GENERAL"
    DAY_SCHOLAR = "DAY_SCHOLAR"
    HOSTELLER = "HOSTELLER"
    ACADEMIC = "ACADEMIC"
    PARENT = "PARENT"


class StudentTypeScope(str, enum.Enum):
    ALL = "ALL"
    DAY_SCHOLAR = "DAY_SCHOLAR"
    HOSTELLER = "HOSTELLER"


class GuidanceCategory(str, enum.Enum):
    CONTACTS = "CONTACTS"
    INAUGURATION = "INAUGURATION"
    CAMPUS_GUIDELINES = "CAMPUS_GUIDELINES"
    DRESS_CODE = "DRESS_CODE"
    LAPTOP = "LAPTOP"
    COMMUNICATION = "COMMUNICATION"
    HOSTELLER_RULES = "HOSTELLER_RULES"
    DAY_SCHOLAR_RULES = "DAY_SCHOLAR_RULES"
    GENERAL = "GENERAL"


class EventStatus(str, enum.Enum):
    UPCOMING = "UPCOMING"
    TODAY = "TODAY"
    PAST = "PAST"


class OnboardingProfile(Base):
    __tablename__ = "onboarding_profiles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = Column(String(36), ForeignKey("students.id"), unique=True, index=True, nullable=False)
    application_id = Column(String(36), ForeignKey("admission_applications.id"), unique=True, index=True, nullable=False)
    academic_year = Column(String(20), default="2026-27", nullable=False)
    student_type = Column(Enum(StudentType), default=StudentType.UNSPECIFIED, nullable=False)
    student_type_status = Column(Enum(StudentTypeStatus), default=StudentTypeStatus.UNSPECIFIED, nullable=False)
    onboarding_status = Column(Enum(OnboardingStatus), default=OnboardingStatus.ONBOARDING_NOT_STARTED, nullable=False)
    overall_completion_percentage = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    student = orm_relationship("Student", backref=backref("onboarding_profile", uselist=False), lazy="selectin")
    application = orm_relationship("AdmissionApplication", backref=backref("onboarding_profile", uselist=False), lazy="selectin")
    checklist_items = orm_relationship("OnboardingChecklistItem", back_populates="profile", cascade="all, delete-orphan", lazy="selectin")
    audit_logs = orm_relationship("OnboardingAuditLog", back_populates="profile", cascade="all, delete-orphan", lazy="selectin")


class ParentGuardian(Base):
    __tablename__ = "parent_guardians"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    name = Column(String(150), nullable=False)
    phone = Column(String(20), nullable=False)
    email = Column(String(150), nullable=True)
    relationship = Column(String(50), nullable=False)  # FATHER, MOTHER, GUARDIAN
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = orm_relationship("User", lazy="selectin")
    student_links = orm_relationship("StudentGuardianLink", back_populates="guardian", lazy="selectin")


class StudentGuardianLink(Base):
    __tablename__ = "student_guardian_links"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = Column(String(36), ForeignKey("students.id"), nullable=False, index=True)
    guardian_id = Column(String(36), ForeignKey("parent_guardians.id"), nullable=True, index=True)
    invite_token_hash = Column(String(64), unique=True, index=True, nullable=False)  # SHA-256 hash only
    token_expires_at = Column(DateTime(timezone=True), nullable=False)
    token_used_at = Column(DateTime(timezone=True), nullable=True)
    relationship = Column(String(50), nullable=False)
    status = Column(Enum(ParentLinkStatus), default=ParentLinkStatus.PENDING, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    student = orm_relationship("Student", backref="guardian_links", lazy="selectin")
    guardian = orm_relationship("ParentGuardian", back_populates="student_links", lazy="selectin")


class OnboardingChecklistItem(Base):
    __tablename__ = "onboarding_checklist_items"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    profile_id = Column(String(36), ForeignKey("onboarding_profiles.id"), nullable=False, index=True)
    item_key = Column(String(100), nullable=False)
    title = Column(String(255), nullable=False)
    category = Column(String(50), default="GENERAL", nullable=False)
    student_type_scope = Column(String(50), default="ALL", nullable=False)  # ALL, DAY_SCHOLAR, HOSTELLER
    is_mandatory = Column(Boolean, default=True, nullable=False)
    is_acknowledged = Column(Boolean, default=False, nullable=False)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    source_reference = Column(String(150), default="General Instructions to be informed to all students", nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    profile = orm_relationship("OnboardingProfile", back_populates="checklist_items")


class OnboardingGuidanceConfiguration(Base):
    __tablename__ = "onboarding_guidance_configurations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    category = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    content_json = Column(JSON, nullable=False)
    source_document = Column(String(150), default="General Instructions to be informed to all students", nullable=False)
    source_section = Column(String(100), nullable=True)
    version_number = Column(Integer, default=1, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class InaugurationEvent(Base):
    __tablename__ = "inauguration_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    academic_year = Column(String(20), default="2026-27", nullable=False)
    event_name = Column(String(255), default="First-Year Inauguration Ceremony", nullable=False)
    event_date = Column(String(20), default="2026-08-31", nullable=False)  # YYYY-MM-DD
    reporting_time = Column(String(50), default="08:30 AM", nullable=False)
    ceremony_time = Column(String(50), default="09:30 AM", nullable=False)
    venue = Column(String(255), default="Main College Auditorium, Campus Block A", nullable=False)
    instructions_student = Column(
        Text,
        default="Formal dress code strictly required. Please arrive on time with your admission confirmation slip.",
        nullable=False,
    )
    instructions_parent = Column(
        Text,
        default="Parents and guardians are cordially invited. Refreshments and lunch will be provided.",
        nullable=False,
    )
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class TransportConfiguration(Base):
    __tablename__ = "transport_configurations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    college_code = Column(String(50), default="XYZ", nullable=False)
    routes_json = Column(JSON, default=list, nullable=False)
    general_instructions = Column(Text, nullable=True)
    is_configured = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class OnboardingAuditLog(Base):
    __tablename__ = "onboarding_audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    actor_id = Column(String(36), nullable=False)
    actor_role = Column(String(50), nullable=False)
    action = Column(String(100), nullable=False)
    profile_id = Column(String(36), ForeignKey("onboarding_profiles.id"), nullable=True, index=True)
    student_id = Column(String(36), nullable=True, index=True)
    details_json = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    profile = orm_relationship("OnboardingProfile", back_populates="audit_logs")
