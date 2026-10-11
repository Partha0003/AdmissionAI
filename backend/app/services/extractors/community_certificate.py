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
    normalize_community,
    normalize_date,
)


class CommunityCertificateExtractor(FieldExtractor):
    """
    Modular extractor for Tamil Nadu Permanent Community Certificate Cards.
    Extracts candidate name, parent/guardian name, community category (OC/BC/BCM/MBC/SC/SCA/ST),
    caste/sub-caste, certificate number, issuing authority, and issue date.
    """

    DOCUMENT_TYPE = "COMMUNITY_CERTIFICATE"
    ENGINE_NAME = "CommunityCertificateExtractor"
    ENGINE_VERSION = "1.0.0-comm"

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

        # 1. Candidate Name / This is to certify that
        name_match = re.search(
            r"(?:THIS IS TO CERTIFY THAT|NAME OF APPLICANT|NAME|SELVI|THIRU|KUMAR)\s*[:\-]?\s*([A-Za-z\.\t ]{2,50})",
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

        # 2. Father / Guardian Name
        father_match = re.search(
            r"(?:SON OF|DAUGHTER OF|S\/O|D\/O|FATHER NAME|PARENT NAME)\s*[:\-]?\s*([A-Za-z\.\t ]{2,50})",
            raw_text,
            re.IGNORECASE,
        )
        if father_match:
            raw_val = father_match.group(1).strip()
            prov = find_ocr_blocks_for_text(raw_val, blocks, doc_version, father_match.group(0))
            ocr_c = extract_mean_block_confidence(prov, blocks)
            fields["father_name"] = ExtractedField(
                field_key="father_name",
                field_name="Father / Guardian Name",
                raw_value=raw_val,
                normalized_value=raw_val.upper(),
                field_type="string",
                confidence=calculate_field_confidence(ocr_c, 0.90),
                requires_review=False,
                source=prov,
            )
        else:
            fields["father_name"] = ExtractedField(
                field_key="father_name",
                field_name="Father / Guardian Name",
                raw_value=None,
                normalized_value=None,
                field_type="string",
                confidence=0.0,
                requires_review=True,
                review_reason="Field not detected in OCR output",
                source=FieldSourceProvenance(document_version=doc_version),
            )

        # 3. Community Category (OC / BC / BCM / MBC / SC / SCA / ST)
        comm_match = re.search(
            r"(?:COMMUNITY|BELONGS TO|CASTE CATEGORY|CATEGORY)\s*[:\-]?\s*([A-Za-z0-9\/\_\&\(\)\t ]{2,40})",
            raw_text,
            re.IGNORECASE,
        )

        if comm_match:
            raw_val = comm_match.group(1).strip()
            norm_comm, req_rev, rev_reason = normalize_community(raw_val)
            prov = find_ocr_blocks_for_text(raw_val, blocks, doc_version, comm_match.group(0))
            ocr_c = extract_mean_block_confidence(prov, blocks)
            fields["community"] = ExtractedField(
                field_key="community",
                field_name="Community Category",
                raw_value=raw_val,
                normalized_value=norm_comm,
                field_type="category",
                confidence=calculate_field_confidence(ocr_c, 0.95),
                requires_review=req_rev,
                review_reason=rev_reason,
                source=prov,
            )
        else:
            # Try searching individual direct tokens
            token_match = re.search(r"\b(MBC[_\s/]?DNC|MBC|BCM|BC|SCA|SC|ST|OC)\b", raw_text, re.IGNORECASE)
            if token_match:
                raw_val = token_match.group(1).strip()
                norm_comm, req_rev, rev_reason = normalize_community(raw_val)
                prov = find_ocr_blocks_for_text(raw_val, blocks, doc_version, token_match.group(0))
                ocr_c = extract_mean_block_confidence(prov, blocks)
                fields["community"] = ExtractedField(
                    field_key="community",
                    field_name="Community Category",
                    raw_value=raw_val,
                    normalized_value=norm_comm,
                    field_type="category",
                    confidence=calculate_field_confidence(ocr_c, 0.85),
                    requires_review=req_rev,
                    review_reason=rev_reason,
                    source=prov,
                )
            else:
                fields["community"] = ExtractedField(
                    field_key="community",
                    field_name="Community Category",
                    raw_value=None,
                    normalized_value=None,
                    field_type="category",
                    confidence=0.0,
                    requires_review=True,
                    review_reason="Field not detected in OCR output",
                    source=FieldSourceProvenance(document_version=doc_version),
                )

        # 4. Certificate Number
        cert_match = re.search(
            r"(?:CERTIFICATE NO|CERTIFICATE NUMBER|CERT NO|DOC NO|REF NO|G\.O|TN\d{8,14})\s*[:\-]?\s*([A-Z0-9\-\/]{6,25})",
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
        else:
            fields["certificate_number"] = ExtractedField(
                field_key="certificate_number",
                field_name="Certificate Number",
                raw_value=None,
                normalized_value=None,
                field_type="string",
                confidence=0.0,
                requires_review=True,
                review_reason="Field not detected in OCR output",
                source=FieldSourceProvenance(document_version=doc_version),
            )

        # 5. Issuing Authority
        auth_match = re.search(
            r"(?:ISSUING AUTHORITY|DESIGNATION|ISSUED BY|TAHSILDAR|ZONAL DEPUTY TAHSILDAR|REVENUE DIVISIONAL OFFICER)\s*[:\-]?\s*([A-Z\s\,\.]{4,60})",
            raw_text,
            re.IGNORECASE,
        )
        if auth_match:
            raw_val = auth_match.group(0).strip()
            prov = find_ocr_blocks_for_text(raw_val, blocks, doc_version, auth_match.group(0))
            ocr_c = extract_mean_block_confidence(prov, blocks)
            fields["issuing_authority"] = ExtractedField(
                field_key="issuing_authority",
                field_name="Issuing Authority",
                raw_value=raw_val,
                normalized_value=raw_val.title(),
                field_type="string",
                confidence=calculate_field_confidence(ocr_c, 0.90),
                requires_review=False,
                source=prov,
            )

        # 6. Issue Date
        date_match = re.search(
            r"(?:DATE OF ISSUE|DATE|ISSUED ON|DATED)\s*[:\-]?\s*([0-9]{1,4}[\/\-\.][0-9]{1,2}[\/\-\.][0-9]{2,4})",
            raw_text,
            re.IGNORECASE,
        )
        if date_match:
            raw_val = date_match.group(1).strip()
            norm_dt, req_rev, rev_reason = normalize_date(raw_val)
            prov = find_ocr_blocks_for_text(raw_val, blocks, doc_version, date_match.group(0))
            ocr_c = extract_mean_block_confidence(prov, blocks)
            fields["issue_date"] = ExtractedField(
                field_key="issue_date",
                field_name="Issue Date",
                raw_value=raw_val,
                normalized_value=norm_dt,
                field_type="date",
                confidence=calculate_field_confidence(ocr_c, 0.90),
                requires_review=req_rev,
                review_reason=rev_reason,
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
            metadata={"source": "Community Certificate extraction engine"},
        )
