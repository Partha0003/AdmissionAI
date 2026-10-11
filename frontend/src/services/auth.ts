import { apiClient } from './api';
import { AuthResponse, User, ActivationResponse } from '../types';

export const authService = {
  async login(email: string, password: string): Promise<AuthResponse> {
    const response = await apiClient.post<AuthResponse>('/auth/login', { email, password });
    if (response.data.access_token) {
      localStorage.setItem('admissionai_token', response.data.access_token);
    }
    return response.data;
  },

  async activateAccount(activationToken: string, password: string): Promise<ActivationResponse> {
    const response = await apiClient.post<ActivationResponse>('/auth/activate', {
      activation_token: activationToken,
      password,
    });
    return response.data;
  },

  async getCurrentUser(): Promise<User> {
    const response = await apiClient.get<User>('/auth/me');
    localStorage.setItem('admissionai_user', JSON.stringify(response.data));
    return response.data;
  },

  logout() {
    localStorage.removeItem('admissionai_token');
    localStorage.removeItem('admissionai_user');
  },

  getStoredToken(): string | null {
    return localStorage.getItem('admissionai_token');
  },

  getStoredUser(): User | null {
    const data = localStorage.getItem('admissionai_user');
    return data ? JSON.parse(data) : null;
  }
};
