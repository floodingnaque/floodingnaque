/**
 * useRiverLevel Hook
 *
 * Fetches river/water level readings from the aggregation API.
 * If no data is available, returns empty state gracefully.
 */

import { API_ENDPOINTS } from "@/config/api.config";
import api from "@/lib/api-client";
import { useQuery } from "@tanstack/react-query";
import type { RiverReading } from "../types";

interface RiverReadingsResponse {
  readings: RiverReading[];
}

export const riverKeys = {
  all: ["river"] as const,
  level: (stationId?: string) =>
    [...riverKeys.all, "level", stationId] as const,
};

export function useRiverLevel(stationId?: string) {
  return useQuery({
    queryKey: riverKeys.level(stationId),
    queryFn: async () => {
      const params = stationId ? { station_id: stationId } : {};
      const response = await api.get<RiverReadingsResponse>(
        API_ENDPOINTS.aggregation.riverReadings,
        { params },
      );
      return response.readings ?? [];
    },
    staleTime: 60_000,
    refetchInterval: 2 * 60_000,
  });
}
