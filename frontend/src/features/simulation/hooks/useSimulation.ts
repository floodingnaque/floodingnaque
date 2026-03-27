/**
 * useSimulation – TanStack Query hook for the simulation endpoint.
 *
 * Uses `useMutation` because simulation is a POST that the user triggers
 * on demand (slider change / preset selection), not an auto-fetching query.
 */

import { useMutation } from "@tanstack/react-query";
import { simulationApi } from "../services/simulationApi";
import type { SimulationParams, SimulationResult } from "../types";

export const simulationKeys = {
  all: ["simulation"] as const,
  run: (params: SimulationParams) =>
    [...simulationKeys.all, "run", params] as const,
};

export function useSimulation() {
  return useMutation<SimulationResult, Error, SimulationParams>({
    mutationFn: (params) => simulationApi.simulate(params),
  });
}
