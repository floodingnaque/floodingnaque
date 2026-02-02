/**
 * Alerts API Service
 *
 * Provides API methods for alert functionality including fetching,
 * acknowledging, and managing flood alerts.
 */

import { api } from '@/lib/api-client';
import { API_ENDPOINTS } from '@/config/api.config';
import type {
  Alert,
  AlertParams,
  AlertHistory,
  PaginatedResponse,
  ApiResponse,
} from '@/types';

/**
 * Alerts API methods
 */
export const alertsApi = {
  /**
   * Get paginated list of alerts with optional filters
   *
   * @param params - Optional query parameters for filtering and pagination
   * @returns Paginated response with alerts
   *
   * @example
   * const alerts = await alertsApi.getAlerts({ page: 1, limit: 10, risk_level: 2 });
   */
  getAlerts: async (params?: AlertParams): Promise<PaginatedResponse<Alert>> => {
    const queryParams = new URLSearchParams();

    if (params?.page) queryParams.set('page', params.page.toString());
    if (params?.limit) queryParams.set('limit', params.limit.toString());
    if (params?.sort_by) queryParams.set('sort_by', params.sort_by);
    if (params?.order) queryParams.set('order', params.order);
    if (params?.risk_level !== undefined)
      queryParams.set('risk_level', params.risk_level.toString());
    if (params?.acknowledged !== undefined)
      queryParams.set('acknowledged', params.acknowledged.toString());
    if (params?.start_date) queryParams.set('start_date', params.start_date);
    if (params?.end_date) queryParams.set('end_date', params.end_date);

    const queryString = queryParams.toString();
    const url = queryString
      ? `${API_ENDPOINTS.alerts.list}?${queryString}`
      : API_ENDPOINTS.alerts.list;

    return api.get<PaginatedResponse<Alert>>(url);
  },

  /**
   * Get recent alerts
   *
   * @param limit - Maximum number of alerts to return (default: 10)
   * @returns Array of recent alerts
   *
   * @example
   * const recentAlerts = await alertsApi.getRecentAlerts(5);
   */
  getRecentAlerts: async (limit: number = 10): Promise<Alert[]> => {
    const response = await api.get<ApiResponse<Alert[]>>(
      `${API_ENDPOINTS.alerts.recent}?limit=${limit}`
    );
    return response.data;
  },

  /**
   * Get alert history with summary statistics
   *
   * @returns Alert history with aggregated summary
   *
   * @example
   * const history = await alertsApi.getAlertHistory();
   * console.log(history.summary.total);
   */
  getAlertHistory: async (): Promise<AlertHistory> => {
    return api.get<AlertHistory>(`${API_ENDPOINTS.alerts.list}/history`);
  },

  /**
   * Acknowledge a single alert
   *
   * @param id - Alert ID to acknowledge
   *
   * @example
   * await alertsApi.acknowledgeAlert(123);
   */
  acknowledgeAlert: async (id: number): Promise<void> => {
    await api.patch<ApiResponse<void>>(`${API_ENDPOINTS.alerts.list}/${id}/acknowledge`);
  },

  /**
   * Acknowledge all pending alerts
   *
   * @example
   * await alertsApi.acknowledgeAll();
   */
  acknowledgeAll: async (): Promise<void> => {
    await api.post<ApiResponse<void>>(`${API_ENDPOINTS.alerts.list}/acknowledge-all`);
  },
};

export default alertsApi;
