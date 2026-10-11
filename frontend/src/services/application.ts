import { apiClient } from './api';
import {
  ApplicationDetail,
  ApplicationDraft,
  ApplicationCompletion,
  ChecklistItem,
  ApplicationSubmissionResponse,
  AdminApplicationListItem,
  CrossDocumentReconciliation,
} from '../types';

export const applicationService = {
  async getMyApplication(): Promise<ApplicationDetail> {
    const res = await apiClient.get<ApplicationDetail>('/applications/me');
    return res.data;
  },

  async updateDraft(draft: ApplicationDraft): Promise<ApplicationDetail> {
    const res = await apiClient.put<ApplicationDetail>('/applications/me', draft);
    return res.data;
  },

  async getCompletion(): Promise<ApplicationCompletion> {
    const res = await apiClient.get<ApplicationCompletion>('/applications/me/completion');
    return res.data;
  },

  async getChecklist(): Promise<ChecklistItem[]> {
    const res = await apiClient.get<ChecklistItem[]>('/applications/me/checklist');
    return res.data;
  },

  async submitApplication(declarationAccepted: boolean): Promise<ApplicationSubmissionResponse> {
    const res = await apiClient.post<ApplicationSubmissionResponse>('/applications/me/submit', {
      declaration_accepted: declarationAccepted,
    });
    return res.data;
  },

  async listAdminApplications(params?: { status?: string; search?: string }): Promise<AdminApplicationListItem[]> {
    const res = await apiClient.get<AdminApplicationListItem[]>('/applications/admin/list', { params });
    return res.data;
  },

  async getAdminApplicationDetail(id: string): Promise<ApplicationDetail> {
    const res = await apiClient.get<ApplicationDetail>(`/applications/admin/${id}`);
    return res.data;
  },

  // ================= Phase 4E Cross-Document Reconciliation =================

  async runMyReconciliation(): Promise<CrossDocumentReconciliation> {
    const res = await apiClient.post<CrossDocumentReconciliation>('/applications/me/reconcile');
    return res.data;
  },

  async getMyReconciliation(): Promise<CrossDocumentReconciliation> {
    const res = await apiClient.get<CrossDocumentReconciliation>('/applications/me/reconciliation');
    return res.data;
  },

  async runAdminReconciliation(applicationId: string): Promise<CrossDocumentReconciliation> {
    const res = await apiClient.post<CrossDocumentReconciliation>(`/admin/applications/${applicationId}/reconcile`);
    return res.data;
  },

  async getAdminReconciliation(applicationId: string): Promise<CrossDocumentReconciliation> {
    const res = await apiClient.get<CrossDocumentReconciliation>(`/admin/applications/${applicationId}/reconciliation`);
    return res.data;
  },
};

