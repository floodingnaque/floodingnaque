/**
 * useForecastMap Hook
 *
 * Fetches per-barangay flood risk predictions at current, +1 h, and +3 h
 * offsets from the forecast-map endpoint. Use with ForecastOverlay.
 */

import { API_ENDPOINTS } from "@/config/api.config";
import { api } from "@/lib/api-client";
import { useQuery } from "@tanstack/react-query";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface BarangayForecast {
  risk_level: 0 | 1 | 2;
  risk_label: "Safe" | "Alert" | "Critical";
  probability: number;
  confidence: number;
}

export interface ForecastMapResponse {
  success: boolean;
  barangays: Record<string, Record<string, BarangayForecast>>;
  offsets: number[];
  weather_snapshot: {
    temperature: number;
    humidity: number;
    precipitation: number;
    source: string;
  };
  timestamp: string;
}

// ---------------------------------------------------------------------------
// Query key factory
// ---------------------------------------------------------------------------

export const forecastKeys = {
  all: ["forecast-map"] as const,
  map: (offsets?: string) => [...forecastKeys.all, offsets ?? "0,1,3"] as const,
};

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useForecastMap(offsets = "0,1,3", enabled = true) {
  return useQuery<ForecastMapResponse>({
    queryKey: forecastKeys.map(offsets),
    queryFn: async ({ signal }) => {
      return api.get<ForecastMapResponse>(
        API_ENDPOINTS.predict.forecastMap,
        { params: { hours: offsets }, signal },
      );
    },
    enabled,
    staleTime: 5 * 60 * 1000, // 5 min
    refetchInterval: 5 * 60 * 1000,
    retry: 1,
  });
}
