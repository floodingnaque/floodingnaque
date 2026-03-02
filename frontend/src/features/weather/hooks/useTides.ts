/**
 * useTides Hook
 *
 * TanStack Query hooks for tidal data from the WorldTides API.
 */

import { useQuery } from '@tanstack/react-query';
import { tidesApi } from '../services/tidesApi';

export function useCurrentTide(enabled = true) {
  return useQuery({
    queryKey: ['tides', 'current'],
    queryFn: tidesApi.getCurrent,
    enabled,
    staleTime: 30 * 60 * 1000, // 30 min - tides change slowly
    refetchInterval: 30 * 60 * 1000,
    retry: 1,
  });
}

export function useTideExtremes(enabled = true) {
  return useQuery({
    queryKey: ['tides', 'extremes'],
    queryFn: tidesApi.getExtremes,
    enabled,
    staleTime: 60 * 60 * 1000, // 1 hour
    retry: 1,
  });
}

export function useTidePrediction(enabled = true) {
  return useQuery({
    queryKey: ['tides', 'prediction'],
    queryFn: tidesApi.getPrediction,
    enabled,
    staleTime: 15 * 60 * 1000,
    refetchInterval: 15 * 60 * 1000,
    retry: 1,
  });
}

export function useTideStatus() {
  return useQuery({
    queryKey: ['tides', 'status'],
    queryFn: tidesApi.getStatus,
    staleTime: 5 * 60 * 1000,
    retry: 1,
  });
}
