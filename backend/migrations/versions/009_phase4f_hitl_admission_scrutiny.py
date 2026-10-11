"""Phase 4F Human-in-the-Loop Admission Scrutiny Schema

Revision ID: 009_phase4f_hitl_admission_scrutiny
Revises: 008_phase4e_cross_document_reconciliation
Create Date: 2026-09-22

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '009_phase4f_hitl_admission_scrutiny'
down_revision: Union[str, None] = '008_phase4e_cross_document_reconciliation'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. admission_reviews
    op.create_table(
        'admission_reviews',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('application_id', sa.String(length=36), nullable=False),
        sa.Column('reviewer_id', sa.String(length=36), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='NOT_STARTED'),
        sa.Column('decision', sa.String(length=50), nullable=True),
        sa.Column('overall_comments', sa.Text(), nullable=True),
        sa.Column('correction_reason', sa.String(length=100), nullable=True),
        sa.Column('correction_instructions', sa.Text(), nullable=True),
        sa.Column('reviewed_document_versions', sa.JSON(), nullable=False),
        sa.Column('reviewed_reconciliation_id', sa.String(length=36), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['application_id'], ['admission_applications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewer_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['reviewed_reconciliation_id'], ['cross_document_reconciliations.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_admission_reviews_application_id'), 'admission_reviews', ['application_id'], unique=False)
    op.create_index(op.f('ix_admission_reviews_reviewer_id'), 'admission_reviews', ['reviewer_id'], unique=False)
    op.create_index(op.f('ix_admission_reviews_status'), 'admission_reviews', ['status'], unique=False)

    # 2. document_review_items
    op.create_table(
        'document_review_items',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('review_id', sa.String(length=36), nullable=False),
        sa.Column('document_id', sa.String(length=36), nullable=False),
        sa.Column('document_version_id', sa.String(length=36), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='PENDING'),
        sa.Column('correction_reason', sa.String(length=100), nullable=True),
        sa.Column('reviewer_comments', sa.Text(), nullable=True),
        sa.Column('reviewed_by_id', sa.String(length=36), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['review_id'], ['admission_reviews.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['document_version_id'], ['document_versions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['reviewed_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_document_review_items_review_id'), 'document_review_items', ['review_id'], unique=False)
    op.create_index(op.f('ix_document_review_items_document_id'), 'document_review_items', ['document_id'], unique=False)

    # 3. field_review_items
    op.create_table(
        'field_review_items',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('review_id', sa.String(length=36), nullable=False),
        sa.Column('field_key', sa.String(length=100), nullable=False),
        sa.Column('declared_value', sa.String(length=255), nullable=True),
        sa.Column('extracted_value', sa.String(length=255), nullable=True),
        sa.Column('reconciliation_status', sa.String(length=50), nullable=True),
        sa.Column('decision', sa.String(length=50), nullable=False, server_default='CONFIRMED'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('document_id', sa.String(length=36), nullable=True),
        sa.Column('document_version_id', sa.String(length=36), nullable=True),
        sa.Column('reviewed_by_id', sa.String(length=36), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['review_id'], ['admission_reviews.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['document_version_id'], ['document_versions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['reviewed_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_field_review_items_review_id'), 'field_review_items', ['review_id'], unique=False)
    op.create_index(op.f('ix_field_review_items_field_key'), 'field_review_items', ['field_key'], unique=False)

    # 4. scrutiny_audit_logs
    op.create_table(
        'scrutiny_audit_logs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('review_id', sa.String(length=36), nullable=True),
        sa.Column('application_id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=True),
        sa.Column('user_name', sa.String(length=150), nullable=True),
        sa.Column('user_role', sa.String(length=50), nullable=False),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('previous_status', sa.String(length=50), nullable=True),
        sa.Column('new_status', sa.String(length=50), nullable=True),
        sa.Column('details', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['review_id'], ['admission_reviews.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['application_id'], ['admission_applications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_scrutiny_audit_logs_review_id'), 'scrutiny_audit_logs', ['review_id'], unique=False)
    op.create_index(op.f('ix_scrutiny_audit_logs_application_id'), 'scrutiny_audit_logs', ['application_id'], unique=False)
    op.create_index(op.f('ix_scrutiny_audit_logs_action'), 'scrutiny_audit_logs', ['action'], unique=False)
    op.create_index(op.f('ix_scrutiny_audit_logs_created_at'), 'scrutiny_audit_logs', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_table('scrutiny_audit_logs')
    op.drop_table('field_review_items')
    op.drop_table('document_review_items')
    op.drop_table('admission_reviews')
