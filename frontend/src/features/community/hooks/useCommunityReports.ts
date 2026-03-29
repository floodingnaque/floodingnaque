/**
 * useCommunityReports Hooks
 *
 * TanStack Query hooks for community flood report data.
 * Provides queries for listing/fetching reports and mutations
 * for submitting, voting, flagging, and verifying.
 *
 * Real-time: Uses BroadcastChannel to sync report changes across
 * browser tabs instantly. SSE broadcast from the backend handles
 * cross-user propagation; connected clients pick it up via polling.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { toast } from "sonner";
import {
  communityApi,
  type ReportListParams,
  type ReportListResponse,
  type ReportStatsParams,
} from "../services/communityApi";

// ---------------------------------------------------------------------------
// Cross-tab real-time sync via BroadcastChannel
// ---------------------------------------------------------------------------

const CHANNEL_NAME = "community-reports-sync";

function notifyCrossTabs() {
  try {
    const ch = new BroadcastChannel(CHANNEL_NAME);
    ch.postMessage({ type: "report-updated", ts: Date.now() });
    ch.close();
  } catch {
    // BroadcastChannel not supported - graceful no-op
  }
}

/**
 * Listens for cross-tab report changes and invalidates community queries.
 * Mount once in any component that displays community report data.
 */
export function useReportRealtimeSync() {
  const qc = useQueryClient();
  useEffect(() => {
    let ch: BroadcastChannel | null = null;
    try {
      ch = new BroadcastChannel(CHANNEL_NAME);
      ch.onmessage = () => {
        qc.invalidateQueries({ queryKey: communityKeys.all });
      };
    } catch {
      // BroadcastChannel not supported
    }
    return () => ch?.close();
  }, [qc]);
}

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
    refetchInterval: (query) =>
      query.state.status === "error" ? false : 30_000,
  });
}

/**
 * Fetch aggregate report stats. Auto-refreshes every 2 minutes.
 */
export function useReportStats(params?: ReportStatsParams) {
  return useQuery({
    queryKey: communityKeys.stats(params),
    queryFn: () => communityApi.getStats(params),
    refetchInterval: (query) =>
      query.state.status === "error" ? false : 30_000,
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
      qc.invalidateQueries({ queryKey: communityKeys.all });
      notifyCrossTabs();
    },
    onError: () => toast.error("Failed to submit report"),
  });
}

/**
 * Vote on a report (confirm / dispute).
 * Uses optimistic cache updates to avoid marker re-mount flicker.
 */
export function useVoteReport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, vote }: { id: number; vote: "confirm" | "dispute" }) =>
      communityApi.voteReport(id, vote),
    onMutate: async ({ id, vote }) => {
      // Cancel any in-flight refetches so they don't overwrite our optimistic update
      await qc.cancelQueries({ queryKey: communityKeys.all });

      // Snapshot current cache entries for rollback
      const previousLists = qc.getQueriesData<ReportListResponse>({
        queryKey: communityKeys.lists(),
      });

      // Optimistically update every cached list that contains this report
      qc.setQueriesData<ReportListResponse>(
        { queryKey: communityKeys.lists() },
        (old) => {
          if (!old) return old;
          return {
            ...old,
            reports: old.reports.map((r) =>
              r.id === id
                ? {
                    ...r,
                    confirmation_count:
                      r.confirmation_count + (vote === "confirm" ? 1 : 0),
                    dispute_count:
                      r.dispute_count + (vote === "dispute" ? 1 : 0),
                  }
                : r,
            ),
          };
        },
      );

      return { previousLists };
    },
    onError: (_err, _vars, context) => {
      // Rollback on failure
      if (context?.previousLists) {
        for (const [key, data] of context.previousLists) {
          if (data) qc.setQueryData(key, data);
        }
      }
      toast.error("Failed to submit vote");
    },
    onSuccess: () => {
      notifyCrossTabs();
    },
  });
}

/**
 * Flag a report for abuse.
 * Does NOT refetch or hide the report — operators/admins are notified instead.
 */
export function useFlagReport() {
  return useMutation({
    mutationFn: (id: number) => communityApi.flagReport(id),
    onSuccess: () => {
      toast.success("Report flagged — operators will review it");
    },
    onError: () => toast.error("Failed to flag report"),
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
      qc.invalidateQueries({ queryKey: communityKeys.all });
      notifyCrossTabs();
    },
    onError: () => toast.error("Failed to verify report"),
  });
}
