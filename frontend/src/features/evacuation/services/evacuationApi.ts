/**
 * Evacuation API Service
 *
 * Provides API methods for evacuation center management,
 * nearest-center lookups, safe-route generation, and SMS alerts.
 */

import { API_ENDPOINTS } from "@/config/api.config";
import { api } from "@/lib/api-client";
import type {
  EvacuationCenter,
  EvacuationRoute,
  NearestCenterResult,
} from "@/types";
import type { AxiosRequestConfig } from "axios";

// ---------------------------------------------------------------------------
// Request / Response Shapes
// ---------------------------------------------------------------------------

export interface CenterListParams {
  barangay?: string;
  active_only?: boolean;
}

interface CenterListResponse {
  success: boolean;
  centers: EvacuationCenter[];
}

interface NearestResponse {
  success: boolean;
  results: NearestCenterResult[];
}

interface RouteResponse {
  success: boolean;
  route: EvacuationRoute;
}

interface AlertPayload {
  center_id: number;
  message: string;
  phone_numbers?: string[];
}

interface AlertResponse {
  success: boolean;
  sent: number;
  failed: number;
}

interface CapacityPayload {
  center_id: number;
  capacity_current: number;
}

interface CapacityResponse {
  success: boolean;
  center: EvacuationCenter;
}

// ---------------------------------------------------------------------------
// API Methods
// ---------------------------------------------------------------------------

export const evacuationApi = {
  /**
   * Get a list of evacuation centers with optional barangay filter
   */
  getCenters: async (
    params?: CenterListParams,
    config?: AxiosRequestConfig,
  ): Promise<EvacuationCenter[]> => {
    const queryParams = new URLSearchParams();

    if (params?.barangay) queryParams.set("barangay", params.barangay);
    if (params?.active_only !== undefined)
      queryParams.set("active_only", params.active_only.toString());

    const qs = queryParams.toString();
    const url = qs
      ? `${API_ENDPOINTS.evacuation.centers}?${qs}`
      : API_ENDPOINTS.evacuation.centers;

    const response = await api.get<CenterListResponse>(url, config);
    return response.centers;
  },

  /**
   * Find the nearest evacuation centers to a given location
   *
   * @param lat - User latitude
   * @param lon - User longitude
   * @param limit - Max results to return (default: 3)
   */
  getNearestCenters: async (
    lat: number,
    lon: number,
    limit = 3,
    config?: AxiosRequestConfig,
  ): Promise<NearestCenterResult[]> => {
    const url = `${API_ENDPOINTS.evacuation.nearest}?lat=${lat}&lon=${lon}&limit=${limit}`;
    const response = await api.get<NearestResponse>(url, config);
    return response.results;
  },

  /**
   * Get a safe evacuation route from origin to a center
   *
   * @param originLat - Start latitude
   * @param originLon - Start longitude
   * @param centerId - Target evacuation center ID
   */
  getRoute: async (
    originLat: number,
    originLon: number,
    centerId: number,
    config?: AxiosRequestConfig,
  ): Promise<EvacuationRoute> => {
    const url = `${API_ENDPOINTS.evacuation.route}?lat=${originLat}&lon=${originLon}&center_id=${centerId}`;
    const response = await api.get<RouteResponse>(url, config);
    return response.route;
  },

  /**
   * Update the current occupancy of an evacuation center (LGU/Admin)
   */
  updateCapacity: async (
    payload: CapacityPayload,
  ): Promise<EvacuationCenter> => {
    const response = await api.patch<CapacityResponse>(
      API_ENDPOINTS.evacuation.centers,
      payload,
    );
    return response.center;
  },

  /**
   * Trigger an SMS alert for an evacuation center (Admin)
   */
  triggerAlert: async (payload: AlertPayload): Promise<AlertResponse> => {
    return api.post<AlertResponse>(API_ENDPOINTS.evacuation.alert, payload);
  },
};
