from __future__ import annotations

from typing import Dict, Any, List, Optional
from app.services.reconciliation.base import ComparisonRule, RuleResult, ReconciliationFinding
from app.services.reconciliation.utils import build_provenance_from_extracted_field


class FirstGraduateRule(ComparisonRule):
    """
    Compares declared First Graduate claim against First Graduate Certificate extraction:
    - Declared True & Certificate extracted eligible: MATCH
    - Declared True & Certificate missing: INCOMPLETE_DOCUMENTS
    - Declared False & Certificate uploaded: PENDING_SCRUTINY
    - Explicit non-authenticity notice: compares extracted fields only; does not claim certificate validity.
    """

    RULE_ID = "RULE_FIRST_GRADUATE"
    RULE_NAME = "First Graduate Concession Claim Consistency"

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

        declared_fg = bool(application_data.get("is_first_graduate", False))
        fg_ext = extractions.get("FIRST_GRADUATE_CERTIFICATE")

        if declared_fg:
            if fg_ext and "fields" in fg_ext:
                field_d = fg_ext["fields"].get("is_eligible")
                ext_val = field_d.get("normalized_value") if field_d else None
                prov = build_provenance_from_extracted_field(field_d, fg_ext.get("meta")) if field_d else None

                if ext_val is True:
                    status = "MATCH"
                    disc_reason = None
                elif ext_val is False:
                    status = "DISCREPANCY"
                    disc_reason = "Declared First Graduate claim is True but certificate extraction indicates ineligibility"
                else:
                    status = "PENDING_SCRUTINY"
                    disc_reason = "First Graduate certificate uploaded but eligibility flag requires manual scrutiny"

                findings.append(
                    ReconciliationFinding(
                        rule_id=self.rule_id,
                        rule_name="Declared First Graduate Claim vs Certificate Extraction",
                        field_key="is_first_graduate",
                        status=status,
                        declared_value=declared_fg,
                        extracted_value=ext_val,
                        discrepancy_reason=disc_reason,
                        human_review_required=(status in ["DISCREPANCY", "PENDING_SCRUTINY"]),
                        review_reason="Compares declared claim with extracted certificate fields; does not establish legal document validity.",
                        provenance=prov,
                    )
                )
            else:
                findings.append(
                    ReconciliationFinding(
                        rule_id=self.rule_id,
                        rule_name="Declared First Graduate Claim vs Certificate Extraction",
                        field_key="is_first_graduate",
                        status="INCOMPLETE_DOCUMENTS",
                        declared_value=declared_fg,
                        extracted_value=None,
                        discrepancy_reason="First Graduate concession claimed but certificate is not uploaded/extracted",
                        human_review_required=True,
                        review_reason="Mandatory certificate missing for claimed First Graduate concession",
                    )
                )
        else:
            # Candidate did not claim FG
            if fg_ext:
                findings.append(
                    ReconciliationFinding(
                        rule_id=self.rule_id,
                        rule_name="Declared First Graduate Claim vs Certificate Upload",
                        field_key="is_first_graduate",
                        status="PENDING_SCRUTINY",
                        declared_value=False,
                        extracted_value="CERTIFICATE_PRESENT",
                        discrepancy_reason=None,
                        human_review_required=True,
                        review_reason="First Graduate certificate uploaded but form declaration is set to False; manual scrutiny required to confirm if applicant intended to claim FG concession or uploaded by mistake",
                    )
                )
            else:
                findings.append(
                    ReconciliationFinding(
                        rule_id=self.rule_id,
                        rule_name="Declared First Graduate Claim",
                        field_key="is_first_graduate",
                        status="MATCH",
                        declared_value=False,
                        extracted_value=None,
                    )
                )

        overall_st = findings[0].status
        return RuleResult(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            status=overall_st,
            findings=findings,
            requires_human_review=(overall_st in ["DISCREPANCY", "PENDING_SCRUTINY"]),
            summary=f"Evaluated First Graduate claim consistency ({overall_st}).",
        )
