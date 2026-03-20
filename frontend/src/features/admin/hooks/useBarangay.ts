/**
 * Barangay Management Hooks
 *
 * TanStack Query hooks for live hazard data, evacuation center
 * status, and barangay detail fetching.
 */

import { useQuery } from "@tanstack/react-query";
import { barangayApi } from "../services/barangayApi";

export const barangayQueryKeys = {
  all: ["barangay"] as const,
  hazardMap: () => [...barangayQueryKeys.all, "hazardMap"] as const,
  evacuationCenters: () =>
    [...barangayQueryKeys.all, "evacuationCenters"] as const,
  detail: (key: string) => [...barangayQueryKeys.all, "detail", key] as const,
};

/**
 * Fetch the live GIS hazard map with per-barangay risk scores.
 * Refreshes every 5 minutes while the tab is active.
 */
export function useHazardMap() {
  return useQuery({
    queryKey: barangayQueryKeys.hazardMap(),
    queryFn: () => barangayApi.getHazardMap(),
    staleTime: 60_000,
    refetchInterval: 5 * 60_000,
    refetchIntervalInBackground: false,
  });
}

/**
 * Fetch all evacuation centers with capacity/occupancy data.
 */
export function useEvacuationCenters() {
  return useQuery({
    queryKey: barangayQueryKeys.evacuationCenters(),
    queryFn: () => barangayApi.getEvacuationCenters(),
    staleTime: 30_000,
  });
}

/**
 * Fetch detailed GIS data for a single barangay (on-demand).
 */
export function useBarangayDetail(key: string | null) {
  return useQuery({
    queryKey: barangayQueryKeys.detail(key ?? ""),
    queryFn: () => barangayApi.getBarangayDetail(key!),
    enabled: !!key,
    staleTime: 60_000,
  });
}
