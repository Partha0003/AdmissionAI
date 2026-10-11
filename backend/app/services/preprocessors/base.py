from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


@dataclass
class PreprocessingOptions:
    """
    Configuration options for image preprocessing.
    Allows fine-grained control over individual pipeline steps.
    """
    convert_grayscale: bool = True
    denoise: bool = True
    enhance_contrast: bool = True
    apply_threshold: bool = True
    deskew: bool = True
    max_dimension: int = 3500


@dataclass
class PreprocessingContext:
    """
    Context passed to document preprocessors containing source file details.
    """
    document_id: str
    document_version_id: Optional[str]
    file_path: str
    mime_type: str
    original_filename: str
    options: PreprocessingOptions = field(default_factory=PreprocessingOptions)


@dataclass
class PreprocessingResultData:
    """
    Structured output produced by a document image preprocessor.
    """
    output_image_bytes: bytes
    input_dimensions: Dict[str, int]
    output_dimensions: Dict[str, int]
    operations_applied: List[str]
    deskew_angle_deg: float
    output_format: str
    output_mime_type: str
    engine_name: str
    engine_version: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class DocumentPreprocessor(ABC):
    """
    Abstract interface for document image preprocessing engines.
    Enables modular replacement of OpenCV with alternative image processing libraries in future.
    """
    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the preprocessor engine."""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Version of the preprocessor engine."""
        pass

    @abstractmethod
    async def preprocess(self, context: PreprocessingContext) -> PreprocessingResultData:
        """
        Executes preprocessing pipeline on the input document.
        Must return PreprocessingResultData without mutating original file.
        """
        pass
