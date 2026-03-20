/**
 * Community Reports API Service
 *
 * Provides API methods for crowdsourced flood report functionality
 * including submission, voting, flagging, and admin verification.
 */

import { API_ENDPOINTS } from "@/config/api.config";
import { api } from "@/lib/api-client";
import type { CommunityReport, ReportVote } from "@/types";

/**
 * Query parameters for listing community reports
 */
export interface ReportListParams {
  barangay?: string;
  hours?: number;
  status?: string;
  verified?: boolean;
  limit?: number;
  page?: number;
}

/**
 * Paginated list response for community reports
 */
export interface ReportListResponse {
  success: boolean;
  reports: CommunityReport[];
  total: number;
  pages: number;
}

/**
 * Stats response from /stats endpoint
 */
export interface ReportStatsResponse {
  success: boolean;
  stats: {
    total: number;
    verified: number;
    pending: number;
    critical: number;
  };
}

/**
 * Params for stats query (mirrors filter params)
 */
export interface ReportStatsParams {
  hours?: number;
  barangay?: string;
}

/**
 * Single report API response wrapper
 */
interface ReportResponse {
  success: boolean;
  report: CommunityReport;
}

/**
 * Community Reports API methods
 */
export const communityApi = {
  /**
   * Get aggregate report stats (total, verified, pending, critical)
   */
  getStats: async (
    params?: ReportStatsParams,
  ): Promise<ReportStatsResponse> => {
    const queryParams = new URLSearchParams();
    if (params?.hours) queryParams.set("hours", params.hours.toString());
    if (params?.barangay) queryParams.set("barangay", params.barangay);
    const qs = queryParams.toString();
    const url = qs
      ? `${API_ENDPOINTS.communityReports.stats}?${qs}`
      : API_ENDPOINTS.communityReports.stats;
    return api.get<ReportStatsResponse>(url);
  },

  /**
   * Submit a new flood report with optional photo
   *
   * @param formData - Multipart form data with report fields + optional photo
   * @returns The created community report
   */
  submitReport: async (formData: FormData): Promise<CommunityReport> => {
    const response = await api.post<ReportResponse>(
      API_ENDPOINTS.communityReports.submit,
      formData,
      { headers: { "Content-Type": "multipart/form-data" } },
    );
    return response.report;
  },

  /**
   * Get paginated list of community reports with optional filters
   */
  getReports: async (
    params?: ReportListParams,
  ): Promise<ReportListResponse> => {
    const queryParams = new URLSearchParams();

    if (params?.barangay) queryParams.set("barangay", params.barangay);
    if (params?.hours) queryParams.set("hours", params.hours.toString());
    if (params?.status) queryParams.set("status", params.status);
    if (params?.verified !== undefined)
      queryParams.set("verified", params.verified.toString());
    if (params?.limit) queryParams.set("limit", params.limit.toString());
    if (params?.page) queryParams.set("page", params.page.toString());

    const qs = queryParams.toString();
    const url = qs
      ? `${API_ENDPOINTS.communityReports.list}?${qs}`
      : API_ENDPOINTS.communityReports.list;

    return api.get<ReportListResponse>(url);
  },

  /**
   * Get a single community report by ID
   */
  getReport: async (id: number): Promise<CommunityReport> => {
    const response = await api.get<ReportResponse>(
      `${API_ENDPOINTS.communityReports.detail}/${id}`,
    );
    return response.report;
  },

  /**
   * Vote on a community report (confirm or dispute)
   */
  voteReport: async (
    id: number,
    vote: ReportVote,
  ): Promise<CommunityReport> => {
    const response = await api.post<ReportResponse>(
      `${API_ENDPOINTS.communityReports.confirm}/${id}/confirm`,
      { vote },
    );
    return response.report;
  },

  /**
   * Flag a report for abuse
   */
  flagReport: async (id: number): Promise<void> => {
    await api.post<{ success: boolean }>(
      `${API_ENDPOINTS.communityReports.flag}/${id}/flag`,
    );
  },

  /**
   * Admin: verify (accept/reject) a community report
   */
  verifyReport: async (
    id: number,
    status: "accepted" | "rejected",
  ): Promise<CommunityReport> => {
    const response = await api.patch<ReportResponse>(
      `${API_ENDPOINTS.communityReports.verify}/${id}/verify`,
      { status },
    );
    return response.report;
  },
};
