/**
 * Prediction API Service
 *
 * Provides API methods for flood risk prediction functionality.
 *
 * The backend response shape differs from the frontend PredictionResponse
 * type (e.g. `probability` is an object, several fields are absent).
 * This service normalises the response before returning it.
 */

import { API_ENDPOINTS } from "@/config/api.config";
import { api } from "@/lib/api-client";
import { PredictionResponseSchema } from "@/lib/schemas";
import type {
  LocationPredictionRequest,
  PredictionRequest,
  PredictionResponse,
} from "@/types";
import type { AxiosRequestConfig } from "axios";

// ---------------------------------------------------------------------------
// Backend response shape
// ---------------------------------------------------------------------------

interface BackendPredictResponse {
  success: boolean;
  api_version?: string;
  prediction: 0 | 1;
  probability: { flood: number; no_flood: number } | number;
  risk_level: 0 | 1 | 2;
  risk_label: "Safe" | "Alert" | "Critical";
  confidence: number;
  flood_risk?: string;
  model_version: string | null;
  features_used?: string[];
  timestamp?: string;
  request_id?: string;
  weather_data?: PredictionResponse["weather_data"];
  simulated_weather?: boolean;
  smart_alert?: PredictionResponse["smart_alert"];
  explanation?: PredictionResponse["explanation"];
}

// ---------------------------------------------------------------------------
// Normalisation helper
// ---------------------------------------------------------------------------

function toFrontendResponse(raw: BackendPredictResponse): PredictionResponse {
  // probability may be an object { flood, no_flood } or a plain number
  const probability =
    typeof raw.probability === "object" && raw.probability !== null
      ? raw.probability.flood
      : (raw.probability as number);

  const normalized = {
    prediction: raw.prediction,
    probability,
    risk_level: raw.risk_level,
    risk_label: raw.risk_label,
    confidence: raw.confidence,
    model_version: raw.model_version ?? "unknown",
    features_used: raw.features_used ?? [],
    timestamp: raw.timestamp ?? new Date().toISOString(),
    request_id: raw.request_id ?? "",
    weather_data: raw.weather_data,
    smart_alert: raw.smart_alert,
    explanation: raw.explanation,
  };

  // Runtime validation - log but don't crash on schema mismatch
  const result = PredictionResponseSchema.safeParse(normalized);
  if (!result.success) {
    console.warn(
      "[predictionApi] Response schema mismatch:",
      result.error.issues,
    );
  }

  return normalized;
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Prediction API methods
 */
export const predictionApi = {
  /**
   * Submit a flood risk prediction request with manual weather parameters
   */
  predict: async (
    data: PredictionRequest,
    config?: AxiosRequestConfig,
  ): Promise<PredictionResponse> => {
    const raw = await api.post<BackendPredictResponse>(
      API_ENDPOINTS.predict.predict,
      data,
      config,
    );
    return toFrontendResponse(raw);
  },

  /**
   * Submit a flood risk prediction using GPS coordinates.
   * The backend fetches current weather data for the given location.
   */
  predictByLocation: async (
    data: LocationPredictionRequest,
    config?: AxiosRequestConfig,
  ): Promise<PredictionResponse> => {
    const raw = await api.post<BackendPredictResponse>(
      API_ENDPOINTS.predict.predictByLocation,
      data,
      config,
    );
    return toFrontendResponse(raw);
  },
};

export default predictionApi;
