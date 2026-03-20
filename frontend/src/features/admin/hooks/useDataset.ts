/**
 * Dataset Hooks
 *
 * TanStack Query hooks for the Dataset Management page.
 */

import { datasetApi } from "@/features/admin/services/datasetApi";
import { useQuery } from "@tanstack/react-query";

export const datasetQueryKeys = {
  all: ["dataset"] as const,
  stats: () => [...datasetQueryKeys.all, "stats"] as const,
  weatherCount: (params?: Record<string, string | undefined>) =>
    [...datasetQueryKeys.all, "weatherCount", params] as const,
  predictionsCount: (params?: Record<string, string | undefined>) =>
    [...datasetQueryKeys.all, "predictionsCount", params] as const,
  alertsCount: (params?: Record<string, string | undefined>) =>
    [...datasetQueryKeys.all, "alertsCount", params] as const,
};

export function useDatasetStats() {
  return useQuery({
    queryKey: datasetQueryKeys.stats(),
    queryFn: () => datasetApi.getStats(),
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
}

export function useWeatherCount(params?: {
  start_date?: string;
  end_date?: string;
  source?: string;
}) {
  return useQuery({
    queryKey: datasetQueryKeys.weatherCount(params),
    queryFn: () => datasetApi.getWeatherCount(params),
    staleTime: 15_000,
  });
}

export function usePredictionsCount(params?: {
  start_date?: string;
  end_date?: string;
  risk_level?: string;
}) {
  return useQuery({
    queryKey: datasetQueryKeys.predictionsCount(params),
    queryFn: () => datasetApi.getPredictionsCount(params),
    staleTime: 15_000,
  });
}

export function useAlertsCount(params?: {
  start_date?: string;
  end_date?: string;
  risk_level?: string;
}) {
  return useQuery({
    queryKey: datasetQueryKeys.alertsCount(params),
    queryFn: () => datasetApi.getAlertsCount(params),
    staleTime: 15_000,
  });
}
