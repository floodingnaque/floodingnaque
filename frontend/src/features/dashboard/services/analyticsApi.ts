/**
 * Analytics API Service
 *
 * Provides API methods for fetching historical flood data,
 * trend statistics, and model confidence metrics.
 */

import { API_ENDPOINTS } from "@/config/api.config";
import { BARANGAYS } from "@/config/paranaque";
import api from "@/lib/api-client";
import type {
  FloodEvent,
  FloodFrequencyItem,
  FloodHistoryData,
  ModelMetricsData,
  YearlyFloodTrend,
} from "../types";

// ---------------------------------------------------------------------------
// Backend response shapes
// ---------------------------------------------------------------------------

interface ModelListItem {
  version: string;
  path: string;
  is_current: boolean;
  created_at?: string;
  metrics?: {
    accuracy: number | null;
    precision: number | null;
    recall: number | null;
    f1_score: number | null;
  };
}

interface ModelsResponse {
  success: boolean;
  models: ModelListItem[];
}

interface IncidentItem {
  id: number;
  barangay: string;
  reported_at: string;
  flood_depth?: string;
  weather_disturbance?: string;
  duration?: string;
  status: string;
  risk_level: number;
}

interface IncidentsResponse {
  success: boolean;
  data: IncidentItem[];
  total: number;
}

interface WeatherDataItem {
  id: number;
  recorded_at: string;
  precipitation: number;
  temperature: number;
  humidity: number;
}

interface WeatherDataResponse {
  success: boolean;
  data: WeatherDataItem[];
  total: number;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function depthLabel(riskLevel: number): string {
  if (riskLevel >= 2) return "Waist";
  if (riskLevel >= 1) return "Knee";
  return "Gutter";
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

export const analyticsApi = {
  /**
   * Fetch historical flood data (frequency, yearly, monthly, recent events).
   * Falls back to static DRRMO data if backend is unavailable.
   */
  getFloodHistory: async (): Promise<FloodHistoryData> => {
    try {
      // Attempt to fetch from LGU incidents endpoint
      const [incidentsRes, weatherRes] = await Promise.allSettled([
        api.get<IncidentsResponse>(
          `${API_ENDPOINTS.lgu.incidents}?limit=200&sort_by=reported_at&order=desc`,
        ),
        api.get<WeatherDataResponse>(
          `${API_ENDPOINTS.data.weather}?limit=500&sort_by=recorded_at&order=desc`,
        ),
      ]);

      // Build frequency from incidents if available
      if (
        incidentsRes.status === "fulfilled" &&
        incidentsRes.value.data?.length > 0
      ) {
        const incidents = incidentsRes.value.data;

        // Frequency by barangay
        const freqMap = new Map<string, number>();
        for (const inc of incidents) {
          freqMap.set(inc.barangay, (freqMap.get(inc.barangay) ?? 0) + 1);
        }
        const frequency: FloodFrequencyItem[] = Array.from(freqMap.entries())
          .map(([barangay, events]) => ({ barangay, events }))
          .sort((a, b) => b.events - a.events);

        // Yearly aggregation
        const yearMap = new Map<string, { events: number; rain: number }>();
        for (const inc of incidents) {
          const year = new Date(inc.reported_at).getFullYear().toString();
          const entry = yearMap.get(year) ?? { events: 0, rain: 0 };
          entry.events += 1;
          yearMap.set(year, entry);
        }

        // Merge rainfall from weather data if available
        if (
          weatherRes.status === "fulfilled" &&
          weatherRes.value.data?.length > 0
        ) {
          for (const w of weatherRes.value.data) {
            const year = new Date(w.recorded_at).getFullYear().toString();
            const entry = yearMap.get(year);
            if (entry) {
              entry.rain += w.precipitation;
            }
          }
        }

        const yearly: YearlyFloodTrend[] = Array.from(yearMap.entries())
          .map(([year, { events, rain }]) => ({
            year,
            events,
            rain: Math.round(rain),
          }))
          .sort((a, b) => a.year.localeCompare(b.year));

        // Recent events
        const recentEvents: FloodEvent[] = incidents.slice(0, 8).map((inc) => ({
          id: inc.id,
          date: new Date(inc.reported_at).toISOString().split("T")[0] ?? "",
          barangay: inc.barangay,
          depth: inc.flood_depth ?? depthLabel(inc.risk_level),
          disturbance: inc.weather_disturbance ?? "Unknown",
          duration: inc.duration ?? "-",
        }));

        // Most affected barangay
        const mostAffected = frequency[0]?.barangay ?? "Baclaran";

        return {
          frequency,
          yearly: yearly.length > 0 ? yearly : [],
          monthly: [], // Monthly aggregation requires full dataset
          recentEvents,
          summary: {
            totalEvents: incidents.length,
            barangaysHit: `${frequency.length} / 16`,
            worstMonth: "August",
            mostAffected,
          },
        };
      }
    } catch {
      // Fall through to unavailable state
    }

    // Backend unavailable or no incidents - fall back to static DRRMO data
    // from the BARANGAYS config which contains verified 2022-2025 flood event counts.
    const frequency: FloodFrequencyItem[] = BARANGAYS.filter(
      (b) => b.floodEvents > 0,
    )
      .map((b) => ({ barangay: b.name, events: b.floodEvents }))
      .sort((a, b) => b.events - a.events);

    const totalEvents = BARANGAYS.reduce((sum, b) => sum + b.floodEvents, 0);
    const barangaysHit = frequency.length;
    const mostAffected = frequency[0]?.barangay ?? "-";

    // Yearly breakdown from DRRMO records (approximate counts by year)
    const yearly: YearlyFloodTrend[] = [
      { year: "2022", events: 209, rain: 0 },
      { year: "2023", events: 8, rain: 0 },
      { year: "2024", events: 376, rain: 0 },
      { year: "2025", events: 589, rain: 0 },
    ];

    return {
      available: true,
      frequency,
      yearly,
      monthly: [],
      recentEvents: [],
      summary: {
        totalEvents,
        barangaysHit: `${barangaysHit} / 16`,
        worstMonth: "August",
        mostAffected,
      },
    };
  },

  /**
   * Fetch model confidence metrics from the models endpoint.
   * Returns unavailable state if backend cannot be reached.
   */
  getModelMetrics: async (): Promise<ModelMetricsData> => {
    try {
      const res = await api.get<ModelsResponse>(API_ENDPOINTS.models.list);
      const active = res.models?.find((m) => m.is_current);
      if (active?.metrics) {
        const m = active.metrics;
        return {
          metrics: {
            overall: Math.round((m.accuracy ?? 0) * 100 * 10) / 10,
            precision: Math.round((m.precision ?? 0) * 100 * 100) / 100,
            recall: Math.round((m.recall ?? 0) * 100 * 100) / 100,
            f1: Math.round((m.f1_score ?? 0) * 100 * 100) / 100,
            roc_auc: 0,
            cv_mean: 0,
            cv_std: 0,
            ensemble_agreement: 0,
            calibration: 0,
          },
          cvFolds: [],
          calibration: [],
          modelVersion: active.version,
          modelName: active.version,
        };
      }
    } catch {
      // Fall through to unavailable state
    }

    // Backend unavailable - return empty metrics instead of fabricated data
    return {
      available: false,
      metrics: {
        overall: 0,
        precision: 0,
        recall: 0,
        f1: 0,
        roc_auc: 0,
        cv_mean: 0,
        cv_std: 0,
        ensemble_agreement: 0,
        calibration: 0,
      },
      cvFolds: [],
      calibration: [],
      modelVersion: "-",
      modelName: "Unavailable",
    };
  },
};

export default analyticsApi;
