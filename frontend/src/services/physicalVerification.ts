import { apiClient } from './api';
import {
  AvailableSlot,
  PhysicalVerificationAppointment,
  PhysicalVerificationSession,
  PhysicalDocumentVerification,
  PhysicalVerificationAuditLog,
  StudentPhysicalVerificationSummary,
  CheckInResult,
  PhysicalDocDecision,
  PhysicalVerificationDecision,
} from '../types';

export const PhysicalVerificationService = {
  // 1. Get available appointment slots
  getSlots: async (slotDate?: string): Promise<AvailableSlot[]> => {
    const params = slotDate ? { slot_date: slotDate } : {};
    const res = await apiClient.get<AvailableSlot[]>('/physical-verification/slots', { params });
    return res.data;
  },

  // 2. Candidate: Book appointment
  createAppointment: async (data: {
    appointment_date: string;
    start_time: string;
    end_time: string;
    location?: string;
    notes?: string;
  }): Promise<PhysicalVerificationAppointment> => {
    const res = await apiClient.post<PhysicalVerificationAppointment>(
      '/physical-verification/appointments',
      data
    );
    return res.data;
  },

  // 3. Candidate: Get my appointment
  getMyAppointment: async (): Promise<PhysicalVerificationAppointment | null> => {
    const res = await apiClient.get<PhysicalVerificationAppointment | null>(
      '/physical-verification/appointments/me'
    );
    return res.data;
  },

  // 4. Candidate: Confirm appointment
  confirmAppointment: async (appointmentId: string): Promise<PhysicalVerificationAppointment> => {
    const res = await apiClient.post<PhysicalVerificationAppointment>(
      `/physical-verification/appointments/${appointmentId}/confirm`
    );
    return res.data;
  },

  // 5. Candidate/Admin: Reschedule appointment
  rescheduleAppointment: async (
    appointmentId: string,
    data: {
      appointment_date: string;
      start_time: string;
      end_time: string;
      reason?: string;
    }
  ): Promise<PhysicalVerificationAppointment> => {
    const res = await apiClient.post<PhysicalVerificationAppointment>(
      `/physical-verification/appointments/${appointmentId}/reschedule`,
      data
    );
    return res.data;
  },

  // 6. Candidate/Admin: Cancel appointment
  cancelAppointment: async (
    appointmentId: string,
    reason?: string
  ): Promise<PhysicalVerificationAppointment> => {
    const res = await apiClient.post<PhysicalVerificationAppointment>(
      `/physical-verification/appointments/${appointmentId}/cancel`,
      null,
      { params: reason ? { reason } : {} }
    );
    return res.data;
  },

  // 7. Candidate: Physical Verification Summary & Corrections
  getMySummary: async (): Promise<StudentPhysicalVerificationSummary> => {
    const res = await apiClient.get<StudentPhysicalVerificationSummary>(
      '/physical-verification/me/summary'
    );
    return res.data;
  },

  // 8. Admin: List appointments queue
  listAppointments: async (params?: {
    appointment_date?: string;
    status_filter?: string;
    search_query?: string;
  }): Promise<PhysicalVerificationAppointment[]> => {
    const res = await apiClient.get<PhysicalVerificationAppointment[]>(
      '/physical-verification/admin/appointments',
      { params }
    );
    return res.data;
  },

  // 9. Admin: Check-in candidate
  checkIn: async (data: {
    token_number?: string;
    checkin_token?: string;
    counter_desk?: string;
  }): Promise<CheckInResult> => {
    const res = await apiClient.post<CheckInResult>(
      '/physical-verification/admin/check-in',
      data
    );
    return res.data;
  },

  // 10. Admin: Start verification session
  startSession: async (
    applicationId: string,
    data: {
      appointment_id?: string;
      counter_desk?: string;
      officer_notes?: string;
    }
  ): Promise<PhysicalVerificationSession> => {
    const res = await apiClient.post<PhysicalVerificationSession>(
      `/physical-verification/admin/applications/${applicationId}/sessions/start`,
      data
    );
    return res.data;
  },

  // 11. Admin: Get verification session
  getSession: async (sessionId: string): Promise<PhysicalVerificationSession> => {
    const res = await apiClient.get<PhysicalVerificationSession>(
      `/physical-verification/admin/sessions/${sessionId}`
    );
    return res.data;
  },

  // 12. Admin: Verify physical document
  verifyDocument: async (
    sessionId: string,
    documentId: string,
    data: {
      officer_decision: PhysicalDocDecision;
      verification_notes?: string;
      discrepancy_reason?: string;
      checklist_checks?: Record<string, any>;
    }
  ): Promise<PhysicalDocumentVerification> => {
    const res = await apiClient.post<PhysicalDocumentVerification>(
      `/physical-verification/admin/sessions/${sessionId}/documents/${documentId}/verify`,
      data
    );
    return res.data;
  },

  // 13. Admin: Request physical document correction
  requestCorrection: async (
    sessionId: string,
    documentId: string,
    data: {
      discrepancy_reason: string;
      verification_notes?: string;
      checklist_checks?: Record<string, any>;
    }
  ): Promise<PhysicalDocumentVerification> => {
    const res = await apiClient.post<PhysicalDocumentVerification>(
      `/physical-verification/admin/sessions/${sessionId}/documents/${documentId}/correction`,
      data
    );
    return res.data;
  },

  // 14. Admin: Complete physical verification session
  completeSession: async (
    sessionId: string,
    data: {
      overall_decision: PhysicalVerificationDecision;
      officer_notes?: string;
    }
  ): Promise<PhysicalVerificationSession> => {
    const res = await apiClient.post<PhysicalVerificationSession>(
      `/physical-verification/admin/sessions/${sessionId}/complete`,
      data
    );
    return res.data;
  },

  // 15. Admin: Reopen physical verification session (ADMISSION_HEAD / SUPER_ADMIN)
  reopenSession: async (
    sessionId: string,
    reason: string
  ): Promise<PhysicalVerificationSession> => {
    const res = await apiClient.post<PhysicalVerificationSession>(
      `/physical-verification/admin/sessions/${sessionId}/reopen`,
      { reason }
    );
    return res.data;
  },

  // 16. Admin: Get audit logs
  getAuditLogs: async (sessionId: string): Promise<PhysicalVerificationAuditLog[]> => {
    const res = await apiClient.get<PhysicalVerificationAuditLog[]>(
      `/physical-verification/admin/sessions/${sessionId}/audit-logs`
    );
    return res.data;
  },
};
