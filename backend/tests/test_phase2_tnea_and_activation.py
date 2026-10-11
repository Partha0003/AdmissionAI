import pytest
import hashlib
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tnea_allotment import TNEAAllotment, TNEAImportBatch
from app.models.activation_token import StudentActivationToken
from app.models.student import Student
from app.models.admission import AdmissionApplication, AdmissionStatusHistory
from app.models.user import User
from app.adapters.tnea_adapter import MockTNEAAdapter


@pytest.mark.asyncio
async def test_mock_tnea_adapter_validation():
    adapter = MockTNEAAdapter()

    valid_record = {
        "tnea_application_number": "XYZ2026999",
        "allotment_number": "XYZALT2026999",
        "student_name": "Test Candidate",
        "college_code": "XYZ",
        "college_name": "XYZ Engineering College",
        "branch_name": "Computer Science and Engineering",
        "allotment_date": "2026-08-10",
        "joining_deadline": "2026-08-25",
        "allotment_status": "ALLOTTED",
    }
    is_valid, errors = adapter.validate_record(valid_record, target_institution_code="XYZ")
    assert is_valid is True
    assert len(errors) == 0

    # Wrong college code
    wrong_inst_record = dict(valid_record, college_code="ABC")
    is_valid_wrong, errors_wrong = adapter.validate_record(wrong_inst_record, target_institution_code="XYZ")
    assert is_valid_wrong is False
    assert any("Institution mismatch" in e for e in errors_wrong)

    # Missing mandatory field
    missing_field_record = dict(valid_record)
    del missing_field_record["student_name"]
    is_valid_missing, errors_missing = adapter.validate_record(missing_field_record, target_institution_code="XYZ")
    assert is_valid_missing is False
    assert any("Missing mandatory field 'student_name'" in e for e in errors_missing)


@pytest.mark.asyncio
async def test_admin_import_allotments_success(client: AsyncClient, admin_token: str, test_db: AsyncSession):
    payload = {
        "source": "MOCK_TNEA_TEST",
        "filename_or_reference": "sample_batch_01.json",
        "records": [
            {
                "tnea_application_number": "XYZ2026201",
                "allotment_number": "XYZALT2026201",
                "student_name": "Venkatesh Babu",
                "date_of_birth": "2008-03-15",
                "email": "venkatesh.xyz2026201@demo.admissionai.local",
                "mobile": "9840199991",
                "college_code": "XYZ",
                "college_name": "XYZ Engineering College",
                "branch_code": "CSE",
                "branch_name": "Computer Science and Engineering",
                "community": "BC",
                "quota": "GOVERNMENT",
                "cutoff_mark": 195.0,
                "allotment_date": "2026-08-10",
                "joining_deadline": "2026-08-25",
                "allotment_status": "ALLOTTED"
            },
            {
                "tnea_application_number": "XYZ2026202",
                "allotment_number": "XYZALT2026202",
                "student_name": "Lakshmi Narayanan",
                "date_of_birth": "2008-07-20",
                "email": "lakshmi.xyz2026202@demo.admissionai.local",
                "mobile": "9840199992",
                "college_code": "XYZ",
                "college_name": "XYZ Engineering College",
                "branch_code": "ECE",
                "branch_name": "Electronics and Communication Engineering",
                "community": "MBC",
                "quota": "GOVERNMENT",
                "cutoff_mark": 191.5,
                "allotment_date": "2026-08-10",
                "joining_deadline": "2026-08-25",
                "allotment_status": "ALLOTTED"
            }
        ]
    }

    response = await client.post(
        "/api/v1/admin/tnea/import",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_records"] == 2
    assert data["successful_records"] == 2
    assert data["duplicate_records"] == 0
    assert data["failed_records"] == 0
    assert data["status"] == "COMPLETED"
    assert len(data["results"]) == 2
    assert data["results"][0]["raw_activation_token"] is not None

    # Check database records
    student_res = await test_db.execute(select(Student).where(Student.tnea_application_number == "XYZ2026201"))
    student = student_res.scalar_one_or_none()
    assert student is not None
    assert student.status == "ACTIVATION_PENDING"

    # Check Admission Application & Status History
    app_res = await test_db.execute(select(AdmissionApplication).where(AdmissionApplication.student_id == student.id))
    app = app_res.scalar_one_or_none()
    assert app is not None
    assert app.status == "ACTIVATION_PENDING"

    # Check user is created but inactive
    user_res = await test_db.execute(select(User).where(User.id == student.user_id))
    user = user_res.scalar_one_or_none()
    assert user is not None
    assert user.is_active is False


@pytest.mark.asyncio
async def test_import_idempotency_and_duplicate_detection(client: AsyncClient, admin_token: str):
    record = {
        "tnea_application_number": "XYZ2026301",
        "allotment_number": "XYZALT2026301",
        "student_name": "Deepak Raj",
        "date_of_birth": "2008-02-10",
        "email": "deepak.xyz2026301@demo.admissionai.local",
        "mobile": "9840199993",
        "college_code": "XYZ",
        "college_name": "XYZ Engineering College",
        "branch_name": "Information Technology",
        "allotment_date": "2026-08-10",
        "joining_deadline": "2026-08-25",
        "allotment_status": "ALLOTTED"
    }
    payload = {"records": [record]}

    # First import
    res1 = await client.post(
        "/api/v1/admin/tnea/import",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res1.status_code == 200
    assert res1.json()["successful_records"] == 1

    # Second import with the exact same record (Idempotent)
    res2 = await client.post(
        "/api/v1/admin/tnea/import",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["successful_records"] == 0
    assert data2["duplicate_records"] == 1
    assert data2["results"][0]["status"] == "SKIPPED_DUPLICATE"


@pytest.mark.asyncio
async def test_import_wrong_institution_and_validation_failure(client: AsyncClient, admin_token: str):
    payload = {
        "records": [
            {
                # Wrong college code ABC
                "tnea_application_number": "XYZ2026401",
                "allotment_number": "XYZALT2026401",
                "student_name": "Wrong College Candidate",
                "college_code": "ABC",
                "college_name": "ABC Institute of Tech",
                "branch_name": "Mechanical Engineering",
                "allotment_date": "2026-08-10",
                "joining_deadline": "2026-08-25",
                "allotment_status": "ALLOTTED"
            },
            {
                # Missing branch name
                "tnea_application_number": "XYZ2026402",
                "allotment_number": "XYZALT2026402",
                "student_name": "Invalid Record Candidate",
                "college_code": "XYZ",
                "college_name": "XYZ Engineering College",
                "branch_name": "",
                "allotment_date": "2026-08-10",
                "joining_deadline": "2026-08-25",
                "allotment_status": "ALLOTTED"
            }
        ]
    }

    res = await client.post(
        "/api/v1/admin/tnea/import",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["skipped_records"] == 1
    assert data["failed_records"] == 1
    assert data["results"][0]["status"] == "REJECTED_WRONG_INSTITUTION"
    assert data["results"][1]["status"] == "FAILED_VALIDATION"


@pytest.mark.asyncio
async def test_student_cannot_trigger_import(client: AsyncClient, student1_token: str):
    payload = {"records": []}
    res = await client.post(
        "/api/v1/admin/tnea/import",
        json=payload,
        headers={"Authorization": f"Bearer {student1_token}"}
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_successful_student_activation_workflow(client: AsyncClient, admin_token: str, test_db: AsyncSession):
    # 1. Import a candidate
    record = {
        "tnea_application_number": "XYZ2026501",
        "allotment_number": "XYZALT2026501",
        "student_name": "Meenakshi Sundaram",
        "date_of_birth": "2008-05-18",
        "email": "meenakshi.xyz2026501@demo.admissionai.local",
        "mobile": "9840199995",
        "college_code": "XYZ",
        "college_name": "XYZ Engineering College",
        "branch_name": "Artificial Intelligence and Data Science",
        "allotment_date": "2026-08-10",
        "joining_deadline": "2026-08-25",
        "allotment_status": "ALLOTTED"
    }
    import_res = await client.post(
        "/api/v1/admin/tnea/import",
        json={"records": [record]},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    raw_token = import_res.json()["results"][0]["raw_activation_token"]
    assert raw_token is not None

    # 2. Student activates account with token
    activate_res = await client.post(
        "/api/v1/auth/activate",
        json={
            "activation_token": raw_token,
            "password": "NewSecureStudent@123"
        }
    )
    assert activate_res.status_code == 200
    act_data = activate_res.json()
    assert act_data["success"] is True
    assert act_data["new_status"] == "ACTIVATED"

    # 3. Verify student can log in with new password
    login_res = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "XYZ2026501",
            "password": "NewSecureStudent@123"
        }
    )
    assert login_res.status_code == 200
    token_data = login_res.json()
    assert token_data["role"] == "STUDENT"
    student_jwt = token_data["access_token"]

    # 4. Verify student can fetch their allotment
    allotment_res = await client.get(
        "/api/v1/students/me/allotment",
        headers={"Authorization": f"Bearer {student_jwt}"}
    )
    assert allotment_res.status_code == 200
    allot_data = allotment_res.json()
    assert allot_data["tnea_application_number"] == "XYZ2026501"
    assert allot_data["branch_name"] == "Artificial Intelligence and Data Science"


@pytest.mark.asyncio
async def test_activation_token_security_and_rejection(client: AsyncClient, admin_token: str, test_db: AsyncSession):
    # 1. Invalid token
    res_inv = await client.post(
        "/api/v1/auth/activate",
        json={"activation_token": "ACT-INVALID-TOKEN-9999", "password": "Password@123"}
    )
    assert res_inv.status_code == 400
    assert "Invalid activation token" in res_inv.json()["detail"]

    # 2. Import candidate
    record = {
        "tnea_application_number": "XYZ2026601",
        "allotment_number": "XYZALT2026601",
        "student_name": "Rohan Kumar",
        "college_code": "XYZ",
        "college_name": "XYZ Engineering College",
        "branch_name": "Computer Science and Engineering",
        "allotment_date": "2026-08-10",
        "joining_deadline": "2026-08-25",
        "allotment_status": "ALLOTTED"
    }
    import_res = await client.post(
        "/api/v1/admin/tnea/import",
        json={"records": [record]},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    raw_token = import_res.json()["results"][0]["raw_activation_token"]

    # Test Expired Token by manually modifying expires_at
    token_h = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    t_query = select(StudentActivationToken).where(StudentActivationToken.token_hash == token_h)
    t_res = await test_db.execute(t_query)
    token_rec = t_res.scalar_one()
    token_rec.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
    await test_db.commit()

    res_exp = await client.post(
        "/api/v1/auth/activate",
        json={"activation_token": raw_token, "password": "Password@123"}
    )
    assert res_exp.status_code == 400
    assert "expired" in res_exp.json()["detail"].lower()

    # Reset expiration and activate once
    token_rec.expires_at = datetime.now(timezone.utc) + timedelta(days=2)
    await test_db.commit()

    res_act = await client.post(
        "/api/v1/auth/activate",
        json={"activation_token": raw_token, "password": "Password@123"}
    )
    assert res_act.status_code == 200

    # Test Reused Token (single-use check)
    res_reuse = await client.post(
        "/api/v1/auth/activate",
        json={"activation_token": raw_token, "password": "Password@123"}
    )
    assert res_reuse.status_code == 400
    assert "already been used" in res_reuse.json()["detail"]


@pytest.mark.asyncio
async def test_student_lifecycle_transition_to_in_progress(client: AsyncClient, test_db: AsyncSession):
    # Student 1 is already in ACTIVATED state from conftest
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "XYZ2026001", "password": "Student@1234"}
    )
    student_jwt = login_res.json()["access_token"]

    # Transition ACTIVATED -> APPLICATION_IN_PROGRESS
    trans_res = await client.post(
        "/api/v1/admissions/app-001/transition",
        json={
            "target_state": "APPLICATION_IN_PROGRESS",
            "reason": "Candidate initiated online application form fill"
        },
        headers={"Authorization": f"Bearer {student_jwt}"}
    )
    assert trans_res.status_code == 200
    assert trans_res.json()["status"] == "APPLICATION_IN_PROGRESS"

    # Attempt Invalid Transition (e.g. APPLICATION_IN_PROGRESS -> ERP_SYNCED directly)
    invalid_res = await client.post(
        "/api/v1/admissions/app-001/transition",
        json={
            "target_state": "ERP_SYNCED",
            "reason": "Skip steps"
        },
        headers={"Authorization": f"Bearer {student_jwt}"}
    )
    assert invalid_res.status_code == 400
    assert "Invalid transition" in invalid_res.json()["detail"]


@pytest.mark.asyncio
async def test_admin_allotment_views_and_filters(client: AsyncClient, admin_token: str):
    res = await client.get(
        "/api/v1/admin/allotments",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 200
    allotments = res.json()
    assert isinstance(allotments, list)

    # Batches list
    batches_res = await client.get(
        "/api/v1/admin/tnea/imports",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert batches_res.status_code == 200
    batches = batches_res.json()
    assert isinstance(batches, list)
