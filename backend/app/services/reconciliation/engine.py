from __future__ import annotations

import time
from typing import Dict, Any, List, Optional
from app.services.reconciliation.base import ComparisonRule, RuleResult, ReconciliationFinding
from app.services.reconciliation.rules.name_rule import NameConsistencyRule
from app.services.reconciliation.rules.cutoff_rule import AcademicCutoffRule
from app.services.reconciliation.rules.community_rule import CommunityQuotaRule
from app.services.reconciliation.rules.income_rule import IncomeRule
from app.services.reconciliation.rules.first_graduate_rule import FirstGraduateRule
from app.services.reconciliation.rules.parent_rule import ParentNameRule
from app.services.reconciliation.rules.identifier_rule import IdentifierRule


class CrossDocumentReconciler:
    """
    Coordinator engine executing deterministic multi-document consistency reconciliation.
    Evaluates rule hierarchy and computes precedence-ordered overall status.
    """

    def __init__(self, rules: Optional[List[ComparisonRule]] = None):
        self.rules: List[ComparisonRule] = rules or [
            NameConsistencyRule(),
            AcademicCutoffRule(),
            CommunityQuotaRule(),
            IncomeRule(),
            FirstGraduateRule(),
            ParentNameRule(),
            IdentifierRule(),
        ]

    def reconcile(
        self,
        application_data: Dict[str, Any],
        allotment_baseline: Optional[Dict[str, Any]],
        extractions: Dict[str, Dict[str, Any]],
        participating_versions: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        start_time = time.time()

        all_findings: List[ReconciliationFinding] = []
        rule_results: List[RuleResult] = []
        discrepancy_summary: Dict[str, str] = {}

        total_rules = len(self.rules)
        passed_count = 0
        discrepancy_count = 0
        pending_scrutiny_count = 0
        incomplete_count = 0

        for rule in self.rules:
            res = rule.evaluate(application_data, allotment_baseline, extractions)
            rule_results.append(res)
            all_findings.extend(res.findings)

            if res.status == "MATCH":
                passed_count += 1
            elif res.status == "DISCREPANCY":
                discrepancy_count += 1
                for f in res.findings:
                    if f.status == "DISCREPANCY" and f.discrepancy_reason:
                        discrepancy_summary[f.field_key] = f.discrepancy_reason
            elif res.status == "PENDING_SCRUTINY":
                pending_scrutiny_count += 1
                for f in res.findings:
                    if f.status == "PENDING_SCRUTINY" and f.review_reason:
                        discrepancy_summary[f.field_key] = f.review_reason
            elif res.status == "INCOMPLETE_DOCUMENTS":
                incomplete_count += 1

        # Deterministic Status Precedence Hierarchy:
        # PENDING_SCRUTINY > DISCREPANCY_DETECTED > INCOMPLETE_DOCUMENTS > MATCH
        if pending_scrutiny_count > 0 or any(f.status == "PENDING_SCRUTINY" for f in all_findings):
            overall_status = "PENDING_SCRUTINY"
        elif discrepancy_count > 0 or any(f.status == "DISCREPANCY" for f in all_findings):
            overall_status = "DISCREPANCY_DETECTED"
        elif incomplete_count > 0 or any(f.status == "INCOMPLETE_DOCUMENTS" for f in all_findings):
            overall_status = "INCOMPLETE_DOCUMENTS"
        else:
            overall_status = "MATCH"

        requires_human_review = overall_status != "MATCH"
        duration_ms = int((time.time() - start_time) * 1000)

        return {
            "overall_status": overall_status,
            "participating_document_versions": participating_versions or {},
            "total_rules_evaluated": total_rules,
            "passed_rules_count": passed_count,
            "discrepancy_count": discrepancy_count,
            "pending_scrutiny_count": pending_scrutiny_count,
            "incomplete_count": incomplete_count,
            "findings": [f.to_dict() for f in all_findings],
            "discrepancy_summary": discrepancy_summary,
            "requires_human_review": requires_human_review,
            "reconciliation_time_ms": duration_ms,
        }
