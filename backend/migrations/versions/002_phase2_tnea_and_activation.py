"""Phase 2 TNEA Allotment and Activation Schema

Revision ID: 002_phase2_tnea_and_activation
Revises: 001_phase1_init
Create Date: 2026-09-19

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '002_phase2_tnea_and_activation'
down_revision: Union[str, None] = '001_phase1_init'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. TNEA Import Batches
    op.create_table(
        'tnea_import_batches',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('source', sa.String(length=100), nullable=False),
        sa.Column('filename_or_reference', sa.String(length=255), nullable=True),
        sa.Column('record_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('successful_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failed_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('duplicate_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('skipped_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('imported_by', sa.String(length=150), nullable=False),
        sa.Column('imported_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='STARTED'),
        sa.Column('errors_summary', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # 2. TNEA Allotments
    op.create_table(
        'tnea_allotments',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('student_id', sa.String(length=36), nullable=True),
        sa.Column('tnea_application_number', sa.String(length=50), nullable=False),
        sa.Column('allotment_number', sa.String(length=50), nullable=False),
        sa.Column('college_code', sa.String(length=20), nullable=False),
        sa.Column('college_name', sa.String(length=200), nullable=False),
        sa.Column('branch_code', sa.String(length=20), nullable=True),
        sa.Column('branch_name', sa.String(length=100), nullable=False),
        sa.Column('community', sa.String(length=20), nullable=True),
        sa.Column('quota', sa.String(length=50), nullable=True),
        sa.Column('cutoff_mark', sa.Float(), nullable=True),
        sa.Column('allotment_date', sa.Date(), nullable=False),
        sa.Column('joining_deadline', sa.Date(), nullable=False),
        sa.Column('allotment_status', sa.String(length=50), nullable=False, server_default='ALLOTTED'),
        sa.Column('source', sa.String(length=100), nullable=False, server_default='MOCK_TNEA_IMPORT'),
        sa.Column('raw_data', sa.JSON(), nullable=True),
        sa.Column('imported_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['student_id'], ['students.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('student_id')
    )
    op.create_index('ix_tnea_allotments_tnea_app_no', 'tnea_allotments', ['tnea_application_number'], unique=True)
    op.create_index('ix_tnea_allotments_allotment_no', 'tnea_allotments', ['allotment_number'], unique=True)
    op.create_index('ix_tnea_allotments_college_code', 'tnea_allotments', ['college_code'], unique=False)

    # 3. Student Activation Tokens
    op.create_table(
        'student_activation_tokens',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('student_id', sa.String(length=36), nullable=False),
        sa.Column('token_hash', sa.String(length=128), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_used', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['student_id'], ['students.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('student_id')
    )
    op.create_index('ix_student_activation_tokens_token_hash', 'student_activation_tokens', ['token_hash'], unique=False)


def downgrade() -> None:
    op.drop_table('student_activation_tokens')
    op.drop_table('tnea_allotments')
    op.drop_table('tnea_import_batches')
