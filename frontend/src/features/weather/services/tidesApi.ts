/**
 * Tides API Service
 *
 * Provides API methods for fetching tidal data from WorldTides.
 */

import { api } from '@/lib/api-client';
import { API_ENDPOINTS } from '@/config/api.config';

export interface TideDataPoint {
  dt: number;
  date: string;
  height: number;
  type?: string;
}

export interface CurrentTideResponse {
  success: boolean;
  height: number;
  datum: string;
  station: string;
  timestamp: string;
  unit: string;
}

export interface TideExtremesResponse {
  success: boolean;
  extremes: TideDataPoint[];
  datum: string;
  station: string;
}

export interface TidePredictionResponse {
  success: boolean;
  current_height: number;
  risk_factor: 'low' | 'moderate' | 'high';
  next_high_tide?: TideDataPoint;
  message: string;
}

export interface TideStatusResponse {
  success: boolean;
  enabled: boolean;
  api_configured: boolean;
  datum: string;
}

export const tidesApi = {
  getCurrent: async (): Promise<CurrentTideResponse> => {
    return api.get<CurrentTideResponse>(API_ENDPOINTS.tides.current);
  },

  getExtremes: async (): Promise<TideExtremesResponse> => {
    return api.get<TideExtremesResponse>(API_ENDPOINTS.tides.extremes);
  },

  getPrediction: async (): Promise<TidePredictionResponse> => {
    return api.get<TidePredictionResponse>(API_ENDPOINTS.tides.prediction);
  },

  getStatus: async (): Promise<TideStatusResponse> => {
    return api.get<TideStatusResponse>(API_ENDPOINTS.tides.status);
  },
};
