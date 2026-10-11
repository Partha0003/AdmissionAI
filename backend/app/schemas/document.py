from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class DocumentTypeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    code: str
    name: str
    description: Optional[str] = None
    allowed_extensions: List[str]
    max_file_size_mb: int = 5
    is_mandatory_default: bool = False
    display_order: int = 0


class ChecklistItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document_type_id: str
    code: str
    name: str
    description: Optional[str] = None
    is_mandatory: bool
    mandatory_reason: Optional[str] = None
    allowed_extensions: List[str]
    max_file_size_mb: int
    document_id: Optional[str] = None
    document_status: str = "NOT_UPLOADED"
    active_version: Optional[int] = None
    rejection_reason: Optional[str] = None
    original_filename: Optional[str] = None
    uploaded_at: Optional[datetime] = None
    file_size_bytes: Optional[int] = None
    processing_status: Optional[str] = "NOT_PROCESSED"
    predicted_document_type: Optional[str] = None
    predicted_document_type_name: Optional[str] = None
    heuristic_confidence: Optional[float] = None
    classifier_name: Optional[str] = None
    classifier_version: Optional[str] = None
    preprocessing_status: Optional[str] = "NOT_PROCESSED"
    has_preprocessed_image: Optional[bool] = False
    ocr_status: Optional[str] = "NOT_PROCESSED"
    has_ocr_result: Optional[bool] = False
    extraction_status: Optional[str] = "NOT_PROCESSED"
    has_extracted_fields: Optional[bool] = False





class DocumentVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    version_number: int
    original_filename: str
    mime_type: str
    file_size_bytes: int = 0
    file_hash_sha256: str = ""
    uploaded_at: datetime


class DocumentDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    admission_application_id: str
    document_type_id: str
    document_type_code: str
    document_type_name: str
    document_status: str
    rejection_reason: Optional[str] = None
    active_version_number: int
    created_at: datetime
    updated_at: datetime
    versions: List[DocumentVersionResponse] = []


class DocumentUploadResponse(BaseModel):
    document_id: str
    version_id: str
    document_type_code: str
    original_filename: str
    version_number: int
    document_status: str
    message: str
