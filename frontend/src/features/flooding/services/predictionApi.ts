/**
 * Prediction API Service
 *
 * Provides API methods for flood risk prediction functionality.
 */

import { api } from '@/lib/api-client';
import { API_ENDPOINTS } from '@/config/api.config';
import type { PredictionRequest, PredictionResponse } from '@/types';

/**
 * Prediction API methods
 */
export const predictionApi = {
  /**
   * Submit a flood risk prediction request
   *
   * @param data - Prediction request data with weather parameters
   * @returns Prediction response with risk assessment
   *
   * @example
   * const result = await predictionApi.predict({
   *   temperature: 298.15,  // Kelvin
   *   humidity: 85,         // Percentage
   *   precipitation: 50,    // mm
   *   wind_speed: 15,       // m/s
   *   pressure: 1013,       // hPa (optional)
   * });
   */
  predict: async (data: PredictionRequest): Promise<PredictionResponse> => {
    return api.post<PredictionResponse>(API_ENDPOINTS.predict.predict, data);
  },
};

export default predictionApi;
