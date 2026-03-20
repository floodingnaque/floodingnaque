/**
 * Community Engagement Types
 *
 * Types for crowdsourced flood reporting and evacuation assistance features.
 */

// ---------------------------------------------------------------------------
// Community Reports
// ---------------------------------------------------------------------------

export type ReportStatus = "pending" | "accepted" | "rejected";

export type ReportVote = "confirm" | "dispute";

export interface FloodHeightOption {
  label: string;
  value: number | null;
  description: string;
}

/**
 * Predefined flood height options for the report submission form.
 * Values represent approximate midpoint flood height in centimeters.
 */
export const FLOOD_HEIGHT_OPTIONS: FloodHeightOption[] = [
  { label: "Gutter", value: 8, description: "< 15 cm" },
  { label: "Ankle", value: 22, description: "15–30 cm" },
  { label: "Knee", value: 45, description: "30–60 cm" },
  { label: "Waist", value: 75, description: "> 60 cm" },
  { label: "Unknown", value: null, description: "Not sure" },
];

export interface CommunityReport {
  id: number;
  user_id: number | null;
  latitude: number;
  longitude: number;
  barangay: string | null;
  flood_height_cm: number | null;
  description: string | null;
  specific_location: string | null;
  contact_number: string | null;
  photo_url: string | null;
  risk_label: string;
  credibility_score: number | null;
  verified: boolean;
  status: ReportStatus;
  confirmation_count: number;
  dispute_count: number;
  abuse_flag_count: number;
  verified_by: number | null;
  verified_at: string | null;
  created_at: string;
  updated_at: string | null;
}

// ---------------------------------------------------------------------------
// Evacuation
// ---------------------------------------------------------------------------

export interface EvacuationCenter {
  id: number;
  name: string;
  barangay: string;
  address: string | null;
  latitude: number;
  longitude: number;
  capacity_total: number;
  capacity_current: number;
  contact_number: string | null;
  is_active: boolean;
  updated_at: string | null;
  /** Computed: occupancy percentage (0–100) */
  occupancy_pct: number;
  /** Computed: remaining available slots */
  available_slots: number;
}

export interface NearestCenterResult {
  center: EvacuationCenter;
  distance_km: number;
  available_slots: number;
  occupancy_pct: number;
  google_maps_url: string;
}

export interface EvacuationRoute {
  geometry: GeoJSON.LineString;
  distance_m: number;
  duration_s: number;
  flood_segments_avoided: number;
  google_maps_url: string;
}

export interface CapacityUpdateEvent {
  center_id: number;
  capacity_current: number;
  capacity_total: number;
  near_full: boolean;
}
