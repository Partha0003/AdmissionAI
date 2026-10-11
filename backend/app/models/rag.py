import enum
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    Integer,
    Float,
    Enum,
    JSON,
    Index,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

import uuid
from app.database.base import Base


def generate_uuid():
    return str(uuid.uuid4())




class KnowledgeCategory(str, enum.Enum):
    ADMISSION_GUIDELINES = "ADMISSION_GUIDELINES"
    DOCUMENT_VERIFICATION = "DOCUMENT_VERIFICATION"
    PHYSICAL_VERIFICATION = "PHYSICAL_VERIFICATION"
    FEE_AND_PAYMENT = "FEE_AND_PAYMENT"
    ERP_ONBOARDING = "ERP_ONBOARDING"
    FIRST_YEAR_ONBOARDING = "FIRST_YEAR_ONBOARDING"
    PARENT_GUIDANCE = "PARENT_GUIDANCE"
    CAMPUS_GUIDELINES = "CAMPUS_GUIDELINES"
    DAY_SCHOLAR = "DAY_SCHOLAR"
    HOSTELLER = "HOSTELLER"
    INAUGURATION = "INAUGURATION"
    CONTACTS = "CONTACTS"
    FAQ = "FAQ"
    GENERAL = "GENERAL"


class KnowledgeLifecycleState(str, enum.Enum):
    DRAFT = "DRAFT"
    PROCESSING = "PROCESSING"
    READY = "READY"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class ResponseType(str, enum.Enum):
    GROUNDED_KNOWLEDGE = "GROUNDED_KNOWLEDGE"
    PERSONAL_CONTEXT = "PERSONAL_CONTEXT"
    GROUNDED_KNOWLEDGE_PLUS_PERSONAL_CONTEXT = "GROUNDED_KNOWLEDGE_PLUS_PERSONAL_CONTEXT"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    SECURITY_REFUSAL = "SECURITY_REFUSAL"
    SYSTEM_ERROR = "SYSTEM_ERROR"


class ChatRole(str, enum.Enum):
    USER = "USER"
    ASSISTANT = "ASSISTANT"
    SYSTEM = "SYSTEM"


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String(255), nullable=False)
    category = Column(Enum(KnowledgeCategory), nullable=False, default=KnowledgeCategory.GENERAL)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    versions = relationship(
        "KnowledgeDocumentVersion",
        back_populates="document",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="desc(KnowledgeDocumentVersion.version_number)",
    )
    chunks = relationship(
        "KnowledgeChunk",
        back_populates="document",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class KnowledgeDocumentVersion(Base):
    __tablename__ = "knowledge_document_versions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False)
    version_number = Column(Integer, nullable=False, default=1)
    lifecycle_state = Column(
        Enum(KnowledgeLifecycleState),
        nullable=False,
        default=KnowledgeLifecycleState.DRAFT,
    )
    content = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=False)  # SHA-256 hash
    created_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    activated_at = Column(DateTime, nullable=True)
    archived_at = Column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("document_id", "version_number", name="uq_doc_version_number"),
        Index("ix_kdv_doc_state", "document_id", "lifecycle_state"),
    )

    document = relationship("KnowledgeDocument", back_populates="versions", lazy="selectin")
    chunks = relationship(
        "KnowledgeChunk",
        back_populates="version",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="KnowledgeChunk.chunk_index",
    )


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False)
    version_id = Column(String(36), ForeignKey("knowledge_document_versions.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    section_title = Column(String(255), nullable=True)
    page_number = Column(Integer, nullable=True)
    content = Column(Text, nullable=False)
    embedding_json = Column(JSON, nullable=True)  # Float array stored as JSON
    token_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("version_id", "chunk_index", name="uq_ver_chunk_idx"),
        Index("ix_kc_version_id", "version_id"),
        Index("ix_kc_doc_id", "document_id"),
    )

    document = relationship("KnowledgeDocument", back_populates="chunks", lazy="selectin")
    version = relationship("KnowledgeDocumentVersion", back_populates="chunks", lazy="selectin")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    application_id = Column(String(36), ForeignKey("admission_applications.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(255), nullable=False, default="Admission Support")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_cs_user_id", "user_id"),
        Index("ix_cs_app_id", "application_id"),
    )

    user = relationship("User", lazy="selectin")
    application = relationship("AdmissionApplication", lazy="selectin")
    messages = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="ChatMessage.created_at",
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_id = Column(String(36), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    sender_role = Column(Enum(ChatRole), nullable=False, default=ChatRole.USER)
    message = Column(Text, nullable=False)
    response_type = Column(
        Enum(ResponseType),
        nullable=True,
        default=ResponseType.GROUNDED_KNOWLEDGE,
    )
    retrieved_sources_json = Column(JSON, nullable=True)
    personal_context_used_json = Column(JSON, nullable=True)
    latency_ms = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_cm_session_id", "session_id"),
        Index("ix_cm_user_id", "user_id"),
    )

    session = relationship("ChatSession", back_populates="messages", lazy="selectin")


class ChatAuditLog(Base):
    __tablename__ = "chat_audit_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    user_role = Column(String(50), nullable=False)
    session_id = Column(String(36), ForeignKey("chat_sessions.id", ondelete="SET NULL"), nullable=True)
    message_id = Column(String(36), ForeignKey("chat_messages.id", ondelete="SET NULL"), nullable=True)
    query_preview = Column(String(500), nullable=False)
    query_category = Column(String(100), nullable=False, default="GENERAL")
    retrieved_source_ids_json = Column(JSON, nullable=True)
    response_status = Column(String(50), nullable=False, default="SUCCESS")
    model_provider = Column(String(50), nullable=False, default="mock")
    latency_ms = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_cal_user_id", "user_id"),
        Index("ix_cal_session_id", "session_id"),
    )
