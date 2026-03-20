/**
 * Prediction History API Service
 *
 * Provides API methods for fetching prediction history data.
 *
 * The backend uses offset-based pagination and different field names
 * (e.g. `confidence` instead of `flood_probability`).  This service
 * normalises those differences for the frontend.
 */

import { API_CONFIG } from "@/config/api.config";
import api from "@/lib/api-client";

const { endpoints } = API_CONFIG;

// ---------------------------------------------------------------------------
// Frontend-facing types
// ---------------------------------------------------------------------------

/**
 * Single prediction record from the API (frontend shape)
 */
export interface PredictionRecord {
  id: number;
  risk_level: number;
  flood_probability: number;
  risk_label?: string;
  location?: string;
  latitude?: number;
  longitude?: number;
  created_at: string;
  model_version?: string;
  model_name?: string;
  input_data?: Record<string, unknown>;
}

/**
 * Paginated prediction list response (frontend shape)
 */
export interface PredictionListResponse {
  data: PredictionRecord[];
  page: number;
  pages: number;
  total: number;
  per_page: number;
}

/**
 * Prediction statistics
 */
export interface PredictionStats {
  total: number;
  today: number;
  avg_risk: number;
  high_risk_count: number;
}

/**
 * Query parameters for listing predictions
 */
export interface PredictionListParams {
  page?: number;
  limit?: number;
  sort_by?: string;
  order?: "asc" | "desc";
  start_date?: string;
  end_date?: string;
}

// ---------------------------------------------------------------------------
// Backend response shapes (offset-based, different field names)
// ---------------------------------------------------------------------------

interface BackendPredictionRecord {
  id: number;
  weather_data_id?: number;
  prediction?: number;
  risk_level: number;
  risk_label?: string;
  confidence?: number;
  model_version?: string;
  model_name?: string;
  created_at: string;
  weather_data?: {
    temperature?: number;
    humidity?: number;
    precipitation?: number;
    wind_speed?: number;
    pressure?: number;
  };
}

interface BackendPredictionResponse {
  success: boolean;
  data: BackendPredictionRecord[];
  total: number;
  limit: number;
  offset: number;
  count: number;
  sort_by: string;
  order: string;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function pageToOffset(page: number, limit: number): number {
  return (Math.max(1, page) - 1) * limit;
}

function totalPages(total: number, limit: number): number {
  return Math.max(1, Math.ceil(total / limit));
}

function toFrontendRecord(r: BackendPredictionRecord): PredictionRecord {
  return {
    id: r.id,
    risk_level: r.risk_level,
    flood_probability: r.confidence ?? 0,
    risk_label: r.risk_label ?? undefined,
    location: r.risk_label ?? undefined,
    model_version: r.model_version ?? undefined,
    model_name: r.model_name ?? undefined,
    created_at: r.created_at,
    input_data: r.weather_data
      ? {
          temperature: r.weather_data.temperature,
          humidity: r.weather_data.humidity,
          precipitation: r.weather_data.precipitation,
          wind_speed: r.weather_data.wind_speed,
          pressure: r.weather_data.pressure,
        }
      : undefined,
  };
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Prediction history API methods
 */
export const predictionApi = {
  /**
   * Get paginated list of past predictions.
   *
   * Converts page-based params → offset-based query, then normalises the
   * backend response to match the frontend PredictionListResponse type.
   */
  list: async (
    params?: PredictionListParams,
  ): Promise<PredictionListResponse> => {
    const limit = params?.limit ?? 50;
    const page = params?.page ?? 1;

    const searchParams = new URLSearchParams();
    searchParams.set("limit", String(limit));
    searchParams.set("offset", String(pageToOffset(page, limit)));
    if (params?.sort_by) searchParams.set("sort_by", params.sort_by);
    if (params?.order) searchParams.set("order", params.order);
    if (params?.start_date) searchParams.set("start_date", params.start_date);
    if (params?.end_date) searchParams.set("end_date", params.end_date);

    const url = `${endpoints.predictions.list}?${searchParams}`;
    const raw = await api.get<BackendPredictionResponse>(url);

    return {
      data: raw.data.map(toFrontendRecord),
      page,
      pages: totalPages(raw.total, limit),
      total: raw.total,
      per_page: limit,
    };
  },

  /**
   * Get prediction statistics
   */
  getStats: async (): Promise<PredictionStats> => {
    return api.get<PredictionStats>(endpoints.predictions.stats);
  },
};

export default predictionApi;
