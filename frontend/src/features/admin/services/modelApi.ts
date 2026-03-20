/**
 * Model Management API Service
 *
 * Dedicated API methods for the AI Model Control admin page.
 * Wraps feature-importance and model-specific endpoints.
 */

import { API_ENDPOINTS } from "@/config/api.config";
import api from "@/lib/api-client";

// ── Types ──

export interface FeatureImportanceEntry {
  feature: string;
  importance: number;
}

export interface FeatureImportanceResponse {
  features: FeatureImportanceEntry[];
  model_version: number | null;
}

export interface CalibrationResponse {
  model_version: number | null;
  cross_validation: {
    cv_folds?: number;
    cv_mean?: number;
    cv_std?: number;
  };
  metrics: Record<string, number>;
  calibration?: Record<string, unknown>;
}

// ── API Methods ──

export const modelApi = {
  getFeatureImportance: async (): Promise<FeatureImportanceResponse> => {
    return api.get<FeatureImportanceResponse>(
      API_ENDPOINTS.models.featureImportance,
    );
  },

  getCalibration: async (): Promise<CalibrationResponse> => {
    return api.get<CalibrationResponse>(API_ENDPOINTS.models.calibration);
  },
};
