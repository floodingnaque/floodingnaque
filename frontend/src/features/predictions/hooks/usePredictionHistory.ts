/**
 * usePredictionHistory Hook
 *
 * Provides queries for prediction history data.
 */

import { useQuery } from '@tanstack/react-query';
import {
  predictionApi,
  type PredictionListParams,
} from '../services/predictionApi';

/**
 * Query keys
 */
export const predictionQueryKeys = {
  all: ['predictions'] as const,
  list: (params?: PredictionListParams) =>
    [...predictionQueryKeys.all, 'list', params] as const,
  stats: () => [...predictionQueryKeys.all, 'stats'] as const,
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

export default usePredictionHistory;
