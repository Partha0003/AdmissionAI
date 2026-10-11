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
)


class TenthMarksheetExtractor(FieldExtractor):
    """
    Modular extractor for Secondary School (10th Standard / SSLC) Marksheets.
    Extracts candidate name, roll number, year of passing, total marks, percentage, and school.
    """

    DOCUMENT_TYPE = "TENTH_MARKSHEET"
    ENGINE_NAME = "TenthMarksheetExtractor"
    ENGINE_VERSION = "1.0.0-sslc"

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

        # 1. Candidate Name
        name_match = re.search(
            r"(?:NAME OF CANDIDATE|CANDIDATE NAME|NAME|STUDENT NAME)\s*[:\-]?\s*([A-Za-z\.\t ]{2,50})",
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

        # 2. Registration Number / Roll Number
        reg_match = re.search(
            r"(?:ROLL NO|REG(?:ISTRATION)?\s*NO|REGN NO|CERTIFICATE NO)\s*[:\-]?\s*([A-Za-z0-9\-\/\t ]{4,25})",
            raw_text,
            re.IGNORECASE,
        )

        if reg_match:
            raw_val = reg_match.group(1).strip()
            prov = find_ocr_blocks_for_text(raw_val, blocks, doc_version, reg_match.group(0))
            ocr_c = extract_mean_block_confidence(prov, blocks)
            fields["registration_number"] = ExtractedField(
                field_key="registration_number",
                field_name="Registration / Roll Number",
                raw_value=raw_val,
                normalized_value=raw_val.upper(),
                field_type="string",
                confidence=calculate_field_confidence(ocr_c, 0.95),
                requires_review=False,
                source=prov,
            )
        else:
            fields["registration_number"] = ExtractedField(
                field_key="registration_number",
                field_name="Registration / Roll Number",
                raw_value=None,
                normalized_value=None,
                field_type="string",
                confidence=0.0,
                requires_review=True,
                review_reason="Field not detected in OCR output",
                source=FieldSourceProvenance(document_version=doc_version),
            )

        # 3. Year of Passing
        year_match = re.search(
            r"(?:YEAR OF PASSING|SESSION|MONTH & YEAR|EXAM MONTH/YEAR)\s*[:\-]?\s*(?:[A-Z]+\s*)?((?:19|20)\d{2})",
            raw_text,
            re.IGNORECASE,
        )
        if year_match:
            raw_val = year_match.group(1).strip()
            prov = find_ocr_blocks_for_text(raw_val, blocks, doc_version, year_match.group(0))
            ocr_c = extract_mean_block_confidence(prov, blocks)
            fields["year_of_passing"] = ExtractedField(
                field_key="year_of_passing",
                field_name="Year of Passing",
                raw_value=raw_val,
                normalized_value=int(raw_val),
                field_type="number",
                confidence=calculate_field_confidence(ocr_c, 0.95),
                requires_review=False,
                source=prov,
            )
        else:
            fields["year_of_passing"] = ExtractedField(
                field_key="year_of_passing",
                field_name="Year of Passing",
                raw_value=None,
                normalized_value=None,
                field_type="number",
                confidence=0.0,
                requires_review=True,
                review_reason="Field not detected in OCR output",
                source=FieldSourceProvenance(document_version=doc_version),
            )

        # 4. Total Marks & Max Marks
        total_match = re.search(
            r"(?:TOTAL MARKS|TOTAL|GRAND TOTAL|MARKS OBTAINED)\s*[:\-]?\s*(\d{2,4}(?:\.\d+)?)\s*(?:\/\s*(\d{3,4}))?",
            raw_text,
            re.IGNORECASE,
        )
        total_val = None
        if total_match:
            raw_val = total_match.group(0).strip()
            total_str = total_match.group(1).strip()
            max_str = total_match.group(2) if total_match.group(2) else "500"
            prov = find_ocr_blocks_for_text(total_str, blocks, doc_version, raw_val)
            ocr_c = extract_mean_block_confidence(prov, blocks)
            total_num, req_rev, rev_reason = normalize_number(total_str)
            total_val = total_num
            max_num, _, _ = normalize_number(max_str)
            
            fields["total_marks"] = ExtractedField(
                field_key="total_marks",
                field_name="Total Marks",
                raw_value=raw_val,
                normalized_value=total_num,
                field_type="number",
                confidence=calculate_field_confidence(ocr_c, 0.95),
                requires_review=req_rev,
                review_reason=rev_reason,
                source=prov,
            )
            fields["max_marks"] = ExtractedField(
                field_key="max_marks",
                field_name="Maximum Marks",
                raw_value=max_str,
                normalized_value=max_num or 500.0,
                field_type="number",
                confidence=calculate_field_confidence(ocr_c, 0.95),
                requires_review=False,
                source=prov,
            )
        else:
            fields["total_marks"] = ExtractedField(
                field_key="total_marks",
                field_name="Total Marks",
                raw_value=None,
                normalized_value=None,
                field_type="number",
                confidence=0.0,
                requires_review=True,
                review_reason="Field not detected in OCR output",
                source=FieldSourceProvenance(document_version=doc_version),
            )
            fields["max_marks"] = ExtractedField(
                field_key="max_marks",
                field_name="Maximum Marks",
                raw_value=None,
                normalized_value=500.0,
                field_type="number",
                confidence=0.5,
                requires_review=False,
                source=FieldSourceProvenance(document_version=doc_version),
            )

        # 5. Percentage
        if total_val is not None:
            max_m = fields["max_marks"].normalized_value or 500.0
            pct_val = round((total_val / max_m) * 100.0, 2)
            fields["percentage"] = ExtractedField(
                field_key="percentage",
                field_name="Percentage",
                raw_value=f"{pct_val}%",
                normalized_value=pct_val,
                field_type="number",
                confidence=fields["total_marks"].confidence,
                requires_review=fields["total_marks"].requires_review,
                source=fields["total_marks"].source,
            )
        else:
            fields["percentage"] = ExtractedField(
                field_key="percentage",
                field_name="Percentage",
                raw_value=None,
                normalized_value=None,
                field_type="number",
                confidence=0.0,
                requires_review=True,
                review_reason="Unable to calculate percentage without total marks",
                source=FieldSourceProvenance(document_version=doc_version),
            )

        # 6. School Name
        school_match = re.search(
            r"(?:SCHOOL NAME|NAME OF SCHOOL|INSTITUTION|STUDIED AT)\s*[:\-]?\s*([A-Z0-9\s\,\.\-]{5,80})",
            raw_text,
            re.IGNORECASE,
        )
        if school_match:
            raw_val = school_match.group(1).strip()
            prov = find_ocr_blocks_for_text(raw_val, blocks, doc_version, school_match.group(0))
            ocr_c = extract_mean_block_confidence(prov, blocks)
            fields["school_name"] = ExtractedField(
                field_key="school_name",
                field_name="School Name",
                raw_value=raw_val,
                normalized_value=raw_val.title(),
                field_type="string",
                confidence=calculate_field_confidence(ocr_c, 0.85),
                requires_review=False,
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
            metadata={"source": "SSLC regex and layout extraction engine"},
        )
