import uuid
import hashlib
import json
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, or_
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status

from app.models.admission import AdmissionApplication
from app.models.student import Student
from app.models.tnea_allotment import TNEAAllotment
from app.models.physical_verification import (
    PhysicalVerificationSession,
    PhysicalSessionStatus,
    PhysicalVerificationDecision,
)
from app.models.payment import PaymentTransaction, PaymentStatus
from app.models.erp import (
    ERPRecordStatus,
    ERPIntegrationStatus,
    ERPAdmissionRecord,
    ERPIntegrationEvent,
)
from app.adapters.erp_adapter import mock_erp_adapter


class ERPService:
    @classmethod
    async def validate_erp_readiness(
        cls, db: AsyncSession, application_id: str
    ) -> Dict[str, Any]:
        """
        Evaluates the institutional readiness policy for staging an admission record into the ERP.
        Explicitly identifies any missing requirements or blocking discrepancies.
        """
        stmt_app = select(AdmissionApplication).where(AdmissionApplication.id == application_id)
        res_app = await db.execute(stmt_app)
        application = res_app.scalar_one_or_none()
        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Admission application not found.",
            )

        stmt_stud = select(Student).where(Student.id == application.student_id)
        res_stud = await db.execute(stmt_stud)
        student = res_stud.scalar_one_or_none()

        allotment = None
        if student:
            stmt_allot = select(TNEAAllotment).where(TNEAAllotment.student_id == student.id)
            res_allot = await db.execute(stmt_allot)
            allotment = res_allot.scalar_one_or_none()

        # Check 1: Candidate & Allotment Identity
        has_identity = bool(student and student.full_name and student.tnea_application_number)
        has_allotment = bool((allotment and allotment.allotment_number and allotment.branch_name) or (student and student.allotted_branch and student.tnea_application_number))

        # Check 2: Physical Verification Session
        stmt_phys = (
            select(PhysicalVerificationSession)
            .where(
                PhysicalVerificationSession.application_id == application.id,
                PhysicalVerificationSession.session_status == PhysicalSessionStatus.COMPLETED.value,
            )
            .order_by(desc(PhysicalVerificationSession.completed_at))
        )
        res_phys = await db.execute(stmt_phys)
        physical_session = res_phys.scalars().first()

        is_physical_verified = bool(
            physical_session
            and physical_session.overall_decision in [
                PhysicalVerificationDecision.VERIFIED.value,
                PhysicalVerificationDecision.PARTIALLY_VERIFIED.value,
            ]
        )

        # Check 3: Finance / Fee Settlement
        stmt_pay = select(PaymentTransaction).where(
            PaymentTransaction.application_id == application.id,
            PaymentTransaction.status == PaymentStatus.VERIFIED.value,
        )
        res_pay = await db.execute(stmt_pay)
        verified_payment = res_pay.scalars().first()
        is_payment_verified = bool(verified_payment)

        # Check 4: Unresolved Corrections
        stmt_corr = select(PaymentTransaction).where(
            PaymentTransaction.application_id == application.id,
            PaymentTransaction.status == PaymentStatus.CORRECTION_REQUIRED.value,
        )
        res_corr = await db.execute(stmt_corr)
        has_active_payment_correction = bool(res_corr.scalars().first())

        errors = []
        if not has_identity:
            errors.append("Candidate personal identity information is incomplete.")
        if not has_allotment:
            errors.append("TNEA allotment order details are missing or invalid.")
        if not is_physical_verified:
            errors.append("Physical document verification is incomplete or pending officer decision.")
        if not is_payment_verified:
            errors.append("Admission fee payment verification is pending with Finance.")
        if has_active_payment_correction:
            errors.append("Active payment correction request requires student re-submission.")

        is_ready = len(errors) == 0
        readiness_status = (
            ERPRecordStatus.READY_FOR_STAGING.value
            if is_ready
            else ERPRecordStatus.NOT_READY.value
        )

        return {
            "application_id": application.id,
            "is_ready": is_ready,
            "status": readiness_status,
            "validation_errors": errors,
            "readiness_checks": {
                "identity_present": has_identity,
                "allotment_present": has_allotment,
                "physical_verification_completed": is_physical_verified,
                "payment_verified": is_payment_verified,
                "zero_blocking_corrections": not has_active_payment_correction,
            },
        }

    @classmethod
    async def build_sanitized_erp_payload(
        cls, db: AsyncSession, application: AdmissionApplication
    ) -> Dict[str, Any]:
        """
        Assembles a normalized, sanitized JSON payload without passwords, JWTs, secrets, or raw OCR.
        """
        stmt_stud = select(Student).where(Student.id == application.student_id)
        res_stud = await db.execute(stmt_stud)
        student = res_stud.scalar_one_or_none()

        allotment = None
        if student:
            stmt_allot = select(TNEAAllotment).where(TNEAAllotment.student_id == student.id)
            res_allot = await db.execute(stmt_allot)
            allotment = res_allot.scalar_one_or_none()
        
        stmt_phys = (
            select(PhysicalVerificationSession)
            .options(selectinload(PhysicalVerificationSession.document_verifications))
            .where(PhysicalVerificationSession.application_id == application.id)
            .order_by(desc(PhysicalVerificationSession.created_at))
        )
        res_phys = await db.execute(stmt_phys)
        physical_session = res_phys.scalars().first()
        
        stmt_pay = (
            select(PaymentTransaction)
            .where(PaymentTransaction.application_id == application.id)
            .order_by(desc(PaymentTransaction.created_at))
        )
        res_pay = await db.execute(stmt_pay)
        payment = res_pay.scalars().first()

        payload = {
            "institution": {
                "code": "XYZ",
                "name": "XYZ Engineering College",
                "academic_year": "2026-27",
            },
            "application": {
                "id": application.id,
                "application_number": application.application_number,
                "submitted_at": application.submitted_at.isoformat() if application.submitted_at else None,
                "lifecycle_state": application.status,
            },
            "student": {
                "id": student.id if student else None,
                "full_name": student.full_name if student else None,
                "email": student.email if student else None,
                "mobile": student.mobile if student else None,
                "community": student.community if student else "OC",
                "quota": student.quota if student else "GOVERNMENT",
                "allotted_branch": student.allotted_branch if student else None,
            },
            "allotment": {
                "allotment_number": allotment.allotment_number if allotment else None,
                "allotment_date": str(allotment.allotment_date) if allotment and allotment.allotment_date else None,
                "cutoff_mark": float(allotment.cutoff_mark) if allotment and allotment.cutoff_mark is not None else None,
                "branch_name": allotment.branch_name if allotment else None,
            },
            "physical_verification": {
                "session_id": physical_session.id if physical_session else None,
                "status": physical_session.session_status if physical_session else "NOT_STARTED",
                "overall_decision": physical_session.overall_decision if physical_session else "PENDING",
                "verified_documents_count": len(physical_session.document_verifications) if physical_session and physical_session.document_verifications else 0,
            },
            "finance": {
                "payment_reference": payment.payment_reference if payment else None,
                "payment_method": payment.payment_method if payment else None,
                "amount": float(payment.amount) if payment else None,
                "currency": payment.currency if payment else "INR",
                "status": payment.status if payment else "PENDING",
                "verified_at": payment.verified_at.isoformat() if payment and payment.verified_at else None,
            },
            "metadata": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "is_prototype": True,
                "adapter": "MockERPAdapter",
            },
        }

        return payload

    @classmethod
    async def stage_admission_record(
        cls, db: AsyncSession, application_id: str, force_stage: bool = False
    ) -> ERPAdmissionRecord:
        """
        Stages an admission record into the ERP staging domain.
        Idempotent: updates existing record and increments payload_version without duplicating records.
        """
        readiness = await cls.validate_erp_readiness(db, application_id)
        if not readiness["is_ready"] and not force_stage:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot stage ERP record: {', '.join(readiness['validation_errors'])}",
            )

        stmt_app = select(AdmissionApplication).where(AdmissionApplication.id == application_id)
        res_app = await db.execute(stmt_app)
        application = res_app.scalar_one_or_none()
        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Admission application not found.",
            )

        payload = await cls.build_sanitized_erp_payload(db, application)
        payload_str = json.dumps(payload, sort_keys=True)
        payload_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()

        stmt_rec = select(ERPAdmissionRecord).where(ERPAdmissionRecord.application_id == application_id)
        res_rec = await db.execute(stmt_rec)
        erp_record = res_rec.scalar_one_or_none()

        if not erp_record:
            ref_num = application.application_number.replace("APP-", "").replace("-", "") if application.application_number else uuid.uuid4().hex[:6].upper()
            staging_ref = f"ERP-XYZ2026-{ref_num}"
            erp_record = ERPAdmissionRecord(
                id=str(uuid.uuid4()),
                application_id=application_id,
                staging_reference=staging_ref,
                payload=payload,
                payload_hash=payload_hash,
                payload_version=1,
                status=ERPRecordStatus.STAGED.value,
                validation_errors=readiness["validation_errors"] if not readiness["is_ready"] else None,
                staged_at=datetime.now(timezone.utc),
            )
            db.add(erp_record)
        else:
            # Idempotent update
            erp_record.payload = payload
            erp_record.payload_hash = payload_hash
            erp_record.payload_version += 1
            erp_record.status = ERPRecordStatus.STAGED.value
            erp_record.validation_errors = readiness["validation_errors"] if not readiness["is_ready"] else None
            erp_record.staged_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(erp_record)
        return erp_record

    @classmethod
    async def sync_record(
        cls,
        db: AsyncSession,
        record_id: str,
        simulate_failure: bool = False,
        failure_reason: Optional[str] = None,
    ) -> ERPAdmissionRecord:
        """
        Dispatches staged payload to the MockERPAdapter.
        Records append-only integration events and updates ERP staging record status.
        """
        stmt_rec = select(ERPAdmissionRecord).where(ERPAdmissionRecord.id == record_id)
        res_rec = await db.execute(stmt_rec)
        erp_record = res_rec.scalar_one_or_none()
        if not erp_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="ERP admission record not found.",
            )

        erp_record.status = ERPRecordStatus.SYNCING.value
        await db.commit()

        # Call MockERPAdapter
        result = mock_erp_adapter.sync_admission_record(
            staging_reference=erp_record.staging_reference,
            payload=erp_record.payload,
            simulate_failure=simulate_failure,
            failure_reason=failure_reason,
        )

        now = datetime.now(timezone.utc)
        if result["success"]:
            erp_record.status = ERPRecordStatus.SYNCED.value
            erp_record.synced_at = now
            erp_record.last_error = None
            event_status = ERPIntegrationStatus.SUCCESS.value
        else:
            erp_record.status = ERPRecordStatus.SYNC_FAILED.value
            erp_record.last_error = result["error_summary"]
            event_status = ERPIntegrationStatus.FAILED.value

        event = ERPIntegrationEvent(
            id=str(uuid.uuid4()),
            erp_record_id=erp_record.id,
            event_type="ERP_SYNC_DISPATCH",
            adapter_name="MockERPAdapter",
            request_reference=erp_record.staging_reference,
            response_reference=result.get("response_reference"),
            status=event_status,
            error_summary=result.get("error_summary"),
            details=result.get("details"),
            created_at=now,
        )
        db.add(event)
        await db.commit()
        await db.refresh(erp_record)

        return erp_record

    @classmethod
    async def retry_sync(
        cls,
        db: AsyncSession,
        record_id: str,
        simulate_failure: bool = False,
        failure_reason: Optional[str] = None,
    ) -> ERPAdmissionRecord:
        """
        Retries a failed synchronization attempt safely on the same logical ERP record.
        """
        stmt_rec = select(ERPAdmissionRecord).where(ERPAdmissionRecord.id == record_id)
        res_rec = await db.execute(stmt_rec)
        erp_record = res_rec.scalar_one_or_none()
        if not erp_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="ERP admission record not found.",
            )

        erp_record.retry_count += 1
        erp_record.status = ERPRecordStatus.RETRY_PENDING.value
        await db.commit()

        # Re-dispatch
        return await cls.sync_record(
            db,
            record_id=erp_record.id,
            simulate_failure=simulate_failure,
            failure_reason=failure_reason,
        )

    @classmethod
    async def list_erp_records(
        cls,
        db: AsyncSession,
        status_filter: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[ERPAdmissionRecord]:
        stmt = select(ERPAdmissionRecord).join(AdmissionApplication)
        if status_filter:
            stmt = stmt.where(ERPAdmissionRecord.status == status_filter)
        if search:
            search_term = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    ERPAdmissionRecord.staging_reference.ilike(search_term),
                    AdmissionApplication.application_number.ilike(search_term),
                )
            )
        stmt = stmt.order_by(desc(ERPAdmissionRecord.created_at))
        res = await db.execute(stmt)
        return res.scalars().all()

    @classmethod
    async def get_erp_record_by_id(cls, db: AsyncSession, record_id: str) -> ERPAdmissionRecord:
        stmt = select(ERPAdmissionRecord).where(ERPAdmissionRecord.id == record_id)
        res = await db.execute(stmt)
        record = res.scalar_one_or_none()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="ERP record not found.",
            )
        return record

    @classmethod
    async def get_record_events(cls, db: AsyncSession, record_id: str) -> List[ERPIntegrationEvent]:
        stmt = (
            select(ERPIntegrationEvent)
            .where(ERPIntegrationEvent.erp_record_id == record_id)
            .order_by(ERPIntegrationEvent.created_at.asc())
        )
        res = await db.execute(stmt)
        return res.scalars().all()
