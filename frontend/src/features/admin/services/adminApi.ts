/**
 * Admin API Service
 *
 * Provides API methods for system health, user management,
 * system logs, model management, and admin-specific data.
 */

import { API_CONFIG } from "@/config/api.config";
import api from "@/lib/api-client";

const { endpoints } = API_CONFIG;

/**
 * System health check response from /api/v1/health
 */
export interface SystemHealth {
  status: "healthy" | "degraded";
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
    model_file?: string;
    file_size_bytes?: number | null;
    checksum?: string | null;
    training_data?: {
      total_records?: number;
      num_features?: number;
      files?: string[];
    };
    model_parameters?: Record<string, unknown>;
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
  role: "admin" | "operator" | "user";
  is_active: boolean;
  created_at: string;
  last_login_at: string | null;
}

export interface CreateUserParams {
  email: string;
  name?: string;
  role: "admin" | "operator" | "user";
}

export interface CreateUserResponse {
  success: boolean;
  data: AdminUser;
  temporary_password: string;
  message: string;
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
  request_id: string;
  method: string;
  endpoint: string;
  status_code: number;
  response_time_ms: number;
  user_id: string | null;
  ip_address: string | null;
  error_message: string | null;
  created_at: string;
  category: string;
}

export interface LogListParams {
  page?: number;
  per_page?: number;
  category?: string;
  status_min?: number;
  start_date?: string;
  end_date?: string;
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

// ── Backend Response Shapes ──

interface BackendPaginatedResponse<T> {
  success: boolean;
  data: T[];
  pagination: {
    page: number;
    per_page: number;
    total: number;
    total_pages: number;
  };
}

interface BackendLogStats {
  success: boolean;
  data: {
    total_today: number;
    predictions_today: number;
    login_attempts: number;
    uploads_today: number;
    errors_today: number;
    total_all_time: number;
  };
}

// ── Security & Audit Types ──

export interface AuditLogEntry {
  id: number;
  action: string;
  severity: "info" | "warning" | "critical";
  user_id: number | null;
  user_email: string | null;
  target_user_id: number | null;
  ip_address: string | null;
  request_id: string | null;
  details: Record<string, unknown> | null;
  created_at: string;
}

export interface AuditLogListParams {
  page?: number;
  per_page?: number;
  action?: string;
  severity?: string;
  user_email?: string;
  date_from?: string;
  date_to?: string;
  search?: string;
}

export interface AuditLogListResponse {
  success: boolean;
  data: {
    logs: AuditLogEntry[];
    total: number;
    page: number;
    per_page: number;
    total_pages: number;
  };
}

export interface AuditStats {
  total_events_24h: number;
  severity_breakdown: Record<string, number>;
  top_actions: Record<string, number>;
  failed_logins_24h: number;
  access_denied_24h: number;
  critical_events_24h: number;
}

export interface SecurityCheck {
  name: string;
  status: "pass" | "fail" | "warn";
  category: string;
  detail: string;
  remediation: string;
}

export interface SecurityPosture {
  score: number;
  checks: SecurityCheck[];
  passed: number;
  total: number;
  threat_level: "low" | "moderate" | "high";
  threat_indicators: {
    failed_logins_24h: number;
    critical_events_24h: number;
    locked_accounts: number;
  };
  user_stats: {
    total: number;
    active: number;
    locked: number;
    admins: number;
  };
}

// ── Feature Flag Types ──

export interface FeatureFlagDetail {
  name: string;
  description: string;
  enabled: boolean;
  flag_type: string;
  rollout_percentage: number;
  allowed_segments: string[];
  tags: string[];
  created_at: string;
  updated_at: string;
  force_value: boolean | null;
  owner: string;
}

export interface FeatureFlagsResponse {
  success: boolean;
  data: Record<string, boolean>;
  flags: FeatureFlagDetail[];
}

// ── Monitoring Types ──

export interface ServiceStatus {
  service: string;
  status: "healthy" | "degraded" | "offline" | "unknown";
  latency_ms: number;
  last_checked: string | null;
  detail: string;
  uptime_pct_24h: number | null;
}

export interface UptimeStats {
  uptime_seconds: number;
  uptime_formatted: string;
  health_check_count: number;
  healthy_count: number;
  uptime_percentage: number;
  avg_response_ms: number;
  last_check: {
    timestamp: string;
    healthy: boolean;
    response_ms: number;
  } | null;
  services: ServiceStatus[];
}

export interface SlowestEndpoint {
  endpoint: string;
  avg_ms: number;
  count: number;
  p95_ms: number;
  p99_ms: number;
  error_count: number;
  sla_exceeded: boolean;
}

export interface ApiResponseStats {
  period_minutes: number;
  total_requests: number;
  avg_response_ms: number;
  p95_response_ms: number;
  p99_response_ms: number;
  error_rate: number;
  status_breakdown: Record<string, number>;
  slowest_endpoints: SlowestEndpoint[];
}

export interface PredictionDriftStats {
  window_minutes: number;
  total_predictions: number;
  current_distribution: Record<string, number>;
  baseline_distribution: Record<string, number> | null;
  psi: number | null;
  psi_threshold: number;
  drift_detected: boolean;
  avg_confidence: number;
  confidence_stats: Partial<{
    min: number;
    max: number;
    p50: number;
    p95: number;
  }>;
}

export interface AlertDeliveryStats {
  period_hours: number;
  total_alerts: number;
  status_breakdown: Record<string, number>;
  channel_breakdown: Record<string, number>;
  success_rate: number;
  recent_failures: {
    id: number;
    risk_label: string;
    channel: string;
    error: string;
    created_at: string;
  }[];
}

export interface MonitoringSummary {
  uptime: UptimeStats;
  api_responses: ApiResponseStats;
  prediction_drift: PredictionDriftStats;
  alert_delivery: AlertDeliveryStats;
  generated_at: string;
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
  createUser: async (params: CreateUserParams): Promise<CreateUserResponse> => {
    return api.post(endpoints.admin.users, params);
  },

  getUsers: async (params?: UserListParams): Promise<UserListResponse> => {
    const raw = await api.get<BackendPaginatedResponse<AdminUser>>(
      endpoints.admin.users,
      { params },
    );
    return {
      success: raw.success,
      data: {
        users: raw.data ?? [],
        total: raw.pagination?.total ?? 0,
        page: raw.pagination?.page ?? 1,
        per_page: raw.pagination?.per_page ?? 20,
        total_pages: raw.pagination?.total_pages ?? 1,
      },
    };
  },

  getUser: async (
    id: string,
  ): Promise<{ success: boolean; data: AdminUser }> => {
    return api.get(`${endpoints.admin.users}/${id}`);
  },

  updateUserRole: async (
    id: string,
    role: string,
  ): Promise<{ success: boolean; data: AdminUser }> => {
    return api.patch(`${endpoints.admin.users}/${id}/role`, { role });
  },

  toggleUserStatus: async (
    id: string,
    isActive: boolean,
  ): Promise<{ success: boolean; data: AdminUser }> => {
    return api.patch(`${endpoints.admin.users}/${id}/status`, {
      is_active: isActive,
    });
  },

  resetUserPassword: async (
    id: string,
  ): Promise<{
    success: boolean;
    message: string;
    temporary_password: string;
  }> => {
    return api.post(`${endpoints.admin.users}/${id}/reset-password`);
  },

  deleteUser: async (
    id: string,
  ): Promise<{ success: boolean; message: string }> => {
    return api.delete(`${endpoints.admin.users}/${id}`);
  },

  // ── System Logs ──
  getLogs: async (params?: LogListParams): Promise<LogListResponse> => {
    const raw = await api.get<BackendPaginatedResponse<LogEntry>>(
      endpoints.admin.logs,
      { params },
    );
    return {
      success: raw.success,
      data: {
        logs: raw.data ?? [],
        total: raw.pagination?.total ?? 0,
        page: raw.pagination?.page ?? 1,
        per_page: raw.pagination?.per_page ?? 20,
        total_pages: raw.pagination?.total_pages ?? 1,
      },
    };
  },

  getLogStats: async (): Promise<LogStats> => {
    const raw = await api.get<BackendLogStats>(endpoints.admin.logStats);
    return {
      success: raw.success,
      data: {
        total_today: raw.data?.total_today ?? 0,
        predictions: raw.data?.predictions_today ?? 0,
        logins: raw.data?.login_attempts ?? 0,
        uploads: raw.data?.uploads_today ?? 0,
        errors: raw.data?.errors_today ?? 0,
      },
    };
  },

  // ── Model Management ──
  getModels: async (): Promise<{ success: boolean; data: ModelInfo }> => {
    return api.get(endpoints.admin.models);
  },

  triggerRetrain: async (modelId?: string): Promise<RetrainResult> => {
    return api.post(
      endpoints.admin.modelRetrain,
      modelId ? { model_id: modelId } : undefined,
    );
  },

  getRetrainStatus: async (taskId: string): Promise<RetrainResult> => {
    return api.get(endpoints.admin.modelRetrainStatus, {
      params: { task_id: taskId },
    });
  },

  rollbackModel: async (
    version: string,
  ): Promise<{ success: boolean; message: string }> => {
    return api.post(endpoints.admin.modelRollback, { version });
  },

  getModelComparison: async (): Promise<{
    success: boolean;
    data: Record<string, unknown>;
  }> => {
    return api.get(endpoints.admin.modelComparison);
  },

  // ── Feature Flags ──
  getFeatureFlags: async (): Promise<FeatureFlagsResponse> => {
    const response = await api.get<{
      success: boolean;
      data: { flags: FeatureFlagDetail[]; count: number };
    }>(endpoints.admin.featureFlags);
    const flagArr: FeatureFlagDetail[] = response?.data?.flags ?? [];
    const flagMap: Record<string, boolean> = {};
    for (const f of flagArr) {
      flagMap[f.name] = f.enabled;
    }
    return {
      success: response?.success ?? true,
      data: flagMap,
      flags: flagArr,
    };
  },

  updateFeatureFlag: async (
    flag: string,
    enabled: boolean,
  ): Promise<{ success: boolean }> => {
    return api.patch(`${endpoints.admin.featureFlags}/${flag}`, { enabled });
  },

  // ── Security & Audit ──
  getAuditLogs: async (
    params?: AuditLogListParams,
  ): Promise<AuditLogListResponse> => {
    const raw = await api.get<BackendPaginatedResponse<AuditLogEntry>>(
      endpoints.admin.auditLogs,
      { params },
    );
    return {
      success: raw.success,
      data: {
        logs: raw.data ?? [],
        total: raw.pagination?.total ?? 0,
        page: raw.pagination?.page ?? 1,
        per_page: raw.pagination?.per_page ?? 25,
        total_pages: raw.pagination?.total_pages ?? 1,
      },
    };
  },

  getAuditStats: async (): Promise<{ success: boolean; data: AuditStats }> => {
    return api.get(endpoints.admin.auditStats);
  },

  getSecurityPosture: async (): Promise<{
    success: boolean;
    data: SecurityPosture;
  }> => {
    return api.get(endpoints.admin.securityPosture);
  },

  // ── Monitoring ──
  getMonitoringSummary: async (): Promise<{
    success: boolean;
    data: MonitoringSummary;
  }> => {
    return api.get(endpoints.admin.monitoring);
  },

  getUptimeStats: async (): Promise<{
    success: boolean;
    data: UptimeStats;
  }> => {
    return api.get(endpoints.admin.monitoringUptime);
  },

  getApiResponseStats: async (
    minutes?: number,
  ): Promise<{ success: boolean; data: ApiResponseStats }> => {
    return api.get(endpoints.admin.monitoringApiResponses, {
      params: minutes ? { minutes } : undefined,
    });
  },

  getPredictionDriftStats: async (
    minutes?: number,
  ): Promise<{ success: boolean; data: PredictionDriftStats }> => {
    return api.get(endpoints.admin.monitoringPredictionDrift, {
      params: minutes ? { minutes } : undefined,
    });
  },

  getAlertDeliveryStats: async (
    hours?: number,
  ): Promise<{ success: boolean; data: AlertDeliveryStats }> => {
    return api.get(endpoints.admin.monitoringAlertDelivery, {
      params: hours ? { hours } : undefined,
    });
  },
};

export default adminApi;
