/**
 * useLivePrediction Hook
 *
 * Fires a location-based /predict call on mount and refreshes
 * every 5 minutes. Used by the Resident dashboard hero card
 * to show live flood risk status.
 */

import { useQuery } from '@tanstack/react-query';
import { predictionApi } from '@/features/flooding/services/predictionApi';
import type { PredictionResponse } from '@/types';

const DEFAULT_LAT = 14.4793;
const DEFAULT_LON = 121.0198;
const REFRESH_INTERVAL = 5 * 60 * 1000; // 5 minutes

interface UseLivePredictionOptions {
  lat?: number;
  lon?: number;
  enabled?: boolean;
}

/**
 * Automatically fetches flood prediction for a location on mount
 * and refreshes every 5 minutes.
 */
export function useLivePrediction({
  lat = DEFAULT_LAT,
  lon = DEFAULT_LON,
  enabled = true,
}: UseLivePredictionOptions = {}) {
  return useQuery<PredictionResponse>({
    queryKey: ['prediction', 'live', lat, lon],
    queryFn: () =>
      predictionApi.predictByLocation({
        latitude: lat,
        longitude: lon,
      }),
    enabled,
    staleTime: REFRESH_INTERVAL,
    refetchInterval: REFRESH_INTERVAL,
    retry: 2,
    refetchOnWindowFocus: true,
  });
}
