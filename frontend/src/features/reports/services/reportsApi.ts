/**
 * Reports API Service
 *
 * Provides API methods for generating and exporting reports
 * in PDF and CSV formats.
 */

import axios from 'axios';
import { API_CONFIG, API_ENDPOINTS } from '@/config/api.config';
import { useAuthStore } from '@/state/stores/authStore';

/**
 * Report types available for export
 */
export type ReportType = 'predictions' | 'alerts' | 'weather';

/**
 * Parameters for generating reports
 */
export interface ReportParams {
  /** Type of report to generate */
  report_type: ReportType;
  /** Start date for the report range (ISO string) */
  start_date?: string;
  /** End date for the report range (ISO string) */
  end_date?: string;
  /** Additional format-specific options */
  format_options?: Record<string, unknown>;
}

/**
 * Get authorization header for blob requests
 */
function getAuthHeader(): Record<string, string> {
  const token = useAuthStore.getState().accessToken;
  if (token) {
    return { Authorization: `Bearer ${token}` };
  }
  return {};
}

/**
 * Reports API methods
 */
export const reportsApi = {
  /**
   * Export report as PDF
   *
   * @param params - Report configuration parameters
   * @returns Blob containing the PDF file
   *
   * @example
   * const blob = await reportsApi.exportPDF({
   *   report_type: 'predictions',
   *   start_date: '2026-01-01',
   *   end_date: '2026-01-31'
   * });
   */
  exportPDF: async (params: ReportParams): Promise<Blob> => {
    const response = await axios.post(
      `${API_CONFIG.baseUrl}${API_ENDPOINTS.export.pdf}`,
      params,
      {
        responseType: 'blob',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeader(),
        },
        timeout: API_CONFIG.timeout * 2, // Longer timeout for report generation
      }
    );
    return response.data;
  },

  /**
   * Export report as CSV
   *
   * @param params - Report configuration parameters
   * @returns Blob containing the CSV file
   *
   * @example
   * const blob = await reportsApi.exportCSV({
   *   report_type: 'alerts',
   *   start_date: '2026-01-01',
   *   end_date: '2026-01-31'
   * });
   */
  exportCSV: async (params: ReportParams): Promise<Blob> => {
    const response = await axios.post(
      `${API_CONFIG.baseUrl}${API_ENDPOINTS.export.csv}`,
      params,
      {
        responseType: 'blob',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeader(),
        },
        timeout: API_CONFIG.timeout * 2, // Longer timeout for report generation
      }
    );
    return response.data;
  },
};

export default reportsApi;
