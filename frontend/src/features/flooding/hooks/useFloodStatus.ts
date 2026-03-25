/**
 * useFloodStatus Hook
 *
 * Unified hook for flood status consumed by all dashboards:
 *   - Resident: scoped to user's barangay (barangayId provided)
 *   - Operator/Admin: city-wide view (barangayId omitted)
 *
 * Wraps useLivePrediction with a role-consistent interface.
 */

import { useLivePrediction } from "./useLivePrediction";

interface FloodStatusOptions {
  /** Scope to a specific barangay (resident). Omit for city-wide. */
  lat?: number;
  lon?: number;
  /** Refetch interval in ms. Default: 60_000 (1 minute). */
  refetchInterval?: number;
  enabled?: boolean;
}

/**
 * Single hook for flood status used across all role dashboards.
 * Returns the same shape regardless of role — components decide
 * how to display based on the data.
 */
export function useFloodStatus(options: FloodStatusOptions = {}) {
  return useLivePrediction({
    lat: options.lat,
    lon: options.lon,
    enabled: options.enabled,
  });
}
