/**
 * useHazardMap Hook
 *
 * Fetches GeoJSON flood hazard overlay data from the GIS API
 * for rendering barangay-level hazard polygons on the map.
 */

import { useState, useEffect, useCallback } from 'react';
import api from '@/lib/api-client';
import { API_ENDPOINTS } from '@/config/api.config';
import { captureException } from '@/lib/sentry';

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
  drainage_capacity: 'poor' | 'moderate' | 'good';
  impervious_surface_pct: number;
  flood_history_events: number;
  hazard_score: number;
  hazard_classification: 'low' | 'moderate' | 'high';
  hazard_color: string;
  hazard_factors: Record<string, number>;
  current_rainfall_mm: number;
}

export interface HazardFeature {
  type: 'Feature';
  geometry: {
    type: 'Polygon';
    coordinates: number[][][];
  };
  properties: HazardFeatureProperties;
}

export interface HazardMapData {
  type: 'FeatureCollection';
  features: HazardFeature[];
  metadata: {
    city: string;
    barangay_count: number;
    generated_at: string;
    crs: string;
    data_sources: string[];
  };
}

type OverlayType = 'hazard' | 'elevation' | 'drainage';

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

/**
 * Fetches GIS hazard/elevation/drainage overlay data from the backend.
 */
export function useHazardMap(options: UseHazardMapOptions = {}): UseHazardMapReturn {
  const {
    overlay = 'hazard',
    includeRainfall = true,
    refreshInterval = 0,
    enabled = true,
  } = options;

  const [data, setData] = useState<HazardMapData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchData = useCallback(async () => {
    if (!enabled) return;
    setIsLoading(true);
    setError(null);

    try {
      let endpoint: string;
      const params = new URLSearchParams();

      switch (overlay) {
        case 'elevation':
          endpoint = API_ENDPOINTS.gis.elevation;
          break;
        case 'drainage':
          endpoint = API_ENDPOINTS.gis.drainage;
          break;
        case 'hazard':
        default:
          endpoint = API_ENDPOINTS.gis.hazardMap;
          params.set('include_rainfall', includeRainfall.toString());
          break;
      }

      const url = params.toString() ? `${endpoint}?${params}` : endpoint;
      const response = await api.get<{ success: boolean; data: HazardMapData }>(url);

      if (response.success && response.data) {
        setData(response.data);
        setLastUpdated(new Date());
      } else {
        setError('Failed to load GIS data');
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch hazard map data';
      setError(message);
      captureException(err, { context: 'useHazardMap fetch' });
    } finally {
      setIsLoading(false);
    }
  }, [enabled, overlay, includeRainfall]);

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
  }, [refreshInterval, enabled, fetchData]);

  return {
    data,
    isLoading,
    error,
    refresh: fetchData,
    lastUpdated,
  };
}

export default useHazardMap;
