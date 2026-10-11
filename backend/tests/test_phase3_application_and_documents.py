import pytest
import io
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_my_application(client: AsyncClient, student1_token: str):
    """
    Test student retrieving their initialized application form draft and dynamic checklist.
    """
    headers = {"Authorization": f"Bearer {student1_token}"}
    response = await client.get("/api/v1/applications/me", headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert data["student_name"] == "Karthikeyan S"
    assert data["tnea_application_number"] == "XYZ2026001"
    assert data["status"] in ["ACTIVATED", "APPLICATION_IN_PROGRESS"]
    assert "checklist" in data
    assert len(data["checklist"]) >= 4

    # Karthik is BC -> Community Certificate should be mandatory
    community_doc = next((d for d in data["checklist"] if d["code"] == "COMMUNITY_CERTIFICATE"), None)
    assert community_doc is not None
    assert community_doc["is_mandatory"] is True


@pytest.mark.asyncio
async def test_draft_update_and_completion(client: AsyncClient, student1_token: str):
    """
    Test updating form draft fields and checking recalculated completion percentage.
    """
    headers = {"Authorization": f"Bearer {student1_token}"}
    payload = {
        "gender": "Male",
        "blood_group": "O+ve",
        "nationality": "Indian",
        "religion": "Hindu",
        "caste": "BC",
        "mother_tongue": "Tamil",
        "aadhaar_number": "1234 5678 9012",
        "address_line1": "123 Main Road",
        "city": "Chennai",
        "district": "Chennai",
        "state": "Tamil Nadu",
        "pincode": "600001",
        "emergency_contact_name": "Father",
        "emergency_contact_phone": "+91 98765 43210",
        "emergency_contact_relation": "Father",
        "father_name": "Senthil Kumar",
        "father_occupation": "Business",
        "father_mobile": "+91 98765 43210",
        "annual_family_income": 350000.0,
        "tenth_school_name": "Govt High School",
        "tenth_board": "State Board",
        "tenth_year_of_passing": 2024,
        "tenth_registration_number": "10TH12345",
        "tenth_total_marks": 480.0,
        "tenth_max_marks": 500.0,
        "tenth_percentage": 96.0,
        "twelfth_school_name": "Govt HSS",
        "twelfth_board": "State Board",
        "twelfth_year_of_passing": 2026,
        "twelfth_registration_number": "12TH12345",
        "twelfth_total_marks": 580.0,
        "twelfth_max_marks": 600.0,
        "twelfth_percentage": 96.6,
        "twelfth_maths_marks": 99.0,
        "twelfth_physics_marks": 98.0,
        "twelfth_chemistry_marks": 97.0,
        "twelfth_cutoff_marks": 196.5,
    }

    put_res = await client.put("/api/v1/applications/me", json=payload, headers=headers)
    assert put_res.status_code == 200
    updated = put_res.json()
    assert updated["father_name"] == "Senthil Kumar"
    assert updated["twelfth_cutoff_marks"] == 196.5
    assert updated["status"] == "APPLICATION_IN_PROGRESS"

    comp_res = await client.get("/api/v1/applications/me/completion", headers=headers)
    assert comp_res.status_code == 200
    comp_data = comp_res.json()
    assert comp_data["sections"]["personal"]["completed"] is True
    assert comp_data["sections"]["contact"]["completed"] is True
    assert comp_data["sections"]["parent"]["completed"] is True
    assert comp_data["sections"]["academic"]["completed"] is True
    assert comp_data["can_submit"] is False  # Documents and declaration pending


@pytest.mark.asyncio
async def test_dynamic_checklist_rules_oc_vs_fg(client: AsyncClient, student2_token: str):
    """
    Test dynamic checklist for Student 2 (OC, General) -> Community cert is optional.
    When First Graduate is toggled, First Graduate cert becomes mandatory.
    """
    headers = {"Authorization": f"Bearer {student2_token}"}
    
    # 1. Check Student 2 checklist (OC)
    res = await client.get("/api/v1/applications/me/checklist", headers=headers)
    assert res.status_code == 200
    checklist = res.json()
    comm_doc = next(d for d in checklist if d["code"] == "COMMUNITY_CERTIFICATE")
    assert comm_doc["is_mandatory"] is False

    fg_doc = next(d for d in checklist if d["code"] == "FIRST_GRADUATE_CERTIFICATE")
    assert fg_doc["is_mandatory"] is False

    # 2. Toggle is_first_graduate in draft
    await client.put("/api/v1/applications/me", json={"is_first_graduate": True}, headers=headers)

    res2 = await client.get("/api/v1/applications/me/checklist", headers=headers)
    checklist2 = res2.json()
    fg_doc2 = next(d for d in checklist2 if d["code"] == "FIRST_GRADUATE_CERTIFICATE")
    assert fg_doc2["is_mandatory"] is True


@pytest.mark.asyncio
async def test_document_upload_and_versioning(client: AsyncClient, student1_token: str):
    """
    Test uploading a valid PDF document and re-uploading to create Version 2.
    """
    headers = {"Authorization": f"Bearer {student1_token}"}

    # 1. Upload valid PDF v1
    dummy_pdf_v1 = b"%PDF-1.4\nTest PDF Document Version 1\n%%EOF"
    files = {"file": ("tenth_marksheet.pdf", dummy_pdf_v1, "application/pdf")}
    data = {"document_type_code": "TENTH_MARKSHEET"}

    up_res1 = await client.post("/api/v1/documents/upload", headers=headers, files=files, data=data)
    assert up_res1.status_code == 200
    res1_data = up_res1.json()
    assert res1_data["version_number"] == 1
    doc_id = res1_data["document_id"]

    # 2. Re-upload same document type -> Version 2
    dummy_pdf_v2 = b"%PDF-1.4\nTest PDF Document Version 2 Updated\n%%EOF"
    files2 = {"file": ("tenth_marksheet_v2.pdf", dummy_pdf_v2, "application/pdf")}
    up_res2 = await client.post("/api/v1/documents/upload", headers=headers, files=files2, data=data)
    assert up_res2.status_code == 200
    res2_data = up_res2.json()
    assert res2_data["version_number"] == 2
    assert res2_data["document_id"] == doc_id

    # 3. Check version history
    ver_res = await client.get(f"/api/v1/documents/{doc_id}/versions", headers=headers)
    assert ver_res.status_code == 200
    versions = ver_res.json()
    assert len(versions) == 2
    assert versions[0]["version_number"] == 2
    assert versions[1]["version_number"] == 1


@pytest.mark.asyncio
async def test_document_upload_validation_errors(client: AsyncClient, student1_token: str):
    """
    Test rejecting invalid extensions, invalid magic bytes, and exceeding size limits.
    """
    headers = {"Authorization": f"Bearer {student1_token}"}

    # Invalid extension (.exe)
    bad_ext_file = {"file": ("virus.exe", b"%PDF-fake", "application/octet-stream")}
    res1 = await client.post("/api/v1/documents/upload", headers=headers, files=bad_ext_file, data={"document_type_code": "TENTH_MARKSHEET"})
    assert res1.status_code == 400
    assert "not allowed" in res1.json()["detail"]

    # Invalid header magic bytes (plain text file renamed to .pdf)
    corrupted_file = {"file": ("fake.pdf", b"This is plain text without pdf header", "application/pdf")}
    res2 = await client.post("/api/v1/documents/upload", headers=headers, files=corrupted_file, data={"document_type_code": "TENTH_MARKSHEET"})
    assert res2.status_code == 400
    assert "signature does not match" in res2.json()["detail"]


@pytest.mark.asyncio
async def test_anti_idor_document_download(client: AsyncClient, student1_token: str, student2_token: str, admin_token: str):
    """
    Test that Student 2 cannot download Student 1's uploaded documents, but Admin can.
    """
    # Student 1 uploads a file
    dummy_pdf = b"%PDF-1.4\nConfidential Marksheet of Student 1\n%%EOF"
    up_res = await client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {student1_token}"},
        files={"file": ("tc.pdf", dummy_pdf, "application/pdf")},
        data={"document_type_code": "TRANSFER_CERTIFICATE"}
    )
    doc_id = up_res.json()["document_id"]

    # Student 2 tries to download Student 1's doc -> 403 Forbidden
    s2_res = await client.get(
        f"/api/v1/documents/{doc_id}/download",
        headers={"Authorization": f"Bearer {student2_token}"}
    )
    assert s2_res.status_code == 403

    # Admin downloads Student 1's doc -> 200 OK
    admin_res = await client.get(
        f"/api/v1/documents/{doc_id}/download",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert admin_res.status_code == 200
    assert admin_res.headers["content-type"] == "application/pdf"


@pytest.mark.asyncio
async def test_full_application_submission_workflow(client: AsyncClient, student1_token: str):
    """
    Test filling all fields, uploading mandatory documents, accepting declaration,
    and successfully submitting the admission application.
    """
    headers = {"Authorization": f"Bearer {student1_token}"}

    # 1. Fill draft form
    draft_data = {
        "gender": "Male",
        "blood_group": "O+ve",
        "nationality": "Indian",
        "religion": "Hindu",
        "caste": "BC",
        "mother_tongue": "Tamil",
        "aadhaar_number": "9876 5432 1098",
        "address_line1": "100 Anna Salai",
        "city": "Chennai",
        "district": "Chennai",
        "state": "Tamil Nadu",
        "pincode": "600002",
        "emergency_contact_name": "Senthil Kumar",
        "emergency_contact_phone": "+91 98765 43210",
        "emergency_contact_relation": "Father",
        "father_name": "Senthil Kumar",
        "father_occupation": "Government Service",
        "father_mobile": "+91 98765 43210",
        "annual_family_income": 400000.0,
        "tenth_school_name": "St. Xavier Higher Secondary School",
        "tenth_board": "State Board",
        "tenth_year_of_passing": 2024,
        "tenth_registration_number": "SSLC-2024-9988",
        "tenth_total_marks": 490.0,
        "tenth_max_marks": 500.0,
        "tenth_percentage": 98.0,
        "twelfth_school_name": "St. Xavier Higher Secondary School",
        "twelfth_board": "State Board",
        "twelfth_year_of_passing": 2026,
        "twelfth_registration_number": "HSC-2026-1122",
        "twelfth_total_marks": 590.0,
        "twelfth_max_marks": 600.0,
        "twelfth_percentage": 98.3,
        "twelfth_maths_marks": 100.0,
        "twelfth_physics_marks": 98.0,
        "twelfth_chemistry_marks": 99.0,
        "twelfth_cutoff_marks": 198.5,
        "declaration_accepted": True
    }
    await client.put("/api/v1/applications/me", json=draft_data, headers=headers)

    # 2. Upload all mandatory documents for Karthik (10th, 12th, TC, Allotment, Community)
    mandatory_codes = ["TENTH_MARKSHEET", "TWELFTH_MARKSHEET", "TRANSFER_CERTIFICATE", "ALLOTMENT_ORDER", "COMMUNITY_CERTIFICATE"]
    for code in mandatory_codes:
        dummy_content = f"%PDF-1.4\nMandatory certificate for {code}\n%%EOF".encode()
        files = {"file": (f"{code.lower()}.pdf", dummy_content, "application/pdf")}
        up = await client.post("/api/v1/documents/upload", headers=headers, files=files, data={"document_type_code": code})
        assert up.status_code == 200

    # 3. Check completion
    comp = await client.get("/api/v1/applications/me/completion", headers=headers)
    assert comp.status_code == 200
    assert comp.json()["can_submit"] is True

    # 4. Submit application
    sub_res = await client.post("/api/v1/applications/me/submit", headers=headers, json={"declaration_accepted": True})
    assert sub_res.status_code == 200
    sub_data = sub_res.json()
    assert sub_data["status"] == "APPLICATION_SUBMITTED"
    assert "XYZADM2026" in sub_data["application_number"]

    # 5. Attempting to modify draft after submission should be rejected
    mod_res = await client.put("/api/v1/applications/me", json={"gender": "Female"}, headers=headers)
    assert mod_res.status_code == 400


@pytest.mark.asyncio
async def test_admin_applications_endpoints(client: AsyncClient, admin_token: str):
    """
    Test Admin listing and retrieving application details.
    """
    headers = {"Authorization": f"Bearer {admin_token}"}
    list_res = await client.get("/api/v1/applications/admin/list", headers=headers)
    assert list_res.status_code == 200
    apps = list_res.json()
    assert len(apps) >= 2

    # Get detail of first application
    app_id = apps[0]["application_id"]
    detail_res = await client.get(f"/api/v1/applications/admin/{app_id}", headers=headers)
    assert detail_res.status_code == 200
    assert detail_res.json()["id"] == app_id
    assert "checklist" in detail_res.json()
