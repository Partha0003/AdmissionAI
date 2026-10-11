"""Phase 4C OCR Results Schema

Revision ID: 006_phase4c_ocr_results
Revises: 005_phase4b_opencv_preprocessing
Create Date: 2026-09-22

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '006_phase4c_ocr_results'
down_revision: Union[str, None] = '005_phase4b_opencv_preprocessing'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'ocr_results',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('job_id', sa.String(length=36), nullable=False),
        sa.Column('document_id', sa.String(length=36), nullable=False),
        sa.Column('document_version_id', sa.String(length=36), nullable=True),
        sa.Column('preprocessing_result_id', sa.String(length=36), nullable=True),
        sa.Column('engine_name', sa.String(length=100), nullable=False, server_default='tesseract'),
        sa.Column('engine_version', sa.String(length=50), nullable=False, server_default='unknown'),
        sa.Column('language', sa.String(length=20), nullable=False, server_default='eng'),
        sa.Column('image_sha256', sa.String(length=64), nullable=False),
        sa.Column('ocr_confidence', sa.Float(), nullable=True),
        sa.Column('full_text', sa.Text(), nullable=True),
        sa.Column('blocks', sa.JSON(), nullable=False),
        sa.Column('processing_time_ms', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['job_id'], ['document_processing_jobs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['document_version_id'], ['document_versions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['preprocessing_result_id'], ['preprocessing_results.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_ocr_results_job_id', 'ocr_results', ['job_id'], unique=True)
    op.create_index('ix_ocr_results_document_id', 'ocr_results', ['document_id'], unique=False)
    op.create_index('ix_ocr_results_document_version_id', 'ocr_results', ['document_version_id'], unique=False)
    op.create_index('ix_ocr_results_preprocessing_result_id', 'ocr_results', ['preprocessing_result_id'], unique=False)


def downgrade() -> None:
    op.drop_table('ocr_results')
