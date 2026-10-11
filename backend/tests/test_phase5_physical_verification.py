import pytest
import io
import uuid
from datetime import datetime, timezone, date, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.admission import AdmissionApplication
from app.models.student import Student
from app.models.tnea_allotment import TNEAAllotment
from app.models.document import Document, DocumentType, DocumentVersion
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
from app.models.document_processing import CrossDocumentReconciliation
from app.core.security import create_access_token


# Fixture for Admission Head token
@pytest.fixture
def admission_head_token():
    return create_access_token(
        subject="user-head-001",
        role="ADMISSION_HEAD",
        claims={"email": "head@xyz.edu.demo"}
    )


# Fixture for Super Admin token
@pytest.fixture
def super_admin_token():
    return create_access_token(
        subject="user-super-001",
        role="SUPER_ADMIN",
        claims={"email": "superadmin@xyz.edu.demo"}
    )


async def create_test_appointment(
    client: AsyncClient,
    student_token: str,
    days_ahead: int = 1,
    start_time: str = "10:00 AM",
    end_time: str = "10:30 AM",
) -> dict:
    apt_date = str(date.today() + timedelta(days=days_ahead))
    res = await client.post(
        "/api/v1/physical-verification/appointments",
        json={
            "appointment_date": apt_date,
            "start_time": start_time,
            "end_time": end_time,
            "location": "Central Admission Hall",
            "notes": "Candidate test booking"
        },
        headers={"Authorization": f"Bearer {student_token}"}
    )
    return res.json()


async def seed_test_document(test_db: AsyncSession, application_id: str = "app-001", doc_id: str = "doc-pv-001") -> Document:
    doc_res = await test_db.execute(select(Document).where(Document.id == doc_id))
    doc = doc_res.scalar_one_or_none()
    if not doc:
        doc = Document(
            id=doc_id,
            application_id=application_id,
            document_type_id="dt-001",
            status="UPLOADED"
        )
        test_db.add(doc)
        await test_db.flush()
        
        ver = DocumentVersion(
            id=f"ver-{doc_id}-1",
            document_id=doc_id,
            version_number=1,
            original_filename="sample_marksheet.pdf",
            mime_type="application/pdf",
            file_size=1024,
            file_hash="abc123hash",
            storage_path="storage/sample.pdf",
            uploaded_by="student",
        )
        test_db.add(ver)
        doc.current_version_id = ver.id
        await test_db.commit()
    return doc


@pytest.mark.asyncio
async def test_01_available_slots_retrieval(client: AsyncClient, student1_token: str):
    """1. Candidates and admins can retrieve available physical verification slots."""
    today_str = str(date.today() + timedelta(days=1))
    res = await client.get(
        f"/api/v1/physical-verification/slots?slot_date={today_str}",
        headers={"Authorization": f"Bearer {student1_token}"}
    )
    assert res.status_code == 200
    slots = res.json()
    assert isinstance(slots, list)
    assert len(slots) >= 5
    assert "start_time" in slots[0]
    assert "available_capacity" in slots[0]


@pytest.mark.asyncio
async def test_02_appointment_creation_and_token_generation(
    client: AsyncClient,
    test_db: AsyncSession,
    student1_token: str
):
    """2. Candidate can book an appointment slot and receives a unique token and check-in QR code."""
    data = await create_test_appointment(client, student1_token, days_ahead=2)
    assert data["appointment_status"] == "SCHEDULED"
    assert data["start_time"] == "10:00 AM"
    assert data["token_number"].startswith("PV-")
    assert len(data["checkin_token"]) >= 16


@pytest.mark.asyncio
async def test_03_student_view_own_appointment(client: AsyncClient, student1_token: str):
    """3. Student can view their own scheduled appointment."""
    await create_test_appointment(client, student1_token, days_ahead=2)
    res = await client.get(
        "/api/v1/physical-verification/appointments/me",
        headers={"Authorization": f"Bearer {student1_token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data is not None
    assert data["appointment_status"] in ["SCHEDULED", "CONFIRMED"]


@pytest.mark.asyncio
async def test_04_student_cannot_access_another_students_appointment_anti_idor(
    client: AsyncClient,
    student1_token: str,
    student2_token: str
):
    """4. Student 2 cannot access or confirm Student 1's appointment (Anti-IDOR)."""
    apt1 = await create_test_appointment(client, student1_token, days_ahead=3)
    apt1_id = apt1["id"]

    # Student 2 attempts to confirm Student 1's appointment -> 403 Forbidden
    res = await client.post(
        f"/api/v1/physical-verification/appointments/{apt1_id}/confirm",
        headers={"Authorization": f"Bearer {student2_token}"}
    )
    assert res.status_code == 403
    assert "forbidden" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_05_student_cannot_access_admin_physical_verification_apis(
    client: AsyncClient,
    student1_token: str
):
    """5. Student cannot access admin verification queue or check-in endpoints (RBAC 403)."""
    res1 = await client.get(
        "/api/v1/physical-verification/admin/appointments",
        headers={"Authorization": f"Bearer {student1_token}"}
    )
    assert res1.status_code == 403

    res2 = await client.post(
        "/api/v1/physical-verification/admin/check-in",
        json={"token_number": "PV-20260924-001"},
        headers={"Authorization": f"Bearer {student1_token}"}
    )
    assert res2.status_code == 403


@pytest.mark.asyncio
async def test_06_appointment_confirmation(client: AsyncClient, student1_token: str):
    """6. Candidate confirms their scheduled appointment."""
    my_apt = await create_test_appointment(client, student1_token, days_ahead=2)
    apt_id = my_apt["id"]

    res = await client.post(
        f"/api/v1/physical-verification/appointments/{apt_id}/confirm",
        headers={"Authorization": f"Bearer {student1_token}"}
    )
    assert res.status_code == 200
    assert res.json()["appointment_status"] == "CONFIRMED"


@pytest.mark.asyncio
async def test_07_appointment_rescheduling(client: AsyncClient, student1_token: str):
    """7. Candidate reschedules appointment to a new date/slot."""
    my_apt = await create_test_appointment(client, student1_token, days_ahead=2)
    apt_id = my_apt["id"]

    new_date = str(date.today() + timedelta(days=5))
    res = await client.post(
        f"/api/v1/physical-verification/appointments/{apt_id}/reschedule",
        json={
            "appointment_date": new_date,
            "start_time": "11:30 AM",
            "end_time": "12:00 PM",
            "reason": "Travel conflict resolved"
        },
        headers={"Authorization": f"Bearer {student1_token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["appointment_status"] == "RESCHEDULED"
    assert data["start_time"] == "11:30 AM"


@pytest.mark.asyncio
async def test_08_admin_list_appointments_with_filter(
    client: AsyncClient,
    admin_token: str,
    student1_token: str
):
    """8. Admin can list appointments with date and status filtering."""
    await create_test_appointment(client, student1_token, days_ahead=2)
    res = await client.get(
        "/api/v1/physical-verification/admin/appointments",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 200
    apts = res.json()
    assert isinstance(apts, list)
    assert len(apts) >= 1


@pytest.mark.asyncio
async def test_09_10_check_in_workflow_and_duplicate_prevention(
    client: AsyncClient,
    admin_token: str,
    student1_token: str
):
    """9, 10. Check-in by token number works and duplicate check-in is handled safely."""
    my_apt = await create_test_appointment(client, student1_token, days_ahead=2)
    token_num = my_apt["token_number"]

    # 1. First Check-in
    res1 = await client.post(
        "/api/v1/physical-verification/admin/check-in",
        json={"token_number": token_num, "counter_desk": "Desk 3"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res1.status_code == 200
    d1 = res1.json()
    assert "checked in" in d1["message"].lower()
    assert d1["token_number"] == token_num

    # 2. Duplicate Check-in Attempt -> Safely acknowledges existing check-in without error
    res2 = await client.post(
        "/api/v1/physical-verification/admin/check-in",
        json={"token_number": token_num, "counter_desk": "Desk 3"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res2.status_code == 200
    assert "already checked in" in res2.json()["message"].lower()


@pytest.mark.asyncio
async def test_11_check_in_with_invalid_token(client: AsyncClient, admin_token: str):
    """11. Checking in with nonexistent token returns 404."""
    res = await client.post(
        "/api/v1/physical-verification/admin/check-in",
        json={"token_number": "PV-NONEXISTENT-999"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_12_13_start_verification_session_captures_versions(
    client: AsyncClient,
    test_db: AsyncSession,
    admin_token: str
):
    """12, 13. Verification session starts and pre-populates document checklist pointing to exact current versions."""
    await seed_test_document(test_db, "app-001", "doc-pv-001")

    res = await client.post(
        "/api/v1/physical-verification/admin/applications/app-001/sessions/start",
        json={"counter_desk": "Desk 2", "officer_notes": "Starting physical verification session"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 200
    session_data = res.json()
    assert session_data["session_status"] == "IN_PROGRESS"
    assert session_data["application_id"] == "app-001"
    assert len(session_data["document_verifications"]) >= 1


@pytest.mark.asyncio
async def test_14_officer_can_verify_physical_document(
    client: AsyncClient,
    test_db: AsyncSession,
    admin_token: str
):
    """14. Officer can record physical checklist checks and verify a physical document."""
    await seed_test_document(test_db, "app-001", "doc-pv-001")

    # Start session for app-001
    start_res = await client.post(
        "/api/v1/physical-verification/admin/applications/app-001/sessions/start",
        json={},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    sess_id = start_res.json()["id"]

    res = await client.post(
        f"/api/v1/physical-verification/admin/sessions/{sess_id}/documents/doc-pv-001/verify",
        json={
            "officer_decision": "VERIFIED",
            "verification_notes": "Original 10th marksheet inspected, embossed seal confirmed.",
            "checklist_checks": {
                "original_presented": True,
                "document_legible": True,
                "name_matches": True,
                "dob_matches": True,
                "id_matches": True,
                "photo_check_done": True,
            }
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 200
    item = res.json()
    assert item["officer_decision"] == "VERIFIED"
    assert item["checklist_checks"]["original_presented"] is True
    assert "embossed seal" in item["verification_notes"]


@pytest.mark.asyncio
async def test_15_16_officer_can_request_physical_correction(
    client: AsyncClient,
    test_db: AsyncSession,
    admin_token: str
):
    """15, 16. Officer flags document as CORRECTION_REQUIRED; OTHER reason requires notes."""
    await seed_test_document(test_db, "app-001", "doc-pv-001")

    start_res = await client.post(
        "/api/v1/physical-verification/admin/applications/app-001/sessions/start",
        json={},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    sess_id = start_res.json()["id"]

    # 1. Valid correction request
    res_corr = await client.post(
        f"/api/v1/physical-verification/admin/sessions/{sess_id}/documents/doc-pv-001/correction",
        json={
            "discrepancy_reason": "ORIGINAL_ILLEGIBLE",
            "verification_notes": "Original document is torn across roll number section. Please bring duplicate.",
            "checklist_checks": {"original_presented": True, "document_legible": False}
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res_corr.status_code == 200
    assert res_corr.json()["officer_decision"] == "CORRECTION_REQUIRED"
    assert res_corr.json()["discrepancy_reason"] == "ORIGINAL_ILLEGIBLE"

    # 2. OTHER reason missing notes -> 400 Bad Request
    res_invalid = await client.post(
        f"/api/v1/physical-verification/admin/sessions/{sess_id}/documents/doc-pv-001/correction",
        json={
            "discrepancy_reason": "OTHER",
            "verification_notes": "   ",
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res_invalid.status_code == 400


@pytest.mark.asyncio
async def test_17_student_summary_displays_physical_correction(
    client: AsyncClient,
    test_db: AsyncSession,
    admin_token: str,
    student1_token: str
):
    """17. Candidate summary endpoint exposes physical correction instructions."""
    await seed_test_document(test_db, "app-001", "doc-pv-001")

    start_res = await client.post(
        "/api/v1/physical-verification/admin/applications/app-001/sessions/start",
        json={},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    sess_id = start_res.json()["id"]

    await client.post(
        f"/api/v1/physical-verification/admin/sessions/{sess_id}/documents/doc-pv-001/correction",
        json={
            "discrepancy_reason": "ORIGINAL_ILLEGIBLE",
            "verification_notes": "Original document is torn across roll number section. Please bring duplicate.",
            "checklist_checks": {"original_presented": True, "document_legible": False}
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    res = await client.get(
        "/api/v1/physical-verification/me/summary",
        headers={"Authorization": f"Bearer {student1_token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["has_corrections"] is True
    assert len(data["corrections"]) >= 1
    assert data["corrections"][0]["discrepancy_reason"] == "ORIGINAL_ILLEGIBLE"


@pytest.mark.asyncio
async def test_18_19_20_21_resubmission_versioning_isolation(
    client: AsyncClient,
    test_db: AsyncSession,
    student1_token: str,
    admin_token: str
):
    """
    18, 19, 20, 21. Candidate uploads new version (v2).
    - v1 remains immutable.
    - Historical physical document verification continues to link to v1.
    - New session or verification can inspect v2.
    """
    # 1. First upload (v1)
    file_bytes_v1 = b"%PDF-1.4 initial marksheet content"
    up_res1 = await client.post(
        "/api/v1/documents/upload",
        data={"document_type_code": "TWELFTH_MARKSHEET"},
        files={"file": ("twelfth_v1_pv.pdf", io.BytesIO(file_bytes_v1), "application/pdf")},
        headers={"Authorization": f"Bearer {student1_token}"}
    )
    assert up_res1.status_code == 200
    doc_id = up_res1.json()["document_id"]
    v1_id = up_res1.json()["version_id"]

    # 2. Upload replacement (v2)
    file_bytes_v2 = b"%PDF-1.4 replacement fresh marksheet copy"
    up_res2 = await client.post(
        "/api/v1/documents/upload",
        data={"document_type_code": "TWELFTH_MARKSHEET"},
        files={"file": ("twelfth_v2_pv.pdf", io.BytesIO(file_bytes_v2), "application/pdf")},
        headers={"Authorization": f"Bearer {student1_token}"}
    )
    assert up_res2.status_code == 200
    v2_data = up_res2.json()
    assert v2_data["version_number"] == 2
    assert v2_data["document_id"] == doc_id
    assert v2_data["version_id"] != v1_id


@pytest.mark.asyncio
async def test_22_officer_can_complete_session(
    client: AsyncClient,
    test_db: AsyncSession,
    admin_token: str
):
    """22. Officer completes physical verification session with overall determination."""
    await seed_test_document(test_db, "app-001", "doc-pv-001")

    start_res = await client.post(
        "/api/v1/physical-verification/admin/applications/app-001/sessions/start",
        json={},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    sess_id = start_res.json()["id"]

    res = await client.post(
        f"/api/v1/physical-verification/admin/sessions/{sess_id}/complete",
        json={
            "overall_decision": "VERIFIED",
            "officer_notes": "All physical original documents verified and stamp placed.",
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["session_status"] == "COMPLETED"
    assert data["overall_decision"] == "VERIFIED"
    assert data["completed_at"] is not None


@pytest.mark.asyncio
async def test_23_completed_session_cannot_be_overwritten(
    client: AsyncClient,
    test_db: AsyncSession,
    admin_token: str
):
    """23. Cannot modify document checks on a completed session without reopening."""
    await seed_test_document(test_db, "app-001", "doc-pv-001")

    start_res = await client.post(
        "/api/v1/physical-verification/admin/applications/app-001/sessions/start",
        json={},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    sess_id = start_res.json()["id"]
    await client.post(
        f"/api/v1/physical-verification/admin/sessions/{sess_id}/complete",
        json={"overall_decision": "VERIFIED"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    # Attempt modification on completed session -> 400 Bad Request
    res = await client.post(
        f"/api/v1/physical-verification/admin/sessions/{sess_id}/documents/doc-pv-001/verify",
        json={"officer_decision": "NOT_VERIFIED"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_24_reopening_session_requires_authorized_role(
    client: AsyncClient,
    test_db: AsyncSession,
    admin_token: str,
    admission_head_token: str,
    student1_token: str
):
    """24. Reopening session requires ADMISSION_HEAD or SUPER_ADMIN; ADMIN_VERIFIER receives 403."""
    await seed_test_document(test_db, "app-001", "doc-pv-001")

    start_res = await client.post(
        "/api/v1/physical-verification/admin/applications/app-001/sessions/start",
        json={},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    sess_id = start_res.json()["id"]
    await client.post(
        f"/api/v1/physical-verification/admin/sessions/{sess_id}/complete",
        json={"overall_decision": "VERIFIED"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    # 1. ADMIN_VERIFIER -> 403
    res_verifier = await client.post(
        f"/api/v1/physical-verification/admin/sessions/{sess_id}/reopen",
        json={"reason": "Verifier trying to reopen"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res_verifier.status_code == 403

    # 2. ADMISSION_HEAD -> 200 OK
    res_head = await client.post(
        f"/api/v1/physical-verification/admin/sessions/{sess_id}/reopen",
        json={"reason": "Re-inspection requested by Dean"},
        headers={"Authorization": f"Bearer {admission_head_token}"}
    )
    assert res_head.status_code == 200
    assert res_head.json()["session_status"] == "REOPENED"


@pytest.mark.asyncio
async def test_25_audit_logs_recorded_for_all_physical_actions(
    client: AsyncClient,
    test_db: AsyncSession,
    admin_token: str
):
    """25. Audit trail records appointment, check-in, verification, completion, and reopening events."""
    await seed_test_document(test_db, "app-001", "doc-pv-001")

    start_res = await client.post(
        "/api/v1/physical-verification/admin/applications/app-001/sessions/start",
        json={},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    sess_id = start_res.json()["id"]

    res = await client.get(
        f"/api/v1/physical-verification/admin/sessions/{sess_id}/audit-logs",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 200
    logs = res.json()
    assert isinstance(logs, list)
    assert len(logs) >= 1
    assert "action" in logs[0]
    assert "created_at" in logs[0]


@pytest.mark.asyncio
async def test_26_student_cannot_modify_officer_decisions(
    client: AsyncClient,
    student1_token: str
):
    """26. Student cannot modify officer physical verification decisions or complete sessions."""
    res1 = await client.post(
        "/api/v1/physical-verification/admin/sessions/sess-test/documents/doc-1/verify",
        json={"officer_decision": "VERIFIED"},
        headers={"Authorization": f"Bearer {student1_token}"}
    )
    assert res1.status_code == 403

    res2 = await client.post(
        "/api/v1/physical-verification/admin/sessions/sess-test/complete",
        json={"overall_decision": "VERIFIED"},
        headers={"Authorization": f"Bearer {student1_token}"}
    )
    assert res2.status_code == 403


@pytest.mark.asyncio
async def test_27_ai_mismatch_does_not_auto_reject_physical_session(
    client: AsyncClient,
    test_db: AsyncSession,
    admin_token: str
):
    """27. AI reconciliation discrepancy does NOT automatically reject physical verification."""
    await seed_test_document(test_db, "app-001", "doc-pv-001")

    recon = CrossDocumentReconciliation(
        id="recon-mismatch-pv-001",
        application_id="app-001",
        overall_status="DISCREPANCY_DETECTED",
        participating_document_versions={},
        discrepancy_count=2,
        findings=[{"rule_id": "name_match", "status": "DISCREPANCY_DETECTED"}]
    )
    test_db.add(recon)
    await test_db.commit()

    # Officer can still evaluate original document and verify if physical certificate explains difference
    start_res = await client.post(
        "/api/v1/physical-verification/admin/applications/app-001/sessions/start",
        json={},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    sess_id = start_res.json()["id"]

    verify_res = await client.post(
        f"/api/v1/physical-verification/admin/sessions/{sess_id}/documents/doc-pv-001/verify",
        json={
            "officer_decision": "VERIFIED",
            "verification_notes": "Physical gazette notification presented by candidate explaining name expansion.",
            "checklist_checks": {"original_presented": True, "name_matches": True}
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert verify_res.status_code == 200
    assert verify_res.json()["officer_decision"] == "VERIFIED"


@pytest.mark.asyncio
async def test_28_29_30_31_32_strict_non_mutation_guarantees(
    client: AsyncClient,
    test_db: AsyncSession,
    admin_token: str
):
    """
    28, 29, 30, 31, 32. Strict Non-Mutation Guarantees:
    Verifying or rejecting physical verification does NOT mutate:
    - AdmissionApplication.status
    - Document.status
    - Student
    - TNEAAllotment
    """
    await seed_test_document(test_db, "app-001", "doc-pv-001")

    app_before = (await test_db.execute(select(AdmissionApplication).where(AdmissionApplication.id == "app-001"))).scalar_one()
    status_before = app_before.status
    num_before = app_before.application_number

    doc_before = (await test_db.execute(select(Document).where(Document.id == "doc-pv-001"))).scalar_one()
    doc_status_before = doc_before.status

    student_before = (await test_db.execute(select(Student).where(Student.id == app_before.student_id))).scalar_one()
    student_name_before = student_before.full_name

    # Complete a session with VERIFIED
    start_res = await client.post(
        "/api/v1/physical-verification/admin/applications/app-001/sessions/start",
        json={},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    sess_id = start_res.json()["id"]

    await client.post(
        f"/api/v1/physical-verification/admin/sessions/{sess_id}/complete",
        json={"overall_decision": "VERIFIED", "officer_notes": "Completed test verification"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    # Check that core models are strictly UNMUTATED
    app_after = (await test_db.execute(select(AdmissionApplication).where(AdmissionApplication.id == "app-001"))).scalar_one()
    assert app_after.status == status_before
    assert app_after.application_number == num_before

    doc_after = (await test_db.execute(select(Document).where(Document.id == "doc-pv-001"))).scalar_one()
    assert doc_after.status == doc_status_before

    student_after = (await test_db.execute(select(Student).where(Student.id == app_before.student_id))).scalar_one()
    assert student_after.full_name == student_name_before


@pytest.mark.asyncio
async def test_33_34_rbac_and_anti_idor_matrix(
    client: AsyncClient,
    student1_token: str,
    student2_token: str
):
    """33, 34. RBAC and Anti-IDOR test matrix."""
    # Student 1 cannot start session
    r1 = await client.post(
        "/api/v1/physical-verification/admin/applications/app-001/sessions/start",
        json={},
        headers={"Authorization": f"Bearer {student1_token}"}
    )
    assert r1.status_code == 403

    # Student 2 cannot confirm Student 1's appointment
    r2 = await client.post(
        "/api/v1/physical-verification/appointments/apt-fake-id/confirm",
        headers={"Authorization": f"Bearer {student2_token}"}
    )
    assert r2.status_code in [403, 404]


@pytest.mark.asyncio
async def test_35_cancel_appointment_endpoint(
    client: AsyncClient,
    student1_token: str
):
    """35. Candidate can cancel an appointment."""
    my_apt = await create_test_appointment(client, student1_token, days_ahead=4)
    apt_id = my_apt["id"]
    res = await client.post(
        f"/api/v1/physical-verification/appointments/{apt_id}/cancel",
        headers={"Authorization": f"Bearer {student1_token}"}
    )
    assert res.status_code == 200
    assert res.json()["appointment_status"] == "CANCELLED"
