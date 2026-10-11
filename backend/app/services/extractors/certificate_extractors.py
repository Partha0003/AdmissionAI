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
    normalize_date,
    normalize_number,
)


class TransferCertificateExtractor(FieldExtractor):
    """
    Extractor for School Transfer Certificates (TC).
    Extracts candidate name, date of birth, date of leaving, school/institution, and TC number.
    """

    DOCUMENT_TYPE = "TRANSFER_CERTIFICATE"
    ENGINE_NAME = "TransferCertificateExtractor"
    ENGINE_VERSION = "1.0.0-tc"

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
            r"(?:NAME OF PUPIL|NAME OF STUDENT|NAME OF CANDIDATE|NAME)\s*[:\-]?\s*([A-Z\s\.]{3,50})",
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

        # 2. TC Number
        tc_match = re.search(
            r"(?:T\.C\.?\s*NO|TRANSFER CERTIFICATE NO|TC NUMBER|SERIAL NO)\s*[:\-]?\s*([A-Z0-9\-\/]{3,20})",
            raw_text,
            re.IGNORECASE,
        )
        if tc_match:
            raw_val = tc_match.group(1).strip()
            prov = find_ocr_blocks_for_text(raw_val, blocks, doc_version, tc_match.group(0))
            ocr_c = extract_mean_block_confidence(prov, blocks)
            fields["tc_number"] = ExtractedField(
                field_key="tc_number",
                field_name="Transfer Certificate Number",
                raw_value=raw_val,
                normalized_value=raw_val.upper(),
                field_type="string",
                confidence=calculate_field_confidence(ocr_c, 0.95),
                requires_review=False,
                source=prov,
            )

        # 3. Date of Birth
        dob_match = re.search(
            r"(?:DATE OF BIRTH|DOB)\s*[:\-]?\s*([0-9]{1,4}[\/\-\.][0-9]{1,2}[\/\-\.][0-9]{2,4})",
            raw_text,
            re.IGNORECASE,
        )
        if dob_match:
            raw_val = dob_match.group(1).strip()
            norm_dt, req_rev, rev_reason = normalize_date(raw_val)
            prov = find_ocr_blocks_for_text(raw_val, blocks, doc_version, dob_match.group(0))
            ocr_c = extract_mean_block_confidence(prov, blocks)
            fields["date_of_birth"] = ExtractedField(
                field_key="date_of_birth",
                field_name="Date of Birth",
                raw_value=raw_val,
                normalized_value=norm_dt,
                field_type="date",
                confidence=calculate_field_confidence(ocr_c, 0.90),
                requires_review=req_rev,
                review_reason=rev_reason,
                source=prov,
            )

        # 4. School Name
        school_match = re.search(
            r"(?:SCHOOL NAME|NAME OF SCHOOL|INSTITUTION|COLLEGE)\s*[:\-]?\s*([A-Z0-9\s\,\.\-]{5,80})",
            raw_text,
            re.IGNORECASE,
        )
        if school_match:
            raw_val = school_match.group(1).strip()
            prov = find_ocr_blocks_for_text(raw_val, blocks, doc_version, school_match.group(0))
            ocr_c = extract_mean_block_confidence(prov, blocks)
            fields["school_name"] = ExtractedField(
                field_key="school_name",
                field_name="School / Institution Name",
                raw_value=raw_val,
                normalized_value=raw_val.title(),
                field_type="string",
                confidence=calculate_field_confidence(ocr_c, 0.85),
                requires_review=False,
                source=prov,
            )

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
            metadata={"source": "TC extraction engine"},
        )


class IncomeCertificateExtractor(FieldExtractor):
    """
    Extractor for Annual Family Income Certificates.
    Extracts candidate/parent name, annual income amount, certificate number, issuing authority.
    """

    DOCUMENT_TYPE = "INCOME_CERTIFICATE"
    ENGINE_NAME = "IncomeCertificateExtractor"
    ENGINE_VERSION = "1.0.0-income"

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

        # 1. Candidate / Parent Name
        name_match = re.search(
            r"(?:THIS IS TO CERTIFY THAT|NAME OF APPLICANT|THIRU|SELVI|NAME)\s*[:\-]?\s*([A-Z\s\.]{3,50})",
            raw_text,
            re.IGNORECASE,
        )
        if name_match:
            raw_val = name_match.group(1).strip()
            prov = find_ocr_blocks_for_text(raw_val, blocks, doc_version, name_match.group(0))
            ocr_c = extract_mean_block_confidence(prov, blocks)
            fields["candidate_name"] = ExtractedField(
                field_key="candidate_name",
                field_name="Applicant / Parent Name",
                raw_value=raw_val,
                normalized_value=raw_val.upper(),
                field_type="string",
                confidence=calculate_field_confidence(ocr_c, 0.95),
                requires_review=False,
                source=prov,
            )

        # 2. Annual Income Amount
        inc_match = re.search(
            r"(?:ANNUAL INCOME|ANNUAL FAMILY INCOME|TOTAL INCOME|INCOME IS RS\.?|RS\.?)\s*[:\-]?\s*(?:RS\.?\s*)?([0-9\,]+(?:\.\d+)?)",
            raw_text,
            re.IGNORECASE,
        )
        if inc_match:
            raw_val = inc_match.group(1).strip()
            num_val, req_rev, rev_reason = normalize_number(raw_val)
            prov = find_ocr_blocks_for_text(raw_val, blocks, doc_version, inc_match.group(0))
            ocr_c = extract_mean_block_confidence(prov, blocks)
            fields["annual_income"] = ExtractedField(
                field_key="annual_income",
                field_name="Annual Family Income (INR)",
                raw_value=raw_val,
                normalized_value=num_val,
                field_type="number",
                confidence=calculate_field_confidence(ocr_c, 0.90),
                requires_review=req_rev,
                review_reason=rev_reason,
                source=prov,
            )
        else:
            fields["annual_income"] = ExtractedField(
                field_key="annual_income",
                field_name="Annual Family Income (INR)",
                raw_value=None,
                normalized_value=None,
                field_type="number",
                confidence=0.0,
                requires_review=True,
                review_reason="Field not detected in OCR output",
                source=FieldSourceProvenance(document_version=doc_version),
            )

        # 3. Certificate Number
        cert_match = re.search(
            r"(?:CERTIFICATE NO|CERT NO|REF NO|DOC NO)\s*[:\-]?\s*([A-Z0-9\-\/]{6,25})",
            raw_text,
            re.IGNORECASE,
        )
        if cert_match:
            raw_val = cert_match.group(1).strip()
            prov = find_ocr_blocks_for_text(raw_val, blocks, doc_version, cert_match.group(0))
            ocr_c = extract_mean_block_confidence(prov, blocks)
            fields["certificate_number"] = ExtractedField(
                field_key="certificate_number",
                field_name="Certificate Number",
                raw_value=raw_val,
                normalized_value=raw_val.upper(),
                field_type="string",
                confidence=calculate_field_confidence(ocr_c, 0.95),
                requires_review=False,
                source=prov,
            )

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
            metadata={"source": "Income Certificate extraction engine"},
        )


class FirstGraduateCertificateExtractor(FieldExtractor):
    """
    Extractor for First Graduate Certificates & Joint Declarations.
    """

    DOCUMENT_TYPE = "FIRST_GRADUATE_CERTIFICATE"
    ENGINE_NAME = "FirstGraduateCertificateExtractor"
    ENGINE_VERSION = "1.0.0-fg"

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

        name_match = re.search(
            r"(?:THIS IS TO CERTIFY THAT|NAME OF APPLICANT|SELVI|THIRU|NAME)\s*[:\-]?\s*([A-Z\s\.]{3,50})",
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

        cert_match = re.search(
            r"(?:CERTIFICATE NO|CERT NO|REF NO|DOC NO)\s*[:\-]?\s*([A-Z0-9\-\/]{6,25})",
            raw_text,
            re.IGNORECASE,
        )
        if cert_match:
            raw_val = cert_match.group(1).strip()
            prov = find_ocr_blocks_for_text(raw_val, blocks, doc_version, cert_match.group(0))
            ocr_c = extract_mean_block_confidence(prov, blocks)
            fields["certificate_number"] = ExtractedField(
                field_key="certificate_number",
                field_name="Certificate Number",
                raw_value=raw_val,
                normalized_value=raw_val.upper(),
                field_type="string",
                confidence=calculate_field_confidence(ocr_c, 0.95),
                requires_review=False,
                source=prov,
            )

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
            metadata={"source": "First Graduate extraction engine"},
        )
