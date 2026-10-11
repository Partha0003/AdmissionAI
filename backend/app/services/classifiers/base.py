from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from datetime import datetime


@dataclass
class DocumentClassificationContext:
    """
    Context passed to document classifiers containing uploaded document metadata.
    Note: Image pixel data / OCR extraction will be introduced in future phases.
    """
    document_id: str
    document_version_id: Optional[str]
    original_filename: str
    declared_document_type_code: str
    declared_document_type_name: str
    mime_type: str
    file_size: int
    extra_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ClassificationResultData:
    """
    Structured output produced by a document classifier.
    Confidence score is explicitly documented as a heuristic/prototype score in Phase 4A.
    """
    predicted_document_type: str
    predicted_document_type_name: str
    confidence: float
    confidence_type: str  # e.g., "heuristic_confidence" or "prototype_confidence"
    classifier_name: str
    classifier_version: str
    rule_used: Optional[str] = None
    reasoning: Optional[str] = None
    raw_metadata: Dict[str, Any] = field(default_factory=dict)
    processed_at: Optional[datetime] = None


class DocumentClassifier(ABC):
    """
    Abstract interface for document classification engines.
    Allows transparent future replacement with ML models, PyTorch/ONNX, or inference services.
    """
    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the classifier engine."""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Version of the classifier engine."""
        pass

    @abstractmethod
    async def classify(self, context: DocumentClassificationContext) -> ClassificationResultData:
        """
        Classifies the document given the context.
        Must return ClassificationResultData.
        """
        pass
