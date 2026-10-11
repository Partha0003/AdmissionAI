from app.models.institution import Institution
from app.models.role import Role
from app.models.user import User
from app.models.student import Student
from app.models.admission import AdmissionApplication, AdmissionStatusHistory
from app.models.tnea_allotment import TNEAAllotment, TNEAImportBatch
from app.models.activation_token import StudentActivationToken
from app.models.document import DocumentType, DocumentRule, Document, DocumentVersion
from app.models.document_processing import (
    DocumentProcessingJob,
    ClassificationResult,
    PreprocessingResult,
    OCRResult,
    DocumentExtractionResult,
    CrossDocumentReconciliation,
    ProcessingStatus,
    ProcessingType,
)

from app.models.scrutiny import (
    ReviewStatus,
    ReviewDecision,
    FieldReviewDecision,
    CorrectionReason,
    ScrutinyAction,
    AdmissionReview,
    DocumentReviewItem,
    FieldReviewItem,
    ScrutinyAuditLog,
)

from app.models.physical_verification import (
    AppointmentStatus,
    PhysicalSessionStatus,
    PhysicalVerificationDecision,
    PhysicalDocDecision,
    PhysicalCorrectionReason,
    PhysicalVerificationAction,
    PhysicalVerificationAppointment,
    PhysicalVerificationSession,
    PhysicalDocumentVerification,
    PhysicalVerificationAuditLog,
)

from app.models.payment import (
    PaymentMethod,
    PaymentStatus,
    PaymentCorrectionReason,
    PaymentAuditAction,
    FeeRequirement,
    PaymentTransaction,
    DemandDraftSubmission,
    PaymentAuditLog,
)

from app.models.erp import (
    ERPRecordStatus,
    ERPIntegrationStatus,
    ERPAdmissionRecord,
    ERPIntegrationEvent,
)

from app.models.notification import (
    NotificationType,
    NotificationSeverity,
    NotificationChannel,
    NotificationStatus,
    Notification,
)

from app.models.rag import (
    KnowledgeCategory,
    KnowledgeLifecycleState,
    ResponseType,
    ChatRole,
    KnowledgeDocument,
    KnowledgeDocumentVersion,
    KnowledgeChunk,
    ChatSession,
    ChatMessage,
    ChatAuditLog,
)

from app.models.onboarding import (
    StudentType,
    StudentTypeStatus,
    OnboardingStatus,
    ParentLinkStatus,
    ChecklistCategory,
    StudentTypeScope,
    GuidanceCategory,
    EventStatus,
    OnboardingProfile,
    ParentGuardian,
    StudentGuardianLink,
    OnboardingChecklistItem,
    OnboardingGuidanceConfiguration,
    InaugurationEvent,
    TransportConfiguration,
    OnboardingAuditLog,
)

__all__ = [
    "Institution",
    "Role",
    "User",
    "Student",
    "AdmissionApplication",
    "AdmissionStatusHistory",
    "TNEAAllotment",
    "TNEAImportBatch",
    "StudentActivationToken",
    "DocumentType",
    "DocumentRule",
    "Document",
    "DocumentVersion",
    "DocumentProcessingJob",
    "ClassificationResult",
    "PreprocessingResult",
    "OCRResult",
    "DocumentExtractionResult",
    "CrossDocumentReconciliation",
    "ProcessingStatus",
    "ProcessingType",
    "ReviewStatus",
    "ReviewDecision",
    "FieldReviewDecision",
    "CorrectionReason",
    "ScrutinyAction",
    "AdmissionReview",
    "DocumentReviewItem",
    "FieldReviewItem",
    "ScrutinyAuditLog",
    "AppointmentStatus",
    "PhysicalSessionStatus",
    "PhysicalVerificationDecision",
    "PhysicalDocDecision",
    "PhysicalCorrectionReason",
    "PhysicalVerificationAction",
    "PhysicalVerificationAppointment",
    "PhysicalVerificationSession",
    "PhysicalDocumentVerification",
    "PhysicalVerificationAuditLog",
    "PaymentMethod",
    "PaymentStatus",
    "PaymentCorrectionReason",
    "PaymentAuditAction",
    "FeeRequirement",
    "PaymentTransaction",
    "DemandDraftSubmission",
    "PaymentAuditLog",
    "ERPRecordStatus",
    "ERPIntegrationStatus",
    "ERPAdmissionRecord",
    "ERPIntegrationEvent",
    "NotificationType",
    "NotificationSeverity",
    "NotificationChannel",
    "NotificationStatus",
    "Notification",
    "KnowledgeCategory",
    "KnowledgeLifecycleState",
    "ResponseType",
    "ChatRole",
    "KnowledgeDocument",
    "KnowledgeDocumentVersion",
    "KnowledgeChunk",
    "ChatSession",
    "ChatMessage",
    "ChatAuditLog",
    "StudentType",
    "StudentTypeStatus",
    "OnboardingStatus",
    "ParentLinkStatus",
    "ChecklistCategory",
    "StudentTypeScope",
    "GuidanceCategory",
    "EventStatus",
    "OnboardingProfile",
    "ParentGuardian",
    "StudentGuardianLink",
    "OnboardingChecklistItem",
    "OnboardingGuidanceConfiguration",
    "InaugurationEvent",
    "TransportConfiguration",
    "OnboardingAuditLog",
]




