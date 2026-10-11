from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.models.admission import AdmissionApplication
from app.models.document import Document
from app.models.document_processing import (
    ClassificationResult,
    PreprocessingResult,
    OCRResult,
    DocumentExtractionResult,
    CrossDocumentReconciliation,
)
from app.models.scrutiny import AdmissionReview
from app.models.physical_verification import (
    PhysicalVerificationAppointment,
    PhysicalVerificationSession,
)
from app.models.payment import PaymentTransaction
from app.models.erp import ERPAdmissionRecord
from app.models.notification import Notification


class AnalyticsService:
    @classmethod
    async def get_overview_metrics(
        cls,
        db: AsyncSession,
        date_filter: str = "all_time",
        start_date_str: Optional[str] = None,
        end_date_str: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Calculates operational descriptive metrics computed directly from active database records.
        Strictly READ-ONLY.
        """
        now = datetime.now(timezone.utc)
        filter_start = None
        filter_end = now

        if date_filter == "today":
            filter_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif date_filter == "last_7_days":
            filter_start = now - timedelta(days=7)
        elif date_filter == "last_30_days":
            filter_start = now - timedelta(days=30)
        elif date_filter == "custom" and start_date_str:
            try:
                filter_start = datetime.fromisoformat(start_date_str)
                if end_date_str:
                    filter_end = datetime.fromisoformat(end_date_str)
            except Exception:
                filter_start = None

        # 1. Applications Metrics
        stmt_apps = select(AdmissionApplication)
        if filter_start:
            stmt_apps = stmt_apps.where(AdmissionApplication.created_at >= filter_start)
        res_apps = await db.execute(stmt_apps)
        all_apps = res_apps.scalars().all()
        total_apps = len(all_apps)
        submitted_apps = sum(1 for a in all_apps if a.status in ["APPLICATION_SUBMITTED", "DOCUMENT_REVIEW", "DOCUMENTS_VERIFIED", "ADMISSION_CONFIRMED", "ACTIVE_STUDENT"])
        incomplete_apps = sum(1 for a in all_apps if a.status in ["ACTIVATION_PENDING", "ACTIVATED", "APPLICATION_IN_PROGRESS"])
        corr_req_apps = sum(1 for a in all_apps if a.status == "CORRECTION_REQUIRED")

        # 2. Document & Processing Metrics
        stmt_docs = select(Document)
        if filter_start:
            stmt_docs = stmt_docs.where(Document.created_at >= filter_start)
        res_docs = await db.execute(stmt_docs)
        all_docs = res_docs.scalars().all()
        total_docs = len(all_docs)
        verified_docs = sum(1 for d in all_docs if d.status == "DOCUMENTS_VERIFIED")
        corr_docs = sum(1 for d in all_docs if d.status in ["CORRECTION_REQUIRED", "RESUBMISSION_REQUIRED"])
        
        res_ocr = await db.execute(select(func.count(OCRResult.id)))
        ocr_count = res_ocr.scalar() or 0
        
        res_ext = await db.execute(select(func.count(DocumentExtractionResult.id)))
        extract_count = res_ext.scalar() or 0
        
        res_rec = await db.execute(select(func.count(CrossDocumentReconciliation.id)))
        reconcile_count = res_rec.scalar() or 0

        # 3. Physical Verification Metrics
        stmt_appts = select(PhysicalVerificationAppointment)
        if filter_start:
            stmt_appts = stmt_appts.where(PhysicalVerificationAppointment.created_at >= filter_start)
        res_appts = await db.execute(stmt_appts)
        all_appts = res_appts.scalars().all()
        total_appts = len(all_appts)
        checked_in_appts = sum(1 for p in all_appts if p.appointment_status in ["CHECKED_IN", "IN_PROGRESS", "COMPLETED"])

        stmt_sess = select(PhysicalVerificationSession)
        if filter_start:
            stmt_sess = stmt_sess.where(PhysicalVerificationSession.created_at >= filter_start)
        res_sess = await db.execute(stmt_sess)
        all_sessions = res_sess.scalars().all()
        completed_sessions = sum(1 for s in all_sessions if s.session_status == "COMPLETED")
        verified_sessions = sum(1 for s in all_sessions if s.overall_decision in ["VERIFIED", "PARTIALLY_VERIFIED"])
        corr_sessions = sum(1 for s in all_sessions if s.overall_decision == "CORRECTION_REQUIRED")
        rejected_sessions = sum(1 for s in all_sessions if s.overall_decision == "REJECTED")

        # 4. Payment Metrics
        stmt_pay = select(PaymentTransaction)
        if filter_start:
            stmt_pay = stmt_pay.where(PaymentTransaction.created_at >= filter_start)
        res_pay = await db.execute(stmt_pay)
        all_payments = res_pay.scalars().all()
        total_payments = len(all_payments)
        pending_payments = sum(1 for p in all_payments if p.status in ["INITIATED", "PENDING"])
        submitted_payments = sum(1 for p in all_payments if p.status in ["SUBMITTED", "UNDER_REVIEW"])
        verified_payments = sum(1 for p in all_payments if p.status == "VERIFIED")
        rejected_payments = sum(1 for p in all_payments if p.status in ["REJECTED", "FAILED"])
        corr_payments = sum(1 for p in all_payments if p.status == "CORRECTION_REQUIRED")

        # 5. ERP Metrics
        stmt_erp = select(ERPAdmissionRecord)
        if filter_start:
            stmt_erp = stmt_erp.where(ERPAdmissionRecord.created_at >= filter_start)
        res_erp = await db.execute(stmt_erp)
        all_erp = res_erp.scalars().all()
        total_erp = len(all_erp)
        staged_erp = sum(1 for e in all_erp if e.status == "STAGED")
        synced_erp = sum(1 for e in all_erp if e.status == "SYNCED")
        failed_erp = sum(1 for e in all_erp if e.status in ["SYNC_FAILED", "RETRY_PENDING"])

        # 6. Notifications Metrics
        stmt_notif = select(Notification)
        if filter_start:
            stmt_notif = stmt_notif.where(Notification.created_at >= filter_start)
        res_notif = await db.execute(stmt_notif)
        all_notifs = res_notif.scalars().all()
        total_notifs = len(all_notifs)
        unread_notifs = sum(1 for n in all_notifs if n.read_at is None)

        # 7. Processing Times (in hours)
        avg_app_time = cls._calculate_avg_app_review_time(all_apps)
        avg_phys_time = cls._calculate_avg_physical_time(all_sessions)
        avg_pay_time = cls._calculate_avg_payment_time(all_payments)
        avg_erp_time = cls._calculate_avg_erp_sync_time(all_erp)

        # 8. Operational Bottlenecks
        bottlenecks = []
        if corr_req_apps > 0:
            bottlenecks.append({
                "stage": "Document Scrutiny",
                "severity": "WARNING",
                "count": corr_req_apps,
                "message": f"{corr_req_apps} application(s) awaiting student certificate correction resubmission.",
            })
        if submitted_payments > 0:
            bottlenecks.append({
                "stage": "Finance Review",
                "severity": "INFO",
                "count": submitted_payments,
                "message": f"{submitted_payments} Demand Draft submission(s) pending finance officer verification.",
            })
        if failed_erp > 0:
            bottlenecks.append({
                "stage": "ERP Synchronization",
                "severity": "ERROR",
                "count": failed_erp,
                "message": f"{failed_erp} staged ERP record(s) failed synchronization and require retry.",
            })

        return {
            "institution_name": "XYZ Engineering College",
            "academic_year": "2026-27",
            "date_filter": date_filter,
            "filter_start_date": filter_start.isoformat() if filter_start else None,
            "filter_end_date": filter_end.isoformat() if filter_end else None,
            "applications": {
                "total": total_apps,
                "submitted": submitted_apps,
                "incomplete": incomplete_apps,
                "correction_required": corr_req_apps,
            },
            "documents": {
                "total_uploaded": total_docs,
                "verified": verified_docs,
                "correction_required": corr_docs,
                "ocr_processed": ocr_count,
                "fields_extracted": extract_count,
                "reconciled": reconcile_count,
            },
            "physical_verification": {
                "appointments_scheduled": total_appts,
                "checked_in": checked_in_appts,
                "sessions_completed": completed_sessions,
                "verified": verified_sessions,
                "correction_required": corr_sessions,
                "rejected": rejected_sessions,
            },
            "payments": {
                "total_transactions": total_payments,
                "pending": pending_payments,
                "submitted_for_review": submitted_payments,
                "verified": verified_payments,
                "rejected": rejected_payments,
                "correction_required": corr_payments,
            },
            "erp": {
                "total_records": total_erp,
                "staged": staged_erp,
                "synced": synced_erp,
                "sync_failed": failed_erp,
            },
            "notifications": {
                "total_dispatched": total_notifs,
                "unread": unread_notifs,
            },
            "bottlenecks": bottlenecks,
            "processing_times_hours": {
                "application_review": avg_app_time,
                "physical_verification": avg_phys_time,
                "payment_verification": avg_pay_time,
                "erp_synchronization": avg_erp_time,
            },
        }

    @staticmethod
    def _calculate_avg_app_review_time(apps: List[AdmissionApplication]) -> Optional[float]:
        durations = []
        for a in apps:
            if a.submitted_at and a.updated_at and a.status in ["DOCUMENTS_VERIFIED", "ADMISSION_CONFIRMED"]:
                delta = (a.updated_at - a.submitted_at).total_seconds() / 3600.0
                if delta >= 0:
                    durations.append(delta)
        return round(sum(durations) / len(durations), 2) if durations else None

    @staticmethod
    def _calculate_avg_physical_time(sessions: List[PhysicalVerificationSession]) -> Optional[float]:
        durations = []
        for s in sessions:
            if s.started_at and s.completed_at:
                delta = (s.completed_at - s.started_at).total_seconds() / 3600.0
                if delta >= 0:
                    durations.append(delta)
        return round(sum(durations) / len(durations), 2) if durations else None

    @staticmethod
    def _calculate_avg_payment_time(payments: List[PaymentTransaction]) -> Optional[float]:
        durations = []
        for p in payments:
            if p.submitted_at and p.verified_at:
                delta = (p.verified_at - p.submitted_at).total_seconds() / 3600.0
                if delta >= 0:
                    durations.append(delta)
        return round(sum(durations) / len(durations), 2) if durations else None

    @staticmethod
    def _calculate_avg_erp_sync_time(records: List[ERPAdmissionRecord]) -> Optional[float]:
        durations = []
        for r in records:
            if r.staged_at and r.synced_at:
                delta = (r.synced_at - r.staged_at).total_seconds() / 3600.0
                if delta >= 0:
                    durations.append(delta)
        return round(sum(durations) / len(durations), 2) if durations else None
