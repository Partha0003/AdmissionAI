import { apiClient } from './api';
import { StudentJourneyTimeline } from '../types';

export const timelineService = {
  async getMyTimeline(): Promise<StudentJourneyTimeline> {
    const res = await apiClient.get<StudentJourneyTimeline>('/timeline/me');
    return res.data;
  },

  async getAdminTimeline(applicationId: string): Promise<StudentJourneyTimeline> {
    const res = await apiClient.get<StudentJourneyTimeline>(`/timeline/admin/${applicationId}`);
    return res.data;
  },
};
