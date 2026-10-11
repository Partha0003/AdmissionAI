from __future__ import annotations

from typing import Dict, Any, List, Optional
from app.services.reconciliation.base import ComparisonRule, RuleResult, ReconciliationFinding
from app.services.reconciliation.utils import normalize_string, build_provenance_from_extracted_field


class IdentifierRule(ComparisonRule):
    """
    Compares strict alphanumeric application & exam registration numbers:
    1. Declared TNEA App No vs Allotment Order extracted TNEA App No vs Allotment Baseline
    2. Declared 12th Registration/Roll No vs 12th Marksheet extracted Roll No
    3. Declared 10th Registration/Roll No vs 10th Marksheet extracted Roll No
    """

    RULE_ID = "RULE_IDENTIFIERS_CONSISTENCY"
    RULE_NAME = "Registration and Application Identifiers Consistency"

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

        decl_tnea = normalize_string(application_data.get("tnea_application_number"))
        base_tnea = normalize_string(allotment_baseline.get("tnea_application_number")) if allotment_baseline else None

        # 1. Declared TNEA App No vs Allotment Baseline
        if decl_tnea and base_tnea:
            if decl_tnea == base_tnea:
                status = "MATCH"
                disc_r = None
            else:
                status = "DISCREPANCY"
                disc_r = f"Declared TNEA application number '{decl_tnea}' differs from allotment baseline '{base_tnea}'"

            findings.append(
                ReconciliationFinding(
                    rule_id=self.rule_id,
                    rule_name="Declared TNEA Number vs Allotment Baseline",
                    field_key="tnea_application_number",
                    status=status,
                    declared_value=decl_tnea,
                    extracted_value=None,
                    allotment_baseline_value=base_tnea,
                    discrepancy_reason=disc_r,
                    human_review_required=(status == "DISCREPANCY"),
                )
            )

        # 2. Declared TNEA App No vs Allotment Order Document
        allot_ext = extractions.get("ALLOTMENT_ORDER")
        if allot_ext and "fields" in allot_ext:
            field_d = allot_ext["fields"].get("tnea_application_number")
            if field_d and field_d.get("normalized_value"):
                ext_tnea = normalize_string(field_d["normalized_value"])
                prov = build_provenance_from_extracted_field(field_d, allot_ext.get("meta"))
                if decl_tnea:
                    if decl_tnea == ext_tnea:
                        status = "MATCH"
                        disc_r = None
                    else:
                        status = "DISCREPANCY"
                        disc_r = f"Declared TNEA number '{decl_tnea}' differs from allotment order document number '{ext_tnea}'"
                else:
                    status = "PENDING_SCRUTINY"
                    disc_r = None

                findings.append(
                    ReconciliationFinding(
                        rule_id=self.rule_id,
                        rule_name="Declared TNEA Number vs Allotment Order Document",
                        field_key="allotment_extracted_tnea_number",
                        status=status,
                        declared_value=decl_tnea,
                        extracted_value=ext_tnea,
                        allotment_baseline_value=base_tnea,
                        discrepancy_reason=disc_r,
                        human_review_required=(status == "DISCREPANCY"),
                        provenance=prov,
                    )
                )

        # 3. 12th Registration Number
        decl_12th = normalize_string(application_data.get("twelfth_registration_number"))
        hsc_ext = extractions.get("TWELFTH_MARKSHEET")
        if hsc_ext and "fields" in hsc_ext:
            field_d = hsc_ext["fields"].get("registration_number")
            if field_d and field_d.get("normalized_value"):
                ext_12th = normalize_string(field_d["normalized_value"])
                prov = build_provenance_from_extracted_field(field_d, hsc_ext.get("meta"))
                if decl_12th:
                    if decl_12th == ext_12th or decl_12th in ext_12th or ext_12th in decl_12th:
                        status = "MATCH"
                        disc_r = None
                    else:
                        status = "DISCREPANCY"
                        disc_r = f"Declared 12th roll number '{decl_12th}' differs from marksheet roll number '{ext_12th}'"
                else:
                    status = "PENDING_SCRUTINY"
                    disc_r = None

                findings.append(
                    ReconciliationFinding(
                        rule_id=self.rule_id,
                        rule_name="Declared 12th Roll Number vs Marksheet",
                        field_key="twelfth_registration_number",
                        status=status,
                        declared_value=decl_12th,
                        extracted_value=ext_12th,
                        discrepancy_reason=disc_r,
                        human_review_required=(status == "DISCREPANCY"),
                        provenance=prov,
                    )
                )

        # 4. 10th Registration Number
        decl_10th = normalize_string(application_data.get("tenth_registration_number"))
        sslc_ext = extractions.get("TENTH_MARKSHEET")
        if sslc_ext and "fields" in sslc_ext:
            field_d = sslc_ext["fields"].get("registration_number")
            if field_d and field_d.get("normalized_value"):
                ext_10th = normalize_string(field_d["normalized_value"])
                prov = build_provenance_from_extracted_field(field_d, sslc_ext.get("meta"))
                if decl_10th:
                    if decl_10th == ext_10th or decl_10th in ext_10th or ext_10th in decl_10th:
                        status = "MATCH"
                        disc_r = None
                    else:
                        status = "DISCREPANCY"
                        disc_r = f"Declared 10th roll number '{decl_10th}' differs from marksheet roll number '{ext_10th}'"
                else:
                    status = "PENDING_SCRUTINY"
                    disc_r = None

                findings.append(
                    ReconciliationFinding(
                        rule_id=self.rule_id,
                        rule_name="Declared 10th Roll Number vs Marksheet",
                        field_key="tenth_registration_number",
                        status=status,
                        declared_value=decl_10th,
                        extracted_value=ext_10th,
                        discrepancy_reason=disc_r,
                        human_review_required=(status == "DISCREPANCY"),
                        provenance=prov,
                    )
                )

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
            summary=f"Evaluated registration and application identifiers ({len(findings)} checks).",
        )
