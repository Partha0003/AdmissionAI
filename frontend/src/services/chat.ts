import { apiClient } from './api';
import {
  ChatSession,
  ChatMessage,
  KnowledgeDocument,
  KnowledgeDocumentVersion,
  KnowledgeChunk,
  KnowledgeIngestPayload,
} from '../types';

export const chatService = {
  // Session management
  async createSession(title?: string): Promise<ChatSession> {
    const res = await apiClient.post<ChatSession>('/chat/sessions', { title });
    return res.data;
  },

  async listSessions(): Promise<ChatSession[]> {
    const res = await apiClient.get<ChatSession[]>('/chat/sessions');
    return res.data;
  },

  async getSession(sessionId: string): Promise<ChatSession> {
    const res = await apiClient.get<ChatSession>(`/chat/sessions/${sessionId}`);
    return res.data;
  },

  // Messaging & Retrieval
  async sendMessage(
    sessionId: string,
    message: string,
    llmProvider: string = 'mock',
    topK: number = 4
  ): Promise<ChatMessage> {
    const res = await apiClient.post<ChatMessage>(`/chat/sessions/${sessionId}/messages`, {
      message,
      llm_provider: llmProvider,
      top_k: topK,
    });
    return res.data;
  },

  async getSourceChunk(chunkId: string): Promise<KnowledgeChunk> {
    const res = await apiClient.get<KnowledgeChunk>(`/chat/sources/${chunkId}`);
    return res.data;
  },

  // Admin Knowledge Desk
  async listKnowledgeDocuments(category?: string): Promise<KnowledgeDocument[]> {
    const res = await apiClient.get<KnowledgeDocument[]>('/admin/knowledge/documents', {
      params: category ? { category } : undefined,
    });
    return res.data;
  },

  async getKnowledgeDocument(docId: string): Promise<KnowledgeDocument> {
    const res = await apiClient.get<KnowledgeDocument>(`/admin/knowledge/documents/${docId}`);
    return res.data;
  },

  async ingestKnowledge(payload: KnowledgeIngestPayload): Promise<KnowledgeDocument> {
    const res = await apiClient.post<KnowledgeDocument>('/admin/knowledge/ingest', payload);
    return res.data;
  },

  async activateKnowledgeVersion(versionId: string): Promise<KnowledgeDocumentVersion> {
    const res = await apiClient.post<KnowledgeDocumentVersion>(
      `/admin/knowledge/documents/${versionId}/activate`
    );
    return res.data;
  },
};
