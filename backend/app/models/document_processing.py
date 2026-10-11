import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Boolean, Float, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base


class ProcessingStatus(str, enum.Enum):
    NOT_PROCESSED = "NOT_PROCESSED"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ProcessingType(str, enum.Enum):
    DOCUMENT_CLASSIFICATION = "DOCUMENT_CLASSIFICATION"
    IMAGE_PREPROCESSING = "IMAGE_PREPROCESSING"
    OCR = "OCR"  # Future Phase 4
    FIELD_EXTRACTION = "FIELD_EXTRACTION"  # Future Phase 4
    FULL_PIPELINE = "FULL_PIPELINE"  # Future Phase 4


class DocumentProcessingJob(Base):
    __tablename__ = "document_processing_jobs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id"), nullable=False, index=True
    )
    document_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("document_versions.id"), nullable=True, index=True
    )
    processing_type: Mapped[str] = mapped_column(
        String(50), default=ProcessingType.DOCUMENT_CLASSIFICATION.value, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(50), default=ProcessingStatus.NOT_PROCESSED.value, nullable=False, index=True
    )
    requested_by: Mapped[str] = mapped_column(String(150), nullable=False)
    
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    processing_time_ms: Mapped[int] = mapped_column(Integer, nullable=True)
    
    engine_name: Mapped[str] = mapped_column(
        String(100), default="RuleBasedDocumentClassifier", nullable=False
    )
    engine_version: Mapped[str] = mapped_column(
        String(50), default="1.0.0-prototype", nullable=False
    )
    
    error_code: Mapped[str] = mapped_column(String(50), nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    document = relationship("Document", back_populates="processing_jobs", lazy="selectin")
    document_version = relationship("DocumentVersion", lazy="selectin")
    classification_result = relationship(
        "ClassificationResult",
        back_populates="job",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    preprocessing_result = relationship(
        "PreprocessingResult",
        back_populates="job",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    ocr_result = relationship(
        "OCRResult",
        back_populates="job",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    extraction_result = relationship(
        "DocumentExtractionResult",
        back_populates="job",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin"
    )



class ClassificationResult(Base):
    __tablename__ = "classification_results"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("document_processing_jobs.id"), nullable=False, unique=True, index=True
    )
    predicted_document_type: Mapped[str] = mapped_column(String(50), nullable=False)
    predicted_document_type_name: Mapped[str] = mapped_column(String(150), nullable=False)
    
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_type: Mapped[str] = mapped_column(
        String(50), default="heuristic_confidence", nullable=False
    )
    classifier_name: Mapped[str] = mapped_column(
        String(100), default="RuleBasedDocumentClassifier", nullable=False
    )
    classifier_version: Mapped[str] = mapped_column(
        String(50), default="1.0.0-prototype", nullable=False
    )
    rule_used: Mapped[str] = mapped_column(String(255), nullable=True)
    reasoning: Mapped[str] = mapped_column(Text, nullable=True)
    raw_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    job = relationship("DocumentProcessingJob", back_populates="classification_result", lazy="selectin")


class PreprocessingResult(Base):
    __tablename__ = "preprocessing_results"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("document_processing_jobs.id"), nullable=False, unique=True, index=True
    )
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id"), nullable=False, index=True
    )
    document_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("document_versions.id"), nullable=True, index=True
    )
    
    engine_name: Mapped[str] = mapped_column(
        String(100), default="OpenCVDocumentPreprocessor", nullable=False
    )
    engine_version: Mapped[str] = mapped_column(
        String(50), default="1.0.0-opencv", nullable=False
    )
    
    input_dimensions: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    output_dimensions: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    operations_applied: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    deskew_angle_deg: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    output_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    output_mime_type: Mapped[str] = mapped_column(String(100), default="image/png", nullable=False)
    output_file_size: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    processing_time_ms: Mapped[int] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    job = relationship("DocumentProcessingJob", back_populates="preprocessing_result", lazy="selectin")
    document = relationship("Document", lazy="selectin")
    document_version = relationship("DocumentVersion", lazy="selectin")


class OCRResult(Base):
    __tablename__ = "ocr_results"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("document_processing_jobs.id"), nullable=False, unique=True, index=True
    )
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id"), nullable=False, index=True
    )
    document_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("document_versions.id"), nullable=True, index=True
    )
    preprocessing_result_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("preprocessing_results.id"), nullable=True, index=True
    )
    
    engine_name: Mapped[str] = mapped_column(
        String(100), default="tesseract", nullable=False
    )
    engine_version: Mapped[str] = mapped_column(
        String(50), default="unknown", nullable=False
    )
    language: Mapped[str] = mapped_column(
        String(20), default="eng", nullable=False
    )
    image_sha256: Mapped[str] = mapped_column(
        String(64), nullable=False
    )
    
    ocr_confidence: Mapped[float] = mapped_column(Float, nullable=True)
    full_text: Mapped[str] = mapped_column(Text, nullable=True)
    blocks: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    
    processing_time_ms: Mapped[int] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    job = relationship("DocumentProcessingJob", back_populates="ocr_result", lazy="selectin")
    document = relationship("Document", lazy="selectin")
    document_version = relationship("DocumentVersion", lazy="selectin")
    preprocessing_result = relationship("PreprocessingResult", lazy="selectin")


class DocumentExtractionResult(Base):
    __tablename__ = "document_extraction_results"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("document_processing_jobs.id"), nullable=False, unique=True, index=True
    )
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id"), nullable=False, index=True
    )
    document_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("document_versions.id"), nullable=True, index=True
    )
    ocr_result_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("ocr_results.id"), nullable=True, index=True
    )

    document_type_code: Mapped[str] = mapped_column(String(50), nullable=False)
    extractor_name: Mapped[str] = mapped_column(String(100), nullable=False)
    extractor_version: Mapped[str] = mapped_column(String(50), nullable=False)

    overall_confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    requires_human_review: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    fields: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    raw_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    extraction_time_ms: Mapped[int] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    job = relationship("DocumentProcessingJob", back_populates="extraction_result", lazy="selectin")
    document = relationship("Document", lazy="selectin")
    document_version = relationship("DocumentVersion", lazy="selectin")
    ocr_result = relationship("OCRResult", lazy="selectin")


class CrossDocumentReconciliation(Base):
    __tablename__ = "cross_document_reconciliations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    application_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("admission_applications.id"), nullable=False, index=True
    )
    overall_status: Mapped[str] = mapped_column(
        String(30), default="MATCH", nullable=False, index=True
    )
    participating_document_versions: Mapped[dict] = mapped_column(
        JSON, default=dict, nullable=False
    )
    total_rules_evaluated: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    passed_rules_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    discrepancy_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    pending_scrutiny_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    incomplete_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    findings: Mapped[list] = mapped_column(
        JSON, default=list, nullable=False
    )
    discrepancy_summary: Mapped[dict] = mapped_column(
        JSON, default=dict, nullable=False
    )
    requires_human_review: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    reconciliation_time_ms: Mapped[int] = mapped_column(
        Integer, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    application = relationship("AdmissionApplication", lazy="selectin")



