/**
 * useAdmin Hook
 *
 * Provides system health queries for the admin dashboard.
 */

import { useQuery } from '@tanstack/react-query';
import { adminApi } from '../services/adminApi';

/**
 * Query keys for admin-related queries
 */
export const adminQueryKeys = {
  all: ['admin'] as const,
  health: () => [...adminQueryKeys.all, 'health'] as const,
};

/**
 * Hook to fetch system health status
 */
export function useSystemHealth(enabled = true) {
  return useQuery({
    queryKey: adminQueryKeys.health(),
    queryFn: () => adminApi.getHealth(),
    enabled,
    refetchInterval: 30_000, // Refresh every 30 seconds
    staleTime: 10_000,
  });
}

export default useSystemHealth;
