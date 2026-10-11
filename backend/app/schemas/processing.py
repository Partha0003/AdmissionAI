from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ConfigDict


class ClassificationResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    job_id: str
    predicted_document_type: str
    predicted_document_type_name: str
    confidence: float
    confidence_type: str
    classifier_name: str
    classifier_version: str
    rule_used: Optional[str] = None
    reasoning: Optional[str] = None
    raw_metadata: Dict[str, Any] = {}
    processed_at: datetime


class PreprocessingResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    job_id: str
    document_id: str
    document_version_id: Optional[str] = None
    engine_name: str
    engine_version: str
    input_dimensions: Dict[str, Any] = {}
    output_dimensions: Dict[str, Any] = {}
    operations_applied: List[str] = []
    deskew_angle_deg: float = 0.0
    output_filename: str
    output_mime_type: str
    output_file_size: int
    processing_time_ms: Optional[int] = None
    created_at: datetime


class OCRBoundingBox(BaseModel):
    x: int
    y: int
    width: int
    height: int


class OCRBlockResponse(BaseModel):
    text: str
    confidence: Optional[float] = None
    bounding_box: OCRBoundingBox
    block_num: int = 0
    line_num: int = 0
    word_num: int = 0


class OCRResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    job_id: str
    document_id: str
    document_version_id: Optional[str] = None
    preprocessing_result_id: Optional[str] = None
    engine_name: str
    engine_version: str
    language: str
    image_sha256: str
    ocr_confidence: Optional[float] = None
    full_text: Optional[str] = None
    blocks: List[OCRBlockResponse] = []
    processing_time_ms: Optional[int] = None
    error_message: Optional[str] = None
    created_at: datetime


class DocumentProcessingJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    document_version_id: Optional[str] = None
    processing_type: str
    status: str
    requested_by: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    processing_time_ms: Optional[int] = None
    engine_name: str
    engine_version: str
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    classification_result: Optional[ClassificationResultResponse] = None
    preprocessing_result: Optional[PreprocessingResultResponse] = None
    ocr_result: Optional[OCRResultResponse] = None
    extraction_result: Optional["DocumentExtractionResultResponse"] = None


class FieldProvenanceResponse(BaseModel):
    ocr_block_indices: List[int] = []
    bounding_box: Optional[Dict[str, int]] = None
    context: Optional[str] = None
    document_version: int = 1


class ExtractedFieldResponse(BaseModel):
    field_key: str
    field_name: str
    raw_value: Optional[str] = None
    normalized_value: Any = None
    field_type: str
    confidence: float
    requires_review: bool = False
    review_reason: Optional[str] = None
    source: FieldProvenanceResponse = FieldProvenanceResponse()
    description: Optional[str] = None


class DocumentExtractionResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    job_id: str
    document_id: str
    document_version_id: Optional[str] = None
    ocr_result_id: Optional[str] = None
    document_type_code: str
    extractor_name: str
    extractor_version: str
    overall_confidence: float
    requires_human_review: bool
    fields: Dict[str, ExtractedFieldResponse] = {}
    raw_metadata: Dict[str, Any] = {}
    extraction_time_ms: Optional[int] = None
    created_at: datetime


class RunFieldExtractionRequest(BaseModel):
    force_reprocess: Optional[bool] = False


class ProcessDocumentRequest(BaseModel):
    processing_type: Optional[str] = "DOCUMENT_CLASSIFICATION"
    force_reprocess: Optional[bool] = False


class PreprocessDocumentRequest(BaseModel):
    convert_grayscale: Optional[bool] = True
    denoise: Optional[bool] = True
    enhance_contrast: Optional[bool] = True
    apply_threshold: Optional[bool] = True
    deskew: Optional[bool] = True
    force_reprocess: Optional[bool] = False


class RunOCRRequest(BaseModel):
    language: Optional[str] = "eng"
    engine_name: Optional[str] = None
    force_reprocess: Optional[bool] = False


class DocumentProcessingHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document_id: str
    total_jobs: int
    latest_job: Optional[DocumentProcessingJobResponse] = None
    jobs: List[DocumentProcessingJobResponse] = []


