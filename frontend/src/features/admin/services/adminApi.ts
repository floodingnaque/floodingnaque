/**
 * Admin API Service
 *
 * Provides API methods for fetching system health,
 * dashboard statistics, and other admin-specific data.
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

/**
 * Admin API methods
 */
export const adminApi = {
  /**
   * Get comprehensive system health status
   */
  getHealth: async (): Promise<SystemHealth> => {
    return api.get<SystemHealth>(endpoints.health.status);
  },
};

export default adminApi;
