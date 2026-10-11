from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


class OCRException(Exception):
    """Base exception for OCR errors."""
    pass


class OCREngineUnavailableException(OCRException):
    """Raised when the requested OCR engine is not installed or unavailable."""
    pass


class OCRProcessingException(OCRException):
    """Raised when OCR processing encounters a runtime failure."""
    pass


@dataclass
class BoundingBox:
    """
    Bounding box coordinates in pixels relative to the PREPROCESSED IMAGE.
    Coordinate origin (0, 0) is the top-left corner of the preprocessed image.
    """
    x: int
    y: int
    width: int
    height: int

    def to_dict(self) -> Dict[str, int]:
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
        }


@dataclass
class OCRBlock:
    """
    Hierarchical text block / word unit extracted by OCR.
    Coordinates are strictly relative to the preprocessed image.
    """
    text: str
    confidence: Optional[float]  # 0.0 - 1.0 (word/block level confidence)
    bounding_box: BoundingBox
    block_num: int = 0
    line_num: int = 0
    word_num: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "confidence": self.confidence,
            "bounding_box": self.bounding_box.to_dict(),
            "block_num": self.block_num,
            "line_num": self.line_num,
            "word_num": self.word_num,
        }


@dataclass
class OCRResultData:
    """
    Normalized result of machine-readable text extraction.
    Note: OCR output represents extracted raw text, not document verification or structured fields.
    """
    full_text: str
    language: str
    engine_name: str
    engine_version: str
    processing_duration_ms: int
    ocr_confidence: Optional[float]  # Average word-level OCR confidence (0.0 - 1.0)
    blocks: List[OCRBlock] = field(default_factory=list)
    image_sha256: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "full_text": self.full_text,
            "language": self.language,
            "engine_name": self.engine_name,
            "engine_version": self.engine_version,
            "processing_duration_ms": self.processing_duration_ms,
            "ocr_confidence": self.ocr_confidence,
            "blocks": [b.to_dict() for b in self.blocks],
            "image_sha256": self.image_sha256,
        }


class OCREngine(ABC):
    """
    Abstract interface for pluggable OCR engines.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Returns the unique name of the OCR engine."""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Returns the version of the OCR engine."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Checks whether the OCR engine and its required binaries/models are available."""
        pass

    @abstractmethod
    def extract(self, image_bytes: bytes, language: str = "eng") -> OCRResultData:
        """
        Extract machine-readable text and layout from preprocessed image bytes.

        :param image_bytes: PNG or JPEG encoded preprocessed image bytes.
        :param language: Language code (e.g. 'eng', 'tam').
        :return: Normalized OCRResultData.
        :raises OCREngineUnavailableException: If engine is missing or unconfigured.
        :raises OCRProcessingException: If processing fails.
        """
        pass
