from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database.session import get_db
from app.models.admission import AdmissionApplication
from app.models.student import Student
from app.models.user import User
from app.models.document import Document, DocumentVersion, DocumentType
from app.api.deps import get_current_user, get_current_student, require_roles
from app.services.application_service import ApplicationService
from app.services.document_service import DocumentService
from app.services.document_processing_service import DocumentProcessingService
from app.services.document_preprocessing_service import DocumentPreprocessingService
from app.services.document_ocr_service import DocumentOCRService
from app.services.document_field_extraction_service import DocumentFieldExtractionService
from app.services.preprocessors.base import PreprocessingOptions
from app.schemas.document import (
    DocumentTypeResponse,
    DocumentUploadResponse,
    DocumentDetailResponse,
    DocumentVersionResponse,
)
from app.schemas.processing import (
    DocumentProcessingJobResponse,
    DocumentProcessingHistoryResponse,
    ProcessDocumentRequest,
    PreprocessDocumentRequest,
    RunOCRRequest,
    OCRResultResponse,
    RunFieldExtractionRequest,
    DocumentExtractionResultResponse,
)

router = APIRouter(prefix="/documents", tags=["Documents"])



@router.get("/types", response_model=List[DocumentTypeResponse])
async def list_document_types(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns all active document types and their allowed specifications.
    """
    stmt = (
        select(DocumentType)
        .where(DocumentType.is_active == True)
        .order_by(DocumentType.sort_order.asc())
    )
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    document_type_code: str = Form(...),
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db)
):
    """
    Uploads or updates a document for the authenticated student's application.
    Enforces MIME, magic-byte checks, SHA-256 calculation, and automatic versioning.
    """
    app = await ApplicationService.get_or_initialize_application(db, student)

    if app.status in ["APPLICATION_SUBMITTED", "DOCUMENTS_VERIFIED", "ADMISSION_CONFIRMED"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot upload documents in status '{app.status}'. Application is locked for verification."
        )

    doc, doc_version = await DocumentService.upload_document(
        db=db,
        application=app,
        document_type_code=document_type_code,
        upload_file=file,
        current_user=student.user,
    )

    # Recalculate completion percentage
    completion = await ApplicationService.evaluate_completion(db, app, student)
    app.completion_percentage = completion.overall_percentage
    await db.commit()

    return DocumentUploadResponse(
        document_id=doc.id,
        version_id=doc_version.id,
        document_type_code=document_type_code,
        original_filename=doc_version.original_filename,
        version_number=doc_version.version_number,
        document_status=doc.status,
        message=f"Document uploaded successfully as Version {doc_version.version_number}."
    )


@router.get("/{document_id}/download")
async def download_document_file(
    document_id: str,
    version: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Secure file retrieval endpoint with IDOR prevention.
    Students can only download their own application files; Staff can view any.
    """
    stmt = (
        select(Document, AdmissionApplication)
        .join(AdmissionApplication, Document.application_id == AdmissionApplication.id)
        .where(Document.id == document_id)
    )
    res = await db.execute(stmt)
    row = res.first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    doc, app = row

    # IDOR Check
    role_name = current_user.role.name if current_user.role else ""
    if role_name == "STUDENT":
        if not current_user.student or current_user.student.id != app.student_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You do not have permission to view this document."
            )

    file_path, filename, mime_type = await DocumentService.get_document_file_path(
        db=db,
        document_id=document_id,
        version_number=version
    )

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type=mime_type,
        content_disposition_type="inline"
    )


@router.get("/{document_id}/versions", response_model=List[DocumentVersionResponse])
async def get_document_versions(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns audit trail and version history for a specific document.
    """
    stmt = (
        select(Document, AdmissionApplication)
        .join(AdmissionApplication, Document.application_id == AdmissionApplication.id)
        .where(Document.id == document_id)
    )
    res = await db.execute(stmt)
    row = res.first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    doc, app = row

    # IDOR Check
    role_name = current_user.role.name if current_user.role else ""
    if role_name == "STUDENT":
        if not current_user.student or current_user.student.id != app.student_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You cannot view versions of another student's documents."
            )

    return doc.versions


@router.post("/{document_id}/process", response_model=DocumentProcessingJobResponse)
async def process_document_classification(
    document_id: str,
    body: Optional[ProcessDocumentRequest] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Initiates prototype AI document classification on the uploaded document.
    Enforces Anti-IDOR (student can process their own document; staff can process any).
    State lifecycle: NOT_PROCESSED -> QUEUED -> PROCESSING -> COMPLETED (or FAILED).
    """
    req = body or ProcessDocumentRequest()
    job = await DocumentProcessingService.process_document(
        db=db,
        document_id=document_id,
        current_user=current_user,
        processing_type=req.processing_type or "DOCUMENT_CLASSIFICATION",
        force_reprocess=req.force_reprocess or False,
    )
    return job


@router.get("/{document_id}/processing", response_model=DocumentProcessingHistoryResponse)
async def get_document_processing_history(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns the processing job history and classification results for a document.
    Enforces Anti-IDOR for students and authorized role checks for staff.
    """
    history = await DocumentProcessingService.get_processing_history(
        db=db,
        document_id=document_id,
        current_user=current_user,
        require_admin=False,
    )
    return history


@router.post("/{document_id}/preprocess", response_model=DocumentProcessingJobResponse)
async def preprocess_document_image(
    document_id: str,
    body: Optional[PreprocessDocumentRequest] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Initiates OpenCV document image preprocessing pipeline (grayscale, denoise, CLAHE, threshold, deskew).
    Preserves the original uploaded file in storage and creates a distinct preprocessed artifact.
    Enforces Anti-IDOR (student can preprocess their own documents; staff can preprocess any).
    """
    req = body or PreprocessDocumentRequest()
    opts = PreprocessingOptions(
        convert_grayscale=req.convert_grayscale if req.convert_grayscale is not None else True,
        denoise=req.denoise if req.denoise is not None else True,
        enhance_contrast=req.enhance_contrast if req.enhance_contrast is not None else True,
        apply_threshold=req.apply_threshold if req.apply_threshold is not None else True,
        deskew=req.deskew if req.deskew is not None else True,
    )
    job = await DocumentPreprocessingService.preprocess_document(
        db=db,
        document_id=document_id,
        current_user=current_user,
        options=opts,
    )
    return job


@router.get("/{document_id}/preprocessing", response_model=DocumentProcessingHistoryResponse)
async def get_document_preprocessing_history(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns the preprocessing job history and transformation metadata for a document.
    Enforces Anti-IDOR for students and authorized role checks for staff.
    """
    history = await DocumentPreprocessingService.get_preprocessing_history(
        db=db,
        document_id=document_id,
        current_user=current_user,
        require_admin=False,
    )
    return history


@router.get("/{document_id}/preprocessed-image")
async def get_preprocessed_image_file(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Secure retrieval endpoint for the preprocessed document image artifact.
    Enforces Anti-IDOR (students can only retrieve their own preprocessed images; staff can access any).
    Never exposes internal server filesystem paths.
    """
    file_path, filename, mime_type = await DocumentPreprocessingService.get_preprocessed_file(
        db=db,
        document_id=document_id,
        current_user=current_user,
    )
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type=mime_type,
        content_disposition_type="inline"
    )


@router.post("/{document_id}/ocr", response_model=DocumentProcessingJobResponse)
async def run_document_ocr(
    document_id: str,
    body: Optional[RunOCRRequest] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Initiates OCR machine-readable text and bounding box extraction on the Phase 4B preprocessed image.
    Enforces strict Anti-IDOR (student can OCR their own documents; staff can OCR any).
    Requires completed preprocessing.
    """
    req = body or RunOCRRequest()
    job = await DocumentOCRService.process_document_ocr(
        db=db,
        document_id=document_id,
        current_user=current_user,
        request_options=req,
    )
    return job


@router.get("/{document_id}/ocr", response_model=Optional[OCRResultResponse])
async def get_document_ocr(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieves the latest OCR extraction result for a document.
    Enforces Anti-IDOR for students and authorized role checks for staff.
    """
    ocr_result = await DocumentOCRService.get_latest_ocr_result(
        db=db,
        document_id=document_id,
        current_user=current_user,
    )
    return ocr_result


@router.post("/{document_id}/extract-fields", response_model=DocumentProcessingJobResponse)
async def run_document_field_extraction(
    document_id: str,
    body: Optional[RunFieldExtractionRequest] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Executes structured key-value entity extraction from the document's Phase 4C OCR result.
    Enforces Anti-IDOR (students can extract their own documents; staff can extract any).
    Requires completed OCR.
    """
    req = body or RunFieldExtractionRequest()
    job = await DocumentFieldExtractionService.process_document_field_extraction(
        db=db,
        document_id=document_id,
        current_user=current_user,
        request_options=req,
    )
    return job


@router.get("/{document_id}/extracted-fields", response_model=Optional[DocumentExtractionResultResponse])
async def get_document_extracted_fields(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves the latest structured field extraction result for a document.
    Enforces Anti-IDOR for students and authorized role checks for staff.
    """
    res = await DocumentFieldExtractionService.get_latest_extraction_result(
        db=db,
        document_id=document_id,
        current_user=current_user,
    )
    return res



