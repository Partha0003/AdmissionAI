import { apiClient } from './api';
import {
  StudentPaymentSummary,
  PaymentTransaction,
  PaymentAuditLog,
} from '../types';

export const paymentService = {
  // Student endpoints
  async getStudentPaymentSummary(): Promise<StudentPaymentSummary> {
    const res = await apiClient.get<StudentPaymentSummary>('/payments/me');
    return res.data;
  },

  async initiatePayment(payload: {
    payment_method: string;
    notes?: string;
  }): Promise<PaymentTransaction> {
    const res = await apiClient.post<PaymentTransaction>('/payments/initiate', payload);
    return res.data;
  },

  async submitDemandDraft(
    paymentId: string,
    payload: {
      dd_number: string;
      dd_date: string;
      bank_name: string;
      branch_name?: string;
      amount: number;
      supporting_document_id?: string;
      supporting_document_version_id?: string;
    }
  ): Promise<PaymentTransaction> {
    const res = await apiClient.post<PaymentTransaction>(`/payments/${paymentId}/submit-dd`, payload);
    return res.data;
  },

  async simulateOnlinePayment(
    paymentId: string,
    payload: {
      simulate_failure?: boolean;
      notes?: string;
    }
  ): Promise<PaymentTransaction> {
    const res = await apiClient.post<PaymentTransaction>(`/payments/${paymentId}/simulate-online`, payload);
    return res.data;
  },

  // Finance Officer / Admin Desk endpoints
  async listAdminPayments(params?: {
    status?: string;
    method?: string;
    search?: string;
  }): Promise<PaymentTransaction[]> {
    const res = await apiClient.get<PaymentTransaction[]>('/payments/admin/list', { params });
    return res.data;
  },

  async getAdminPaymentDetail(paymentId: string): Promise<PaymentTransaction> {
    const res = await apiClient.get<PaymentTransaction>(`/payments/admin/${paymentId}`);
    return res.data;
  },

  async reviewAdminPayment(
    paymentId: string,
    payload: {
      decision: 'VERIFIED' | 'REJECTED' | 'CORRECTION_REQUIRED';
      reason?: string;
      notes?: string;
    }
  ): Promise<PaymentTransaction> {
    const res = await apiClient.post<PaymentTransaction>(`/payments/admin/${paymentId}/review`, payload);
    return res.data;
  },

  async getPaymentAudit(paymentId: string): Promise<PaymentAuditLog[]> {
    const res = await apiClient.get<PaymentAuditLog[]>(`/payments/admin/${paymentId}/audit`);
    return res.data;
  },
};
