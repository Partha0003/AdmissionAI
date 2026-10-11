from __future__ import annotations

from typing import Dict, Any, List, Optional
from app.services.reconciliation.base import ComparisonRule, RuleResult, ReconciliationFinding
from app.services.reconciliation.utils import compare_names, build_provenance_from_extracted_field


class ParentNameRule(ComparisonRule):
    """
    Compares declared Father / Mother name against parent name extracted from:
    1. Community Certificate (father_name)
    2. Income Certificate (candidate_name / parent name)
    """

    RULE_ID = "RULE_PARENT_NAME_CONSISTENCY"
    RULE_NAME = "Parent / Guardian Name Multi-Document Consistency"

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

        declared_father = application_data.get("father_name")
        declared_mother = application_data.get("mother_name")

        # 1. Community Certificate Father Name
        comm_ext = extractions.get("COMMUNITY_CERTIFICATE")
        if comm_ext and "fields" in comm_ext:
            field_d = comm_ext["fields"].get("father_name")
            if field_d and field_d.get("normalized_value"):
                ext_parent = field_d["normalized_value"]
                status, reason = compare_names(declared_father, ext_parent)
                prov = build_provenance_from_extracted_field(field_d, comm_ext.get("meta"))
                findings.append(
                    ReconciliationFinding(
                        rule_id=self.rule_id,
                        rule_name="Declared Father Name vs Community Certificate Parent Name",
                        field_key="community_father_name",
                        status=status,
                        declared_value=declared_father,
                        extracted_value=ext_parent,
                        discrepancy_reason=reason if status == "DISCREPANCY" else None,
                        human_review_required=(status in ["DISCREPANCY", "PENDING_SCRUTINY"]),
                        review_reason=reason if status == "PENDING_SCRUTINY" else None,
                        provenance=prov,
                    )
                )

        # 2. Income Certificate Applicant / Parent Name
        inc_ext = extractions.get("INCOME_CERTIFICATE")
        if inc_ext and "fields" in inc_ext:
            field_d = inc_ext["fields"].get("candidate_name")
            if field_d and field_d.get("normalized_value"):
                ext_inc_name = field_d["normalized_value"]
                # Income certificate might be in father's name or candidate's name
                status_f, reason_f = compare_names(declared_father, ext_inc_name)
                status_s, _ = compare_names(application_data.get("student_name"), ext_inc_name)

                if status_f == "MATCH" or status_s == "MATCH":
                    status = "MATCH"
                    disc_r = None
                elif status_f == "PENDING_SCRUTINY" or status_s == "PENDING_SCRUTINY":
                    status = "PENDING_SCRUTINY"
                    disc_r = reason_f
                else:
                    status = "DISCREPANCY"
                    disc_r = f"Income certificate holder '{ext_inc_name}' matches neither applicant nor father ('{declared_father}')"

                prov = build_provenance_from_extracted_field(field_d, inc_ext.get("meta"))
                findings.append(
                    ReconciliationFinding(
                        rule_id=self.rule_id,
                        rule_name="Declared Family Name vs Income Certificate Holder",
                        field_key="income_cert_holder_name",
                        status=status,
                        declared_value=f"Father: {declared_father} / Student: {application_data.get('student_name')}",
                        extracted_value=ext_inc_name,
                        discrepancy_reason=disc_r if status == "DISCREPANCY" else None,
                        human_review_required=(status in ["DISCREPANCY", "PENDING_SCRUTINY"]),
                        review_reason=disc_r if status == "PENDING_SCRUTINY" else None,
                        provenance=prov,
                    )
                )

        if not findings:
            return RuleResult(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                status="MATCH" if (not declared_father and not declared_mother) else "INCOMPLETE_DOCUMENTS",
                findings=[],
                summary="No certificate parent fields available to evaluate.",
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
            summary=f"Evaluated parent and guardian name consistency ({len(findings)} checks).",
        )
