/**
 * Resident API Service
 *
 * API methods for resident-specific features: household profile,
 * community report submission, and personal report history.
 */

import { API_ENDPOINTS } from "@/config/api.config";
import { api } from "@/lib/api-client";
import type { ApiResponse, CommunityReport } from "@/types";
import type { AxiosRequestConfig } from "axios";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface HouseholdProfile {
  id: number;
  user_id: number;
  date_of_birth: string | null;
  sex: string | null;
  civil_status: string | null;
  contact_number: string | null;
  alt_contact_number: string | null;
  alt_contact_name: string | null;
  alt_contact_relationship: string | null;
  is_pwd: boolean;
  is_senior_citizen: boolean;
  household_members: number;
  children_count: number;
  senior_count: number;
  pwd_count: number;
  barangay: string | null;
  purok: string | null;
  street_address: string | null;
  nearest_landmark: string | null;
  home_type: string | null;
  floor_level: string | null;
  has_flood_experience: boolean;
  most_recent_flood_year: number | null;
  sms_alerts: boolean;
  email_alerts: boolean;
  push_notifications: boolean;
  preferred_language: string;
  data_privacy_consent: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface HouseholdProfileUpdate {
  contact_number?: string;
  alt_contact_number?: string;
  alt_contact_name?: string;
  alt_contact_relationship?: string;
  is_pwd?: boolean;
  is_senior_citizen?: boolean;
  household_members?: number;
  children_count?: number;
  senior_count?: number;
  pwd_count?: number;
  barangay?: string;
  purok?: string;
  street_address?: string;
  nearest_landmark?: string;
  home_type?: string;
  floor_level?: string;
  has_flood_experience?: boolean;
  most_recent_flood_year?: number;
  sms_alerts?: boolean;
  email_alerts?: boolean;
  push_notifications?: boolean;
  preferred_language?: string;
}

export interface MyReportsResponse {
  success: boolean;
  reports: CommunityReport[];
  total: number;
  pages: number;
}

// ---------------------------------------------------------------------------
// API
// ---------------------------------------------------------------------------

export const residentApi = {
  /** Get the current user's household/resident profile */
  getHouseholdProfile: async (
    config?: AxiosRequestConfig,
  ): Promise<HouseholdProfile> => {
    const res = await api.get<ApiResponse<HouseholdProfile>>(
      `${API_ENDPOINTS.auth.me}/profile`,
      config,
    );
    return res.data;
  },

  /** Update household profile fields */
  updateHouseholdProfile: async (
    data: HouseholdProfileUpdate,
    config?: AxiosRequestConfig,
  ): Promise<HouseholdProfile> => {
    const res = await api.patch<ApiResponse<HouseholdProfile>>(
      `${API_ENDPOINTS.auth.me}/profile`,
      data,
      config,
    );
    return res.data;
  },

  /** Get the current user's submitted community reports */
  getMyReports: async (
    params?: { limit?: number; page?: number },
    config?: AxiosRequestConfig,
  ): Promise<MyReportsResponse> => {
    const qp = new URLSearchParams();
    if (params?.limit) qp.set("limit", params.limit.toString());
    if (params?.page) qp.set("page", params.page.toString());
    qp.set("mine", "true");
    const qs = qp.toString();
    const url = qs
      ? `${API_ENDPOINTS.communityReports.list}?${qs}`
      : API_ENDPOINTS.communityReports.list;
    return api.get<MyReportsResponse>(url, config);
  },
};
