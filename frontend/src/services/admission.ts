import { apiClient } from './api';
import { 
  StudentProfile, 
  AdmissionApplication, 
  AdminDashboardMetrics, 
  AdminStudentItem 
} from '../types';

export const admissionService = {
  // Student endpoints
  async getStudentProfile(): Promise<StudentProfile> {
    const response = await apiClient.get<StudentProfile>('/students/me');
    return response.data;
  },

  async getStudentAdmission(): Promise<AdmissionApplication> {
    const response = await apiClient.get<AdmissionApplication>('/students/me/admission');
    return response.data;
  },

  async transitionState(admissionId: string, targetState: string, reason?: string): Promise<AdmissionApplication> {
    const response = await apiClient.post<AdmissionApplication>(`/admissions/${admissionId}/transition`, {
      target_state: targetState,
      reason: reason || `Transition triggered by candidate/admin`
    });
    return response.data;
  },

  // Admin endpoints
  async getAdminDashboardMetrics(): Promise<AdminDashboardMetrics> {
    const response = await apiClient.get<AdminDashboardMetrics>('/admin/dashboard');
    return response.data;
  },

  async getAdminStudents(params?: { status?: string; branch?: string; search?: string }): Promise<AdminStudentItem[]> {
    const response = await apiClient.get<AdminStudentItem[]>('/admin/students', { params });
    return response.data;
  }
};
