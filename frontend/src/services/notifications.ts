import { apiClient } from './api';
import {
  NotificationSummary,
  NotificationItem,
} from '../types';

export const notificationService = {
  async getMyNotifications(): Promise<NotificationSummary> {
    const res = await apiClient.get<NotificationSummary>('/notifications/me');
    return res.data;
  },

  async markRead(notificationId: string): Promise<NotificationItem> {
    const res = await apiClient.post<NotificationItem>(`/notifications/${notificationId}/read`);
    return res.data;
  },

  async markAllRead(): Promise<{ message: string; marked_count: number }> {
    const res = await apiClient.post<{ message: string; marked_count: number }>('/notifications/read-all');
    return res.data;
  },
};
