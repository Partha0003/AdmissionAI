from typing import Optional
from app.core.config import settings
from app.services.ocr.base import (
    OCREngine,
    OCRResultData,
    OCRBlock,
    BoundingBox,
    OCRException,
    OCREngineUnavailableException,
    OCRProcessingException,
)
from app.services.ocr.tesseract_engine import TesseractOCREngine
from app.services.ocr.mock_engine import MockOCREngine


def get_ocr_engine(engine_name: Optional[str] = None) -> OCREngine:
    """
    Factory to obtain the configured OCR engine.
    Strictly avoids silent automatic fallbacks to mock OCR.
    """
    selected = (engine_name or settings.OCR_ENGINE).lower()

    if selected == "tesseract":
        return TesseractOCREngine()
    elif selected == "mock":
        return MockOCREngine()
    else:
        raise ValueError(
            f"Unsupported OCR engine '{selected}'. Supported engines are 'tesseract' and 'mock'."
        )


__all__ = [
    "OCREngine",
    "OCRResultData",
    "OCRBlock",
    "BoundingBox",
    "OCRException",
    "OCREngineUnavailableException",
    "OCRProcessingException",
    "TesseractOCREngine",
    "MockOCREngine",
    "get_ocr_engine",
]
