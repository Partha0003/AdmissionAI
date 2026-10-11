import { apiClient } from './api';
import {
  OnboardingProfile,
  OnboardingChecklistItem,
  StudentType,
  ParentInvitationResponse,
  ParentRedeemPayload,
  ParentRedeemResponse,
  GuidanceCard,
  InaugurationEvent,
  TransportConfig,
  OnboardingAuditLog,
} from '../types';

export const onboardingService = {
  // Student APIs
  async getMyProfile(): Promise<OnboardingProfile> {
    const res = await apiClient.get<OnboardingProfile>('/onboarding/me');
    return res.data;
  },

  async requestStudentType(studentType: StudentType): Promise<OnboardingProfile> {
    const res = await apiClient.post<OnboardingProfile>('/onboarding/me/student-type', {
      student_type: studentType,
    });
    return res.data;
  },

  async getMyChecklist(): Promise<OnboardingChecklistItem[]> {
    const res = await apiClient.get<OnboardingChecklistItem[]>('/onboarding/me/checklist');
    return res.data;
  },

  async acknowledgeChecklistItem(itemKey: string): Promise<OnboardingChecklistItem> {
    const res = await apiClient.post<OnboardingChecklistItem>(
      `/onboarding/me/checklist/${itemKey}/acknowledge`
    );
    return res.data;
  },

  async createParentInvitation(payload: {
    parent_name: string;
    phone: string;
    email?: string;
    relationship: string;
  }): Promise<ParentInvitationResponse> {
    const res = await apiClient.post<ParentInvitationResponse>(
      '/onboarding/me/parent-invitation',
      payload
    );
    return res.data;
  },

  async getGuidance(): Promise<GuidanceCard[]> {
    const res = await apiClient.get<GuidanceCard[]>('/onboarding/me/guidance');
    return res.data;
  },

  async getInauguration(): Promise<InaugurationEvent> {
    const res = await apiClient.get<InaugurationEvent>('/onboarding/me/inauguration');
    return res.data;
  },

  async getTransport(): Promise<TransportConfig> {
    const res = await apiClient.get<TransportConfig>('/onboarding/me/transport');
    return res.data;
  },

  // Parent APIs
  async redeemParentInvitation(payload: ParentRedeemPayload): Promise<ParentRedeemResponse> {
    const res = await apiClient.post<ParentRedeemResponse>('/parent/redeem-invitation', payload);
    return res.data;
  },

  async getLinkedStudentSummary(): Promise<Record<string, any>> {
    const res = await apiClient.get<Record<string, any>>('/parent/student');
    return res.data;
  },

  async getLinkedStudentOnboarding(): Promise<OnboardingProfile> {
    const res = await apiClient.get<OnboardingProfile>('/parent/onboarding');
    return res.data;
  },

  async getParentGuidance(): Promise<GuidanceCard[]> {
    const res = await apiClient.get<GuidanceCard[]>('/parent/guidance');
    return res.data;
  },

  // Admin APIs
  async listProfiles(params?: { student_type?: string; status_filter?: string }): Promise<OnboardingProfile[]> {
    const res = await apiClient.get<OnboardingProfile[]>('/admin/onboarding/profiles', { params });
    return res.data;
  },

  async confirmStudentType(studentId: string, studentType: StudentType): Promise<OnboardingProfile> {
    const res = await apiClient.post<OnboardingProfile>(
      `/admin/onboarding/students/${studentId}/confirm-type`,
      { student_type: studentType }
    );
    return res.data;
  },

  async updateInauguration(payload: Partial<InaugurationEvent>): Promise<InaugurationEvent> {
    const res = await apiClient.post<InaugurationEvent>('/admin/onboarding/inauguration', payload);
    return res.data;
  },

  async updateTransport(payload: {
    college_code?: string;
    routes?: any[];
    general_instructions?: string;
    is_configured?: boolean;
  }): Promise<TransportConfig> {
    const res = await apiClient.post<TransportConfig>('/admin/onboarding/transport', payload);
    return res.data;
  },

  async listAuditLogs(params?: { student_id?: string; action?: string; limit?: number }): Promise<OnboardingAuditLog[]> {
    const res = await apiClient.get<OnboardingAuditLog[]>('/admin/onboarding/audit-logs', { params });
    return res.data;
  },
};
