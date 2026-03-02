/**
 * Reports API Service
 *
 * Provides API methods for generating and exporting reports
 * in PDF and CSV formats.
 *
 * Uses the shared api client from api-client.ts so all requests
 * benefit from the token refresh interceptor and CSRF handling.
 */

import api from '@/lib/api-client';
import { API_ENDPOINTS } from '@/config/api.config';

/**
 * Report types available for export
 */
export type ReportType = 'predictions' | 'weather' | 'alerts';

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
 * Build the export endpoint path (relative) with query string.
 */
function getExportPath(params: ReportParams, format: 'csv' | 'json' | 'pdf'): string {
  const endpoint =
    params.report_type === 'predictions'
      ? API_ENDPOINTS.export.predictions
      : params.report_type === 'alerts'
      ? API_ENDPOINTS.export.alerts
      : API_ENDPOINTS.export.weather;

  const searchParams = new URLSearchParams({ format });
  if (params.start_date) searchParams.set('start_date', params.start_date);
  if (params.end_date) searchParams.set('end_date', params.end_date);

  return `${endpoint}?${searchParams.toString()}`;
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
   */
  exportPDF: async (params: ReportParams): Promise<Blob> => {
    const path = getExportPath(params, 'pdf');
    return api.get<Blob>(path, {
      responseType: 'blob',
      headers: { Accept: 'application/pdf' },
    });
  },

  /**
   * Export report as CSV
   *
   * @param params - Report configuration parameters
   * @returns Blob containing the CSV file
   */
  exportCSV: async (params: ReportParams): Promise<Blob> => {
    const path = getExportPath(params, 'csv');
    return api.get<Blob>(path, {
      responseType: 'blob',
    });
  },
};

export default reportsApi;
