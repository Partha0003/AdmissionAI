from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Union


class FieldExtractionException(Exception):
    """Base exception for field extraction errors."""
    pass


class ExtractorNotFoundException(FieldExtractionException):
    """Raised when no suitable extractor is registered for a document type."""
    pass


@dataclass
class FieldSourceProvenance:
    """
    Source traceability details connecting an extracted field to raw OCR output.
    All bounding boxes are in preprocessed image pixel coordinates.
    """
    ocr_block_indices: List[int] = field(default_factory=list)
    bounding_box: Optional[Dict[str, int]] = None
    context: Optional[str] = None
    document_version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExtractedField:
    """
    Structured key-value field extracted from document OCR text.
    Preserves raw value, typed normalized value, deterministic confidence, and provenance.
    """
    field_key: str
    field_name: str
    raw_value: Optional[str]
    normalized_value: Any
    field_type: str  # 'string' | 'number' | 'date' | 'category' | 'boolean'
    confidence: float  # Deterministic heuristic score clamped to [0.0, 1.0]
    requires_review: bool
    review_reason: Optional[str] = None
    source: FieldSourceProvenance = field(default_factory=FieldSourceProvenance)
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExtractionResultData:
    """
    Container representing the complete set of structured fields extracted from a document.
    """
    document_type_code: str
    extractor_name: str
    extractor_version: str
    fields: Dict[str, ExtractedField] = field(default_factory=dict)
    overall_confidence: float = 0.0
    requires_human_review: bool = False
    raw_field_count: int = 0
    extracted_field_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_type_code": self.document_type_code,
            "extractor_name": self.extractor_name,
            "extractor_version": self.extractor_version,
            "fields": {k: v.to_dict() for k, v in self.fields.items()},
            "overall_confidence": self.overall_confidence,
            "requires_human_review": self.requires_human_review,
            "raw_field_count": self.raw_field_count,
            "extracted_field_count": self.extracted_field_count,
            "metadata": self.metadata,
        }


class FieldExtractor(ABC):
    """
    Abstract base class for document-specific structured field extractors.
    All implementations must be deterministic, non-mutating, and preserve provenance.
    """

    @property
    @abstractmethod
    def document_type_code(self) -> str:
        """Standard document type code (e.g., 'TWELFTH_MARKSHEET', 'COMMUNITY_CERTIFICATE')."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the extractor engine."""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Semantic version of the extractor."""
        pass

    @abstractmethod
    def extract(
        self,
        raw_text: str,
        blocks: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
    ) -> ExtractionResultData:
        """
        Extracts structured fields from raw OCR text and spatial blocks.

        Args:
            raw_text: Full raw OCR string from Phase 4C.
            blocks: List of OCR block dictionaries containing text, confidence, and box coordinates.
            context: Optional contextual parameters (e.g. document_version).

        Returns:
            ExtractionResultData containing typed fields with provenance.
        """
        pass
