/**
 * Sensor API Service
 *
 * API methods for weather data ingestion and retrieval.
 */

import { API_ENDPOINTS } from "@/config/api.config";
import { api } from "@/lib/api-client";
import type { ApiResponse } from "@/types/api/common";
import type { HourlyResponse, SensorSubmitPayload } from "../types";

export const sensorApi = {
  /** Submit a new weather observation */
  submit: async (payload: SensorSubmitPayload) => {
    return api.post<ApiResponse<unknown>>(
      API_ENDPOINTS.data.weather,
      payload,
    );
  },

  /** Fetch recent hourly weather data */
  getHourly: async (days = 1) => {
    const end = new Date();
    const start = new Date();
    start.setDate(start.getDate() - days);
    return api.get<HourlyResponse>(API_ENDPOINTS.data.hourly, {
      params: {
        start_date: start.toISOString(),
        end_date: end.toISOString(),
      },
    });
  },
};
