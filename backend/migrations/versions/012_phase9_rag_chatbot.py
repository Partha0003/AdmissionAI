"""Phase 9 RAG Chatbot, Knowledge Base and Audit Schema

Revision ID: 012_phase9_rag_chatbot
Revises: 011_phase6_7_8_finance_erp_notifications
Create Date: 2026-09-22

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '012_phase9_rag_chatbot'
down_revision: Union[str, None] = '011_phase6_7_8_finance_erp_notifications'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. knowledge_documents
    op.create_table(
        'knowledge_documents',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False, server_default='GENERAL'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # 2. knowledge_document_versions
    op.create_table(
        'knowledge_document_versions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('document_id', sa.String(length=36), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('lifecycle_state', sa.String(length=50), nullable=False, server_default='DRAFT'),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column('created_by_id', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('activated_at', sa.DateTime(), nullable=True),
        sa.Column('archived_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['document_id'], ['knowledge_documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('document_id', 'version_number', name='uq_doc_version_number')
    )
    op.create_index('ix_kdv_doc_state', 'knowledge_document_versions', ['document_id', 'lifecycle_state'], unique=False)

    # 3. knowledge_chunks
    op.create_table(
        'knowledge_chunks',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('document_id', sa.String(length=36), nullable=False),
        sa.Column('version_id', sa.String(length=36), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('section_title', sa.String(length=255), nullable=True),
        sa.Column('page_number', sa.Integer(), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('embedding_json', sa.JSON(), nullable=True),
        sa.Column('token_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['knowledge_documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['version_id'], ['knowledge_document_versions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('version_id', 'chunk_index', name='uq_ver_chunk_idx')
    )
    op.create_index(op.f('ix_knowledge_chunks_document_id'), 'knowledge_chunks', ['document_id'], unique=False)
    op.create_index(op.f('ix_knowledge_chunks_version_id'), 'knowledge_chunks', ['version_id'], unique=False)

    # 4. chat_sessions
    op.create_table(
        'chat_sessions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('application_id', sa.String(length=36), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False, server_default='Admission Support'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['application_id'], ['admission_applications.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_chat_sessions_application_id'), 'chat_sessions', ['application_id'], unique=False)
    op.create_index(op.f('ix_chat_sessions_user_id'), 'chat_sessions', ['user_id'], unique=False)

    # 5. chat_messages
    op.create_table(
        'chat_messages',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('session_id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('sender_role', sa.String(length=20), nullable=False, server_default='USER'),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('response_type', sa.String(length=50), nullable=True, server_default='GROUNDED_KNOWLEDGE'),
        sa.Column('retrieved_sources_json', sa.JSON(), nullable=True),
        sa.Column('personal_context_used_json', sa.JSON(), nullable=True),
        sa.Column('latency_ms', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['chat_sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_chat_messages_session_id'), 'chat_messages', ['session_id'], unique=False)
    op.create_index(op.f('ix_chat_messages_user_id'), 'chat_messages', ['user_id'], unique=False)

    # 6. chat_audit_logs
    op.create_table(
        'chat_audit_logs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=True),
        sa.Column('user_role', sa.String(length=50), nullable=False),
        sa.Column('session_id', sa.String(length=36), nullable=True),
        sa.Column('message_id', sa.String(length=36), nullable=True),
        sa.Column('query_preview', sa.String(length=500), nullable=False),
        sa.Column('query_category', sa.String(length=100), nullable=False, server_default='GENERAL'),
        sa.Column('retrieved_source_ids_json', sa.JSON(), nullable=True),
        sa.Column('response_status', sa.String(length=50), nullable=False, server_default='SUCCESS'),
        sa.Column('model_provider', sa.String(length=50), nullable=False, server_default='mock'),
        sa.Column('latency_ms', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['message_id'], ['chat_messages.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['session_id'], ['chat_sessions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_chat_audit_logs_session_id'), 'chat_audit_logs', ['session_id'], unique=False)
    op.create_index(op.f('ix_chat_audit_logs_user_id'), 'chat_audit_logs', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_table('chat_audit_logs')
    op.drop_table('chat_messages')
    op.drop_table('chat_sessions')
    op.drop_table('knowledge_chunks')
    op.drop_table('knowledge_document_versions')
    op.drop_table('knowledge_documents')
