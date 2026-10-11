"""Phase 6, 7, 8 Finance, ERP and Notifications Schema

Revision ID: 011_phase6_7_8_finance_erp_notifications
Revises: 010_phase5_physical_verification
Create Date: 2026-09-22

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '011_phase6_7_8_finance_erp_notifications'
down_revision: Union[str, None] = '010_phase5_physical_verification'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. fee_requirements
    op.create_table(
        'fee_requirements',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('academic_year', sa.String(length=20), nullable=False, server_default='2026-27'),
        sa.Column('category', sa.String(length=50), nullable=False, server_default='GENERAL'),
        sa.Column('quota', sa.String(length=50), nullable=False, server_default='GOVERNMENT'),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False, server_default='50000.00'),
        sa.Column('currency', sa.String(length=10), nullable=False, server_default='INR'),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # 2. payment_transactions
    op.create_table(
        'payment_transactions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('application_id', sa.String(length=36), nullable=False),
        sa.Column('payment_reference', sa.String(length=64), nullable=False),
        sa.Column('payment_method', sa.String(length=50), nullable=False, server_default='DEMAND_DRAFT'),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=10), nullable=False, server_default='INR'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='INITIATED'),
        sa.Column('initiated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('verified_by_id', sa.String(length=36), nullable=True),
        sa.Column('rejection_reason', sa.String(length=64), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('fee_requirement_id', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['application_id'], ['admission_applications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['fee_requirement_id'], ['fee_requirements.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['verified_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_payment_transactions_application_id'), 'payment_transactions', ['application_id'], unique=False)
    op.create_index(op.f('ix_payment_transactions_payment_reference'), 'payment_transactions', ['payment_reference'], unique=True)
    op.create_index(op.f('ix_payment_transactions_status'), 'payment_transactions', ['status'], unique=False)

    # 3. demand_draft_submissions
    op.create_table(
        'demand_draft_submissions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('payment_id', sa.String(length=36), nullable=False),
        sa.Column('dd_number', sa.String(length=64), nullable=False),
        sa.Column('dd_date', sa.String(length=20), nullable=False),
        sa.Column('bank_name', sa.String(length=128), nullable=False),
        sa.Column('branch_name', sa.String(length=128), nullable=True),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('supporting_document_id', sa.String(length=36), nullable=True),
        sa.Column('supporting_document_version_id', sa.String(length=36), nullable=True),
        sa.Column('submitted_by_id', sa.String(length=36), nullable=False),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('finance_verified_by_id', sa.String(length=36), nullable=True),
        sa.Column('finance_verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finance_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['payment_id'], ['payment_transactions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['supporting_document_id'], ['documents.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['supporting_document_version_id'], ['document_versions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['submitted_by_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['finance_verified_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('payment_id')
    )
    op.create_index(op.f('ix_demand_draft_submissions_dd_number'), 'demand_draft_submissions', ['dd_number'], unique=False)
    op.create_index(op.f('ix_demand_draft_submissions_bank_name'), 'demand_draft_submissions', ['bank_name'], unique=False)

    # 4. payment_audit_logs
    op.create_table(
        'payment_audit_logs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('application_id', sa.String(length=36), nullable=False),
        sa.Column('payment_id', sa.String(length=36), nullable=False),
        sa.Column('actor_id', sa.String(length=36), nullable=True),
        sa.Column('actor_name', sa.String(length=128), nullable=True),
        sa.Column('actor_role', sa.String(length=64), nullable=True),
        sa.Column('action', sa.String(length=64), nullable=False),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['application_id'], ['admission_applications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['payment_id'], ['payment_transactions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_payment_audit_logs_application_id'), 'payment_audit_logs', ['application_id'], unique=False)
    op.create_index(op.f('ix_payment_audit_logs_payment_id'), 'payment_audit_logs', ['payment_id'], unique=False)
    op.create_index(op.f('ix_payment_audit_logs_action'), 'payment_audit_logs', ['action'], unique=False)

    # 5. erp_admission_records
    op.create_table(
        'erp_admission_records',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('application_id', sa.String(length=36), nullable=False),
        sa.Column('staging_reference', sa.String(length=64), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('payload_hash', sa.String(length=64), nullable=False),
        sa.Column('payload_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='READY_FOR_STAGING'),
        sa.Column('validation_errors', sa.JSON(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('staged_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('synced_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['application_id'], ['admission_applications.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('application_id'),
        sa.UniqueConstraint('staging_reference')
    )
    op.create_index(op.f('ix_erp_admission_records_application_id'), 'erp_admission_records', ['application_id'], unique=True)
    op.create_index(op.f('ix_erp_admission_records_staging_reference'), 'erp_admission_records', ['staging_reference'], unique=True)
    op.create_index(op.f('ix_erp_admission_records_status'), 'erp_admission_records', ['status'], unique=False)

    # 6. erp_integration_events
    op.create_table(
        'erp_integration_events',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('erp_record_id', sa.String(length=36), nullable=False),
        sa.Column('event_type', sa.String(length=64), nullable=False),
        sa.Column('adapter_name', sa.String(length=64), nullable=False, server_default='MockERPAdapter'),
        sa.Column('request_reference', sa.String(length=64), nullable=True),
        sa.Column('response_reference', sa.String(length=64), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('error_summary', sa.Text(), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['erp_record_id'], ['erp_admission_records.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_erp_integration_events_erp_record_id'), 'erp_integration_events', ['erp_record_id'], unique=False)
    op.create_index(op.f('ix_erp_integration_events_event_type'), 'erp_integration_events', ['event_type'], unique=False)
    op.create_index(op.f('ix_erp_integration_events_created_at'), 'erp_integration_events', ['created_at'], unique=False)

    # 7. notifications
    op.create_table(
        'notifications',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('application_id', sa.String(length=36), nullable=True),
        sa.Column('type', sa.String(length=64), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False, server_default='INFO'),
        sa.Column('channel', sa.String(length=20), nullable=False, server_default='IN_APP'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='DELIVERED'),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['application_id'], ['admission_applications.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notifications_user_id'), 'notifications', ['user_id'], unique=False)
    op.create_index(op.f('ix_notifications_status'), 'notifications', ['status'], unique=False)
    op.create_index(op.f('ix_notifications_created_at'), 'notifications', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_table('notifications')
    op.drop_table('erp_integration_events')
    op.drop_table('erp_admission_records')
    op.drop_table('payment_audit_logs')
    op.drop_table('demand_draft_submissions')
    op.drop_table('payment_transactions')
    op.drop_table('fee_requirements')
