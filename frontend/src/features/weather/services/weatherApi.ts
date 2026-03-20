/**
 * Weather API Service
 *
 * Provides API methods for weather data functionality including fetching
 * historical data, hourly forecasts, and aggregated statistics.
 *
 * The backend uses offset-based pagination and returns `timestamp` instead
 * of `recorded_at`.  This service normalises those differences so the rest
 * of the frontend can rely on the canonical frontend types.
 */

import { API_ENDPOINTS } from "@/config/api.config";
import { api } from "@/lib/api-client";
import type {
  DateRangeParams,
  HourlyWeatherParams,
  PaginatedResponse,
  WeatherData,
  WeatherDataParams,
  WeatherStats,
} from "@/types";
import type { AxiosRequestConfig } from "axios";

// ---------------------------------------------------------------------------
// Backend response shape (offset-based, `timestamp` field)
// ---------------------------------------------------------------------------

interface BackendWeatherRecord {
  id: number;
  temperature: number;
  humidity: number;
  precipitation: number;
  wind_speed: number | null;
  pressure: number | null;
  source: string;
  timestamp: string;
  created_at: string;
}

interface BackendWeatherResponse {
  success: boolean;
  data: BackendWeatherRecord[];
  total: number;
  limit: number;
  offset: number;
  count: number;
  sort_by: string;
  order: string;
  cache_hit: boolean;
  request_id?: string;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Convert a frontend `page` number to a backend `offset`. */
function pageToOffset(page: number, limit: number): number {
  return (Math.max(1, page) - 1) * limit;
}

/** Derive the total number of pages from total records and page size. */
function totalPages(total: number, limit: number): number {
  return Math.max(1, Math.ceil(total / limit));
}

/** Map a backend record to the frontend WeatherData type. */
function toWeatherData(r: BackendWeatherRecord): WeatherData {
  return {
    id: r.id,
    temperature: r.temperature,
    humidity: r.humidity,
    precipitation: r.precipitation,
    wind_speed: r.wind_speed ?? 0,
    pressure: r.pressure ?? 0,
    source: r.source as WeatherData["source"],
    recorded_at: r.timestamp, // backend calls it `timestamp`
    created_at: r.created_at,
  };
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Weather API methods
 */
export const weatherApi = {
  /**
   * Get paginated weather data with optional filters.
   *
   * Translates the frontend page-based params into the backend's
   * offset-based query and normalises the response shape.
   */
  getData: async (
    params?: WeatherDataParams,
    config?: AxiosRequestConfig,
  ): Promise<PaginatedResponse<WeatherData>> => {
    const limit = params?.limit ?? 100;
    const page = params?.page ?? 1;

    const qp = new URLSearchParams();
    qp.set("limit", String(limit));
    qp.set("offset", String(pageToOffset(page, limit)));
    if (params?.sort_by) qp.set("sort_by", params.sort_by);
    if (params?.order) qp.set("order", params.order);
    if (params?.source) qp.set("source", params.source);
    if (params?.start_date) qp.set("start_date", params.start_date);
    if (params?.end_date) qp.set("end_date", params.end_date);

    const url = `${API_ENDPOINTS.data.weather}?${qp}`;
    const raw = await api.get<BackendWeatherResponse>(url, config);

    return {
      success: raw.success,
      data: raw.data.map(toWeatherData),
      total: raw.total,
      page,
      limit,
      pages: totalPages(raw.total, limit),
      request_id: raw.request_id ?? "",
    };
  },

  /**
   * Get hourly weather forecast data
   */
  getHourlyForecast: async (
    params?: HourlyWeatherParams,
    config?: AxiosRequestConfig,
  ): Promise<WeatherData[]> => {
    const qp = new URLSearchParams();
    if (params?.lat) qp.set("lat", params.lat.toString());
    if (params?.lon) qp.set("lon", params.lon.toString());
    if (params?.days) qp.set("days", params.days.toString());

    const qs = qp.toString();
    const url = qs
      ? `${API_ENDPOINTS.data.hourly}?${qs}`
      : API_ENDPOINTS.data.hourly;

    const response = await api.get<{
      success: boolean;
      data: BackendWeatherRecord[];
    }>(url, config);
    return response.data.map(toWeatherData);
  },

  /**
   * Get aggregated weather statistics for a date range.
   *
   * The backend does not have a dedicated stats endpoint, so we fetch
   * all records for the range and compute the aggregates client-side.
   *
   * Data quality: Records with implausible values for Parañaque's tropical
   * climate are excluded from aggregation (temperature outside 293–318 K /
   * 20–45 °C, humidity outside 0–100 %, negative precipitation).
   */
  getStats: async (
    params?: DateRangeParams,
    config?: AxiosRequestConfig,
  ): Promise<WeatherStats> => {
    const qp = new URLSearchParams();
    qp.set("limit", "1000");
    qp.set("offset", "0");
    if (params?.start_date) qp.set("start_date", params.start_date);
    if (params?.end_date) qp.set("end_date", params.end_date);

    const url = `${API_ENDPOINTS.data.weather}?${qp}`;
    const raw = await api.get<BackendWeatherResponse>(url, config);

    const allRecords = raw.data;
    if (allRecords.length === 0) {
      return {
        avg_temperature: 0,
        avg_humidity: 0,
        total_precipitation: 0,
        avg_wind_speed: 0,
        record_count: 0,
        flagged_count: 0,
      };
    }

    // Filter out implausible records for stats (Parañaque tropical climate)
    const valid = allRecords.filter(
      (r) =>
        r.temperature >= 293.15 &&
        r.temperature <= 318.15 &&
        r.humidity >= 0 &&
        r.humidity <= 100 &&
        r.precipitation >= 0,
    );

    const flagged = allRecords.length - valid.length;

    if (valid.length === 0) {
      return {
        avg_temperature: 0,
        avg_humidity: 0,
        total_precipitation: 0,
        avg_wind_speed: 0,
        record_count: raw.total,
        flagged_count: flagged,
      };
    }

    const sum = valid.reduce(
      (acc, r) => ({
        temp: acc.temp + (r.temperature ?? 0),
        hum: acc.hum + (r.humidity ?? 0),
        prec: acc.prec + (r.precipitation ?? 0),
        wind: acc.wind + (r.wind_speed ?? 0),
      }),
      { temp: 0, hum: 0, prec: 0, wind: 0 },
    );

    const n = valid.length;
    return {
      avg_temperature: sum.temp / n,
      avg_humidity: sum.hum / n,
      total_precipitation: sum.prec,
      avg_wind_speed: sum.wind / n,
      record_count: raw.total,
      flagged_count: flagged,
    };
  },
};
