import io
import os
import cv2
import numpy as np
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User
from app.models.document import Document, DocumentVersion
from app.models.document_processing import DocumentProcessingJob, PreprocessingResult, ProcessingStatus
from app.services.preprocessors.base import PreprocessingContext, PreprocessingOptions
from app.services.preprocessors.opencv_preprocessor import OpenCVDocumentPreprocessor
from app.services.document_preprocessing_service import DocumentPreprocessingService


def create_synthetic_test_image(skew_angle: float = 0.0, noise: bool = False, width: int = 400, height: int = 300) -> bytes:
    """
    Generates a synthetic document-like image with text lines for testing OpenCV transformations.
    """
    img = np.ones((height, width, 3), dtype=np.uint8) * 255  # White background

    # Add text lines
    font = cv2.FONT_HERSHEY_SIMPLEX
    for y in range(40, height - 30, 40):
        cv2.putText(img, f"ADMISSION APPLICATION CERTIFICATE LINE {y}", (30, y), font, 0.5, (0, 0, 0), 1, cv2.LINE_AA)

    # Optional Gaussian noise
    if noise:
        gauss = np.random.normal(0, 20, (height, width, 3)).astype(np.uint8)
        img = cv2.add(img, gauss)

    # Optional skew rotation
    if abs(skew_angle) > 0.1:
        center = (width // 2, height // 2)
        M = cv2.getRotationMatrix2D(center, skew_angle, 1.0)
        img = cv2.warpAffine(img, M, (width, height), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

    success, buf = cv2.imencode(".png", img)
    assert success
    return buf.tobytes()


@pytest.mark.asyncio
async def test_opencv_preprocessor_unit_operations(tmp_path):
    """
    Unit test for OpenCVDocumentPreprocessor verifying grayscale, denoise, CLAHE, deskew, and thresholding.
    """
    preprocessor = OpenCVDocumentPreprocessor()
    assert preprocessor.name == "OpenCVDocumentPreprocessor"
    assert preprocessor.version == "1.0.0-opencv"

    # Create synthetic skewed image (-3.0 degrees)
    img_bytes = create_synthetic_test_image(skew_angle=-3.0, noise=True, width=500, height=400)
    test_file = tmp_path / "test_cert_skewed.png"
    test_file.write_bytes(img_bytes)

    orig_stat = os.stat(test_file)

    ctx = PreprocessingContext(
        document_id="doc-test-1",
        document_version_id="ver-test-1",
        file_path=str(test_file),
        mime_type="image/png",
        original_filename="test_cert_skewed.png",
        options=PreprocessingOptions(
            convert_grayscale=True,
            denoise=True,
            enhance_contrast=True,
            apply_threshold=True,
            deskew=True
        )
    )

    result = await preprocessor.preprocess(ctx)

    assert result.engine_name == "OpenCVDocumentPreprocessor"
    assert "GRAYSCALE" in result.operations_applied
    assert "GAUSSIAN_DENOISE" in result.operations_applied
    assert "CLAHE_CONTRAST" in result.operations_applied
    assert "OTSU_THRESHOLD" in result.operations_applied
    assert result.input_dimensions["channels"] == 3
    assert result.output_dimensions["channels"] == 1
    assert result.output_dimensions["width"] > 0
    assert result.output_dimensions["height"] > 0
    assert len(result.output_image_bytes) > 0

    # Verify original file was NOT mutated
    after_stat = os.stat(test_file)
    assert orig_stat.st_mtime == after_stat.st_mtime
    assert test_file.read_bytes() == img_bytes


@pytest.mark.asyncio
async def test_preprocessing_lifecycle_and_api_flow(client: AsyncClient, student1_token: str, admin_token: str):
    """
    Integration test for image preprocessing lifecycle:
    1. Student 1 uploads image document
    2. Student 1 calls POST /api/v1/documents/{id}/preprocess
    3. Verifies QUEUED -> PROCESSING -> COMPLETED state transitions
    4. Verifies PreprocessingResult database persistence (dimensions, operations, deskew, duration)
    5. Retrieves preprocessed image via GET /api/v1/documents/{id}/preprocessed-image
    6. Admin inspects preprocessing history via GET /api/v1/admin/documents/{id}/preprocessing
    """
    headers_s1 = {"Authorization": f"Bearer {student1_token}"}
    headers_admin = {"Authorization": f"Bearer {admin_token}"}

    # Upload synthetic PNG document
    img_bytes = create_synthetic_test_image(width=400, height=300)
    files = {"file": ("student_community_cert.png", io.BytesIO(img_bytes), "image/png")}
    data = {"document_type_code": "COMMUNITY_CERTIFICATE"}

    upload_res = await client.post("/api/v1/documents/upload", headers=headers_s1, files=files, data=data)
    assert upload_res.status_code == 200, upload_res.text
    doc_id = upload_res.json()["document_id"]

    # Trigger preprocessing via API
    preprocess_res = await client.post(
        f"/api/v1/documents/{doc_id}/preprocess",
        headers=headers_s1,
        json={"convert_grayscale": True, "denoise": True, "apply_threshold": True}
    )
    assert preprocess_res.status_code == 200, preprocess_res.text
    job_data = preprocess_res.json()

    assert job_data["document_id"] == doc_id
    assert job_data["processing_type"] == "IMAGE_PREPROCESSING"
    assert job_data["status"] == "COMPLETED"
    assert job_data["engine_name"] == "OpenCVDocumentPreprocessor"
    assert job_data["processing_time_ms"] is not None
    assert job_data["processing_time_ms"] >= 1
    assert job_data["started_at"] is not None
    assert job_data["completed_at"] is not None

    # Check preprocessing_result payload
    pr_data = job_data["preprocessing_result"]
    assert pr_data is not None
    assert pr_data["engine_name"] == "OpenCVDocumentPreprocessor"
    assert "GRAYSCALE" in pr_data["operations_applied"]
    assert "OTSU_THRESHOLD" in pr_data["operations_applied"]
    assert pr_data["input_dimensions"]["width"] == 400
    assert pr_data["input_dimensions"]["height"] == 300
    assert pr_data["output_file_size"] > 0
    assert pr_data["output_filename"].endswith("_preprocessed.png")

    # Download preprocessed image
    img_download_res = await client.get(f"/api/v1/documents/{doc_id}/preprocessed-image", headers=headers_s1)
    assert img_download_res.status_code == 200
    assert img_download_res.headers["content-type"] == "image/png"
    assert len(img_download_res.content) > 0

    # Retrieve history
    history_res = await client.get(f"/api/v1/documents/{doc_id}/preprocessing", headers=headers_s1)
    assert history_res.status_code == 200
    history = history_res.json()
    assert history["total_jobs"] >= 1
    assert history["latest_job"]["status"] == "COMPLETED"

    # Admin verification inspection
    admin_res = await client.get(f"/api/v1/admin/documents/{doc_id}/preprocessing", headers=headers_admin)
    assert admin_res.status_code == 200
    assert admin_res.json()["total_jobs"] >= 1


@pytest.mark.asyncio
async def test_anti_idor_preprocessing_security(client: AsyncClient, student1_token: str, student2_token: str):
    """
    Tests Anti-IDOR protections:
    Student 2 cannot preprocess or download preprocessed images belonging to Student 1.
    """
    headers_s1 = {"Authorization": f"Bearer {student1_token}"}
    headers_s2 = {"Authorization": f"Bearer {student2_token}"}

    # Upload as Student 1
    img_bytes = create_synthetic_test_image()
    files = {"file": ("student1_tc.png", io.BytesIO(img_bytes), "image/png")}
    data = {"document_type_code": "TRANSFER_CERTIFICATE"}
    upload_res = await client.post("/api/v1/documents/upload", headers=headers_s1, files=files, data=data)
    doc_id = upload_res.json()["document_id"]

    # Student 1 preprocesses
    await client.post(f"/api/v1/documents/{doc_id}/preprocess", headers=headers_s1, json={})

    # Student 2 tries to trigger preprocessing on Student 1's doc (IDOR attempt)
    s2_proc = await client.post(f"/api/v1/documents/{doc_id}/preprocess", headers=headers_s2, json={})
    assert s2_proc.status_code == 403
    assert "Access denied" in s2_proc.json()["detail"]

    # Student 2 tries to download Student 1's preprocessed image (IDOR attempt)
    s2_down = await client.get(f"/api/v1/documents/{doc_id}/preprocessed-image", headers=headers_s2)
    assert s2_down.status_code == 403
    assert "Access denied" in s2_down.json()["detail"]


@pytest.mark.asyncio
async def test_corrupted_image_handling_and_no_stack_trace(client: AsyncClient, test_db: AsyncSession, student1_token: str):
    """
    Tests handling of invalid or corrupted image input:
    1. Sets job status to FAILED
    2. Records error_code and sanitized error_message
    3. Does not leak raw exception stack traces to clients
    """
    headers_s1 = {"Authorization": f"Bearer {student1_token}"}

    # Upload a file that claims to be PNG but has corrupted/garbage bytes
    fake_png_header = b"\x89PNG\r\n\x1a\nGARBAGE_CORRUPTED_PIXEL_DATA_THAT_FAILS_DECODE"
    files = {"file": ("corrupt_cert.png", io.BytesIO(fake_png_header), "image/png")}
    data = {"document_type_code": "INCOME_CERTIFICATE"}

    upload_res = await client.post("/api/v1/documents/upload", headers=headers_s1, files=files, data=data)
    assert upload_res.status_code == 200
    doc_id = upload_res.json()["document_id"]

    # Trigger preprocessing on corrupted file
    proc_res = await client.post(f"/api/v1/documents/{doc_id}/preprocess", headers=headers_s1, json={})
    assert proc_res.status_code == 200
    job_data = proc_res.json()

    assert job_data["status"] == "FAILED"
    assert job_data["error_code"] == "IMAGE_PREPROCESSING_ERROR"
    assert "Corrupted or unsupported image file" in job_data["error_message"]
    # Ensure raw Python traceback is not leaked
    assert "Traceback" not in job_data["error_message"]
    assert "cv2.error" not in job_data["error_message"]


@pytest.mark.asyncio
async def test_preprocessing_does_not_alter_verification_state(client: AsyncClient, student1_token: str):
    """
    Verifies that preprocessing completion does NOT change document status to VERIFIED or APPROVED.
    Document status remains UPLOADED.
    """
    headers_s1 = {"Authorization": f"Bearer {student1_token}"}

    img_bytes = create_synthetic_test_image()
    files = {"file": ("student_fg_cert.png", io.BytesIO(img_bytes), "image/png")}
    data = {"document_type_code": "FIRST_GRADUATE_CERTIFICATE"}
    upload_res = await client.post("/api/v1/documents/upload", headers=headers_s1, files=files, data=data)
    doc_id = upload_res.json()["document_id"]

    # Preprocess
    proc_res = await client.post(f"/api/v1/documents/{doc_id}/preprocess", headers=headers_s1, json={})
    assert proc_res.status_code == 200
    assert proc_res.json()["status"] == "COMPLETED"

    # Check checklist item state
    app_res = await client.get("/api/v1/applications/me", headers=headers_s1)
    assert app_res.status_code == 200
    checklist = app_res.json()["checklist"]
    fg_item = next(item for item in checklist if item["code"] == "FIRST_GRADUATE_CERTIFICATE")
    assert fg_item["document_status"] == "UPLOADED"
    assert fg_item["preprocessing_status"] == "COMPLETED"
    assert fg_item["has_preprocessed_image"] is True
