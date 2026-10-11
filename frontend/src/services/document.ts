import { apiClient } from './api';
import {
  DocumentType,
  DocumentUploadResponse,
  DocumentVersion,
} from '../types';

export const documentService = {
  async getDocumentTypes(): Promise<DocumentType[]> {
    const res = await apiClient.get<DocumentType[]>('/documents/types');
    return res.data;
  },

  async uploadDocument(documentTypeCode: string, file: File): Promise<DocumentUploadResponse> {
    const formData = new FormData();
    formData.append('document_type_code', documentTypeCode);
    formData.append('file', file);

    const res = await apiClient.post<DocumentUploadResponse>('/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return res.data;
  },

  async getDocumentVersions(documentId: string): Promise<DocumentVersion[]> {
    const res = await apiClient.get<DocumentVersion[]>(`/documents/${documentId}/versions`);
    return res.data;
  },

  getDocumentDownloadUrl(documentId: string, version?: number): string {
    const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';
    const versionQuery = version ? `?version=${version}` : '';
    return `${baseUrl}/documents/${documentId}/download${versionQuery}`;
  },

  async downloadDocumentBlob(documentId: string, version?: number): Promise<{ blob: Blob; filename: string }> {
    const res = await apiClient.get(`/documents/${documentId}/download`, {
      params: { version },
      responseType: 'blob',
    });
    const disposition = res.headers['content-disposition'];
    let filename = 'downloaded_document';
    if (disposition && disposition.includes('filename=')) {
      const match = disposition.match(/filename="?([^"]+)"?/);
      if (match && match[1]) filename = match[1];
    }
    return { blob: res.data, filename };
  },

  async processDocument(documentId: string, forceReprocess: boolean = false): Promise<any> {
    const res = await apiClient.post(`/documents/${documentId}/process`, {
      processing_type: 'DOCUMENT_CLASSIFICATION',
      force_reprocess: forceReprocess,
    });
    return res.data;
  },

  async getDocumentProcessing(documentId: string): Promise<any> {
    const res = await apiClient.get(`/documents/${documentId}/processing`);
    return res.data;
  },

  async preprocessDocument(documentId: string, options?: any): Promise<any> {
    const res = await apiClient.post(`/documents/${documentId}/preprocess`, options || {});
    return res.data;
  },

  async getDocumentPreprocessing(documentId: string): Promise<any> {
    const res = await apiClient.get(`/documents/${documentId}/preprocessing`);
    return res.data;
  },

  getPreprocessedImageUrl(documentId: string): string {
    const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';
    return `${baseUrl}/documents/${documentId}/preprocessed-image`;
  },

  async getAdminDocumentProcessing(documentId: string): Promise<any> {
    const res = await apiClient.get(`/admin/documents/${documentId}/processing`);
    return res.data;
  },

  async getAdminDocumentPreprocessing(documentId: string): Promise<any> {
    const res = await apiClient.get(`/admin/documents/${documentId}/preprocessing`);
    return res.data;
  },

  async runDocumentOCR(documentId: string, options?: { language?: string; engine_name?: string }): Promise<any> {
    const res = await apiClient.post(`/documents/${documentId}/ocr`, options || {});
    return res.data;
  },

  async getDocumentOCR(documentId: string): Promise<any> {
    const res = await apiClient.get(`/documents/${documentId}/ocr`);
    return res.data;
  },

  async getAdminDocumentOCR(documentId: string): Promise<any> {
    const res = await apiClient.get(`/admin/documents/${documentId}/ocr`);
    return res.data;
  },

  async runFieldExtraction(documentId: string, forceReprocess: boolean = false): Promise<any> {
    const res = await apiClient.post(`/documents/${documentId}/extract-fields`, {
      force_reprocess: forceReprocess,
    });
    return res.data;
  },

  async getDocumentExtractedFields(documentId: string): Promise<any> {
    const res = await apiClient.get(`/documents/${documentId}/extracted-fields`);
    return res.data;
  },

  async getAdminDocumentExtractedFields(documentId: string): Promise<any> {
    const res = await apiClient.get(`/admin/documents/${documentId}/extracted-fields`);
    return res.data;
  },
};



