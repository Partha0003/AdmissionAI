from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.schemas.admission import (
    AdminDashboardMetricsResponse,
    AdminStudentListItem,
)
from app.schemas.processing import (
    DocumentProcessingHistoryResponse,
    OCRResultResponse,
    DocumentExtractionResultResponse,
)
from app.schemas.reconciliation import CrossDocumentReconciliationResponse
from app.models.user import User
from app.api.deps import require_roles
from app.services.admission_service import (
    get_dashboard_metrics,
    list_students_with_admissions,
)

router = APIRouter(prefix="/admin", tags=["Admin Operations"])

admin_role_check = require_roles([
    "ADMIN_VERIFIER",
    "ADMISSION_HEAD",
    "FINANCE_OFFICER",
    "SUPER_ADMIN"
])


@router.get("/dashboard", response_model=AdminDashboardMetricsResponse)
async def get_admin_dashboard(
    current_user: User = Depends(admin_role_check),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns aggregated real database metrics for the administration dashboard.
    """
    metrics = await get_dashboard_metrics(db)
    return AdminDashboardMetricsResponse(**metrics)


@router.get("/students", response_model=List[AdminStudentListItem])
async def list_admin_students(
    status: Optional[str] = Query(None, description="Filter by admission status"),
    branch: Optional[str] = Query(None, description="Filter by allotted branch"),
    search: Optional[str] = Query(None, description="Search by student name, app no, or email"),
    current_user: User = Depends(admin_role_check),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns the list of student records and their current admission lifecycle status.
    Supports filtering by status, branch, and keyword search.
    """
    students = await list_students_with_admissions(
        db=db,
        status_filter=status,
        branch_filter=branch,
        search=search
    )
    return students


@router.get("/documents/{document_id}/processing", response_model=DocumentProcessingHistoryResponse)
async def get_admin_document_processing(
    document_id: str,
    current_user: User = Depends(admin_role_check),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns AI document processing inspection history and classification details for scrutiny.
    Requires administrative verification privileges.
    """
    from app.services.document_processing_service import DocumentProcessingService
    return await DocumentProcessingService.get_processing_history(
        db=db,
        document_id=document_id,
        current_user=current_user,
        require_admin=True,
    )


@router.get("/documents/{document_id}/preprocessing", response_model=DocumentProcessingHistoryResponse)
async def get_admin_document_preprocessing(
    document_id: str,
    current_user: User = Depends(admin_role_check),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns OpenCV image preprocessing inspection history and transform metadata for scrutiny.
    Requires administrative verification privileges.
    """
    from app.services.document_preprocessing_service import DocumentPreprocessingService
    return await DocumentPreprocessingService.get_preprocessing_history(
        db=db,
        document_id=document_id,
        current_user=current_user,
        require_admin=True,
    )


@router.get("/documents/{document_id}/ocr", response_model=Optional[OCRResultResponse])
async def get_admin_document_ocr(
    document_id: str,
    current_user: User = Depends(admin_role_check),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns extracted OCR text, confidence, bounding boxes, and image SHA-256 for scrutiny.
    Requires administrative verification privileges.
    """
    from app.services.document_ocr_service import DocumentOCRService
    return await DocumentOCRService.get_latest_ocr_result(
        db=db,
        document_id=document_id,
        current_user=current_user,
    )


@router.get("/documents/{document_id}/extracted-fields", response_model=Optional[DocumentExtractionResultResponse])
async def get_admin_document_extracted_fields(
    document_id: str,
    current_user: User = Depends(admin_role_check),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns structured key-value extracted fields, normalized values, confidence, and provenance for scrutiny.
    Requires administrative verification privileges.
    """
    from app.services.document_field_extraction_service import DocumentFieldExtractionService
    return await DocumentFieldExtractionService.get_admin_extraction_result(
        db=db,
        document_id=document_id,
    )


@router.post("/applications/{application_id}/reconcile", response_model=CrossDocumentReconciliationResponse)
async def run_admin_application_reconciliation(
    application_id: str,
    current_user: User = Depends(admin_role_check),
    db: AsyncSession = Depends(get_db),
):
    """
    Triggers deterministic cross-document consistency reconciliation for admin scrutiny.
    Strictly read-only; does NOT alter application status or verify document authenticity.
    """
    from app.services.cross_document_reconciliation_service import CrossDocumentReconciliationService
    
    service = CrossDocumentReconciliationService()
    try:
        recon = await service.run_reconciliation(db, application_id)
        return recon
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Reconciliation run failed: {str(e)}",
        )


@router.get("/applications/{application_id}/reconciliation", response_model=Optional[CrossDocumentReconciliationResponse])
async def get_admin_application_reconciliation(
    application_id: str,
    current_user: User = Depends(admin_role_check),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves the latest cross-document consistency reconciliation snapshot and findings for admin scrutiny.
    """
    from app.services.cross_document_reconciliation_service import CrossDocumentReconciliationService
    
    service = CrossDocumentReconciliationService()
    recon = await service.get_latest_reconciliation(db, application_id)
    if not recon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No reconciliation snapshot found for this application.",
        )
    return recon





