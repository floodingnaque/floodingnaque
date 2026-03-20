/**
 * Dataset API Service
 *
 * Provides API methods for the Dataset Management page:
 * upload, validate, download templates, export data, and fetch stats.
 */

import { API_ENDPOINTS } from "@/config/api.config";
import api from "@/lib/api-client";

// ── Types ──

export interface DatasetStats {
  total_records: number;
  date_range: {
    earliest: string | null;
    latest: string | null;
  };
  sources: string[];
  last_ingestion: string | null;
  records_this_month: number;
}

export interface DatasetStatsResponse {
  success: boolean;
  stats: DatasetStats;
}

export interface ValidationResult {
  success: boolean;
  validation?: {
    valid: boolean;
    total_rows: number;
    valid_rows: number;
    invalid_rows: number;
    errors: string[];
    errors_truncated: boolean;
  };
  data?: {
    valid: boolean;
    records: number;
    errors: string[];
    warnings: string[];
    sample?: Record<string, unknown>[];
  };
}

export interface UploadResult {
  success: boolean;
  message?: string;
  summary?: {
    total_rows_processed: number;
    rows_inserted: number;
    rows_skipped: number;
    errors: string[];
  };
  data?: {
    records_processed?: number;
    records_inserted?: number;
    errors?: string[];
    warnings?: string[];
  };
}

export interface ExportCountResponse {
  success: boolean;
  count: number;
}

// ── API Methods ──

export const datasetApi = {
  /** Fetch dataset overview statistics */
  getStats: () =>
    api.get<DatasetStatsResponse>(`${API_ENDPOINTS.admin.upload}/stats`),

  /** Validate a file without ingesting */
  validateFile: (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return api.post<ValidationResult>(
      `${API_ENDPOINTS.admin.upload}/validate`,
      formData,
      { headers: { "Content-Type": "multipart/form-data" } },
    );
  },

  /** Upload and ingest a CSV file */
  uploadCsv: (file: File, skipErrors = false) => {
    const formData = new FormData();
    formData.append("file", file);
    if (skipErrors) formData.append("skip_errors", "true");
    return api.post<UploadResult>(
      `${API_ENDPOINTS.admin.upload}/csv`,
      formData,
      { headers: { "Content-Type": "multipart/form-data" } },
    );
  },

  /** Upload and ingest an Excel file */
  uploadExcel: (file: File, skipErrors = false) => {
    const formData = new FormData();
    formData.append("file", file);
    if (skipErrors) formData.append("skip_errors", "true");
    return api.post<UploadResult>(
      `${API_ENDPOINTS.admin.upload}/excel`,
      formData,
      { headers: { "Content-Type": "multipart/form-data" } },
    );
  },

  /** Download CSV template as blob */
  downloadTemplateCsv: () =>
    api.get<Blob>(`${API_ENDPOINTS.admin.upload}/template/csv`, {
      responseType: "blob",
    }),

  /** Get the legacy JSON template (column info) */
  getTemplateInfo: () =>
    api.get<{
      success: boolean;
      template: string;
      required_columns: string[];
      optional_columns: string[];
      notes: Record<string, string>;
    }>(`${API_ENDPOINTS.admin.upload}/template`),

  // ── Export counts ──

  getWeatherCount: (params?: {
    start_date?: string;
    end_date?: string;
    source?: string;
  }) =>
    api.get<ExportCountResponse>(API_ENDPOINTS.export.weatherCount, {
      params,
    }),

  getPredictionsCount: (params?: {
    start_date?: string;
    end_date?: string;
    risk_level?: string;
  }) =>
    api.get<ExportCountResponse>(API_ENDPOINTS.export.predictionsCount, {
      params,
    }),

  getAlertsCount: (params?: {
    start_date?: string;
    end_date?: string;
    risk_level?: string;
  }) =>
    api.get<ExportCountResponse>(API_ENDPOINTS.export.alertsCount, {
      params,
    }),

  // ── Export downloads ──

  exportWeather: (params?: {
    start_date?: string;
    end_date?: string;
    source?: string;
    format?: string;
    limit?: number;
  }) =>
    api.get<Blob>(API_ENDPOINTS.export.weather, {
      params: { format: "csv", limit: 10000, ...params },
      responseType: "blob",
    }),

  exportPredictions: (params?: {
    start_date?: string;
    end_date?: string;
    risk_level?: string;
    format?: string;
    limit?: number;
  }) =>
    api.get<Blob>(API_ENDPOINTS.export.predictions, {
      params: { format: "csv", limit: 10000, ...params },
      responseType: "blob",
    }),

  exportAlerts: (params?: {
    start_date?: string;
    end_date?: string;
    risk_level?: string;
    format?: string;
    limit?: number;
  }) =>
    api.get<Blob>(API_ENDPOINTS.export.alerts, {
      params: { format: "csv", limit: 10000, ...params },
      responseType: "blob",
    }),
};
