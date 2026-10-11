"""Phase 4E Cross-Document Verification and Consistency Reconciliation Schema

Revision ID: 008_phase4e_cross_document_reconciliation
Revises: 007_phase4d_field_extraction
Create Date: 2026-09-22

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '008_phase4e_cross_document_reconciliation'
down_revision: Union[str, None] = '007_phase4d_field_extraction'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'cross_document_reconciliations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('application_id', sa.String(length=36), nullable=False),
        sa.Column('overall_status', sa.String(length=30), nullable=False, server_default='MATCH'),
        sa.Column('participating_document_versions', sa.JSON(), nullable=False),
        sa.Column('total_rules_evaluated', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('passed_rules_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('discrepancy_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('pending_scrutiny_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('incomplete_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('findings', sa.JSON(), nullable=False),
        sa.Column('discrepancy_summary', sa.JSON(), nullable=False),
        sa.Column('requires_human_review', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('reconciliation_time_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['application_id'], ['admission_applications.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(
        op.f('ix_cross_document_reconciliations_application_id'),
        'cross_document_reconciliations',
        ['application_id'],
        unique=False
    )
    op.create_index(
        op.f('ix_cross_document_reconciliations_overall_status'),
        'cross_document_reconciliations',
        ['overall_status'],
        unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_cross_document_reconciliations_overall_status'), table_name='cross_document_reconciliations')
    op.drop_index(op.f('ix_cross_document_reconciliations_application_id'), table_name='cross_document_reconciliations')
    op.drop_table('cross_document_reconciliations')
