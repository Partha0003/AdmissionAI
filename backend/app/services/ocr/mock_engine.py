import hashlib
import time
from typing import List, Optional

from app.services.ocr.base import (
    OCREngine,
    OCRResultData,
    OCRBlock,
    BoundingBox,
)


class MockOCREngine(OCREngine):
    """
    Mock OCR engine strictly for deterministic unit/integration testing
    and explicit mock configuration (OCR_ENGINE=mock).
    Never to be presented as real Tesseract OCR.
    """

    def __init__(self, predefined_text: Optional[str] = None):
        self._predefined_text = predefined_text

    @property
    def name(self) -> str:
        return "mock"

    @property
    def version(self) -> str:
        return "1.0.0-mock"

    def is_available(self) -> bool:
        return True

    def extract(self, image_bytes: bytes, language: str = "eng") -> OCRResultData:
        start_time = time.perf_counter()
        image_sha256 = hashlib.sha256(image_bytes).hexdigest()

        # Default sample text for synthetic test fixtures
        text_content = self._predefined_text
        if text_content is None:
            text_content = (
                "XYZ ENGINEERING COLLEGE\n"
                "HIGHER SECONDARY COURSE CERTIFICATE\n"
                "NAME: TEST STUDENT\n"
                "ROLL NO: 12345678\n"
                "DATE OF BIRTH: 01/01/2005\n"
                "MATHEMATICS: 95 PHYSICS: 92 CHEMISTRY: 90\n"
                "TOTAL MARKS: 560 / 600\n"
                "COMMUNITY: BC"
            )

        lines = text_content.strip().split("\n") if text_content else []
        blocks: List[OCRBlock] = []
        word_confidences: List[float] = []

        curr_y = 50
        block_idx = 1
        for line_idx, line in enumerate(lines, start=1):
            words = line.split()
            curr_x = 40
            for word_idx, word in enumerate(words, start=1):
                word_w = max(30, len(word) * 12)
                word_h = 24
                conf = 0.95

                word_confidences.append(conf)
                box = BoundingBox(
                    x=curr_x,
                    y=curr_y,
                    width=word_w,
                    height=word_h,
                )
                blocks.append(
                    OCRBlock(
                        text=word,
                        confidence=conf,
                        bounding_box=box,
                        block_num=block_idx,
                        line_num=line_idx,
                        word_num=word_idx,
                    )
                )
                curr_x += word_w + 10
            curr_y += 35

        avg_conf = round(sum(word_confidences) / len(word_confidences), 4) if word_confidences else None
        duration_ms = max(1, int((time.perf_counter() - start_time) * 1000))

        return OCRResultData(
            full_text=text_content,
            language=language,
            engine_name=self.name,
            engine_version=self.version,
            processing_duration_ms=duration_ms,
            ocr_confidence=avg_conf,
            blocks=blocks,
            image_sha256=image_sha256,
        )
