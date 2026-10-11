from __future__ import annotations

from typing import Dict, Any, List, Optional
from app.services.reconciliation.base import ComparisonRule, RuleResult, ReconciliationFinding
from app.services.reconciliation.utils import compare_names, build_provenance_from_extracted_field


class NameConsistencyRule(ComparisonRule):
    """
    Compares candidate name across:
    1. Declared Application Draft name
    2. Stored TNEA Allotment Baseline name
    3. 12th Marksheet extracted candidate_name
    4. 10th Marksheet extracted candidate_name
    5. Community Certificate extracted candidate_name
    """

    RULE_ID = "RULE_NAME_CONSISTENCY"
    RULE_NAME = "Candidate Name Multi-Document Consistency"

    @property
    def rule_id(self) -> str:
        return self.RULE_ID

    @property
    def rule_name(self) -> str:
        return self.RULE_NAME

    def evaluate(
        self,
        application_data: Dict[str, Any],
        allotment_baseline: Optional[Dict[str, Any]],
        extractions: Dict[str, Dict[str, Any]],
    ) -> RuleResult:
        declared_name = application_data.get("student_name")
        allotment_name = allotment_baseline.get("candidate_name") if allotment_baseline else None

        findings: List[ReconciliationFinding] = []

        # 1. Declared vs Allotment Baseline Name
        if declared_name and allotment_name:
            status, reason = compare_names(declared_name, allotment_name)
            findings.append(
                ReconciliationFinding(
                    rule_id=self.rule_id,
                    rule_name="Declared vs Allotment Baseline Name",
                    field_key="student_name",
                    status=status,
                    declared_value=declared_name,
                    extracted_value=None,
                    allotment_baseline_value=allotment_name,
                    discrepancy_reason=reason if status == "DISCREPANCY" else None,
                    human_review_required=(status in ["DISCREPANCY", "PENDING_SCRUTINY"]),
                    review_reason=reason if status == "PENDING_SCRUTINY" else None,
                )
            )

        # Helper to compare declared vs extracted doc field
        doc_targets = [
            ("TWELFTH_MARKSHEET", "candidate_name", "12th Marksheet Name"),
            ("TENTH_MARKSHEET", "candidate_name", "10th Marksheet Name"),
            ("COMMUNITY_CERTIFICATE", "candidate_name", "Community Certificate Name"),
            ("ALLOTMENT_ORDER", "candidate_name", "Allotment Order Document Name"),
        ]

        for doc_type, field_key, label in doc_targets:
            doc_ext = extractions.get(doc_type)
            if doc_ext and "fields" in doc_ext:
                field_dict = doc_ext["fields"].get(field_key)
                if field_dict and field_dict.get("normalized_value"):
                    extracted_name = field_dict.get("normalized_value")
                    status, reason = compare_names(declared_name, extracted_name)
                    prov = build_provenance_from_extracted_field(field_dict, doc_ext.get("meta"))
                    findings.append(
                        ReconciliationFinding(
                            rule_id=self.rule_id,
                            rule_name=f"Declared vs {label}",
                            field_key=f"{doc_type.lower()}_{field_key}",
                            status=status,
                            declared_value=declared_name,
                            extracted_value=extracted_name,
                            allotment_baseline_value=allotment_name,
                            discrepancy_reason=reason if status == "DISCREPANCY" else None,
                            human_review_required=(status in ["DISCREPANCY", "PENDING_SCRUTINY"]),
                            review_reason=reason if status == "PENDING_SCRUTINY" else None,
                            provenance=prov,
                        )
                    )
                else:
                    findings.append(
                        ReconciliationFinding(
                            rule_id=self.rule_id,
                            rule_name=f"Declared vs {label}",
                            field_key=f"{doc_type.lower()}_{field_key}",
                            status="INCOMPLETE_DOCUMENTS",
                            declared_value=declared_name,
                            extracted_value=None,
                            allotment_baseline_value=allotment_name,
                            review_reason=f"Candidate name not detected or missing in {label}",
                        )
                    )

        # Determine aggregate status
        if any(f.status == "PENDING_SCRUTINY" for f in findings):
            overall_st = "PENDING_SCRUTINY"
        elif any(f.status == "DISCREPANCY" for f in findings):
            overall_st = "DISCREPANCY"
        elif any(f.status == "INCOMPLETE_DOCUMENTS" for f in findings) and not any(f.status == "MATCH" for f in findings):
            overall_st = "INCOMPLETE_DOCUMENTS"
        else:
            overall_st = "MATCH"

        return RuleResult(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            status=overall_st,
            findings=findings,
            requires_human_review=(overall_st in ["PENDING_SCRUTINY", "DISCREPANCY"]),
            summary=f"Evaluated {len(findings)} name comparisons across documents and baseline.",
        )
