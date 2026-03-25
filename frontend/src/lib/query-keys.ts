/**
 * Central Query Key Registry
 *
 * Re-exports all per-feature query key factories for easy discovery
 * and consistent cache invalidation across roles. Each feature owns
 * its own keys — this file simply aggregates them.
 */

export { alertKeys } from "@/features/alerts/hooks/useAlerts";
export { authQueryKeys } from "@/features/auth/hooks/useAuth";
export { dashboardQueryKeys } from "@/features/dashboard/hooks/useDashboard";
export { weatherKeys } from "@/features/weather/hooks/useWeather";

/**
 * Shared query key prefixes for cross-feature invalidation.
 *
 * Usage:
 *   queryClient.invalidateQueries({ queryKey: QUERY_PREFIXES.alerts })
 */
export const QUERY_PREFIXES = {
  alerts: ["alerts"] as const,
  weather: ["weather"] as const,
  dashboard: ["dashboard"] as const,
  prediction: ["prediction"] as const,
  chat: ["chat"] as const,
  barangays: ["barangays"] as const,
  auth: ["auth"] as const,
} as const;
