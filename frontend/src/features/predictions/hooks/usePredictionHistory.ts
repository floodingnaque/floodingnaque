/**
 * usePredictionHistory Hook
 *
 * Provides queries for prediction history data.
 * Falls back to IndexedDB-cached predictions when offline.
 */

import { useQuery } from '@tanstack/react-query';
import {
  predictionApi,
  type PredictionListParams,
  type PredictionListResponse,
} from '../services/predictionApi';
import {
  getCachedPredictions,
  type CachedPrediction,
} from '@/lib/offlineCache';
import { useNetworkStatus } from '@/hooks/useNetworkStatus';

/**
 * Query keys
 */
export const predictionQueryKeys = {
  all: ['predictions'] as const,
  list: (params?: PredictionListParams) =>
    [...predictionQueryKeys.all, 'list', params] as const,
  stats: () => [...predictionQueryKeys.all, 'stats'] as const,
  cachedOffline: () => [...predictionQueryKeys.all, 'cached-offline'] as const,
};

/**
 * Hook to fetch paginated prediction history
 */
export function usePredictionHistory(params?: PredictionListParams) {
  return useQuery({
    queryKey: predictionQueryKeys.list(params),
    queryFn: () => predictionApi.list(params),
    staleTime: 60_000,
  });
}

/**
 * Hook to fetch prediction statistics
 */
export function usePredictionStats() {
  return useQuery({
    queryKey: predictionQueryKeys.stats(),
    queryFn: () => predictionApi.getStats(),
    staleTime: 60_000,
  });
}

/**
 * Hook that returns cached offline predictions when the browser is
 * offline, converting them into the same shape as the API response.
 *
 * Returns `{ data, isOffline, cachedAt }`.
 */
export function useOfflinePredictions(limit: number = 20) {
  const { isOnline } = useNetworkStatus();

  const query = useQuery<{
    predictions: PredictionListResponse;
    cachedAt: string | null;
  }>({
    queryKey: predictionQueryKeys.cachedOffline(),
    queryFn: async () => {
      const cached: CachedPrediction[] = await getCachedPredictions(limit);

      const predictions: PredictionListResponse = {
        data: cached.map((c, idx) => ({
          id: c.id ?? idx,
          risk_level: c.data.risk_level,
          flood_probability: c.data.probability,
          location: undefined,
          latitude: undefined,
          longitude: undefined,
          created_at: c.data.timestamp,
          input_data: c.data.weather_data as unknown as Record<string, unknown>,
        })),
        page: 1,
        pages: 1,
        total: cached.length,
        per_page: limit,
      };

      return {
        predictions,
        cachedAt: cached[0]?.cachedAt ?? null,
      };
    },
    // Only activate this query when offline
    enabled: !isOnline,
    staleTime: Infinity,
  });

  return {
    data: query.data?.predictions ?? null,
    cachedAt: query.data?.cachedAt ?? null,
    isOffline: !isOnline,
    isLoading: query.isLoading,
  };
}

export default usePredictionHistory;
