"""Phase 4A Document Processing Jobs and Classification Results Schema

Revision ID: 004_phase4a_document_processing
Revises: 003_phase3_application_and_documents
Create Date: 2026-09-21

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '004_phase4a_document_processing'
down_revision: Union[str, None] = '003_phase3_application_and_documents'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Document Processing Jobs
    op.create_table(
        'document_processing_jobs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('document_id', sa.String(length=36), nullable=False),
        sa.Column('document_version_id', sa.String(length=36), nullable=True),
        sa.Column('processing_type', sa.String(length=50), nullable=False, server_default='DOCUMENT_CLASSIFICATION'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='NOT_PROCESSED'),
        sa.Column('requested_by', sa.String(length=150), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('processing_time_ms', sa.Integer(), nullable=True),
        sa.Column('engine_name', sa.String(length=100), nullable=False, server_default='RuleBasedDocumentClassifier'),
        sa.Column('engine_version', sa.String(length=50), nullable=False, server_default='1.0.0-prototype'),
        sa.Column('error_code', sa.String(length=50), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['document_version_id'], ['document_versions.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_document_processing_jobs_document_id', 'document_processing_jobs', ['document_id'], unique=False)
    op.create_index('ix_document_processing_jobs_document_version_id', 'document_processing_jobs', ['document_version_id'], unique=False)
    op.create_index('ix_document_processing_jobs_status', 'document_processing_jobs', ['status'], unique=False)

    # 2. Classification Results
    op.create_table(
        'classification_results',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('job_id', sa.String(length=36), nullable=False),
        sa.Column('predicted_document_type', sa.String(length=50), nullable=False),
        sa.Column('predicted_document_type_name', sa.String(length=150), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('confidence_type', sa.String(length=50), nullable=False, server_default='heuristic_confidence'),
        sa.Column('classifier_name', sa.String(length=100), nullable=False, server_default='RuleBasedDocumentClassifier'),
        sa.Column('classifier_version', sa.String(length=50), nullable=False, server_default='1.0.0-prototype'),
        sa.Column('rule_used', sa.String(length=255), nullable=True),
        sa.Column('reasoning', sa.Text(), nullable=True),
        sa.Column('raw_metadata', sa.JSON(), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['job_id'], ['document_processing_jobs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_classification_results_job_id', 'classification_results', ['job_id'], unique=True)


def downgrade() -> None:
    op.drop_table('classification_results')
    op.drop_table('document_processing_jobs')
