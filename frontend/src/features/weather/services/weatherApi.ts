/**
 * Weather API Service
 *
 * Provides API methods for weather data functionality including fetching
 * historical data, hourly forecasts, and aggregated statistics.
 */

import { api } from '@/lib/api-client';
import { API_ENDPOINTS } from '@/config/api.config';
import type {
  WeatherData,
  WeatherDataParams,
  HourlyWeatherParams,
  WeatherStats,
  PaginatedResponse,
  DateRangeParams,
} from '@/types';

/**
 * Weather API methods
 */
export const weatherApi = {
  /**
   * Get paginated weather data with optional filters
   *
   * @param params - Optional query parameters for filtering and pagination
   * @returns Paginated response with weather data
   *
   * @example
   * const data = await weatherApi.getData({ page: 1, limit: 50, source: 'OWM' });
   */
  getData: async (params?: WeatherDataParams): Promise<PaginatedResponse<WeatherData>> => {
    const queryParams = new URLSearchParams();

    if (params?.page) queryParams.set('page', params.page.toString());
    if (params?.limit) queryParams.set('limit', params.limit.toString());
    if (params?.sort_by) queryParams.set('sort_by', params.sort_by);
    if (params?.order) queryParams.set('order', params.order);
    if (params?.source) queryParams.set('source', params.source);
    if (params?.start_date) queryParams.set('start_date', params.start_date);
    if (params?.end_date) queryParams.set('end_date', params.end_date);

    const queryString = queryParams.toString();
    const url = queryString
      ? `${API_ENDPOINTS.data.weather}?${queryString}`
      : API_ENDPOINTS.data.weather;

    return api.get<PaginatedResponse<WeatherData>>(url);
  },

  /**
   * Get hourly weather forecast data
   *
   * @param params - Optional parameters for location and forecast days
   * @returns Array of hourly weather data
   *
   * @example
   * const forecast = await weatherApi.getHourlyForecast({ lat: 14.5995, lon: 120.9842, days: 3 });
   */
  getHourlyForecast: async (params?: HourlyWeatherParams): Promise<WeatherData[]> => {
    const queryParams = new URLSearchParams();

    if (params?.lat) queryParams.set('lat', params.lat.toString());
    if (params?.lon) queryParams.set('lon', params.lon.toString());
    if (params?.days) queryParams.set('days', params.days.toString());

    const queryString = queryParams.toString();
    const url = queryString
      ? `${API_ENDPOINTS.data.hourly}?${queryString}`
      : API_ENDPOINTS.data.hourly;

    const response = await api.get<{ success: boolean; data: WeatherData[] }>(url);
    return response.data;
  },

  /**
   * Get aggregated weather statistics for a date range
   *
   * @param params - Optional date range parameters
   * @returns Aggregated weather statistics
   *
   * @example
   * const stats = await weatherApi.getStats({ start_date: '2026-01-01', end_date: '2026-01-31' });
   */
  getStats: async (params?: DateRangeParams): Promise<WeatherStats> => {
    const queryParams = new URLSearchParams();
    queryParams.set('stats', 'true');

    if (params?.start_date) queryParams.set('start_date', params.start_date);
    if (params?.end_date) queryParams.set('end_date', params.end_date);

    const queryString = queryParams.toString();
    const url = `${API_ENDPOINTS.data.weather}?${queryString}`;

    const response = await api.get<{ success: boolean; data: WeatherStats }>(url);
    return response.data;
  },
};
