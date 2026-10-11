"""Initial Phase 1 Schema

Revision ID: 001_phase1_init
Revises: 
Create Date: 2026-09-18

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '001_phase1_init'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Institutions
    op.create_table(
        'institutions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('code', sa.String(length=20), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('academic_year', sa.String(length=20), nullable=False),
        sa.Column('environment', sa.String(length=50), nullable=False),
        sa.Column('config', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_institutions_code', 'institutions', ['code'], unique=True)

    # 2. Roles
    op.create_table(
        'roles',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_roles_name', 'roles', ['name'], unique=True)

    # 3. Users
    op.create_table(
        'users',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('email', sa.String(length=150), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # 4. Students
    op.create_table(
        'students',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('institution_id', sa.String(length=36), nullable=False),
        sa.Column('tnea_application_number', sa.String(length=50), nullable=False),
        sa.Column('full_name', sa.String(length=150), nullable=False),
        sa.Column('date_of_birth', sa.Date(), nullable=False),
        sa.Column('email', sa.String(length=150), nullable=False),
        sa.Column('mobile', sa.String(length=20), nullable=False),
        sa.Column('community', sa.String(length=20), nullable=True),
        sa.Column('allotted_branch', sa.String(length=100), nullable=True),
        sa.Column('quota', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['institution_id'], ['institutions.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
    op.create_index('ix_students_tnea_application_number', 'students', ['tnea_application_number'], unique=True)
    op.create_index('ix_students_email', 'students', ['email'], unique=False)

    # 5. Admission Applications
    op.create_table(
        'admission_applications',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('student_id', sa.String(length=36), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('completion_percentage', sa.Integer(), nullable=False),
        sa.Column('personal_data', sa.JSON(), nullable=True),
        sa.Column('academic_data', sa.JSON(), nullable=True),
        sa.Column('parent_data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['student_id'], ['students.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('student_id')
    )
    op.create_index('ix_admission_applications_status', 'admission_applications', ['status'], unique=False)

    # 6. Admission Status History
    op.create_table(
        'admission_status_history',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('admission_application_id', sa.String(length=36), nullable=False),
        sa.Column('previous_status', sa.String(length=50), nullable=True),
        sa.Column('new_status', sa.String(length=50), nullable=False),
        sa.Column('changed_by', sa.String(length=100), nullable=False),
        sa.Column('actor_role', sa.String(length=50), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('metadata_info', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['admission_application_id'], ['admission_applications.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_admission_status_history_app_id', 'admission_status_history', ['admission_application_id'], unique=False)


def downgrade() -> None:
    op.drop_table('admission_status_history')
    op.drop_table('admission_applications')
    op.drop_table('students')
    op.drop_table('users')
    op.drop_table('roles')
    op.drop_table('institutions')
