/**
 * useAlerts Hooks
 *
 * React Query hooks for fetching and managing alerts data.
 * Provides queries for alerts list, recent alerts, and history,
 * as well as mutations for acknowledging alerts.
 */

import type {
  Alert,
  AlertHistory,
  AlertParams,
  ApiError,
  PaginatedResponse,
} from "@/types";
import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseQueryOptions,
} from "@tanstack/react-query";
import type { SmsSimulationResponse } from "../services/alertsApi";
import { alertsApi } from "../services/alertsApi";

/**
 * Query keys for alerts
 */
export const alertKeys = {
  all: ["alerts"] as const,
  lists: () => [...alertKeys.all, "list"] as const,
  list: (params?: AlertParams) => [...alertKeys.lists(), params] as const,
  recent: (limit?: number) => [...alertKeys.all, "recent", limit] as const,
  history: () => [...alertKeys.all, "history"] as const,
};

/**
 * useAlerts hook for fetching paginated alerts
 *
 * @param params - Optional query parameters for filtering
 * @param options - Optional React Query options
 * @returns Query result with paginated alerts
 *
 * @example
 * const { data, isLoading } = useAlerts({ page: 1, limit: 10 });
 */
export function useAlerts(
  params?: AlertParams,
  options?: Omit<
    UseQueryOptions<PaginatedResponse<Alert>, ApiError>,
    "queryKey" | "queryFn"
  >,
) {
  return useQuery({
    queryKey: alertKeys.list(params),
    queryFn: ({ signal }) => alertsApi.getAlerts(params, { signal }),
    ...options,
  });
}

/**
 * useRecentAlerts hook for fetching recent alerts
 *
 * @param limit - Maximum number of alerts to return (default: 10)
 * @param options - Optional React Query options
 * @returns Query result with recent alerts array
 *
 * @example
 * const { data: recentAlerts } = useRecentAlerts(5);
 */
export function useRecentAlerts(
  limit: number = 10,
  options?: Omit<UseQueryOptions<Alert[], ApiError>, "queryKey" | "queryFn">,
) {
  return useQuery({
    queryKey: alertKeys.recent(limit),
    queryFn: ({ signal }) => alertsApi.getRecentAlerts(limit, { signal }),
    ...options,
  });
}

/**
 * useAlertHistory hook for fetching alert history with summary
 *
 * @param options - Optional React Query options
 * @returns Query result with alert history and summary
 *
 * @example
 * const { data: history } = useAlertHistory();
 * console.log(history?.summary.total);
 */
export function useAlertHistory(
  options?: Omit<
    UseQueryOptions<AlertHistory, ApiError>,
    "queryKey" | "queryFn"
  >,
) {
  return useQuery({
    queryKey: alertKeys.history(),
    queryFn: ({ signal }) => alertsApi.getAlertHistory({ signal }),
    ...options,
  });
}

/**
 * Options for acknowledge mutations
 */
interface AcknowledgeMutationOptions {
  /** Callback when acknowledgment succeeds */
  onSuccess?: () => void;
  /** Callback when acknowledgment fails */
  onError?: (error: ApiError) => void;
}

/**
 * useAcknowledgeAlert hook for acknowledging a single alert
 *
 * @param options - Optional callbacks for success and error handling
 * @returns Mutation object with acknowledge function
 *
 * @example
 * const { mutate: acknowledge, isPending } = useAcknowledgeAlert();
 * acknowledge(123);
 */
export function useAcknowledgeAlert(options?: AcknowledgeMutationOptions) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (alertId: number) => alertsApi.acknowledgeAlert(alertId),
    // Optimistic update: mark alert as acknowledged immediately in cache
    onMutate: async (alertId: number) => {
      // Cancel outgoing refetches so they don't overwrite our optimistic update
      await queryClient.cancelQueries({ queryKey: alertKeys.all });

      // Snapshot all alert queries so we can rollback on error
      const previousQueries = queryClient.getQueriesData<
        PaginatedResponse<Alert> | Alert[]
      >({ queryKey: alertKeys.all });

      // Optimistically update any cached alert data
      queryClient.setQueriesData<PaginatedResponse<Alert>>(
        { queryKey: alertKeys.lists() },
        (old) => {
          if (!old) return old;
          return {
            ...old,
            data: old.data.map((a) =>
              a.id === alertId ? { ...a, acknowledged: true } : a,
            ),
          };
        },
      );

      queryClient.setQueriesData<Alert[]>(
        { queryKey: alertKeys.recent() },
        (old) =>
          old?.map((a) =>
            a.id === alertId ? { ...a, acknowledged: true } : a,
          ),
      );

      return { previousQueries };
    },
    onError: (_error, _alertId, context) => {
      // Rollback to the previous cache state on failure
      if (context?.previousQueries) {
        for (const [queryKey, data] of context.previousQueries) {
          queryClient.setQueryData(queryKey, data);
        }
      }
      options?.onError?.(_error as unknown as ApiError);
    },
    onSettled: () => {
      // Always refetch after error or success to ensure server truth
      queryClient.invalidateQueries({ queryKey: alertKeys.all });
    },
    onSuccess: () => {
      options?.onSuccess?.();
    },
  });
}

/**
 * useAcknowledgeAll hook for acknowledging all pending alerts
 *
 * @param options - Optional callbacks for success and error handling
 * @returns Mutation object with acknowledgeAll function
 *
 * @example
 * const { mutate: acknowledgeAll, isPending } = useAcknowledgeAll();
 * acknowledgeAll();
 */
export function useAcknowledgeAll(options?: AcknowledgeMutationOptions) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => alertsApi.acknowledgeAll(),
    // Optimistic update: mark ALL alerts as acknowledged immediately
    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey: alertKeys.all });

      const previousQueries = queryClient.getQueriesData<
        PaginatedResponse<Alert> | Alert[]
      >({ queryKey: alertKeys.all });

      queryClient.setQueriesData<PaginatedResponse<Alert>>(
        { queryKey: alertKeys.lists() },
        (old) => {
          if (!old) return old;
          return {
            ...old,
            data: old.data.map((a) => ({ ...a, acknowledged: true })),
          };
        },
      );

      queryClient.setQueriesData<Alert[]>(
        { queryKey: alertKeys.recent() },
        (old) => old?.map((a) => ({ ...a, acknowledged: true })),
      );

      return { previousQueries };
    },
    onError: (_error, _vars, context) => {
      if (context?.previousQueries) {
        for (const [queryKey, data] of context.previousQueries) {
          queryClient.setQueryData(queryKey, data);
        }
      }
      options?.onError?.(_error as unknown as ApiError);
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: alertKeys.all });
    },
    onSuccess: () => {
      options?.onSuccess?.();
    },
  });
}

/**
 * useSimulateSms hook for sending an SMS simulation
 *
 * @param options - Optional callbacks for success and error handling
 * @returns Mutation object with simulateSms function
 *
 * @example
 * const { mutate: simulate, isPending } = useSimulateSms();
 * simulate({ phone: '09171234567', riskLevel: 2 });
 */
export function useSimulateSms(options?: {
  onSuccess?: (data: SmsSimulationResponse) => void;
  onError?: (error: ApiError) => void;
}) {
  return useMutation({
    mutationFn: ({
      phone,
      message,
      riskLevel,
    }: {
      phone: string;
      message?: string;
      riskLevel?: number;
    }) => alertsApi.simulateSms(phone, message, riskLevel),
    onSuccess: options?.onSuccess,
    onError: options?.onError,
  });
}

export default {
  useAlerts,
  useRecentAlerts,
  useAlertHistory,
  useAcknowledgeAlert,
  useAcknowledgeAll,
  useSimulateSms,
};
