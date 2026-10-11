import pytest
import io
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.document import Document, DocumentVersion, DocumentType
from app.models.document_processing import DocumentProcessingJob, ClassificationResult, ProcessingStatus
from app.services.classifiers.base import DocumentClassificationContext, DocumentClassifier, ClassificationResultData
from app.services.classifiers.rule_based import RuleBasedDocumentClassifier
from app.services.document_processing_service import DocumentProcessingService


@pytest.mark.asyncio
async def test_rule_based_classifier_exact_and_heuristics():
    """
    Unit test for RuleBasedDocumentClassifier logic.
    Tests exact keyword match, cross-category mismatch detection, and fallback heuristic.
    """
    classifier = RuleBasedDocumentClassifier()
    assert classifier.name == "RuleBasedDocumentClassifier"
    assert classifier.version == "1.0.0-prototype"

    # 1. Exact match test (Tenth Marksheet)
    ctx1 = DocumentClassificationContext(
        document_id="doc-1",
        document_version_id="ver-1",
        original_filename="karthik_10th_marksheet_sslccert.pdf",
        declared_document_type_code="TENTH_MARKSHEET",
        declared_document_type_name="10th Marksheet",
        mime_type="application/pdf",
        file_size=102400,
    )
    res1 = await classifier.classify(ctx1)
    assert res1.predicted_document_type == "TENTH_MARKSHEET"
    assert res1.confidence == 0.90
    assert res1.confidence_type == "heuristic_confidence"
    assert "RULE_FILENAME_EXACT_MATCH" in res1.rule_used
    assert "10th Marksheet" in res1.predicted_document_type_name

    # 2. Mismatch test (Uploaded Transfer Certificate under Twelfth Marksheet slot)
    ctx2 = DocumentClassificationContext(
        document_id="doc-2",
        document_version_id="ver-2",
        original_filename="school_tc_leaving_cert.pdf",
        declared_document_type_code="TWELFTH_MARKSHEET",
        declared_document_type_name="12th Marksheet",
        mime_type="application/pdf",
        file_size=85000,
    )
    res2 = await classifier.classify(ctx2)
    assert res2.predicted_document_type == "TRANSFER_CERTIFICATE"
    assert res2.confidence == 0.75
    assert "RULE_FILENAME_MISMATCH" in res2.rule_used
    assert "Flagged for verifier inspection" in res2.reasoning

    # 3. Fallback test (Generic scan filename)
    ctx3 = DocumentClassificationContext(
        document_id="doc-3",
        document_version_id="ver-3",
        original_filename="scan_doc_20260901_001.pdf",
        declared_document_type_code="COMMUNITY_CERTIFICATE",
        declared_document_type_name="Community Certificate",
        mime_type="application/pdf",
        file_size=120000,
    )
    res3 = await classifier.classify(ctx3)
    assert res3.predicted_document_type == "COMMUNITY_CERTIFICATE"
    assert res3.confidence == 0.50
    assert "RULE_DECLARED_TYPE_FALLBACK" in res3.rule_used


@pytest.mark.asyncio
async def test_processing_lifecycle_and_api_flow(client: AsyncClient, student1_token: str, admin_token: str):
    """
    Integration test for processing lifecycle:
    1. Upload document as Student 1
    2. Process document via POST /api/v1/documents/{id}/process
    3. Verify lifecycle transitions: QUEUED -> PROCESSING -> COMPLETED
    4. Verify persistence of engine, version, processing_time_ms, confidence score
    5. Retrieve processing history via GET /api/v1/documents/{id}/processing
    """
    headers_s1 = {"Authorization": f"Bearer {student1_token}"}
    headers_admin = {"Authorization": f"Bearer {admin_token}"}

    # Upload Tenth Marksheet as Student 1 (PDF format)
    pdf_content = b"%PDF-1.4 Minimal PDF content for testing Tenth Marksheet"
    files = {"file": ("student_10th_marksheet.pdf", io.BytesIO(pdf_content), "application/pdf")}
    data = {"document_type_code": "TENTH_MARKSHEET"}

    upload_res = await client.post("/api/v1/documents/upload", headers=headers_s1, files=files, data=data)
    assert upload_res.status_code == 200, upload_res.text
    doc_id = upload_res.json()["document_id"]
    assert doc_id is not None

    # Trigger processing via API
    proc_res = await client.post(f"/api/v1/documents/{doc_id}/process", headers=headers_s1, json={})
    assert proc_res.status_code == 200, proc_res.text
    job_data = proc_res.json()

    assert job_data["document_id"] == doc_id
    assert job_data["status"] == "COMPLETED"
    assert job_data["processing_type"] == "DOCUMENT_CLASSIFICATION"
    assert job_data["engine_name"] == "RuleBasedDocumentClassifier"
    assert job_data["engine_version"] == "1.0.0-prototype"
    assert job_data["processing_time_ms"] is not None
    assert job_data["processing_time_ms"] >= 1
    assert job_data["started_at"] is not None
    assert job_data["completed_at"] is not None
    assert job_data["error_code"] is None

    # Verify classification result payload
    clf_res = job_data["classification_result"]
    assert clf_res is not None
    assert clf_res["predicted_document_type"] == "TENTH_MARKSHEET"
    assert clf_res["confidence"] == 0.90
    assert clf_res["confidence_type"] == "heuristic_confidence"
    assert clf_res["classifier_name"] == "RuleBasedDocumentClassifier"

    # Check Student 1 can retrieve processing history
    history_res = await client.get(f"/api/v1/documents/{doc_id}/processing", headers=headers_s1)
    assert history_res.status_code == 200
    history_data = history_res.json()
    assert history_data["document_id"] == doc_id
    assert history_data["total_jobs"] == 1
    assert history_data["latest_job"]["status"] == "COMPLETED"
    assert history_data["latest_job"]["classification_result"]["predicted_document_type"] == "TENTH_MARKSHEET"

    # Check Admin can view processing history via Admin endpoint
    admin_res = await client.get(f"/api/v1/admin/documents/{doc_id}/processing", headers=headers_admin)
    assert admin_res.status_code == 200
    admin_history = admin_res.json()
    assert admin_history["total_jobs"] == 1
    assert admin_history["latest_job"]["classification_result"]["predicted_document_type"] == "TENTH_MARKSHEET"


@pytest.mark.asyncio
async def test_anti_idor_processing_security(client: AsyncClient, student1_token: str, student2_token: str):
    """
    Tests Anti-IDOR security:
    Student 2 cannot trigger processing or view processing results for Student 1's documents.
    """
    headers_s1 = {"Authorization": f"Bearer {student1_token}"}
    headers_s2 = {"Authorization": f"Bearer {student2_token}"}

    # Upload document as Student 1
    pdf_content = b"%PDF-1.4 Transfer Certificate Content"
    files = {"file": ("student_tc.pdf", io.BytesIO(pdf_content), "application/pdf")}
    data = {"document_type_code": "TRANSFER_CERTIFICATE"}

    upload_res = await client.post("/api/v1/documents/upload", headers=headers_s1, files=files, data=data)
    assert upload_res.status_code == 200
    doc_id = upload_res.json()["document_id"]

    # Student 2 attempts to trigger processing on Student 1's document (IDOR attempt)
    s2_proc_res = await client.post(f"/api/v1/documents/{doc_id}/process", headers=headers_s2, json={})
    assert s2_proc_res.status_code == 403
    assert "Access denied" in s2_proc_res.json()["detail"]

    # Student 2 attempts to read processing history for Student 1's document (IDOR attempt)
    s2_hist_res = await client.get(f"/api/v1/documents/{doc_id}/processing", headers=headers_s2)
    assert s2_hist_res.status_code == 403
    assert "Access denied" in s2_hist_res.json()["detail"]


@pytest.mark.asyncio
async def test_unauthenticated_and_unauthorized_role_processing(client: AsyncClient, student1_token: str):
    """
    Tests unauthenticated and invalid role access to admin processing endpoint.
    """
    # 1. Unauthenticated request to process
    unauth_res = await client.post("/api/v1/documents/non-existent-id/process", json={})
    assert unauth_res.status_code == 401

    # 2. Student attempts to access admin processing endpoint
    headers_s1 = {"Authorization": f"Bearer {student1_token}"}
    admin_ep_res = await client.get("/api/v1/admin/documents/some-id/processing", headers=headers_s1)
    assert admin_ep_res.status_code == 403


class FailingMockClassifier(DocumentClassifier):
    """Mock classifier that simulates internal unexpected processing failure."""
    @property
    def name(self) -> str:
        return "FailingMockClassifier"

    @property
    def version(self) -> str:
        return "0.0.1-error"

    async def classify(self, context: DocumentClassificationContext) -> ClassificationResultData:
        raise RuntimeError("Internal simulation failure: DB memory corruption / buffer overflow trace")


@pytest.mark.asyncio
async def test_failed_processing_graceful_handling_and_no_stack_trace(test_db: AsyncSession, client: AsyncClient, student1_token: str):
    """
    Tests that a failure during classifier execution:
    1. Sets job status to FAILED
    2. Records error_code and sanitized error_message
    3. Never exposes internal stack trace / raw exceptions to clients
    """
    headers_s1 = {"Authorization": f"Bearer {student1_token}"}

    # Upload a document
    pdf_content = b"%PDF-1.4 Mock Document"
    files = {"file": ("twelfth_marksheet.pdf", io.BytesIO(pdf_content), "application/pdf")}
    data = {"document_type_code": "TWELFTH_MARKSHEET"}
    upload_res = await client.post("/api/v1/documents/upload", headers=headers_s1, files=files, data=data)
    doc_id = upload_res.json()["document_id"]

    # Retrieve current student user
    from app.models.user import User
    stmt = select(User).where(User.id == "user-student-001")
    res = await test_db.execute(stmt)
    user = res.scalar_one()

    # Process with FailingMockClassifier directly via service
    job = await DocumentProcessingService.process_document(
        db=test_db,
        document_id=doc_id,
        current_user=user,
        classifier=FailingMockClassifier(),
    )

    assert job.status == ProcessingStatus.FAILED.value
    assert job.error_code == "PROCESSING_EXECUTION_ERROR"
    # Ensure raw runtime exception trace is NOT in error_message
    assert "buffer overflow trace" not in job.error_message
    assert "Automated prototype document classification encountered an error" in job.error_message

    # Verify history response
    history = await DocumentProcessingService.get_processing_history(
        db=test_db,
        document_id=doc_id,
        current_user=user,
    )
    assert history.total_jobs >= 1
    latest = history.latest_job
    assert latest.status == "FAILED"
    assert "buffer overflow trace" not in latest.error_message


@pytest.mark.asyncio
async def test_document_processing_does_not_alter_verification_status(client: AsyncClient, student1_token: str):
    """
    Verifies that AI classification completion does NOT alter document status to VERIFIED or APPROVED.
    Document status remains UPLOADED (human review required).
    """
    headers_s1 = {"Authorization": f"Bearer {student1_token}"}

    # Upload document
    pdf_content = b"%PDF-1.4 10th marksheet"
    files = {"file": ("tenth_marksheet.pdf", io.BytesIO(pdf_content), "application/pdf")}
    data = {"document_type_code": "TENTH_MARKSHEET"}
    upload_res = await client.post("/api/v1/documents/upload", headers=headers_s1, files=files, data=data)
    doc_id = upload_res.json()["document_id"]

    # Process document
    proc_res = await client.post(f"/api/v1/documents/{doc_id}/process", headers=headers_s1, json={})
    assert proc_res.status_code == 200
    assert proc_res.json()["status"] == "COMPLETED"

    # Check checklist item state: document status should still be UPLOADED, not VERIFIED
    app_res = await client.get("/api/v1/applications/me", headers=headers_s1)
    assert app_res.status_code == 200
    checklist = app_res.json()["checklist"]
    tenth_item = next(item for item in checklist if item["code"] == "TENTH_MARKSHEET")
    assert tenth_item["document_status"] == "UPLOADED"
    assert tenth_item["processing_status"] == "COMPLETED"
    assert tenth_item["predicted_document_type"] == "TENTH_MARKSHEET"
