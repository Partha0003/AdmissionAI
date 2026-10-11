import { apiClient } from './api';
import {
  ERPAdmissionRecord,
  ERPReadinessCheck,
  ERPIntegrationEvent,
} from '../types';

export const erpService = {
  async validateReadiness(applicationId: string): Promise<ERPReadinessCheck> {
    const res = await apiClient.post<ERPReadinessCheck>(`/admin/erp/validate/${applicationId}`);
    return res.data;
  },

  async stageRecord(applicationId: string): Promise<ERPAdmissionRecord> {
    const res = await apiClient.post<ERPAdmissionRecord>(`/admin/erp/stage/${applicationId}`);
    return res.data;
  },

  async listRecords(params?: {
    status?: string;
    search?: string;
  }): Promise<ERPAdmissionRecord[]> {
    const res = await apiClient.get<ERPAdmissionRecord[]>('/admin/erp/records', { params });
    return res.data;
  },

  async getRecordDetail(recordId: string): Promise<ERPAdmissionRecord> {
    const res = await apiClient.get<ERPAdmissionRecord>(`/admin/erp/records/${recordId}`);
    return res.data;
  },

  async syncRecord(
    recordId: string,
    payload?: {
      simulate_failure?: boolean;
      failure_reason?: string;
    }
  ): Promise<ERPAdmissionRecord> {
    const res = await apiClient.post<ERPAdmissionRecord>(`/admin/erp/records/${recordId}/sync`, payload || {});
    return res.data;
  },

  async retrySync(
    recordId: string,
    payload?: {
      simulate_failure?: boolean;
      failure_reason?: string;
    }
  ): Promise<ERPAdmissionRecord> {
    const res = await apiClient.post<ERPAdmissionRecord>(`/admin/erp/records/${recordId}/retry`, payload || {});
    return res.data;
  },

  async getRecordEvents(recordId: string): Promise<ERPIntegrationEvent[]> {
    const res = await apiClient.get<ERPIntegrationEvent[]>(`/admin/erp/records/${recordId}/events`);
    return res.data;
  },
};
