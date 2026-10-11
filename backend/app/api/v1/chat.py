from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from app.database.session import get_db
from app.models.user import User
from app.models.rag import KnowledgeDocument, KnowledgeDocumentVersion, KnowledgeChunk
from app.api.deps import get_current_user, require_roles
from app.services.rag_service import ChatService, KnowledgeService
from app.schemas.rag import (
    ChatSessionCreate,
    ChatSessionResponse,
    ChatMessageCreate,
    ChatMessageResponse,
    KnowledgeIngestRequest,
    KnowledgeDocumentResponse,
    KnowledgeVersionResponse,
    KnowledgeChunkResponse,
    SourceCitationResponse,
)

router = APIRouter(tags=["RAG & Chatbot Support"])


# ==============================================================================
# STUDENT & USER CHAT ENDPOINTS
# ==============================================================================

@router.post("/chat/sessions", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_chat_session(
    payload: Optional[ChatSessionCreate] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new context-bound chat session for the authenticated user."""
    title = payload.title if payload and payload.title else "Admission Support"
    session = await ChatService.create_session(db, current_user, title=title)
    return session


@router.get("/chat/sessions", response_model=List[ChatSessionResponse])
async def list_chat_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all chat sessions belonging to the authenticated user."""
    sessions = await ChatService.get_user_sessions(db, current_user.id)
    return sessions


@router.get("/chat/sessions/{session_id}", response_model=ChatSessionResponse)
async def get_chat_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve chat session details and chronological message history."""
    session = await ChatService.get_session_detail(db, session_id, current_user.id, current_user.role)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found or unauthorized.",
        )
    return session


@router.post("/chat/sessions/{session_id}/messages", response_model=ChatMessageResponse)
async def send_chat_message(
    session_id: str,
    payload: ChatMessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Send a message to the AI admission assistant.
    Executes context resolution, security filtering, knowledge retrieval, and grounded response generation.
    """
    if not payload.message or not payload.message.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Message content cannot be empty.",
        )

    try:
        msg = await ChatService.process_user_message(
            db=db,
            session_id=session_id,
            user=current_user,
            query=payload.message,
            llm_provider=payload.llm_provider or "mock",
            top_k=payload.top_k or 4,
        )
        return msg
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get("/chat/sources/{chunk_id}", response_model=KnowledgeChunkResponse)
async def get_source_chunk(
    chunk_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Inspect knowledge chunk provenance and content."""
    stmt = select(KnowledgeChunk).where(KnowledgeChunk.id == chunk_id)
    res = await db.execute(stmt)
    chunk = res.scalar_one_or_none()
    if not chunk:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge source chunk not found.",
        )
    return chunk


# ==============================================================================
# ADMIN KNOWLEDGE MANAGEMENT ENDPOINTS
# ==============================================================================

@router.post(
    "/admin/knowledge/ingest",
    response_model=KnowledgeDocumentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(["ADMIN_VERIFIER", "ADMISSION_HEAD", "SUPER_ADMIN"]))],
)
async def ingest_knowledge_document(
    payload: KnowledgeIngestRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Ingest a new knowledge document or version into the knowledge repository."""
    if not payload.title or not payload.content:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Document title and content are mandatory.",
        )

    doc, version = await KnowledgeService.ingest_document(
        db=db,
        title=payload.title,
        content=payload.content,
        category=payload.category,
        description=payload.description,
        created_by_id=current_user.id,
        auto_activate=payload.auto_activate,
    )

    # Re-fetch document with versions
    stmt = select(KnowledgeDocument).where(KnowledgeDocument.id == doc.id).options(selectinload(KnowledgeDocument.versions))
    res = await db.execute(stmt)
    return res.scalar_one()


@router.get(
    "/admin/knowledge/documents",
    response_model=List[KnowledgeDocumentResponse],
    dependencies=[Depends(require_roles(["ADMIN_VERIFIER", "ADMISSION_HEAD", "SUPER_ADMIN"]))],
)
async def list_knowledge_documents(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all knowledge base documents and their version lifecycle statuses."""
    stmt = select(KnowledgeDocument).options(selectinload(KnowledgeDocument.versions)).order_by(desc(KnowledgeDocument.created_at))
    res = await db.execute(stmt)
    return res.scalars().all()


@router.get(
    "/admin/knowledge/documents/{document_id}",
    response_model=KnowledgeDocumentResponse,
    dependencies=[Depends(require_roles(["ADMIN_VERIFIER", "ADMISSION_HEAD", "SUPER_ADMIN"]))],
)
async def get_knowledge_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve detailed knowledge document with all versions and chunks."""
    stmt = (
        select(KnowledgeDocument)
        .where(KnowledgeDocument.id == document_id)
        .options(
            selectinload(KnowledgeDocument.versions).selectinload(KnowledgeDocumentVersion.chunks)
        )
    )
    res = await db.execute(stmt)
    doc = res.scalar_one_or_none()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge document not found.",
        )
    return doc


@router.post(
    "/admin/knowledge/documents/{version_id}/activate",
    response_model=KnowledgeVersionResponse,
    dependencies=[Depends(require_roles(["ADMISSION_HEAD", "SUPER_ADMIN"]))],
)
async def activate_knowledge_version(
    version_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Activate a specific knowledge document version (archives previous active version)."""
    try:
        ver = await KnowledgeService.activate_version(db, version_id)
        return ver
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
