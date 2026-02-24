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
export type ReportType = 'predictions' | 'weather';

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
   * Determine the correct export endpoint based on report type
   */
  _getExportUrl(params: ReportParams, format: 'csv' | 'json' | 'pdf'): string {
    const endpoint =
      params.report_type === 'predictions'
        ? API_ENDPOINTS.export.predictions
        : API_ENDPOINTS.export.weather;

    const searchParams = new URLSearchParams({ format });
    if (params.start_date) searchParams.set('start_date', params.start_date);
    if (params.end_date) searchParams.set('end_date', params.end_date);

    return `${API_CONFIG.baseUrl}${endpoint}?${searchParams.toString()}`;
  },

  /**
   * Export report as PDF
   *
   * @param params - Report configuration parameters
   * @returns Blob containing the PDF file
   */
  exportPDF: async (params: ReportParams): Promise<Blob> => {
    const url = reportsApi._getExportUrl(params, 'pdf');
    const response = await axios.get(url, {
      responseType: 'blob',
      headers: {
        ...getAuthHeader(),
        Accept: 'application/pdf',
      },
      timeout: API_CONFIG.timeout * 2,
    });
    return response.data;
  },

  /**
   * Export report as CSV
   *
   * @param params - Report configuration parameters
   * @returns Blob containing the CSV file
   */
  exportCSV: async (params: ReportParams): Promise<Blob> => {
    const url = reportsApi._getExportUrl(params, 'csv');
    const response = await axios.get(url, {
      responseType: 'blob',
      headers: {
        ...getAuthHeader(),
      },
      timeout: API_CONFIG.timeout * 2,
    });
    return response.data;
  },
};

export default reportsApi;
