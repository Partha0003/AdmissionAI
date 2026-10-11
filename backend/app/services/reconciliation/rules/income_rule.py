from __future__ import annotations

from typing import Dict, Any, List, Optional
from app.services.reconciliation.base import ComparisonRule, RuleResult, ReconciliationFinding
from app.services.reconciliation.utils import build_provenance_from_extracted_field


class IncomeRule(ComparisonRule):
    """
    Compares declared Annual Family Income vs Income Certificate extracted income.
    Tolerance: Exact integer equality (abs(declared - cert) == 0).
    """

    RULE_ID = "RULE_INCOME_CONSISTENCY"
    RULE_NAME = "Annual Family Income Consistency"

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
        findings: List[ReconciliationFinding] = []

        declared_income = application_data.get("annual_family_income")
        income_ext = extractions.get("INCOME_CERTIFICATE")

        if income_ext and "fields" in income_ext:
            field_d = income_ext["fields"].get("annual_income")
            if field_d and field_d.get("normalized_value") is not None:
                ext_income = int(field_d["normalized_value"])
                prov = build_provenance_from_extracted_field(
                    field_d,
                    income_ext.get("meta"),
                    comparison_method="EXACT_INTEGER",
                    tolerance_applied="diff == 0",
                )

                if declared_income is not None:
                    decl_int = int(declared_income)
                    diff = abs(decl_int - ext_income)
                    if diff == 0:
                        status = "MATCH"
                        disc_reason = None
                    else:
                        status = "DISCREPANCY"
                        disc_reason = f"Declared annual income (Rs. {decl_int:,}) differs from certificate income (Rs. {ext_income:,}) by delta Rs. {diff:,}"
                else:
                    status = "PENDING_SCRUTINY"
                    diff = None
                    disc_reason = "Declared income value not provided in form"

                findings.append(
                    ReconciliationFinding(
                        rule_id=self.rule_id,
                        rule_name="Declared Income vs Income Certificate Extracted Amount",
                        field_key="annual_family_income",
                        status=status,
                        declared_value=declared_income,
                        extracted_value=ext_income,
                        delta=diff,
                        discrepancy_reason=disc_reason,
                        human_review_required=(status in ["DISCREPANCY", "PENDING_SCRUTINY"]),
                        provenance=prov,
                    )
                )
            else:
                findings.append(
                    ReconciliationFinding(
                        rule_id=self.rule_id,
                        rule_name="Declared Income vs Income Certificate Extracted Amount",
                        field_key="annual_family_income",
                        status="INCOMPLETE_DOCUMENTS",
                        declared_value=declared_income,
                        extracted_value=None,
                        review_reason="Income certificate uploaded but income amount not extracted",
                    )
                )

        if not findings:
            return RuleResult(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                status="MATCH" if declared_income is None else "INCOMPLETE_DOCUMENTS",
                findings=[],
                summary="No income certificate uploaded to evaluate.",
            )

        overall_st = findings[0].status
        return RuleResult(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            status=overall_st,
            findings=findings,
            requires_human_review=(overall_st in ["DISCREPANCY", "PENDING_SCRUTINY"]),
            summary=f"Evaluated annual family income consistency ({findings[0].status}).",
        )
