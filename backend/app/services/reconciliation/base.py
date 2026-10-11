from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


@dataclass
class ReconciliationFindingProvenance:
    document_id: Optional[str] = None
    document_version: Optional[int] = None
    extraction_result_id: Optional[str] = None
    extracted_field_key: Optional[str] = None
    ocr_block_indices: List[int] = field(default_factory=list)
    bounding_box: Optional[Dict[str, int]] = None
    comparison_method: str = "EXACT_NORMALIZED"
    tolerance_applied: Optional[str] = None


@dataclass
class ReconciliationFinding:
    rule_id: str
    rule_name: str
    field_key: str
    status: str  # MATCH | DISCREPANCY | PENDING_SCRUTINY | INCOMPLETE_DOCUMENTS
    declared_value: Any = None
    extracted_value: Any = None
    allotment_baseline_value: Any = None
    delta: Optional[Any] = None
    discrepancy_reason: Optional[str] = None
    human_review_required: bool = False
    review_reason: Optional[str] = None
    provenance: Optional[ReconciliationFindingProvenance] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "field_key": self.field_key,
            "status": self.status,
            "declared_value": self.declared_value,
            "extracted_value": self.extracted_value,
            "allotment_baseline_value": self.allotment_baseline_value,
            "delta": self.delta,
            "discrepancy_reason": self.discrepancy_reason,
            "human_review_required": self.human_review_required,
            "review_reason": self.review_reason,
            "provenance": {
                "document_id": self.provenance.document_id,
                "document_version": self.provenance.document_version,
                "extraction_result_id": self.provenance.extraction_result_id,
                "extracted_field_key": self.provenance.extracted_field_key,
                "ocr_block_indices": self.provenance.ocr_block_indices,
                "bounding_box": self.provenance.bounding_box,
                "comparison_method": self.provenance.comparison_method,
                "tolerance_applied": self.provenance.tolerance_applied,
            }
            if self.provenance
            else None,
        }


@dataclass
class RuleResult:
    rule_id: str
    rule_name: str
    status: str  # MATCH | DISCREPANCY | PENDING_SCRUTINY | INCOMPLETE_DOCUMENTS
    findings: List[ReconciliationFinding] = field(default_factory=list)
    requires_human_review: bool = False
    summary: Optional[str] = None


class ComparisonRule(ABC):
    """
    Abstract base class for deterministic cross-document reconciliation rules.
    """

    @property
    @abstractmethod
    def rule_id(self) -> str:
        pass

    @property
    @abstractmethod
    def rule_name(self) -> str:
        pass

    @abstractmethod
    def evaluate(
        self,
        application_data: Dict[str, Any],
        allotment_baseline: Optional[Dict[str, Any]],
        extractions: Dict[str, Dict[str, Any]],  # doc_type_code -> extraction_dict
    ) -> RuleResult:
        """
        Executes deterministic rule comparison.
        """
        pass
