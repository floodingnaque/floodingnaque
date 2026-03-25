/**
 * Tides API Service
 *
 * Provides API methods for fetching tidal data from WorldTides.
 *
 * Backend returns `api_success()` shape: `{ success, data: {...}, message }`.
 * `api.get()` strips the Axios wrapper → we get the raw JSON body.
 * Each method unwraps `.data` so callers see the domain payload directly.
 */

import { API_ENDPOINTS } from "@/config/api.config";
import { api } from "@/lib/api-client";

export interface TideDataPoint {
  dt?: number;
  date?: string;
  timestamp?: string;
  height: number;
  type?: string;
  datum?: string;
}

export interface CurrentTideResponse {
  height: number;
  datum: string;
  source: string;
  timestamp: string;
}

export interface TideExtremesResponse {
  extremes: TideDataPoint[];
  count: number;
  days: number;
}

export interface TidePredictionResponse {
  current_height: number;
  risk_factor: "low" | "moderate" | "high";
  next_high_tide?: TideDataPoint;
  message: string;
}

export interface TideStatusResponse {
  active_provider: string;
  worldtides: {
    installed: boolean;
    enabled: boolean;
    api_key_configured: boolean;
    default_datum: string;
    [key: string]: unknown;
  };
  open_meteo_fallback: {
    installed: boolean;
    enabled: boolean;
    [key: string]: unknown;
  };
}

/** Shape returned by `api_success()` after Axios unwrap */
interface ApiSuccessWrapper<T> {
  success: boolean;
  data: T;
  message?: string;
  request_id?: string;
}

export const tidesApi = {
  getCurrent: async (): Promise<CurrentTideResponse> => {
    const raw = await api.get<ApiSuccessWrapper<CurrentTideResponse>>(
      API_ENDPOINTS.tides.current,
    );
    return raw.data;
  },

  getExtremes: async (): Promise<TideExtremesResponse> => {
    const raw = await api.get<ApiSuccessWrapper<TideExtremesResponse>>(
      API_ENDPOINTS.tides.extremes,
    );
    return raw.data;
  },

  getPrediction: async (): Promise<TidePredictionResponse> => {
    const raw = await api.get<ApiSuccessWrapper<TidePredictionResponse>>(
      API_ENDPOINTS.tides.prediction,
    );
    return raw.data;
  },

  getStatus: async (): Promise<TideStatusResponse> => {
    const raw = await api.get<ApiSuccessWrapper<TideStatusResponse>>(
      API_ENDPOINTS.tides.status,
    );
    return raw.data;
  },
};
