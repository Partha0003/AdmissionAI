from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict
from app.models.rag import (
    KnowledgeCategory,
    KnowledgeLifecycleState,
    ResponseType,
    ChatRole,
)


class KnowledgeChunkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    version_id: str
    chunk_index: int
    section_title: Optional[str] = None
    page_number: Optional[int] = None
    content: str
    token_count: int
    created_at: datetime


class KnowledgeVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    version_number: int
    lifecycle_state: KnowledgeLifecycleState
    content_hash: str
    created_at: datetime
    activated_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None
    chunks: Optional[List[KnowledgeChunkResponse]] = None


class KnowledgeDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    category: KnowledgeCategory
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    versions: Optional[List[KnowledgeVersionResponse]] = None


class KnowledgeIngestRequest(BaseModel):
    title: str
    content: str
    category: Optional[KnowledgeCategory] = KnowledgeCategory.GENERAL
    description: Optional[str] = None
    auto_activate: bool = False


class SourceCitationResponse(BaseModel):
    chunk_id: str
    document_id: str
    document_title: str
    section_title: Optional[str] = None
    page_number: Optional[int] = None
    version_number: int
    category: str


class ChatMessageCreate(BaseModel):
    message: str
    llm_provider: Optional[str] = "mock"
    top_k: Optional[int] = 4


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    user_id: str
    sender_role: ChatRole
    message: str
    response_type: Optional[ResponseType] = None
    retrieved_sources_json: Optional[List[Dict[str, Any]]] = None
    personal_context_used_json: Optional[Dict[str, Any]] = None
    latency_ms: Optional[float] = None
    created_at: datetime


class ChatSessionCreate(BaseModel):
    title: Optional[str] = "Admission Support"


class ChatSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    application_id: Optional[str] = None
    title: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    messages: Optional[List[ChatMessageResponse]] = None


class ChatAuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: Optional[str] = None
    user_role: str
    session_id: Optional[str] = None
    message_id: Optional[str] = None
    query_preview: str
    query_category: str
    retrieved_source_ids_json: Optional[List[str]] = None
    response_status: str
    model_provider: str
    latency_ms: Optional[float] = None
    created_at: datetime
