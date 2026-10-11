"""Phase 10 Context-Aware Student, Parent & First-Year Onboarding Schema

Revision ID: 013_phase10_onboarding
Revises: 012_phase9_rag_chatbot
Create Date: 2026-09-22

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '013_phase10_onboarding'
down_revision: Union[str, None] = '012_phase9_rag_chatbot'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. onboarding_profiles
    op.create_table(
        'onboarding_profiles',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('student_id', sa.String(length=36), nullable=False),
        sa.Column('application_id', sa.String(length=36), nullable=False),
        sa.Column('academic_year', sa.String(length=20), nullable=False, server_default='2026-27'),
        sa.Column('student_type', sa.String(length=50), nullable=False, server_default='UNSPECIFIED'),
        sa.Column('student_type_status', sa.String(length=50), nullable=False, server_default='UNSPECIFIED'),
        sa.Column('onboarding_status', sa.String(length=50), nullable=False, server_default='ONBOARDING_NOT_STARTED'),
        sa.Column('overall_completion_percentage', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['application_id'], ['admission_applications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['student_id'], ['students.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('application_id'),
        sa.UniqueConstraint('student_id')
    )
    op.create_index('ix_onboarding_profiles_student_id', 'onboarding_profiles', ['student_id'], unique=True)
    op.create_index('ix_onboarding_profiles_application_id', 'onboarding_profiles', ['application_id'], unique=True)

    # 2. parent_guardians
    op.create_table(
        'parent_guardians',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=True),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=False),
        sa.Column('email', sa.String(length=150), nullable=True),
        sa.Column('relationship', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_parent_guardians_user_id', 'parent_guardians', ['user_id'], unique=False)

    # 3. student_guardian_links
    op.create_table(
        'student_guardian_links',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('student_id', sa.String(length=36), nullable=False),
        sa.Column('guardian_id', sa.String(length=36), nullable=True),
        sa.Column('invite_token_hash', sa.String(length=64), nullable=False),
        sa.Column('token_expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('token_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('relationship', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='PENDING'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['guardian_id'], ['parent_guardians.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['student_id'], ['students.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('invite_token_hash')
    )
    op.create_index('ix_student_guardian_links_student_id', 'student_guardian_links', ['student_id'], unique=False)
    op.create_index('ix_student_guardian_links_guardian_id', 'student_guardian_links', ['guardian_id'], unique=False)
    op.create_index('ix_student_guardian_links_invite_token_hash', 'student_guardian_links', ['invite_token_hash'], unique=True)

    # 4. onboarding_checklist_items
    op.create_table(
        'onboarding_checklist_items',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('profile_id', sa.String(length=36), nullable=False),
        sa.Column('item_key', sa.String(length=100), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False, server_default='GENERAL'),
        sa.Column('student_type_scope', sa.String(length=50), nullable=False, server_default='ALL'),
        sa.Column('is_mandatory', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('is_acknowledged', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('source_reference', sa.String(length=150), nullable=False, server_default='General Instructions to be informed to all students'),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['profile_id'], ['onboarding_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_onboarding_checklist_items_profile_id', 'onboarding_checklist_items', ['profile_id'], unique=False)

    # 5. onboarding_guidance_configurations
    op.create_table(
        'onboarding_guidance_configurations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('content_json', sa.JSON(), nullable=False),
        sa.Column('source_document', sa.String(length=150), nullable=False, server_default='General Instructions to be informed to all students'),
        sa.Column('source_section', sa.String(length=100), nullable=True),
        sa.Column('version_number', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )

    # 6. inauguration_events
    op.create_table(
        'inauguration_events',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('academic_year', sa.String(length=20), nullable=False, server_default='2026-27'),
        sa.Column('event_name', sa.String(length=255), nullable=False, server_default='First-Year Inauguration Ceremony'),
        sa.Column('event_date', sa.String(length=20), nullable=False, server_default='2026-08-31'),
        sa.Column('reporting_time', sa.String(length=50), nullable=False, server_default='08:30 AM'),
        sa.Column('ceremony_time', sa.String(length=50), nullable=False, server_default='09:30 AM'),
        sa.Column('venue', sa.String(length=255), nullable=False, server_default='Main College Auditorium, Campus Block A'),
        sa.Column('instructions_student', sa.Text(), nullable=False),
        sa.Column('instructions_parent', sa.Text(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )

    # 7. transport_configurations
    op.create_table(
        'transport_configurations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('college_code', sa.String(length=50), nullable=False, server_default='XYZ'),
        sa.Column('routes_json', sa.JSON(), nullable=False),
        sa.Column('general_instructions', sa.Text(), nullable=True),
        sa.Column('is_configured', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )

    # 8. onboarding_audit_logs
    op.create_table(
        'onboarding_audit_logs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('actor_id', sa.String(length=36), nullable=False),
        sa.Column('actor_role', sa.String(length=50), nullable=False),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('profile_id', sa.String(length=36), nullable=True),
        sa.Column('student_id', sa.String(length=36), nullable=True),
        sa.Column('details_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['profile_id'], ['onboarding_profiles.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_onboarding_audit_logs_profile_id', 'onboarding_audit_logs', ['profile_id'], unique=False)
    op.create_index('ix_onboarding_audit_logs_student_id', 'onboarding_audit_logs', ['student_id'], unique=False)


def downgrade() -> None:
    op.drop_table('onboarding_audit_logs')
    op.drop_table('transport_configurations')
    op.drop_table('inauguration_events')
    op.drop_table('onboarding_guidance_configurations')
    op.drop_table('onboarding_checklist_items')
    op.drop_table('student_guardian_links')
    op.drop_table('parent_guardians')
    op.drop_table('onboarding_profiles')
