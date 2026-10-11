from __future__ import annotations

import hashlib
import io
import time
from typing import Optional, List

from app.core.config import settings
from app.services.ocr.base import (
    OCREngine,
    OCRResultData,
    OCRBlock,
    BoundingBox,
    OCREngineUnavailableException,
    OCRProcessingException,
)


class TesseractOCREngine(OCREngine):
    """
    Concrete OCR engine implementation wrapping Tesseract via pytesseract.
    Coordinates produced are strictly relative to the preprocessed image.
    """

    def __init__(self, tesseract_cmd: Optional[str] = None):
        self._custom_cmd = tesseract_cmd or settings.TESSERACT_CMD
        self._cached_version: Optional[str] = None

    @property
    def name(self) -> str:
        return "tesseract"

    @property
    def version(self) -> str:
        if self._cached_version:
            return self._cached_version
        try:
            import pytesseract
            if self._custom_cmd:
                pytesseract.pytesseract.tesseract_cmd = self._custom_cmd
            ver = pytesseract.get_tesseract_version()
            self._cached_version = str(ver)
            return self._cached_version
        except Exception:
            return "unavailable"

    def is_available(self) -> bool:
        try:
            import pytesseract
            if self._custom_cmd:
                pytesseract.pytesseract.tesseract_cmd = self._custom_cmd
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False

    def extract(self, image_bytes: bytes, language: str = "eng") -> OCRResultData:
        if not self.is_available():
            raise OCREngineUnavailableException(
                "Tesseract OCR engine binary is not installed or not found on system PATH. "
                "Please install Tesseract OCR and set TESSERACT_CMD in settings/environment."
            )

        start_time = time.perf_counter()
        image_sha256 = hashlib.sha256(image_bytes).hexdigest()

        try:
            from PIL import Image
            import pytesseract
            from pytesseract import Output

            if self._custom_cmd:
                pytesseract.pytesseract.tesseract_cmd = self._custom_cmd

            image = Image.open(io.BytesIO(image_bytes))

            # Full text string extraction
            full_text = pytesseract.image_to_string(image, lang=language).strip()

            # Structured block / word data extraction
            data = pytesseract.image_to_data(image, lang=language, output_type=Output.DICT)

            blocks: List[OCRBlock] = []
            word_confidences: List[float] = []

            n_boxes = len(data.get("text", []))
            for i in range(n_boxes):
                text = (data["text"][i] or "").strip()
                conf_raw = data["conf"][i]

                # Tesseract conf is integer 0-100 or -1 for structure elements
                conf_float: Optional[float] = None
                try:
                    conf_val = float(conf_raw)
                    if conf_val >= 0:
                        conf_float = max(0.0, min(1.0, conf_val / 100.0))
                except (ValueError, TypeError):
                    pass

                if text:
                    if conf_float is not None:
                        word_confidences.append(conf_float)

                    box = BoundingBox(
                        x=int(data["left"][i]),
                        y=int(data["top"][i]),
                        width=int(data["width"][i]),
                        height=int(data["height"][i]),
                    )
                    block = OCRBlock(
                        text=text,
                        confidence=conf_float,
                        bounding_box=box,
                        block_num=int(data.get("block_num", [0])[i]),
                        line_num=int(data.get("line_num", [0])[i]),
                        word_num=int(data.get("word_num", [0])[i]),
                    )
                    blocks.append(block)

            # Calculate average word-level OCR confidence
            avg_conf: Optional[float] = None
            if word_confidences:
                avg_conf = round(sum(word_confidences) / len(word_confidences), 4)

            duration_ms = int((time.perf_counter() - start_time) * 1000)

            return OCRResultData(
                full_text=full_text,
                language=language,
                engine_name=self.name,
                engine_version=self.version,
                processing_duration_ms=duration_ms,
                ocr_confidence=avg_conf,
                blocks=blocks,
                image_sha256=image_sha256,
            )

        except OCRException:
            raise
        except Exception as e:
            raise OCRProcessingException(f"Tesseract OCR processing failed: {str(e)}") from e
