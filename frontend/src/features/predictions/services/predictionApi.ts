/**
 * Prediction History API Service
 *
 * Provides API methods for fetching prediction history data.
 */

import api from '@/lib/api-client';
import { API_CONFIG } from '@/config/api.config';

const { endpoints } = API_CONFIG;

/**
 * Single prediction record from the API
 */
export interface PredictionRecord {
  id: number;
  risk_level: number;
  flood_probability: number;
  location?: string;
  latitude?: number;
  longitude?: number;
  created_at: string;
  input_data?: Record<string, unknown>;
}

/**
 * Paginated prediction list response
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
  order?: 'asc' | 'desc';
  start_date?: string;
  end_date?: string;
}

/**
 * Prediction history API methods
 */
export const predictionApi = {
  /**
   * Get paginated list of past predictions
   */
  list: async (params?: PredictionListParams): Promise<PredictionListResponse> => {
    const searchParams = new URLSearchParams();
    if (params?.page) searchParams.set('page', String(params.page));
    if (params?.limit) searchParams.set('limit', String(params.limit));
    if (params?.sort_by) searchParams.set('sort_by', params.sort_by);
    if (params?.order) searchParams.set('order', params.order);
    if (params?.start_date) searchParams.set('start_date', params.start_date);
    if (params?.end_date) searchParams.set('end_date', params.end_date);

    const qs = searchParams.toString();
    const url = qs
      ? `${endpoints.predictions.list}?${qs}`
      : endpoints.predictions.list;

    return api.get<PredictionListResponse>(url);
  },

  /**
   * Get prediction statistics
   */
  getStats: async (): Promise<PredictionStats> => {
    return api.get<PredictionStats>(endpoints.predictions.stats);
  },
};

export default predictionApi;
