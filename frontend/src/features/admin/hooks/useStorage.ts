/**
 * Storage Management Hooks
 *
 * TanStack Query hooks for real-time storage stats
 * and cleanup count previews.
 */

import {
  storageApi,
  type CleanupCountResponse,
  type StorageStatsResponse,
} from "@/features/admin/services/storageApi";
import { useQuery } from "@tanstack/react-query";

// ── Query Keys ──

export const storageQueryKeys = {
  all: ["storage"] as const,
  stats: () => [...storageQueryKeys.all, "stats"] as const,
  cleanupCount: (params: Record<string, unknown>) =>
    [...storageQueryKeys.all, "cleanup-count", params] as const,
};

// ── Hooks ──

export function useStorageStats() {
  return useQuery<StorageStatsResponse>({
    queryKey: storageQueryKeys.stats(),
    queryFn: () => storageApi.getStats(),
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
}

export function useCleanupCount(params: {
  type: "logs" | "reports" | "alerts";
  older_than_days: number;
  status?: string;
  delivery_status?: string;
  enabled?: boolean;
}) {
  const { enabled = true, ...queryParams } = params;
  return useQuery<CleanupCountResponse>({
    queryKey: storageQueryKeys.cleanupCount(queryParams),
    queryFn: () => storageApi.getCleanupCount(queryParams),
    staleTime: 15_000,
    enabled: enabled && queryParams.older_than_days >= 1,
  });
}
