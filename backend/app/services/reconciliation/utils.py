from __future__ import annotations

import re
from typing import Dict, Any, List, Optional, Tuple, Set
from app.services.reconciliation.base import ReconciliationFindingProvenance


# Explicit prototype mapping table between TNEA Allotted Quota and declared / certificate community categories
COMMUNITY_QUOTA_PROTOTYPE_MAP: Dict[str, Set[str]] = {
    "OC": {"OC", "BC", "BCM", "MBC", "SC", "SCA", "ST"},
    "BC": {"BC"},
    "BCM": {"BCM"},
    "MBC": {"MBC", "MBC/DNC", "MBC_DNC"},
    "MBC/DNC": {"MBC", "MBC/DNC", "MBC_DNC"},
    "MBC_DNC": {"MBC", "MBC/DNC", "MBC_DNC"},
    "SC": {"SC"},
    "SCA": {"SCA"},
    "ST": {"ST"},
}


def normalize_string(val: Optional[str]) -> str:
    """Trims, uppercases, and collapses whitespace."""
    if not val:
        return ""
    cleaned = re.sub(r"\s+", " ", str(val).strip().upper())
    return cleaned


def normalize_name_tokens(name: Optional[str]) -> Tuple[Set[str], List[str], str]:
    """
    Deterministic Tamil Nadu name normalization pipeline:
    1. Trim & uppercase
    2. Strip punctuation (. , - /)
    3. Collapse whitespace
    4. Extract single-letter initial tokens vs core name words
    Returns: (core_tokens_set, initials_list, canonical_string)
    """
    if not name:
        return set(), [], ""
    raw = str(name).upper()
    # Strip dots, commas, hyphens
    cleaned = re.sub(r"[\.,\-\/\_]", " ", raw)
    tokens = [t.strip() for t in cleaned.split() if t.strip()]

    initials: List[str] = []
    core_tokens: Set[str] = set()

    for t in tokens:
        if len(t) == 1 and t.isalpha():
            initials.append(t)
        elif len(t) > 1:
            core_tokens.add(t)

    canonical = " ".join(sorted(list(core_tokens)) + sorted(initials))
    return core_tokens, sorted(initials), canonical


def compare_names(name1: Optional[str], name2: Optional[str]) -> Tuple[str, Optional[str]]:
    """
    Deterministic comparison between two names:
    - MATCH: Exact normalized token and initial equivalence (e.g., 'S. KARTHIKEYAN' == 'KARTHIKEYAN S').
    - PENDING_SCRUTINY: Shared core token but missing/mismatched initials or partial subset requiring human review.
    - DISCREPANCY: Completely disjoint core tokens.
    """
    if not name1 or not name2:
        return "INCOMPLETE_DOCUMENTS", "One or both names missing from source"

    core1, init1, canon1 = normalize_name_tokens(name1)
    core2, init2, canon2 = normalize_name_tokens(name2)

    if not core1 or not core2:
        return "INCOMPLETE_DOCUMENTS", "Unparseable name tokens"

    # Exact canonical match
    if canon1 == canon2 or (core1 == core2 and init1 == init2):
        return "MATCH", None

    # Exact core token match but one side has extra or missing initial
    if core1 == core2:
        return "PENDING_SCRUTINY", f"Core names match ('{' '.join(core1)}') but initials differ: '{'.'.join(init1)}' vs '{'.'.join(init2)}'"

    # Substring / partial token overlap
    overlap = core1.intersection(core2)
    if overlap:
        return "PENDING_SCRUTINY", f"Partial name token overlap ({' '.join(overlap)}) between '{name1}' and '{name2}'"

    return "DISCREPANCY", f"Names are completely distinct: '{name1}' vs '{name2}'"


def build_provenance_from_extracted_field(
    field_dict: Optional[Dict[str, Any]],
    doc_meta: Optional[Dict[str, Any]],
    comparison_method: str = "EXACT_NORMALIZED",
    tolerance_applied: Optional[str] = None,
) -> Optional[ReconciliationFindingProvenance]:
    """Extracts Phase 4D provenance details from an extracted field dictionary."""
    if not field_dict:
        return None
    
    prov_data = field_dict.get("provenance") or field_dict.get("source") or {}
    return ReconciliationFindingProvenance(
        document_id=doc_meta.get("document_id") if doc_meta else None,
        document_version=doc_meta.get("document_version") if doc_meta else None,
        extraction_result_id=doc_meta.get("extraction_result_id") if doc_meta else None,
        extracted_field_key=field_dict.get("field_key") or field_dict.get("field_name"),
        ocr_block_indices=prov_data.get("ocr_block_indices", []),
        bounding_box=prov_data.get("bounding_box"),
        comparison_method=comparison_method,
        tolerance_applied=tolerance_applied,
    )
