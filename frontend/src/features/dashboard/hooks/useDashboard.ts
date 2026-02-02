/**
 * useDashboard Hook
 *
 * React Query hooks for fetching and managing dashboard data
 * with automatic refresh capabilities.
 */

import { useQuery } from '@tanstack/react-query';
import { dashboardApi, type DashboardStats } from '../services/dashboardApi';

/**
 * Query keys for dashboard-related queries
 */
export const dashboardQueryKeys = {
  all: ['dashboard'] as const,
  stats: () => [...dashboardQueryKeys.all, 'stats'] as const,
};

/**
 * Hook for fetching dashboard statistics
 *
 * Features:
 * - 1 minute stale time (data considered fresh for 1 minute)
 * - Auto-refresh every 5 minutes
 * - Automatic retry on failure
 *
 * @returns Query result with dashboard stats
 */
export function useDashboardStats() {
  return useQuery<DashboardStats>({
    queryKey: dashboardQueryKeys.stats(),
    queryFn: dashboardApi.getStats,
    staleTime: 1000 * 60, // 1 minute
    refetchInterval: 1000 * 60 * 5, // 5 minutes
    refetchIntervalInBackground: false, // Don't refetch when tab is hidden
  });
}

export default useDashboardStats;
