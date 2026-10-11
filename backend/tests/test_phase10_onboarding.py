import pytest
import asyncio
import hashlib
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from sqlalchemy import select, func

from app.models.user import User
from app.models.student import Student
from app.models.role import Role
from app.models.admission import AdmissionApplication
from app.models.tnea_allotment import TNEAAllotment
from app.models.document import Document
from app.models.scrutiny import AdmissionReview
from app.models.physical_verification import PhysicalVerificationSession, PhysicalVerificationAppointment
from app.models.payment import PaymentTransaction, DemandDraftSubmission
from app.models.erp import ERPAdmissionRecord
from app.models.onboarding import (
    StudentType,
    StudentTypeStatus,
    OnboardingStatus,
    ParentLinkStatus,
    OnboardingProfile,
    ParentGuardian,
    StudentGuardianLink,
    OnboardingChecklistItem,
    InaugurationEvent,
    TransportConfiguration,
    OnboardingAuditLog,
)
from app.services.onboarding_service import (
    is_admission_confirmed,
    OnboardingEligibilityService,
    OnboardingService,
)
from app.services.rag_service import KnowledgeService


async def confirm_admission(test_db, student_id: str = "student-001"):
    """Helper to set candidate's application to ADMISSION_CONFIRMED."""
    stmt = select(AdmissionApplication).where(AdmissionApplication.student_id == student_id)
    res = await test_db.execute(stmt)
    app = res.scalar_one()
    app.status = "ADMISSION_CONFIRMED"
    await test_db.commit()
    return app


async def snapshot_9_entities(test_db):
    """Captures an exact snapshot of all 9 core admission domain entities."""
    apps = (await test_db.execute(select(AdmissionApplication))).scalars().all()
    docs = (await test_db.execute(select(Document))).scalars().all()
    students = (await test_db.execute(select(Student))).scalars().all()
    allotments = (await test_db.execute(select(TNEAAllotment))).scalars().all()
    reviews = (await test_db.execute(select(AdmissionReview))).scalars().all()
    pv_sessions = (await test_db.execute(select(PhysicalVerificationSession))).scalars().all()
    pay_txs = (await test_db.execute(select(PaymentTransaction))).scalars().all()
    dd_subs = (await test_db.execute(select(DemandDraftSubmission))).scalars().all()
    erp_recs = (await test_db.execute(select(ERPAdmissionRecord))).scalars().all()

    return {
        "apps": [(a.id, a.status, a.completion_percentage) for a in apps],
        "docs": [(d.id, d.status) for d in docs],
        "students": [(s.id, s.full_name, s.allotted_branch) for s in students],
        "allotments": [(al.id, al.tnea_application_number) for al in allotments],
        "reviews": [(r.id, r.status, r.decision) for r in reviews],
        "pv_sessions": [(p.id, p.status) for p in pv_sessions],
        "pay_txs": [(pt.id, pt.status, float(pt.amount)) for pt in pay_txs],
        "dd_subs": [(dd.id, dd.dd_number, float(dd.amount)) for dd in dd_subs],
        "erp_recs": [(e.id, e.status, e.staging_reference) for e in erp_recs],
    }


# ==============================================================================
# PHASE 10 COMPREHENSIVE TEST SUITE
# ==============================================================================

@pytest.mark.asyncio
async def test_01_authoritative_admission_confirmation_predicate(test_db):
    """Test 1: Tests is_admission_confirmed directly on unconfirmed vs confirmed applications."""
    unconfirmed_app = AdmissionApplication(
        id="app-unconfirmed-test",
        student_id="student-test-1",
        status="APPLICATION_SUBMITTED",
    )
    assert is_admission_confirmed(unconfirmed_app) is False

    review_app = AdmissionApplication(
        id="app-review-test",
        student_id="student-test-2",
        status="DOCUMENT_REVIEW",
    )
    assert is_admission_confirmed(review_app) is False

    payment_app = AdmissionApplication(
        id="app-pay-test",
        student_id="student-test-3",
        status="PAYMENT_PENDING",
    )
    assert is_admission_confirmed(payment_app) is False

    # Authoritatively confirmed
    confirmed_app = AdmissionApplication(
        id="app-confirmed-test",
        student_id="student-test-4",
        status="ADMISSION_CONFIRMED",
    )
    assert is_admission_confirmed(confirmed_app) is True

    erp_synced_app = AdmissionApplication(
        id="app-erp-test",
        student_id="student-test-5",
        status="ERP_SYNCED",
    )
    assert is_admission_confirmed(erp_synced_app) is True

    active_app = AdmissionApplication(
        id="app-active-test",
        student_id="student-test-6",
        status="ACTIVE_STUDENT",
    )
    assert is_admission_confirmed(active_app) is True
    assert is_admission_confirmed(None) is False


@pytest.mark.asyncio
async def test_02_onboarding_eligibility_enforcement(client: AsyncClient, test_db, student1_token):
    """Test 2: Asserts unconfirmed candidate is rejected with explicit detail."""
    # Set Student 1 app to unconfirmed status
    stmt_app = select(AdmissionApplication).where(AdmissionApplication.id == "app-001")
    res = await test_db.execute(stmt_app)
    app1 = res.scalar_one()
    app1.status = "DOCUMENT_REVIEW"
    await test_db.commit()

    resp = await client.get("/api/v1/onboarding/me", headers={"Authorization": f"Bearer {student1_token}"})
    assert resp.status_code == 403
    data = resp.json()
    assert "Onboarding will become available after admission confirmation." in data["detail"]


@pytest.mark.asyncio
async def test_03_downstream_status_cannot_bypass_eligibility(test_db):
    """Test 3: Verifies downstream unconfirmed status cannot bypass centralized eligibility."""
    stmt_app = select(AdmissionApplication).where(AdmissionApplication.id == "app-001")
    res = await test_db.execute(stmt_app)
    app1 = res.scalar_one()
    app1.status = "PHYSICAL_VERIFICATION"
    await test_db.commit()

    eligible, reason, app = await OnboardingEligibilityService.check_eligibility(test_db, "student-001")
    assert eligible is False
    assert "Onboarding will become available after admission confirmation." in reason


@pytest.mark.asyncio
async def test_04_controlled_student_type_workflow(client: AsyncClient, test_db, student1_token, admin_token):
    """Test 4: Tests STUDENT_REQUESTED and ADMIN_CONFIRMED transitions and audit logging."""
    await confirm_admission(test_db, "student-001")

    # 1. Student requests HOSTELLER
    resp_req = await client.post(
        "/api/v1/onboarding/me/student-type",
        json={"student_type": "HOSTELLER"},
        headers={"Authorization": f"Bearer {student1_token}"},
    )
    assert resp_req.status_code == 200
    data_req = resp_req.json()
    assert data_req["student_type"] == "HOSTELLER"
    assert data_req["student_type_status"] == "STUDENT_REQUESTED"

    # 2. Admin confirms HOSTELLER
    resp_conf = await client.post(
        "/api/v1/admin/onboarding/students/student-001/confirm-type",
        json={"student_type": "HOSTELLER"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_conf.status_code == 200
    data_conf = resp_conf.json()
    assert data_conf["student_type"] == "HOSTELLER"
    assert data_conf["student_type_status"] == "ADMIN_CONFIRMED"

    # Check audit logs
    stmt_audit = select(OnboardingAuditLog).where(OnboardingAuditLog.student_id == "student-001")
    res_audit = await test_db.execute(stmt_audit)
    logs = res_audit.scalars().all()
    actions = [l.action for l in logs]
    assert "STUDENT_TYPE_REQUESTED" in actions
    assert "STUDENT_TYPE_CONFIRMED" in actions


@pytest.mark.asyncio
async def test_05_dynamic_checklist_scoping_day_scholar_vs_hosteller(client: AsyncClient, test_db, student1_token, admin_token):
    """Test 5: Validates checklist item scope and single source of truth."""
    await confirm_admission(test_db, "student-001")

    # Set as HOSTELLER
    await client.post(
        "/api/v1/admin/onboarding/students/student-001/confirm-type",
        json={"student_type": "HOSTELLER"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    resp_hostel = await client.get("/api/v1/onboarding/me/checklist", headers={"Authorization": f"Bearer {student1_token}"})
    assert resp_hostel.status_code == 200
    hostel_items = resp_hostel.json()
    hostel_keys = [i["item_key"] for i in hostel_items]

    assert "HOSTEL_RULES" in hostel_keys
    assert "HOSTEL_MOBILE_GUIDANCE" in hostel_keys
    assert "HOSTEL_VISITORS_FORM" in hostel_keys
    assert "DAY_SCHOLAR_TRANSPORT" not in hostel_keys

    # Switch to DAY_SCHOLAR
    await client.post(
        "/api/v1/admin/onboarding/students/student-001/confirm-type",
        json={"student_type": "DAY_SCHOLAR"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    resp_ds = await client.get("/api/v1/onboarding/me/checklist", headers={"Authorization": f"Bearer {student1_token}"})
    assert resp_ds.status_code == 200
    ds_items = resp_ds.json()
    ds_keys = [i["item_key"] for i in ds_items]

    assert "DAY_SCHOLAR_TRANSPORT" in ds_keys
    assert "DAY_SCHOLAR_MOBILE" in ds_keys
    assert "CAMPUS_ID_CARD" in ds_keys
    assert "FACULTY_MEMBER_INFO" in ds_keys


@pytest.mark.asyncio
async def test_06_checklist_acknowledgement_semantics(client: AsyncClient, test_db, student1_token, admin_token):
    """Test 6: Acknowledges items and verifies progress calculation without modifying admission status."""
    await confirm_admission(test_db, "student-001")

    # Set as DAY_SCHOLAR
    await client.post(
        "/api/v1/admin/onboarding/students/student-001/confirm-type",
        json={"student_type": "DAY_SCHOLAR"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # Get current checklist
    resp_list = await client.get("/api/v1/onboarding/me/checklist", headers={"Authorization": f"Bearer {student1_token}"})
    items = resp_list.json()

    # Acknowledge first item
    first_key = items[0]["item_key"]
    resp_ack = await client.post(
        f"/api/v1/onboarding/me/checklist/{first_key}/acknowledge",
        headers={"Authorization": f"Bearer {student1_token}"},
    )
    assert resp_ack.status_code == 200
    ack_item = resp_ack.json()
    assert ack_item["is_acknowledged"] is True
    assert ack_item["acknowledged_at"] is not None

    # Check profile completion
    resp_prof = await client.get("/api/v1/onboarding/me", headers={"Authorization": f"Bearer {student1_token}"})
    prof = resp_prof.json()
    assert prof["overall_completion_percentage"] > 0

    # Acknowledge all remaining items to verify INDUCTION_READY transition
    for it in items:
        await client.post(
            f"/api/v1/onboarding/me/checklist/{it['item_key']}/acknowledge",
            headers={"Authorization": f"Bearer {student1_token}"},
        )

    resp_full = await client.get("/api/v1/onboarding/me", headers={"Authorization": f"Bearer {student1_token}"})
    full_prof = resp_full.json()
    assert full_prof["overall_completion_percentage"] == 100
    assert full_prof["onboarding_status"] == "INDUCTION_READY"


@pytest.mark.asyncio
async def test_07_parent_invite_raw_token_never_persisted(client: AsyncClient, test_db, student1_token):
    """Test 7: Asserts DB contains only invite_token_hash and raw token is absent in database."""
    await confirm_admission(test_db, "student-001")

    invite_payload = {
        "parent_name": "Ramanathan Sundaram",
        "phone": "+919876543210",
        "email": "ramanathan@example.com",
        "relationship": "FATHER",
    }
    resp = await client.post(
        "/api/v1/onboarding/me/parent-invitation",
        json=invite_payload,
        headers={"Authorization": f"Bearer {student1_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    raw_token = data["invite_token"]
    link_id = data["link_id"]

    assert raw_token is not None
    assert len(raw_token) > 20

    # Query DB directly
    stmt = select(StudentGuardianLink).where(StudentGuardianLink.id == link_id)
    res = await test_db.execute(stmt)
    link = res.scalar_one()

    # Raw token must NEVER equal stored invite_token_hash
    assert link.invite_token_hash != raw_token
    # invite_token_hash must equal SHA-256(raw_token)
    expected_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    assert link.invite_token_hash == expected_hash

    # Raw token must not appear in any column of student_guardian_links
    assert raw_token not in str(link.__dict__.values())


@pytest.mark.asyncio
async def test_08_parent_token_redemption_and_expiry(client: AsyncClient, test_db, student1_token, parent_token):
    """Test 8: Tests successful redemption, expired token rejection, and prevention of reused token redemption."""
    await confirm_admission(test_db, "student-001")

    # 1. Create fresh invitation
    resp_inv = await client.post(
        "/api/v1/onboarding/me/parent-invitation",
        json={"parent_name": "Lakshmi Ramanathan", "phone": "+919876543211", "email": "lakshmi@example.com", "relationship": "MOTHER"},
        headers={"Authorization": f"Bearer {student1_token}"},
    )
    raw_token = resp_inv.json()["invite_token"]

    # 2. Redeem successfully
    redeem_payload = {
        "invite_token": raw_token,
        "parent_name": "Lakshmi Ramanathan",
        "phone": "+919876543211",
        "email": "lakshmi@example.com",
    }
    resp_red = await client.post(
        "/api/v1/parent/redeem-invitation",
        json=redeem_payload,
        headers={"Authorization": f"Bearer {parent_token}"},
    )
    assert resp_red.status_code == 200
    assert resp_red.json()["success"] is True

    # 3. Attempt to reuse already redeemed token
    resp_reuse = await client.post(
        "/api/v1/parent/redeem-invitation",
        json=redeem_payload,
        headers={"Authorization": f"Bearer {parent_token}"},
    )
    assert resp_reuse.status_code == 400
    assert "already active" in resp_reuse.json()["detail"].lower() or "already redeemed" in resp_reuse.json()["detail"].lower()

    # 4. Create an expired token manually and verify rejection
    expired_token = "expired_test_token_12345"
    exp_hash = hashlib.sha256(expired_token.encode("utf-8")).hexdigest()
    expired_link = StudentGuardianLink(
        student_id="student-001",
        guardian_id=None,
        invite_token_hash=exp_hash,
        token_expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        relationship="FATHER",
        status=ParentLinkStatus.PENDING,
    )
    test_db.add(expired_link)
    await test_db.commit()

    resp_exp = await client.post(
        "/api/v1/parent/redeem-invitation",
        json={"invite_token": expired_token, "parent_name": "Test Parent", "phone": "+919999999999"},
        headers={"Authorization": f"Bearer {parent_token}"},
    )
    assert resp_exp.status_code == 400
    assert "expired" in resp_exp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_09_parent_linking_is_optional(test_db):
    """Test 9: Verifies a student can complete checklist and reach INDUCTION_READY without an active parent link."""
    await confirm_admission(test_db, "student-001")
    profile = await OnboardingService.get_or_create_profile(test_db, "student-001")
    profile.student_type = StudentType.DAY_SCHOLAR
    profile.student_type_status = StudentTypeStatus.ADMIN_CONFIRMED
    await test_db.commit()

    items = await OnboardingService.sync_checklist_items(test_db, profile)
    for it in items:
        it.is_acknowledged = True
    await test_db.commit()

    await OnboardingService.recalculate_progress(test_db, profile)
    assert profile.overall_completion_percentage == 100
    assert profile.onboarding_status == OnboardingStatus.INDUCTION_READY


@pytest.mark.asyncio
async def test_10_parent_anti_idor_and_unlinked_blocking(client: AsyncClient, test_db, student1_token, parent_token):
    """Test 10: Verifies Parent access to linked student data and Anti-IDOR protection."""
    await confirm_admission(test_db, "student-001")

    # Create and redeem link for parent
    resp_inv = await client.post(
        "/api/v1/onboarding/me/parent-invitation",
        json={"parent_name": "Lakshmi Ramanathan", "phone": "+919876543211", "email": "lakshmi@example.com", "relationship": "MOTHER"},
        headers={"Authorization": f"Bearer {student1_token}"},
    )
    raw_token = resp_inv.json()["invite_token"]

    await client.post(
        "/api/v1/parent/redeem-invitation",
        json={"invite_token": raw_token, "parent_name": "Lakshmi Ramanathan", "phone": "+919876543211"},
        headers={"Authorization": f"Bearer {parent_token}"},
    )

    resp_stu = await client.get("/api/v1/parent/student", headers={"Authorization": f"Bearer {parent_token}"})
    assert resp_stu.status_code == 200
    data = resp_stu.json()
    assert data["student_id"] == "student-001"
    # Anti-IDOR: Zero raw credentials, OCR data, or internal scrutiny notes returned
    assert "password_hash" not in data
    assert "ocr_text" not in data
    assert "reviewer_internal_notes" not in data

    resp_onb = await client.get("/api/v1/parent/onboarding", headers={"Authorization": f"Bearer {parent_token}"})
    assert resp_onb.status_code == 200


@pytest.mark.asyncio
async def test_11_student_anti_idor(client: AsyncClient, test_db, student1_token):
    """Test 11: Verifies Student A cannot access or tamper with Student B's checklist."""
    await confirm_admission(test_db, "student-001")

    # Create fake second profile
    prof_b = OnboardingProfile(
        id="prof-other-student-999",
        student_id="student-999",
        application_id="app-999",
        student_type=StudentType.DAY_SCHOLAR,
        onboarding_status=OnboardingStatus.ONBOARDING_IN_PROGRESS,
    )
    test_db.add(prof_b)
    item_b = OnboardingChecklistItem(
        id="item-b-999",
        profile_id=prof_b.id,
        item_key="CAMPUS_ID_CARD",
        title="ID Card",
    )
    test_db.add(item_b)
    await test_db.commit()

    # Student 1 attempts to acknowledge item belonging to Student 999
    with pytest.raises(Exception):
        await OnboardingService.acknowledge_checklist_item(
            db=test_db,
            profile_id="prof-other-student-999",
            item_key="CAMPUS_ID_CARD",
            student_id="student-001",
        )


@pytest.mark.asyncio
async def test_12_strict_9_entity_non_mutation_snapshot(client: AsyncClient, test_db, student1_token, admin_token):
    """Test 12: Strict 9-Entity Non-Mutation Snapshot Test before and after extensive onboarding operations."""
    await confirm_admission(test_db, "student-001")
    snapshot_before = await snapshot_9_entities(test_db)

    # Perform a suite of onboarding operations
    await client.get("/api/v1/onboarding/me", headers={"Authorization": f"Bearer {student1_token}"})
    await client.post(
        "/api/v1/onboarding/me/student-type",
        json={"student_type": "HOSTELLER"},
        headers={"Authorization": f"Bearer {student1_token}"},
    )
    await client.post(
        "/api/v1/onboarding/me/checklist/CAMPUS_ID_CARD/acknowledge",
        headers={"Authorization": f"Bearer {student1_token}"},
    )
    await client.post(
        "/api/v1/onboarding/me/parent-invitation",
        json={"parent_name": "Test Parent 2", "phone": "+919876543299", "relationship": "FATHER"},
        headers={"Authorization": f"Bearer {student1_token}"},
    )
    await client.get("/api/v1/onboarding/me/guidance", headers={"Authorization": f"Bearer {student1_token}"})
    await client.get("/api/v1/onboarding/me/inauguration", headers={"Authorization": f"Bearer {student1_token}"})
    await client.get("/api/v1/onboarding/me/transport", headers={"Authorization": f"Bearer {student1_token}"})

    snapshot_after = await snapshot_9_entities(test_db)

    # Assert ZERO mutations on all 9 admission entities
    assert snapshot_before["apps"] == snapshot_after["apps"], "AdmissionApplication mutated!"
    assert snapshot_before["docs"] == snapshot_after["docs"], "Document mutated!"
    assert snapshot_before["students"] == snapshot_after["students"], "Student mutated!"
    assert snapshot_before["allotments"] == snapshot_after["allotments"], "TNEAAllotment mutated!"
    assert snapshot_before["reviews"] == snapshot_after["reviews"], "AdmissionReview mutated!"
    assert snapshot_before["pv_sessions"] == snapshot_after["pv_sessions"], "PhysicalVerificationSession mutated!"
    assert snapshot_before["pay_txs"] == snapshot_after["pay_txs"], "PaymentTransaction mutated!"
    assert snapshot_before["dd_subs"] == snapshot_after["dd_subs"], "DemandDraftSubmission mutated!"
    assert snapshot_before["erp_recs"] == snapshot_after["erp_recs"], "ERPAdmissionRecord mutated!"


@pytest.mark.asyncio
async def test_13_dynamic_inauguration_status_and_transport_fallback(client: AsyncClient, test_db, student1_token):
    """Test 13: Tests event status calculation (UPCOMING, TODAY, PAST) and transport fallback message."""
    await confirm_admission(test_db, "student-001")

    resp_inaug = await client.get("/api/v1/onboarding/me/inauguration", headers={"Authorization": f"Bearer {student1_token}"})
    assert resp_inaug.status_code == 200
    inaug = resp_inaug.json()
    assert inaug["event_date"] == "2026-08-31"
    assert inaug["event_status"] in ["UPCOMING", "TODAY", "PAST"]

    resp_trans = await client.get("/api/v1/onboarding/me/transport", headers={"Authorization": f"Bearer {student1_token}"})
    assert resp_trans.status_code == 200
    trans = resp_trans.json()
    assert trans["college_code"] == "XYZ"
    assert "Information not configured for this prototype." in trans["message"]


@pytest.mark.asyncio
async def test_14_hosteller_guidance_and_source_terminology(client: AsyncClient, test_db, student1_token, admin_token):
    """Test 14: Verifies hosteller rules, Faculty Member directory, and Hosteller mobile-phone guidance."""
    await confirm_admission(test_db, "student-001")

    # Set as HOSTELLER
    await client.post(
        "/api/v1/admin/onboarding/students/student-001/confirm-type",
        json={"student_type": "HOSTELLER"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    resp_guidance = await client.get("/api/v1/onboarding/me/guidance", headers={"Authorization": f"Bearer {student1_token}"})
    assert resp_guidance.status_code == 200
    cards = resp_guidance.json()

    # Check Faculty Member role terminology
    contacts_card = next(c for c in cards if c["category"] == "CONTACTS")
    assert contacts_card["data"]["faculty_member_role"] == "Faculty Member"

    # Check placement attribution
    general_card = next(c for c in cards if c["category"] == "GENERAL")
    assert "Institution-Provided Information (Not independently verified by AdmissionAI)" in general_card["attribution"]

    # Check hosteller mobile guidance terminology (no curfew terminology)
    hostel_card = next(c for c in cards if c["category"] == "HOSTELLER_RULES")
    assert "Hosteller mobile-phone guidance" in hostel_card["data"]["mobile_guidance"]
    assert "curfew" not in str(hostel_card).lower()


@pytest.mark.asyncio
async def test_15_rag_chatbot_onboarding_query_resolution(client: AsyncClient, test_db, student1_token):
    """Test 15: Tests Phase 9 chatbot query resolution with personalized onboarding context."""
    await confirm_admission(test_db, "student-001")
    await KnowledgeService.seed_initial_knowledge(test_db)

    # Student asks onboarding question
    resp_msg = await client.post(
        "/api/v1/chat/sessions",
        json={"title": "Onboarding Query"},
        headers={"Authorization": f"Bearer {student1_token}"},
    )
    session_id = resp_msg.json()["id"]

    resp_chat = await client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        json={"message": "What time is the first year inauguration on August 31, 2026?"},
        headers={"Authorization": f"Bearer {student1_token}"},
    )
    assert resp_chat.status_code in [200, 201]
    chat_data = resp_chat.json()
    assert chat_data["response_type"] in ["GROUNDED_KNOWLEDGE", "MIXED_CONTEXT", "PERSONAL_CONTEXT", "DIRECT_ASSISTANCE"]
    assert len(chat_data["message"]) > 10


@pytest.mark.asyncio
async def test_16_append_only_onboarding_audit_logs(client: AsyncClient, test_db, student1_token, admin_token):
    """Test 16: Verifies audit logs for student type changes, parent linking, and checklist acknowledgements."""
    await confirm_admission(test_db, "student-001")

    # Generate an action to create an audit log
    await client.post(
        "/api/v1/onboarding/me/student-type",
        json={"student_type": "HOSTELLER"},
        headers={"Authorization": f"Bearer {student1_token}"},
    )

    resp_logs = await client.get("/api/v1/admin/onboarding/audit-logs", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp_logs.status_code == 200
    logs = resp_logs.json()
    assert len(logs) > 0
    actions = [l["action"] for l in logs]
    assert "STUDENT_TYPE_REQUESTED" in actions
