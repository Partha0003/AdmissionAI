import { apiClient } from './api';
import {
  AdmissionReview,
  DocumentReviewItem,
  FieldReviewItem,
  ScrutinyAuditLog,
  StudentCorrectionSummary,
  FieldReviewDecision,
} from '../types';

export const ScrutinyService = {
  // 1. Start Review
  startReview: async (applicationId: string, notes?: string): Promise<AdmissionReview> => {
    const res = await apiClient.post<AdmissionReview>(`/scrutiny/applications/${applicationId}/start`, {
      notes: notes || undefined,
    });
    return res.data;
  },

  // 2. Get Current Review (Staff or Student Anti-IDOR)
  getCurrentReview: async (applicationId: string): Promise<AdmissionReview> => {
    const res = await apiClient.get<AdmissionReview>(`/scrutiny/applications/${applicationId}/current`);
    return res.data;
  },

  // 3. Get Review History
  getReviewHistory: async (applicationId: string): Promise<AdmissionReview[]> => {
    const res = await apiClient.get<AdmissionReview[]>(`/scrutiny/applications/${applicationId}/history`);
    return res.data;
  },

  // 4. Record Document Review
  reviewDocument: async (
    applicationId: string,
    data: {
      document_id: string;
      status: string;
      correction_reason?: string;
      reviewer_comments?: string;
    }
  ): Promise<DocumentReviewItem> => {
    const res = await apiClient.post<DocumentReviewItem>(
      `/scrutiny/applications/${applicationId}/documents/review`,
      data
    );
    return res.data;
  },

  // 5. Record Field Review
  reviewField: async (
    applicationId: string,
    data: {
      field_key: string;
      decision: FieldReviewDecision;
      declared_value?: string | null;
      extracted_value?: string | null;
      reconciliation_status?: string | null;
      notes?: string | null;
      document_id?: string | null;
      document_version_id?: string | null;
    }
  ): Promise<FieldReviewItem> => {
    const res = await apiClient.post<FieldReviewItem>(
      `/scrutiny/applications/${applicationId}/fields/review`,
      data
    );
    return res.data;
  },

  // 6. Request Candidate Correction
  requestCorrection: async (
    applicationId: string,
    data: {
      correction_reason: string;
      correction_instructions: string;
      flagged_document_ids?: string[];
    }
  ): Promise<AdmissionReview> => {
    const res = await apiClient.post<AdmissionReview>(
      `/scrutiny/applications/${applicationId}/request-correction`,
      data
    );
    return res.data;
  },

  // 7. Complete Review
  completeReview: async (
    applicationId: string,
    data: {
      decision: 'VERIFIED' | 'CORRECTION_REQUIRED' | 'REJECTED';
      overall_comments?: string;
    }
  ): Promise<AdmissionReview> => {
    const res = await apiClient.post<AdmissionReview>(
      `/scrutiny/applications/${applicationId}/complete`,
      data
    );
    return res.data;
  },

  // 8. Reopen Review (ADMISSION_HEAD / SUPER_ADMIN)
  reopenReview: async (applicationId: string, reason: string): Promise<AdmissionReview> => {
    const res = await apiClient.post<AdmissionReview>(
      `/scrutiny/applications/${applicationId}/reopen`,
      { reason }
    );
    return res.data;
  },

  // 9. Get Audit Logs
  getAuditLogs: async (applicationId: string): Promise<ScrutinyAuditLog[]> => {
    const res = await apiClient.get<ScrutinyAuditLog[]>(
      `/scrutiny/applications/${applicationId}/audit-logs`
    );
    return res.data;
  },

  // 10. Student: Get Pending Corrections
  getMyCorrections: async (): Promise<StudentCorrectionSummary> => {
    const res = await apiClient.get<StudentCorrectionSummary>('/scrutiny/me/corrections');
    return res.data;
  },
};
