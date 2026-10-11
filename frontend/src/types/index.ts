export type UserRole = 
  | 'STUDENT'
  | 'PARENT'
  | 'ADMIN_VERIFIER'
  | 'FINANCE_OFFICER'
  | 'ADMISSION_HEAD'
  | 'SUPER_ADMIN';

export type AdmissionLifecycleState =
  | 'ALLOTTED'
  | 'ACTIVATION_PENDING'
  | 'ACTIVATED'
  | 'APPLICATION_IN_PROGRESS'
  | 'APPLICATION_SUBMITTED'
  | 'DOCUMENT_PROCESSING'
  | 'DOCUMENT_REVIEW'
  | 'CORRECTION_REQUIRED'
  | 'DOCUMENTS_VERIFIED'
  | 'VISIT_SCHEDULED'
  | 'PHYSICAL_VERIFICATION'
  | 'PAYMENT_PENDING'
  | 'PAYMENT_SUBMITTED'
  | 'PAYMENT_VERIFICATION'
  | 'PAYMENT_VERIFIED'
  | 'ADMISSION_CONFIRMED'
  | 'ERP_SYNC_PENDING'
  | 'ERP_SYNCED'
  | 'ONBOARDING'
  | 'INDUCTION_READY'
  | 'ACTIVE_STUDENT'
  | 'WITHDRAWN'
  | 'CANCELLED'
  | 'ALLOTMENT_CHANGED'
  | 'VERIFICATION_FAILED'
  | 'PAYMENT_FAILED'
  | 'ERP_SYNC_FAILED';

export interface User {
  id: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  student_id?: string | null;
  institution_name: string;
  institution_code: string;
  academic_year: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  role: UserRole;
  user_id: string;
  email: string;
}

export interface StudentProfile {
  id: string;
  user_id: string;
  institution_id: string;
  tnea_application_number: string;
  full_name: string;
  date_of_birth: string;
  email: string;
  mobile: string;
  community?: string;
  allotted_branch?: string;
  quota?: string;
  status: AdmissionLifecycleState;
  institution_name: string;
  institution_code: string;
  academic_year: string;
  admission_application_id?: string;
  admission_status?: AdmissionLifecycleState;
  completion_percentage: number;
}

export interface StatusHistoryItem {
  id: string;
  admission_application_id: string;
  previous_status?: string | null;
  new_status: string;
  changed_by: string;
  actor_role: string;
  reason?: string | null;
  metadata_info?: Record<string, any> | null;
  created_at: string;
}

export interface AdmissionApplication {
  id: string;
  student_id: string;
  status: AdmissionLifecycleState;
  completion_percentage: number;
  personal_data?: Record<string, any>;
  academic_data?: Record<string, any>;
  parent_data?: Record<string, any>;
  created_at: string;
  updated_at: string;
  status_history: StatusHistoryItem[];
  student_name?: string;
  tnea_application_number?: string;
  allotted_branch?: string;
}

export interface AdminDashboardMetrics {
  institution_name: string;
  institution_code: string;
  academic_year: string;
  total_allotted: number;
  activation_pending: number;
  activated: number;
  applications_in_progress: number;
  applications_submitted: number;
  document_review: number;
  documents_verified: number;
  admission_confirmed: number;
}

export interface AdminStudentItem {
  student_id: string;
  admission_id: string;
  full_name: string;
  tnea_application_number: string;
  allotted_branch?: string;
  community?: string;
  status: AdmissionLifecycleState;
  completion_percentage: number;
  updated_at: string;
}

export interface TNEAAllotment {
  id: string;
  student_id?: string | null;
  tnea_application_number: string;
  allotment_number: string;
  college_code: string;
  college_name: string;
  branch_code?: string | null;
  branch_name: string;
  community?: string | null;
  quota?: string | null;
  cutoff_mark?: number | null;
  allotment_date: string;
  joining_deadline: string;
  allotment_status: string;
  source: string;
  imported_at: string;
  student_name?: string | null;
  admission_status?: AdmissionLifecycleState | string | null;
}

export interface TNEARecordResult {
  tnea_application_number: string;
  student_name: string;
  branch_name: string;
  allotment_number: string;
  status: 'CREATED' | 'EXISTING_UPDATED' | 'SKIPPED_DUPLICATE' | 'REJECTED_WRONG_INSTITUTION' | 'FAILED_VALIDATION';
  message: string;
  raw_activation_token?: string | null;
}

export interface TNEAImportResponse {
  batch_id: string;
  source: string;
  total_records: number;
  successful_records: number;
  duplicate_records: number;
  skipped_records: number;
  failed_records: number;
  status: 'COMPLETED' | 'PARTIAL' | 'FAILED';
  results: TNEARecordResult[];
  dispatched_notifications_count: number;
}

export interface TNEAImportBatch {
  id: string;
  source: string;
  filename_or_reference?: string | null;
  record_count: number;
  successful_count: number;
  failed_count: number;
  duplicate_count: number;
  skipped_count: number;
  imported_by: string;
  imported_at: string;
  status: string;
}

export interface ActivationResponse {
  success: boolean;
  message: string;
  student_id: string;
  student_name: string;
  tnea_application_number: string;
  email: string;
  new_status: string;
}

// ================= Phase 3 Types =================

export interface ChecklistItem {
  document_type_id: string;
  code: string;
  name: string;
  description?: string | null;
  is_mandatory: boolean;
  mandatory_reason?: string | null;
  allowed_extensions: string[];
  max_file_size_mb: number;
  document_id?: string | null;
  document_status: 'NOT_UPLOADED' | 'UPLOADED' | 'CORRECTION_REQUIRED' | 'RESUBMISSION_REQUIRED' | 'DOCUMENTS_VERIFIED' | string;
  active_version?: number | null;
  rejection_reason?: string | null;
  original_filename?: string | null;
  uploaded_at?: string | null;
  file_size_bytes?: number | null;
  processing_status?: 'NOT_PROCESSED' | 'QUEUED' | 'PROCESSING' | 'COMPLETED' | 'FAILED' | string;
  predicted_document_type?: string | null;
  predicted_document_type_name?: string | null;
  heuristic_confidence?: number | null;
  classifier_name?: string | null;
  classifier_version?: string | null;
  preprocessing_status?: 'NOT_PROCESSED' | 'QUEUED' | 'PROCESSING' | 'COMPLETED' | 'FAILED' | string;
  has_preprocessed_image?: boolean;
  ocr_status?: 'NOT_PROCESSED' | 'QUEUED' | 'PROCESSING' | 'COMPLETED' | 'FAILED' | string;
  has_ocr_result?: boolean;
  extraction_status?: 'NOT_PROCESSED' | 'QUEUED' | 'PROCESSING' | 'COMPLETED' | 'FAILED' | string;
  has_extracted_fields?: boolean;
}



export interface DocumentVersion {
  id: string;
  document_id: string;
  version_number: number;
  original_filename: string;
  mime_type: string;
  file_size_bytes: number;
  file_hash_sha256: string;
  uploaded_at: string;
}

export interface DocumentType {
  id: string;
  code: string;
  name: string;
  description?: string | null;
  allowed_extensions: string[];
  max_file_size_mb: number;
  is_mandatory_default: boolean;
  display_order: number;
}

export interface DocumentUploadResponse {
  document_id: string;
  version_id: string;
  document_type_code: string;
  original_filename: string;
  version_number: number;
  document_status: string;
  message: string;
}

// ================= Phase 4A, 4B & 4C Types =================

export type ProcessingStatus = 'NOT_PROCESSED' | 'QUEUED' | 'PROCESSING' | 'COMPLETED' | 'FAILED';

export interface ClassificationResult {
  id: string;
  job_id: string;
  predicted_document_type: string;
  predicted_document_type_name: string;
  confidence: number;
  confidence_type: string;
  classifier_name: string;
  classifier_version: string;
  rule_used?: string | null;
  reasoning?: string | null;
  raw_metadata: Record<string, any>;
  processed_at: string;
}

export interface PreprocessingResult {
  id: string;
  job_id: string;
  document_id: string;
  document_version_id?: string | null;
  engine_name: string;
  engine_version: string;
  input_dimensions: { width: number; height: number; channels: number };
  output_dimensions: { width: number; height: number; channels: number };
  operations_applied: string[];
  deskew_angle_deg: number;
  output_filename: string;
  output_mime_type: string;
  output_file_size: number;
  processing_time_ms?: number | null;
  created_at: string;
}

export interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface OCRBlock {
  text: string;
  confidence?: number | null;
  bounding_box: BoundingBox;
  block_num?: number;
  line_num?: number;
  word_num?: number;
}

export interface OCRResult {
  id: string;
  job_id: string;
  document_id: string;
  document_version_id?: string | null;
  preprocessing_result_id?: string | null;
  engine_name: string;
  engine_version: string;
  language: string;
  image_sha256: string;
  ocr_confidence?: number | null;
  full_text?: string | null;
  blocks: OCRBlock[];
  processing_time_ms?: number | null;
  error_message?: string | null;
  created_at: string;
}

export interface DocumentProcessingJob {
  id: string;
  document_id: string;
  document_version_id?: string | null;
  processing_type: string;
  status: ProcessingStatus;
  requested_by: string;
  started_at?: string | null;
  completed_at?: string | null;
  processing_time_ms?: number | null;
  engine_name: string;
  engine_version: string;
  error_code?: string | null;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
  classification_result?: ClassificationResult | null;
  preprocessing_result?: PreprocessingResult | null;
  ocr_result?: OCRResult | null;
  extraction_result?: DocumentExtractionResult | null;
}

// ================= Phase 4D Field Extraction Types =================

export interface FieldSourceProvenance {
  ocr_block_indices: number[];
  bounding_box?: BoundingBox | null;
  context?: string | null;
  source_document_version?: number;
}

export interface ExtractedField {
  field_name: string;
  raw_value?: string | null;
  normalized_value?: any;
  value_type: string;
  confidence: number;
  requires_review: boolean;
  review_reason?: string | null;
  is_derived?: boolean;
  provenance?: FieldSourceProvenance | null;
}

export interface DocumentExtractionResult {
  id: string;
  document_id: string;
  document_version: number;
  processing_job_id: string;
  ocr_result_id: string;
  extractor_name: string;
  extractor_version: string;
  document_type: string;
  overall_confidence?: number | null;
  is_valid_format: boolean;
  fields: Record<string, ExtractedField>;
  calculated_fields: Record<string, ExtractedField>;
  validation_warnings: string[];
  processing_time_ms?: number | null;
  created_at: string;
}

export interface DocumentProcessingHistoryResponse {
  document_id: string;
  total_jobs: number;
  latest_job?: DocumentProcessingJob | null;
  jobs: DocumentProcessingJob[];
}

// ================= Phase 4E Cross-Document Reconciliation Types =================

export type ReconciliationStatus = 'MATCH' | 'DISCREPANCY_DETECTED' | 'DISCREPANCY' | 'PENDING_SCRUTINY' | 'INCOMPLETE_DOCUMENTS';

export interface ReconciliationFindingProvenance {
  document_id?: string | null;
  document_version?: number | null;
  extraction_result_id?: string | null;
  ocr_block_indices: number[];
  bounding_box?: BoundingBox | null;
  comparison_method: string;
  tolerance_applied?: string | null;
}

export interface ReconciliationFinding {
  rule_id: string;
  rule_name: string;
  field_key: string;
  status: 'MATCH' | 'DISCREPANCY' | 'PENDING_SCRUTINY' | 'INCOMPLETE_DOCUMENTS';
  declared_value?: any;
  extracted_value?: any;
  allotment_baseline_value?: any;
  delta?: number | null;
  discrepancy_reason?: string | null;
  human_review_required: boolean;
  review_reason?: string | null;
  provenance?: ReconciliationFindingProvenance | null;
}

export interface CrossDocumentReconciliation {
  id: string;
  application_id: string;
  overall_status: ReconciliationStatus;
  participating_document_versions: Record<string, any>;
  total_rules_evaluated: number;
  passed_rules_count: number;
  discrepancy_count: number;
  pending_scrutiny_count: number;
  incomplete_count: number;
  findings: ReconciliationFinding[];
  discrepancy_summary: string[];
  requires_human_review: boolean;
  reconciliation_time_ms?: number | null;
  created_at: string;
}




export interface ApplicationDraft {
  gender?: string;
  blood_group?: string;
  nationality?: string;
  religion?: string;
  caste?: string;
  mother_tongue?: string;
  aadhaar_number?: string;
  
  address_line1?: string;
  address_line2?: string;
  city?: string;
  district?: string;
  state?: string;
  pincode?: string;
  emergency_contact_name?: string;
  emergency_contact_phone?: string;
  emergency_contact_relation?: string;
  
  father_name?: string;
  father_occupation?: string;
  father_mobile?: string;
  father_email?: string;
  mother_name?: string;
  mother_occupation?: string;
  mother_mobile?: string;
  mother_email?: string;
  guardian_name?: string;
  guardian_occupation?: string;
  guardian_mobile?: string;
  guardian_relation?: string;
  annual_family_income?: number;
  
  tenth_school_name?: string;
  tenth_board?: string;
  tenth_year_of_passing?: number;
  tenth_registration_number?: string;
  tenth_total_marks?: number;
  tenth_max_marks?: number;
  tenth_percentage?: number;
  
  twelfth_school_name?: string;
  twelfth_board?: string;
  twelfth_year_of_passing?: number;
  twelfth_registration_number?: string;
  twelfth_total_marks?: number;
  twelfth_max_marks?: number;
  twelfth_percentage?: number;
  twelfth_maths_marks?: number;
  twelfth_physics_marks?: number;
  twelfth_chemistry_marks?: number;
  twelfth_cutoff_marks?: number;
  
  is_first_graduate?: boolean;
  is_pmss_scholarship?: boolean;
  is_7_5_govt_quota?: boolean;
  is_hostel_required?: boolean;
  is_transport_required?: boolean;
  
  declaration_accepted?: boolean;
}

export interface SectionCompletion {
  completed: boolean;
  fields_filled: number;
  fields_total: number;
  missing_fields: string[];
}

export interface ApplicationCompletion {
  overall_percentage: number;
  sections: Record<string, SectionCompletion>;
  documents_uploaded: number;
  mandatory_documents_total: number;
  mandatory_documents_uploaded: number;
  can_submit: boolean;
  blockers: string[];
}

export interface ApplicationDetail {
  id: string;
  application_number?: string | null;
  student_id: string;
  status: AdmissionLifecycleState;
  completion_percentage: number;
  
  student_name: string;
  student_dob: string;
  student_email: string;
  student_mobile: string;
  tnea_application_number: string;
  allotted_branch?: string | null;
  community?: string | null;
  quota?: string | null;
  
  allotment_order_number?: string | null;
  allotment_quota?: string | null;
  allotted_category?: string | null;
  allotted_college_code?: string | null;
  allotted_branch_name?: string | null;
  
  gender?: string | null;
  blood_group?: string | null;
  nationality?: string | null;
  religion?: string | null;
  caste?: string | null;
  mother_tongue?: string | null;
  aadhaar_number?: string | null;
  
  address_line1?: string | null;
  address_line2?: string | null;
  city?: string | null;
  district?: string | null;
  state?: string | null;
  pincode?: string | null;
  emergency_contact_name?: string | null;
  emergency_contact_phone?: string | null;
  emergency_contact_relation?: string | null;
  
  father_name?: string | null;
  father_occupation?: string | null;
  father_mobile?: string | null;
  father_email?: string | null;
  mother_name?: string | null;
  mother_occupation?: string | null;
  mother_mobile?: string | null;
  mother_email?: string | null;
  guardian_name?: string | null;
  guardian_occupation?: string | null;
  guardian_mobile?: string | null;
  guardian_relation?: string | null;
  annual_family_income?: number | null;
  
  tenth_school_name?: string | null;
  tenth_board?: string | null;
  tenth_year_of_passing?: number | null;
  tenth_registration_number?: string | null;
  tenth_total_marks?: number | null;
  tenth_max_marks?: number | null;
  tenth_percentage?: number | null;
  
  twelfth_school_name?: string | null;
  twelfth_board?: string | null;
  twelfth_year_of_passing?: number | null;
  twelfth_registration_number?: string | null;
  twelfth_total_marks?: number | null;
  twelfth_max_marks?: number | null;
  twelfth_percentage?: number | null;
  twelfth_maths_marks?: number | null;
  twelfth_physics_marks?: number | null;
  twelfth_chemistry_marks?: number | null;
  twelfth_cutoff_marks?: number | null;
  
  is_first_graduate: boolean;
  is_pmss_scholarship: boolean;
  is_7_5_govt_quota: boolean;
  is_hostel_required: boolean;
  is_transport_required: boolean;
  
  declaration_accepted: boolean;
  declaration_accepted_at?: string | null;
  submitted_at?: string | null;
  created_at: string;
  updated_at: string;
  
  checklist: ChecklistItem[];
}

export interface ApplicationSubmissionResponse {
  admission_id: string;
  application_number: string;
  status: string;
  submitted_at: string;
  message: string;
}

export interface AdminApplicationListItem {
  application_id: string;
  application_number?: string | null;
  student_id: string;
  student_name: string;
  tnea_application_number: string;
  allotted_branch?: string | null;
  community?: string | null;
  quota?: string | null;
  status: string;
  completion_percentage: number;
  submitted_at?: string | null;
  updated_at: string;
}

// Phase 4F Human-In-The-Loop Scrutiny Types
export type ReviewStatus =
  | 'NOT_STARTED'
  | 'IN_REVIEW'
  | 'CORRECTION_REQUIRED'
  | 'RESUBMISSION_PENDING'
  | 'VERIFIED'
  | 'REJECTED';

export type ReviewDecision = 'VERIFIED' | 'CORRECTION_REQUIRED' | 'REJECTED';

export type FieldReviewDecision =
  | 'CONFIRMED'
  | 'REQUIRES_CORRECTION'
  | 'ACCEPTED_WITH_REVIEW'
  | 'NOT_APPLICABLE';

export type CorrectionReason =
  | 'MISSING_DOCUMENT'
  | 'ILLEGIBLE_DOCUMENT'
  | 'FIELD_MISMATCH'
  | 'INCORRECT_INFORMATION'
  | 'WRONG_DOCUMENT_TYPE'
  | 'EXPIRED_OR_OUTDATED_DOCUMENT'
  | 'ADDITIONAL_INFORMATION_REQUIRED'
  | 'OTHER';

export interface DocumentReviewItem {
  id: string;
  review_id: string;
  document_id: string;
  document_version_id?: string | null;
  status: string;
  correction_reason?: string | null;
  reviewer_comments?: string | null;
  reviewed_by_id?: string | null;
  reviewed_at?: string | null;
}

export interface FieldReviewItem {
  id: string;
  review_id: string;
  field_key: string;
  declared_value?: string | null;
  extracted_value?: string | null;
  reconciliation_status?: string | null;
  decision: FieldReviewDecision;
  notes?: string | null;
  document_id?: string | null;
  document_version_id?: string | null;
  reviewed_by_id?: string | null;
  reviewed_at?: string | null;
}

export interface ScrutinyAuditLog {
  id: string;
  review_id?: string | null;
  application_id: string;
  user_id?: string | null;
  user_name?: string | null;
  user_role: string;
  action: string;
  previous_status?: string | null;
  new_status?: string | null;
  details: Record<string, any>;
  created_at: string;
}

export interface AdmissionReview {
  id: string;
  application_id: string;
  reviewer_id?: string | null;
  reviewer_name?: string | null;
  reviewer_email?: string | null;
  status: ReviewStatus;
  decision?: ReviewDecision | null;
  overall_comments?: string | null;
  correction_reason?: string | null;
  correction_instructions?: string | null;
  reviewed_document_versions: Record<string, number>;
  reviewed_reconciliation_id?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  created_at: string;
  updated_at: string;
  document_reviews: DocumentReviewItem[];
  field_reviews: FieldReviewItem[];
  audit_logs: ScrutinyAuditLog[];
}

export interface CorrectionDocumentItem {
  document_id: string;
  document_type_code: string;
  document_type_name: string;
  current_version_number: number;
  correction_reason?: string | null;
  reviewer_comments?: string | null;
}

export interface StudentCorrectionSummary {
  application_id: string;
  application_status: string;
  review_status: string;
  correction_required: boolean;
  correction_reason?: string | null;
  correction_instructions?: string | null;
  requested_at?: string | null;
  affected_documents: CorrectionDocumentItem[];
}

// ================= Phase 5 Physical Verification Types =================

export type AppointmentStatus =
  | 'SCHEDULED'
  | 'CONFIRMED'
  | 'CHECKED_IN'
  | 'IN_PROGRESS'
  | 'COMPLETED'
  | 'MISSED'
  | 'CANCELLED'
  | 'RESCHEDULED';

export type PhysicalSessionStatus =
  | 'NOT_STARTED'
  | 'IN_PROGRESS'
  | 'COMPLETED'
  | 'REOPENED';

export type PhysicalVerificationDecision =
  | 'VERIFIED'
  | 'PARTIALLY_VERIFIED'
  | 'CORRECTION_REQUIRED'
  | 'REJECTED'
  | 'PENDING';

export type PhysicalDocDecision =
  | 'VERIFIED'
  | 'NOT_VERIFIED'
  | 'CORRECTION_REQUIRED'
  | 'NOT_APPLICABLE'
  | 'PENDING';

export type PhysicalCorrectionReason =
  | 'ORIGINAL_NOT_PRESENT'
  | 'ORIGINAL_ILLEGIBLE'
  | 'INFORMATION_MISMATCH'
  | 'WRONG_DOCUMENT'
  | 'OUTDATED_DOCUMENT'
  | 'MISSING_REQUIRED_DOCUMENT'
  | 'ADDITIONAL_DOCUMENT_REQUIRED'
  | 'OTHER';

export interface PhysicalChecklistChecks {
  original_presented: boolean;
  document_legible: boolean;
  name_matches: boolean;
  dob_matches?: boolean;
  id_matches?: boolean;
  photo_check_done?: boolean;
  custom_checks?: Record<string, any>;
}

export interface PhysicalDocumentVerification {
  id: string;
  session_id: string;
  document_id: string;
  document_version_id?: string | null;
  document_type_id?: string | null;
  document_type_code?: string;
  document_type_name?: string;
  version_number?: number;
  officer_decision: PhysicalDocDecision;
  verification_notes?: string | null;
  discrepancy_reason?: string | null;
  checklist_checks: PhysicalChecklistChecks;
  verified_by_id?: string | null;
  verified_by_name?: string | null;
  verified_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface PhysicalVerificationSession {
  id: string;
  application_id: string;
  appointment_id?: string | null;
  officer_id?: string | null;
  officer_name?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  session_status: PhysicalSessionStatus;
  overall_decision: PhysicalVerificationDecision;
  officer_notes?: string | null;
  created_at: string;
  updated_at: string;
  document_verifications: PhysicalDocumentVerification[];
}

export interface PhysicalVerificationAppointment {
  id: string;
  application_id: string;
  appointment_date: string;
  start_time: string;
  end_time: string;
  token_number: string;
  checkin_token: string;
  location: string;
  counter_desk?: string | null;
  counter?: string | null;
  appointment_status: AppointmentStatus;
  notes?: string | null;
  created_by_id?: string | null;
  checked_in_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface AvailableSlot {
  slot_date: string;
  start_time: string;
  end_time: string;
  available_capacity: number;
  location: string;
  counter_desk: string;
}

export interface PhysicalVerificationAuditLog {
  id: string;
  application_id: string;
  appointment_id?: string | null;
  session_id?: string | null;
  actor_id?: string | null;
  actor_name?: string | null;
  actor_role?: string | null;
  action: string;
  details?: Record<string, any> | null;
  created_at: string;
}

export interface PhysicalCorrectionItem {
  document_id: string;
  document_type_code: string;
  document_type_name: string;
  version_number?: number;
  document_version_number?: number;
  discrepancy_reason?: string | null;
  reason?: string | null;
  officer_notes?: string | null;
  notes?: string | null;
}

export interface StudentPhysicalVerificationSummary {
  application_id: string;
  application_number: string;
  has_appointment: boolean;
  appointment?: PhysicalVerificationAppointment | null;
  session_status: string;
  overall_decision: PhysicalVerificationDecision | string;
  has_corrections: boolean;
  corrections: PhysicalCorrectionItem[];
  active_correction_request?: PhysicalCorrectionItem | null;
  session?: PhysicalVerificationSession | null;
}

export interface CheckInResult {
  message: string;
  appointment_id: string;
  token_number: string;
  application_id: string;
  candidate_name: string;
  allotted_branch?: string | null;
  checked_in_at: string;
  counter_desk?: string | null;
}

// ==============================================================================
// PHASE 6: PAYMENT & DEMAND DRAFT INTERFACES
// ==============================================================================

export type PaymentMethod = 'DEMAND_DRAFT' | 'DEMO_ONLINE_PAYMENT';

export type PaymentStatus = 
  | 'INITIATED'
  | 'PENDING'
  | 'SUBMITTED'
  | 'UNDER_REVIEW'
  | 'VERIFIED'
  | 'REJECTED'
  | 'CORRECTION_REQUIRED'
  | 'FAILED'
  | 'CANCELLED';

export type PaymentCorrectionReason =
  | 'INVALID_DD_DETAILS'
  | 'AMOUNT_MISMATCH'
  | 'MISSING_SUPPORTING_DOCUMENT'
  | 'ILLEGIBLE_DOCUMENT'
  | 'OUTDATED_DOCUMENT'
  | 'INCORRECT_REFERENCE'
  | 'DUPLICATE_PAYMENT_REFERENCE'
  | 'OTHER';

export interface FeeRequirement {
  id: string;
  academic_year: string;
  category: string;
  quota: string;
  amount: number;
  currency: string;
  description?: string | null;
  is_active: boolean;
}

export interface DemandDraftSubmission {
  id: string;
  payment_id: string;
  dd_number: string;
  dd_date: string;
  bank_name: string;
  branch_name?: string | null;
  amount: number;
  supporting_document_id?: string | null;
  supporting_document_version_id?: string | null;
  submitted_by_id: string;
  submitted_at: string;
  finance_verified_by_id?: string | null;
  finance_verified_at?: string | null;
  finance_notes?: string | null;
}

export interface PaymentAuditLog {
  id: string;
  application_id: string;
  payment_id: string;
  actor_id?: string | null;
  actor_name?: string | null;
  actor_role: string;
  action: string;
  details?: Record<string, any> | null;
  created_at: string;
}

export interface PaymentTransaction {
  id: string;
  application_id: string;
  payment_reference: string;
  payment_method: PaymentMethod | string;
  amount: number;
  currency: string;
  status: PaymentStatus | string;
  initiated_at: string;
  submitted_at?: string | null;
  verified_at?: string | null;
  verified_by_id?: string | null;
  rejection_reason?: string | null;
  notes?: string | null;
  created_at: string;
  updated_at: string;
  fee_requirement?: FeeRequirement | null;
  dd_submission?: DemandDraftSubmission | null;
  application_number?: string | null;
  candidate_name?: string | null;
}

export interface StudentPaymentSummary {
  application_id: string;
  application_number: string;
  has_active_payment: boolean;
  fee_requirement?: FeeRequirement | null;
  active_payment?: PaymentTransaction | null;
  payment_status: string;
  is_payment_verified: boolean;
  has_correction_required: boolean;
  correction_reason?: string | null;
  correction_instructions?: string | null;
  duplicate_warning?: string | null;
}

// ==============================================================================
// PHASE 7: ERP STAGING & INTEGRATION INTERFACES
// ==============================================================================

export type ERPRecordStatus =
  | 'NOT_READY'
  | 'READY_FOR_STAGING'
  | 'STAGED'
  | 'SYNC_PENDING'
  | 'SYNCING'
  | 'SYNCED'
  | 'SYNC_FAILED'
  | 'RETRY_PENDING'
  | 'CANCELLED';

export interface ERPIntegrationEvent {
  id: string;
  erp_record_id: string;
  event_type: string;
  adapter_name: string;
  request_reference?: string | null;
  response_reference?: string | null;
  status: string;
  error_summary?: string | null;
  details?: Record<string, any> | null;
  created_at: string;
}

export interface ERPAdmissionRecord {
  id: string;
  application_id: string;
  staging_reference: string;
  payload: Record<string, any>;
  payload_hash: string;
  payload_version: number;
  status: ERPRecordStatus | string;
  validation_errors?: string[] | null;
  retry_count: number;
  last_error?: string | null;
  staged_at: string;
  synced_at?: string | null;
  created_at: string;
  updated_at: string;
  application_number?: string | null;
  candidate_name?: string | null;
  allotted_branch?: string | null;
  integration_events?: ERPIntegrationEvent[];
}

export interface ERPReadinessCheck {
  application_id: string;
  is_ready: boolean;
  status: string;
  validation_errors: string[];
  readiness_checks: {
    identity_present: boolean;
    allotment_present: boolean;
    physical_verification_completed: boolean;
    payment_verified: boolean;
    zero_blocking_corrections: boolean;
  };
}

// ==============================================================================
// PHASE 8: NOTIFICATIONS INTERFACES
// ==============================================================================

export interface NotificationItem {
  id: string;
  user_id: string;
  application_id?: string | null;
  type: string;
  title: string;
  message: string;
  severity: 'INFO' | 'WARNING' | 'SUCCESS' | 'ERROR' | string;
  channel: 'IN_APP' | 'EMAIL_MOCK' | 'SMS_MOCK' | string;
  status: 'QUEUED' | 'SENT' | 'DELIVERED' | 'FAILED' | 'READ' | string;
  read_at?: string | null;
  metadata_json?: Record<string, any> | null;
  created_at: string;
}

export interface NotificationSummary {
  unread_count: number;
  total_count: number;
  notifications: NotificationItem[];
}

// ==============================================================================
// PHASE 8: UNIFIED OPERATIONAL TIMELINE & JOURNEY
// ==============================================================================

export interface TimelineEvent {
  id: string;
  stage: string;
  event_type: string;
  actor_type: 'SYSTEM_EVENT' | 'HUMAN_ACTION';
  actor_name: string;
  actor_role: string;
  title: string;
  description: string;
  status: string;
  reference_id?: string | null;
  metadata?: Record<string, any> | null;
  timestamp: string;
}

export interface StudentJourneyTimeline {
  application_id: string;
  application_number: string;
  current_status: string;
  candidate_name: string;
  allotted_branch?: string | null;
  stages: {
    allotment: string;
    activation: string;
    application: string;
    documents: string;
    digital_scrutiny: string;
    physical_verification: string;
    payment: string;
    erp: string;
  };
  events: TimelineEvent[];
}

// ==============================================================================
// PHASE 8: OPERATIONAL ANALYTICS INTERFACES
// ==============================================================================

export interface ApplicationMetrics {
  total: number;
  submitted: number;
  incomplete: number;
  correction_required: number;
}

export interface DocumentMetrics {
  total_uploaded: number;
  processing_or_ocr: number;
  verified: number;
  correction_required: number;
  pending_scrutiny: number;
}

export interface PhysicalMetrics {
  appointments_scheduled: number;
  checked_in: number;
  in_progress: number;
  completed: number;
  correction_required: number;
  pending: number;
}

export interface PaymentMetrics {
  total_transactions: number;
  pending: number;
  submitted: number;
  verified: number;
  rejected: number;
  correction_required: number;
  total_verified_amount: number;
}

export interface ERPMetrics {
  total_records: number;
  ready_for_staging: number;
  staged: number;
  syncing: number;
  synced: number;
  sync_failed: number;
}

export interface NotificationMetrics {
  total_dispatched: number;
  unread: number;
  failed: number;
}

export interface ProcessingTimes {
  avg_application_review_hours?: number | null;
  avg_physical_verification_hours?: number | null;
  avg_payment_verification_hours?: number | null;
  avg_erp_sync_seconds?: number | null;
}

export interface AnalyticsOverview {
  date_filter: string;
  institution_name: string;
  academic_year: string;
  computed_at: string;
  is_read_only: boolean;
  applications: ApplicationMetrics;
  documents: DocumentMetrics;
  physical_verification: PhysicalMetrics;
  payments: PaymentMetrics;
  erp: ERPMetrics;
  notifications: NotificationMetrics;
  processing_times_hours: ProcessingTimes;
  bottlenecks: string[];
}

// ==============================================================================
// Phase 9: RAG Chatbot & Knowledge Management Types
// ==============================================================================

export type ChatRole = 'USER' | 'ASSISTANT' | 'SYSTEM';
export type ResponseType = 'GROUNDED_ANSWER' | 'INSUFFICIENT_EVIDENCE' | 'SECURITY_REFUSAL' | 'SYSTEM_ERROR';
export type KnowledgeCategory = 'ADMISSION_GUIDELINES' | 'DOCUMENT_VERIFICATION' | 'PHYSICAL_VERIFICATION' | 'FEE_AND_PAYMENT' | 'GENERAL' | 'FAQ';
export type KnowledgeLifecycleState = 'DRAFT' | 'PROCESSING' | 'READY' | 'ACTIVE' | 'ARCHIVED';

export interface SourceCitation {
  chunk_id: string;
  document_id: string;
  document_title: string;
  document_category: string;
  version_number: number;
  section_title?: string | null;
  page_number?: number | null;
  score: number;
}

export interface ChatMessage {
  id: string;
  session_id: string;
  user_id: string;
  sender_role: ChatRole;
  message: string;
  response_type?: ResponseType | null;
  retrieved_sources_json?: SourceCitation[];
  personal_context_used_json?: {
    used: boolean;
    app_status?: string | null;
    [key: string]: any;
  } | null;
  latency_ms?: number | null;
  created_at: string;
}

export interface ChatSession {
  id: string;
  user_id: string;
  application_id?: string | null;
  title: string;
  created_at: string;
  updated_at: string;
  messages?: ChatMessage[];
}

export interface KnowledgeChunk {
  id: string;
  document_id: string;
  version_id: string;
  chunk_index: number;
  section_title?: string | null;
  page_number?: number | null;
  content: string;
  token_count: number;
  created_at: string;
}

export interface KnowledgeDocumentVersion {
  id: string;
  document_id: string;
  version_number: number;
  lifecycle_state: KnowledgeLifecycleState;
  content: string;
  content_hash: string;
  created_by_id?: string | null;
  activated_at?: string | null;
  archived_at?: string | null;
  created_at: string;
  chunks?: KnowledgeChunk[];
}

export interface KnowledgeDocument {
  id: string;
  title: string;
  category: KnowledgeCategory;
  description?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  versions?: KnowledgeDocumentVersion[];
}

export interface KnowledgeIngestPayload {
  title: string;
  content: string;
  category: KnowledgeCategory;
  description?: string;
  auto_activate?: boolean;
}

// =============================================================================
// PHASE 10 ONBOARDING & PARENT PORTAL TYPES
// =============================================================================

export type StudentType = 'UNSPECIFIED' | 'DAY_SCHOLAR' | 'HOSTELLER';
export type StudentTypeStatus = 'UNSPECIFIED' | 'STUDENT_REQUESTED' | 'ADMIN_CONFIRMED';
export type OnboardingStatus = 
  | 'ONBOARDING_NOT_STARTED'
  | 'ONBOARDING_PROFILE_PENDING'
  | 'ONBOARDING_IN_PROGRESS'
  | 'ONBOARDING_CHECKLIST_ACTIVE'
  | 'INDUCTION_READY'
  | 'FIRST_YEAR_ACTIVE'
  | 'ONBOARDING_BLOCKED'
  | 'WITHDRAWN';

export type ParentLinkStatus = 'PENDING' | 'ACTIVE' | 'REVOKED' | 'EXPIRED';

export interface OnboardingChecklistItem {
  id: string;
  item_key: string;
  title: string;
  category: string;
  student_type_scope: string;
  is_mandatory: boolean;
  is_acknowledged: boolean;
  acknowledged_at?: string | null;
  source_reference: string;
  sort_order: number;
}

export interface OnboardingProfile {
  id: string;
  student_id: string;
  application_id: string;
  academic_year: string;
  student_type: StudentType;
  student_type_status: StudentTypeStatus;
  onboarding_status: OnboardingStatus;
  overall_completion_percentage: number;
  checklist_items?: OnboardingChecklistItem[];
  created_at: string;
  updated_at: string;
}

export interface ParentInvitationResponse {
  link_id: string;
  invite_token: string;
  relationship: string;
  expires_at: string;
  status: string;
}

export interface ParentRedeemPayload {
  invite_token: string;
  parent_name: string;
  phone: string;
  email?: string;
}

export interface ParentRedeemResponse {
  success: boolean;
  message: string;
  link_id: string;
  student_id: string;
  relationship: string;
  status: string;
}

export interface GuidanceCard {
  category: string;
  title: string;
  source_reference: string;
  attribution?: string;
  data: Record<string, any>;
}

export interface InaugurationEvent {
  id: string;
  academic_year: string;
  event_name: string;
  event_date: string;
  reporting_time: string;
  ceremony_time: string;
  venue: string;
  instructions_student: string;
  instructions_parent: string;
  event_status: 'UPCOMING' | 'TODAY' | 'PAST';
}

export interface TransportConfig {
  is_configured: boolean;
  college_code: string;
  message?: string;
  routes: any[];
  general_instructions?: string;
}

export interface OnboardingAuditLog {
  id: string;
  actor_id: string;
  actor_role: string;
  action: string;
  profile_id?: string | null;
  student_id?: string | null;
  details_json: Record<string, any>;
  created_at: string;
}


