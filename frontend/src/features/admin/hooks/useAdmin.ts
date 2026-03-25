/**
 * Admin Hooks
 *
 * TanStack Query hooks for system health, user management,
 * system logs, and model management.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import type {
  CreateUserParams,
  LogListParams,
  UserListParams,
} from "../services/adminApi";
import { adminApi } from "../services/adminApi";

/**
 * Query keys for admin-related queries
 */
export const adminQueryKeys = {
  all: ["admin"] as const,
  health: () => [...adminQueryKeys.all, "health"] as const,
  users: (params?: UserListParams) =>
    [...adminQueryKeys.all, "users", params] as const,
  user: (id: string) => [...adminQueryKeys.all, "user", id] as const,
  logs: (params?: LogListParams) =>
    [...adminQueryKeys.all, "logs", params] as const,
  logStats: () => [...adminQueryKeys.all, "logStats"] as const,
  models: () => [...adminQueryKeys.all, "models"] as const,
  modelComparison: () => [...adminQueryKeys.all, "modelComparison"] as const,
  retrainStatus: (taskId: string) =>
    [...adminQueryKeys.all, "retrainStatus", taskId] as const,
  featureFlags: () => [...adminQueryKeys.all, "featureFlags"] as const,
  auditLogs: (params?: AuditLogListParams) =>
    [...adminQueryKeys.all, "auditLogs", params] as const,
  auditStats: () => [...adminQueryKeys.all, "auditStats"] as const,
  securityPosture: () => [...adminQueryKeys.all, "securityPosture"] as const,
  monitoring: () => [...adminQueryKeys.all, "monitoring"] as const,
  uptime: () => [...adminQueryKeys.all, "uptime"] as const,
  apiResponses: (minutes?: number) =>
    [...adminQueryKeys.all, "apiResponses", minutes] as const,
  predictionDrift: (minutes?: number) =>
    [...adminQueryKeys.all, "predictionDrift", minutes] as const,
  alertDelivery: (hours?: number) =>
    [...adminQueryKeys.all, "alertDelivery", hours] as const,
};

// ── Health ──

export function useSystemHealth(enabled = true) {
  return useQuery({
    queryKey: adminQueryKeys.health(),
    queryFn: () => adminApi.getHealth(),
    enabled,
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
    staleTime: 10_000,
  });
}

// ── User Management ──

export function useUsers(params?: UserListParams) {
  return useQuery({
    queryKey: adminQueryKeys.users(params),
    queryFn: () => adminApi.getUsers(params),
    staleTime: 15_000,
  });
}

export function useCreateUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (params: CreateUserParams) => adminApi.createUser(params),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "users"] }),
    onError: () => toast.error("Failed to create user"),
  });
}

export function useUpdateUserRole() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, role }: { id: string; role: string }) =>
      adminApi.updateUserRole(id, role),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "users"] }),
    onError: () => toast.error("Failed to update user role"),
  });
}

export function useToggleUserStatus() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, isActive }: { id: string; isActive: boolean }) =>
      adminApi.toggleUserStatus(id, isActive),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "users"] }),
    onError: () => toast.error("Failed to update user status"),
  });
}

export function useResetUserPassword() {
  return useMutation({
    mutationFn: (id: string) => adminApi.resetUserPassword(id),
    onError: () => toast.error("Failed to reset password"),
  });
}

export function useDeleteUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => adminApi.deleteUser(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "users"] }),
    onError: () => toast.error("Failed to delete user"),
  });
}

// ── System Logs ──

export function useLogs(params?: LogListParams) {
  return useQuery({
    queryKey: adminQueryKeys.logs(params),
    queryFn: () => adminApi.getLogs(params),
    staleTime: 10_000,
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });
}

export function useLogStats() {
  return useQuery({
    queryKey: adminQueryKeys.logStats(),
    queryFn: () => adminApi.getLogStats(),
    staleTime: 15_000,
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });
}

// ── Model Management ──

export function useModels() {
  return useQuery({
    queryKey: adminQueryKeys.models(),
    queryFn: () => adminApi.getModels(),
    staleTime: 30_000,
  });
}

export function useModelComparison() {
  return useQuery({
    queryKey: adminQueryKeys.modelComparison(),
    queryFn: () => adminApi.getModelComparison(),
    staleTime: 60_000,
  });
}

export function useTriggerRetrain() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (modelId?: string) => adminApi.triggerRetrain(modelId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "models"] }),
    onError: () => toast.error("Failed to trigger model retrain"),
  });
}

export function useRollbackModel() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (version: string) => adminApi.rollbackModel(version),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "models"] }),
    onError: () => toast.error("Failed to rollback model"),
  });
}

export function useRetrainStatus(taskId: string | null) {
  return useQuery({
    queryKey: adminQueryKeys.retrainStatus(taskId ?? ""),
    queryFn: () => adminApi.getRetrainStatus(taskId!),
    enabled: !!taskId,
    refetchInterval: (query) => {
      const status = query.state.data?.data?.status;
      if (status === "completed" || status === "failed") return false;
      return 3_000;
    },
    staleTime: 0,
  });
}

// ── Feature Flags ──

export function useFeatureFlags() {
  return useQuery({
    queryKey: adminQueryKeys.featureFlags(),
    queryFn: () => adminApi.getFeatureFlags(),
    staleTime: 30_000,
  });
}

/**
 * Lightweight feature flag hook for non-admin consumers.
 * Fetches once per session (staleTime: Infinity) to avoid
 * re-fetching on every mount.
 */
export function useFeatureFlag(flag: string): boolean {
  const { data } = useQuery({
    queryKey: adminQueryKeys.featureFlags(),
    queryFn: () => adminApi.getFeatureFlags(),
    staleTime: Infinity,
    gcTime: Infinity,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  });
  return data?.data?.[flag] ?? false;
}

export function useUpdateFeatureFlag() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ flag, enabled }: { flag: string; enabled: boolean }) =>
      adminApi.updateFeatureFlag(flag, enabled),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["admin", "featureFlags"] }),
    onError: () => toast.error("Failed to update feature flag"),
  });
}

// ── Security & Audit ──

export function useAuditLogs(params?: AuditLogListParams) {
  return useQuery({
    queryKey: adminQueryKeys.auditLogs(params),
    queryFn: () => adminApi.getAuditLogs(params),
    staleTime: 10_000,
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });
}

export function useAuditStats() {
  return useQuery({
    queryKey: adminQueryKeys.auditStats(),
    queryFn: () => adminApi.getAuditStats(),
    staleTime: 15_000,
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });
}

export function useSecurityPosture(enabled = true) {
  return useQuery({
    queryKey: adminQueryKeys.securityPosture(),
    queryFn: () => adminApi.getSecurityPosture(),
    enabled,
    staleTime: 30_000,
    refetchInterval: 60_000,
    refetchIntervalInBackground: false,
  });
}

// ── System Monitoring ──

export function useMonitoringSummary(enabled = true) {
  return useQuery({
    queryKey: adminQueryKeys.monitoring(),
    queryFn: () => adminApi.getMonitoringSummary(),
    enabled,
    staleTime: 15_000,
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });
}

export function useUptimeStats(enabled = true) {
  return useQuery({
    queryKey: adminQueryKeys.uptime(),
    queryFn: () => adminApi.getUptimeStats(),
    enabled,
    staleTime: 10_000,
    refetchInterval: 15_000,
    refetchIntervalInBackground: false,
  });
}

export function useApiResponseStats(minutes?: number) {
  return useQuery({
    queryKey: adminQueryKeys.apiResponses(minutes),
    queryFn: () => adminApi.getApiResponseStats(minutes),
    staleTime: 15_000,
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });
}

export function usePredictionDriftStats(minutes?: number) {
  return useQuery({
    queryKey: adminQueryKeys.predictionDrift(minutes),
    queryFn: () => adminApi.getPredictionDriftStats(minutes),
    staleTime: 30_000,
    refetchInterval: 60_000,
    refetchIntervalInBackground: false,
  });
}

export function useAlertDeliveryStats(hours?: number) {
  return useQuery({
    queryKey: adminQueryKeys.alertDelivery(hours),
    queryFn: () => adminApi.getAlertDeliveryStats(hours),
    staleTime: 15_000,
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });
}

export default useSystemHealth;
