import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from app.models.admission import AdmissionApplication, AdmissionStatusHistory
from app.models.student import Student
from app.models.user import User
from app.models.document import Document, DocumentVersion
from app.models.document_processing import CrossDocumentReconciliation
from app.models.scrutiny import (
    ReviewStatus,
    ReviewDecision,
    FieldReviewDecision,
    CorrectionReason,
    ScrutinyAction,
    AdmissionReview,
    DocumentReviewItem,
    FieldReviewItem,
    ScrutinyAuditLog,
)
from app.schemas.scrutiny import (
    CorrectionRequestPayload,
    CompleteReviewRequest,
    ReopenReviewRequest,
    DocumentReviewRequest,
    FieldReviewRequest,
)
from app.core.state_machine import (
    AdmissionState,
    UserRole,
    can_transition,
)


class ScrutinyService:
    @staticmethod
    async def get_or_create_active_review(
        db: AsyncSession,
        application_id: str,
        reviewer_user: Optional[User] = None
    ) -> AdmissionReview:
        """
        Retrieves the latest review record for an application or initializes a new one.
        """
        stmt = (
            select(AdmissionReview)
            .where(AdmissionReview.application_id == application_id)
            .order_by(desc(AdmissionReview.created_at))
            .options(
                selectinload(AdmissionReview.document_reviews),
                selectinload(AdmissionReview.field_reviews),
                selectinload(AdmissionReview.audit_logs),
                selectinload(AdmissionReview.reviewer),
                selectinload(AdmissionReview.application),
            )
        )
        res = await db.execute(stmt)
        review = res.scalars().first()

        if not review:
            review = AdmissionReview(
                application_id=application_id,
                reviewer_id=reviewer_user.id if reviewer_user else None,
                status=ReviewStatus.NOT_STARTED.value,
                reviewed_document_versions={},
            )
            db.add(review)
            await db.flush()
            await db.refresh(review)

        return review

    @classmethod
    async def start_review(
        cls,
        db: AsyncSession,
        application_id: str,
        current_user: User,
        notes: Optional[str] = None,
    ) -> AdmissionReview:
        """
        Initializes or transitions review session to IN_REVIEW.
        Captures versioned snapshots of participating documents and latest reconciliation.
        """
        app_stmt = select(AdmissionApplication).where(AdmissionApplication.id == application_id)
        app_res = await db.execute(app_stmt)
        app = app_res.scalar_one_or_none()
        if not app:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Admission application '{application_id}' not found"
            )

        review = await cls.get_or_create_active_review(db, application_id, current_user)
        old_status = review.status

        # Snapshot document versions
        doc_stmt = (
            select(Document)
            .where(Document.application_id == application_id)
            .options(selectinload(Document.versions))
        )
        doc_res = await db.execute(doc_stmt)
        docs = doc_res.scalars().all()
        doc_version_map = {}
        for d in docs:
            if d.versions:
                doc_version_map[d.id] = d.versions[0].version_number

        # Find latest reconciliation snapshot
        recon_stmt = (
            select(CrossDocumentReconciliation)
            .where(CrossDocumentReconciliation.application_id == application_id)
            .order_by(desc(CrossDocumentReconciliation.created_at))
        )
        recon_res = await db.execute(recon_stmt)
        latest_recon = recon_res.scalars().first()

        review.reviewer_id = current_user.id
        review.status = ReviewStatus.IN_REVIEW.value
        review.started_at = datetime.now(timezone.utc)
        review.reviewed_document_versions = doc_version_map
        if latest_recon:
            review.reviewed_reconciliation_id = latest_recon.id

        # Lifecycle update on application if in submitted/processing state
        if app.status in ["APPLICATION_SUBMITTED", "DOCUMENT_PROCESSING"]:
            app.status = "DOCUMENT_REVIEW"
            app.updated_at = datetime.now(timezone.utc)

        # Append audit log
        role_name = current_user.role.name if current_user.role else "ADMIN_VERIFIER"
        audit = ScrutinyAuditLog(
            review_id=review.id,
            application_id=application_id,
            user_id=current_user.id,
            user_name=current_user.email,
            user_role=role_name,
            action=ScrutinyAction.REVIEW_STARTED.value,
            previous_status=old_status,
            new_status=ReviewStatus.IN_REVIEW.value,
            details={"notes": notes or "Scrutiny session started by reviewer"},
        )
        db.add(audit)

        await db.commit()
        await db.refresh(review)
        return review

    @classmethod
    async def get_current_review(
        cls,
        db: AsyncSession,
        application_id: str,
        current_user: User,
    ) -> AdmissionReview:
        """
        Retrieves the active review with full relationships and Anti-IDOR verification.
        """
        app_stmt = (
            select(AdmissionApplication)
            .where(AdmissionApplication.id == application_id)
            .options(selectinload(AdmissionApplication.student))
        )
        app_res = await db.execute(app_stmt)
        app = app_res.scalar_one_or_none()
        if not app:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Admission application '{application_id}' not found"
            )

        role_name = current_user.role.name if current_user.role else "STUDENT"
        if role_name == "STUDENT":
            if not app.student or app.student.user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access forbidden: You cannot view another student's scrutiny record"
                )

        review = await cls.get_or_create_active_review(db, application_id, current_user)
        return review

    @classmethod
    async def get_review_history(
        cls,
        db: AsyncSession,
        application_id: str,
        current_user: User,
    ) -> List[AdmissionReview]:
        """
        Retrieves historical reviews for an application.
        """
        stmt = (
            select(AdmissionReview)
            .where(AdmissionReview.application_id == application_id)
            .order_by(desc(AdmissionReview.created_at))
            .options(
                selectinload(AdmissionReview.document_reviews),
                selectinload(AdmissionReview.field_reviews),
                selectinload(AdmissionReview.audit_logs),
                selectinload(AdmissionReview.reviewer),
            )
        )
        res = await db.execute(stmt)
        return res.scalars().all()

    @classmethod
    async def record_document_review(
        cls,
        db: AsyncSession,
        application_id: str,
        payload: DocumentReviewRequest,
        current_user: User,
    ) -> DocumentReviewItem:
        """
        Records human verification decision for a specific document.
        """
        review = await cls.get_or_create_active_review(db, application_id, current_user)
        
        doc_stmt = (
            select(Document)
            .where(Document.id == payload.document_id, Document.application_id == application_id)
            .options(selectinload(Document.versions))
        )
        doc_res = await db.execute(doc_stmt)
        doc = doc_res.scalar_one_or_none()
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document '{payload.document_id}' not found for application '{application_id}'"
            )

        current_ver_id = doc.current_version_id
        if not current_ver_id and doc.versions:
            current_ver_id = doc.versions[0].id

        # Check existing item
        item_stmt = (
            select(DocumentReviewItem)
            .where(
                DocumentReviewItem.review_id == review.id,
                DocumentReviewItem.document_id == payload.document_id
            )
        )
        item_res = await db.execute(item_stmt)
        item = item_res.scalar_one_or_none()

        if not item:
            item = DocumentReviewItem(
                review_id=review.id,
                document_id=payload.document_id,
                document_version_id=current_ver_id,
                status=payload.status,
                correction_reason=payload.correction_reason,
                reviewer_comments=payload.reviewer_comments,
                reviewed_by_id=current_user.id,
                reviewed_at=datetime.now(timezone.utc),
            )
            db.add(item)
        else:
            item.document_version_id = current_ver_id
            item.status = payload.status
            item.correction_reason = payload.correction_reason
            item.reviewer_comments = payload.reviewer_comments
            item.reviewed_by_id = current_user.id
            item.reviewed_at = datetime.now(timezone.utc)

        role_name = current_user.role.name if current_user.role else "ADMIN_VERIFIER"
        audit = ScrutinyAuditLog(
            review_id=review.id,
            application_id=application_id,
            user_id=current_user.id,
            user_name=current_user.email,
            user_role=role_name,
            action=ScrutinyAction.DOCUMENT_REVIEWED.value,
            previous_status=None,
            new_status=payload.status,
            details={
                "document_id": payload.document_id,
                "document_version_id": current_ver_id,
                "status": payload.status,
                "correction_reason": payload.correction_reason,
                "comments": payload.reviewer_comments,
            },
        )
        db.add(audit)

        await db.commit()
        await db.refresh(item)
        return item

    @classmethod
    async def record_field_review(
        cls,
        db: AsyncSession,
        application_id: str,
        payload: FieldReviewRequest,
        current_user: User,
    ) -> FieldReviewItem:
        """
        Records human decision on an individual extracted entity/field.
        """
        review = await cls.get_or_create_active_review(db, application_id, current_user)

        item_stmt = (
            select(FieldReviewItem)
            .where(
                FieldReviewItem.review_id == review.id,
                FieldReviewItem.field_key == payload.field_key
            )
        )
        item_res = await db.execute(item_stmt)
        item = item_res.scalar_one_or_none()

        if not item:
            item = FieldReviewItem(
                review_id=review.id,
                field_key=payload.field_key,
                declared_value=payload.declared_value,
                extracted_value=payload.extracted_value,
                reconciliation_status=payload.reconciliation_status,
                decision=payload.decision,
                notes=payload.notes,
                document_id=payload.document_id,
                document_version_id=payload.document_version_id,
                reviewed_by_id=current_user.id,
                reviewed_at=datetime.now(timezone.utc),
            )
            db.add(item)
        else:
            item.declared_value = payload.declared_value or item.declared_value
            item.extracted_value = payload.extracted_value or item.extracted_value
            item.reconciliation_status = payload.reconciliation_status or item.reconciliation_status
            item.decision = payload.decision
            item.notes = payload.notes
            item.document_id = payload.document_id or item.document_id
            item.document_version_id = payload.document_version_id or item.document_version_id
            item.reviewed_by_id = current_user.id
            item.reviewed_at = datetime.now(timezone.utc)

        role_name = current_user.role.name if current_user.role else "ADMIN_VERIFIER"
        action_name = ScrutinyAction.FIELD_CONFIRMED.value if payload.decision == "CONFIRMED" else ScrutinyAction.FIELD_FLAGGED.value
        audit = ScrutinyAuditLog(
            review_id=review.id,
            application_id=application_id,
            user_id=current_user.id,
            user_name=current_user.email,
            user_role=role_name,
            action=action_name,
            previous_status=None,
            new_status=payload.decision,
            details={
                "field_key": payload.field_key,
                "decision": payload.decision,
                "notes": payload.notes,
            },
        )
        db.add(audit)

        await db.commit()
        await db.refresh(item)
        return item

    @classmethod
    async def request_correction(
        cls,
        db: AsyncSession,
        application_id: str,
        payload: CorrectionRequestPayload,
        current_user: User,
    ) -> AdmissionReview:
        """
        Executes a formal correction request from the reviewer to the student.
        Mandates structured correction reasons and requires notes if 'OTHER'.
        Transitions review and application state to CORRECTION_REQUIRED.
        """
        if not payload.correction_reason or not payload.correction_reason.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Correction reason is mandatory"
            )

        if payload.correction_reason.upper() == "OTHER" and (
            not payload.correction_instructions or not payload.correction_instructions.strip()
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reviewer instructions/comments are required when correction reason is 'OTHER'"
            )

        app_stmt = select(AdmissionApplication).where(AdmissionApplication.id == application_id)
        app_res = await db.execute(app_stmt)
        app = app_res.scalar_one_or_none()
        if not app:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Admission application '{application_id}' not found"
            )

        review = await cls.get_or_create_active_review(db, application_id, current_user)
        old_review_status = review.status

        review.status = ReviewStatus.CORRECTION_REQUIRED.value
        review.decision = ReviewDecision.CORRECTION_REQUIRED.value
        review.correction_reason = payload.correction_reason
        review.correction_instructions = payload.correction_instructions
        review.reviewer_id = current_user.id
        review.updated_at = datetime.now(timezone.utc)

        # Flag individual documents if specified
        if payload.flagged_document_ids:
            for doc_id in payload.flagged_document_ids:
                doc_stmt = select(Document).where(Document.id == doc_id, Document.application_id == application_id)
                doc_res = await db.execute(doc_stmt)
                doc = doc_res.scalar_one_or_none()
                if doc:
                    # Upsert DocumentReviewItem without mutating Document.status
                    item_stmt = select(DocumentReviewItem).where(
                        DocumentReviewItem.review_id == review.id,
                        DocumentReviewItem.document_id == doc_id
                    )
                    item_res = await db.execute(item_stmt)
                    item = item_res.scalar_one_or_none()
                    if not item:
                        item = DocumentReviewItem(
                            review_id=review.id,
                            document_id=doc_id,
                            document_version_id=doc.current_version_id,
                            status="CORRECTION_REQUIRED",
                            correction_reason=payload.correction_reason,
                            reviewer_comments=payload.correction_instructions,
                            reviewed_by_id=current_user.id,
                            reviewed_at=datetime.now(timezone.utc),
                        )
                        db.add(item)
                    else:
                        item.status = "CORRECTION_REQUIRED"
                        item.correction_reason = payload.correction_reason
                        item.reviewer_comments = payload.correction_instructions
                        item.reviewed_by_id = current_user.id
                        item.reviewed_at = datetime.now(timezone.utc)

        role_name = current_user.role.name if current_user.role else "ADMIN_VERIFIER"

        # Audit Log
        audit = ScrutinyAuditLog(
            review_id=review.id,
            application_id=application_id,
            user_id=current_user.id,
            user_name=current_user.email,
            user_role=role_name,
            action=ScrutinyAction.CORRECTION_REQUESTED.value,
            previous_status=old_review_status,
            new_status=ReviewStatus.CORRECTION_REQUIRED.value,
            details={
                "reason": payload.correction_reason,
                "instructions": payload.correction_instructions,
                "flagged_documents": payload.flagged_document_ids or [],
            },
        )
        db.add(audit)

        await db.commit()
        await db.refresh(review)
        return review

    @classmethod
    async def complete_review(
        cls,
        db: AsyncSession,
        application_id: str,
        payload: CompleteReviewRequest,
        current_user: User,
    ) -> AdmissionReview:
        """
        Records the final human verification decision on an application.
        Strictly requires human verifier intervention. Machine AI results NEVER automatically trigger this.
        Decoupled from AdmissionApplication.status and Document.status to maintain state machine safety.
        """
        valid_decisions = {ReviewDecision.VERIFIED.value, ReviewDecision.CORRECTION_REQUIRED.value, ReviewDecision.REJECTED.value}
        if payload.decision.upper() not in valid_decisions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid review decision '{payload.decision}'. Allowed: {valid_decisions}"
            )

        app_stmt = select(AdmissionApplication).where(AdmissionApplication.id == application_id)
        app_res = await db.execute(app_stmt)
        app = app_res.scalar_one_or_none()
        if not app:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Admission application '{application_id}' not found"
            )

        review = await cls.get_or_create_active_review(db, application_id, current_user)
        old_review_status = review.status

        # Snapshot active document versions at completion time
        doc_stmt = (
            select(Document)
            .where(Document.application_id == application_id)
            .options(selectinload(Document.versions))
        )
        doc_res = await db.execute(doc_stmt)
        docs = doc_res.scalars().all()
        doc_version_map = {}
        for d in docs:
            if d.versions:
                doc_version_map[d.id] = d.versions[0].version_number

        recon_stmt = (
            select(CrossDocumentReconciliation)
            .where(CrossDocumentReconciliation.application_id == application_id)
            .order_by(desc(CrossDocumentReconciliation.created_at))
        )
        recon_res = await db.execute(recon_stmt)
        latest_recon = recon_res.scalars().first()

        dec = payload.decision.upper()
        review.decision = dec
        review.overall_comments = payload.overall_comments
        review.completed_at = datetime.now(timezone.utc)
        review.reviewer_id = current_user.id
        review.reviewed_document_versions = doc_version_map
        if latest_recon:
            review.reviewed_reconciliation_id = latest_recon.id

        role_name = current_user.role.name if current_user.role else "ADMIN_VERIFIER"

        if dec == ReviewDecision.VERIFIED.value:
            review.status = ReviewStatus.VERIFIED.value
        elif dec == ReviewDecision.REJECTED.value:
            review.status = ReviewStatus.REJECTED.value
        elif dec == ReviewDecision.CORRECTION_REQUIRED.value:
            review.status = ReviewStatus.CORRECTION_REQUIRED.value

        audit = ScrutinyAuditLog(
            review_id=review.id,
            application_id=application_id,
            user_id=current_user.id,
            user_name=current_user.email,
            user_role=role_name,
            action=ScrutinyAction.REVIEW_COMPLETED.value,
            previous_status=old_review_status,
            new_status=review.status,
            details={
                "decision": dec,
                "comments": payload.overall_comments,
                "document_versions_snapshot": doc_version_map,
                "reconciliation_id": latest_recon.id if latest_recon else None,
            },
        )
        db.add(audit)

        await db.commit()
        await db.refresh(review)
        return review

    @classmethod
    async def reopen_review(
        cls,
        db: AsyncSession,
        application_id: str,
        payload: ReopenReviewRequest,
        current_user: User,
    ) -> AdmissionReview:
        """
        Reopens a finalized scrutiny review.
        RBAC: Restricted strictly to ADMISSION_HEAD and SUPER_ADMIN.
        Decoupled from AdmissionApplication.status to preserve state machine safety.
        """
        role_name = current_user.role.name if current_user.role else ""
        if role_name not in ["ADMISSION_HEAD", "SUPER_ADMIN"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: Only ADMISSION_HEAD or SUPER_ADMIN can reopen a review. Your role is '{role_name}'"
            )

        if not payload.reason or not payload.reason.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reopening justification reason is required"
            )

        app_stmt = select(AdmissionApplication).where(AdmissionApplication.id == application_id)
        app_res = await db.execute(app_stmt)
        app = app_res.scalar_one_or_none()
        if not app:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Admission application '{application_id}' not found"
            )

        review = await cls.get_or_create_active_review(db, application_id, current_user)
        old_review_status = review.status

        review.status = ReviewStatus.IN_REVIEW.value
        review.completed_at = None
        review.updated_at = datetime.now(timezone.utc)

        audit = ScrutinyAuditLog(
            review_id=review.id,
            application_id=application_id,
            user_id=current_user.id,
            user_name=current_user.email,
            user_role=role_name,
            action=ScrutinyAction.REVIEW_REOPENED.value,
            previous_status=old_review_status,
            new_status=ReviewStatus.IN_REVIEW.value,
            details={"reason": payload.reason},
        )
        db.add(audit)

        await db.commit()
        await db.refresh(review)
        return review

    @classmethod
    async def get_student_corrections(
        cls,
        db: AsyncSession,
        student: Student,
    ) -> dict:
        """
        Retrieves pending correction requests for the authenticated candidate.
        Enforces strict Anti-IDOR and leaks no internal reviewer-only notes.
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

        review = await cls.get_or_create_active_review(db, app.id)

        is_correction_req = (
            review.status == ReviewStatus.CORRECTION_REQUIRED.value
        )

        affected_docs = []
        if is_correction_req and app.documents:
            # Check for document review items
            rev_items_stmt = select(DocumentReviewItem).where(
                DocumentReviewItem.review_id == review.id,
                DocumentReviewItem.status == "CORRECTION_REQUIRED"
            )
            rev_items_res = await db.execute(rev_items_stmt)
            flagged_items = {item.document_id: item for item in rev_items_res.scalars().all()}

            for d in app.documents:
                flagged_item = flagged_items.get(d.id)
                if flagged_item:
                    v_num = d.versions[0].version_number if d.versions else 1
                    affected_docs.append({
                        "document_id": d.id,
                        "document_type_code": d.document_type.code if d.document_type else "",
                        "document_type_name": d.document_type.name if d.document_type else "",
                        "current_version_number": v_num,
                        "correction_reason": flagged_item.correction_reason if flagged_item.correction_reason else review.correction_reason,
                        "reviewer_comments": flagged_item.reviewer_comments if flagged_item.reviewer_comments else review.correction_instructions,
                    })
                elif not flagged_items:
                    # If whole application correction requested without specific document flags
                    v_num = d.versions[0].version_number if d.versions else 1
                    affected_docs.append({
                        "document_id": d.id,
                        "document_type_code": d.document_type.code if d.document_type else "",
                        "document_type_name": d.document_type.name if d.document_type else "",
                        "current_version_number": v_num,
                        "correction_reason": review.correction_reason,
                        "reviewer_comments": review.correction_instructions,
                    })

        return {
            "application_id": app.id,
            "application_status": app.status,
            "review_status": review.status,
            "correction_required": is_correction_req,
            "correction_reason": review.correction_reason if is_correction_req else None,
            "correction_instructions": review.correction_instructions if is_correction_req else None,
            "requested_at": review.updated_at if is_correction_req else None,
            "affected_documents": affected_docs,
        }

    @classmethod
    async def record_resubmission(
        cls,
        db: AsyncSession,
        application_id: str,
        document_id: str,
        document_version: DocumentVersion,
        student_user: User,
    ) -> None:
        """
        Called when candidate uploads replacement document during correction phase.
        Sets review status to RESUBMISSION_PENDING and logs audit trail.
        """
        review = await cls.get_or_create_active_review(db, application_id)
        old_status = review.status

        if review.status == ReviewStatus.CORRECTION_REQUIRED.value:
            review.status = ReviewStatus.RESUBMISSION_PENDING.value
            review.updated_at = datetime.now(timezone.utc)

        role_name = student_user.role.name if student_user.role else "STUDENT"
        audit = ScrutinyAuditLog(
            review_id=review.id,
            application_id=application_id,
            user_id=student_user.id,
            user_name=student_user.email,
            user_role=role_name,
            action=ScrutinyAction.RESUBMISSION_RECEIVED.value,
            previous_status=old_status,
            new_status=review.status,
            details={
                "document_id": document_id,
                "new_version_number": document_version.version_number,
                "filename": document_version.original_filename,
            },
        )
        db.add(audit)
        await db.commit()
