/**
 * Evacuation TanStack Query Hooks
 *
 * Provides cached, auto-refetching hooks for evacuation center data,
 * nearest-center lookups, route generation, and admin mutations.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import {
  evacuationApi,
  type CenterListParams,
} from "../services/evacuationApi";

// ---------------------------------------------------------------------------
// Query Key Factory
// ---------------------------------------------------------------------------

export const evacuationKeys = {
  all: ["evacuation"] as const,
  centers: (params?: CenterListParams) =>
    [...evacuationKeys.all, "centers", params ?? {}] as const,
  nearest: (lat: number, lon: number, limit?: number) =>
    [...evacuationKeys.all, "nearest", { lat, lon, limit }] as const,
  route: (lat: number, lon: number, centerId: number) =>
    [...evacuationKeys.all, "route", { lat, lon, centerId }] as const,
};

// ---------------------------------------------------------------------------
// Queries
// ---------------------------------------------------------------------------

/**
 * Fetch evacuation centers (staleTime: 60 s, refetch every 2 min)
 */
export function useEvacuationCenters(params?: CenterListParams) {
  return useQuery({
    queryKey: evacuationKeys.centers(params),
    queryFn: ({ signal }) => evacuationApi.getCenters(params, { signal }),
    staleTime: 60_000,
    refetchInterval: 120_000,
  });
}

/**
 * Find nearest evacuation centers to a location
 */
export function useNearestCenters(
  lat: number | undefined,
  lon: number | undefined,
  limit = 3,
) {
  return useQuery({
    queryKey: evacuationKeys.nearest(lat ?? 0, lon ?? 0, limit),
    queryFn: ({ signal }) =>
      evacuationApi.getNearestCenters(lat!, lon!, limit, { signal }),
    enabled: lat !== undefined && lon !== undefined,
    staleTime: 30_000,
  });
}

/**
 * Get a safe evacuation route from origin to center
 */
export function useEvacuationRoute(
  originLat: number | undefined,
  originLon: number | undefined,
  centerId: number | undefined,
) {
  return useQuery({
    queryKey: evacuationKeys.route(
      originLat ?? 0,
      originLon ?? 0,
      centerId ?? 0,
    ),
    queryFn: ({ signal }) =>
      evacuationApi.getRoute(originLat!, originLon!, centerId!, { signal }),
    enabled:
      originLat !== undefined &&
      originLon !== undefined &&
      centerId !== undefined,
    staleTime: 60_000,
  });
}

// ---------------------------------------------------------------------------
// Mutations
// ---------------------------------------------------------------------------

/**
 * Update evacuation center current occupancy (LGU/Admin)
 */
export function useUpdateCapacity() {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: (payload: { center_id: number; capacity_current: number }) =>
      evacuationApi.updateCapacity(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: evacuationKeys.all });
      toast.success("Capacity updated");
    },
    onError: () => {
      toast.error("Failed to update capacity");
    },
  });
}

/**
 * Trigger an SMS evacuation alert (Admin)
 */
export function useTriggerAlert() {
  return useMutation({
    mutationFn: (payload: {
      center_id: number;
      message: string;
      phone_numbers?: string[];
    }) => evacuationApi.triggerAlert(payload),
    onSuccess: (data) => {
      toast.success(`Alert sent to ${data.sent} recipient(s)`);
    },
    onError: () => {
      toast.error("Failed to send evacuation alert");
    },
  });
}
