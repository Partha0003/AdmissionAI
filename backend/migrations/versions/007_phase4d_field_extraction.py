"""Phase 4D Structured Field Extraction Schema

Revision ID: 007_phase4d_field_extraction
Revises: 006_phase4c_ocr_results
Create Date: 2026-09-22

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '007_phase4d_field_extraction'
down_revision: Union[str, None] = '006_phase4c_ocr_results'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'document_extraction_results',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('job_id', sa.String(length=36), nullable=False),
        sa.Column('document_id', sa.String(length=36), nullable=False),
        sa.Column('document_version_id', sa.String(length=36), nullable=True),
        sa.Column('ocr_result_id', sa.String(length=36), nullable=True),
        sa.Column('document_type_code', sa.String(length=50), nullable=False),
        sa.Column('extractor_name', sa.String(length=100), nullable=False),
        sa.Column('extractor_version', sa.String(length=50), nullable=False),
        sa.Column('overall_confidence', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('requires_human_review', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('fields', sa.JSON(), nullable=False),
        sa.Column('raw_metadata', sa.JSON(), nullable=False),
        sa.Column('extraction_time_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['job_id'], ['document_processing_jobs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['document_version_id'], ['document_versions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['ocr_result_id'], ['ocr_results.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_document_extraction_results_job_id', 'document_extraction_results', ['job_id'], unique=True)
    op.create_index('ix_document_extraction_results_document_id', 'document_extraction_results', ['document_id'], unique=False)
    op.create_index('ix_document_extraction_results_document_version_id', 'document_extraction_results', ['document_version_id'], unique=False)
    op.create_index('ix_document_extraction_results_ocr_result_id', 'document_extraction_results', ['ocr_result_id'], unique=False)


def downgrade() -> None:
    op.drop_table('document_extraction_results')
