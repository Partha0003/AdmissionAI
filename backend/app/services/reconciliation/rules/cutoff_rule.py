from __future__ import annotations

from typing import Dict, Any, List, Optional
from app.services.reconciliation.base import ComparisonRule, RuleResult, ReconciliationFinding
from app.services.reconciliation.utils import build_provenance_from_extracted_field


class AcademicCutoffRule(ComparisonRule):
    """
    Compares 12th Cutoff & Subject Marks:
    1. Declared 12th Cutoff vs TwelfthMarksheet calculated_cutoff_marks (derived value, tolerance: <= 0.01)
    2. Declared 12th Cutoff vs AllotmentOrder document_cutoff_mark (from document, tolerance: <= 0.01)
    3. Declared Subject Marks (Maths, Physics, Chemistry) vs TwelfthMarksheet extracted marks
    """

    RULE_ID = "RULE_ACADEMIC_CUTOFF"
    RULE_NAME = "12th Academic Marks and Cutoff Reconciliation"
    TOLERANCE = 0.01

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

        declared_cutoff = application_data.get("twelfth_cutoff_marks")
        hsc_ext = extractions.get("TWELFTH_MARKSHEET")
        allotment_ext = extractions.get("ALLOTMENT_ORDER")

        # 1. Declared Cutoff vs TwelfthMarksheet calculated_cutoff_marks
        if hsc_ext and "fields" in hsc_ext:
            calc_cutoff_field = (
                hsc_ext.get("calculated_fields", {}).get("calculated_cutoff_marks")
                or hsc_ext["fields"].get("calculated_cutoff_marks")
            )
            if calc_cutoff_field and calc_cutoff_field.get("normalized_value") is not None:
                calc_val = float(calc_cutoff_field["normalized_value"])
                prov = build_provenance_from_extracted_field(
                    calc_cutoff_field,
                    hsc_ext.get("meta"),
                    comparison_method="FLOAT_TOLERANCE",
                    tolerance_applied=f"abs(diff) <= {self.TOLERANCE}",
                )

                if declared_cutoff is not None:
                    decl_val = float(declared_cutoff)
                    diff = round(abs(decl_val - calc_val), 2)
                    if diff <= self.TOLERANCE:
                        status = "MATCH"
                        disc_reason = None
                    else:
                        status = "DISCREPANCY"
                        disc_reason = f"Declared cutoff ({decl_val}) differs from calculated marksheet cutoff ({calc_val}) by delta {diff}"
                else:
                    status = "PENDING_SCRUTINY"
                    disc_reason = None

                findings.append(
                    ReconciliationFinding(
                        rule_id=self.rule_id,
                        rule_name="Declared Cutoff vs 12th Marksheet Derived Cutoff",
                        field_key="calculated_cutoff_marks",
                        status=status,
                        declared_value=declared_cutoff,
                        extracted_value=calc_val,
                        allotment_baseline_value=None,
                        delta=diff if declared_cutoff is not None else None,
                        discrepancy_reason=disc_reason,
                        human_review_required=(status == "DISCREPANCY"),
                        review_reason="This is a deterministic comparison against derived marksheet cutoff; not external verification.",
                        provenance=prov,
                    )
                )
            else:
                findings.append(
                    ReconciliationFinding(
                        rule_id=self.rule_id,
                        rule_name="Declared Cutoff vs 12th Marksheet Derived Cutoff",
                        field_key="calculated_cutoff_marks",
                        status="INCOMPLETE_DOCUMENTS",
                        declared_value=declared_cutoff,
                        extracted_value=None,
                        review_reason="12th Marksheet marks not detected or missing",
                    )
                )

        # 2. Declared Cutoff vs Allotment Order document_cutoff_mark
        if allotment_ext and "fields" in allotment_ext:
            doc_cutoff_field = allotment_ext["fields"].get("document_cutoff_mark")
            if doc_cutoff_field and doc_cutoff_field.get("normalized_value") is not None:
                doc_cutoff_val = float(doc_cutoff_field["normalized_value"])
                prov = build_provenance_from_extracted_field(
                    doc_cutoff_field,
                    allotment_ext.get("meta"),
                    comparison_method="FLOAT_TOLERANCE",
                    tolerance_applied=f"abs(diff) <= {self.TOLERANCE}",
                )

                if declared_cutoff is not None:
                    decl_val = float(declared_cutoff)
                    diff = round(abs(decl_val - doc_cutoff_val), 2)
                    if diff <= self.TOLERANCE:
                        status = "MATCH"
                        disc_reason = None
                    else:
                        status = "DISCREPANCY"
                        disc_reason = f"Declared cutoff ({decl_val}) differs from allotment document cutoff ({doc_cutoff_val}) by delta {diff}"
                else:
                    status = "PENDING_SCRUTINY"
                    disc_reason = None

                findings.append(
                    ReconciliationFinding(
                        rule_id=self.rule_id,
                        rule_name="Declared Cutoff vs Allotment Order Document Cutoff",
                        field_key="allotment_document_cutoff_mark",
                        status=status,
                        declared_value=declared_cutoff,
                        extracted_value=doc_cutoff_val,
                        allotment_baseline_value=None,
                        delta=diff if declared_cutoff is not None else None,
                        discrepancy_reason=disc_reason,
                        human_review_required=(status == "DISCREPANCY"),
                        review_reason="The cutoff value is extracted from the allotment document; it is not independently verified against an authoritative external source.",
                        provenance=prov,
                    )
                )

        # 3. Individual Subject Marks (Maths, Physics, Chemistry)
        subjects = [
            ("twelfth_maths_marks", "maths_marks", "Mathematics"),
            ("twelfth_physics_marks", "physics_marks", "Physics"),
            ("twelfth_chemistry_marks", "chemistry_marks", "Chemistry"),
        ]
        for app_field, ext_field, subj_name in subjects:
            decl_m = application_data.get(app_field)
            if decl_m is not None and hsc_ext and "fields" in hsc_ext:
                field_d = hsc_ext["fields"].get(ext_field)
                if field_d and field_d.get("normalized_value") is not None:
                    ext_m = float(field_d["normalized_value"])
                    prov = build_provenance_from_extracted_field(field_d, hsc_ext.get("meta"))
                    if float(decl_m) == ext_m:
                        status = "MATCH"
                        disc_r = None
                    else:
                        status = "DISCREPANCY"
                        disc_r = f"Declared {subj_name} mark ({decl_m}) differs from extracted mark ({ext_m})"

                    findings.append(
                        ReconciliationFinding(
                            rule_id=self.rule_id,
                            rule_name=f"Declared vs 12th Marksheet {subj_name} Mark",
                            field_key=app_field,
                            status=status,
                            declared_value=decl_m,
                            extracted_value=ext_m,
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
            summary=f"Evaluated cutoff and academic subject marks ({len(findings)} checks).",
        )
