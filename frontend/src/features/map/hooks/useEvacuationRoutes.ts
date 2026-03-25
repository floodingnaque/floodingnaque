/**
 * useEvacuationRoutes Hook
 *
 * Fetches OSRM-based road-following routes for all barangay
 * evacuation paths. Routes between fixed points (barangay centroids
 * → evacuation centers) are cached for 1 hour since they rarely change.
 */

import { BARANGAYS } from "@/config/paranaque";
import { useQuery } from "@tanstack/react-query";
import {
  fetchMultipleRoutes,
  type OSRMRoute,
} from "../services/routingService";

export const evacuationRouteKeys = {
  all: ["evacuation-routes"] as const,
  osrm: () => [...evacuationRouteKeys.all, "osrm"] as const,
};

export interface BarangayRoute {
  key: string;
  name: string;
  evacuationCenter: string;
  floodRisk: "low" | "moderate" | "high";
  route: OSRMRoute;
}

/**
 * Fetch OSRM road-following routes for all 16 barangay evacuation paths.
 * Caches aggressively (1 hour) since these connect fixed locations.
 */
export function useEvacuationRoutes(enabled = true) {
  return useQuery<BarangayRoute[]>({
    queryKey: evacuationRouteKeys.osrm(),
    queryFn: async () => {
      const pairs = BARANGAYS.filter((b) => b.evacuationCenter).map((b) => ({
        key: b.key,
        originLat: b.lat,
        originLon: b.lon,
        destLat: b.evacLat,
        destLon: b.evacLon,
      }));

      const routeMap = await fetchMultipleRoutes(pairs);

      const results: BarangayRoute[] = [];
      for (const b of BARANGAYS) {
        const route = routeMap.get(b.key);
        if (route) {
          results.push({
            key: b.key,
            name: b.name,
            evacuationCenter: b.evacuationCenter,
            floodRisk: b.floodRisk,
            route,
          });
        }
      }
      return results;
    },
    enabled,
    staleTime: 60 * 60 * 1000, // 1 hour — fixed-point routes
    gcTime: 2 * 60 * 60 * 1000, // keep in cache 2 hours
    retry: 2,
    refetchOnWindowFocus: false,
  });
}
