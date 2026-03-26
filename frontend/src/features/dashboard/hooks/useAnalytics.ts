/**
 * useAnalytics Hooks
 *
 * React Query hooks for fetching historical flood data
 * and model confidence metrics.
 */

import { API_ENDPOINTS } from "@/config/api.config";
import api from "@/lib/api-client";
import { useQuery } from "@tanstack/react-query";
import { analyticsApi } from "../services/analyticsApi";
import type { FloodHistoryData, ModelMetricsData } from "../types";

/**
 * Query keys for analytics-related queries
 */
export const analyticsQueryKeys = {
  all: ["analytics"] as const,
  history: () => [...analyticsQueryKeys.all, "history"] as const,
  metrics: () => [...analyticsQueryKeys.all, "metrics"] as const,
  modelHistory: () => [...analyticsQueryKeys.all, "modelHistory"] as const,
  featureImportance: () =>
    [...analyticsQueryKeys.all, "featureImportance"] as const,
  calibration: () => [...analyticsQueryKeys.all, "calibration"] as const,
};

/**
 * Hook for fetching historical flood data (frequency, yearly, monthly, recent events).
 * Data is considered fresh for 10 minutes and auto-refreshes every 30 minutes.
 */
export function useFloodHistory() {
  return useQuery<FloodHistoryData>({
    queryKey: analyticsQueryKeys.history(),
    queryFn: analyticsApi.getFloodHistory,
    staleTime: 1000 * 60 * 10,
    refetchInterval: 1000 * 60 * 30,
  });
}

/**
 * Hook for fetching model confidence metrics (precision, recall, F1, etc.).
 * Metrics change rarely - stale for 30 minutes.
 */
export function useModelMetrics() {
  return useQuery<ModelMetricsData>({
    queryKey: analyticsQueryKeys.metrics(),
    queryFn: analyticsApi.getModelMetrics,
    staleTime: 1000 * 60 * 30,
  });
}

/** Model version entry from /api/models/history */
export interface ModelVersionEntry {
  version: number;
  name: string;
  description: string;
  model_type?: string;
  created_at: string;
  is_active: boolean;
  training_data: {
    total_records: number;
    num_features: number;
    files: string[];
  };
  metrics: {
    accuracy: number;
    precision: number;
    recall: number;
    f1_score: number;
    f2_score: number;
    roc_auc: number;
    cv_mean: number;
    cv_std: number;
  };
  cross_validation: { cv_folds: number; cv_mean: number; cv_std: number };
  features: string[];
  model_parameters?: Record<string, unknown>;
  file_size_bytes?: number | null;
  checksum?: string | null;
}

interface ModelHistoryResponse {
  models: ModelVersionEntry[];
  active_version: number | null;
}

/**
 * Hook for fetching model version history with real metrics from backend.
 * Replaces the deleted MODEL_VERSIONS constant.
 */
export function useModelHistory() {
  return useQuery<ModelHistoryResponse>({
    queryKey: analyticsQueryKeys.modelHistory(),
    queryFn: async () => {
      const res = await api.get<ModelHistoryResponse>(
        API_ENDPOINTS.models.history,
      );
      return res;
    },
    staleTime: 1000 * 60 * 60, // 1 hour - model versions change rarely
    refetchInterval: 60 * 1000, // auto-refresh every 60s for analytics dashboard
  });
}

/** Feature importance entry from /api/models/feature-importance */
export interface FeatureImportanceEntry {
  feature: string;
  importance: number;
}

interface FeatureImportanceResponse {
  features: FeatureImportanceEntry[];
  model_version: number | null;
}

/**
 * Hook for fetching real feature importances from the loaded model.
 * Replaces the deleted FEATURE_IMPORTANCES constant.
 */
export function useModelFeatureImportance() {
  return useQuery<FeatureImportanceResponse>({
    queryKey: analyticsQueryKeys.featureImportance(),
    queryFn: async () => {
      const res = await api.get<FeatureImportanceResponse>(
        API_ENDPOINTS.models.featureImportance,
      );
      return res;
    },
    staleTime: 1000 * 60 * 60,
  });
}
