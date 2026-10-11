from __future__ import annotations

import io
import os
from typing import Dict, Any, List, Tuple

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    cv2 = None
    np = None
    CV2_AVAILABLE = False

from app.services.preprocessors.base import (
    DocumentPreprocessor,
    PreprocessingContext,
    PreprocessingResultData,
    PreprocessingOptions,
)




class OpenCVDocumentPreprocessor(DocumentPreprocessor):
    """
    OpenCV-based document image preprocessor.
    
    Transforms uploaded raw document images into clean, standardized, deskewed,
    and high-contrast images optimized for downstream OCR extraction.
    
    IMPORTANT DISCLAIMER:
    Image preprocessing prepares visual content for OCR. It does not perform OCR,
    text extraction, or verify document authenticity.
    """

    ENGINE_NAME = "OpenCVDocumentPreprocessor"
    ENGINE_VERSION = "1.0.0-opencv"

    MIN_DIMENSION = 10
    MAX_DIMENSION = 10000

    @property
    def name(self) -> str:
        return self.ENGINE_NAME

    @property
    def version(self) -> str:
        return self.ENGINE_VERSION

    def _load_image(self, file_path: str, mime_type: str) -> np.ndarray:
        """
        Safely loads and decodes image or PDF document to OpenCV BGR ndarray.
        Rejects empty, corrupt, or unreadable files.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Document file does not exist on disk.")

        file_size = os.path.getsize(file_path)
        if file_size == 0:
            raise ValueError("Document file is empty (0 bytes).")

        # Handle PDF documents by rendering page 0 to image via PyMuPDF
        if mime_type == "application/pdf" or file_path.lower().endswith(".pdf"):
            try:
                import fitz  # pymupdf
                doc = fitz.open(file_path)
                if doc.page_count < 1:
                    raise ValueError("PDF document contains no pages.")
                page = doc.load_page(0)
                pix = page.get_pixmap(dpi=150)
                img_data = pix.tobytes("png")
                nparr = np.frombuffer(img_data, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                doc.close()
                if img is None:
                    raise ValueError("Failed to rasterize PDF page into image.")
                return img
            except Exception as e:
                raise ValueError(f"Failed to decode PDF document for image preprocessing: {str(e)}")

        # Handle standard image formats
        with open(file_path, "rb") as f:
            file_bytes = f.read()

        nparr = np.frombuffer(file_bytes, np.uint8)
        if len(nparr) == 0:
            raise ValueError("Failed to read image bytes.")

        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None or not isinstance(img, np.ndarray) or img.size == 0:
            raise ValueError("Corrupted or unsupported image file. Image could not be decoded.")

        return img

    def _calculate_skew_angle(self, gray: np.ndarray) -> float:
        """
        Detects orientation skew of document text using Otsu thresholded coordinates.
        """
        try:
            # Invert threshold to isolate text features
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            coords = np.column_stack(np.where(thresh > 0))
            if len(coords) < 100:
                return 0.0

            rect = cv2.minAreaRect(coords)
            angle = rect[-1]

            # Normalize angle to [-45, 45]
            if angle < -45:
                angle = -(90 + angle)
            elif angle > 45:
                angle = 90 - angle
            else:
                angle = -angle

            # Clamp skew correction to realistic document tilts
            if abs(angle) > 45.0:
                return 0.0

            return float(angle)
        except Exception:
            return 0.0

    def _deskew_image(self, img: np.ndarray, angle: float) -> np.ndarray:
        """
        Rotates image by detected skew angle using affine transform with replication borders.
        """
        if abs(angle) < 0.2:
            return img

        (h, w) = img.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(
            img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
        )
        return rotated

    async def preprocess(self, context: PreprocessingContext) -> PreprocessingResultData:
        if not CV2_AVAILABLE:
            raise RuntimeError("OpenCV (opencv-python-headless) and numpy are required for image preprocessing. Please run: pip install -r backend/requirements.txt")

        options = context.options or PreprocessingOptions()

        # Step 1: Load and decode image
        raw_img = self._load_image(context.file_path, context.mime_type)

        h, w = raw_img.shape[:2]
        channels = raw_img.shape[2] if len(raw_img.shape) > 2 else 1

        if h < self.MIN_DIMENSION or w < self.MIN_DIMENSION:
            raise ValueError(f"Image dimensions ({w}x{h}) are below minimum allowed threshold ({self.MIN_DIMENSION}px).")

        if h > self.MAX_DIMENSION or w > self.MAX_DIMENSION:
            raise ValueError(f"Image dimensions ({w}x{h}) exceed maximum allowed threshold ({self.MAX_DIMENSION}px).")

        input_dims = {"width": int(w), "height": int(h), "channels": int(channels)}
        operations_applied: List[str] = []

        current_img = raw_img.copy()

        # Step 1.5: Optional aspect-ratio preserving downscale if image exceeds max_dimension
        if max(h, w) > options.max_dimension:
            scale = options.max_dimension / float(max(h, w))
            new_w = max(10, int(w * scale))
            new_h = max(10, int(h * scale))
            current_img = cv2.resize(current_img, (new_w, new_h), interpolation=cv2.INTER_AREA)
            operations_applied.append("RESIZE_DOWNSCALE")

        # Step 2: Grayscale Conversion
        if options.convert_grayscale:
            if len(current_img.shape) == 3 and current_img.shape[2] == 3:
                gray = cv2.cvtColor(current_img, cv2.COLOR_BGR2GRAY)
            else:
                gray = current_img.copy()
            operations_applied.append("GRAYSCALE")
        else:
            gray = current_img.copy()

        # Step 3: Noise Reduction
        if options.denoise:
            if len(gray.shape) == 2:
                gray = cv2.GaussianBlur(gray, (3, 3), 0)
            else:
                gray = cv2.GaussianBlur(gray, (3, 3), 0)
            operations_applied.append("GAUSSIAN_DENOISE")

        # Step 4: Contrast Enhancement via CLAHE
        if options.enhance_contrast and len(gray.shape) == 2:
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            gray = clahe.apply(gray)
            operations_applied.append("CLAHE_CONTRAST")

        # Step 5: Deskewing
        deskew_angle = 0.0
        if options.deskew and len(gray.shape) == 2:
            detected_angle = self._calculate_skew_angle(gray)
            if abs(detected_angle) >= 0.5:
                gray = self._deskew_image(gray, detected_angle)
                deskew_angle = round(detected_angle, 2)
                operations_applied.append("DESKEW")

        # Step 6: Binarization / Thresholding
        if options.apply_threshold and len(gray.shape) == 2:
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            final_img = thresh
            operations_applied.append("OTSU_THRESHOLD")
        else:
            final_img = gray

        # Step 7: Output Normalization & Encoding to PNG
        out_h, out_w = final_img.shape[:2]
        out_channels = final_img.shape[2] if len(final_img.shape) > 2 else 1
        output_dims = {"width": int(out_w), "height": int(out_h), "channels": int(out_channels)}

        success, encoded_buf = cv2.imencode(".png", final_img, [cv2.IMWRITE_PNG_COMPRESSION, 4])
        if not success:
            raise RuntimeError("Failed to encode preprocessed image to PNG format.")

        output_bytes = encoded_buf.tobytes()

        return PreprocessingResultData(
            output_image_bytes=output_bytes,
            input_dimensions=input_dims,
            output_dimensions=output_dims,
            operations_applied=operations_applied,
            deskew_angle_deg=deskew_angle,
            output_format="PNG",
            output_mime_type="image/png",
            engine_name=self.ENGINE_NAME,
            engine_version=self.ENGINE_VERSION,
            metadata={
                "input_format": context.mime_type,
                "original_filename": context.original_filename,
                "pipeline_steps": operations_applied,
                "note": "OpenCV document image preprocessing for downstream OCR optimization.",
            },
        )
