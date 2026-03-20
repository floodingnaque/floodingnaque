/**
 * useHazardMap Hook
 *
 * Fetches GeoJSON flood hazard overlay data from the GIS API
 * for rendering barangay-level hazard polygons on the map.
 *
 * Uses TanStack Query for automatic caching, deduplication,
 * signal-based cancellation on unmount, and stale-while-revalidate.
 */

import { API_ENDPOINTS } from "@/config/api.config";
import api from "@/lib/api-client";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useMemo } from "react";

/** GeoJSON Feature properties for a single barangay */
export interface HazardFeatureProperties {
  key: string;
  name: string;
  population: number;
  lat: number;
  lon: number;
  mean_elevation_m: number;
  min_elevation_m: number;
  slope_pct: number;
  nearest_waterway: string;
  distance_to_waterway_m: number;
  drainage_capacity: "poor" | "moderate" | "good";
  impervious_surface_pct: number;
  flood_history_events: number;
  hazard_score: number;
  hazard_classification: "low" | "moderate" | "high";
  hazard_color: string;
  hazard_factors: Record<string, number>;
  current_rainfall_mm: number;
}

export interface HazardFeature {
  type: "Feature";
  geometry: {
    type: "Polygon";
    coordinates: number[][][];
  };
  properties: HazardFeatureProperties;
}

export interface HazardMapData {
  type: "FeatureCollection";
  features: HazardFeature[];
  metadata: {
    city: string;
    barangay_count: number;
    generated_at: string;
    crs: string;
    data_sources: string[];
  };
}

type OverlayType = "hazard" | "elevation" | "drainage";

interface UseHazardMapOptions {
  /** Which overlay to fetch (default: 'hazard') */
  overlay?: OverlayType;
  /** Include live PAGASA radar rainfall in hazard scoring (default: true) */
  includeRainfall?: boolean;
  /** Auto-refresh interval in milliseconds (0 = disabled) */
  refreshInterval?: number;
  /** Whether the hook is enabled */
  enabled?: boolean;
}

interface UseHazardMapReturn {
  /** GeoJSON data for map rendering */
  data: HazardMapData | null;
  /** Whether the data is currently loading */
  isLoading: boolean;
  /** Error message if fetch failed */
  error: string | null;
  /** Manually trigger a refresh */
  refresh: () => void;
  /** Timestamp of last successful fetch */
  lastUpdated: Date | null;
}

/** Query key factory for hazard map data */
export const hazardMapKeys = {
  all: ["hazardMap"] as const,
  overlay: (overlay: OverlayType, includeRainfall: boolean) =>
    [...hazardMapKeys.all, overlay, includeRainfall] as const,
};

/** Build the API URL for a given overlay */
function buildHazardUrl(
  overlay: OverlayType,
  includeRainfall: boolean,
): string {
  let endpoint: string;
  const params = new URLSearchParams();

  switch (overlay) {
    case "elevation":
      endpoint = API_ENDPOINTS.gis.elevation;
      break;
    case "drainage":
      endpoint = API_ENDPOINTS.gis.drainage;
      break;
    case "hazard":
    default:
      endpoint = API_ENDPOINTS.gis.hazardMap;
      params.set("include_rainfall", includeRainfall.toString());
      break;
  }

  return params.toString() ? `${endpoint}?${params}` : endpoint;
}

/**
 * Fetches GIS hazard/elevation/drainage overlay data from the backend.
 *
 * Benefits over manual useState/useEffect:
 * - Automatic request deduplication (multiple components sharing same data)
 * - Signal-based cancellation on unmount (no memory leaks)
 * - Stale-while-revalidate caching (instant UI on revisit)
 * - Built-in refetchInterval for auto-refresh
 * - Garbage collection of unused cache entries
 */
export function useHazardMap(
  options: UseHazardMapOptions = {},
): UseHazardMapReturn {
  const {
    overlay = "hazard",
    includeRainfall = true,
    refreshInterval = 0,
    enabled = true,
  } = options;

  const queryClient = useQueryClient();

  const queryKey = hazardMapKeys.overlay(overlay, includeRainfall);

  const { data, isLoading, error, dataUpdatedAt } = useQuery({
    queryKey,
    queryFn: async ({ signal }) => {
      const url = buildHazardUrl(overlay, includeRainfall);
      const response = await api.get<{ success: boolean; data: HazardMapData }>(
        url,
        { signal },
      );

      if (response.success && response.data) {
        return response.data;
      }
      throw new Error("Failed to load GIS data");
    },
    enabled,
    staleTime: 5 * 60 * 1000, // 5 min — GIS data changes slowly
    gcTime: 10 * 60 * 1000, // Keep unused cache for 10 min
    refetchInterval: refreshInterval > 0 ? refreshInterval : false,
    retry: 2,
  });

  // Derive last-updated timestamp from query cache (no effect needed)
  const lastUpdated = useMemo(
    () => (dataUpdatedAt > 0 ? new Date(dataUpdatedAt) : null),
    [dataUpdatedAt],
  );

  const refresh = useCallback(() => {
    queryClient.invalidateQueries({ queryKey });
  }, [queryClient, queryKey]);

  return {
    data: data ?? null,
    isLoading,
    error: error
      ? error instanceof Error
        ? error.message
        : "Failed to fetch hazard map data"
      : null,
    refresh,
    lastUpdated,
  };
}

export default useHazardMap;
