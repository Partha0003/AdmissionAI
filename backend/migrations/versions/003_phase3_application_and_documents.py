"""Phase 3 Application Form and Document Management Schema

Revision ID: 003_phase3_application_and_documents
Revises: 002_phase2_tnea_and_activation
Create Date: 2026-09-20

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '003_phase3_application_and_documents'
down_revision: Union[str, None] = '002_phase2_tnea_and_activation'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Document Types
    op.create_table(
        'document_types',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(length=50), nullable=False, server_default='ACADEMIC'),
        sa.Column('allowed_extensions', sa.JSON(), nullable=False),
        sa.Column('max_size_mb', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_document_types_code', 'document_types', ['code'], unique=True)

    # 2. Document Rules
    op.create_table(
        'document_rules',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('document_type_id', sa.String(length=36), nullable=False),
        sa.Column('required', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('applicable_conditions', sa.JSON(), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('academic_year', sa.String(length=20), nullable=False, server_default='2026-27'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['document_type_id'], ['document_types.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_document_rules_doc_type', 'document_rules', ['document_type_id'], unique=False)

    # 3. Documents
    op.create_table(
        'documents',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('application_id', sa.String(length=36), nullable=False),
        sa.Column('document_type_id', sa.String(length=36), nullable=False),
        sa.Column('current_version_id', sa.String(length=36), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='UPLOADED'),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['application_id'], ['admission_applications.id']),
        sa.ForeignKeyConstraint(['document_type_id'], ['document_types.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_documents_app_id', 'documents', ['application_id'], unique=False)
    op.create_index('ix_documents_type_id', 'documents', ['document_type_id'], unique=False)

    # 4. Document Versions
    op.create_table(
        'document_versions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('document_id', sa.String(length=36), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('storage_path', sa.String(length=500), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('mime_type', sa.String(length=100), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('file_hash', sa.String(length=64), nullable=False),
        sa.Column('uploaded_by', sa.String(length=150), nullable=False),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_document_versions_document_id', 'document_versions', ['document_id'], unique=False)
    op.create_index('ix_document_versions_file_hash', 'document_versions', ['file_hash'], unique=False)

    # 5. Extend admission_applications table with Phase 3 columns
    with op.batch_alter_table('admission_applications') as batch_op:
        batch_op.add_column(sa.Column('application_number', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('gender', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('blood_group', sa.String(length=10), nullable=True))
        batch_op.add_column(sa.Column('nationality', sa.String(length=50), nullable=True, server_default='Indian'))
        batch_op.add_column(sa.Column('religion', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('caste', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('mother_tongue', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('aadhaar_number', sa.String(length=20), nullable=True))
        
        batch_op.add_column(sa.Column('address_line1', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('address_line2', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('city', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('district', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('state', sa.String(length=100), nullable=True, server_default='Tamil Nadu'))
        batch_op.add_column(sa.Column('pincode', sa.String(length=20), nullable=True))
        
        batch_op.add_column(sa.Column('emergency_contact_name', sa.String(length=150), nullable=True))
        batch_op.add_column(sa.Column('emergency_contact_phone', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('emergency_contact_relation', sa.String(length=50), nullable=True))
        
        batch_op.add_column(sa.Column('father_name', sa.String(length=150), nullable=True))
        batch_op.add_column(sa.Column('father_occupation', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('father_mobile', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('father_email', sa.String(length=150), nullable=True))
        
        batch_op.add_column(sa.Column('mother_name', sa.String(length=150), nullable=True))
        batch_op.add_column(sa.Column('mother_occupation', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('mother_mobile', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('mother_email', sa.String(length=150), nullable=True))
        
        batch_op.add_column(sa.Column('guardian_name', sa.String(length=150), nullable=True))
        batch_op.add_column(sa.Column('guardian_occupation', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('guardian_mobile', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('guardian_relation', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('annual_family_income', sa.Float(), nullable=True))
        
        batch_op.add_column(sa.Column('tenth_school_name', sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column('tenth_board', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('tenth_year_of_passing', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('tenth_registration_number', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('tenth_total_marks', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('tenth_max_marks', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('tenth_percentage', sa.Float(), nullable=True))
        
        batch_op.add_column(sa.Column('twelfth_school_name', sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column('twelfth_board', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('twelfth_year_of_passing', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('twelfth_registration_number', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('twelfth_total_marks', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('twelfth_max_marks', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('twelfth_percentage', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('twelfth_maths_marks', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('twelfth_physics_marks', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('twelfth_chemistry_marks', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('twelfth_cutoff_marks', sa.Float(), nullable=True))
        
        batch_op.add_column(sa.Column('allotment_order_number', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('allotment_quota', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('allotted_category', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('allotted_college_code', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('allotted_branch_name', sa.String(length=100), nullable=True))
        
        batch_op.add_column(sa.Column('is_first_graduate', sa.Boolean(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('is_pmss_scholarship', sa.Boolean(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('is_7_5_govt_quota', sa.Boolean(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('is_hostel_required', sa.Boolean(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('is_transport_required', sa.Boolean(), nullable=False, server_default='0'))
        
        batch_op.add_column(sa.Column('declaration_accepted', sa.Boolean(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('declaration_accepted_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True))
        
        batch_op.create_unique_constraint('uq_admission_applications_app_no', ['application_number'])


def downgrade() -> None:
    with op.batch_alter_table('admission_applications') as batch_op:
        batch_op.drop_constraint('uq_admission_applications_app_no', type_='unique')
        batch_op.drop_column('submitted_at')
        batch_op.drop_column('declaration_accepted_at')
        batch_op.drop_column('declaration_accepted')
        batch_op.drop_column('is_transport_required')
        batch_op.drop_column('is_hostel_required')
        batch_op.drop_column('is_7_5_govt_quota')
        batch_op.drop_column('is_pmss_scholarship')
        batch_op.drop_column('is_first_graduate')
        batch_op.drop_column('allotted_branch_name')
        batch_op.drop_column('allotted_college_code')
        batch_op.drop_column('allotted_category')
        batch_op.drop_column('allotment_quota')
        batch_op.drop_column('allotment_order_number')
        batch_op.drop_column('twelfth_cutoff_marks')
        batch_op.drop_column('twelfth_chemistry_marks')
        batch_op.drop_column('twelfth_physics_marks')
        batch_op.drop_column('twelfth_maths_marks')
        batch_op.drop_column('twelfth_percentage')
        batch_op.drop_column('twelfth_max_marks')
        batch_op.drop_column('twelfth_total_marks')
        batch_op.drop_column('twelfth_registration_number')
        batch_op.drop_column('twelfth_year_of_passing')
        batch_op.drop_column('twelfth_board')
        batch_op.drop_column('twelfth_school_name')
        batch_op.drop_column('tenth_percentage')
        batch_op.drop_column('tenth_max_marks')
        batch_op.drop_column('tenth_total_marks')
        batch_op.drop_column('tenth_registration_number')
        batch_op.drop_column('tenth_year_of_passing')
        batch_op.drop_column('tenth_board')
        batch_op.drop_column('tenth_school_name')
        batch_op.drop_column('annual_family_income')
        batch_op.drop_column('guardian_relation')
        batch_op.drop_column('guardian_mobile')
        batch_op.drop_column('guardian_occupation')
        batch_op.drop_column('guardian_name')
        batch_op.drop_column('mother_email')
        batch_op.drop_column('mother_mobile')
        batch_op.drop_column('mother_occupation')
        batch_op.drop_column('mother_name')
        batch_op.drop_column('father_email')
        batch_op.drop_column('father_mobile')
        batch_op.drop_column('father_occupation')
        batch_op.drop_column('father_name')
        batch_op.drop_column('emergency_contact_relation')
        batch_op.drop_column('emergency_contact_phone')
        batch_op.drop_column('emergency_contact_name')
        batch_op.drop_column('pincode')
        batch_op.drop_column('state')
        batch_op.drop_column('district')
        batch_op.drop_column('city')
        batch_op.drop_column('address_line2')
        batch_op.drop_column('address_line1')
        batch_op.drop_column('aadhaar_number')
        batch_op.drop_column('mother_tongue')
        batch_op.drop_column('caste')
        batch_op.drop_column('religion')
        batch_op.drop_column('nationality')
        batch_op.drop_column('blood_group')
        batch_op.drop_column('gender')
        batch_op.drop_column('application_number')

    op.drop_table('document_versions')
    op.drop_table('documents')
    op.drop_table('document_rules')
    op.drop_table('document_types')
