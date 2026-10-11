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
    normalize_number,
    normalize_community,
)


class AllotmentOrderExtractor(FieldExtractor):
    """
    Modular extractor for TNEA Provisional Allotment Orders.
    Extracts TNEA Application Number, Allotment Number, Candidate Name,
    Allotted College Code (e.g., XYZ), Allotted Branch, Category, Quota, and Cutoff Mark.
    """

    DOCUMENT_TYPE = "ALLOTMENT_ORDER"
    ENGINE_NAME = "AllotmentOrderExtractor"
    ENGINE_VERSION = "1.0.0-tnea"

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
        fields: Dict[str, ExtractedField] = {}

        # 1. TNEA Application Number
        app_match = re.search(
            r"(?:TNEA\s*APPLICATION\s*NO|APPLICATION\s*NO|APP\s*NO)\s*[:\-]?\s*([A-Z0-9]{6,15})",
            raw_text,
            re.IGNORECASE,
        )
        if app_match:
            raw_val = app_match.group(1).strip()
            prov = find_ocr_blocks_for_text(raw_val, blocks, doc_version, app_match.group(0))
            ocr_c = extract_mean_block_confidence(prov, blocks)
            fields["tnea_application_number"] = ExtractedField(
                field_key="tnea_application_number",
                field_name="TNEA Application Number",
                raw_value=raw_val,
                normalized_value=raw_val.upper(),
                field_type="string",
                confidence=calculate_field_confidence(ocr_c, 0.95),
                requires_review=False,
                source=prov,
            )
        else:
            fields["tnea_application_number"] = ExtractedField(
                field_key="tnea_application_number",
                field_name="TNEA Application Number",
                raw_value=None,
                normalized_value=None,
                field_type="string",
                confidence=0.0,
                requires_review=True,
                review_reason="Field not detected in OCR output",
                source=FieldSourceProvenance(document_version=doc_version),
            )

        # 2. Allotment Order Number
        alt_match = re.search(
            r"(?:ALLOTMENT\s*ORDER\s*NO|ALLOTMENT\s*NO|ORDER\s*NO)\s*[:\-]?\s*([A-Z0-9\-\/]{6,25})",
            raw_text,
            re.IGNORECASE,
        )
        if alt_match:
            raw_val = alt_match.group(1).strip()
            prov = find_ocr_blocks_for_text(raw_val, blocks, doc_version, alt_match.group(0))
            ocr_c = extract_mean_block_confidence(prov, blocks)
            fields["allotment_order_number"] = ExtractedField(
                field_key="allotment_order_number",
                field_name="Allotment Order Number",
                raw_value=raw_val,
                normalized_value=raw_val.upper(),
                field_type="string",
                confidence=calculate_field_confidence(ocr_c, 0.95),
                requires_review=False,
                source=prov,
            )
        else:
            fields["allotment_order_number"] = ExtractedField(
                field_key="allotment_order_number",
                field_name="Allotment Order Number",
                raw_value=None,
                normalized_value=None,
                field_type="string",
                confidence=0.0,
                requires_review=True,
                review_reason="Field not detected in OCR output",
                source=FieldSourceProvenance(document_version=doc_version),
            )

        # 3. Candidate Name
        name_match = re.search(
            r"(?:NAME OF CANDIDATE|CANDIDATE NAME|NAME)\s*[:\-]?\s*([A-Z\s\.]{3,50})",
            raw_text,
            re.IGNORECASE,
        )
        if name_match:
            raw_val = name_match.group(1).strip()
            prov = find_ocr_blocks_for_text(raw_val, blocks, doc_version, name_match.group(0))
            ocr_c = extract_mean_block_confidence(prov, blocks)
            fields["candidate_name"] = ExtractedField(
                field_key="candidate_name",
                field_name="Candidate Name",
                raw_value=raw_val,
                normalized_value=raw_val.upper(),
                field_type="string",
                confidence=calculate_field_confidence(ocr_c, 0.95),
                requires_review=False,
                source=prov,
            )
        else:
            fields["candidate_name"] = ExtractedField(
                field_key="candidate_name",
                field_name="Candidate Name",
                raw_value=None,
                normalized_value=None,
                field_type="string",
                confidence=0.0,
                requires_review=True,
                review_reason="Field not detected in OCR output",
                source=FieldSourceProvenance(document_version=doc_version),
            )

        # 4. Allotted College Code
        code_match = re.search(
            r"(?:COLLEGE CODE|INSTITUTION CODE|ALLOTTED COLLEGE CODE)\s*[:\-]?\s*([A-Z0-9]{3,10})",
            raw_text,
            re.IGNORECASE,
        )
        if code_match:
            raw_val = code_match.group(1).strip()
            prov = find_ocr_blocks_for_text(raw_val, blocks, doc_version, code_match.group(0))
            ocr_c = extract_mean_block_confidence(prov, blocks)
            fields["allotted_college_code"] = ExtractedField(
                field_key="allotted_college_code",
                field_name="Allotted College Code",
                raw_value=raw_val,
                normalized_value=raw_val.upper(),
                field_type="string",
                confidence=calculate_field_confidence(ocr_c, 0.95),
                requires_review=False,
                source=prov,
            )

        # 5. Allotted Branch
        branch_match = re.search(
            r"(?:BRANCH|ALLOTTED BRANCH|COURSE ALLOTTED)\s*[:\-]?\s*([A-Z\s\&\,\.\-]{3,60})",
            raw_text,
            re.IGNORECASE,
        )
        if branch_match:
            raw_val = branch_match.group(1).strip()
            prov = find_ocr_blocks_for_text(raw_val, blocks, doc_version, branch_match.group(0))
            ocr_c = extract_mean_block_confidence(prov, blocks)
            fields["allotted_branch"] = ExtractedField(
                field_key="allotted_branch",
                field_name="Allotted Branch",
                raw_value=raw_val,
                normalized_value=raw_val.title(),
                field_type="string",
                confidence=calculate_field_confidence(ocr_c, 0.90),
                requires_review=False,
                source=prov,
            )

        # 6. Document Cutoff Mark (from allotment document, not verified against external database)
        cutoff_match = re.search(
            r"(?:CUTOFF MARK|CUTOFF|MERIT MARK|TNEA MARK)\s*[:\-]?\s*(\d{2,3}(?:\.\d+)?)",
            raw_text,
            re.IGNORECASE,
        )
        if cutoff_match:
            raw_val = cutoff_match.group(1).strip()
            num_val, req_rev, rev_reason = normalize_number(raw_val)
            prov = find_ocr_blocks_for_text(raw_val, blocks, doc_version, cutoff_match.group(0))
            ocr_c = extract_mean_block_confidence(prov, blocks)
            fields["document_cutoff_mark"] = ExtractedField(
                field_key="document_cutoff_mark",
                field_name="Document Cutoff Mark",
                raw_value=raw_val,
                normalized_value=num_val,
                field_type="number",
                confidence=calculate_field_confidence(ocr_c, 0.90),
                requires_review=req_rev,
                review_reason=rev_reason,
                description="The cutoff value extracted from the allotment document. It is not independently verified against an authoritative external source.",
                source=prov,
            )

        # Overall confidence
        detected_fields = [f for f in fields.values() if f.normalized_value is not None]
        overall_c = (
            sum(f.confidence for f in detected_fields) / len(detected_fields)
            if detected_fields
            else 0.0
        )
        has_review = any(f.requires_review for f in fields.values())

        return ExtractionResultData(
            document_type_code=self.DOCUMENT_TYPE,
            extractor_name=self.ENGINE_NAME,
            extractor_version=self.ENGINE_VERSION,
            fields=fields,
            overall_confidence=round(overall_c, 4),
            requires_human_review=has_review,
            raw_field_count=len(fields),
            extracted_field_count=len(detected_fields),
            metadata={"source": "TNEA Allotment extraction engine"},
        )
