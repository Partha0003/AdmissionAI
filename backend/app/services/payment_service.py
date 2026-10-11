import uuid
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, and_, or_
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status

from app.models.admission import AdmissionApplication
from app.models.student import Student
from app.models.document import Document, DocumentVersion
from app.models.user import User
from app.models.payment import (
    PaymentMethod,
    PaymentStatus,
    PaymentCorrectionReason,
    PaymentAuditAction,
    FeeRequirement,
    PaymentTransaction,
    DemandDraftSubmission,
    PaymentAuditLog,
)
from app.adapters.payment_adapter import mock_payment_adapter


class PaymentService:
    @classmethod
    async def _get_student_application(cls, db: AsyncSession, user: User) -> Optional[AdmissionApplication]:
        stmt = (
            select(AdmissionApplication)
            .outerjoin(Student, AdmissionApplication.student_id == Student.id)
            .where(
                or_(
                    AdmissionApplication.student_id == user.id,
                    Student.user_id == user.id,
                )
            )
        )
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    @classmethod
    async def _check_application_ownership(cls, db: AsyncSession, application_id: str, user: User) -> bool:
        stmt = (
            select(AdmissionApplication)
            .outerjoin(Student, AdmissionApplication.student_id == Student.id)
            .where(
                AdmissionApplication.id == application_id,
                or_(
                    AdmissionApplication.student_id == user.id,
                    Student.user_id == user.id,
                )
            )
        )
        res = await db.execute(stmt)
        return res.scalar_one_or_none() is not None

    @classmethod
    async def get_or_create_fee_requirement(
        cls,
        db: AsyncSession,
        academic_year: str = "2026-27",
        category: str = "GENERAL",
        quota: str = "GOVERNMENT",
    ) -> FeeRequirement:
        """
        Retrieves the authoritative server-side fee requirement or seeds standard institutional fee.
        """
        stmt = select(FeeRequirement).where(
            FeeRequirement.academic_year == academic_year,
            FeeRequirement.category == category,
            FeeRequirement.quota == quota,
            FeeRequirement.is_active == True,
        )
        res = await db.execute(stmt)
        fee = res.scalar_one_or_none()
        if not fee:
            fee = FeeRequirement(
                id=str(uuid.uuid4()),
                academic_year=academic_year,
                category=category,
                quota=quota,
                amount=50000.00,
                currency="INR",
                description=f"Standard Semester Admission Fee ({academic_year}) - XYZ Engineering College",
                is_active=True,
            )
            db.add(fee)
            await db.commit()
            await db.refresh(fee)
        return fee

    @classmethod
    async def get_student_payment_summary(cls, db: AsyncSession, user: User) -> Dict[str, Any]:
        """
        Returns the active payment status and fee requirements for the authenticated student.
        """
        application = await cls._get_student_application(db, user)
        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Admission application not found for student.",
            )

        fee_req = await cls.get_or_create_fee_requirement(db)
        
        # Get latest active payment transaction with relationships
        stmt_pay = (
            select(PaymentTransaction)
            .options(
                selectinload(PaymentTransaction.dd_submission),
                selectinload(PaymentTransaction.fee_requirement),
            )
            .where(PaymentTransaction.application_id == application.id)
            .order_by(desc(PaymentTransaction.created_at))
        )
        res_pay = await db.execute(stmt_pay)
        latest_payment = res_pay.scalars().first()

        has_active_payment = latest_payment is not None
        is_verified = latest_payment.status == PaymentStatus.VERIFIED.value if latest_payment else False
        has_correction_required = latest_payment.status == PaymentStatus.CORRECTION_REQUIRED.value if latest_payment else False

        duplicate_warning = None
        if latest_payment and latest_payment.dd_submission:
            is_dup, dup_msg = await cls.check_duplicate_dd(
                db,
                latest_payment.dd_submission.dd_number,
                latest_payment.dd_submission.bank_name,
                exclude_payment_id=latest_payment.id,
            )
            if is_dup:
                duplicate_warning = dup_msg

        return {
            "application_id": application.id,
            "application_number": application.application_number or "APP-PENDING",
            "has_active_payment": has_active_payment,
            "fee_requirement": fee_req,
            "active_payment": latest_payment,
            "payment_status": latest_payment.status if latest_payment else "PENDING",
            "is_payment_verified": is_verified,
            "has_correction_required": has_correction_required,
            "correction_reason": latest_payment.rejection_reason if has_correction_required else None,
            "correction_instructions": latest_payment.notes if has_correction_required else None,
            "duplicate_warning": duplicate_warning,
        }

    @classmethod
    async def check_duplicate_dd(
        cls, db: AsyncSession, dd_number: str, bank_name: str, exclude_payment_id: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Detects if a DD with the same number and bank has been submitted across other applications.
        """
        stmt = select(DemandDraftSubmission).where(
            DemandDraftSubmission.dd_number == dd_number.strip(),
            func.lower(DemandDraftSubmission.bank_name) == bank_name.strip().lower(),
        )
        if exclude_payment_id:
            stmt = stmt.where(DemandDraftSubmission.payment_id != exclude_payment_id)
        
        res = await db.execute(stmt)
        duplicate = res.scalar_one_or_none()
        if duplicate:
            return True, f"A Demand Draft with Number '{dd_number}' from '{bank_name}' was previously registered. Flagged for review."
        return False, None

    @classmethod
    async def initiate_payment(
        cls,
        db: AsyncSession,
        user: User,
        payment_method: str,
        notes: Optional[str] = None,
    ) -> PaymentTransaction:
        """
        Student initiates a payment transaction.
        Enforces server-side fee requirement amount.
        """
        application = await cls._get_student_application(db, user)
        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Admission application not found.",
            )

        fee_req = await cls.get_or_create_fee_requirement(db)

        # Check existing verified payment
        stmt_exist = select(PaymentTransaction).where(
            PaymentTransaction.application_id == application.id,
            PaymentTransaction.status == PaymentStatus.VERIFIED.value,
        )
        res_exist = await db.execute(stmt_exist)
        if res_exist.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Admission fee has already been verified for this application.",
            )

        ref_suffix = uuid.uuid4().hex[:8].upper()
        payment_ref = f"PAY-XYZ2026-{ref_suffix}"

        transaction = PaymentTransaction(
            id=str(uuid.uuid4()),
            application_id=application.id,
            payment_reference=payment_ref,
            payment_method=payment_method,
            amount=fee_req.amount,  # Authoritative server-side amount
            currency=fee_req.currency,
            status=PaymentStatus.INITIATED.value,
            initiated_at=datetime.now(timezone.utc),
            fee_requirement_id=fee_req.id,
            notes=notes,
        )
        db.add(transaction)
        await db.commit()
        await db.refresh(transaction)

        await cls._log_audit(
            db,
            application.id,
            transaction.id,
            user,
            PaymentAuditAction.PAYMENT_INITIATED.value,
            {
                "payment_reference": payment_ref,
                "payment_method": payment_method,
                "amount": float(fee_req.amount),
                "currency": fee_req.currency,
            },
        )

        return transaction

    @classmethod
    async def submit_demand_draft(
        cls,
        db: AsyncSession,
        user: User,
        payment_id: str,
        dd_number: str,
        dd_date: str,
        bank_name: str,
        branch_name: Optional[str],
        amount: float,
        supporting_document_id: Optional[str] = None,
        supporting_document_version_id: Optional[str] = None,
    ) -> PaymentTransaction:
        """
        Submits Demand Draft details for finance officer review.
        Pins exact supporting document version.
        """
        stmt_txn = (
            select(PaymentTransaction)
            .options(selectinload(PaymentTransaction.dd_submission))
            .where(PaymentTransaction.id == payment_id)
        )
        res_txn = await db.execute(stmt_txn)
        transaction = res_txn.scalar_one_or_none()
        if not transaction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment transaction not found.",
            )

        # Anti-IDOR ownership check
        is_owner = await cls._check_application_ownership(db, transaction.application_id, user)
        if not is_owner:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Cannot submit DD for another student's payment.",
            )

        # Server-side amount validation
        fee_req = await cls.get_or_create_fee_requirement(db)
        if abs(float(amount) - float(fee_req.amount)) > 0.01:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Submitted DD amount ({amount}) does not match configured fee requirement ({fee_req.amount}).",
            )

        # Pin supporting document version if provided
        doc_version_id = None
        if supporting_document_id:
            stmt_doc = select(Document).where(Document.id == supporting_document_id)
            res_doc = await db.execute(stmt_doc)
            doc = res_doc.scalar_one_or_none()
            if doc:
                doc_version_id = supporting_document_version_id or doc.current_version_id

        # Check duplicate DD
        is_duplicate, duplicate_msg = await cls.check_duplicate_dd(
            db, dd_number, bank_name, exclude_payment_id=payment_id
        )

        # Update or create DD submission
        if transaction.dd_submission:
            dd_sub = transaction.dd_submission
            dd_sub.dd_number = dd_number.strip()
            dd_sub.dd_date = dd_date
            dd_sub.bank_name = bank_name.strip()
            dd_sub.branch_name = branch_name.strip() if branch_name else None
            dd_sub.amount = amount
            dd_sub.supporting_document_id = supporting_document_id
            dd_sub.supporting_document_version_id = doc_version_id
            dd_sub.submitted_by_id = user.id
            dd_sub.submitted_at = datetime.now(timezone.utc)
            dd_sub.updated_at = datetime.now(timezone.utc)
        else:
            dd_sub = DemandDraftSubmission(
                id=str(uuid.uuid4()),
                payment_id=transaction.id,
                dd_number=dd_number.strip(),
                dd_date=dd_date,
                bank_name=bank_name.strip(),
                branch_name=branch_name.strip() if branch_name else None,
                amount=amount,
                supporting_document_id=supporting_document_id,
                supporting_document_version_id=doc_version_id,
                submitted_by_id=user.id,
                submitted_at=datetime.now(timezone.utc),
            )
            db.add(dd_sub)

        # Update payment transaction status
        transaction.status = PaymentStatus.SUBMITTED.value
        transaction.submitted_at = datetime.now(timezone.utc)
        transaction.updated_at = datetime.now(timezone.utc)
        if is_duplicate:
            transaction.notes = f"[DUPLICATE WARNING] {duplicate_msg}"

        await db.commit()
        await db.refresh(transaction)

        # Append-only audit log
        await cls._log_audit(
            db,
            transaction.application_id,
            transaction.id,
            user,
            PaymentAuditAction.DD_SUBMITTED.value,
            {
                "dd_number": dd_number,
                "bank_name": bank_name,
                "amount": float(amount),
                "is_duplicate": is_duplicate,
                "pinned_document_version": doc_version_id,
            },
        )

        return transaction

    @classmethod
    async def simulate_online_payment(
        cls,
        db: AsyncSession,
        user: User,
        payment_id: str,
        simulate_failure: bool = False,
        notes: Optional[str] = None,
    ) -> PaymentTransaction:
        """
        Executes a simulated online payment through MockPaymentAdapter.
        Clearly designated as PROTOTYPE SIMULATION ONLY.
        """
        stmt_txn = select(PaymentTransaction).where(PaymentTransaction.id == payment_id)
        res_txn = await db.execute(stmt_txn)
        transaction = res_txn.scalar_one_or_none()
        if not transaction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment transaction not found.",
            )

        is_owner = await cls._check_application_ownership(db, transaction.application_id, user)
        if not is_owner:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Cannot process another student's payment.",
            )

        # Mark as pending gateway processing
        transaction.status = PaymentStatus.PENDING.value
        await db.commit()

        # Call MockPaymentAdapter
        result = mock_payment_adapter.process_online_payment(
            payment_reference=transaction.payment_reference,
            amount=float(transaction.amount),
            currency=transaction.currency,
            student_name=getattr(user, "email", "Candidate"),
            simulate_failure=simulate_failure,
        )

        if result["success"]:
            transaction.status = PaymentStatus.VERIFIED.value
            transaction.verified_at = datetime.now(timezone.utc)
            transaction.submitted_at = datetime.now(timezone.utc)
            transaction.notes = f"Mock Gateway Payment Approved (Ref: {result.get('gateway_reference')})"
            action = PaymentAuditAction.PAYMENT_VERIFIED.value
        else:
            transaction.status = PaymentStatus.FAILED.value
            transaction.rejection_reason = "PAYMENT_FAILED"
            transaction.notes = result.get("error_message")
            action = PaymentAuditAction.PAYMENT_FAILED.value

        await db.commit()
        await db.refresh(transaction)

        await cls._log_audit(
            db,
            transaction.application_id,
            transaction.id,
            user,
            action,
            {
                "simulate_failure": simulate_failure,
                "gateway_result": result,
                "notes": notes,
            },
        )

        return transaction

    @classmethod
    async def finance_review_payment(
        cls,
        db: AsyncSession,
        officer: User,
        payment_id: str,
        decision: str,
        reason: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> PaymentTransaction:
        """
        Finance officer reviews submitted payment and records authoritative physical finance decision.
        """
        stmt_txn = (
            select(PaymentTransaction)
            .options(selectinload(PaymentTransaction.dd_submission))
            .where(PaymentTransaction.id == payment_id)
        )
        res_txn = await db.execute(stmt_txn)
        transaction = res_txn.scalar_one_or_none()
        if not transaction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment transaction not found.",
            )

        # Concurrency check: already verified
        if transaction.status == PaymentStatus.VERIFIED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This payment has already been verified and locked by Finance.",
            )

        if decision == "CORRECTION_REQUIRED":
            if not reason:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A structured correction reason is required when requesting payment correction.",
                )
            if reason == PaymentCorrectionReason.OTHER.value and (not notes or not notes.strip()):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Explanatory notes are required when selecting 'OTHER' correction reason.",
                )
            transaction.status = PaymentStatus.CORRECTION_REQUIRED.value
            transaction.rejection_reason = reason
            transaction.notes = notes
            action = PaymentAuditAction.PAYMENT_CORRECTION_REQUESTED.value

        elif decision == "REJECTED":
            if not reason:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A rejection reason is required.",
                )
            if reason == PaymentCorrectionReason.OTHER.value and (not notes or not notes.strip()):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Explanatory notes are required when selecting 'OTHER' rejection reason.",
                )
            transaction.status = PaymentStatus.REJECTED.value
            transaction.rejection_reason = reason
            transaction.notes = notes
            action = PaymentAuditAction.PAYMENT_REJECTED.value

        elif decision == "VERIFIED":
            transaction.status = PaymentStatus.VERIFIED.value
            transaction.verified_at = datetime.now(timezone.utc)
            transaction.verified_by_id = officer.id
            transaction.rejection_reason = None
            transaction.notes = notes
            action = PaymentAuditAction.PAYMENT_VERIFIED.value

            if transaction.dd_submission:
                transaction.dd_submission.finance_verified_by_id = officer.id
                transaction.dd_submission.finance_verified_at = datetime.now(timezone.utc)
                transaction.dd_submission.finance_notes = notes

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid finance decision: {decision}",
            )

        await db.commit()
        await db.refresh(transaction)

        await cls._log_audit(
            db,
            transaction.application_id,
            transaction.id,
            officer,
            action,
            {
                "decision": decision,
                "reason": reason,
                "notes": notes,
            },
        )

        return transaction

    @classmethod
    async def list_admin_payments(
        cls,
        db: AsyncSession,
        status_filter: Optional[str] = None,
        method_filter: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[PaymentTransaction]:
        """
        Lists payment transactions for the finance officer desk.
        """
        stmt = (
            select(PaymentTransaction)
            .join(AdmissionApplication)
            .options(
                selectinload(PaymentTransaction.dd_submission),
                selectinload(PaymentTransaction.fee_requirement),
            )
        )
        if status_filter:
            stmt = stmt.where(PaymentTransaction.status == status_filter)
        if method_filter:
            stmt = stmt.where(PaymentTransaction.payment_method == method_filter)
        if search:
            search_term = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    PaymentTransaction.payment_reference.ilike(search_term),
                    AdmissionApplication.application_number.ilike(search_term),
                )
            )
        stmt = stmt.order_by(desc(PaymentTransaction.created_at))
        res = await db.execute(stmt)
        return res.scalars().all()

    @classmethod
    async def get_payment_by_id(cls, db: AsyncSession, payment_id: str) -> PaymentTransaction:
        stmt = (
            select(PaymentTransaction)
            .options(
                selectinload(PaymentTransaction.dd_submission),
                selectinload(PaymentTransaction.fee_requirement),
            )
            .where(PaymentTransaction.id == payment_id)
        )
        res = await db.execute(stmt)
        transaction = res.scalar_one_or_none()
        if not transaction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment transaction not found.",
            )
        return transaction

    @classmethod
    async def get_payment_audit_logs(cls, db: AsyncSession, payment_id: str) -> List[PaymentAuditLog]:
        stmt = (
            select(PaymentAuditLog)
            .where(PaymentAuditLog.payment_id == payment_id)
            .order_by(PaymentAuditLog.created_at.asc())
        )
        res = await db.execute(stmt)
        return res.scalars().all()

    @classmethod
    async def _log_audit(
        cls,
        db: AsyncSession,
        application_id: str,
        payment_id: str,
        actor: User,
        action: str,
        details: Dict[str, Any],
    ) -> PaymentAuditLog:
        actor_name = "System"
        actor_role = "SYSTEM"
        if actor:
            actor_name = getattr(actor, "email", getattr(actor, "name", "User"))
            if hasattr(actor, "role") and actor.role:
                actor_role = getattr(actor.role, "name", str(actor.role))
            elif hasattr(actor, "role_id"):
                actor_role = str(actor.role_id)

        log = PaymentAuditLog(
            id=str(uuid.uuid4()),
            application_id=application_id,
            payment_id=payment_id,
            actor_id=actor.id if actor else None,
            actor_name=actor_name,
            actor_role=actor_role,
            action=action,
            details=details,
            created_at=datetime.now(timezone.utc),
        )
        db.add(log)
        await db.commit()
        return log
