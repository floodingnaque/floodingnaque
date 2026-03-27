/**
 * Simulation API service
 */

import { API_ENDPOINTS } from "@/config/api.config";
import { api } from "@/lib/api-client";
import type { AxiosRequestConfig } from "axios";
import type { SimulationParams, SimulationResult } from "../types";

export const simulationApi = {
  /**
   * Run a what-if flood prediction simulation.
   * Ephemeral — does not persist to the database.
   */
  simulate: async (
    params: SimulationParams,
    config?: AxiosRequestConfig,
  ): Promise<SimulationResult> => {
    return api.post<SimulationResult>(
      API_ENDPOINTS.predict.simulate,
      params,
      config,
    );
  },
};
