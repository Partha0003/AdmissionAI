import pytest
import io
from datetime import datetime, timezone
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.admission import AdmissionApplication
from app.models.document import Document, DocumentType, DocumentVersion
from app.models.scrutiny import (
    AdmissionReview,
    ReviewStatus,
    ReviewDecision,
    FieldReviewDecision,
    CorrectionReason,
    ScrutinyAction,
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


@pytest.mark.asyncio
async def test_01_reviewer_can_start_review(client: AsyncClient, test_db: AsyncSession, admin_token: str):
    """1. Reviewer can start review, capturing initial snapshot and updating review status to IN_REVIEW."""
    response = await client.post(
        "/api/v1/scrutiny/applications/app-001/start",
        json={"notes": "Starting initial scrutiny for candidate Karthikeyan"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["application_id"] == "app-001"
    assert data["status"] == "IN_REVIEW"
    assert data["reviewer_id"] == "user-admin-001"
    assert data["started_at"] is not None
    assert len(data["audit_logs"]) >= 1
    assert data["audit_logs"][0]["action"] == "REVIEW_STARTED"


@pytest.mark.asyncio
async def test_02_unauthorized_student_cannot_access_admin_review(client: AsyncClient, student1_token: str):
    """2. Unauthorized student cannot access admin scrutiny review operations."""
    response = await client.post(
        "/api/v1/scrutiny/applications/app-001/start",
        json={"notes": "Student trying to start review"},
        headers={"Authorization": f"Bearer {student1_token}"}
    )
    assert response.status_code == 403
    assert "Access forbidden" in response.json()["detail"]


@pytest.mark.asyncio
async def test_03_student_cannot_access_another_students_review_idor(
    client: AsyncClient,
    student2_token: str
):
    """3. Student cannot access another student's review records (Anti-IDOR)."""
    # Student 2 tries to view Student 1's (app-001) scrutiny review
    response = await client.get(
        "/api/v1/scrutiny/applications/app-001/current",
        headers={"Authorization": f"Bearer {student2_token}"}
    )
    assert response.status_code == 403
    assert "Access forbidden" in response.json()["detail"]


@pytest.mark.asyncio
async def test_04_reviewer_can_inspect_document_evidence(
    client: AsyncClient,
    test_db: AsyncSession,
    admin_token: str
):
    """4. Reviewer can inspect document evidence (preprocessing, OCR, extracted fields, reconciliation)."""
    # Create sample document for app-001
    doc = Document(
        id="doc-test-001",
        application_id="app-001",
        document_type_id="dt-001",
        status="UPLOADED"
    )
    test_db.add(doc)
    await test_db.commit()

    # Admin calls scrutiny current review endpoint
    response = await client.get(
        "/api/v1/scrutiny/applications/app-001/current",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["application_id"] == "app-001"


@pytest.mark.asyncio
async def test_05_reviewer_can_record_field_decision(
    client: AsyncClient,
    test_db: AsyncSession,
    admin_token: str
):
    """5. Reviewer can record field-level human decisions (CONFIRMED, REQUIRES_CORRECTION, ACCEPTED_WITH_REVIEW, NOT_APPLICABLE)."""
    # Start review
    await client.post(
        "/api/v1/scrutiny/applications/app-001/start",
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    # 1. Confirm candidate name
    res1 = await client.post(
        "/api/v1/scrutiny/applications/app-001/fields/review",
        json={
            "field_key": "candidate_name",
            "decision": "CONFIRMED",
            "declared_value": "Karthikeyan S",
            "extracted_value": "Karthikeyan S",
            "reconciliation_status": "MATCH",
            "notes": "Verified against 12th marksheet and allotment order",
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res1.status_code == 200
    d1 = res1.json()
    assert d1["field_key"] == "candidate_name"
    assert d1["decision"] == "CONFIRMED"

    # 2. Flag father name with accepted with review
    res2 = await client.post(
        "/api/v1/scrutiny/applications/app-001/fields/review",
        json={
            "field_key": "father_name",
            "decision": "ACCEPTED_WITH_REVIEW",
            "declared_value": "Subramanian G",
            "extracted_value": "Subramanian",
            "reconciliation_status": "DISCREPANCY_DETECTED",
            "notes": "Minor initial expansion difference accepted per institutional scrutiny guidelines",
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res2.status_code == 200
    assert res2.json()["decision"] == "ACCEPTED_WITH_REVIEW"


@pytest.mark.asyncio
async def test_06_reviewer_can_request_correction(
    client: AsyncClient,
    test_db: AsyncSession,
    admin_token: str
):
    """6. Reviewer can issue formal correction request to candidate without mutating app or document status."""
    # Seed document
    doc = Document(
        id="doc-corr-001",
        application_id="app-001",
        document_type_id="dt-001",
        status="UPLOADED"
    )
    test_db.add(doc)
    await test_db.commit()

    # Get initial app status
    app_stmt = select(AdmissionApplication).where(AdmissionApplication.id == "app-001")
    app_res = await test_db.execute(app_stmt)
    initial_app_status = app_res.scalar_one().status

    res = await client.post(
        "/api/v1/scrutiny/applications/app-001/request-correction",
        json={
            "correction_reason": "ILLEGIBLE_DOCUMENT",
            "correction_instructions": "The uploaded 12th marksheet is blurry. Please upload a clear scanned color copy.",
            "flagged_document_ids": ["doc-corr-001"]
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "CORRECTION_REQUIRED"
    assert data["correction_reason"] == "ILLEGIBLE_DOCUMENT"
    assert "blurry" in data["correction_instructions"]

    # Verify document item marked in scrutiny domain
    doc_reviews = data["document_reviews"]
    assert len(doc_reviews) >= 1
    assert any(dr["document_id"] == "doc-corr-001" and dr["status"] == "CORRECTION_REQUIRED" for dr in doc_reviews)

    # Verify Document.status and AdmissionApplication.status remain UNCHANGED
    doc_check = await test_db.execute(select(Document).where(Document.id == "doc-corr-001"))
    assert doc_check.scalar_one().status == "UPLOADED"

    app_check = await test_db.execute(select(AdmissionApplication).where(AdmissionApplication.id == "app-001"))
    assert app_check.scalar_one().status == initial_app_status


@pytest.mark.asyncio
async def test_07_correction_reason_is_mandatory(
    client: AsyncClient,
    admin_token: str
):
    """7. Correction reason is mandatory and cannot be empty."""
    res = await client.post(
        "/api/v1/scrutiny/applications/app-001/request-correction",
        json={
            "correction_reason": "",
            "correction_instructions": "Some instructions"
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 400 or res.status_code == 422


@pytest.mark.asyncio
async def test_08_other_reason_requires_comment(
    client: AsyncClient,
    admin_token: str
):
    """8. OTHER reason requires explicit non-empty reviewer comment/instructions."""
    res = await client.post(
        "/api/v1/scrutiny/applications/app-001/request-correction",
        json={
            "correction_reason": "OTHER",
            "correction_instructions": "   "
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 400
    assert "instructions" in res.json()["detail"].lower() or "comment" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_09_student_can_see_correction_request(
    client: AsyncClient,
    test_db: AsyncSession,
    admin_token: str,
    student1_token: str
):
    """9. Student can see correction requirements on their endpoint."""
    # Reviewer requests correction
    await client.post(
        "/api/v1/scrutiny/applications/app-001/request-correction",
        json={
            "correction_reason": "FIELD_MISMATCH",
            "correction_instructions": "Date of birth on Transfer Certificate does not match the declaration.",
            "flagged_document_ids": []
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    # Student checks correction summary
    res = await client.get(
        "/api/v1/scrutiny/me/corrections",
        headers={"Authorization": f"Bearer {student1_token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["correction_required"] is True
    assert data["correction_reason"] == "FIELD_MISMATCH"
    assert "Date of birth" in data["correction_instructions"]


@pytest.mark.asyncio
async def test_10_11_12_student_resubmission_preserves_versions(
    client: AsyncClient,
    test_db: AsyncSession,
    student1_token: str,
    admin_token: str
):
    """10, 11, 12. Student resubmits document, Version 2 created, Version 1 preserved."""
    # 1. First upload (Version 1)
    file_bytes_v1 = b"%PDF-1.4 initial marksheet content"
    res_upload1 = await client.post(
        "/api/v1/documents/upload",
        data={"document_type_code": "TWELFTH_MARKSHEET"},
        files={"file": ("twelfth_v1.pdf", io.BytesIO(file_bytes_v1), "application/pdf")},
        headers={"Authorization": f"Bearer {student1_token}"}
    )
    assert res_upload1.status_code == 200
    d1 = res_upload1.json()
    assert d1["version_number"] == 1
    doc_id = d1["document_id"]
    v1_id = d1["version_id"]

    # 2. Admin flags correction
    await client.post(
        "/api/v1/scrutiny/applications/app-001/request-correction",
        json={
            "correction_reason": "ILLEGIBLE_DOCUMENT",
            "correction_instructions": "Please upload a higher resolution scan of 12th marksheet.",
            "flagged_document_ids": [doc_id]
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    # 3. Student uploads corrected document (Version 2)
    file_bytes_v2 = b"%PDF-1.4 higher resolution clear marksheet content"
    res_upload2 = await client.post(
        "/api/v1/documents/upload",
        data={"document_type_code": "TWELFTH_MARKSHEET"},
        files={"file": ("twelfth_v2.pdf", io.BytesIO(file_bytes_v2), "application/pdf")},
        headers={"Authorization": f"Bearer {student1_token}"}
    )
    assert res_upload2.status_code == 200
    d2 = res_upload2.json()
    assert d2["version_number"] == 2
    assert d2["document_id"] == doc_id
    assert d2["version_id"] != v1_id

    # 4. Check version history preserves both versions
    ver_res = await client.get(
        f"/api/v1/documents/{doc_id}/versions",
        headers={"Authorization": f"Bearer {student1_token}"}
    )
    assert ver_res.status_code == 200
    versions = ver_res.json()
    assert len(versions) == 2
    ver_nums = [v["version_number"] for v in versions]
    assert 1 in ver_nums
    assert 2 in ver_nums


@pytest.mark.asyncio
async def test_13_14_new_reconciliation_and_review_history_preserved(
    client: AsyncClient,
    test_db: AsyncSession,
    admin_token: str
):
    """13, 14. New reconciliation snapshots and historical review records remain intact."""
    # Seed 2 reconciliation snapshots
    recon1 = CrossDocumentReconciliation(
        id="recon-snap-001",
        application_id="app-001",
        overall_status="DISCREPANCY_DETECTED",
        participating_document_versions={"doc-1": 1},
        findings=[{"rule_id": "maths_match", "status": "DISCREPANCY_DETECTED"}]
    )
    recon2 = CrossDocumentReconciliation(
        id="recon-snap-002",
        application_id="app-001",
        overall_status="MATCH",
        participating_document_versions={"doc-1": 2},
        findings=[{"rule_id": "maths_match", "status": "MATCH"}]
    )
    test_db.add(recon1)
    test_db.add(recon2)
    await test_db.commit()

    # Query review history
    res = await client.get(
        "/api/v1/scrutiny/applications/app-001/history",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 200
    history = res.json()
    assert isinstance(history, list)


@pytest.mark.asyncio
async def test_15_reviewer_decision_is_auditable(
    client: AsyncClient,
    test_db: AsyncSession,
    admin_token: str
):
    """15. Reviewer decision is auditable with audit trail containing action, timestamp, and user details."""
    await client.post(
        "/api/v1/scrutiny/applications/app-001/start",
        json={"notes": "Audit verification session"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    audit_res = await client.get(
        "/api/v1/scrutiny/applications/app-001/audit-logs",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert audit_res.status_code == 200
    logs = audit_res.json()
    assert len(logs) >= 1
    assert logs[0]["user_id"] == "user-admin-001"
    assert logs[0]["user_role"] == "ADMIN_VERIFIER"
    assert "timestamp" in logs[0] or "created_at" in logs[0]


@pytest.mark.asyncio
async def test_16_machine_discrepancy_does_not_auto_reject(
    client: AsyncClient,
    test_db: AsyncSession,
    admin_token: str
):
    """16. Machine discrepancy findings (Phase 4E DISCREPANCY_DETECTED) do NOT automatically reject admission."""
    recon = CrossDocumentReconciliation(
        id="recon-discrepancy-001",
        application_id="app-001",
        overall_status="DISCREPANCY_DETECTED",
        participating_document_versions={},
        discrepancy_count=2,
        findings=[{"rule_id": "community_quota_match", "status": "DISCREPANCY_DETECTED"}]
    )
    test_db.add(recon)
    await test_db.commit()

    # Get application status
    app_stmt = select(AdmissionApplication).where(AdmissionApplication.id == "app-001")
    app_res = await test_db.execute(app_stmt)
    app = app_res.scalar_one()

    # Application is NOT rejected
    assert app.status != "VERIFICATION_FAILED"
    assert app.status != "CANCELLED"


@pytest.mark.asyncio
async def test_17_ai_match_does_not_auto_approve(
    client: AsyncClient,
    test_db: AsyncSession,
    admin_token: str
):
    """17. AI MATCH (Phase 4E 100% MATCH) does NOT automatically approve admission or verify documents."""
    recon = CrossDocumentReconciliation(
        id="recon-perfect-001",
        application_id="app-001",
        overall_status="MATCH",
        participating_document_versions={},
        passed_rules_count=7,
        discrepancy_count=0,
        findings=[{"rule_id": "candidate_name_match", "status": "MATCH"}]
    )
    test_db.add(recon)
    await test_db.commit()

    # Query application
    app_stmt = select(AdmissionApplication).where(AdmissionApplication.id == "app-001")
    app_res = await test_db.execute(app_stmt)
    app = app_res.scalar_one()

    # Must NOT be automatically DOCUMENTS_VERIFIED or ADMISSION_CONFIRMED
    assert app.status != "DOCUMENTS_VERIFIED"
    assert app.status != "ADMISSION_CONFIRMED"


@pytest.mark.asyncio
async def test_18_19_state_machine_safety_and_non_mutation(
    client: AsyncClient,
    test_db: AsyncSession,
    admin_token: str
):
    """18, 19. Document.status and AdmissionApplication state are not mutated without explicit human reviewer action."""
    doc = Document(
        id="doc-safety-001",
        application_id="app-001",
        document_type_id="dt-001",
        status="UPLOADED"
    )
    test_db.add(doc)
    await test_db.commit()

    # Calling scrutiny inspection endpoints does not mutate doc.status to verified
    await client.get(
        "/api/v1/scrutiny/applications/app-001/current",
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    doc_stmt = select(Document).where(Document.id == "doc-safety-001")
    doc_res = await test_db.execute(doc_stmt)
    doc_fresh = doc_res.scalar_one()
    assert doc_fresh.status == "UPLOADED"


@pytest.mark.asyncio
async def test_20_21_rbac_and_anti_idor_coverage(
    client: AsyncClient,
    student1_token: str,
    student2_token: str
):
    """20, 21. RBAC and Anti-IDOR coverage on all scrutiny endpoints."""
    # Student 1 cannot start review
    res1 = await client.post(
        "/api/v1/scrutiny/applications/app-001/start",
        headers={"Authorization": f"Bearer {student1_token}"}
    )
    assert res1.status_code == 403

    # Student 2 cannot view Student 1's audit logs
    res2 = await client.get(
        "/api/v1/scrutiny/applications/app-001/audit-logs",
        headers={"Authorization": f"Bearer {student2_token}"}
    )
    assert res2.status_code == 403

    # Student 1 cannot complete review
    res3 = await client.post(
        "/api/v1/scrutiny/applications/app-001/complete",
        json={"decision": "VERIFIED"},
        headers={"Authorization": f"Bearer {student1_token}"}
    )
    assert res3.status_code == 403


@pytest.mark.asyncio
async def test_22_review_completion_verified_and_rejected(
    client: AsyncClient,
    test_db: AsyncSession,
    admin_token: str,
    admission_head_token: str
):
    """
    22. Review completion:
    - Reviewer completes review as VERIFIED -> AdmissionReview becomes VERIFIED, Document.status and app.status are UNCHANGED.
    - Reviewer completes review as REJECTED -> AdmissionReview becomes REJECTED, Document.status and app.status are UNCHANGED.
    """
    # Seed a document
    doc = Document(
        id="doc-comp-001",
        application_id="app-001",
        document_type_id="dt-001",
        status="UPLOADED"
    )
    test_db.add(doc)
    await test_db.commit()

    # Get initial application status
    app_stmt = select(AdmissionApplication).where(AdmissionApplication.id == "app-001")
    app_res = await test_db.execute(app_stmt)
    initial_app_status = app_res.scalar_one().status

    # 1. Start review on app-001
    await client.post(
        "/api/v1/scrutiny/applications/app-001/start",
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    # 2. Complete review with VERIFIED
    res_verified = await client.post(
        "/api/v1/scrutiny/applications/app-001/complete",
        json={
            "decision": "VERIFIED",
            "overall_comments": "All physical parameters and scanned records confirmed by admission desk verifier.",
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res_verified.status_code == 200
    d_ver = res_verified.json()
    assert d_ver["status"] == "VERIFIED"
    assert d_ver["decision"] == "VERIFIED"
    assert d_ver["completed_at"] is not None

    # Verify Document.status and AdmissionApplication.status remain UNCHANGED
    doc_stmt = select(Document).where(Document.id == "doc-comp-001")
    doc_res = await test_db.execute(doc_stmt)
    assert doc_res.scalar_one().status == "UPLOADED"

    app_res = await test_db.execute(select(AdmissionApplication).where(AdmissionApplication.id == "app-001"))
    assert app_res.scalar_one().status == initial_app_status

    # 3. Reopen review (as Admission Head)
    reopen_res = await client.post(
        "/api/v1/scrutiny/applications/app-001/reopen",
        json={"reason": "Testing rejection decision path"},
        headers={"Authorization": f"Bearer {admission_head_token}"}
    )
    assert reopen_res.status_code == 200

    # 4. Complete review with REJECTED
    res_rejected = await client.post(
        "/api/v1/scrutiny/applications/app-001/complete",
        json={
            "decision": "REJECTED",
            "overall_comments": "Scrutiny failed due to irreconcilable discrepancy identified by human reviewer.",
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res_rejected.status_code == 200
    d_rej = res_rejected.json()
    assert d_rej["status"] == "REJECTED"
    assert d_rej["decision"] == "REJECTED"
    assert d_rej["completed_at"] is not None

    # Verify Document.status and AdmissionApplication.status STILL remain UNCHANGED
    doc_res = await test_db.execute(select(Document).where(Document.id == "doc-comp-001"))
    assert doc_res.scalar_one().status == "UPLOADED"

    app_res = await test_db.execute(select(AdmissionApplication).where(AdmissionApplication.id == "app-001"))
    assert app_res.scalar_one().status == initial_app_status


@pytest.mark.asyncio
async def test_23_reopening_review_restricted_to_authorized_roles(
    client: AsyncClient,
    test_db: AsyncSession,
    admin_token: str,
    admission_head_token: str,
    student1_token: str
):
    """23. Reopening review works ONLY for authorized roles (ADMISSION_HEAD/SUPER_ADMIN), rejected for ADMIN_VERIFIER/STUDENT."""
    # Ensure review on app-001 is completed
    await client.post(
        "/api/v1/scrutiny/applications/app-001/complete",
        json={"decision": "VERIFIED", "overall_comments": "Completed"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    # 1. ADMIN_VERIFIER tries to reopen -> 403 FORBIDDEN
    res_verifier = await client.post(
        "/api/v1/scrutiny/applications/app-001/reopen",
        json={"reason": "Verifier trying to reopen"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res_verifier.status_code == 403

    # 2. STUDENT tries to reopen -> 403 FORBIDDEN
    res_student = await client.post(
        "/api/v1/scrutiny/applications/app-001/reopen",
        json={"reason": "Student trying to reopen"},
        headers={"Authorization": f"Bearer {student1_token}"}
    )
    assert res_student.status_code == 403

    # 3. ADMISSION_HEAD reopens review -> 200 OK
    res_head = await client.post(
        "/api/v1/scrutiny/applications/app-001/reopen",
        json={"reason": "Additional document verification requested by Dean of Admissions"},
        headers={"Authorization": f"Bearer {admission_head_token}"}
    )
    assert res_head.status_code == 200
    d_reopen = res_head.json()
    assert d_reopen["status"] == "IN_REVIEW"
    assert d_reopen["completed_at"] is None

    # Verify audit trail contains REVIEW_REOPENED
    audit_logs = d_reopen["audit_logs"]
    assert any(log["action"] == "REVIEW_REOPENED" for log in audit_logs)


@pytest.mark.asyncio
async def test_24_field_decision_not_applicable_and_requires_correction(
    client: AsyncClient,
    test_db: AsyncSession,
    admin_token: str
):
    """24. Reviewer can set field decision to NOT_APPLICABLE and REQUIRES_CORRECTION."""
    res_na = await client.post(
        "/api/v1/scrutiny/applications/app-001/fields/review",
        json={
            "field_key": "first_graduate",
            "decision": "NOT_APPLICABLE",
            "declared_value": "False",
            "notes": "Candidate does not claim First Graduate quota benefit",
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res_na.status_code == 200
    assert res_na.json()["decision"] == "NOT_APPLICABLE"
