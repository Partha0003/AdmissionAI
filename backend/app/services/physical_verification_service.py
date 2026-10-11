import uuid
from datetime import datetime, timezone, date, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, and_, or_
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status

from app.models.user import User
from app.models.student import Student
from app.models.admission import AdmissionApplication
from app.models.document import Document, DocumentVersion, DocumentType
from app.models.scrutiny import AdmissionReview
from app.models.document_processing import CrossDocumentReconciliation
from app.models.physical_verification import (
    AppointmentStatus,
    PhysicalSessionStatus,
    PhysicalVerificationDecision,
    PhysicalDocDecision,
    PhysicalCorrectionReason,
    PhysicalVerificationAction,
    PhysicalVerificationAppointment,
    PhysicalVerificationSession,
    PhysicalDocumentVerification,
    PhysicalVerificationAuditLog,
)
from app.schemas.physical_verification import (
    AppointmentCreateRequest,
    AppointmentRescheduleRequest,
    CheckInRequest,
    CheckInResponse,
    DocumentVerifyRequest,
    DocumentCorrectionRequest,
    SessionStartRequest,
    SessionCompleteRequest,
    SessionReopenRequest,
    AvailableSlotResponse,
)


class PhysicalVerificationService:
    """
    Phase 5 Service: Physical / On-Site Verification Workflow.
    Manages appointment scheduling, check-in, original document verification checklists,
    officer decision recording, and complete audit trail.

    Strict Non-Mutation Rule:
    Does NOT modify AdmissionApplication.status, Document.status, Student, or TNEAAllotment.
    All physical outcomes remain in the physical verification domain.
    """

    @classmethod
    async def generate_token_number(cls, db: AsyncSession, app_date: date) -> str:
        """
        Generates a unique, non-sequential public token for the appointment date.
        Format: PV-YYYYMMDD-XXX
        """
        date_prefix = app_date.strftime("%Y%m%d")
        stmt = (
            select(func.count(PhysicalVerificationAppointment.id))
            .where(PhysicalVerificationAppointment.appointment_date == app_date)
        )
        res = await db.execute(stmt)
        count = res.scalar() or 0
        seq = count + 1
        return f"PV-{date_prefix}-{seq:03d}"

    @classmethod
    async def get_available_slots(cls, db: AsyncSession, app_date: date) -> List[AvailableSlotResponse]:
        """
        Returns configured appointment slots for a given date with availability metrics.
        """
        standard_slots = [
            ("09:00 AM", "09:30 AM", 15),
            ("09:30 AM", "10:00 AM", 15),
            ("10:00 AM", "10:30 AM", 15),
            ("10:30 AM", "11:00 AM", 15),
            ("11:30 AM", "12:00 PM", 15),
            ("12:00 PM", "12:30 PM", 15),
            ("02:00 PM", "02:30 PM", 15),
            ("02:30 PM", "03:00 PM", 15),
            ("03:00 PM", "03:30 PM", 15),
            ("03:30 PM", "04:00 PM", 15),
        ]

        # Query existing bookings on this date
        stmt = (
            select(
                PhysicalVerificationAppointment.start_time,
                func.count(PhysicalVerificationAppointment.id)
            )
            .where(
                PhysicalVerificationAppointment.appointment_date == app_date,
                PhysicalVerificationAppointment.appointment_status.in_([
                    AppointmentStatus.SCHEDULED.value,
                    AppointmentStatus.CONFIRMED.value,
                    AppointmentStatus.CHECKED_IN.value,
                    AppointmentStatus.IN_PROGRESS.value,
                ])
            )
            .group_by(PhysicalVerificationAppointment.start_time)
        )
        res = await db.execute(stmt)
        booked_counts = dict(res.all())

        results = []
        for start, end, cap in standard_slots:
            booked = booked_counts.get(start, 0)
            avail = max(0, cap - booked)
            results.append(
                AvailableSlotResponse(
                    slot_date=app_date,
                    start_time=start,
                    end_time=end,
                    available_capacity=avail,
                    location="XYZ Main Campus — Central Admission Hall",
                    counter_desk="Verification Desk 1",
                )
            )
        return results

    @classmethod
    async def create_appointment(
        cls,
        db: AsyncSession,
        student_user: User,
        payload: AppointmentCreateRequest,
    ) -> PhysicalVerificationAppointment:
        """
        Student schedules a physical verification appointment slot.
        """
        # Find student application
        app_stmt = (
            select(AdmissionApplication)
            .join(Student, AdmissionApplication.student_id == Student.id)
            .where(Student.user_id == student_user.id)
        )
        app_res = await db.execute(app_stmt)
        app = app_res.scalar_one_or_none()
        if not app:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Admission application not found for authenticated student"
            )

        # Check existing active appointment
        existing_stmt = (
            select(PhysicalVerificationAppointment)
            .where(
                PhysicalVerificationAppointment.application_id == app.id,
                PhysicalVerificationAppointment.appointment_status.in_([
                    AppointmentStatus.SCHEDULED.value,
                    AppointmentStatus.CONFIRMED.value,
                    AppointmentStatus.CHECKED_IN.value,
                    AppointmentStatus.IN_PROGRESS.value,
                ])
            )
        )
        existing_res = await db.execute(existing_stmt)
        existing = existing_res.scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"An active appointment ({existing.token_number}) is already scheduled. Please reschedule instead."
            )

        token_number = await cls.generate_token_number(db, payload.appointment_date)
        checkin_token = uuid.uuid4().hex

        appointment = PhysicalVerificationAppointment(
            application_id=app.id,
            appointment_date=payload.appointment_date,
            start_time=payload.start_time,
            end_time=payload.end_time,
            token_number=token_number,
            checkin_token=checkin_token,
            location=payload.location or "XYZ Main Campus — Central Admission Hall",
            counter_desk=payload.counter_desk or "Verification Desk 1",
            appointment_status=AppointmentStatus.SCHEDULED.value,
            notes=payload.notes,
            created_by_id=student_user.id,
        )
        db.add(appointment)

        # Audit Log
        audit = PhysicalVerificationAuditLog(
            application_id=app.id,
            appointment_id=appointment.id,
            actor_id=student_user.id,
            actor_name=student_user.email,
            actor_role=student_user.role.name if student_user.role else "STUDENT",
            action=PhysicalVerificationAction.APPOINTMENT_CREATED.value,
            details={
                "appointment_date": str(payload.appointment_date),
                "start_time": payload.start_time,
                "end_time": payload.end_time,
                "token_number": token_number,
            },
        )
        db.add(audit)

        await db.commit()
        await db.refresh(appointment)
        return appointment

    @classmethod
    async def get_student_appointment(
        cls,
        db: AsyncSession,
        student_user: User,
    ) -> Optional[PhysicalVerificationAppointment]:
        """
        Anti-IDOR: Retrieves current appointment for the authenticated student.
        """
        app_stmt = (
            select(AdmissionApplication)
            .join(Student, AdmissionApplication.student_id == Student.id)
            .where(Student.user_id == student_user.id)
        )
        app_res = await db.execute(app_stmt)
        app = app_res.scalar_one_or_none()
        if not app:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Admission application not found"
            )

        stmt = (
            select(PhysicalVerificationAppointment)
            .where(PhysicalVerificationAppointment.application_id == app.id)
            .order_by(desc(PhysicalVerificationAppointment.created_at))
        )
        res = await db.execute(stmt)
        return res.scalars().first()

    @classmethod
    async def confirm_appointment(
        cls,
        db: AsyncSession,
        appointment_id: str,
        student_user: User,
    ) -> PhysicalVerificationAppointment:
        """
        Student confirms their scheduled appointment.
        """
        stmt = (
            select(PhysicalVerificationAppointment)
            .where(PhysicalVerificationAppointment.id == appointment_id)
            .options(selectinload(PhysicalVerificationAppointment.application).selectinload(AdmissionApplication.student))
        )
        res = await db.execute(stmt)
        apt = res.scalar_one_or_none()
        if not apt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Appointment '{appointment_id}' not found"
            )

        # Anti-IDOR Check
        role_name = student_user.role.name if student_user.role else "STUDENT"
        if role_name == "STUDENT":
            if not apt.application or not apt.application.student or apt.application.student.user_id != student_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access forbidden: You cannot confirm another student's appointment"
                )

        apt.appointment_status = AppointmentStatus.CONFIRMED.value
        apt.updated_at = datetime.now(timezone.utc)

        audit = PhysicalVerificationAuditLog(
            application_id=apt.application_id,
            appointment_id=apt.id,
            actor_id=student_user.id,
            actor_name=student_user.email,
            actor_role=role_name,
            action=PhysicalVerificationAction.APPOINTMENT_CONFIRMED.value,
            details={"token_number": apt.token_number},
        )
        db.add(audit)

        await db.commit()
        await db.refresh(apt)
        return apt

    @classmethod
    async def reschedule_appointment(
        cls,
        db: AsyncSession,
        appointment_id: str,
        payload: AppointmentRescheduleRequest,
        current_user: User,
    ) -> PhysicalVerificationAppointment:
        """
        Reschedules an existing appointment slot.
        """
        stmt = (
            select(PhysicalVerificationAppointment)
            .where(PhysicalVerificationAppointment.id == appointment_id)
            .options(selectinload(PhysicalVerificationAppointment.application).selectinload(AdmissionApplication.student))
        )
        res = await db.execute(stmt)
        apt = res.scalar_one_or_none()
        if not apt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Appointment '{appointment_id}' not found"
            )

        role_name = current_user.role.name if current_user.role else "STUDENT"
        if role_name == "STUDENT":
            if not apt.application or not apt.application.student or apt.application.student.user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access forbidden: You cannot reschedule another student's appointment"
                )

        old_date = str(apt.appointment_date)
        old_start = apt.start_time

        apt.appointment_date = payload.appointment_date
        apt.start_time = payload.start_time
        apt.end_time = payload.end_time
        apt.appointment_status = AppointmentStatus.RESCHEDULED.value
        apt.updated_at = datetime.now(timezone.utc)

        audit = PhysicalVerificationAuditLog(
            application_id=apt.application_id,
            appointment_id=apt.id,
            actor_id=current_user.id,
            actor_name=current_user.email,
            actor_role=role_name,
            action=PhysicalVerificationAction.APPOINTMENT_RESCHEDULED.value,
            details={
                "previous": {"date": old_date, "start": old_start},
                "new": {"date": str(payload.appointment_date), "start": payload.start_time, "end": payload.end_time},
                "reason": payload.reason,
            },
        )
        db.add(audit)

        await db.commit()
        await db.refresh(apt)
        return apt

    @classmethod
    async def cancel_appointment(
        cls,
        db: AsyncSession,
        appointment_id: str,
        current_user: User,
        reason: Optional[str] = None,
    ) -> PhysicalVerificationAppointment:
        """
        Cancels an appointment.
        """
        stmt = (
            select(PhysicalVerificationAppointment)
            .where(PhysicalVerificationAppointment.id == appointment_id)
            .options(selectinload(PhysicalVerificationAppointment.application).selectinload(AdmissionApplication.student))
        )
        res = await db.execute(stmt)
        apt = res.scalar_one_or_none()
        if not apt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Appointment '{appointment_id}' not found"
            )

        role_name = current_user.role.name if current_user.role else "STUDENT"
        if role_name == "STUDENT":
            if not apt.application or not apt.application.student or apt.application.student.user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access forbidden: You cannot cancel another student's appointment"
                )

        apt.appointment_status = AppointmentStatus.CANCELLED.value
        apt.updated_at = datetime.now(timezone.utc)

        audit = PhysicalVerificationAuditLog(
            application_id=apt.application_id,
            appointment_id=apt.id,
            actor_id=current_user.id,
            actor_name=current_user.email,
            actor_role=role_name,
            action=PhysicalVerificationAction.APPOINTMENT_CANCELLED.value,
            details={"reason": reason},
        )
        db.add(audit)

        await db.commit()
        await db.refresh(apt)
        return apt

    @classmethod
    async def check_in_student(
        cls,
        db: AsyncSession,
        payload: CheckInRequest,
        officer_user: User,
    ) -> CheckInResponse:
        """
        On-site officer checks in a student using Token Number or Secure Check-In Code.
        Prevents duplicate check-ins.
        """
        if not payload.token_number and not payload.checkin_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either token_number or checkin_token must be provided for check-in"
            )

        query = (
            select(PhysicalVerificationAppointment)
            .options(
                selectinload(PhysicalVerificationAppointment.application).selectinload(AdmissionApplication.student),
            )
        )
        if payload.token_number:
            query = query.where(PhysicalVerificationAppointment.token_number == payload.token_number.strip().upper())
        elif payload.checkin_token:
            query = query.where(PhysicalVerificationAppointment.checkin_token == payload.checkin_token.strip())

        res = await db.execute(query)
        apt = res.scalar_one_or_none()
        if not apt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Appointment not found with provided token credentials"
            )

        candidate_name = apt.application.student.full_name if apt.application and apt.application.student else "Candidate"
        branch = apt.application.student.allotted_branch if apt.application and apt.application.student else None

        # Duplicate Check-in Guard
        if apt.appointment_status in [AppointmentStatus.CHECKED_IN.value, AppointmentStatus.IN_PROGRESS.value, AppointmentStatus.COMPLETED.value]:
            if apt.appointment_status == AppointmentStatus.COMPLETED.value:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"This appointment ({apt.token_number}) has already been completed."
                )
            # If already checked in, return details smoothly
            return CheckInResponse(
                message=f"Candidate {candidate_name} is already checked in at {apt.counter_desk}",
                appointment_id=apt.id,
                token_number=apt.token_number,
                application_id=apt.application_id,
                candidate_name=candidate_name,
                allotted_branch=branch,
                checked_in_at=apt.checked_in_at or datetime.now(timezone.utc),
                counter_desk=apt.counter_desk,
            )

        now = datetime.now(timezone.utc)
        apt.appointment_status = AppointmentStatus.CHECKED_IN.value
        apt.checked_in_at = now
        if payload.counter_desk:
            apt.counter_desk = payload.counter_desk
        apt.updated_at = now

        role_name = officer_user.role.name if officer_user.role else "ADMIN_VERIFIER"
        audit = PhysicalVerificationAuditLog(
            application_id=apt.application_id,
            appointment_id=apt.id,
            actor_id=officer_user.id,
            actor_name=officer_user.email,
            actor_role=role_name,
            action=PhysicalVerificationAction.STUDENT_CHECKED_IN.value,
            details={
                "token_number": apt.token_number,
                "counter_desk": apt.counter_desk,
                "checked_in_at": now.isoformat(),
            },
        )
        db.add(audit)

        await db.commit()
        await db.refresh(apt)

        candidate_name = apt.application.student.full_name if apt.application and apt.application.student else "Candidate"
        branch = apt.application.student.allotted_branch if apt.application and apt.application.student else None

        return CheckInResponse(
            message=f"Successfully checked in candidate {candidate_name}",
            appointment_id=apt.id,
            token_number=apt.token_number,
            application_id=apt.application_id,
            candidate_name=candidate_name,
            allotted_branch=branch,
            checked_in_at=now,
            counter_desk=apt.counter_desk,
        )

    @classmethod
    async def start_verification_session(
        cls,
        db: AsyncSession,
        application_id: str,
        payload: SessionStartRequest,
        officer_user: User,
    ) -> PhysicalVerificationSession:
        """
        Officer starts an on-site physical document verification session for an application.
        Pre-populates document checklist items pointing to the exact latest submitted document versions.
        """
        app_stmt = (
            select(AdmissionApplication)
            .where(AdmissionApplication.id == application_id)
            .options(
                selectinload(AdmissionApplication.documents).selectinload(Document.versions),
                selectinload(AdmissionApplication.documents).selectinload(Document.document_type),
            )
        )
        app_res = await db.execute(app_stmt)
        app = app_res.scalar_one_or_none()
        if not app:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Admission application '{application_id}' not found"
            )

        now = datetime.now(timezone.utc)
        appointment_id = payload.appointment_id

        # If appointment_id is not given, find active appointment for app
        if not appointment_id:
            apt_stmt = (
                select(PhysicalVerificationAppointment)
                .where(
                    PhysicalVerificationAppointment.application_id == application_id,
                    PhysicalVerificationAppointment.appointment_status.in_([
                        AppointmentStatus.CHECKED_IN.value,
                        AppointmentStatus.CONFIRMED.value,
                        AppointmentStatus.SCHEDULED.value,
                    ])
                )
                .order_by(desc(PhysicalVerificationAppointment.created_at))
            )
            apt_res = await db.execute(apt_stmt)
            apt = apt_res.scalars().first()
            if apt:
                appointment_id = apt.id
                apt.appointment_status = AppointmentStatus.IN_PROGRESS.value
                if payload.counter_desk:
                    apt.counter_desk = payload.counter_desk
                apt.updated_at = now

        # Create new PhysicalVerificationSession
        session = PhysicalVerificationSession(
            application_id=application_id,
            appointment_id=appointment_id,
            officer_id=officer_user.id,
            started_at=now,
            session_status=PhysicalSessionStatus.IN_PROGRESS.value,
            overall_decision=PhysicalVerificationDecision.PENDING.value,
            officer_notes=payload.officer_notes,
        )
        db.add(session)
        await db.flush()

        # Seed PhysicalDocumentVerification items for each document in the application
        if app.documents:
            for doc in app.documents:
                # Find current version
                current_ver_id = doc.current_version_id
                if not current_ver_id and doc.versions:
                    current_ver_id = doc.versions[0].id

                doc_ver_item = PhysicalDocumentVerification(
                    session_id=session.id,
                    document_id=doc.id,
                    document_version_id=current_ver_id,
                    document_type_id=doc.document_type_id,
                    officer_decision=PhysicalDocDecision.PENDING.value,
                    checklist_checks={
                        "original_presented": False,
                        "document_legible": True,
                        "name_matches": True,
                        "dob_matches": True,
                        "id_matches": True,
                        "photo_check_done": True,
                    },
                )
                db.add(doc_ver_item)

        role_name = officer_user.role.name if officer_user.role else "ADMIN_VERIFIER"
        audit = PhysicalVerificationAuditLog(
            application_id=application_id,
            appointment_id=appointment_id,
            session_id=session.id,
            actor_id=officer_user.id,
            actor_name=officer_user.email,
            actor_role=role_name,
            action=PhysicalVerificationAction.SESSION_STARTED.value,
            details={
                "appointment_id": appointment_id,
                "notes": payload.officer_notes,
            },
        )
        db.add(audit)

        await db.commit()
        return await cls.get_session_by_id(db, session.id)

    @classmethod
    async def get_session_by_id(
        cls,
        db: AsyncSession,
        session_id: str,
        current_user: Optional[User] = None,
    ) -> PhysicalVerificationSession:
        """
        Retrieves a physical verification session with document verification records.
        """
        stmt = (
            select(PhysicalVerificationSession)
            .where(PhysicalVerificationSession.id == session_id)
            .options(
                selectinload(PhysicalVerificationSession.application).selectinload(AdmissionApplication.student),
                selectinload(PhysicalVerificationSession.appointment),
                selectinload(PhysicalVerificationSession.officer),
                selectinload(PhysicalVerificationSession.document_verifications).selectinload(PhysicalDocumentVerification.document),
                selectinload(PhysicalVerificationSession.document_verifications).selectinload(PhysicalDocumentVerification.document_version),
                selectinload(PhysicalVerificationSession.document_verifications).selectinload(PhysicalDocumentVerification.document_type),
                selectinload(PhysicalVerificationSession.document_verifications).selectinload(PhysicalDocumentVerification.verified_by),
            )
        )
        res = await db.execute(stmt)
        session = res.scalar_one_or_none()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Physical verification session '{session_id}' not found"
            )

        if current_user:
            role_name = current_user.role.name if current_user.role else "STUDENT"
            if role_name == "STUDENT":
                if not session.application or not session.application.student or session.application.student.user_id != current_user.id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access forbidden: You cannot view another student's verification session"
                    )

        return session

    @classmethod
    async def verify_physical_document(
        cls,
        db: AsyncSession,
        session_id: str,
        document_id: str,
        payload: DocumentVerifyRequest,
        officer_user: User,
    ) -> PhysicalDocumentVerification:
        """
        Officer records physical verification findings on a specific original document.
        Does NOT alter Document.status or AdmissionApplication.status.
        """
        session = await cls.get_session_by_id(db, session_id)
        if session.session_status == PhysicalSessionStatus.COMPLETED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot modify a completed verification session. Please reopen the session if changes are required."
            )

        # Check existing item
        item_stmt = (
            select(PhysicalDocumentVerification)
            .where(
                PhysicalDocumentVerification.session_id == session_id,
                PhysicalDocumentVerification.document_id == document_id,
            )
            .options(
                selectinload(PhysicalDocumentVerification.document_version),
                selectinload(PhysicalDocumentVerification.document_type),
            )
        )
        item_res = await db.execute(item_stmt)
        item = item_res.scalar_one_or_none()

        now = datetime.now(timezone.utc)

        if not item:
            # Look up document
            doc_stmt = (
                select(Document)
                .where(Document.id == document_id)
                .options(selectinload(Document.versions))
            )
            doc_res = await db.execute(doc_stmt)
            doc = doc_res.scalar_one_or_none()
            if not doc:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Document '{document_id}' not found"
                )

            current_ver_id = doc.current_version_id
            if not current_ver_id and doc.versions:
                current_ver_id = doc.versions[0].id

            item = PhysicalDocumentVerification(
                session_id=session_id,
                document_id=document_id,
                document_version_id=current_ver_id,
                document_type_id=doc.document_type_id,
                officer_decision=payload.officer_decision,
                verification_notes=payload.verification_notes,
                discrepancy_reason=payload.discrepancy_reason,
                checklist_checks=payload.checklist_checks or {},
                verified_by_id=officer_user.id,
                verified_at=now,
            )
            db.add(item)
        else:
            item.officer_decision = payload.officer_decision
            item.verification_notes = payload.verification_notes
            item.discrepancy_reason = payload.discrepancy_reason
            if payload.checklist_checks is not None:
                item.checklist_checks = payload.checklist_checks
            item.verified_by_id = officer_user.id
            item.verified_at = now
            item.updated_at = now

        role_name = officer_user.role.name if officer_user.role else "ADMIN_VERIFIER"
        action = (
            PhysicalVerificationAction.DOCUMENT_VERIFIED.value
            if payload.officer_decision == PhysicalDocDecision.VERIFIED.value
            else PhysicalVerificationAction.DOCUMENT_NOT_VERIFIED.value
        )
        audit = PhysicalVerificationAuditLog(
            application_id=session.application_id,
            appointment_id=session.appointment_id,
            session_id=session.id,
            actor_id=officer_user.id,
            actor_name=officer_user.email,
            actor_role=role_name,
            action=action,
            details={
                "document_id": document_id,
                "document_version_id": item.document_version_id,
                "decision": payload.officer_decision,
                "notes": payload.verification_notes,
                "discrepancy_reason": payload.discrepancy_reason,
            },
        )
        db.add(audit)

        await db.commit()
        await db.refresh(item)
        return item

    @classmethod
    async def request_physical_correction(
        cls,
        db: AsyncSession,
        session_id: str,
        document_id: str,
        payload: DocumentCorrectionRequest,
        officer_user: User,
    ) -> PhysicalDocumentVerification:
        """
        Officer flags an on-site physical document as requiring correction/resubmission.
        Mandates structured discrepancy reason. If OTHER, requires explanatory notes.
        """
        if not payload.discrepancy_reason or not payload.discrepancy_reason.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Discrepancy reason is mandatory"
            )

        if payload.discrepancy_reason.upper() == PhysicalCorrectionReason.OTHER.value and (
            not payload.verification_notes or not payload.verification_notes.strip()
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Explanatory notes are required when discrepancy reason is 'OTHER'"
            )

        verify_payload = DocumentVerifyRequest(
            officer_decision=PhysicalDocDecision.CORRECTION_REQUIRED.value,
            verification_notes=payload.verification_notes,
            discrepancy_reason=payload.discrepancy_reason,
            checklist_checks=payload.checklist_checks,
        )
        return await cls.verify_physical_document(db, session_id, document_id, verify_payload, officer_user)

    @classmethod
    async def complete_session(
        cls,
        db: AsyncSession,
        session_id: str,
        payload: SessionCompleteRequest,
        officer_user: User,
    ) -> PhysicalVerificationSession:
        """
        Finalizes physical verification session.
        Records human officer determination (VERIFIED, PARTIALLY_VERIFIED, CORRECTION_REQUIRED, REJECTED, PENDING).
        Strict Non-Mutation: Does NOT modify AdmissionApplication.status or Document.status.
        """
        session = await cls.get_session_by_id(db, session_id)
        if session.session_status == PhysicalSessionStatus.COMPLETED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Physical verification session is already completed."
            )

        valid_decisions = {
            PhysicalVerificationDecision.VERIFIED.value,
            PhysicalVerificationDecision.PARTIALLY_VERIFIED.value,
            PhysicalVerificationDecision.CORRECTION_REQUIRED.value,
            PhysicalVerificationDecision.REJECTED.value,
            PhysicalVerificationDecision.PENDING.value,
        }
        dec = payload.overall_decision.upper()
        if dec not in valid_decisions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid decision '{payload.overall_decision}'. Allowed: {valid_decisions}"
            )

        now = datetime.now(timezone.utc)
        session.session_status = PhysicalSessionStatus.COMPLETED.value
        session.overall_decision = dec
        session.officer_notes = payload.officer_notes
        session.completed_at = now
        session.updated_at = now

        # Update appointment status if linked
        if session.appointment_id:
            apt_stmt = select(PhysicalVerificationAppointment).where(PhysicalVerificationAppointment.id == session.appointment_id)
            apt_res = await db.execute(apt_stmt)
            apt = apt_res.scalar_one_or_none()
            if apt:
                apt.appointment_status = AppointmentStatus.COMPLETED.value
                apt.updated_at = now

        role_name = officer_user.role.name if officer_user.role else "ADMIN_VERIFIER"
        audit = PhysicalVerificationAuditLog(
            application_id=session.application_id,
            appointment_id=session.appointment_id,
            session_id=session.id,
            actor_id=officer_user.id,
            actor_name=officer_user.email,
            actor_role=role_name,
            action=PhysicalVerificationAction.SESSION_COMPLETED.value,
            details={
                "overall_decision": dec,
                "notes": payload.officer_notes,
            },
        )
        db.add(audit)

        await db.commit()
        return await cls.get_session_by_id(db, session_id)

    @classmethod
    async def reopen_session(
        cls,
        db: AsyncSession,
        session_id: str,
        payload: SessionReopenRequest,
        officer_user: User,
    ) -> PhysicalVerificationSession:
        """
        Reopens a completed physical verification session.
        RBAC: Restricted strictly to ADMISSION_HEAD and SUPER_ADMIN.
        """
        role_name = officer_user.role.name if officer_user.role else ""
        if role_name not in ["ADMISSION_HEAD", "SUPER_ADMIN"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: Only ADMISSION_HEAD or SUPER_ADMIN can reopen a verification session. Your role is '{role_name}'"
            )

        if not payload.reason or not payload.reason.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reopening justification reason is required"
            )

        session = await cls.get_session_by_id(db, session_id)
        now = datetime.now(timezone.utc)

        session.session_status = PhysicalSessionStatus.REOPENED.value
        session.completed_at = None
        session.updated_at = now

        if session.appointment_id:
            apt_stmt = select(PhysicalVerificationAppointment).where(PhysicalVerificationAppointment.id == session.appointment_id)
            apt_res = await db.execute(apt_stmt)
            apt = apt_res.scalar_one_or_none()
            if apt:
                apt.appointment_status = AppointmentStatus.IN_PROGRESS.value
                apt.updated_at = now

        audit = PhysicalVerificationAuditLog(
            application_id=session.application_id,
            appointment_id=session.appointment_id,
            session_id=session.id,
            actor_id=officer_user.id,
            actor_name=officer_user.email,
            actor_role=role_name,
            action=PhysicalVerificationAction.SESSION_REOPENED.value,
            details={"reason": payload.reason},
        )
        db.add(audit)

        await db.commit()
        return await cls.get_session_by_id(db, session_id)

    @classmethod
    async def admin_list_appointments(
        cls,
        db: AsyncSession,
        app_date: Optional[date] = None,
        status_filter: Optional[str] = None,
        search_query: Optional[str] = None,
    ) -> List[PhysicalVerificationAppointment]:
        """
        Admin query for appointments queue.
        """
        query = (
            select(PhysicalVerificationAppointment)
            .options(
                selectinload(PhysicalVerificationAppointment.application).selectinload(AdmissionApplication.student),
            )
            .order_by(
                PhysicalVerificationAppointment.appointment_date.desc(),
                PhysicalVerificationAppointment.start_time.asc()
            )
        )

        if app_date:
            query = query.where(PhysicalVerificationAppointment.appointment_date == app_date)
        if status_filter:
            query = query.where(PhysicalVerificationAppointment.appointment_status == status_filter.upper())
        if search_query:
            q = f"%{search_query.strip()}%"
            query = query.join(AdmissionApplication, PhysicalVerificationAppointment.application_id == AdmissionApplication.id).filter(
                or_(
                    PhysicalVerificationAppointment.token_number.ilike(q),
                    AdmissionApplication.application_number.ilike(q),
                    AdmissionApplication.student_name.ilike(q),
                )
            )

        res = await db.execute(query)
        return res.scalars().all()

    @classmethod
    async def get_session_audit_logs(
        cls,
        db: AsyncSession,
        session_id: str,
        current_user: User,
    ) -> List[PhysicalVerificationAuditLog]:
        """
        Retrieves audit trail entries for a session.
        """
        session = await cls.get_session_by_id(db, session_id, current_user)
        stmt = (
            select(PhysicalVerificationAuditLog)
            .where(
                or_(
                    PhysicalVerificationAuditLog.session_id == session_id,
                    PhysicalVerificationAuditLog.application_id == session.application_id,
                )
            )
            .order_by(desc(PhysicalVerificationAuditLog.created_at))
        )
        res = await db.execute(stmt)
        return res.scalars().all()

    @classmethod
    async def get_student_physical_verification_summary(
        cls,
        db: AsyncSession,
        student: Student,
    ) -> Dict[str, Any]:
        """
        Student Dashboard: Candidate-facing summary of physical verification state,
        including upcoming appointment, QR token, latest session outcome, and correction requests.
        """
        app_stmt = (
            select(AdmissionApplication)
            .where(AdmissionApplication.student_id == student.id)
            .options(
                selectinload(AdmissionApplication.documents).selectinload(Document.document_type),
                selectinload(AdmissionApplication.documents).selectinload(Document.versions),
            )
        )
        app_res = await db.execute(app_stmt)
        app = app_res.scalar_one_or_none()
        if not app:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Admission application not found"
            )

        # Get latest appointment
        apt_stmt = (
            select(PhysicalVerificationAppointment)
            .where(PhysicalVerificationAppointment.application_id == app.id)
            .order_by(desc(PhysicalVerificationAppointment.created_at))
        )
        apt_res = await db.execute(apt_stmt)
        latest_apt = apt_res.scalars().first()

        # Get latest session
        sess_stmt = (
            select(PhysicalVerificationSession)
            .where(PhysicalVerificationSession.application_id == app.id)
            .order_by(desc(PhysicalVerificationSession.created_at))
            .options(
                selectinload(PhysicalVerificationSession.document_verifications).selectinload(PhysicalDocumentVerification.document).selectinload(Document.document_type),
                selectinload(PhysicalVerificationSession.document_verifications).selectinload(PhysicalDocumentVerification.document_version),
            )
        )
        sess_res = await db.execute(sess_stmt)
        latest_sess = sess_res.scalars().first()

        correction_items = []
        if latest_sess and latest_sess.document_verifications:
            for dv in latest_sess.document_verifications:
                if dv.officer_decision == PhysicalDocDecision.CORRECTION_REQUIRED.value:
                    dt_name = dv.document.document_type.name if dv.document and dv.document.document_type else "Document"
                    dt_code = dv.document.document_type.code if dv.document and dv.document.document_type else ""
                    v_num = dv.document_version.version_number if dv.document_version else 1
                    correction_items.append({
                        "document_id": dv.document_id,
                        "document_type_code": dt_code,
                        "document_type_name": dt_name,
                        "version_number": v_num,
                        "discrepancy_reason": dv.discrepancy_reason,
                        "officer_notes": dv.verification_notes,
                    })

        return {
            "application_id": app.id,
            "application_number": app.application_number,
            "has_appointment": latest_apt is not None,
            "appointment": latest_apt,
            "session_status": latest_sess.session_status if latest_sess else "NOT_SCHEDULED",
            "overall_decision": latest_sess.overall_decision if latest_sess else "PENDING",
            "has_corrections": len(correction_items) > 0,
            "corrections": correction_items,
        }
