/**
 * useLivePrediction Hook
 *
 * Fires a location-based /predict call on mount and refreshes
 * every 60 seconds. Used by the Resident dashboard hero card
 * to show live flood risk status.
 */

import { predictionApi } from "@/features/flooding/services/predictionApi";
import type { PredictionResponse } from "@/types";
import { useQuery } from "@tanstack/react-query";

const DEFAULT_LAT = 14.4793;
const DEFAULT_LON = 121.0198;
const REFRESH_INTERVAL = 60 * 1000; // 60 seconds

interface UseLivePredictionOptions {
  lat?: number;
  lon?: number;
  enabled?: boolean;
}

/**
 * Automatically fetches flood prediction for a location on mount
 * and refreshes every 60 seconds.
 */
export function useLivePrediction({
  lat = DEFAULT_LAT,
  lon = DEFAULT_LON,
  enabled = true,
}: UseLivePredictionOptions = {}) {
  return useQuery<PredictionResponse>({
    queryKey: ["prediction", "live", lat, lon],
    queryFn: ({ signal }) =>
      predictionApi.predictByLocation(
        { latitude: lat, longitude: lon },
        { signal },
      ),
    enabled,
    staleTime: REFRESH_INTERVAL,
    refetchInterval: REFRESH_INTERVAL,
    retry: 2,
    refetchOnWindowFocus: true,
    refetchIntervalInBackground: true,
  });
}
