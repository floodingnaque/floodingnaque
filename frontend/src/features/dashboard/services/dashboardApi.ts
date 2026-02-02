/**
 * Dashboard API Service
 *
 * Provides API methods for fetching dashboard statistics
 * and activity data.
 */

import api from '@/lib/api-client';
import { API_CONFIG } from '@/config/api.config';

const { endpoints } = API_CONFIG;

/**
 * Activity item representing a recent prediction or alert
 */
export interface ActivityItem {
  type: 'prediction' | 'alert';
  timestamp: string;
  description: string;
}

/**
 * Dashboard statistics response from the API
 */
export interface DashboardStats {
  total_predictions: number;
  predictions_today: number;
  active_alerts: number;
  avg_risk_level: number;
  recent_activity: ActivityItem[];
}

/**
 * Dashboard API methods
 */
export const dashboardApi = {
  /**
   * Get dashboard statistics including totals and recent activity
   */
  getStats: async (): Promise<DashboardStats> => {
    return api.get<DashboardStats>(endpoints.dashboard.stats);
  },
};

export default dashboardApi;
