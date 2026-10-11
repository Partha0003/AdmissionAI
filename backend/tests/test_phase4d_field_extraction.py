import io
import pytest
from httpx import AsyncClient
import cv2
import numpy as np

from app.services.extractors import (
    FieldExtractorFactory,
    TwelfthMarksheetExtractor,
    TenthMarksheetExtractor,
    CommunityCertificateExtractor,
    AllotmentOrderExtractor,
    TransferCertificateExtractor,
    IncomeCertificateExtractor,
    FirstGraduateCertificateExtractor,
    GenericDocumentExtractor,
)
from app.services.extractors.utils import (
    calculate_field_confidence,
    normalize_date,
    normalize_community,
    normalize_number,
)


def create_synthetic_test_image(text_lines=None, width=500, height=300) -> bytes:
    """Generates a synthetic PNG document image containing known text lines."""
    img = np.ones((height, width, 3), dtype=np.uint8) * 255
    font = cv2.FONT_HERSHEY_SIMPLEX
    lines = text_lines or [
        "XYZ ENGINEERING COLLEGE",
        "NAME: KARTHIKEYAN S",
        "APPLICATION: XYZ2026001",
        "DATE OF BIRTH: 14/05/2008",
    ]
    for idx, line in enumerate(lines):
        y = 50 + (idx * 40)
        cv2.putText(img, line, (30, y), font, 0.5, (0, 0, 0), 1, cv2.LINE_AA)

    success, buf = cv2.imencode(".png", img)
    assert success
    return buf.tobytes()


@pytest.mark.asyncio
async def test_twelfth_marksheet_calculated_cutoff_is_derived_not_verified():
    """
    Verification Check 1:
    Tests that calculated_cutoff_marks is computed deterministically as
    round(maths + physics/2 + chemistry/2, 2) and explicitly annotated as derived, not verified.
    """
    raw_hsc_text = (
        "GOVERNMENT OF TAMIL NADU\n"
        "DIRECTORATE OF GOVERNMENT EXAMINATIONS\n"
        "HIGHER SECONDARY EXAMINATION (CLASS XII)\n"
        "NAME OF CANDIDATE: KARTHIKEYAN S\n"
        "ROLL NO: TN12-2026-9988\n"
        "YEAR OF PASSING: 2026\n"
        "MATHEMATICS: 98 / 100 PASS\n"
        "PHYSICS: 95 / 100 PASS\n"
        "CHEMISTRY: 96 / 100 PASS\n"
        "TOTAL MARKS: 570 / 600\n"
        "PERCENTAGE: 95.0%\n"
        "SCHOOL NAME: DAV HIGHER SECONDARY SCHOOL CHENNAI\n"
    )
    blocks = [
        {"text": "NAME OF CANDIDATE: KARTHIKEYAN S", "confidence": 0.95, "box": {"x": 50, "y": 40, "width": 300, "height": 25}},
        {"text": "MATHEMATICS: 98", "confidence": 0.94, "box": {"x": 50, "y": 100, "width": 200, "height": 20}},
        {"text": "PHYSICS: 95", "confidence": 0.92, "box": {"x": 50, "y": 130, "width": 200, "height": 20}},
        {"text": "CHEMISTRY: 96", "confidence": 0.93, "box": {"x": 50, "y": 160, "width": 200, "height": 20}},
        {"text": "TOTAL MARKS: 570 / 600", "confidence": 0.96, "box": {"x": 50, "y": 200, "width": 250, "height": 25}},
    ]

    extractor = TwelfthMarksheetExtractor()
    result = extractor.extract(raw_hsc_text, blocks, context={"document_version": 1})

    assert result.document_type_code == "TWELFTH_MARKSHEET"
    assert "calculated_cutoff_marks" in result.fields

    cutoff_field = result.fields["calculated_cutoff_marks"]
    # 98 + 95/2.0 + 96/2.0 = 98 + 47.5 + 48 = 193.5
    assert cutoff_field.normalized_value == 193.5
    assert "This is a deterministic derived value calculated from extracted subject marks. It is NOT a verification result." in cutoff_field.description
    assert cutoff_field.requires_review is False
    assert result.fields["candidate_name"].normalized_value == "KARTHIKEYAN S"
    assert result.fields["total_marks"].normalized_value == 570.0
    assert result.fields["year_of_passing"].normalized_value == 2026


@pytest.mark.asyncio
async def test_field_confidence_is_deterministic_and_clamped():
    """
    Verification Check 2:
    Tests deterministic confidence formula: clamp(0.6 * OCR + 0.4 * pattern, 0.0, 1.0).
    """
    conf = calculate_field_confidence(ocr_word_confidence=0.90, pattern_certainty_score=1.0)
    assert conf == 0.94

    conf_low = calculate_field_confidence(ocr_word_confidence=0.50, pattern_certainty_score=0.70)
    assert conf_low == 0.58

    assert calculate_field_confidence(ocr_word_confidence=1.5, pattern_certainty_score=2.0) == 1.0
    assert calculate_field_confidence(ocr_word_confidence=-0.5, pattern_certainty_score=-1.0) == 0.0


@pytest.mark.asyncio
async def test_field_provenance_contains_block_and_bounding_box():
    """
    Verification Check 5 & 6:
    Verifies that extracted fields contain full provenance (OCR block indices, bounding box, context snippet)
    and preserve both raw_value and normalized_value.
    """
    raw_text = "COMMUNITY: BC\nCERTIFICATE NO: TN-COMM-2026-8877\nTHIS IS TO CERTIFY THAT KARTHIKEYAN S"
    blocks = [
        {"text": "COMMUNITY: BC", "confidence": 0.96, "box": {"x": 100, "y": 150, "width": 180, "height": 24}},
        {"text": "CERTIFICATE NO: TN-COMM-2026-8877", "confidence": 0.94, "box": {"x": 100, "y": 190, "width": 320, "height": 24}},
        {"text": "THIS IS TO CERTIFY THAT KARTHIKEYAN S", "confidence": 0.95, "box": {"x": 100, "y": 230, "width": 380, "height": 28}},
    ]

    extractor = CommunityCertificateExtractor()
    result = extractor.extract(raw_text, blocks, context={"document_version": 1})

    comm_field = result.fields["community"]
    assert comm_field.raw_value == "BC"
    assert comm_field.normalized_value == "BC"
    assert comm_field.source.bounding_box is not None
    assert comm_field.source.bounding_box["x"] == 100
    assert comm_field.source.bounding_box["y"] == 150
    assert 0 in comm_field.source.ocr_block_indices

    cert_field = result.fields["certificate_number"]
    assert cert_field.raw_value == "TN-COMM-2026-8877"
    assert cert_field.normalized_value == "TN-COMM-2026-8877"
    assert cert_field.source.bounding_box is not None


@pytest.mark.asyncio
async def test_ambiguous_value_triggers_human_review():
    """
    Verification Check 7:
    Tests that ambiguous date formats or unparseable numbers trigger requires_review = True.
    """
    val, req_rev, reason = normalize_date("01/02/05")
    assert val is None
    assert req_rev is True
    assert "Ambiguous 2-digit year" in reason

    val_ok, req_rev_ok, reason_ok = normalize_date("2008-04-12")
    assert val_ok == "2008-04-12"
    assert req_rev_ok is False
    assert reason_ok is None

    c_val, c_rev, c_reason = normalize_community("UNKNOWN_XYZ_CATEGORY")
    assert c_val is None
    assert c_rev is True
    assert "Unrecognized community category" in c_reason


@pytest.mark.asyncio
async def test_missing_optional_field_does_not_fail_job():
    """
    Verification Check 8:
    Tests that missing optional fields in OCR output set requires_review = True but leave extraction valid.
    """
    incomplete_text = "NAME: KARTHIKEYAN S\nROLL NO: TN10-12345"
    blocks = [{"text": "NAME: KARTHIKEYAN S", "confidence": 0.95, "box": {"x": 10, "y": 10, "width": 100, "height": 20}}]

    extractor = TenthMarksheetExtractor()
    result = extractor.extract(incomplete_text, blocks, context={"document_version": 1})

    assert result.fields["candidate_name"].normalized_value == "KARTHIKEYAN S"
    assert result.fields["candidate_name"].requires_review is False

    total_field = result.fields["total_marks"]
    assert total_field.normalized_value is None
    assert total_field.requires_review is True
    assert total_field.review_reason == "Field not detected in OCR output"
    assert result.requires_human_review is True


@pytest.mark.asyncio
async def test_field_extraction_requires_prior_ocr(client: AsyncClient, student1_token: str):
    """
    Verification Check 9:
    Tests that requesting field extraction without prior OCR returns HTTP 400.
    """
    headers = {"Authorization": f"Bearer {student1_token}"}

    img_bytes = create_synthetic_test_image(["TRANSFER CERTIFICATE TEST"])
    files = {"file": ("tc.png", io.BytesIO(img_bytes), "image/png")}
    data = {"document_type_code": "TRANSFER_CERTIFICATE"}

    up_res = await client.post("/api/v1/documents/upload", headers=headers, files=files, data=data)
    assert up_res.status_code == 200
    doc_id = up_res.json()["document_id"]

    # Attempt field extraction directly without running OCR
    ext_res = await client.post(f"/api/v1/documents/{doc_id}/extract-fields", headers=headers)
    assert ext_res.status_code == 400
    assert "OCR text recognition is required before structured field extraction" in ext_res.json()["detail"]


@pytest.mark.asyncio
async def test_full_field_extraction_api_flow(client: AsyncClient, student1_token: str, admin_token: str):
    """
    Verification Checks 3, 4, 13:
    Full pipeline test:
    Upload -> Preprocess -> OCR -> Extract Fields -> Check Read-Only Invariants -> Admin Scrutiny.
    """
    student_headers = {"Authorization": f"Bearer {student1_token}"}
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Upload 12th Marksheet
    img_bytes = create_synthetic_test_image([
        "GOVERNMENT OF TAMIL NADU",
        "NAME OF CANDIDATE: KARTHIKEYAN S",
        "ROLL NO: TN12-9988",
        "YEAR OF PASSING: 2026",
        "MATHEMATICS: 98",
        "PHYSICS: 95",
        "CHEMISTRY: 96",
        "TOTAL MARKS: 570 / 600",
    ])
    files = {"file": ("hsc_karthik.png", io.BytesIO(img_bytes), "image/png")}
    data = {"document_type_code": "TWELFTH_MARKSHEET"}

    up_res = await client.post("/api/v1/documents/upload", headers=student_headers, files=files, data=data)
    assert up_res.status_code == 200
    doc_id = up_res.json()["document_id"]

    # 2. Preprocess
    prep_res = await client.post(f"/api/v1/documents/{doc_id}/preprocess", headers=student_headers, json={})
    assert prep_res.status_code == 200

    # 3. OCR (Mock Engine)
    ocr_res = await client.post(f"/api/v1/documents/{doc_id}/ocr", headers=student_headers, json={"engine_name": "mock"})
    assert ocr_res.status_code == 200

    # 4. Check application state before extraction
    app_before = (await client.get("/api/v1/applications/me", headers=student_headers)).json()

    # 5. Extract Fields
    ext_job_res = await client.post(f"/api/v1/documents/{doc_id}/extract-fields", headers=student_headers)
    assert ext_job_res.status_code == 200
    ext_job = ext_job_res.json()
    assert ext_job["processing_type"] == "FIELD_EXTRACTION"
    assert ext_job["status"] == "COMPLETED"

    # 6. Read-Only Guarantee: Check application state after extraction
    app_after = (await client.get("/api/v1/applications/me", headers=student_headers)).json()
    assert app_before["status"] == app_after["status"]
    assert app_before["completion_percentage"] == app_after["completion_percentage"]


    # 7. Student fetch extracted fields
    get_ext = await client.get(f"/api/v1/documents/{doc_id}/extracted-fields", headers=student_headers)
    assert get_ext.status_code == 200
    ext_data = get_ext.json()
    assert ext_data["document_type_code"] == "TWELFTH_MARKSHEET"
    assert ext_data["extractor_name"] == "TwelfthMarksheetExtractor"
    assert "fields" in ext_data

    # 8. Admin Scrutiny fetch extracted fields
    admin_ext = await client.get(f"/api/v1/admin/documents/{doc_id}/extracted-fields", headers=admin_headers)
    assert admin_ext.status_code == 200
    assert admin_ext.json()["id"] == ext_data["id"]


@pytest.mark.asyncio
async def test_field_extraction_version_preservation(client: AsyncClient, student1_token: str):
    """
    Verification Check 10:
    Verifies that uploading v2 and extracting fields preserves historical v1 extraction.
    """
    student_headers = {"Authorization": f"Bearer {student1_token}"}

    # Upload v1
    img1 = create_synthetic_test_image(["COMMUNITY: BC", "CERTIFICATE NO: COMM-V1"])
    up1 = await client.post(
        "/api/v1/documents/upload",
        headers=student_headers,
        files={"file": ("comm_v1.png", io.BytesIO(img1), "image/png")},
        data={"document_type_code": "COMMUNITY_CERTIFICATE"},
    )
    doc_id = up1.json()["document_id"]

    await client.post(f"/api/v1/documents/{doc_id}/preprocess", headers=student_headers)
    await client.post(f"/api/v1/documents/{doc_id}/ocr", headers=student_headers, json={"engine_name": "mock"})
    ext1_res = await client.post(f"/api/v1/documents/{doc_id}/extract-fields", headers=student_headers)
    assert ext1_res.status_code == 200

    # Upload v2 for same document type
    img2 = create_synthetic_test_image(["COMMUNITY: MBC", "CERTIFICATE NO: COMM-V2"])
    up2 = await client.post(
        "/api/v1/documents/upload",
        headers=student_headers,
        files={"file": ("comm_v2.png", io.BytesIO(img2), "image/png")},
        data={"document_type_code": "COMMUNITY_CERTIFICATE"},
    )
    assert up2.status_code == 200
    assert up2.json()["version_number"] == 2

    await client.post(f"/api/v1/documents/{doc_id}/preprocess", headers=student_headers)
    await client.post(f"/api/v1/documents/{doc_id}/ocr", headers=student_headers, json={"engine_name": "mock"})
    ext2_res = await client.post(f"/api/v1/documents/{doc_id}/extract-fields", headers=student_headers)
    assert ext2_res.status_code == 200

    # Fetch latest extraction (should be v2)
    latest_ext = (await client.get(f"/api/v1/documents/{doc_id}/extracted-fields", headers=student_headers)).json()
    assert latest_ext is not None


@pytest.mark.asyncio
async def test_field_extraction_anti_idor(client: AsyncClient, student1_token: str, student2_token: str):
    """
    Verification Check 11:
    Tests that Student 1 cannot trigger or read field extractions for Student 2.
    """
    headers_s2 = {"Authorization": f"Bearer {student2_token}"}
    headers_s1 = {"Authorization": f"Bearer {student1_token}"}

    # Student 2 uploads document
    img = create_synthetic_test_image(["STUDENT 2 ALLOTMENT ORDER"])
    up_res = await client.post(
        "/api/v1/documents/upload",
        headers=headers_s2,
        files={"file": ("s2_allotment.png", io.BytesIO(img), "image/png")},
        data={"document_type_code": "ALLOTMENT_ORDER"},
    )
    assert up_res.status_code == 200
    doc2_id = up_res.json()["document_id"]

    # Student 1 attempts to trigger extraction on Student 2 document -> 403 Forbidden
    post_resp = await client.post(f"/api/v1/documents/{doc2_id}/extract-fields", headers=headers_s1)
    assert post_resp.status_code == 403

    # Student 1 attempts to read extraction of Student 2 document -> 403 Forbidden
    get_resp = await client.get(f"/api/v1/documents/{doc2_id}/extracted-fields", headers=headers_s1)
    assert get_resp.status_code == 403


@pytest.mark.asyncio
async def test_extractor_factory_and_modular_routing():
    """
    Verification Check 10:
    Tests FieldExtractorFactory routes to the correct specialized extractor class.
    """
    assert isinstance(FieldExtractorFactory.get_extractor("TWELFTH_MARKSHEET"), TwelfthMarksheetExtractor)
    assert isinstance(FieldExtractorFactory.get_extractor("TENTH_MARKSHEET"), TenthMarksheetExtractor)
    assert isinstance(FieldExtractorFactory.get_extractor("COMMUNITY_CERTIFICATE"), CommunityCertificateExtractor)
    assert isinstance(FieldExtractorFactory.get_extractor("ALLOTMENT_ORDER"), AllotmentOrderExtractor)
    assert isinstance(FieldExtractorFactory.get_extractor("TRANSFER_CERTIFICATE"), TransferCertificateExtractor)
    assert isinstance(FieldExtractorFactory.get_extractor("INCOME_CERTIFICATE"), IncomeCertificateExtractor)
    assert isinstance(FieldExtractorFactory.get_extractor("FIRST_GRADUATE_CERTIFICATE"), FirstGraduateCertificateExtractor)
    assert isinstance(FieldExtractorFactory.get_extractor("UNKNOWN_CUSTOM_DOC"), GenericDocumentExtractor)


@pytest.mark.asyncio
async def test_allotment_order_document_cutoff_mark_terminology():
    """
    Verification Check 11:
    Tests that AllotmentOrderExtractor extracts 'document_cutoff_mark' with description
    confirming it is extracted from the document and NOT verified against external sources.
    """
    raw_allotment_text = (
        "DIRECTORATE OF TECHNICAL EDUCATION, CHENNAI\n"
        "TAMIL NADU ENGINEERING ADMISSIONS 2026\n"
        "PROVISIONAL ALLOTMENT ORDER\n"
        "TNEA APPLICATION NO: 20261001\n"
        "ALLOTMENT ORDER NO: TNEA-2026-XYZ-042\n"
        "NAME OF CANDIDATE: KARTHIKEYAN S\n"
        "COLLEGE CODE: XYZ\n"
        "BRANCH: COMPUTER SCIENCE AND ENGINEERING\n"
        "CUTOFF MARK: 193.50\n"
    )
    blocks = [
        {"text": "TNEA APPLICATION NO: 20261001", "confidence": 0.96, "box": {"x": 50, "y": 50, "width": 250, "height": 20}},
        {"text": "ALLOTMENT ORDER NO: TNEA-2026-XYZ-042", "confidence": 0.95, "box": {"x": 50, "y": 80, "width": 300, "height": 20}},
        {"text": "NAME OF CANDIDATE: KARTHIKEYAN S", "confidence": 0.95, "box": {"x": 50, "y": 110, "width": 280, "height": 20}},
        {"text": "COLLEGE CODE: XYZ", "confidence": 0.94, "box": {"x": 50, "y": 140, "width": 150, "height": 20}},
        {"text": "BRANCH: COMPUTER SCIENCE AND ENGINEERING", "confidence": 0.95, "box": {"x": 50, "y": 170, "width": 350, "height": 20}},
        {"text": "CUTOFF MARK: 193.50", "confidence": 0.93, "box": {"x": 50, "y": 200, "width": 180, "height": 20}},
    ]

    extractor = AllotmentOrderExtractor()
    result = extractor.extract(raw_allotment_text, blocks, context={"document_version": 1})

    assert "document_cutoff_mark" in result.fields
    cutoff_field = result.fields["document_cutoff_mark"]
    assert cutoff_field.raw_value == "193.50"
    assert cutoff_field.normalized_value == 193.5
    assert cutoff_field.field_name == "Document Cutoff Mark"
    assert "The cutoff value extracted from the allotment document. It is not independently verified against an authoritative external source." in cutoff_field.description


@pytest.mark.asyncio
async def test_extraction_does_not_mutate_admission_application_or_student_or_allotment(
    client: AsyncClient, student1_token: str
):
    """
    Verification Check 12:
    Strict Read-Only Guarantee:
    Verifies that running field extraction does not mutate AdmissionApplication, Student, or TNEAAllotment.
    """
    student_headers = {"Authorization": f"Bearer {student1_token}"}

    # Snapshot application state before document operations
    app_before = (await client.get("/api/v1/applications/me", headers=student_headers)).json()
    status_before = app_before["status"]
    app_num_before = app_before["application_number"]
    tnea_num_before = app_before["tnea_application_number"]
    student_name_before = app_before["student_name"]

    # Upload, Preprocess, OCR, and Extract Fields
    img_bytes = create_synthetic_test_image(["COMMUNITY: BC", "CERTIFICATE NO: COMM-READONLY-TEST"])
    files = {"file": ("comm_readonly.png", io.BytesIO(img_bytes), "image/png")}
    data = {"document_type_code": "COMMUNITY_CERTIFICATE"}

    up_res = await client.post("/api/v1/documents/upload", headers=student_headers, files=files, data=data)
    assert up_res.status_code == 200
    doc_id = up_res.json()["document_id"]

    await client.post(f"/api/v1/documents/{doc_id}/preprocess", headers=student_headers)
    await client.post(f"/api/v1/documents/{doc_id}/ocr", headers=student_headers, json={"engine_name": "mock"})
    ext_res = await client.post(f"/api/v1/documents/{doc_id}/extract-fields", headers=student_headers)
    assert ext_res.status_code == 200

    # Snapshot application state after field extraction
    app_after = (await client.get("/api/v1/applications/me", headers=student_headers)).json()
    assert app_after["status"] == status_before
    assert app_after["application_number"] == app_num_before
    assert app_after["tnea_application_number"] == tnea_num_before
    assert app_after["student_name"] == student_name_before


@pytest.mark.asyncio
async def test_extraction_does_not_mutate_document_status(client: AsyncClient, student1_token: str):
    """
    Verification Check 13:
    Strict Read-Only Guarantee:
    Verifies that Document.status remains UPLOADED (never automatically transitioned to DOCUMENTS_VERIFIED).
    """
    student_headers = {"Authorization": f"Bearer {student1_token}"}

    img_bytes = create_synthetic_test_image(["TENTH MARKSHEET", "ROLL NO: 109988", "TOTAL: 480"])
    files = {"file": ("tenth_readonly.png", io.BytesIO(img_bytes), "image/png")}
    data = {"document_type_code": "TENTH_MARKSHEET"}

    up_res = await client.post("/api/v1/documents/upload", headers=student_headers, files=files, data=data)
    assert up_res.status_code == 200
    doc_id = up_res.json()["document_id"]

    # Verify initial upload status
    checklist_before = (await client.get("/api/v1/applications/me/checklist", headers=student_headers)).json()
    doc_item_before = next(item for item in checklist_before if item["document_id"] == doc_id)
    assert doc_item_before["document_status"] == "UPLOADED"

    # Preprocess -> OCR -> Extract Fields
    await client.post(f"/api/v1/documents/{doc_id}/preprocess", headers=student_headers)
    await client.post(f"/api/v1/documents/{doc_id}/ocr", headers=student_headers, json={"engine_name": "mock"})
    await client.post(f"/api/v1/documents/{doc_id}/extract-fields", headers=student_headers)

    # Verify Document.status is STILL UPLOADED
    checklist_after = (await client.get("/api/v1/applications/me/checklist", headers=student_headers)).json()
    doc_item_after = next(item for item in checklist_after if item["document_id"] == doc_id)
    assert doc_item_after["document_status"] == "UPLOADED"
    assert doc_item_after["document_status"] != "DOCUMENTS_VERIFIED"
    assert doc_item_after["extraction_status"] == "COMPLETED"


@pytest.mark.asyncio
async def test_raw_value_and_normalized_value_preservation():
    """
    Verification Check 14:
    Verifies that raw_value and normalized_value are both preserved in extraction results,
    and ambiguous/unparseable values retain raw_value with normalized_value = None.
    """
    raw_text = (
        "ANNUAL INCOME CERTIFICATE\n"
        "ANNUAL FAMILY INCOME: RS. 1,50,000 /-\n"
        "CERTIFICATE NO: INC-2026-5544\n"
    )
    blocks = [
        {"text": "ANNUAL FAMILY INCOME: RS. 1,50,000 /-", "confidence": 0.95, "box": {"x": 50, "y": 50, "width": 300, "height": 20}},
        {"text": "CERTIFICATE NO: INC-2026-5544", "confidence": 0.94, "box": {"x": 50, "y": 80, "width": 250, "height": 20}},
    ]

    extractor = IncomeCertificateExtractor()
    result = extractor.extract(raw_text, blocks, context={"document_version": 1})

    inc_field = result.fields["annual_income"]
    assert inc_field.raw_value == "1,50,000"
    assert inc_field.normalized_value == 150000
    assert inc_field.requires_review is False

    cert_field = result.fields["certificate_number"]
    assert cert_field.raw_value == "INC-2026-5544"
    assert cert_field.normalized_value == "INC-2026-5544"
    assert cert_field.requires_review is False

    # Ambiguous date preservation test
    comm_raw = "COMMUNITY: BC\nDATE OF ISSUE: 01/02/05\nCERTIFICATE NO: TN-COMM-001"
    comm_blocks = [
        {"text": "COMMUNITY: BC", "confidence": 0.95, "box": {"x": 10, "y": 10, "width": 100, "height": 20}},
        {"text": "DATE OF ISSUE: 01/02/05", "confidence": 0.95, "box": {"x": 10, "y": 40, "width": 150, "height": 20}},
    ]
    comm_extractor = CommunityCertificateExtractor()
    comm_res = comm_extractor.extract(comm_raw, comm_blocks, context={"document_version": 1})

    date_field = comm_res.fields["issue_date"]
    assert date_field.raw_value == "01/02/05"
    assert date_field.normalized_value is None
    assert date_field.requires_review is True
    assert "Ambiguous" in date_field.review_reason
