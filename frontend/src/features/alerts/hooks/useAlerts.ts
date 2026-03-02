/**
 * useAlerts Hooks
 *
 * React Query hooks for fetching and managing alerts data.
 * Provides queries for alerts list, recent alerts, and history,
 * as well as mutations for acknowledging alerts.
 */

import {
  useQuery,
  useMutation,
  useQueryClient,
  type UseQueryOptions,
} from '@tanstack/react-query';
import { alertsApi } from '../services/alertsApi';
import type { SmsSimulationResponse } from '../services/alertsApi';
import type {
  Alert,
  AlertParams,
  AlertHistory,
  PaginatedResponse,
  ApiError,
} from '@/types';

/**
 * Query keys for alerts
 */
export const alertKeys = {
  all: ['alerts'] as const,
  lists: () => [...alertKeys.all, 'list'] as const,
  list: (params?: AlertParams) => [...alertKeys.lists(), params] as const,
  recent: (limit?: number) => [...alertKeys.all, 'recent', limit] as const,
  history: () => [...alertKeys.all, 'history'] as const,
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
    'queryKey' | 'queryFn'
  >
) {
  return useQuery({
    queryKey: alertKeys.list(params),
    queryFn: () => alertsApi.getAlerts(params),
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
  options?: Omit<UseQueryOptions<Alert[], ApiError>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: alertKeys.recent(limit),
    queryFn: () => alertsApi.getRecentAlerts(limit),
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
  options?: Omit<UseQueryOptions<AlertHistory, ApiError>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: alertKeys.history(),
    queryFn: () => alertsApi.getAlertHistory(),
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
    onSuccess: () => {
      // Invalidate alerts queries to refetch fresh data
      queryClient.invalidateQueries({ queryKey: alertKeys.all });
      options?.onSuccess?.();
    },
    onError: options?.onError,
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
    onSuccess: () => {
      // Invalidate alerts queries to refetch fresh data
      queryClient.invalidateQueries({ queryKey: alertKeys.all });
      options?.onSuccess?.();
    },
    onError: options?.onError,
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
