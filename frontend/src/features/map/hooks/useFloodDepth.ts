/**
 * useFloodDepth Hook
 *
 * Fetches per-barangay flood depth estimates from the /flood-depth endpoint.
 */

import { API_ENDPOINTS } from "@/config/api.config";
import { api } from "@/lib/api-client";
import { useQuery } from "@tanstack/react-query";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface BarangayDepth {
  depth_cm: number;
  depth_range_cm: [number, number];
  classification: "none" | "minor" | "moderate" | "major" | "severe";
  uncertainty_pct: number;
}

export interface FloodDepthResponse {
  barangays: Record<string, BarangayDepth>;
  generated_at: string;
}

// ---------------------------------------------------------------------------
// Query keys
// ---------------------------------------------------------------------------

export const floodDepthKeys = {
  all: ["flood-depth"] as const,
  data: () => [...floodDepthKeys.all, "data"] as const,
};

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useFloodDepth(enabled = true) {
  return useQuery<FloodDepthResponse>({
    queryKey: floodDepthKeys.data(),
    queryFn: async ({ signal }) => {
      return api.get<FloodDepthResponse>(API_ENDPOINTS.gis.floodDepth, {
        signal,
      });
    },
    staleTime: 5 * 60 * 1000,
    refetchInterval: 5 * 60 * 1000,
    enabled,
  });
}
