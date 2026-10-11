from datetime import date
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.models.user import User
from app.models.student import Student
from app.api.deps import get_current_user, get_current_student, require_roles
from app.services.physical_verification_service import PhysicalVerificationService
from app.schemas.physical_verification import (
    AppointmentCreateRequest,
    AppointmentRescheduleRequest,
    AppointmentResponse,
    AvailableSlotResponse,
    CheckInRequest,
    CheckInResponse,
    DocumentVerifyRequest,
    DocumentCorrectionRequest,
    SessionStartRequest,
    SessionCompleteRequest,
    SessionReopenRequest,
    PhysicalDocumentVerificationResponse,
    PhysicalSessionResponse,
    PhysicalVerificationAuditResponse,
)

router = APIRouter(prefix="/physical-verification", tags=["Physical Verification & Appointments"])

admin_staff_check = require_roles(["ADMIN_VERIFIER", "ADMISSION_HEAD", "SUPER_ADMIN"])
lead_admin_check = require_roles(["ADMISSION_HEAD", "SUPER_ADMIN"])


def build_session_response(session) -> PhysicalSessionResponse:
    doc_verifications = []
    if session.document_verifications:
        for dv in session.document_verifications:
            v_num = dv.document_version.version_number if dv.document_version else None
            dt_code = dv.document_type.code if dv.document_type else ""
            dt_name = dv.document_type.name if dv.document_type else ""
            officer_name = dv.verified_by.email if dv.verified_by else None

            doc_verifications.append(
                PhysicalDocumentVerificationResponse(
                    id=dv.id,
                    session_id=dv.session_id,
                    document_id=dv.document_id,
                    document_version_id=dv.document_version_id,
                    document_type_id=dv.document_type_id,
                    document_type_code=dt_code,
                    document_type_name=dt_name,
                    version_number=v_num,
                    officer_decision=dv.officer_decision,
                    verification_notes=dv.verification_notes,
                    discrepancy_reason=dv.discrepancy_reason,
                    checklist_checks=dv.checklist_checks or {},
                    verified_by_id=dv.verified_by_id,
                    verified_by_name=officer_name,
                    verified_at=dv.verified_at,
                    created_at=dv.created_at,
                    updated_at=dv.updated_at,
                )
            )

    return PhysicalSessionResponse(
        id=session.id,
        application_id=session.application_id,
        appointment_id=session.appointment_id,
        officer_id=session.officer_id,
        officer_name=session.officer.email if session.officer else None,
        started_at=session.started_at,
        completed_at=session.completed_at,
        session_status=session.session_status,
        overall_decision=session.overall_decision,
        officer_notes=session.officer_notes,
        created_at=session.created_at,
        updated_at=session.updated_at,
        document_verifications=doc_verifications,
    )


# ==========================================
# Student Appointment & Status Endpoints
# ==========================================

@router.get("/slots", response_model=List[AvailableSlotResponse])
async def get_slots(
    slot_date: Optional[date] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns available physical verification appointment slots for a specific date (defaults to today).
    """
    target_date = slot_date or date.today()
    return await PhysicalVerificationService.get_available_slots(db, target_date)


@router.post("/appointments", response_model=AppointmentResponse)
async def create_appointment(
    payload: AppointmentCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Candidate schedules their physical verification appointment slot.
    """
    apt = await PhysicalVerificationService.create_appointment(db, current_user, payload)
    return apt


@router.get("/appointments/me", response_model=Optional[AppointmentResponse])
async def get_my_appointment(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Anti-IDOR: Retrieves current physical verification appointment for authenticated candidate.
    """
    return await PhysicalVerificationService.get_student_appointment(db, current_user)


@router.post("/appointments/{appointment_id}/confirm", response_model=AppointmentResponse)
async def confirm_appointment(
    appointment_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Candidate confirms their physical verification appointment slot.
    """
    return await PhysicalVerificationService.confirm_appointment(db, appointment_id, current_user)


@router.post("/appointments/{appointment_id}/reschedule", response_model=AppointmentResponse)
async def reschedule_appointment(
    appointment_id: str,
    payload: AppointmentRescheduleRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Reschedules an existing appointment slot.
    """
    return await PhysicalVerificationService.reschedule_appointment(db, appointment_id, payload, current_user)


@router.post("/appointments/{appointment_id}/cancel", response_model=AppointmentResponse)
async def cancel_appointment(
    appointment_id: str,
    reason: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Cancels an existing appointment.
    """
    return await PhysicalVerificationService.cancel_appointment(db, appointment_id, current_user, reason)


@router.get("/me/summary")
async def get_student_summary(
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """
    Candidate dashboard summary of physical verification status and correction instructions.
    """
    return await PhysicalVerificationService.get_student_physical_verification_summary(db, student)


# ==========================================
# Admin Physical Verification Desk Endpoints
# ==========================================

@router.get("/admin/appointments", response_model=List[AppointmentResponse], dependencies=[Depends(admin_staff_check)])
async def admin_list_appointments(
    appointment_date: Optional[date] = Query(default=None),
    status_filter: Optional[str] = Query(default=None),
    search_query: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """
    Admin: Lists physical verification appointments with search and status filters.
    """
    return await PhysicalVerificationService.admin_list_appointments(
        db, appointment_date, status_filter, search_query
    )


@router.post("/admin/check-in", response_model=CheckInResponse, dependencies=[Depends(admin_staff_check)])
async def check_in_student(
    payload: CheckInRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Admin: Checks in a candidate at the central admission hall desk using Token Number or QR check-in code.
    """
    return await PhysicalVerificationService.check_in_student(db, payload, current_user)


@router.post(
    "/admin/applications/{application_id}/sessions/start",
    response_model=PhysicalSessionResponse,
    dependencies=[Depends(admin_staff_check)],
)
async def start_session(
    application_id: str,
    payload: SessionStartRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Admin: Initiates on-site physical document verification session for an application.
    """
    session = await PhysicalVerificationService.start_verification_session(db, application_id, payload, current_user)
    return build_session_response(session)


@router.get(
    "/admin/sessions/{session_id}",
    response_model=PhysicalSessionResponse,
    dependencies=[Depends(admin_staff_check)],
)
async def get_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Admin: Retrieves full physical verification session with document inspection items.
    """
    session = await PhysicalVerificationService.get_session_by_id(db, session_id, current_user)
    return build_session_response(session)


@router.post(
    "/admin/sessions/{session_id}/documents/{document_id}/verify",
    response_model=PhysicalDocumentVerificationResponse,
    dependencies=[Depends(admin_staff_check)],
)
async def verify_document(
    session_id: str,
    document_id: str,
    payload: DocumentVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Admin: Records officer physical inspection findings on a specific document.
    """
    item = await PhysicalVerificationService.verify_physical_document(
        db, session_id, document_id, payload, current_user
    )
    v_num = item.document_version.version_number if item.document_version else None
    dt_code = item.document_type.code if item.document_type else ""
    dt_name = item.document_type.name if item.document_type else ""
    officer_name = item.verified_by.email if item.verified_by else None

    return PhysicalDocumentVerificationResponse(
        id=item.id,
        session_id=item.session_id,
        document_id=item.document_id,
        document_version_id=item.document_version_id,
        document_type_id=item.document_type_id,
        document_type_code=dt_code,
        document_type_name=dt_name,
        version_number=v_num,
        officer_decision=item.officer_decision,
        verification_notes=item.verification_notes,
        discrepancy_reason=item.discrepancy_reason,
        checklist_checks=item.checklist_checks or {},
        verified_by_id=item.verified_by_id,
        verified_by_name=officer_name,
        verified_at=item.verified_at,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.post(
    "/admin/sessions/{session_id}/documents/{document_id}/correction",
    response_model=PhysicalDocumentVerificationResponse,
    dependencies=[Depends(admin_staff_check)],
)
async def request_physical_correction(
    session_id: str,
    document_id: str,
    payload: DocumentCorrectionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Admin: Requests physical correction/resubmission for an original document.
    """
    item = await PhysicalVerificationService.request_physical_correction(
        db, session_id, document_id, payload, current_user
    )
    v_num = item.document_version.version_number if item.document_version else None
    dt_code = item.document_type.code if item.document_type else ""
    dt_name = item.document_type.name if item.document_type else ""
    officer_name = item.verified_by.email if item.verified_by else None

    return PhysicalDocumentVerificationResponse(
        id=item.id,
        session_id=item.session_id,
        document_id=item.document_id,
        document_version_id=item.document_version_id,
        document_type_id=item.document_type_id,
        document_type_code=dt_code,
        document_type_name=dt_name,
        version_number=v_num,
        officer_decision=item.officer_decision,
        verification_notes=item.verification_notes,
        discrepancy_reason=item.discrepancy_reason,
        checklist_checks=item.checklist_checks or {},
        verified_by_id=item.verified_by_id,
        verified_by_name=officer_name,
        verified_at=item.verified_at,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.post(
    "/admin/sessions/{session_id}/complete",
    response_model=PhysicalSessionResponse,
    dependencies=[Depends(admin_staff_check)],
)
async def complete_session(
    session_id: str,
    payload: SessionCompleteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Admin: Finalizes physical verification session with overall officer determination.
    Strict Non-Mutation: Does NOT modify AdmissionApplication.status or Document.status.
    """
    session = await PhysicalVerificationService.complete_session(db, session_id, payload, current_user)
    return build_session_response(session)


@router.post(
    "/admin/sessions/{session_id}/reopen",
    response_model=PhysicalSessionResponse,
    dependencies=[Depends(lead_admin_check)],
)
async def reopen_session(
    session_id: str,
    payload: SessionReopenRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Admin: Reopens a finalized physical verification session. Gated to ADMISSION_HEAD and SUPER_ADMIN.
    """
    session = await PhysicalVerificationService.reopen_session(db, session_id, payload, current_user)
    return build_session_response(session)


@router.get(
    "/admin/sessions/{session_id}/audit-logs",
    response_model=List[PhysicalVerificationAuditResponse],
    dependencies=[Depends(admin_staff_check)],
)
async def get_session_audit_logs(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Admin: Returns append-only audit trail for physical verification session.
    """
    return await PhysicalVerificationService.get_session_audit_logs(db, session_id, current_user)
