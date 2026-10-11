"""Phase 4B OpenCV Preprocessing Results Schema

Revision ID: 005_phase4b_opencv_preprocessing
Revises: 004_phase4a_document_processing
Create Date: 2026-09-21

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '005_phase4b_opencv_preprocessing'
down_revision: Union[str, None] = '004_phase4a_document_processing'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'preprocessing_results',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('job_id', sa.String(length=36), nullable=False),
        sa.Column('document_id', sa.String(length=36), nullable=False),
        sa.Column('document_version_id', sa.String(length=36), nullable=True),
        sa.Column('engine_name', sa.String(length=100), nullable=False, server_default='OpenCVDocumentPreprocessor'),
        sa.Column('engine_version', sa.String(length=50), nullable=False, server_default='1.0.0-opencv'),
        sa.Column('input_dimensions', sa.JSON(), nullable=False),
        sa.Column('output_dimensions', sa.JSON(), nullable=False),
        sa.Column('operations_applied', sa.JSON(), nullable=False),
        sa.Column('deskew_angle_deg', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('storage_path', sa.String(length=500), nullable=False),
        sa.Column('output_filename', sa.String(length=255), nullable=False),
        sa.Column('output_mime_type', sa.String(length=100), nullable=False, server_default='image/png'),
        sa.Column('output_file_size', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('processing_time_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['job_id'], ['document_processing_jobs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['document_version_id'], ['document_versions.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_preprocessing_results_job_id', 'preprocessing_results', ['job_id'], unique=True)
    op.create_index('ix_preprocessing_results_document_id', 'preprocessing_results', ['document_id'], unique=False)
    op.create_index('ix_preprocessing_results_document_version_id', 'preprocessing_results', ['document_version_id'], unique=False)


def downgrade() -> None:
    op.drop_table('preprocessing_results')
