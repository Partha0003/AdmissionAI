from __future__ import annotations

import re
from datetime import datetime, date
from typing import Dict, Any, List, Optional, Tuple, Union
from app.services.extractors.base import FieldSourceProvenance, ExtractedField


def calculate_field_confidence(
    ocr_word_confidence: float,
    pattern_certainty_score: float = 1.0,
) -> float:
    """
    Deterministic heuristic confidence calculation formula:
    field_confidence = clamp(0.6 * OCR_word_confidence + 0.4 * pattern_certainty_score, 0.0, 1.0)
    """
    ocr_conf = max(0.0, min(1.0, float(ocr_word_confidence)))
    pattern_conf = max(0.0, min(1.0, float(pattern_certainty_score)))
    score = (0.6 * ocr_conf) + (0.4 * pattern_conf)
    return round(max(0.0, min(1.0, score)), 4)


def find_ocr_blocks_for_text(
    target_substring: str,
    blocks: List[Dict[str, Any]],
    document_version: int = 1,
    full_context_line: Optional[str] = None,
) -> FieldSourceProvenance:
    """
    Finds OCR block indices and calculates the enclosing bounding box union
    for a matched substring across OCR blocks.
    """
    if not target_substring or not blocks:
        return FieldSourceProvenance(
            ocr_block_indices=[],
            bounding_box=None,
            context=full_context_line,
            document_version=document_version,
        )

    target_clean = target_substring.strip().lower()
    target_words = set(re.findall(r"\w+", target_clean))

    matched_indices: List[int] = []
    matched_boxes: List[Dict[str, int]] = []
    matched_confidences: List[float] = []

    for idx, block in enumerate(blocks):
        b_text = block.get("text", "").strip().lower()
        if not b_text:
            continue
        
        b_words = set(re.findall(r"\w+", b_text))
        # Match if block text contains target or shares words
        if target_clean in b_text or b_text in target_clean or (target_words and target_words.intersection(b_words)):
            matched_indices.append(idx)
            box = block.get("box")
            if box and isinstance(box, dict):
                matched_boxes.append(box)
            if "confidence" in block and block["confidence"] is not None:
                matched_confidences.append(float(block["confidence"]))

    if not matched_boxes:
        return FieldSourceProvenance(
            ocr_block_indices=matched_indices,
            bounding_box=None,
            context=full_context_line,
            document_version=document_version,
        )

    # Compute enclosing bounding box union in preprocessed coordinates [x, y, width, height]
    min_x = min(b.get("x", 0) for b in matched_boxes)
    min_y = min(b.get("y", 0) for b in matched_boxes)
    max_x = max(b.get("x", 0) + b.get("width", 0) for b in matched_boxes)
    max_y = max(b.get("y", 0) + b.get("height", 0) for b in matched_boxes)

    union_box = {
        "x": int(min_x),
        "y": int(min_y),
        "width": int(max(0, max_x - min_x)),
        "height": int(max(0, max_y - min_y)),
    }

    return FieldSourceProvenance(
        ocr_block_indices=matched_indices,
        bounding_box=union_box,
        context=full_context_line,
        document_version=document_version,
    )


def extract_mean_block_confidence(
    provenance: FieldSourceProvenance,
    blocks: List[Dict[str, Any]],
    fallback_confidence: float = 0.85,
) -> float:
    """
    Computes average OCR confidence for matched blocks.
    """
    if not provenance.ocr_block_indices or not blocks:
        return fallback_confidence

    confs = []
    for idx in provenance.ocr_block_indices:
        if 0 <= idx < len(blocks):
            c = blocks[idx].get("confidence")
            if c is not None:
                confs.append(float(c))

    if not confs:
        return fallback_confidence
    return sum(confs) / len(confs)


def normalize_date(date_str: str) -> Tuple[Optional[str], bool, Optional[str]]:
    """
    Safely parses and normalizes dates into ISO-8601 (YYYY-MM-DD).
    Returns (normalized_value, requires_review, review_reason).
    """
    if not date_str:
        return None, True, "Date string is empty"

    cleaned = date_str.strip()

    # Ambiguity check: 2-digit year like '01/02/05'
    if re.match(r"^\d{1,2}[/-]\d{1,2}[/-]\d{2}$", cleaned):
        return None, True, f"Ambiguous 2-digit year in date format '{cleaned}' — unable to reliably infer century"

    # Try ISO YYYY-MM-DD
    iso_match = re.match(r"^(\d{4})[/-](\d{1,2})[/-](\d{1,2})$", cleaned)
    if iso_match:
        y, m, d = int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3))
        try:
            val = date(y, m, d).isoformat()
            return val, False, None
        except ValueError:
            return None, True, f"Invalid date components in '{cleaned}'"

    # Try DD/MM/YYYY or DD-MM-YYYY
    dmy_match = re.match(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$", cleaned)
    if dmy_match:
        d, m, y = int(dmy_match.group(1)), int(dmy_match.group(2)), int(dmy_match.group(3))
        try:
            val = date(y, m, d).isoformat()
            return val, False, None
        except ValueError:
            return None, True, f"Invalid date components in '{cleaned}'"

    # Unparseable format
    return None, True, f"Unrecognized date format '{cleaned}'"


def normalize_number(num_str: str) -> Tuple[Optional[float], bool, Optional[str]]:
    """
    Safely normalizes numeric strings.
    """
    if not num_str:
        return None, True, "Number string is empty"
    cleaned = num_str.strip().replace(",", "")
    try:
        val = float(cleaned)
        return val, False, None
    except ValueError:
        return None, True, f"Unable to parse numeric value from '{num_str}'"


def normalize_community(comm_str: str) -> Tuple[Optional[str], bool, Optional[str]]:
    """
    Normalizes Tamil Nadu community category abbreviations.
    """
    if not comm_str:
        return None, True, "Community string is empty"

    clean = comm_str.strip().upper().replace(" ", "_").replace("/", "_")
    valid_map = {
        "OC": "OC",
        "OPEN": "OC",
        "GENERAL": "OC",
        "BC": "BC",
        "BC_OTHERS": "BC",
        "BCM": "BCM",
        "BC_MUSLIM": "BCM",
        "MBC": "MBC",
        "MBC_DNC": "MBC_DNC",
        "MBC&DNC": "MBC_DNC",
        "DNC": "MBC_DNC",
        "SC": "SC",
        "SCA": "SCA",
        "SC_ARUNTHATHIYAR": "SCA",
        "ST": "ST",
    }

    if clean in valid_map:
        return valid_map[clean], False, None

    for k, v in valid_map.items():
        if k in clean:
            return v, False, None

    return None, True, f"Unrecognized community category '{comm_str}'"
