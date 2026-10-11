import io
import os
import cv2
import numpy as np
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.document import Document, DocumentVersion
from app.models.document_processing import (
    DocumentProcessingJob,
    OCRResult,
    ProcessingStatus,
    ProcessingType,
)
from app.models.user import User
from app.services.ocr import (
    get_ocr_engine,
    BoundingBox,
    OCRBlock,
    OCRResultData,
    TesseractOCREngine,
    MockOCREngine,
    OCREngineUnavailableException,
)
from app.services.document_ocr_service import DocumentOCRService


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
async def test_ocr_engine_abstraction_and_bounding_box_contract():
    """
    1. Tests the coordinate origin contract (top-left 0,0) and normalized bounding box.
    2. Tests MockOCREngine produces expected structured OCRResultData.
    """
    box = BoundingBox(x=50, y=100, width=120, height=30)
    assert box.to_dict() == {"x": 50, "y": 100, "width": 120, "height": 30}

    block = OCRBlock(
        text="ENGINEERING",
        confidence=0.98,
        bounding_box=box,
        block_num=1,
        line_num=1,
        word_num=2,
    )
    b_dict = block.to_dict()
    assert b_dict["text"] == "ENGINEERING"
    assert b_dict["confidence"] == 0.98
    assert b_dict["bounding_box"] == {"x": 50, "y": 100, "width": 120, "height": 30}

    # Test MockOCREngine
    mock_engine = MockOCREngine()
    assert mock_engine.name == "mock"
    assert mock_engine.version == "1.0.0-mock"
    assert mock_engine.is_available() is True

    test_img = create_synthetic_test_image(["SAMPLE TEST TEXT"])
    res = mock_engine.extract(test_img, language="eng")

    assert isinstance(res, OCRResultData)
    assert len(res.blocks) > 0
    assert res.ocr_confidence is not None
    assert 0.0 <= res.ocr_confidence <= 1.0
    assert len(res.image_sha256) == 64
    assert res.language == "eng"


@pytest.mark.asyncio
async def test_tesseract_engine_availability_and_explicit_failure():
    """
    1. Tests TesseractOCREngine correctly reports availability without modifying system.
    2. If unavailable, extract() must raise OCREngineUnavailableException with setup instructions.
    3. Factory must never silently fall back from Tesseract to Mock.
    """
    tess_engine = TesseractOCREngine()
    assert tess_engine.name == "tesseract"

    # If tesseract binary is absent on host
    if not tess_engine.is_available():
        test_img = create_synthetic_test_image()
        with pytest.raises(OCREngineUnavailableException) as exc_info:
            tess_engine.extract(test_img)
        assert "Tesseract OCR engine binary is not installed" in str(exc_info.value)

    # Test factory behavior
    engine_tess = get_ocr_engine("tesseract")
    assert isinstance(engine_tess, TesseractOCREngine)

    engine_mock = get_ocr_engine("mock")
    assert isinstance(engine_mock, MockOCREngine)

    with pytest.raises(ValueError) as val_err:
        get_ocr_engine("invalid_engine_name")
    assert "Unsupported OCR engine" in str(val_err.value)


@pytest.mark.asyncio
async def test_preprocessing_dependency_enforcement(client: AsyncClient, student1_token: str):
    """
    Running OCR on a document that has not completed Phase 4B preprocessing
    must be rejected with HTTP 400: 'Document preprocessing is required before OCR.'
    """
    headers = {"Authorization": f"Bearer {student1_token}"}

    # Upload document
    img_bytes = create_synthetic_test_image(["HSC CERTIFICATE NO PREPROCESS"])
    files = {"file": ("hsc_test.png", io.BytesIO(img_bytes), "image/png")}
    data = {"document_type_code": "TWELFTH_MARKSHEET"}

    up_res = await client.post("/api/v1/documents/upload", headers=headers, files=files, data=data)
    assert up_res.status_code == 200, up_res.text
    doc_id = up_res.json()["document_id"]

    # Attempt OCR directly WITHOUT preprocessing
    ocr_res = await client.post(
        f"/api/v1/documents/{doc_id}/ocr",
        headers=headers,
        json={"language": "eng", "engine_name": "mock"}
    )
    assert ocr_res.status_code == 400
    assert "Document preprocessing is required before OCR" in ocr_res.json()["detail"]


@pytest.mark.asyncio
async def test_successful_ocr_lifecycle_and_api_flow(client: AsyncClient, student1_token: str, admin_token: str):
    """
    Full lifecycle:
    Upload -> Preprocess (OpenCV) -> Run OCR (MockOCREngine) -> Check results & Admin scrutiny
    """
    student_headers = {"Authorization": f"Bearer {student1_token}"}
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Upload document
    img_bytes = create_synthetic_test_image([
        "XYZ ENGINEERING COLLEGE",
        "NAME: KARTHIKEYAN S",
        "DATE OF BIRTH: 14/05/2008",
        "TOTAL MARKS: 560",
    ])
    files = {"file": ("hsc_karthik.png", io.BytesIO(img_bytes), "image/png")}
    data = {"document_type_code": "TWELFTH_MARKSHEET"}

    up_res = await client.post("/api/v1/documents/upload", headers=student_headers, files=files, data=data)
    assert up_res.status_code == 200, up_res.text
    doc_id = up_res.json()["document_id"]

    # 2. Run Preprocessing
    prep_res = await client.post(
        f"/api/v1/documents/{doc_id}/preprocess",
        headers=student_headers,
        json={"convert_grayscale": True, "deskew": True}
    )
    assert prep_res.status_code == 200
    assert prep_res.json()["status"] == "COMPLETED"

    # 3. Trigger OCR (using explicit mock engine for deterministic testing)
    ocr_res = await client.post(
        f"/api/v1/documents/{doc_id}/ocr",
        headers=student_headers,
        json={"engine_name": "mock", "language": "eng"}
    )
    assert ocr_res.status_code == 200, ocr_res.text
    job_data = ocr_res.json()
    assert job_data["processing_type"] == "OCR"
    assert job_data["status"] == "COMPLETED"
    assert job_data["engine_name"] == "mock"
    assert job_data["engine_version"] == "1.0.0-mock"

    # 4. Fetch OCR result via student endpoint
    get_res = await client.get(f"/api/v1/documents/{doc_id}/ocr", headers=student_headers)
    assert get_res.status_code == 200
    ocr_result = get_res.json()
    assert ocr_result is not None
    assert ocr_result["document_id"] == doc_id
    assert ocr_result["engine_name"] == "mock"
    assert ocr_result["language"] == "eng"
    assert ocr_result["ocr_confidence"] is not None
    assert len(ocr_result["image_sha256"]) == 64
    assert len(ocr_result["blocks"]) > 0
    assert "XYZ ENGINEERING COLLEGE" in ocr_result["full_text"]

    # 5. Admin Scrutiny endpoint
    admin_ocr_res = await client.get(f"/api/v1/admin/documents/{doc_id}/ocr", headers=admin_headers)
    assert admin_ocr_res.status_code == 200
    admin_ocr_data = admin_ocr_res.json()
    assert admin_ocr_data["document_id"] == doc_id
    assert admin_ocr_data["image_sha256"] == ocr_result["image_sha256"]
    assert len(admin_ocr_data["blocks"]) == len(ocr_result["blocks"])


@pytest.mark.asyncio
async def test_empty_ocr_result_vs_failure_distinction(client: AsyncClient, student1_token: str, test_db: AsyncSession):
    """
    Tests that an OCR run yielding empty readable text completes successfully
    (COMPLETED with full_text = '', blocks = []), NOT FAILED.
    """
    headers = {"Authorization": f"Bearer {student1_token}"}

    # Upload and preprocess
    img_bytes = create_synthetic_test_image(["EMPTY TEST"])
    files = {"file": ("comm_blank.png", io.BytesIO(img_bytes), "image/png")}
    data = {"document_type_code": "COMMUNITY_CERTIFICATE"}

    up_res = await client.post("/api/v1/documents/upload", headers=headers, files=files, data=data)
    doc_id = up_res.json()["document_id"]

    await client.post(f"/api/v1/documents/{doc_id}/preprocess", headers=headers)

    # Use mock engine configured with empty string text
    empty_engine = MockOCREngine(predefined_text="")
    
    user_stmt = select(User).where(User.email == "karthik.xyz2026001@demo.admissionai.local")
    user_res = await test_db.execute(user_stmt)
    user = user_res.scalar_one()

    job = await DocumentOCRService.process_document_ocr(
        db=test_db,
        document_id=doc_id,
        current_user=user,
        custom_engine=empty_engine,
    )

    assert job.status == ProcessingStatus.COMPLETED.value
    assert job.ocr_result is not None
    assert job.ocr_result.full_text == ""
    assert len(job.ocr_result.blocks) == 0


@pytest.mark.asyncio
async def test_document_version_integrity_for_ocr(client: AsyncClient, student1_token: str, test_db: AsyncSession):
    """
    Tests that OCR results for Document v1 and Document v2 remain distinct
    and linked to their respective DocumentVersion and PreprocessingResult records.
    """
    headers = {"Authorization": f"Bearer {student1_token}"}

    # 1. Upload Version 1
    img_v1 = create_synthetic_test_image(["VERSION 1 DOCUMENT"])
    files_v1 = {"file": ("tc_v1.png", io.BytesIO(img_v1), "image/png")}
    data = {"document_type_code": "TRANSFER_CERTIFICATE"}

    up_v1 = await client.post("/api/v1/documents/upload", headers=headers, files=files_v1, data=data)
    doc_id = up_v1.json()["document_id"]

    # Preprocess & OCR Version 1
    await client.post(f"/api/v1/documents/{doc_id}/preprocess", headers=headers)
    await client.post(
        f"/api/v1/documents/{doc_id}/ocr",
        headers=headers,
        json={"engine_name": "mock"}
    )

    # 2. Upload Version 2
    img_v2 = create_synthetic_test_image(["VERSION 2 DOCUMENT UPDATED"])
    files_v2 = {"file": ("tc_v2.png", io.BytesIO(img_v2), "image/png")}

    up_v2 = await client.post("/api/v1/documents/upload", headers=headers, files=files_v2, data=data)
    assert up_v2.json()["version_number"] == 2

    # Preprocess & OCR Version 2
    await client.post(f"/api/v1/documents/{doc_id}/preprocess", headers=headers)
    await client.post(
        f"/api/v1/documents/{doc_id}/ocr",
        headers=headers,
        json={"engine_name": "mock"}
    )

    # Query all OCR results for this document
    ocr_stmt = (
        select(OCRResult)
        .where(OCRResult.document_id == doc_id)
        .order_by(OCRResult.created_at.asc())
    )
    res = await test_db.execute(ocr_stmt)
    ocr_records = res.scalars().all()

    assert len(ocr_records) == 2
    assert ocr_records[0].document_version_id != ocr_records[1].document_version_id
    assert ocr_records[0].preprocessing_result_id != ocr_records[1].preprocessing_result_id


@pytest.mark.asyncio
async def test_anti_idor_and_rbac_ocr_security(client: AsyncClient, student1_token: str, student2_token: str):
    """
    1. Student A cannot OCR or view OCR results for Student B (Anti-IDOR).
    2. Unauthenticated requests are rejected (401).
    3. Students cannot access admin scrutiny OCR endpoints (403).
    """
    headers_s1 = {"Authorization": f"Bearer {student1_token}"}
    headers_s2 = {"Authorization": f"Bearer {student2_token}"}

    img_bytes = create_synthetic_test_image(["KARTHIK CONFIDENTIAL"])
    files = {"file": ("karthik_sec.png", io.BytesIO(img_bytes), "image/png")}
    data = {"document_type_code": "TWELFTH_MARKSHEET"}

    up_res = await client.post("/api/v1/documents/upload", headers=headers_s1, files=files, data=data)
    s1_doc_id = up_res.json()["document_id"]

    await client.post(f"/api/v1/documents/{s1_doc_id}/preprocess", headers=headers_s1)
    await client.post(f"/api/v1/documents/{s1_doc_id}/ocr", headers=headers_s1, json={"engine_name": "mock"})

    # Student 2 tries to run OCR on Student 1's document
    idor_post = await client.post(
        f"/api/v1/documents/{s1_doc_id}/ocr",
        headers=headers_s2,
        json={"engine_name": "mock"}
    )
    assert idor_post.status_code in [403, 404]

    # Student 2 tries to view OCR results of Student 1's document
    idor_get = await client.get(f"/api/v1/documents/{s1_doc_id}/ocr", headers=headers_s2)
    assert idor_get.status_code in [403, 404]

    # Unauthenticated request
    unauth_get = await client.get(f"/api/v1/documents/{s1_doc_id}/ocr")
    assert unauth_get.status_code == 401

    # Student 2 tries to access admin OCR endpoint
    admin_rbac_get = await client.get(f"/api/v1/admin/documents/{s1_doc_id}/ocr", headers=headers_s2)
    assert admin_rbac_get.status_code == 403


@pytest.mark.asyncio
async def test_ocr_does_not_alter_verification_status(client: AsyncClient, student1_token: str, test_db: AsyncSession):
    """
    Verifies that executing OCR does NOT alter document verification_status
    or admission status (remains PENDING).
    """
    headers = {"Authorization": f"Bearer {student1_token}"}

    img_bytes = create_synthetic_test_image(["TEST VERIF PRESERVATION"])
    files = {"file": ("allot_verif.png", io.BytesIO(img_bytes), "image/png")}
    data = {"document_type_code": "ALLOTMENT_ORDER"}

    up_res = await client.post("/api/v1/documents/upload", headers=headers, files=files, data=data)
    doc_id = up_res.json()["document_id"]

    # Preprocess & OCR
    await client.post(f"/api/v1/documents/{doc_id}/preprocess", headers=headers)
    await client.post(f"/api/v1/documents/{doc_id}/ocr", headers=headers, json={"engine_name": "mock"})

    # Check document in database
    doc_stmt = select(Document).where(Document.id == doc_id)
    doc_res = await test_db.execute(doc_stmt)
    doc = doc_res.scalar_one()

    # Must remain UPLOADED (not auto-verified or approved by AI)
    assert doc.status == "UPLOADED"


@pytest.mark.asyncio
async def test_optional_real_tesseract_integration():
    """
    Optional test: runs real Tesseract OCR on a synthetic image if Tesseract binary is available.
    Skips dynamically if Tesseract binary is missing from the host.
    """
    tess = TesseractOCREngine()
    if not tess.is_available():
        pytest.skip("Tesseract binary not installed on host - skipped as per design")

    synthetic_img = create_synthetic_test_image(["XYZ ENGINEERING COLLEGE ADMISSION"])
    res = tess.extract(synthetic_img, language="eng")

    assert res.engine_name == "tesseract"
    assert "XYZ" in res.full_text.upper() or "COLLEGE" in res.full_text.upper()
    assert len(res.blocks) > 0
    assert len(res.image_sha256) == 64
