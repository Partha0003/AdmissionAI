from __future__ import annotations

from typing import Dict, Any, List, Optional
from app.services.reconciliation.base import ComparisonRule, RuleResult, ReconciliationFinding
from app.services.reconciliation.utils import (
    COMMUNITY_QUOTA_PROTOTYPE_MAP,
    normalize_string,
    build_provenance_from_extracted_field,
)


class CommunityQuotaRule(ComparisonRule):
    """
    Compares Community & Reservation Quota:
    1. Declared Community vs Community Certificate extracted community
    2. Declared Community vs TNEA Allotment Baseline Quota (via prototype mapping table)
    3. Community Certificate extracted community vs TNEA Allotment Baseline Quota
    """

    RULE_ID = "RULE_COMMUNITY_QUOTA"
    RULE_NAME = "Community and Allotment Quota Reconciliation"

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

        declared_comm = normalize_string(application_data.get("community") or application_data.get("caste"))
        allotment_quota = normalize_string(allotment_baseline.get("allotted_category") or allotment_baseline.get("quota")) if allotment_baseline else None

        comm_ext = extractions.get("COMMUNITY_CERTIFICATE")

        # 1. Declared Community vs Community Certificate Extracted Community
        if comm_ext and "fields" in comm_ext:
            field_dict = comm_ext["fields"].get("community")
            if field_dict and field_dict.get("normalized_value"):
                extracted_comm = normalize_string(field_dict["normalized_value"])
                prov = build_provenance_from_extracted_field(field_dict, comm_ext.get("meta"))

                if declared_comm:
                    if declared_comm == extracted_comm:
                        status = "MATCH"
                        disc_reason = None
                    else:
                        status = "DISCREPANCY"
                        disc_reason = f"Declared community '{declared_comm}' differs from certificate community '{extracted_comm}'"
                else:
                    status = "PENDING_SCRUTINY"
                    disc_reason = None

                findings.append(
                    ReconciliationFinding(
                        rule_id=self.rule_id,
                        rule_name="Declared Community vs Community Certificate Category",
                        field_key="community_certificate_category",
                        status=status,
                        declared_value=declared_comm,
                        extracted_value=extracted_comm,
                        allotment_baseline_value=allotment_quota,
                        discrepancy_reason=disc_reason,
                        human_review_required=(status in ["DISCREPANCY", "PENDING_SCRUTINY"]),
                        provenance=prov,
                    )
                )
            else:
                findings.append(
                    ReconciliationFinding(
                        rule_id=self.rule_id,
                        rule_name="Declared Community vs Community Certificate Category",
                        field_key="community_certificate_category",
                        status="INCOMPLETE_DOCUMENTS",
                        declared_value=declared_comm,
                        extracted_value=None,
                        allotment_baseline_value=allotment_quota,
                        review_reason="Community certificate uploaded but category field could not be extracted",
                    )
                )

        # 2. Declared Community vs TNEA Allotment Baseline Quota
        if declared_comm and allotment_quota:
            allowed_communities = COMMUNITY_QUOTA_PROTOTYPE_MAP.get(allotment_quota)
            if allowed_communities is not None:
                if declared_comm in allowed_communities:
                    status = "MATCH"
                    disc_reason = None
                else:
                    status = "DISCREPANCY"
                    disc_reason = f"Declared community '{declared_comm}' is not compatible with TNEA baseline quota '{allotment_quota}' (allowed: {', '.join(sorted(allowed_communities))})"
            else:
                status = "PENDING_SCRUTINY"
                disc_reason = None
                rev_reason = f"Unmapped / unsupported TNEA baseline quota '{allotment_quota}' requires manual scrutiny against declared community '{declared_comm}'"

            findings.append(
                ReconciliationFinding(
                    rule_id=self.rule_id,
                    rule_name="Declared Community vs TNEA Allotment Baseline Quota",
                    field_key="allotment_quota_consistency",
                    status=status,
                    declared_value=declared_comm,
                    extracted_value=None,
                    allotment_baseline_value=allotment_quota,
                    discrepancy_reason=disc_reason if status == "DISCREPANCY" else None,
                    human_review_required=(status in ["DISCREPANCY", "PENDING_SCRUTINY"]),
                    review_reason=rev_reason if status == "PENDING_SCRUTINY" else None,
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
            summary=f"Evaluated community and reservation quota consistency ({len(findings)} checks).",
        )
