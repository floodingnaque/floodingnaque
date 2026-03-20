/**
 * Dashboard API Service
 *
 * Provides API methods for fetching dashboard statistics
 * and activity data.
 *
 * The backend returns a nested `summary` object which is
 * normalised here into the flat `DashboardStats` shape that
 * the dashboard components expect.
 */

import { API_CONFIG } from "@/config/api.config";
import api from "@/lib/api-client";
import type { AxiosRequestConfig } from "axios";

const { endpoints } = API_CONFIG;

/**
 * Activity item representing a recent prediction or alert
 */
export interface ActivityItem {
  type: "prediction" | "alert";
  timestamp: string;
  description: string;
}

/**
 * Dashboard statistics consumed by frontend components.
 */
export interface DashboardStats {
  total_predictions: number;
  predictions_today: number;
  active_alerts: number;
  avg_risk_level: number;
  recent_activity: ActivityItem[];
}

// ---------------------------------------------------------------------------
// Backend response shape (from GET /api/v1/dashboard/stats)
// ---------------------------------------------------------------------------

interface BackendDashboardResponse {
  success: boolean;
  summary: {
    weather_data: { total: number; today: number; latest: unknown };
    predictions: {
      total: number;
      today: number;
      this_week: number;
      latest: { risk_level?: number } | null;
    };
    alerts: { total: number; today: number; critical_24h: number };
    risk_distribution_30d: { safe: number; alert: number; critical: number };
  };
  generated_at: string;
  request_id: string;
}

// ---------------------------------------------------------------------------
// Normalisation helper
// ---------------------------------------------------------------------------

function toFrontendStats(raw: BackendDashboardResponse): DashboardStats {
  const s = raw.summary;
  const dist = s.risk_distribution_30d;
  const distTotal = dist.safe + dist.alert + dist.critical;

  // Weighted average on 0–2 scale (0 = Safe, 2 = Critical)
  const avgRisk =
    distTotal > 0
      ? (0 * dist.safe + 1 * dist.alert + 2 * dist.critical) / distTotal
      : 0;

  return {
    total_predictions: s.predictions.total,
    predictions_today: s.predictions.today,
    active_alerts: s.alerts.critical_24h,
    avg_risk_level: avgRisk,
    recent_activity: [],
  };
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Dashboard API methods
 */
export const dashboardApi = {
  /**
   * Get dashboard statistics including totals and recent activity.
   * Normalises the nested backend response into a flat DashboardStats shape.
   */
  getStats: async (config?: AxiosRequestConfig): Promise<DashboardStats> => {
    const raw = await api.get<BackendDashboardResponse>(
      endpoints.dashboard.stats,
      config,
    );
    return toFrontendStats(raw);
  },
};

export default dashboardApi;
