/**
 * Model Management Hooks
 *
 * TanStack Query hooks for the AI Model Control admin page.
 * Provides feature importance, calibration, and model history data.
 */

import { useQuery } from "@tanstack/react-query";
import { modelApi } from "../services/modelApi";

export const modelQueryKeys = {
  all: ["model"] as const,
  featureImportance: () =>
    [...modelQueryKeys.all, "featureImportance"] as const,
  calibration: () => [...modelQueryKeys.all, "calibration"] as const,
};

export function useFeatureImportance() {
  return useQuery({
    queryKey: modelQueryKeys.featureImportance(),
    queryFn: () => modelApi.getFeatureImportance(),
    staleTime: 60_000 * 60, // 1 hour
  });
}

export function useCalibration() {
  return useQuery({
    queryKey: modelQueryKeys.calibration(),
    queryFn: () => modelApi.getCalibration(),
    staleTime: 60_000 * 60,
  });
}
