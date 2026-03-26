/**
 * Operator API Service
 *
 * API calls for the LGU operator dashboard - incidents, broadcasts,
 * resident registry, and after-action reports.
 */

import { API_ENDPOINTS } from "@/config/api.config";
import { api } from "@/lib/api-client";
import type {
  AfterActionReport,
  ApiResponse,
  Incident,
  IncidentStats,
  PaginatedResponse,
  WorkflowAnalytics,
} from "@/types";

// ─── Helpers ─────────────────────────────────────────────────────────────────

/** Shape returned by backend LGU endpoints with offset-based pagination */
interface BackendPaginated<T> {
  success: boolean;
  data: T[];
  pagination: { total: number; limit: number; offset: number };
  request_id: string;
}

/** Normalise backend offset-based pagination → frontend PaginatedResponse */
function normalisePaginated<T>(raw: BackendPaginated<T>): PaginatedResponse<T> {
  const { total, limit, offset } = raw.pagination;
  const page = Math.floor(offset / limit) + 1;
  const pages = Math.max(1, Math.ceil(total / limit));
  return {
    success: raw.success,
    data: raw.data,
    total,
    page,
    limit,
    pages,
    request_id: raw.request_id,
  };
}

// ─── Incidents ───────────────────────────────────────────────────────────────

export interface CreateIncidentRequest {
  title: string;
  description?: string;
  incident_type: string;
  risk_level: number;
  barangay: string;
  location_detail?: string;
  affected_families?: number;
  source?: string;
}

export interface UpdateIncidentRequest {
  status?: string;
  confirmed_by?: string;
  broadcast_channels?: string;
  resolved_by?: string;
  affected_families?: number;
  evacuated_families?: number;
  casualties?: number;
  estimated_damage?: number;
}

export const operatorApi = {
  // Incidents
  getIncidents: async (
    params?: Record<string, unknown>,
    options?: { signal?: AbortSignal },
  ): Promise<PaginatedResponse<Incident>> => {
    const raw = await api.get<BackendPaginated<Incident>>(
      API_ENDPOINTS.lgu.incidents,
      { params, signal: options?.signal },
    );
    return normalisePaginated(raw);
  },

  getIncidentStats: (options?: { signal?: AbortSignal }) =>
    api.get<ApiResponse<IncidentStats>>(API_ENDPOINTS.lgu.incidentStats, {
      signal: options?.signal,
    }),

  getIncidentAnalytics: (options?: { signal?: AbortSignal }) =>
    api.get<ApiResponse<WorkflowAnalytics>>(
      API_ENDPOINTS.lgu.incidentAnalytics,
      { signal: options?.signal },
    ),

  createIncident: (data: CreateIncidentRequest) =>
    api.post<ApiResponse<Incident>>(API_ENDPOINTS.lgu.incidents, data),

  updateIncident: (id: number, data: UpdateIncidentRequest) =>
    api.patch<ApiResponse<Incident>>(
      `${API_ENDPOINTS.lgu.incidents}/${id}`,
      data,
    ),

  advanceIncident: (id: number) =>
    api.post<ApiResponse<Incident>>(
      `${API_ENDPOINTS.lgu.incidents}/${id}/advance`,
    ),

  // After-Action Reports
  getAARs: async (
    params?: Record<string, unknown>,
    options?: { signal?: AbortSignal },
  ): Promise<PaginatedResponse<AfterActionReport>> => {
    const raw = await api.get<BackendPaginated<AfterActionReport>>(
      API_ENDPOINTS.lgu.aar,
      { params, signal: options?.signal },
    );
    return normalisePaginated(raw);
  },

  createAAR: (data: Partial<AfterActionReport>) =>
    api.post<ApiResponse<AfterActionReport>>(API_ENDPOINTS.lgu.aar, data),

  updateAAR: (id: number, data: Partial<AfterActionReport>) =>
    api.patch<ApiResponse<AfterActionReport>>(
      `${API_ENDPOINTS.lgu.aar}/${id}`,
      data,
    ),

  // Broadcasts
  sendBroadcast: (data: {
    target_barangays: string[];
    channels: string[];
    message: string;
    priority: string;
    title?: string;
  }) =>
    api.post<ApiResponse<{ broadcast_id: number; recipients: number }>>(
      API_ENDPOINTS.lgu.broadcasts,
      data,
    ),

  getBroadcasts: async (
    params?: Record<string, unknown>,
    options?: { signal?: AbortSignal },
  ) => {
    const raw = await api.get<
      BackendPaginated<{
        id: number;
        target_barangays: string[];
        channels: string[];
        message: string;
        priority: string;
        sent_at: string;
        sent_by: string;
        recipients: number;
      }>
    >(API_ENDPOINTS.lgu.broadcasts, { params, signal: options?.signal });
    return normalisePaginated(raw);
  },

  // Residents
  getResidents: async (
    params?: Record<string, unknown>,
    options?: { signal?: AbortSignal },
  ) => {
    const raw = await api.get<{
      success: boolean;
      data: {
        id: number;
        full_name: string;
        email: string;
        phone_number: string | null;
        barangay: string | null;
        household_members: number | null;
        is_pwd: boolean;
        is_senior_citizen: boolean;
        children_count: number;
        home_type: string | null;
        floor_level: string | null;
        is_active: boolean;
        is_verified: boolean;
        last_login_at: string | null;
        created_at: string;
      }[];
      pagination: {
        page: number;
        per_page: number;
        total: number;
        total_pages: number;
      };
    }>(API_ENDPOINTS.admin.users, {
      params: { ...params, role: "user" },
      signal: options?.signal,
    });
    return {
      success: raw.success,
      data: raw.data,
      total: raw.pagination.total,
      page: raw.pagination.page,
      limit: raw.pagination.per_page,
      pages: raw.pagination.total_pages,
      request_id: "",
    } satisfies PaginatedResponse<(typeof raw.data)[number]>;
  },
};
