/**
 * usePagasaRadar Hook
 *
 * Fetches radar-based precipitation estimates from the PAGASA integration.
 * Provides per-barangay rainfall data and city-wide summary.
 */

import { API_ENDPOINTS } from "@/config/api.config";
import api from "@/lib/api-client";
import { captureException } from "@/lib/sentry";
import { useCallback, useEffect, useState } from "react";

/** Per-barangay precipitation estimate */
export interface BarangayPrecipitation {
  barangay_key: string;
  barangay_name: string;
  lat: number;
  lon: number;
  rainfall_mm: number;
  intensity:
    | "no_rain"
    | "light"
    | "moderate"
    | "heavy"
    | "intense"
    | "torrential";
  timestamp: string;
  source: string;
  confidence: number;
  calibrated: boolean;
}

/** City-wide precipitation summary */
export interface PrecipitationSummary {
  average_rainfall_mm: number;
  max_rainfall_mm: number;
  max_rainfall_barangay: string;
  overall_intensity: string;
  barangay_count: number;
  source: string;
  calibrated: boolean;
}

/** Full PAGASA precipitation response */
export interface PagasaPrecipitationData {
  status: "ok" | "disabled" | "error";
  city: string;
  timestamp: string;
  summary: PrecipitationSummary;
  barangays: Record<string, BarangayPrecipitation>;
  message?: string;
}

/** Rainfall advisory data */
export interface RainfallAdvisory {
  status: "ok" | "unavailable" | "disabled";
  warning_level: string;
  title: string;
  description: string;
  affected_areas: string[];
  issued_at?: string;
  valid_until?: string;
  source: string;
}

interface UsePagasaRadarOptions {
  /** Whether to fetch data (default: true) */
  enabled?: boolean;
  /** Auto-refresh interval in milliseconds (default: 300000 = 5 min) */
  refreshInterval?: number;
  /** Also fetch rainfall advisory (default: false) */
  includeAdvisory?: boolean;
}

interface UsePagasaRadarReturn {
  /** Precipitation data for all barangays */
  precipitation: PagasaPrecipitationData | null;
  /** Rainfall advisory (if includeAdvisory = true) */
  advisory: RainfallAdvisory | null;
  /** Whether data is currently loading */
  isLoading: boolean;
  /** Error message if fetch failed */
  error: string | null;
  /** Manually trigger refresh */
  refresh: () => void;
  /** Timestamp of last successful fetch */
  lastUpdated: Date | null;
}

/**
 * Hook for fetching PAGASA radar precipitation data
 */
export function usePagasaRadar(
  options: UsePagasaRadarOptions = {},
): UsePagasaRadarReturn {
  const {
    enabled = true,
    refreshInterval = 300_000, // 5 minutes
    includeAdvisory = false,
  } = options;

  const [precipitation, setPrecipitation] =
    useState<PagasaPrecipitationData | null>(null);
  const [advisory, setAdvisory] = useState<RainfallAdvisory | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchData = useCallback(async () => {
    if (!enabled) return;
    setIsLoading(true);
    setError(null);

    try {
      // Fetch precipitation
      const precipResponse = await api.get<{
        success: boolean;
        data: PagasaPrecipitationData;
      }>(API_ENDPOINTS.pagasa.precipitation);

      if (precipResponse.success && precipResponse.data) {
        setPrecipitation(precipResponse.data);
        setLastUpdated(new Date());
      }

      // Optionally fetch advisory
      if (includeAdvisory) {
        try {
          const advisoryResponse = await api.get<{
            success: boolean;
            data: RainfallAdvisory;
          }>(API_ENDPOINTS.pagasa.advisory);

          if (advisoryResponse.success && advisoryResponse.data) {
            setAdvisory(advisoryResponse.data);
          }
        } catch (advErr) {
          // Advisory fetch failure is non-critical
          console.warn("Failed to fetch rainfall advisory:", advErr);
        }
      }
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to fetch PAGASA data";
      setError(message);
      captureException(err, { context: "usePagasaRadar fetch" });
    } finally {
      setIsLoading(false);
    }
  }, [enabled, includeAdvisory]);

  // Initial fetch
  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Auto-refresh
  useEffect(() => {
    if (refreshInterval > 0 && enabled) {
      const interval = setInterval(fetchData, refreshInterval);
      return () => clearInterval(interval);
    }
    return undefined;
  }, [refreshInterval, enabled, fetchData]);

  return {
    precipitation,
    advisory,
    isLoading,
    error,
    refresh: fetchData,
    lastUpdated,
  };
}

export default usePagasaRadar;
