from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class StartReviewRequest(BaseModel):
    notes: Optional[str] = None


class DocumentReviewRequest(BaseModel):
    document_id: str
    status: str = Field(..., description="CONFIRMED, CORRECTION_REQUIRED, REJECTED, PENDING")
    correction_reason: Optional[str] = Field(None, description="Structured correction reason if flagged")
    reviewer_comments: Optional[str] = None


class FieldReviewRequest(BaseModel):
    field_key: str
    decision: str = Field(..., description="CONFIRMED, REQUIRES_CORRECTION, ACCEPTED_WITH_REVIEW, NOT_APPLICABLE")
    declared_value: Optional[str] = None
    extracted_value: Optional[str] = None
    reconciliation_status: Optional[str] = None
    notes: Optional[str] = None
    document_id: Optional[str] = None
    document_version_id: Optional[str] = None


class CorrectionRequestPayload(BaseModel):
    correction_reason: str = Field(
        ...,
        description="Structured reason (MISSING_DOCUMENT, ILLEGIBLE_DOCUMENT, FIELD_MISMATCH, INCORRECT_INFORMATION, WRONG_DOCUMENT_TYPE, EXPIRED_OR_OUTDATED_DOCUMENT, ADDITIONAL_INFORMATION_REQUIRED, OTHER)"
    )
    correction_instructions: str = Field(..., description="Actionable instructions for the candidate to rectify their submission")
    flagged_document_ids: Optional[List[str]] = Field(default_factory=list, description="IDs of specific documents requiring re-upload")


class CompleteReviewRequest(BaseModel):
    decision: str = Field(..., description="VERIFIED, CORRECTION_REQUIRED, REJECTED")
    overall_comments: Optional[str] = None


class ReopenReviewRequest(BaseModel):
    reason: str = Field(..., description="Justification for reopening a completed review")


class DocumentReviewItemResponse(BaseModel):
    id: str
    review_id: str
    document_id: str
    document_version_id: Optional[str] = None
    status: str
    correction_reason: Optional[str] = None
    reviewer_comments: Optional[str] = None
    reviewed_by_id: Optional[str] = None
    reviewed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class FieldReviewItemResponse(BaseModel):
    id: str
    review_id: str
    field_key: str
    declared_value: Optional[str] = None
    extracted_value: Optional[str] = None
    reconciliation_status: Optional[str] = None
    decision: str
    notes: Optional[str] = None
    document_id: Optional[str] = None
    document_version_id: Optional[str] = None
    reviewed_by_id: Optional[str] = None
    reviewed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ScrutinyAuditLogResponse(BaseModel):
    id: str
    review_id: Optional[str] = None
    application_id: str
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    user_role: str
    action: str
    previous_status: Optional[str] = None
    new_status: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdmissionReviewResponse(BaseModel):
    id: str
    application_id: str
    reviewer_id: Optional[str] = None
    reviewer_name: Optional[str] = None
    reviewer_email: Optional[str] = None
    status: str
    decision: Optional[str] = None
    overall_comments: Optional[str] = None
    correction_reason: Optional[str] = None
    correction_instructions: Optional[str] = None
    reviewed_document_versions: Dict[str, Any] = Field(default_factory=dict)
    reviewed_reconciliation_id: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    document_reviews: List[DocumentReviewItemResponse] = Field(default_factory=list)
    field_reviews: List[FieldReviewItemResponse] = Field(default_factory=list)
    audit_logs: List[ScrutinyAuditLogResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class CorrectionDocumentItem(BaseModel):
    document_id: str
    document_type_code: str
    document_type_name: str
    current_version_number: int
    correction_reason: Optional[str] = None
    reviewer_comments: Optional[str] = None


class StudentCorrectionSummaryResponse(BaseModel):
    application_id: str
    application_status: str
    review_status: str
    correction_required: bool
    correction_reason: Optional[str] = None
    correction_instructions: Optional[str] = None
    requested_at: Optional[datetime] = None
    affected_documents: List[CorrectionDocumentItem] = Field(default_factory=list)
