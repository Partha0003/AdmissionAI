"""Phase 5 Physical Verification Schema

Revision ID: 010_phase5_physical_verification
Revises: 009_phase4f_hitl_admission_scrutiny
Create Date: 2026-09-22

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '010_phase5_physical_verification'
down_revision: Union[str, None] = '009_phase4f_hitl_admission_scrutiny'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. physical_verification_appointments
    op.create_table(
        'physical_verification_appointments',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('application_id', sa.String(length=36), nullable=False),
        sa.Column('appointment_date', sa.Date(), nullable=False),
        sa.Column('start_time', sa.String(length=20), nullable=False),
        sa.Column('end_time', sa.String(length=20), nullable=False),
        sa.Column('token_number', sa.String(length=50), nullable=False),
        sa.Column('checkin_token', sa.String(length=64), nullable=False),
        sa.Column('location', sa.String(length=100), nullable=False, server_default='XYZ Main Campus — Central Admission Hall'),
        sa.Column('counter_desk', sa.String(length=50), nullable=True, server_default='Verification Desk 1'),
        sa.Column('appointment_status', sa.String(length=50), nullable=False, server_default='SCHEDULED'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by_id', sa.String(length=36), nullable=True),
        sa.Column('checked_in_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['application_id'], ['admission_applications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_physical_verification_appointments_application_id'), 'physical_verification_appointments', ['application_id'], unique=False)
    op.create_index(op.f('ix_physical_verification_appointments_appointment_date'), 'physical_verification_appointments', ['appointment_date'], unique=False)
    op.create_index(op.f('ix_physical_verification_appointments_token_number'), 'physical_verification_appointments', ['token_number'], unique=True)
    op.create_index(op.f('ix_physical_verification_appointments_checkin_token'), 'physical_verification_appointments', ['checkin_token'], unique=True)
    op.create_index(op.f('ix_physical_verification_appointments_appointment_status'), 'physical_verification_appointments', ['appointment_status'], unique=False)

    # 2. physical_verification_sessions
    op.create_table(
        'physical_verification_sessions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('application_id', sa.String(length=36), nullable=False),
        sa.Column('appointment_id', sa.String(length=36), nullable=True),
        sa.Column('officer_id', sa.String(length=36), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('session_status', sa.String(length=50), nullable=False, server_default='NOT_STARTED'),
        sa.Column('overall_decision', sa.String(length=50), nullable=False, server_default='PENDING'),
        sa.Column('officer_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['application_id'], ['admission_applications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['appointment_id'], ['physical_verification_appointments.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['officer_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_physical_verification_sessions_application_id'), 'physical_verification_sessions', ['application_id'], unique=False)
    op.create_index(op.f('ix_physical_verification_sessions_appointment_id'), 'physical_verification_sessions', ['appointment_id'], unique=False)
    op.create_index(op.f('ix_physical_verification_sessions_officer_id'), 'physical_verification_sessions', ['officer_id'], unique=False)
    op.create_index(op.f('ix_physical_verification_sessions_session_status'), 'physical_verification_sessions', ['session_status'], unique=False)

    # 3. physical_document_verifications
    op.create_table(
        'physical_document_verifications',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('session_id', sa.String(length=36), nullable=False),
        sa.Column('document_id', sa.String(length=36), nullable=False),
        sa.Column('document_version_id', sa.String(length=36), nullable=True),
        sa.Column('document_type_id', sa.String(length=36), nullable=True),
        sa.Column('officer_decision', sa.String(length=50), nullable=False, server_default='PENDING'),
        sa.Column('verification_notes', sa.Text(), nullable=True),
        sa.Column('discrepancy_reason', sa.String(length=100), nullable=True),
        sa.Column('checklist_checks', sa.JSON(), nullable=True),
        sa.Column('verified_by_id', sa.String(length=36), nullable=True),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['physical_verification_sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['document_version_id'], ['document_versions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['document_type_id'], ['document_types.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['verified_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_physical_document_verifications_session_id'), 'physical_document_verifications', ['session_id'], unique=False)
    op.create_index(op.f('ix_physical_document_verifications_document_id'), 'physical_document_verifications', ['document_id'], unique=False)

    # 4. physical_verification_audit_logs
    op.create_table(
        'physical_verification_audit_logs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('application_id', sa.String(length=36), nullable=False),
        sa.Column('appointment_id', sa.String(length=36), nullable=True),
        sa.Column('session_id', sa.String(length=36), nullable=True),
        sa.Column('actor_id', sa.String(length=36), nullable=True),
        sa.Column('actor_name', sa.String(length=100), nullable=True),
        sa.Column('actor_role', sa.String(length=50), nullable=True),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['application_id'], ['admission_applications.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_physical_verification_audit_logs_application_id'), 'physical_verification_audit_logs', ['application_id'], unique=False)
    op.create_index(op.f('ix_physical_verification_audit_logs_appointment_id'), 'physical_verification_audit_logs', ['appointment_id'], unique=False)
    op.create_index(op.f('ix_physical_verification_audit_logs_session_id'), 'physical_verification_audit_logs', ['session_id'], unique=False)
    op.create_index(op.f('ix_physical_verification_audit_logs_action'), 'physical_verification_audit_logs', ['action'], unique=False)


def downgrade() -> None:
    op.drop_table('physical_verification_audit_logs')
    op.drop_table('physical_document_verifications')
    op.drop_table('physical_verification_sessions')
    op.drop_table('physical_verification_appointments')
