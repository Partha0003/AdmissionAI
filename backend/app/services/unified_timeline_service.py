from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, asc, or_, and_
from fastapi import HTTPException, status

from app.models.admission import AdmissionApplication, AdmissionStatusHistory
from app.models.student import Student
from app.models.tnea_allotment import TNEAAllotment
from app.models.scrutiny import ScrutinyAuditLog, AdmissionReview
from app.models.physical_verification import (
    PhysicalVerificationAuditLog,
    PhysicalVerificationSession,
    PhysicalVerificationAppointment,
)
from app.models.payment import PaymentTransaction, PaymentAuditLog
from app.models.erp import ERPAdmissionRecord, ERPIntegrationEvent
from app.models.user import User


class UnifiedTimelineService:
    @classmethod
    async def get_student_journey_timeline(
        cls, db: AsyncSession, user: User
    ) -> Dict[str, Any]:
        """
        Builds the unified 8-stage operational journey for the authenticated student.
        """
        stmt_app = (
            select(AdmissionApplication)
            .outerjoin(Student, AdmissionApplication.student_id == Student.id)
            .where(
                or_(
                    AdmissionApplication.student_id == user.id,
                    Student.user_id == user.id,
                )
            )
        )
        res_app = await db.execute(stmt_app)
        application = res_app.scalar_one_or_none()
        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Admission application not found.",
            )

        return await cls.get_application_timeline(db, application.id)

    @classmethod
    async def get_application_timeline(
        cls, db: AsyncSession, application_id: str
    ) -> Dict[str, Any]:
        """
        Assembles all domain events and calculates authoritative stage progression.
        """
        stmt_app = select(AdmissionApplication).where(AdmissionApplication.id == application_id)
        res_app = await db.execute(stmt_app)
        application = res_app.scalar_one_or_none()
        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Admission application not found.",
            )

        events: List[Dict[str, Any]] = []

        # 1. Allotment & Admission Lifecycle Status History
        stmt_sh = (
            select(AdmissionStatusHistory)
            .where(AdmissionStatusHistory.admission_application_id == application.id)
            .order_by(AdmissionStatusHistory.created_at.asc())
        )
        res_sh = await db.execute(stmt_sh)
        status_histories = res_sh.scalars().all()
        for sh in status_histories:
            is_system = sh.actor_role in ["SYSTEM", "AUTOMATED", None]
            events.append({
                "id": f"STATUS-{sh.id}",
                "stage": "APPLICATION",
                "event_type": "LIFECYCLE_TRANSITION",
                "actor_type": "SYSTEM_EVENT" if is_system else "HUMAN_ACTION",
                "actor_name": "Admission System" if is_system else sh.actor_role,
                "actor_role": sh.actor_role or "SYSTEM",
                "title": f"Lifecycle: {sh.new_status}",
                "description": sh.reason or f"Transitioned from {sh.previous_status} to {sh.new_status}",
                "status": sh.new_status,
                "reference_id": application.application_number,
                "metadata": {"previous_status": sh.previous_status, "new_status": sh.new_status},
                "timestamp": sh.created_at,
            })

        # 2. Digital Scrutiny Audit Logs
        stmt_scl = (
            select(ScrutinyAuditLog)
            .where(ScrutinyAuditLog.application_id == application.id)
            .order_by(ScrutinyAuditLog.created_at.asc())
        )
        res_scl = await db.execute(stmt_scl)
        scrutiny_logs = res_scl.scalars().all()
        for scl in scrutiny_logs:
            events.append({
                "id": f"SCRUTINY-{scl.id}",
                "stage": "DIGITAL_SCRUTINY",
                "event_type": scl.action,
                "actor_type": "HUMAN_ACTION",
                "actor_name": scl.actor_name or "Admission Scrutiny Desk",
                "actor_role": scl.actor_role or "ADMIN_VERIFIER",
                "title": f"Scrutiny: {scl.action.replace('_', ' ').title()}",
                "description": f"Human scrutiny action recorded by {scl.actor_name or 'Reviewer'}.",
                "status": scl.action,
                "reference_id": scl.review_id,
                "metadata": scl.details,
                "timestamp": scl.created_at,
            })

        # 3. Physical Verification Audit Logs
        stmt_pl = (
            select(PhysicalVerificationAuditLog)
            .where(PhysicalVerificationAuditLog.application_id == application.id)
            .order_by(PhysicalVerificationAuditLog.created_at.asc())
        )
        res_pl = await db.execute(stmt_pl)
        physical_logs = res_pl.scalars().all()
        for pl in physical_logs:
            events.append({
                "id": f"PHYSICAL-{pl.id}",
                "stage": "PHYSICAL_VERIFICATION",
                "event_type": pl.action,
                "actor_type": "HUMAN_ACTION",
                "actor_name": pl.actor_name or "Verification Officer",
                "actor_role": pl.actor_role or "ADMIN_VERIFIER",
                "title": f"Physical Verification: {pl.action.replace('_', ' ').title()}",
                "description": f"On-site verification event recorded at campus desk.",
                "status": pl.action,
                "reference_id": pl.session_id or pl.appointment_id,
                "metadata": pl.details,
                "timestamp": pl.created_at,
            })

        # 4. Payment Audit Logs
        stmt_pml = (
            select(PaymentAuditLog)
            .where(PaymentAuditLog.application_id == application.id)
            .order_by(PaymentAuditLog.created_at.asc())
        )
        res_pml = await db.execute(stmt_pml)
        payment_logs = res_pml.scalars().all()
        for pml in payment_logs:
            is_system = pml.actor_role in ["SYSTEM", "MOCK_GATEWAY", None]
            events.append({
                "id": f"PAYMENT-{pml.id}",
                "stage": "PAYMENT",
                "event_type": pml.action,
                "actor_type": "SYSTEM_EVENT" if is_system else "HUMAN_ACTION",
                "actor_name": pml.actor_name or ("Payment Gateway" if is_system else "Finance Officer"),
                "actor_role": pml.actor_role or "FINANCE_OFFICER",
                "title": f"Finance: {pml.action.replace('_', ' ').title()}",
                "description": f"Payment lifecycle event recorded.",
                "status": pml.action,
                "reference_id": pml.payment_id,
                "metadata": pml.details,
                "timestamp": pml.created_at,
            })

        # 5. ERP Integration Events
        stmt_erp = select(ERPAdmissionRecord).where(ERPAdmissionRecord.application_id == application.id)
        res_erp = await db.execute(stmt_erp)
        erp_record = res_erp.scalar_one_or_none()
        if erp_record:
            stmt_ee = (
                select(ERPIntegrationEvent)
                .where(ERPIntegrationEvent.erp_record_id == erp_record.id)
                .order_by(ERPIntegrationEvent.created_at.asc())
            )
            res_ee = await db.execute(stmt_ee)
            erp_events = res_ee.scalars().all()
            for ee in erp_events:
                events.append({
                    "id": f"ERP-{ee.id}",
                    "stage": "ERP_PROCESSING",
                    "event_type": ee.event_type,
                    "actor_type": "SYSTEM_EVENT",
                    "actor_name": "MockERPAdapter",
                    "actor_role": "SYSTEM",
                    "title": f"ERP Sync: {ee.status}",
                    "description": ee.error_summary or f"Mock ERP integration dispatch ({ee.response_reference or ee.request_reference})",
                    "status": ee.status,
                    "reference_id": ee.response_reference or ee.request_reference,
                    "metadata": ee.details,
                    "timestamp": ee.created_at,
                })

        # Sort all timeline events chronologically
        events.sort(key=lambda x: x["timestamp"])

        # Calculate authoritative stage progression
        stages = await cls._calculate_stage_states(db, application)

        return {
            "application_id": application.id,
            "application_number": application.application_number or "APP-PENDING",
            "current_lifecycle_status": application.status,
            "stages": stages,
            "events": events,
        }

    @classmethod
    async def _calculate_stage_states(
        cls, db: AsyncSession, application: AdmissionApplication
    ) -> Dict[str, str]:
        """
        Determines the state of each journey step using authoritative domain records.
        """
        stages = {
            "allotment": "COMPLETED",
            "activation": "COMPLETED",
            "application": "NOT_STARTED",
            "documents": "NOT_STARTED",
            "digital_scrutiny": "NOT_STARTED",
            "physical_verification": "NOT_STARTED",
            "payment": "NOT_STARTED",
            "erp": "NOT_STARTED",
        }

        # Application Form
        if application.status in ["APPLICATION_IN_PROGRESS"]:
            stages["application"] = "IN_PROGRESS"
        elif application.status in ["APPLICATION_SUBMITTED", "DOCUMENT_REVIEW", "DOCUMENTS_VERIFIED", "ADMISSION_CONFIRMED", "ACTIVE_STUDENT"]:
            stages["application"] = "COMPLETED"

        # Documents & Digital Scrutiny
        stmt_sc = (
            select(AdmissionReview)
            .where(AdmissionReview.application_id == application.id)
            .order_by(desc(AdmissionReview.created_at))
        )
        res_sc = await db.execute(stmt_sc)
        scrutiny = res_sc.scalars().first()

        if application.status == "CORRECTION_REQUIRED":
            stages["documents"] = "ACTION_REQUIRED"
            stages["digital_scrutiny"] = "ACTION_REQUIRED"
        elif scrutiny and scrutiny.overall_decision == "VERIFIED":
            stages["documents"] = "COMPLETED"
            stages["digital_scrutiny"] = "COMPLETED"
        elif scrutiny and scrutiny.overall_decision == "CORRECTION_REQUIRED":
            stages["documents"] = "ACTION_REQUIRED"
            stages["digital_scrutiny"] = "ACTION_REQUIRED"
        elif scrutiny and scrutiny.review_status == "IN_PROGRESS":
            stages["documents"] = "IN_PROGRESS"
            stages["digital_scrutiny"] = "IN_PROGRESS"

        # Physical Verification
        stmt_phys = (
            select(PhysicalVerificationSession)
            .where(PhysicalVerificationSession.application_id == application.id)
            .order_by(desc(PhysicalVerificationSession.created_at))
        )
        res_phys = await db.execute(stmt_phys)
        phys_session = res_phys.scalars().first()

        if phys_session:
            if phys_session.overall_decision in ["VERIFIED", "PARTIALLY_VERIFIED"]:
                stages["physical_verification"] = "COMPLETED"
            elif phys_session.overall_decision == "CORRECTION_REQUIRED":
                stages["physical_verification"] = "ACTION_REQUIRED"
            elif phys_session.overall_decision == "REJECTED":
                stages["physical_verification"] = "BLOCKED"
            elif phys_session.session_status == "IN_PROGRESS":
                stages["physical_verification"] = "IN_PROGRESS"
        else:
            stmt_appt = select(PhysicalVerificationAppointment).where(PhysicalVerificationAppointment.application_id == application.id)
            res_appt = await db.execute(stmt_appt)
            phys_appt = res_appt.scalar_one_or_none()
            if phys_appt:
                stages["physical_verification"] = "IN_PROGRESS"

        # Payment
        stmt_pay = (
            select(PaymentTransaction)
            .where(PaymentTransaction.application_id == application.id)
            .order_by(desc(PaymentTransaction.created_at))
        )
        res_pay = await db.execute(stmt_pay)
        payment = res_pay.scalars().first()

        if payment:
            if payment.status == "VERIFIED":
                stages["payment"] = "COMPLETED"
            elif payment.status in ["CORRECTION_REQUIRED", "REJECTED", "FAILED"]:
                stages["payment"] = "ACTION_REQUIRED"
            elif payment.status in ["SUBMITTED", "UNDER_REVIEW", "PENDING"]:
                stages["payment"] = "IN_PROGRESS"
        elif stages["physical_verification"] == "COMPLETED":
            stages["payment"] = "ACTION_REQUIRED"

        # ERP Staging & Sync
        stmt_erp = select(ERPAdmissionRecord).where(ERPAdmissionRecord.application_id == application.id)
        res_erp = await db.execute(stmt_erp)
        erp = res_erp.scalar_one_or_none()

        if erp:
            if erp.status == "SYNCED":
                stages["erp"] = "COMPLETED"
            elif erp.status in ["SYNC_FAILED", "RETRY_PENDING"]:
                stages["erp"] = "ACTION_REQUIRED"
            elif erp.status in ["STAGED", "SYNC_PENDING", "SYNCING"]:
                stages["erp"] = "IN_PROGRESS"
        elif stages["payment"] == "COMPLETED":
            stages["erp"] = "IN_PROGRESS"

        return stages
