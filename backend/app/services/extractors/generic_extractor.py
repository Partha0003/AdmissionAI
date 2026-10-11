from __future__ import annotations

import re
from typing import Dict, Any, List, Optional
from app.services.extractors.base import (
    FieldExtractor,
    ExtractedField,
    ExtractionResultData,
    FieldSourceProvenance,
)
from app.services.extractors.utils import (
    calculate_field_confidence,
    find_ocr_blocks_for_text,
    extract_mean_block_confidence,
)


class GenericDocumentExtractor(FieldExtractor):
    """
    Fallback extractor for generic or unhandled document types.
    Extracts basic key-value patterns using heuristic regex matching.
    
    IMPORTANT DISCLAIMER:
    This is a heuristic key-value extraction engine. It does not verify document
    semantics, validity, or authenticity.
    """

    DOCUMENT_TYPE = "GENERIC"
    ENGINE_NAME = "GenericDocumentExtractor"
    ENGINE_VERSION = "1.0.0-generic"

    @property
    def document_type_code(self) -> str:
        return self.DOCUMENT_TYPE

    @property
    def name(self) -> str:
        return self.ENGINE_NAME

    @property
    def version(self) -> str:
        return self.ENGINE_VERSION

    def extract(
        self,
        raw_text: str,
        blocks: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
    ) -> ExtractionResultData:
        doc_version = context.get("document_version", 1) if context else 1
        doc_type = context.get("document_type_code", "GENERIC") if context else "GENERIC"
        
        fields: Dict[str, ExtractedField] = {}

        # Heuristic search for Name
        name_match = re.search(
            r"(?:NAME|APPLICANT|CANDIDATE|STUDENT)\s*[:\-]?\s*([A-Z\s\.]{3,50})",
            raw_text,
            re.IGNORECASE,
        )
        if name_match:
            raw_val = name_match.group(1).strip()
            prov = find_ocr_blocks_for_text(raw_val, blocks, doc_version, name_match.group(0))
            ocr_c = extract_mean_block_confidence(prov, blocks)
            fields["candidate_name"] = ExtractedField(
                field_key="candidate_name",
                field_name="Candidate Name (Heuristic)",
                raw_value=raw_val,
                normalized_value=raw_val.upper(),
                field_type="string",
                confidence=calculate_field_confidence(ocr_c, 0.70),
                requires_review=True,
                review_reason="Generic heuristic match — requires human verification",
                source=prov,
                description="Generic key-value extraction — does not verify document semantics.",
            )

        # Heuristic search for Reference / Document Number
        ref_match = re.search(
            r"(?:NO|NUMBER|REF|CERTIFICATE|REGN?)\s*[:\-]?\s*([A-Z0-9\-\/]{4,25})",
            raw_text,
            re.IGNORECASE,
        )
        if ref_match:
            raw_val = ref_match.group(1).strip()
            prov = find_ocr_blocks_for_text(raw_val, blocks, doc_version, ref_match.group(0))
            ocr_c = extract_mean_block_confidence(prov, blocks)
            fields["document_reference_number"] = ExtractedField(
                field_key="document_reference_number",
                field_name="Document Reference Number (Heuristic)",
                raw_value=raw_val,
                normalized_value=raw_val.upper(),
                field_type="string",
                confidence=calculate_field_confidence(ocr_c, 0.70),
                requires_review=True,
                review_reason="Generic heuristic match — requires human verification",
                source=prov,
                description="Generic key-value extraction — does not verify document semantics.",
            )

        detected_fields = [f for f in fields.values() if f.normalized_value is not None]
        overall_c = (
            sum(f.confidence for f in detected_fields) / len(detected_fields)
            if detected_fields
            else 0.0
        )

        return ExtractionResultData(
            document_type_code=doc_type,
            extractor_name=self.ENGINE_NAME,
            extractor_version=self.ENGINE_VERSION,
            fields=fields,
            overall_confidence=round(overall_c, 4),
            requires_human_review=True,  # Always true for generic fallback
            raw_field_count=len(fields),
            extracted_field_count=len(detected_fields),
            metadata={
                "source": "Generic heuristic key-value extraction",
                "disclaimer": "Generic heuristic key-value extraction — does not verify document semantics.",
            },
        )
