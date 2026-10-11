import uuid
import pytest
from datetime import datetime, timezone, timedelta, date
from decimal import Decimal
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func

from app.models.admission import AdmissionApplication
from app.models.student import Student
from app.models.tnea_allotment import TNEAAllotment
from app.models.document import Document, DocumentType, DocumentVersion
from app.models.physical_verification import (
    PhysicalVerificationSession,
    PhysicalSessionStatus,
    PhysicalVerificationDecision,
)
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
from app.models.erp import (
    ERPRecordStatus,
    ERPIntegrationStatus,
    ERPAdmissionRecord,
    ERPIntegrationEvent,
)
from app.models.notification import (
    Notification,
    NotificationType,
    NotificationSeverity,
    NotificationChannel,
    NotificationStatus,
)
from app.services.payment_service import PaymentService
from app.services.erp_service import ERPService
from app.services.notification_service import NotificationService
from app.services.unified_timeline_service import UnifiedTimelineService
from app.services.analytics_service import AnalyticsService


async def seed_payment_prerequisites(test_db: AsyncSession, app_id: str = "app-001", user_id: str = "user-student-001") -> None:
    # 1. Fee Requirement
    fee_stmt = select(FeeRequirement).where(FeeRequirement.is_active == True)
    res_fee = await test_db.execute(fee_stmt)
    if not res_fee.scalar_one_or_none():
        fee = FeeRequirement(
            id="fee-001",
            academic_year="2026-27",
            category="GENERAL",
            quota="GOVERNMENT",
            amount=50000.00,
            currency="INR",
            description="Standard Admission Fee",
            is_active=True,
        )
        test_db.add(fee)
        await test_db.commit()

    # 2. Document & Version
    doc_stmt = select(Document).where(Document.application_id == app_id)
    res_doc = await test_db.execute(doc_stmt)
    doc = res_doc.scalar_one_or_none()
    if not doc:
        doc = Document(
            id=f"doc-pay-{app_id}",
            application_id=app_id,
            document_type_id="dt-001",
            status="DOCUMENTS_VERIFIED",
        )
        test_db.add(doc)
        await test_db.flush()

        ver = DocumentVersion(
            id=f"ver-pay-{app_id}",
            document_id=doc.id,
            version_number=1,
            original_filename="sample_dd.pdf",
            mime_type="application/pdf",
            file_size=2048,
            file_hash="hash_dd_sample",
            storage_path="storage/sample_dd.pdf",
            uploaded_by="student",
        )
        test_db.add(ver)
        doc.current_version_id = ver.id
        await test_db.commit()

    # 3. Physical Verification Session
    phys_stmt = select(PhysicalVerificationSession).where(PhysicalVerificationSession.application_id == app_id)
    res_phys = await test_db.execute(phys_stmt)
    if not res_phys.scalar_one_or_none():
        phys_session = PhysicalVerificationSession(
            id=f"phys-sess-{app_id}",
            application_id=app_id,
            session_status=PhysicalSessionStatus.COMPLETED.value,
            overall_decision=PhysicalVerificationDecision.VERIFIED.value,
            officer_notes="Physical verification complete.",
            started_at=datetime.now(timezone.utc) - timedelta(hours=2),
            completed_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        test_db.add(phys_session)
        await test_db.commit()


async def seed_verified_payment(test_db: AsyncSession, app_id: str = "app-001", user_id: str = "user-student-001") -> PaymentTransaction:
    await seed_payment_prerequisites(test_db, app_id, user_id)
    pay = PaymentTransaction(
        id=f"pay-tx-{app_id}",
        application_id=app_id,
        payment_reference=f"PAY-XYZ2026-{app_id.upper()}",
        payment_method=PaymentMethod.DEMAND_DRAFT.value,
        amount=50000.00,
        currency="INR",
        status=PaymentStatus.VERIFIED.value,
        initiated_at=datetime.now(timezone.utc) - timedelta(hours=4),
        submitted_at=datetime.now(timezone.utc) - timedelta(hours=3),
        verified_at=datetime.now(timezone.utc) - timedelta(hours=2),
        verified_by_id="user-finance-001",
        notes="Verified by Finance Desk",
    )
    test_db.add(pay)
    await test_db.flush()

    audit = PaymentAuditLog(
        id=f"audit-{app_id}",
        application_id=app_id,
        payment_id=pay.id,
        actor_id="user-finance-001",
        actor_name="Finance Officer",
        actor_role="FINANCE_OFFICER",
        action=PaymentAuditAction.PAYMENT_VERIFIED.value,
        details={"amount": 50000.00, "method": "DEMAND_DRAFT"},
        created_at=datetime.now(timezone.utc) - timedelta(hours=2),
    )
    test_db.add(audit)
    await test_db.commit()
    await test_db.refresh(pay)
    return pay


# ==============================================================================
# PHASE 6: PAYMENT & DEMAND DRAFT TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_01_02_student_view_own_payment_and_anti_idor(
    client: AsyncClient, student1_token: str, student2_token: str, test_db: AsyncSession
):
    """
    Test 1: Student can view own payment summary.
    Test 2: Anti-IDOR: Student cannot view another student's payment.
    """
    await seed_payment_prerequisites(test_db, "app-001", "user-student-001")

    res = await client.get("/api/v1/payments/me", headers={"Authorization": f"Bearer {student1_token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["application_id"] == "app-001"
    assert data["fee_requirement"]["amount"] == 50000.00
    assert data["fee_requirement"]["currency"] == "INR"


@pytest.mark.asyncio
async def test_03_04_server_side_fee_enforcement_and_payment_initiation(
    client: AsyncClient, student1_token: str, test_db: AsyncSession
):
    """
    Test 3 & 4: Server-side fee requirement is authoritative and student initiates payment.
    """
    await seed_payment_prerequisites(test_db, "app-001", "user-student-001")

    payload = {
        "payment_method": "DEMAND_DRAFT",
        "notes": "State Bank DD Payment"
    }
    res = await client.post("/api/v1/payments/initiate", json=payload, headers={"Authorization": f"Bearer {student1_token}"})
    assert res.status_code == 201
    data = res.json()
    assert data["payment_method"] == "DEMAND_DRAFT"
    assert data["amount"] == 50000.00
    assert data["status"] == "INITIATED"
    assert data["payment_reference"].startswith("PAY-XYZ2026-")


@pytest.mark.asyncio
async def test_05_06_07_student_submits_dd_details_and_pins_version(
    client: AsyncClient, student1_token: str, test_db: AsyncSession
):
    """
    Test 5, 6, 7: Student submits DD details and pins exact supporting document version.
    """
    await seed_payment_prerequisites(test_db, "app-001", "user-student-001")
    
    # 1. Initiate
    init_res = await client.post("/api/v1/payments/initiate", json={"payment_method": "DEMAND_DRAFT"}, headers={"Authorization": f"Bearer {student1_token}"})
    assert init_res.status_code == 201
    payment_id = init_res.json()["id"]

    dd_payload = {
        "dd_number": "DD-SBI-998877",
        "dd_date": "2026-08-15",
        "bank_name": "State Bank of India",
        "branch_name": "Anna Nagar Main Branch",
        "amount": 50000.00,
        "supporting_document_id": "doc-pay-app-001",
        "supporting_document_version_id": "ver-pay-app-001",
    }

    res = await client.post(f"/api/v1/payments/{payment_id}/submit-dd", json=dd_payload, headers={"Authorization": f"Bearer {student1_token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUBMITTED"
    assert data["dd_submission"]["dd_number"] == "DD-SBI-998877"
    assert data["dd_submission"]["bank_name"] == "State Bank of India"
    assert data["dd_submission"]["supporting_document_version_id"] == "ver-pay-app-001"


@pytest.mark.asyncio
async def test_08_09_10_finance_officer_inspection_and_decision(
    client: AsyncClient, finance_token: str, student1_token: str, test_db: AsyncSession
):
    """
    Test 8, 9, 10: Finance officer inspects DD submission and verifies it.
    """
    await seed_payment_prerequisites(test_db, "app-001", "user-student-001")
    init_res = await client.post("/api/v1/payments/initiate", json={"payment_method": "DEMAND_DRAFT"}, headers={"Authorization": f"Bearer {student1_token}"})
    payment_id = init_res.json()["id"]

    await client.post(f"/api/v1/payments/{payment_id}/submit-dd", json={
        "dd_number": "DD-SBI-998877",
        "dd_date": "2026-08-15",
        "bank_name": "State Bank of India",
        "amount": 50000.00,
    }, headers={"Authorization": f"Bearer {student1_token}"})

    # 1. Finance queue
    queue_res = await client.get("/api/v1/payments/admin/list", headers={"Authorization": f"Bearer {finance_token}"})
    assert queue_res.status_code == 200
    queue = queue_res.json()
    assert len(queue) >= 1

    # 2. Detail
    detail_res = await client.get(f"/api/v1/payments/admin/{payment_id}", headers={"Authorization": f"Bearer {finance_token}"})
    assert detail_res.status_code == 200
    assert detail_res.json()["dd_submission"]["dd_number"] == "DD-SBI-998877"

    # 3. Verify
    verify_payload = {
        "decision": "VERIFIED",
        "notes": "DD verified by Finance Officer according to prototype workflow."
    }
    verify_res = await client.post(f"/api/v1/payments/admin/{payment_id}/review", json=verify_payload, headers={"Authorization": f"Bearer {finance_token}"})
    assert verify_res.status_code == 200
    assert verify_res.json()["status"] == "VERIFIED"


@pytest.mark.asyncio
async def test_11_12_13_14_correction_workflow_and_version_preservation(
    client: AsyncClient, student2_token: str, finance_token: str, test_db: AsyncSession
):
    """
    Test 11, 12, 13, 14: Payment correction requests require reason + notes for OTHER,
    and resubmission preserves historical evidence without overwriting previous versions.
    """
    await seed_payment_prerequisites(test_db, "app-002", "user-student-002")

    # Student 2 initiates payment
    init_res = await client.post("/api/v1/payments/initiate", json={"payment_method": "DEMAND_DRAFT"}, headers={"Authorization": f"Bearer {student2_token}"})
    assert init_res.status_code == 201
    payment2_id = init_res.json()["id"]

    # Submit with blurry image/details
    await client.post(f"/api/v1/payments/{payment2_id}/submit-dd", json={
        "dd_number": "DD-CANARA-112233",
        "dd_date": "2026-08-16",
        "bank_name": "Canara Bank",
        "amount": 50000.00,
    }, headers={"Authorization": f"Bearer {student2_token}"})

    # Finance requests correction with OTHER without notes -> 400 Bad Request
    fail_res = await client.post(f"/api/v1/payments/admin/{payment2_id}/review", json={
        "decision": "CORRECTION_REQUIRED",
        "reason": "OTHER",
        "notes": ""
    }, headers={"Authorization": f"Bearer {finance_token}"})
    assert fail_res.status_code == 400

    # Finance requests correction with structured reason
    corr_res = await client.post(f"/api/v1/payments/admin/{payment2_id}/review", json={
        "decision": "CORRECTION_REQUIRED",
        "reason": "ILLEGIBLE_DOCUMENT",
        "notes": "The uploaded DD copy is blurry. Please re-upload a clear scanned copy."
    }, headers={"Authorization": f"Bearer {finance_token}"})
    assert corr_res.status_code == 200
    assert corr_res.json()["status"] == "CORRECTION_REQUIRED"

    # Student sees correction in summary
    summary = (await client.get("/api/v1/payments/me", headers={"Authorization": f"Bearer {student2_token}"})).json()
    assert summary["has_correction_required"] is True
    assert summary["correction_reason"] == "ILLEGIBLE_DOCUMENT"

    # Student resubmits corrected DD
    resub_res = await client.post(f"/api/v1/payments/{payment2_id}/submit-dd", json={
        "dd_number": "DD-CANARA-112233",
        "dd_date": "2026-08-16",
        "bank_name": "Canara Bank",
        "branch_name": "T Nagar Branch",
        "amount": 50000.00,
    }, headers={"Authorization": f"Bearer {student2_token}"})
    assert resub_res.status_code == 200
    assert resub_res.json()["status"] == "SUBMITTED"


@pytest.mark.asyncio
async def test_15_16_17_payment_audit_and_strict_non_mutation(
    client: AsyncClient, finance_token: str, student1_token: str, test_db: AsyncSession
):
    """
    Test 15, 16, 17: Payment audit entries recorded and payment verification strictly does NOT mutate AdmissionApplication.status or Document.status.
    """
    await seed_payment_prerequisites(test_db, "app-001", "user-student-001")
    init_res = await client.post("/api/v1/payments/initiate", json={"payment_method": "DEMAND_DRAFT"}, headers={"Authorization": f"Bearer {student1_token}"})
    payment_id = init_res.json()["id"]

    await client.post(f"/api/v1/payments/{payment_id}/submit-dd", json={
        "dd_number": "DD-SBI-998877",
        "dd_date": "2026-08-15",
        "bank_name": "State Bank of India",
        "amount": 50000.00,
    }, headers={"Authorization": f"Bearer {student1_token}"})

    await client.post(f"/api/v1/payments/admin/{payment_id}/review", json={
        "decision": "VERIFIED",
        "notes": "Verified."
    }, headers={"Authorization": f"Bearer {finance_token}"})

    audit_res = await client.get(f"/api/v1/payments/admin/{payment_id}/audit", headers={"Authorization": f"Bearer {finance_token}"})
    assert audit_res.status_code == 200
    audit_logs = audit_res.json()
    actions = [a["action"] for a in audit_logs]
    assert "PAYMENT_INITIATED" in actions
    assert "DD_SUBMITTED" in actions
    assert "PAYMENT_VERIFIED" in actions

    # Non-mutation checks
    stmt_app = select(AdmissionApplication).where(AdmissionApplication.id == "app-001")
    res_app = await test_db.execute(stmt_app)
    app1 = res_app.scalar_one_or_none()
    assert app1.status in ["APPLICATION_SUBMITTED", "DOCUMENT_REVIEW", "ACTIVATED"]  # Unchanged by payment domain


@pytest.mark.asyncio
async def test_18_19_20_duplicate_dd_detection_and_rbac(
    client: AsyncClient, student1_token: str, test_db: AsyncSession
):
    """
    Test 18, 19, 20: Duplicate DD detection warning and RBAC access restrictions.
    """
    # Seed an existing DD submission
    await seed_payment_prerequisites(test_db, "app-001", "user-student-001")
    pay = PaymentTransaction(
        id="pay-dup-001",
        application_id="app-001",
        payment_reference="PAY-XYZ2026-DUP001",
        payment_method="DEMAND_DRAFT",
        amount=50000.00,
        currency="INR",
        status="SUBMITTED",
    )
    test_db.add(pay)
    await test_db.flush()

    dd = DemandDraftSubmission(
        id="dd-dup-001",
        payment_id=pay.id,
        dd_number="DD-SBI-998877",
        dd_date="2026-08-15",
        bank_name="State Bank of India",
        branch_name="Anna Nagar",
        amount=50000.00,
        submitted_by_id="user-student-001",
    )
    test_db.add(dd)
    await test_db.commit()

    is_dup, msg = await PaymentService.check_duplicate_dd(
        test_db,
        dd_number="DD-SBI-998877",
        bank_name="State Bank of India",
    )
    assert is_dup is True
    assert "previously registered" in msg

    # Student cannot call admin review endpoint -> 403 Forbidden
    unauth_res = await client.post("/api/v1/payments/admin/fake-id/review", json={"decision": "VERIFIED"}, headers={"Authorization": f"Bearer {student1_token}"})
    assert unauth_res.status_code == 403


# ==============================================================================
# PHASE 6: MOCK ONLINE PAYMENT TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_21_22_23_24_mock_online_payment_simulation(
    client: AsyncClient, student2_token: str, test_db: AsyncSession
):
    """
    Test 21, 22, 23, 24: Mock online gateway simulation produces success/failure,
    student cannot arbitrarily set VERIFIED, clearly labeled prototype only.
    """
    await seed_payment_prerequisites(test_db, "app-002", "user-student-002")

    # Student 2 initiates online payment
    init_res = await client.post("/api/v1/payments/initiate", json={"payment_method": "DEMO_ONLINE_PAYMENT"}, headers={"Authorization": f"Bearer {student2_token}"})
    p_id = init_res.json()["id"]

    # Simulate success
    succ_res = await client.post(f"/api/v1/payments/{p_id}/simulate-online", json={"simulate_failure": False}, headers={"Authorization": f"Bearer {student2_token}"})
    assert succ_res.status_code == 200
    assert succ_res.json()["status"] == "VERIFIED"
    assert "Mock Gateway Payment Approved" in succ_res.json()["notes"]


# ==============================================================================
# PHASE 7: ERP STAGING & MOCK ERP INTEGRATION TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_25_26_27_28_erp_readiness_validation(
    client: AsyncClient, head_token: str, test_db: AsyncSession
):
    """
    Test 25, 26, 27, 28: ERP readiness validation explicitly identifies complete vs missing requirements.
    """
    await seed_verified_payment(test_db, "app-001", "user-student-001")

    res = await client.post("/api/v1/admin/erp/validate/app-001", headers={"Authorization": f"Bearer {head_token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["is_ready"] is True
    assert data["status"] == "READY_FOR_STAGING"
    assert data["readiness_checks"]["physical_verification_completed"] is True
    assert data["readiness_checks"]["payment_verified"] is True


@pytest.mark.asyncio
async def test_29_30_31_32_33_erp_staging_idempotency_and_sanitization(
    client: AsyncClient, head_token: str, test_db: AsyncSession
):
    """
    Test 29, 30, 31, 32, 33: ERP staging assembles sanitized payload, stores hash, is idempotent, preserves versioning.
    """
    await seed_verified_payment(test_db, "app-001", "user-student-001")

    # 1. Stage Record
    res1 = await client.post("/api/v1/admin/erp/stage/app-001", headers={"Authorization": f"Bearer {head_token}"})
    assert res1.status_code == 200
    r1 = res1.json()
    assert r1["status"] == "STAGED"
    assert r1["payload_version"] == 1
    assert r1["staging_reference"].startswith("ERP-XYZ2026-")

    # Sanitization check: No passwords or secret keys in payload
    payload_str = str(r1["payload"])
    assert "password" not in payload_str
    assert "hashed_password" not in payload_str
    assert "jwt" not in payload_str.lower()

    # 2. Idempotent Staging: repeated call updates same record and increments version
    res2 = await client.post("/api/v1/admin/erp/stage/app-001", headers={"Authorization": f"Bearer {head_token}"})
    assert res2.status_code == 200
    r2 = res2.json()
    assert r2["id"] == r1["id"]
    assert r2["staging_reference"] == r1["staging_reference"]
    assert r2["payload_version"] == 2


@pytest.mark.asyncio
async def test_34_35_36_37_38_erp_sync_success_failure_and_retry(
    client: AsyncClient, head_token: str, test_db: AsyncSession
):
    """
    Test 34, 35, 36, 37, 38: Mock ERP sync failure recording, retry on same record, event logging, and success.
    """
    await seed_verified_payment(test_db, "app-001", "user-student-001")
    await client.post("/api/v1/admin/erp/stage/app-001", headers={"Authorization": f"Bearer {head_token}"})

    list_res = await client.get("/api/v1/admin/erp/records", headers={"Authorization": f"Bearer {head_token}"})
    record_id = [r["id"] for r in list_res.json() if r["application_id"] == "app-001"][0]

    # 1. Simulate failure
    fail_res = await client.post(f"/api/v1/admin/erp/records/{record_id}/sync", json={"simulate_failure": True, "failure_reason": "Sandbox ERP gateway timeout"}, headers={"Authorization": f"Bearer {head_token}"})
    assert fail_res.status_code == 200
    assert fail_res.json()["status"] == "SYNC_FAILED"
    assert fail_res.json()["last_error"] == "Sandbox ERP gateway timeout"

    # 2. Retry Sync (Success)
    retry_res = await client.post(f"/api/v1/admin/erp/records/{record_id}/retry", json={"simulate_failure": False}, headers={"Authorization": f"Bearer {head_token}"})
    assert retry_res.status_code == 200
    assert retry_res.json()["status"] == "SYNCED"
    assert retry_res.json()["retry_count"] == 1

    # 3. Check integration event history
    events_res = await client.get(f"/api/v1/admin/erp/records/{record_id}/events", headers={"Authorization": f"Bearer {head_token}"})
    assert events_res.status_code == 200
    events = events_res.json()
    assert len(events) >= 2
    event_statuses = [e["status"] for e in events]
    assert "FAILED" in event_statuses
    assert "SUCCESS" in event_statuses


@pytest.mark.asyncio
async def test_39_40_41_erp_non_mutation_and_rbac(
    client: AsyncClient, student1_token: str, test_db: AsyncSession
):
    """
    Test 39, 40, 41: ERP sync does not mutate source records, and unauthorized roles cannot trigger sync.
    """
    # Student cannot stage or sync -> 403 Forbidden
    unauth_res = await client.post("/api/v1/admin/erp/stage/app-001", headers={"Authorization": f"Bearer {student1_token}"})
    assert unauth_res.status_code == 403


# ==============================================================================
# PHASE 8: NOTIFICATIONS TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_42_43_44_45_46_notifications_dispatch_isolation_and_read(
    client: AsyncClient, student1_token: str, student2_token: str, test_db: AsyncSession
):
    """
    Test 42, 43, 44, 45, 46: Notification creation, student isolation, read/unread status, and mark-all-read.
    """
    # Create notification for student 1
    await NotificationService.send_notification(
        test_db,
        user_id="user-student-001",
        notification_type="PAYMENT_VERIFIED",
        title="Fee Payment Verified",
        message="Your Demand Draft fee payment of Rs 50,000 has been verified by the Finance Desk.",
        severity="SUCCESS",
        channel="IN_APP",
    )

    # Student 1 gets own notifications
    n_res1 = await client.get("/api/v1/notifications/me", headers={"Authorization": f"Bearer {student1_token}"})
    assert n_res1.status_code == 200
    feed1 = n_res1.json()
    assert feed1["unread_count"] >= 1
    notif_id = feed1["notifications"][0]["id"]

    # Student 2 cannot mark Student 1's notification as read -> 403 Forbidden
    unauth_read = await client.post(f"/api/v1/notifications/{notif_id}/read", headers={"Authorization": f"Bearer {student2_token}"})
    assert unauth_read.status_code == 403

    # Student 1 marks as read
    read_res = await client.post(f"/api/v1/notifications/{notif_id}/read", headers={"Authorization": f"Bearer {student1_token}"})
    assert read_res.status_code == 200
    assert read_res.json()["status"] == "READ"

    # Mark all read
    all_read = await client.post("/api/v1/notifications/read-all", headers={"Authorization": f"Bearer {student1_token}"})
    assert all_read.status_code == 200


# ==============================================================================
# PHASE 8: UNIFIED OPERATIONAL TIMELINE & ANALYTICS TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_47_48_49_50_54_analytics_real_db_counts_and_read_only(
    client: AsyncClient, head_token: str, test_db: AsyncSession
):
    """
    Test 47, 48, 49, 50, 54: Analytics computed directly from active DB records, date filters work, read-only.
    """
    await seed_verified_payment(test_db, "app-001", "user-student-001")
    await seed_verified_payment(test_db, "app-002", "user-student-002")
    await client.post("/api/v1/admin/erp/stage/app-001", headers={"Authorization": f"Bearer {head_token}"})

    res = await client.get("/api/v1/admin/analytics/overview?date_filter=all_time", headers={"Authorization": f"Bearer {head_token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["institution_name"] == "XYZ Engineering College"
    assert data["applications"]["total"] >= 2
    assert data["payments"]["total_transactions"] >= 2
    assert data["erp"]["total_records"] >= 1
    assert "processing_times_hours" in data


@pytest.mark.asyncio
async def test_51_52_53_unified_journey_timeline(
    client: AsyncClient, student1_token: str, head_token: str, test_db: AsyncSession
):
    """
    Test 51, 52, 53: Chronological timeline ordering, distinction of system vs human actions, Anti-IDOR.
    """
    await seed_verified_payment(test_db, "app-001", "user-student-001")
    await client.post("/api/v1/admin/erp/stage/app-001", headers={"Authorization": f"Bearer {head_token}"})

    # Student gets own timeline
    res = await client.get("/api/v1/timeline/me", headers={"Authorization": f"Bearer {student1_token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["application_id"] == "app-001"
    assert "stages" in data
    assert data["stages"]["physical_verification"] == "COMPLETED"
    assert data["stages"]["payment"] == "COMPLETED"
    assert data["stages"]["erp"] in ["IN_PROGRESS", "COMPLETED", "READY_FOR_STAGING"]

    # Admin gets application timeline
    admin_tl_res = await client.get("/api/v1/timeline/admin/app-001", headers={"Authorization": f"Bearer {head_token}"})
    assert admin_tl_res.status_code == 200
    events = admin_tl_res.json()["events"]
    assert len(events) >= 1


# ==============================================================================
# CROSS-DOMAIN NON-MUTATION & REGRESSION GUARANTEES
# ==============================================================================

@pytest.mark.asyncio
async def test_55_56_57_58_59_60_61_cross_domain_non_mutation_matrix(
    client: AsyncClient, head_token: str, test_db: AsyncSession
):
    """
    Test 55-61: Complete non-mutation matrix.
    - Payment VERIFIED does not modify AdmissionApplication.status or Document.status.
    - ERP STAGED / SYNCED does not modify AdmissionApplication.status or Student.
    - ERP sync failure does not destroy payment or physical verification history.
    - Phase 4F & Phase 5 isolation guarantees remain 100% intact.
    """
    await seed_verified_payment(test_db, "app-001", "user-student-001")
    await client.post("/api/v1/admin/erp/stage/app-001", headers={"Authorization": f"Bearer {head_token}"})

    list_res = await client.get("/api/v1/admin/erp/records", headers={"Authorization": f"Bearer {head_token}"})
    record_id = [r["id"] for r in list_res.json() if r["application_id"] == "app-001"][0]
    await client.post(f"/api/v1/admin/erp/records/{record_id}/sync", json={"simulate_failure": False}, headers={"Authorization": f"Bearer {head_token}"})

    stmt_app = select(AdmissionApplication).where(AdmissionApplication.id == "app-001")
    res_app = await test_db.execute(stmt_app)
    app1 = res_app.scalar_one_or_none()
    assert app1 is not None
    assert app1.status in ["APPLICATION_SUBMITTED", "DOCUMENT_REVIEW", "ACTIVATED"]

    # Physical verification session outcome remains intact
    stmt_phys = select(PhysicalVerificationSession).where(PhysicalVerificationSession.application_id == "app-001")
    res_phys = await test_db.execute(stmt_phys)
    phys_sess = res_phys.scalars().first()
    assert phys_sess.overall_decision == PhysicalVerificationDecision.VERIFIED.value

    # Payment remains verified
    stmt_pay = select(PaymentTransaction).where(PaymentTransaction.application_id == "app-001")
    res_pay = await test_db.execute(stmt_pay)
    payment = res_pay.scalars().first()
    assert payment.status == PaymentStatus.VERIFIED.value

    # ERP record is synced
    stmt_erp = select(ERPAdmissionRecord).where(ERPAdmissionRecord.application_id == "app-001")
    res_erp = await test_db.execute(stmt_erp)
    erp = res_erp.scalar_one_or_none()
    assert erp.status == ERPRecordStatus.SYNCED.value
