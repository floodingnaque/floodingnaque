/**
 * Reports API Service
 *
 * Provides API methods for generating and exporting reports
 * in PDF and CSV formats.
 *
 * Uses the shared api client from api-client.ts so all requests
 * benefit from the token refresh interceptor and CSRF handling.
 */

import { API_ENDPOINTS } from "@/config/api.config";
import api from "@/lib/api-client";

/**
 * Report types available for export.
 * Catalog types map to backend export endpoints:
 *   monthly-flood  → /export/predictions
 *   barangay-risk  → /export/weather
 *   incident-log   → /export/alerts
 * Legacy types (predictions, weather, alerts) are kept for backward compat.
 */
export type ReportType =
  | "predictions"
  | "weather"
  | "alerts"
  | "monthly-flood"
  | "barangay-risk"
  | "incident-log";

/**
 * Parameters for generating reports
 */
export interface ReportParams {
  /** Type of report to generate */
  report_type: ReportType;
  /** Start date for the report range (YYYY-MM-DD) */
  start_date?: string;
  /** End date for the report range (YYYY-MM-DD) */
  end_date?: string;
  /** Additional format-specific options */
  format_options?: Record<string, unknown>;
}

/**
 * Human-readable labels for each report type
 */
const REPORT_TYPE_LABELS: Record<ReportType, string> = {
  predictions: "Flood Predictions",
  weather: "Weather Data",
  alerts: "Flood Alerts",
  "monthly-flood": "Monthly Flood Report",
  "barangay-risk": "Barangay Risk Assessment",
  "incident-log": "Flood Incident Log",
};

export function getReportLabel(type: ReportType): string {
  return REPORT_TYPE_LABELS[type] ?? type;
}

/**
 * Build the export endpoint path (relative) with query string.
 */
function getExportPath(
  params: ReportParams,
  format: "csv" | "json" | "pdf",
): string {
  let endpoint: string;
  switch (params.report_type) {
    case "predictions":
    case "monthly-flood":
      endpoint = API_ENDPOINTS.export.predictions;
      break;
    case "weather":
    case "barangay-risk":
      endpoint = API_ENDPOINTS.export.weather;
      break;
    case "alerts":
    case "incident-log":
      endpoint = API_ENDPOINTS.export.alerts;
      break;
    default:
      endpoint = API_ENDPOINTS.export.predictions;
  }

  const searchParams = new URLSearchParams({ format });
  if (params.start_date) searchParams.set("start_date", params.start_date);
  if (params.end_date) searchParams.set("end_date", params.end_date);

  return `${endpoint}?${searchParams.toString()}`;
}

/**
 * Extract a meaningful error message from a thrown value.
 * Handles ApiError objects from the api-client interceptor as well as
 * standard Error instances.
 */
function extractErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error) return error.message;
  const obj = error as { message?: string; status?: number } | undefined;
  if (obj?.status === 404)
    return "No data found for the selected date range. Try adjusting the dates.";
  if (obj?.status === 503)
    return "Report generation is temporarily unavailable on the server.";
  if (obj?.status === 403)
    return "You do not have permission to export reports.";
  if (obj?.status === 429)
    return "Too many requests. Please wait a moment and try again.";
  return obj?.message || fallback;
}

/**
 * Reports API methods
 */
export const reportsApi = {
  /**
   * Export report as PDF
   */
  exportPDF: async (params: ReportParams): Promise<Blob> => {
    const path = getExportPath(params, "pdf");
    try {
      const blob = await api.get<Blob>(path, {
        responseType: "blob",
        headers: { Accept: "application/pdf" },
      });
      // Guard: if the backend returned JSON error wrapped in a 2xx Blob
      if (blob instanceof Blob && blob.type && !blob.type.includes("pdf")) {
        const text = await blob.text();
        try {
          const json = JSON.parse(text);
          throw new Error(
            json.error || json.message || "Failed to generate PDF",
          );
        } catch (e) {
          if (e instanceof SyntaxError)
            throw new Error("Unexpected response format");
          throw e;
        }
      }
      return blob;
    } catch (error: unknown) {
      throw new Error(
        extractErrorMessage(error, "Failed to generate PDF report."),
      );
    }
  },

  /**
   * Export report as CSV
   */
  exportCSV: async (params: ReportParams): Promise<Blob> => {
    const path = getExportPath(params, "csv");
    try {
      const blob = await api.get<Blob>(path, {
        responseType: "blob",
      });
      // Guard: if the backend returned JSON error wrapped in a Blob
      if (blob instanceof Blob && blob.type && blob.type.includes("json")) {
        const text = await blob.text();
        try {
          const json = JSON.parse(text);
          throw new Error(
            json.error || json.message || "Failed to generate CSV",
          );
        } catch (e) {
          if (e instanceof SyntaxError)
            throw new Error("Unexpected response format");
          throw e;
        }
      }
      return blob;
    } catch (error: unknown) {
      throw new Error(
        extractErrorMessage(error, "Failed to generate CSV report."),
      );
    }
  },

  /**
   * Submit an async report job for long-range reports (>7 days).
   * Returns a taskId for polling, or null if the backend doesn't support it (404).
   */
  submitAsyncReport: async (
    params: ReportParams,
    format: "pdf" | "csv",
  ): Promise<{ taskId: string; statusUrl: string } | null> => {
    try {
      return await api.post<{ taskId: string; statusUrl: string }>(
        `${"/api/v1/reports/async"}`,
        { ...params, format },
      );
    } catch {
      // Backend doesn't support async reports — caller falls back to sync
      return null;
    }
  },

  /**
   * Poll status of an async report task.
   */
  getReportStatus: async (
    taskId: string,
  ): Promise<{
    status: "pending" | "running" | "completed" | "failed";
    downloadUrl?: string;
  }> => {
    return api.get(
        `${"/api/v1/reports/status"}/${taskId}`,
    );
  },
};
