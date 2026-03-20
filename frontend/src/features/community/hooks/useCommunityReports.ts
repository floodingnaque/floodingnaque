/**
 * useCommunityReports Hooks
 *
 * TanStack Query hooks for community flood report data.
 * Provides queries for listing/fetching reports and mutations
 * for submitting, voting, flagging, and verifying.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  communityApi,
  type ReportListParams,
  type ReportStatsParams,
} from "../services/communityApi";

/**
 * Query key factory for community reports
 */
export const communityKeys = {
  all: ["community-reports"] as const,
  lists: () => [...communityKeys.all, "list"] as const,
  list: (params?: ReportListParams) =>
    [...communityKeys.lists(), params] as const,
  detail: (id: number) => [...communityKeys.all, "detail", id] as const,
  stats: (params?: ReportStatsParams) =>
    [...communityKeys.all, "stats", params] as const,
};

/**
 * Fetch a paginated / filtered list of community reports.
 * Auto-refreshes every 2 minutes.
 */
export function useCommunityReports(params?: ReportListParams) {
  return useQuery({
    queryKey: communityKeys.list(params),
    queryFn: () => communityApi.getReports(params),
    refetchInterval: 120_000,
  });
}

/**
 * Fetch aggregate report stats. Auto-refreshes every 2 minutes.
 */
export function useReportStats(params?: ReportStatsParams) {
  return useQuery({
    queryKey: communityKeys.stats(params),
    queryFn: () => communityApi.getStats(params),
    refetchInterval: 120_000,
  });
}

/**
 * Fetch a single community report by ID.
 */
export function useCommunityReport(id: number) {
  return useQuery({
    queryKey: communityKeys.detail(id),
    queryFn: () => communityApi.getReport(id),
    enabled: id > 0,
  });
}

/**
 * Submit a new flood report (multipart FormData with optional photo).
 * Invalidates the reports list on success.
 */
export function useSubmitReport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (formData: FormData) => communityApi.submitReport(formData),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: communityKeys.lists() });
      qc.invalidateQueries({ queryKey: communityKeys.all });
    },
  });
}

/**
 * Vote on a report (confirm / dispute).
 */
export function useVoteReport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, vote }: { id: number; vote: "confirm" | "dispute" }) =>
      communityApi.voteReport(id, vote),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: communityKeys.lists() });
      qc.invalidateQueries({ queryKey: communityKeys.all });
    },
  });
}

/**
 * Flag a report for abuse.
 */
export function useFlagReport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => communityApi.flagReport(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: communityKeys.lists() });
      qc.invalidateQueries({ queryKey: communityKeys.all });
    },
  });
}

/**
 * Admin: verify (accept/reject) a community report.
 */
export function useVerifyReport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      status,
    }: {
      id: number;
      status: "accepted" | "rejected";
    }) => communityApi.verifyReport(id, status),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: communityKeys.lists() });
      qc.invalidateQueries({ queryKey: communityKeys.all });
    },
  });
}
