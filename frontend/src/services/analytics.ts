import { apiClient } from './api';
import { AnalyticsOverview } from '../types';

export const analyticsService = {
  async getOverview(dateFilter: string = 'all_time'): Promise<AnalyticsOverview> {
    const res = await apiClient.get<AnalyticsOverview>('/admin/analytics/overview', {
      params: { date_filter: dateFilter },
    });
    return res.data;
  },
};
