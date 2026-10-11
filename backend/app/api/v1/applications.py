from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.database.session import get_db
from app.models.admission import AdmissionApplication
from app.models.student import Student
from app.models.user import User
from app.api.deps import get_current_student, get_current_user, require_roles
from app.services.application_service import ApplicationService
from app.services.checklist_service import ChecklistService
from app.schemas.application import (
    ApplicationDraftUpdate,
    ApplicationCompletionResponse,
    ApplicationDetailResponse,
    ApplicationSubmissionRequest,
    ApplicationSubmissionResponse,
    AdminApplicationListItem,
)
from app.schemas.document import ChecklistItemResponse
from app.schemas.reconciliation import CrossDocumentReconciliationResponse

router = APIRouter(prefix="/applications", tags=["Applications"])


def build_application_detail_response(
    app: AdmissionApplication,
    student: Student,
    checklist: List[ChecklistItemResponse]
) -> ApplicationDetailResponse:
    return ApplicationDetailResponse(
        id=app.id,
        application_number=app.application_number,
        student_id=student.id,
        status=app.status,
        completion_percentage=app.completion_percentage,
        student_name=student.full_name,
        student_dob=student.date_of_birth,
        student_email=student.email,
        student_mobile=student.mobile,
        tnea_application_number=student.tnea_application_number,
        allotted_branch=student.allotted_branch,
        community=student.community,
        quota=student.quota,
        allotment_order_number=app.allotment_order_number,
        allotment_quota=app.allotment_quota,
        allotted_category=app.allotted_category,
        allotted_college_code=app.allotted_college_code,
        allotted_branch_name=app.allotted_branch_name,
        gender=app.gender,
        blood_group=app.blood_group,
        nationality=app.nationality or "Indian",
        religion=app.religion,
        caste=app.caste,
        mother_tongue=app.mother_tongue,
        aadhaar_number=app.aadhaar_number,
        address_line1=app.address_line1,
        address_line2=app.address_line2,
        city=app.city,
        district=app.district,
        state=app.state or "Tamil Nadu",
        pincode=app.pincode,
        emergency_contact_name=app.emergency_contact_name,
        emergency_contact_phone=app.emergency_contact_phone,
        emergency_contact_relation=app.emergency_contact_relation,
        father_name=app.father_name,
        father_occupation=app.father_occupation,
        father_mobile=app.father_mobile,
        father_email=app.father_email,
        mother_name=app.mother_name,
        mother_occupation=app.mother_occupation,
        mother_mobile=app.mother_mobile,
        mother_email=app.mother_email,
        guardian_name=app.guardian_name,
        guardian_occupation=app.guardian_occupation,
        guardian_mobile=app.guardian_mobile,
        guardian_relation=app.guardian_relation,
        annual_family_income=app.annual_family_income,
        tenth_school_name=app.tenth_school_name,
        tenth_board=app.tenth_board,
        tenth_year_of_passing=app.tenth_year_of_passing,
        tenth_registration_number=app.tenth_registration_number,
        tenth_total_marks=app.tenth_total_marks,
        tenth_max_marks=app.tenth_max_marks,
        tenth_percentage=app.tenth_percentage,
        twelfth_school_name=app.twelfth_school_name,
        twelfth_board=app.twelfth_board,
        twelfth_year_of_passing=app.twelfth_year_of_passing,
        twelfth_registration_number=app.twelfth_registration_number,
        twelfth_total_marks=app.twelfth_total_marks,
        twelfth_max_marks=app.twelfth_max_marks,
        twelfth_percentage=app.twelfth_percentage,
        twelfth_maths_marks=app.twelfth_maths_marks,
        twelfth_physics_marks=app.twelfth_physics_marks,
        twelfth_chemistry_marks=app.twelfth_chemistry_marks,
        twelfth_cutoff_marks=app.twelfth_cutoff_marks,
        is_first_graduate=app.is_first_graduate,
        is_pmss_scholarship=app.is_pmss_scholarship,
        is_7_5_govt_quota=app.is_7_5_govt_quota,
        is_hostel_required=app.is_hostel_required,
        is_transport_required=app.is_transport_required,
        declaration_accepted=app.declaration_accepted,
        declaration_accepted_at=app.declaration_accepted_at,
        submitted_at=app.submitted_at,
        created_at=app.created_at,
        updated_at=app.updated_at,
        checklist=checklist,
    )


@router.get("/me", response_model=ApplicationDetailResponse)
async def get_my_application(
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns the student's admission application form details, along with dynamic checklist.
    """
    app = await ApplicationService.get_or_initialize_application(db, student)
    checklist = await ChecklistService.get_checklist_for_application(db, app, student)
    return build_application_detail_response(app, student, checklist)


@router.put("/me", response_model=ApplicationDetailResponse)
async def update_my_application_draft(
    draft: ApplicationDraftUpdate,
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db)
):
    """
    Auto-saves or updates the student's admission application form draft.
    """
    app = await ApplicationService.get_or_initialize_application(db, student)
    updated_app = await ApplicationService.update_draft(db, app, draft, student)
    checklist = await ChecklistService.get_checklist_for_application(db, updated_app, student)
    return build_application_detail_response(updated_app, student, checklist)


@router.get("/me/completion", response_model=ApplicationCompletionResponse)
async def get_my_application_completion(
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns field-level section completion, uploaded mandatory document status, and submission readiness.
    """
    app = await ApplicationService.get_or_initialize_application(db, student)
    return await ApplicationService.evaluate_completion(db, app, student)


@router.get("/me/checklist", response_model=List[ChecklistItemResponse])
async def get_my_checklist(
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns the dynamic document checklist tailored to the candidate's criteria.
    """
    app = await ApplicationService.get_or_initialize_application(db, student)
    return await ChecklistService.get_checklist_for_application(db, app, student)


@router.post("/me/submit", response_model=ApplicationSubmissionResponse)
async def submit_my_application(
    body: ApplicationSubmissionRequest,
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db)
):
    """
    Finalizes and submits the admission application with digitally signed declaration.
    Transitions status to APPLICATION_SUBMITTED.
    """
    app = await ApplicationService.get_or_initialize_application(db, student)
    submitted_app = await ApplicationService.submit_application(
        db, app, student, declaration_accepted=body.declaration_accepted
    )
    return ApplicationSubmissionResponse(
        admission_id=submitted_app.id,
        application_number=submitted_app.application_number or "",
        status=submitted_app.status,
        submitted_at=submitted_app.submitted_at or submitted_app.updated_at,
        message="Application submitted successfully. Your documents are queued for verification.",
    )


@router.get("/admin/list", response_model=List[AdminApplicationListItem])
async def list_applications_for_admin(
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_roles(["ADMIN_VERIFIER", "ADMISSION_HEAD", "SUPER_ADMIN", "FINANCE_OFFICER"]))
):
    """
    Administrative endpoint: Lists submitted/draft applications with search and filters.
    """
    stmt = (
        select(AdmissionApplication, Student)
        .join(Student, AdmissionApplication.student_id == Student.id)
        .order_by(AdmissionApplication.updated_at.desc())
    )

    if status_filter and status_filter.upper() != "ALL":
        stmt = stmt.where(AdmissionApplication.status == status_filter.upper())

    if search:
        term = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                Student.full_name.ilike(term),
                Student.tnea_application_number.ilike(term),
                AdmissionApplication.application_number.ilike(term),
                Student.email.ilike(term),
            )
        )

    res = await db.execute(stmt)
    rows = res.all()

    items: List[AdminApplicationListItem] = []
    for app_row, student_row in rows:
        items.append(
            AdminApplicationListItem(
                application_id=app_row.id,
                application_number=app_row.application_number,
                student_id=student_row.id,
                student_name=student_row.full_name,
                tnea_application_number=student_row.tnea_application_number,
                allotted_branch=student_row.allotted_branch,
                community=student_row.community,
                quota=student_row.quota,
                status=app_row.status,
                completion_percentage=app_row.completion_percentage,
                submitted_at=app_row.submitted_at,
                updated_at=app_row.updated_at,
            )
        )
    return items


@router.get("/admin/{application_id}", response_model=ApplicationDetailResponse)
async def get_application_detail_for_admin(
    application_id: str,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_roles(["ADMIN_VERIFIER", "ADMISSION_HEAD", "SUPER_ADMIN", "FINANCE_OFFICER"]))
):
    """
    Administrative endpoint: Detailed view of a specific student application.
    """
    stmt = (
        select(AdmissionApplication, Student)
        .join(Student, AdmissionApplication.student_id == Student.id)
        .where(AdmissionApplication.id == application_id)
    )
    res = await db.execute(stmt)
    row = res.first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    app, student = row
    checklist = await ChecklistService.get_checklist_for_application(db, app, student)
    return build_application_detail_response(app, student, checklist)


@router.post("/me/reconcile", response_model=CrossDocumentReconciliationResponse)
async def run_my_application_reconciliation(
    db: AsyncSession = Depends(get_db),
    student: Student = Depends(get_current_student),
):
    """
    Runs deterministic cross-document consistency reconciliation across the active student's
    uploaded documents, application draft, and stored TNEA allotment baseline record.
    Strictly read-only; does not modify application or document status.
    """
    from app.services.cross_document_reconciliation_service import CrossDocumentReconciliationService
    
    app_obj = await ApplicationService.get_or_initialize_application(db, student)
    service = CrossDocumentReconciliationService()
    try:
        recon = await service.run_reconciliation(db, app_obj.id)
        return recon
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Reconciliation failed: {str(e)}",
        )


@router.get("/me/reconciliation", response_model=Optional[CrossDocumentReconciliationResponse])
async def get_my_application_reconciliation(
    db: AsyncSession = Depends(get_db),
    student: Student = Depends(get_current_student),
):
    """
    Retrieves the latest cross-document consistency reconciliation snapshot for the student.
    """
    from app.services.cross_document_reconciliation_service import CrossDocumentReconciliationService
    
    app_obj = await ApplicationService.get_or_initialize_application(db, student)
    service = CrossDocumentReconciliationService()
    recon = await service.get_latest_reconciliation(db, app_obj.id)
    if not recon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No reconciliation snapshot found for this application. Please run reconciliation first.",
        )
    return recon

