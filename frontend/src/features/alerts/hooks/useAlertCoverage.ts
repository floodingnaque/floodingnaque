/**
 * useAlertCoverage – TanStack Query hook for alert delivery coverage data.
 */

import { API_ENDPOINTS } from "@/config/api.config";
import { api } from "@/lib/api-client";
import { useQuery } from "@tanstack/react-query";

export interface BarangayCoverage {
  delivered: number;
  pending: number;
  failed: number;
  partial: number;
  total: number;
  delivery_pct: number;
  risk_levels: Record<number, number>;
}

export interface CoverageResponse {
  success: boolean;
  coverage: {
    hours: number;
    total_alerts: number;
    total_delivered: number;
    total_failed: number;
    total_pending: number;
    delivery_rate_pct: number;
    median_delivery_seconds: number | null;
  };
  barangays: Record<string, BarangayCoverage>;
  channels: Record<
    string,
    { delivered: number; failed: number; pending: number; total: number }
  >;
}

export const coverageKeys = {
  all: ["alert-coverage"] as const,
  byHours: (hours: number) => [...coverageKeys.all, hours] as const,
};

export function useAlertCoverage(hours = 24) {
  return useQuery<CoverageResponse>({
    queryKey: coverageKeys.byHours(hours),
    queryFn: ({ signal }) =>
      api.get<CoverageResponse>(
        `${API_ENDPOINTS.alerts.coverage}?hours=${hours}`,
        { signal },
      ),
    staleTime: 60_000,
    refetchInterval: 5 * 60_000,
  });
}
