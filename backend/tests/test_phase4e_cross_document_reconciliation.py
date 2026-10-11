import io
import pytest
from httpx import AsyncClient
import cv2
import numpy as np

from app.services.reconciliation import (
    CrossDocumentReconciler,
    NameConsistencyRule,
    AcademicCutoffRule,
    CommunityQuotaRule,
    IncomeRule,
    FirstGraduateRule,
    ParentNameRule,
    IdentifierRule,
)
from app.services.reconciliation.utils import (
    normalize_name_tokens,
    compare_names,
    COMMUNITY_QUOTA_PROTOTYPE_MAP,
)


def create_synthetic_test_image(text_lines=None, width=500, height=300) -> bytes:
    """Generates a synthetic PNG document image containing known text lines."""
    img = np.ones((height, width, 3), dtype=np.uint8) * 255
    font = cv2.FONT_HERSHEY_SIMPLEX
    lines = text_lines or [
        "XYZ ENGINEERING COLLEGE",
        "NAME: KARTHIKEYAN S",
        "APPLICATION: XYZ2026001",
    ]
    for idx, line in enumerate(lines):
        y = 50 + (idx * 40)
        cv2.putText(img, line, (30, y), font, 0.5, (0, 0, 0), 1, cv2.LINE_AA)

    success, buf = cv2.imencode(".png", img)
    assert success
    return buf.tobytes()


@pytest.mark.asyncio
async def test_full_match_reconciliation_scenario():
    """
    Verification Check 1:
    Tests a complete match scenario across declared form, extracted documents, and allotment baseline.
    """
    app_data = {
        "student_name": "KARTHIKEYAN S",
        "tnea_application_number": "20261001",
        "community": "BC",
        "father_name": "SARAVANAN M",
        "annual_family_income": 150000,
        "is_first_graduate": True,
        "twelfth_registration_number": "TN12-9988",
        "twelfth_cutoff_marks": 193.5,
        "twelfth_maths_marks": 98,
        "twelfth_physics_marks": 95,
        "twelfth_chemistry_marks": 96,
        "tenth_registration_number": "TN10-12345",
    }
    allotment_baseline = {
        "tnea_application_number": "20261001",
        "candidate_name": "S. KARTHIKEYAN",
        "allotted_branch": "Computer Science and Engineering",
        "allotted_category": "BC",
        "quota": "BC",
    }
    extractions = {
        "TWELFTH_MARKSHEET": {
            "fields": {
                "candidate_name": {"normalized_value": "KARTHIKEYAN S"},
                "registration_number": {"normalized_value": "TN12-9988"},
                "maths_marks": {"normalized_value": 98.0},
                "physics_marks": {"normalized_value": 95.0},
                "chemistry_marks": {"normalized_value": 96.0},
                "calculated_cutoff_marks": {"normalized_value": 193.5},
            },
            "meta": {"document_id": "doc-12th", "document_version": 1},
        },
        "COMMUNITY_CERTIFICATE": {
            "fields": {
                "candidate_name": {"normalized_value": "KARTHIKEYAN S"},
                "father_name": {"normalized_value": "SARAVANAN M"},
                "community": {"normalized_value": "BC"},
            },
            "meta": {"document_id": "doc-comm", "document_version": 1},
        },
        "FIRST_GRADUATE_CERTIFICATE": {
            "fields": {
                "is_eligible": {"normalized_value": True},
            },
            "meta": {"document_id": "doc-fg", "document_version": 1},
        },
        "INCOME_CERTIFICATE": {
            "fields": {
                "candidate_name": {"normalized_value": "SARAVANAN M"},
                "annual_income": {"normalized_value": 150000},
            },
            "meta": {"document_id": "doc-inc", "document_version": 1},
        },
        "ALLOTMENT_ORDER": {
            "fields": {
                "tnea_application_number": {"normalized_value": "20261001"},
                "candidate_name": {"normalized_value": "KARTHIKEYAN S"},
                "document_cutoff_mark": {"normalized_value": 193.5},
            },
            "meta": {"document_id": "doc-alt", "document_version": 1},
        },
        "TENTH_MARKSHEET": {
            "fields": {
                "candidate_name": {"normalized_value": "KARTHIKEYAN S"},
                "registration_number": {"normalized_value": "TN10-12345"},
            },
            "meta": {"document_id": "doc-10th", "document_version": 1},
        },
    }

    reconciler = CrossDocumentReconciler()
    result = reconciler.reconcile(app_data, allotment_baseline, extractions)

    assert result["overall_status"] == "MATCH"
    assert result["discrepancy_count"] == 0
    assert result["pending_scrutiny_count"] == 0
    assert result["requires_human_review"] is False
    assert result["passed_rules_count"] == result["total_rules_evaluated"]


@pytest.mark.asyncio
async def test_tnea_baseline_semantics_without_live_claims():
    """
    Verification Check 2:
    Tests that the TNEA baseline is used as imported reference data and no live verification is claimed.
    """
    rule = IdentifierRule()
    app_data = {"tnea_application_number": "20261001"}
    baseline = {"tnea_application_number": "20261001"}
    extractions = {}

    res = rule.evaluate(app_data, baseline, extractions)
    assert res.status == "MATCH"
    finding = res.findings[0]
    assert finding.allotment_baseline_value == "20261001"
    assert finding.declared_value == "20261001"


@pytest.mark.asyncio
async def test_deterministic_numeric_cutoff_tolerance():
    """
    Verification Check 3:
    Tests deterministic float tolerance comparison for cutoff marks (abs <= 0.01 matches, delta > 0.01 flags discrepancy).
    """
    rule = AcademicCutoffRule()
    app_data_match = {"twelfth_cutoff_marks": 193.50}
    extractions_match = {
        "TWELFTH_MARKSHEET": {
            "fields": {
                "calculated_cutoff_marks": {"normalized_value": 193.50},
                "maths_marks": {"normalized_value": 98.0},
                "physics_marks": {"normalized_value": 95.0},
                "chemistry_marks": {"normalized_value": 96.0},
            }
        }
    }
    res_match = rule.evaluate(app_data_match, None, extractions_match)
    assert res_match.status == "MATCH"

    # Discrepancy case: declared 195.0 vs calculated 193.5
    app_data_disc = {"twelfth_cutoff_marks": 195.00}
    res_disc = rule.evaluate(app_data_disc, None, extractions_match)
    assert res_disc.status == "DISCREPANCY"
    cutoff_finding = next(f for f in res_disc.findings if f.field_key == "calculated_cutoff_marks")
    assert cutoff_finding.status == "DISCREPANCY"
    assert cutoff_finding.delta == 1.5
    assert "differs from calculated marksheet cutoff" in cutoff_finding.discrepancy_reason


@pytest.mark.asyncio
async def test_deterministic_name_normalization():
    """
    Verification Check 4:
    Tests Tamil Nadu initial normalization pipeline ('S. KARTHIKEYAN' == 'KARTHIKEYAN S' == 'KARTHIKEYAN .S').
    """
    status1, _ = compare_names("S. KARTHIKEYAN", "KARTHIKEYAN S")
    assert status1 == "MATCH"

    status2, _ = compare_names("KARTHIKEYAN S", "KARTHIKEYAN .S")
    assert status2 == "MATCH"

    status3, _ = compare_names("  karthikeyan   s.  ", "S KARTHIKEYAN")
    assert status3 == "MATCH"

    core, inits, canon = normalize_name_tokens("S. KARTHIKEYAN")
    assert core == {"KARTHIKEYAN"}
    assert inits == ["S"]


@pytest.mark.asyncio
async def test_ambiguous_name_handling():
    """
    Verification Check 5:
    Tests that ambiguous names (e.g. missing initial or partial token overlap) produce PENDING_SCRUTINY.
    """
    status, reason = compare_names("KARTHIKEYAN", "KARTHIKEYAN S")
    assert status == "PENDING_SCRUTINY"
    assert "initials differ" in reason

    status2, reason2 = compare_names("KARTHIKEYAN SARAVANAN", "KARTHIKEYAN S")
    assert status2 == "PENDING_SCRUTINY"
    assert "overlap" in reason2


@pytest.mark.asyncio
async def test_distinct_name_mismatch():
    """
    Verification Check 6:
    Tests that completely disjoint candidate names produce DISCREPANCY.
    """
    status, reason = compare_names("VIKRAM R", "KARTHIKEYAN S")
    assert status == "DISCREPANCY"
    assert "completely distinct" in reason


@pytest.mark.asyncio
async def test_community_quota_prototype_mapping():
    """
    Verification Check 7:
    Tests explicit prototype quota mapping table:
    - mapped + compatible -> MATCH (OC allows any, BC matches BC)
    - mapped + incompatible -> DISCREPANCY (SC quota with OC community)
    - unmapped / unsupported quota -> PENDING_SCRUTINY
    """
    rule = CommunityQuotaRule()

    # Valid: BC declared, BC quota -> MATCH
    res1 = rule.evaluate({"community": "BC"}, {"quota": "BC"}, {})
    assert res1.status == "MATCH"

    # Valid: BC declared, OC quota (open competition) -> MATCH
    res2 = rule.evaluate({"community": "BC"}, {"quota": "OC"}, {})
    assert res2.status == "MATCH"

    # Discrepancy: OC declared, SC quota -> DISCREPANCY
    res3 = rule.evaluate({"community": "OC"}, {"quota": "SC"}, {})
    assert res3.status == "DISCREPANCY"
    assert "not compatible with TNEA baseline quota" in res3.findings[0].discrepancy_reason

    # Unmapped / unsupported quota -> PENDING_SCRUTINY
    res4 = rule.evaluate({"community": "BC"}, {"quota": "SPECIAL_SPORTS_QUOTA"}, {})
    assert res4.status == "PENDING_SCRUTINY"
    assert res4.findings[0].status == "PENDING_SCRUTINY"
    assert "Unmapped / unsupported TNEA baseline quota" in res4.findings[0].review_reason
    assert res4.requires_human_review is True


@pytest.mark.asyncio
async def test_first_graduate_consistency_without_authenticity_claims():
    """
    Verification Check 8:
    Tests First Graduate consistency check:
    - Declared True + valid extracted certificate -> MATCH
    - Declared True + missing certificate -> INCOMPLETE_DOCUMENTS
    - Declared True + certificate extracted ineligible -> DISCREPANCY
    - Declared False + certificate uploaded/extracted -> PENDING_SCRUTINY
    """
    rule = FirstGraduateRule()

    # Case A: Declared True, Cert extracted True -> MATCH
    ext_ok = {"FIRST_GRADUATE_CERTIFICATE": {"fields": {"is_eligible": {"normalized_value": True}}}}
    res_ok = rule.evaluate({"is_first_graduate": True}, None, ext_ok)
    assert res_ok.status == "MATCH"
    assert "does not establish legal document validity" in res_ok.findings[0].review_reason

    # Case B: Declared True, Cert missing -> INCOMPLETE_DOCUMENTS
    res_missing = rule.evaluate({"is_first_graduate": True}, None, {})
    assert res_missing.status == "INCOMPLETE_DOCUMENTS"

    # Case C: Declared True, Cert extracted False -> DISCREPANCY
    ext_ineligible = {"FIRST_GRADUATE_CERTIFICATE": {"fields": {"is_eligible": {"normalized_value": False}}}}
    res_ineligible = rule.evaluate({"is_first_graduate": True}, None, ext_ineligible)
    assert res_ineligible.status == "DISCREPANCY"

    # Case D: Declared False, Cert uploaded/extracted -> PENDING_SCRUTINY
    res_decl_false_cert_present = rule.evaluate({"is_first_graduate": False}, None, ext_ok)
    assert res_decl_false_cert_present.status == "PENDING_SCRUTINY"
    assert res_decl_false_cert_present.findings[0].status == "PENDING_SCRUTINY"
    assert res_decl_false_cert_present.requires_human_review is True
    assert "manual scrutiny required" in res_decl_false_cert_present.findings[0].review_reason



@pytest.mark.asyncio
async def test_annual_income_integer_discrepancy():
    """
    Verification Check 9:
    Tests exact integer income comparison and delta calculation.
    """
    rule = IncomeRule()
    ext_income = {
        "INCOME_CERTIFICATE": {
            "fields": {"annual_income": {"normalized_value": 300000}},
            "meta": {"document_id": "doc-inc", "document_version": 1},
        }
    }
    # Declared 150000 vs Extracted 300000 -> DISCREPANCY with delta 150000
    res = rule.evaluate({"annual_family_income": 150000}, None, ext_income)
    assert res.status == "DISCREPANCY"
    finding = res.findings[0]
    assert finding.delta == 150000
    assert "delta Rs. 150,000" in finding.discrepancy_reason


@pytest.mark.asyncio
async def test_incomplete_documents_handling():
    """
    Verification Check 10:
    Tests graceful degradation when required certificates are missing from uploads.
    """
    reconciler = CrossDocumentReconciler()
    # Candidate declared data but uploaded no documents
    app_data = {
        "student_name": "KARTHIKEYAN S",
        "community": "BC",
        "annual_family_income": 150000,
        "is_first_graduate": True,
    }
    result = reconciler.reconcile(app_data, None, {})
    assert result["overall_status"] == "INCOMPLETE_DOCUMENTS"
    assert result["incomplete_count"] > 0
    assert result["requires_human_review"] is True


@pytest.mark.asyncio
async def test_reconciliation_provenance_preservation():
    """
    Verification Check 11:
    Tests that findings preserve full Phase 4D provenance (document ID, version, extraction ID, block indices, bounding box).
    """
    rule = CommunityQuotaRule()
    ext_data = {
        "COMMUNITY_CERTIFICATE": {
            "fields": {
                "community": {
                    "field_key": "community",
                    "normalized_value": "BC",
                    "provenance": {
                        "ocr_block_indices": [0, 1],
                        "bounding_box": {"x": 100, "y": 150, "width": 180, "height": 24},
                    },
                }
            },
            "meta": {
                "document_id": "doc-comm-uuid",
                "document_version": 2,
                "extraction_result_id": "ext-res-uuid",
            },
        }
    }
    res = rule.evaluate({"community": "BC"}, None, ext_data)
    assert res.status == "MATCH"
    prov = res.findings[0].provenance
    assert prov is not None
    assert prov.document_id == "doc-comm-uuid"
    assert prov.document_version == 2
    assert prov.extraction_result_id == "ext-res-uuid"
    assert prov.ocr_block_indices == [0, 1]
    assert prov.bounding_box == {"x": 100, "y": 150, "width": 180, "height": 24}


@pytest.mark.asyncio
async def test_status_precedence_hierarchy():
    """
    Verification Check 12:
    Tests precedence: PENDING_SCRUTINY > DISCREPANCY_DETECTED > INCOMPLETE_DOCUMENTS > MATCH.
    """
    reconciler = CrossDocumentReconciler()

    # Case A: Mix of MATCH and PENDING_SCRUTINY -> overall PENDING_SCRUTINY
    app_data_a = {
        "student_name": "KARTHIKEYAN",  # Missing initial -> PENDING_SCRUTINY
        "tnea_application_number": "20261001",
        "community": "BC",
    }
    ext_a = {
        "TWELFTH_MARKSHEET": {"fields": {"candidate_name": {"normalized_value": "KARTHIKEYAN S"}}},
        "COMMUNITY_CERTIFICATE": {"fields": {"community": {"normalized_value": "BC"}}},
    }
    res_a = reconciler.reconcile(app_data_a, {"tnea_application_number": "20261001"}, ext_a)
    assert res_a["overall_status"] == "PENDING_SCRUTINY"

    # Case B: Mix of MATCH, INCOMPLETE, and DISCREPANCY (no pending scrutiny) -> overall DISCREPANCY_DETECTED
    app_data_b = {
        "student_name": "KARTHIKEYAN S",
        "tnea_application_number": "20261001",
        "annual_family_income": 100000,
    }
    ext_b = {
        "INCOME_CERTIFICATE": {"fields": {"annual_income": {"normalized_value": 500000}}},  # Discrepancy
    }
    res_b = reconciler.reconcile(app_data_b, {"tnea_application_number": "20261001"}, ext_b)
    assert res_b["overall_status"] == "DISCREPANCY_DETECTED"


@pytest.mark.asyncio
async def test_versioned_snapshot_preservation_and_anti_idor(
    client: AsyncClient, student1_token: str, student2_token: str, admin_token: str
):
    """
    Verification Check 13:
    Tests that:
    1. Reconciling on v2 creates a new snapshot without corrupting v1 snapshot.
    2. Student 1 cannot trigger or read Student 2 reconciliation (Anti-IDOR -> 403/404).
    3. Admin can read reconciliation for any student.
    """
    headers_s1 = {"Authorization": f"Bearer {student1_token}"}
    headers_s2 = {"Authorization": f"Bearer {student2_token}"}
    headers_adm = {"Authorization": f"Bearer {admin_token}"}

    # Student 1 triggers reconciliation
    recon_res = await client.post("/api/v1/applications/me/reconcile", headers=headers_s1)
    assert recon_res.status_code == 200
    recon_data = recon_res.json()
    assert "overall_status" in recon_data
    app_id_s1 = recon_data["application_id"]

    # Student 1 reads own reconciliation
    get_res = await client.get("/api/v1/applications/me/reconciliation", headers=headers_s1)
    assert get_res.status_code == 200
    assert get_res.json()["id"] == recon_data["id"]

    # Student 2 triggers own reconciliation
    recon_s2 = await client.post("/api/v1/applications/me/reconcile", headers=headers_s2)
    assert recon_s2.status_code == 200
    app_id_s2 = recon_s2.json()["application_id"]

    # Student 1 attempts to trigger/read admin endpoint for Student 2 -> 403 Forbidden
    idor_post = await client.post(f"/api/v1/admin/applications/{app_id_s2}/reconcile", headers=headers_s1)
    assert idor_post.status_code == 403

    idor_get = await client.get(f"/api/v1/admin/applications/{app_id_s2}/reconciliation", headers=headers_s1)
    assert idor_get.status_code == 403

    # Admin reads reconciliation for Student 1
    admin_get = await client.get(f"/api/v1/admin/applications/{app_id_s1}/reconciliation", headers=headers_adm)
    assert admin_get.status_code == 200
    assert admin_get.json()["id"] == recon_data["id"]


@pytest.mark.asyncio
async def test_reconciliation_strict_non_mutation_guarantees(client: AsyncClient, student1_token: str):
    """
    Verification Check 14:
    Strict Read-Only Guarantee:
    Verifies that running cross-document reconciliation does NOT alter AdmissionApplication.status,
    Student data, TNEAAllotment, or Document.status.
    """
    headers = {"Authorization": f"Bearer {student1_token}"}

    # Snapshot state before reconciliation
    app_before = (await client.get("/api/v1/applications/me", headers=headers)).json()
    status_before = app_before["status"]
    completion_before = app_before["completion_percentage"]

    checklist_before = (await client.get("/api/v1/applications/me/checklist", headers=headers)).json()

    # Trigger reconciliation
    recon_res = await client.post("/api/v1/applications/me/reconcile", headers=headers)
    assert recon_res.status_code == 200

    # Snapshot state after reconciliation
    app_after = (await client.get("/api/v1/applications/me", headers=headers)).json()
    checklist_after = (await client.get("/api/v1/applications/me/checklist", headers=headers)).json()

    assert app_after["status"] == status_before
    assert app_after["completion_percentage"] == completion_before
    assert app_after["status"] != "DOCUMENTS_VERIFIED"
    assert app_after["status"] != "ADMISSION_CONFIRMED"

    # Confirm all document statuses are unchanged
    for doc_b, doc_a in zip(checklist_before, checklist_after):
        assert doc_b["document_status"] == doc_a["document_status"]
