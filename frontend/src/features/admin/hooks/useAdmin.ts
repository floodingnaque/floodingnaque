/**
 * Admin Hooks
 *
 * TanStack Query hooks for system health, user management,
 * system logs, and model management.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { adminApi } from '../services/adminApi';
import type { UserListParams, LogListParams } from '../services/adminApi';

/**
 * Query keys for admin-related queries
 */
export const adminQueryKeys = {
  all: ['admin'] as const,
  health: () => [...adminQueryKeys.all, 'health'] as const,
  users: (params?: UserListParams) => [...adminQueryKeys.all, 'users', params] as const,
  user: (id: string) => [...adminQueryKeys.all, 'user', id] as const,
  logs: (params?: LogListParams) => [...adminQueryKeys.all, 'logs', params] as const,
  logStats: () => [...adminQueryKeys.all, 'logStats'] as const,
  models: () => [...adminQueryKeys.all, 'models'] as const,
  modelComparison: () => [...adminQueryKeys.all, 'modelComparison'] as const,
  featureFlags: () => [...adminQueryKeys.all, 'featureFlags'] as const,
};

// ── Health ──

export function useSystemHealth(enabled = true) {
  return useQuery({
    queryKey: adminQueryKeys.health(),
    queryFn: () => adminApi.getHealth(),
    enabled,
    refetchInterval: 30_000,
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

export function useUpdateUserRole() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, role }: { id: string; role: string }) =>
      adminApi.updateUserRole(id, role),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'users'] }),
  });
}

export function useToggleUserStatus() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, isActive }: { id: string; isActive: boolean }) =>
      adminApi.toggleUserStatus(id, isActive),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'users'] }),
  });
}

export function useResetUserPassword() {
  return useMutation({
    mutationFn: (id: string) => adminApi.resetUserPassword(id),
  });
}

export function useDeleteUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => adminApi.deleteUser(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'users'] }),
  });
}

// ── System Logs ──

export function useLogs(params?: LogListParams) {
  return useQuery({
    queryKey: adminQueryKeys.logs(params),
    queryFn: () => adminApi.getLogs(params),
    staleTime: 10_000,
    refetchInterval: 30_000,
  });
}

export function useLogStats() {
  return useQuery({
    queryKey: adminQueryKeys.logStats(),
    queryFn: () => adminApi.getLogStats(),
    staleTime: 15_000,
    refetchInterval: 30_000,
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
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'models'] }),
  });
}

export function useRollbackModel() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (version: string) => adminApi.rollbackModel(version),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'models'] }),
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

export function useUpdateFeatureFlag() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ flag, enabled }: { flag: string; enabled: boolean }) =>
      adminApi.updateFeatureFlag(flag, enabled),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'featureFlags'] }),
  });
}

export default useSystemHealth;
