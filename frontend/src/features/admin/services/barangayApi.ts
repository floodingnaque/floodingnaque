/**
 * Barangay API Service
 *
 * Provides API methods to fetch live GIS hazard data, evacuation center
 * status, and community report counts for the Barangay Management page.
 */

import { API_CONFIG } from "@/config/api.config";
import api from "@/lib/api-client";

const { endpoints } = API_CONFIG;

// ── Types ──

export interface HazardFeatureProperties {
  key: string;
  name: string;
  population: number;
  lat: number;
  lon: number;
  mean_elevation_m: number;
  min_elevation_m: number;
  slope_pct: number;
  nearest_waterway: string;
  distance_to_waterway_m: number;
  drainage_capacity: string;
  impervious_surface_pct: number;
  flood_history_events: number;
  hazard_score: number;
  hazard_classification: "high" | "moderate" | "low";
  hazard_color: string;
  hazard_factors: Record<string, number>;
  current_rainfall_mm: number;
}

export interface HazardFeature {
  type: "Feature";
  geometry: { type: "Polygon"; coordinates: number[][][] };
  properties: HazardFeatureProperties;
}

export interface HazardMapResponse {
  success: boolean;
  data: {
    type: "FeatureCollection";
    features: HazardFeature[];
    metadata: {
      city: string;
      barangay_count: number;
      generated_at: string;
      crs: string;
      data_sources: string[];
    };
  };
}

export interface EvacuationCenterData {
  id: number;
  name: string;
  barangay: string;
  address: string;
  latitude: number;
  longitude: number;
  capacity_total: number;
  capacity_current: number;
  contact_number: string | null;
  is_active: boolean;
  available_slots?: number;
  occupancy_pct?: number;
}

export interface EvacuationCentersResponse {
  success: boolean;
  centers: EvacuationCenterData[];
}

export interface BarangayDetailResponse {
  success: boolean;
  data: {
    key: string;
    name: string;
    population: number;
    center: { lat: number; lon: number };
    polygon: number[][];
    elevation: Record<string, number>;
    drainage: Record<string, unknown>;
    hazard: {
      hazard_score: number;
      classification: string;
      color: string;
      factors: Record<string, number>;
    };
    generated_at: string;
  };
}

// ── API Methods ──

export const barangayApi = {
  /**
   * Fetch live hazard map with risk classification per barangay.
   * The GIS backend computes composite hazard scores from elevation,
   * drainage, flood history, and optional live rainfall.
   */
  getHazardMap: async (): Promise<HazardMapResponse> => {
    return api.get(endpoints.gis.hazardMap, {
      params: { include_rainfall: true },
    });
  },

  /**
   * Fetch all evacuation centers with capacity data.
   */
  getEvacuationCenters: async (): Promise<EvacuationCentersResponse> => {
    return api.get(endpoints.evacuation.centers);
  },

  /**
   * Fetch detailed GIS data for a single barangay.
   */
  getBarangayDetail: async (key: string): Promise<BarangayDetailResponse> => {
    return api.get(`${endpoints.gis.barangayDetail}/${key}`);
  },
};
