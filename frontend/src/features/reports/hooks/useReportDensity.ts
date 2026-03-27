/**
 * useReportDensity – TanStack Query hook for community report density GeoJSON.
 */

import { API_ENDPOINTS } from "@/config/api.config";
import { api } from "@/lib/api-client";
import { useQuery } from "@tanstack/react-query";

export interface DensityFeature {
  type: "Feature";
  geometry: { type: "Point"; coordinates: [number, number] };
  properties: {
    count: number;
    weight: number;
    avg_credibility: number;
    dominant_risk: string;
    max_flood_height_cm: number;
  };
}

export interface DensityResponse {
  success: boolean;
  type: "FeatureCollection";
  features: DensityFeature[];
  meta: {
    hours: number;
    min_credibility: number;
    total_reports: number;
    grid_cells: number;
    grid_size_degrees: number;
  };
}

export const densityKeys = {
  all: ["report-density"] as const,
  byParams: (hours: number, minCred: number) =>
    [...densityKeys.all, hours, minCred] as const,
};

export function useReportDensity(hours = 168, minCredibility = 0) {
  return useQuery<DensityResponse>({
    queryKey: densityKeys.byParams(hours, minCredibility),
    queryFn: ({ signal }) =>
      api.get<DensityResponse>(
        `${API_ENDPOINTS.communityReports.density}?hours=${hours}&min_credibility=${minCredibility}`,
        { signal },
      ),
    staleTime: 2 * 60_000,
    refetchInterval: 10 * 60_000,
  });
}
