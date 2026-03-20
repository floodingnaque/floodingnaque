/**
 * Sensor Hooks
 *
 * TanStack Query hooks for sensor data operations.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { sensorApi } from "../services/sensorApi";
import type { SensorSubmitPayload } from "../types";

export const sensorQueryKeys = {
  all: ["sensor"] as const,
  hourly: (days?: number) => [...sensorQueryKeys.all, "hourly", days] as const,
};

/** Mutation to submit a new weather observation */
export function useSensorSubmit() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: SensorSubmitPayload) => sensorApi.submit(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: sensorQueryKeys.all });
    },
  });
}

/** Query for recent hourly weather data (last N days, default 1) */
export function useRecentReadings(days = 1) {
  return useQuery({
    queryKey: sensorQueryKeys.hourly(days),
    queryFn: () => sensorApi.getHourly(days),
    staleTime: 60_000,
    refetchInterval: 5 * 60_000,
  });
}
