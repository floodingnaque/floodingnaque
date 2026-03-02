/**
 * Admin API Service
 *
 * Provides API methods for system health, user management,
 * system logs, model management, and admin-specific data.
 */

import api from '@/lib/api-client';
import { API_CONFIG } from '@/config/api.config';

const { endpoints } = API_CONFIG;

/**
 * System health check response from /api/v1/health
 */
export interface SystemHealth {
  status: 'healthy' | 'degraded';
  timestamp: string;
  sla: {
    within_sla: boolean;
    response_time_ms: number;
    threshold_ms: number;
    message: string;
  };
  checks: {
    database: {
      status: string;
      connected: boolean;
      latency_ms?: number;
    };
    database_pool?: {
      size?: number;
      checked_out?: number;
      overflow?: number;
    };
    redis: {
      status: string;
      connected?: boolean;
    };
    cache: {
      status: string;
    };
    model_available: boolean;
    scheduler_running: boolean;
    external_apis?: Record<string, unknown>;
    sentry_enabled: boolean;
  };
  model?: {
    loaded: boolean;
    type?: string;
    features_count?: number;
    version?: string;
    created_at?: string;
    metrics?: Record<string, number>;
  };
  system?: {
    python_version: string;
  };
}

// ── User Management Types ──

export interface AdminUser {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'operator' | 'user';
  is_active: boolean;
  created_at: string;
  last_login_at: string | null;
}

export interface UserListParams {
  page?: number;
  per_page?: number;
  role?: string;
  status?: string;
  search?: string;
}

export interface UserListResponse {
  success: boolean;
  data: {
    users: AdminUser[];
    total: number;
    page: number;
    per_page: number;
    total_pages: number;
  };
}

// ── System Logs Types ──

export interface LogEntry {
  id: number;
  method: string;
  endpoint: string;
  status_code: number;
  response_time_ms: number;
  user_id: string | null;
  ip_address: string | null;
  created_at: string;
  category: string;
}

export interface LogListParams {
  page?: number;
  per_page?: number;
  category?: string;
  status?: string;
  date_from?: string;
  date_to?: string;
  search?: string;
}

export interface LogListResponse {
  success: boolean;
  data: {
    logs: LogEntry[];
    total: number;
    page: number;
    per_page: number;
    total_pages: number;
  };
}

export interface LogStats {
  success: boolean;
  data: {
    total_today: number;
    predictions: number;
    logins: number;
    uploads: number;
    errors: number;
  };
}

// ── Model Management Types ──

export interface ModelInfo {
  current_model: Record<string, unknown>;
}

export interface RetrainResult {
  success: boolean;
  data: {
    task_id?: string;
    status?: string;
    message?: string;
  };
}

/**
 * Admin API methods
 */
export const adminApi = {
  // ── Health ──
  getHealth: async (): Promise<SystemHealth> => {
    return api.get<SystemHealth>(endpoints.health.status);
  },

  // ── User Management ──
  getUsers: async (params?: UserListParams): Promise<UserListResponse> => {
    return api.get<UserListResponse>(endpoints.admin.users, { params });
  },

  getUser: async (id: string): Promise<{ success: boolean; data: AdminUser }> => {
    return api.get(`${endpoints.admin.users}/${id}`);
  },

  updateUserRole: async (id: string, role: string): Promise<{ success: boolean; data: AdminUser }> => {
    return api.patch(`${endpoints.admin.users}/${id}/role`, { role });
  },

  toggleUserStatus: async (id: string, isActive: boolean): Promise<{ success: boolean; data: AdminUser }> => {
    return api.patch(`${endpoints.admin.users}/${id}/status`, { is_active: isActive });
  },

  resetUserPassword: async (id: string): Promise<{ success: boolean; message: string }> => {
    return api.post(`${endpoints.admin.users}/${id}/reset-password`);
  },

  deleteUser: async (id: string): Promise<{ success: boolean; message: string }> => {
    return api.delete(`${endpoints.admin.users}/${id}`);
  },

  // ── System Logs ──
  getLogs: async (params?: LogListParams): Promise<LogListResponse> => {
    return api.get<LogListResponse>(endpoints.admin.logs, { params });
  },

  getLogStats: async (): Promise<LogStats> => {
    return api.get<LogStats>(endpoints.admin.logStats);
  },

  // ── Model Management ──
  getModels: async (): Promise<{ success: boolean; data: ModelInfo }> => {
    return api.get(endpoints.admin.models);
  },

  triggerRetrain: async (modelId?: string): Promise<RetrainResult> => {
    return api.post(endpoints.admin.modelRetrain, modelId ? { model_id: modelId } : undefined);
  },

  getRetrainStatus: async (taskId: string): Promise<RetrainResult> => {
    return api.get(endpoints.admin.modelRetrainStatus, { params: { task_id: taskId } });
  },

  rollbackModel: async (version: string): Promise<{ success: boolean; message: string }> => {
    return api.post(endpoints.admin.modelRollback, { version });
  },

  getModelComparison: async (): Promise<{ success: boolean; data: Record<string, unknown> }> => {
    return api.get(endpoints.admin.modelComparison);
  },

  // ── Feature Flags ──
  getFeatureFlags: async (): Promise<{ success: boolean; data: Record<string, boolean> }> => {
    return api.get(endpoints.admin.featureFlags);
  },

  updateFeatureFlag: async (flag: string, enabled: boolean): Promise<{ success: boolean }> => {
    return api.patch(`${endpoints.admin.featureFlags}/${flag}`, { enabled });
  },
};

export default adminApi;
