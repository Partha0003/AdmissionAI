import re
from datetime import datetime, timezone
from typing import Dict, List, Tuple
from app.services.classifiers.base import (
    DocumentClassifier,
    DocumentClassificationContext,
    ClassificationResultData,
)


class RuleBasedDocumentClassifier(DocumentClassifier):
    """
    Deterministic rule-based prototype document classifier.
    
    IMPORTANT DISCLAIMER:
    This is a prototype heuristic classifier based on filename and metadata analysis.
    It does NOT perform OCR, computer vision, or machine learning classification.
    Confidence values are deterministic heuristic scores, NOT calibrated statistical probabilities.
    AI processing is assistive and informational only; it does not replace human document verification.
    """

    ENGINE_NAME = "RuleBasedDocumentClassifier"
    ENGINE_VERSION = "1.0.0-prototype"

    # Category name mappings
    CATEGORY_NAMES: Dict[str, str] = {
        "TENTH_MARKSHEET": "10th Marksheet",
        "TWELFTH_MARKSHEET": "12th Marksheet",
        "TRANSFER_CERTIFICATE": "Transfer Certificate",
        "ALLOTMENT_ORDER": "TNEA Allotment Order",
        "COMMUNITY_CERTIFICATE": "Community Certificate",
        "FIRST_GRADUATE_CERTIFICATE": "First Graduate Certificate",
        "INCOME_CERTIFICATE": "Income Certificate",
        "NATIVITY_CERTIFICATE": "Nativity Certificate",
        "SPECIAL_RESERVATION_CERTIFICATE": "Special Reservation Certificate",
        "DIPLOMA_CERTIFICATE": "Diploma Certificate",
    }

    # Deterministic keyword patterns for heuristic matching
    KEYWORD_RULES: List[Tuple[str, List[str]]] = [
        ("TENTH_MARKSHEET", [r"\b10th\b", r"\btenth\b", r"\bsslc\b", r"\bmatric\b", r"10_mark", r"tenth_mark"]),
        ("TWELFTH_MARKSHEET", [r"\b12th\b", r"\btwelfth\b", r"\bhsc\b", r"\bplus2\b", r"\bplus_two\b", r"\+2\b", r"12_mark", r"twelfth_mark"]),
        ("TRANSFER_CERTIFICATE", [r"\btc\b", r"\btransfer\b", r"transfer_cert", r"\bleaving\b"]),
        ("ALLOTMENT_ORDER", [r"\ballotment\b", r"\btnea\b", r"allotment_order"]),
        ("COMMUNITY_CERTIFICATE", [r"\bcommunity\b", r"\bcaste\b", r"community_cert", r"caste_cert"]),
        ("FIRST_GRADUATE_CERTIFICATE", [r"\bfirst_grad\b", r"\bfirstgraduate\b", r"\bfg\b", r"first_graduate"]),
        ("INCOME_CERTIFICATE", [r"\bincome\b", r"\bvarumanam\b", r"income_cert", r"\bpmss\b", r"\bsalary\b"]),
        ("NATIVITY_CERTIFICATE", [r"\bnativity\b", r"\bresidence\b", r"\bdomicile\b", r"nativity_cert"]),
        ("SPECIAL_RESERVATION_CERTIFICATE", [r"\bspecial\b", r"\b7\.5\b", r"7_5", r"\bsports\b", r"\bpwd\b", r"ex_service"]),
        ("DIPLOMA_CERTIFICATE", [r"\bdiploma\b", r"\bpolytechnic\b", r"\bdme\b", r"\bdce\b", r"\bdeee\b", r"\bdece\b"]),
    ]

    @property
    def name(self) -> str:
        return self.ENGINE_NAME

    @property
    def version(self) -> str:
        return self.ENGINE_VERSION

    async def classify(self, context: DocumentClassificationContext) -> ClassificationResultData:
        filename_lower = context.original_filename.lower()
        cleaned_filename = re.sub(r"[_\-\.]", " ", filename_lower)

        matched_category = None
        matched_rule_pattern = None

        # Test deterministic keyword patterns
        for cat_code, patterns in self.KEYWORD_RULES:
            for pat in patterns:
                if re.search(pat, cleaned_filename, re.IGNORECASE):
                    matched_category = cat_code
                    matched_rule_pattern = pat
                    break
            if matched_category:
                break

        declared_code = context.declared_document_type_code.upper()

        if matched_category:
            if matched_category == declared_code:
                # Strong heuristic match with declared type
                confidence = 0.90
                rule_desc = f"RULE_FILENAME_EXACT_MATCH: '{matched_rule_pattern}' matches declared type '{declared_code}'"
                reasoning = (
                    f"Filename pattern '{context.original_filename}' matches keywords for declared category "
                    f"'{self.CATEGORY_NAMES.get(declared_code, declared_code)}'. Heuristic confidence: High."
                )
                predicted_code = declared_code
            else:
                # Heuristic keyword match suggests a category different from declared
                confidence = 0.75
                rule_desc = f"RULE_FILENAME_MISMATCH: '{matched_rule_pattern}' indicates '{matched_category}', declared is '{declared_code}'"
                reasoning = (
                    f"Filename pattern '{context.original_filename}' contains keywords suggestive of "
                    f"'{self.CATEGORY_NAMES.get(matched_category, matched_category)}', which differs from declared type "
                    f"'{self.CATEGORY_NAMES.get(declared_code, declared_code)}'. Flagged for verifier inspection."
                )
                predicted_code = matched_category
        else:
            # Fallback to declared document type
            confidence = 0.50
            rule_desc = "RULE_DECLARED_TYPE_FALLBACK: No deterministic filename keywords detected"
            reasoning = (
                f"No specific category keywords detected in filename '{context.original_filename}'. "
                f"Assigned default declared category '{self.CATEGORY_NAMES.get(declared_code, declared_code)}' "
                f"with baseline heuristic confidence."
            )
            predicted_code = declared_code

        predicted_name = self.CATEGORY_NAMES.get(predicted_code, context.declared_document_type_name or predicted_code)

        return ClassificationResultData(
            predicted_document_type=predicted_code,
            predicted_document_type_name=predicted_name,
            confidence=confidence,
            confidence_type="heuristic_confidence",
            classifier_name=self.ENGINE_NAME,
            classifier_version=self.ENGINE_VERSION,
            rule_used=rule_desc,
            reasoning=reasoning,
            raw_metadata={
                "original_filename": context.original_filename,
                "declared_type": declared_code,
                "mime_type": context.mime_type,
                "file_size_bytes": context.file_size,
                "prototype_note": "Rule-based prototype classifier (filename heuristic). Not ML calibrated.",
            },
            processed_at=datetime.now(timezone.utc),
        )
