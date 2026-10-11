from __future__ import annotations

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime


class ReconciliationFindingProvenanceResponse(BaseModel):
    document_id: Optional[str] = None
    document_version: Optional[int] = None
    extraction_result_id: Optional[str] = None
    extracted_field_key: Optional[str] = None
    ocr_block_indices: List[int] = []
    bounding_box: Optional[Dict[str, int]] = None
    comparison_method: str = "EXACT_NORMALIZED"
    tolerance_applied: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ReconciliationFindingResponse(BaseModel):
    rule_id: str
    rule_name: str
    field_key: str
    status: str  # MATCH | DISCREPANCY | PENDING_SCRUTINY | INCOMPLETE_DOCUMENTS
    declared_value: Optional[Any] = None
    extracted_value: Optional[Any] = None
    allotment_baseline_value: Optional[Any] = None
    delta: Optional[Any] = None
    discrepancy_reason: Optional[str] = None
    human_review_required: bool = False
    review_reason: Optional[str] = None
    provenance: Optional[ReconciliationFindingProvenanceResponse] = None

    model_config = ConfigDict(from_attributes=True)


class CrossDocumentReconciliationResponse(BaseModel):
    id: str
    application_id: str
    overall_status: str  # MATCH | DISCREPANCY_DETECTED | INCOMPLETE_DOCUMENTS | PENDING_SCRUTINY
    participating_document_versions: Dict[str, Any] = {}
    total_rules_evaluated: int = 0
    passed_rules_count: int = 0
    discrepancy_count: int = 0
    pending_scrutiny_count: int = 0
    incomplete_count: int = 0
    findings: List[ReconciliationFindingResponse] = []
    discrepancy_summary: Dict[str, str] = {}
    requires_human_review: bool = False
    reconciliation_time_ms: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class RunReconciliationRequest(BaseModel):
    force_rerun: bool = True
