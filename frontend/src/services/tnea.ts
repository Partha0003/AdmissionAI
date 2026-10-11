import { apiClient } from './api';
import {
  TNEAAllotment,
  TNEAImportResponse,
  TNEAImportBatch,
} from '../types';

export interface ImportTNEAPayload {
  source?: string;
  filename_or_reference?: string;
  records: any[];
}

export interface AllotmentFilters {
  branch?: string;
  status?: string;
  search?: string;
}

export const tneaService = {
  async importAllotments(payload: ImportTNEAPayload): Promise<TNEAImportResponse> {
    const response = await apiClient.post<TNEAImportResponse>('/admin/tnea/import', payload);
    return response.data;
  },

  async getImportBatches(): Promise<TNEAImportBatch[]> {
    const response = await apiClient.get<TNEAImportBatch[]>('/admin/tnea/imports');
    return response.data;
  },

  async getImportBatch(batchId: string): Promise<TNEAImportBatch> {
    const response = await apiClient.get<TNEAImportBatch>(`/admin/tnea/imports/${batchId}`);
    return response.data;
  },

  async getAllotments(filters?: AllotmentFilters): Promise<TNEAAllotment[]> {
    const params = new URLSearchParams();
    if (filters?.branch) params.append('branch', filters.branch);
    if (filters?.status) params.append('status', filters.status);
    if (filters?.search) params.append('search', filters.search);

    const response = await apiClient.get<TNEAAllotment[]>(`/admin/allotments?${params.toString()}`);
    return response.data;
  },

  async getAllotment(id: string): Promise<TNEAAllotment> {
    const response = await apiClient.get<TNEAAllotment>(`/admin/allotments/${id}`);
    return response.data;
  },

  async getMyAllotment(): Promise<TNEAAllotment> {
    const response = await apiClient.get<TNEAAllotment>('/students/me/allotment');
    return response.data;
  },
};
