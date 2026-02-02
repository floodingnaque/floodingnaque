/**
 * useWeather Hooks
 *
 * React Query hooks for fetching and managing weather data.
 * Provides queries for weather data, hourly forecasts, and statistics.
 */

import { useQuery, type UseQueryOptions } from '@tanstack/react-query';
import { weatherApi } from '../services/weatherApi';
import type {
  WeatherData,
  WeatherDataParams,
  HourlyWeatherParams,
  WeatherStats,
  PaginatedResponse,
  DateRangeParams,
  ApiError,
} from '@/types';

/**
 * Query keys for weather data
 */
export const weatherKeys = {
  all: ['weather'] as const,
  data: () => [...weatherKeys.all, 'data'] as const,
  dataList: (params?: WeatherDataParams) => [...weatherKeys.data(), params] as const,
  hourly: () => [...weatherKeys.all, 'hourly'] as const,
  hourlyList: (params?: HourlyWeatherParams) => [...weatherKeys.hourly(), params] as const,
  stats: () => [...weatherKeys.all, 'stats'] as const,
  statsByRange: (params?: DateRangeParams) => [...weatherKeys.stats(), params] as const,
};

/**
 * useWeatherData hook for fetching paginated weather data
 *
 * @param params - Optional query parameters for filtering and pagination
 * @param options - Optional React Query options
 * @returns Query result with paginated weather data
 *
 * @example
 * const { data, isLoading } = useWeatherData({ page: 1, limit: 50 });
 */
export function useWeatherData(
  params?: WeatherDataParams,
  options?: Omit<
    UseQueryOptions<PaginatedResponse<WeatherData>, ApiError>,
    'queryKey' | 'queryFn'
  >
) {
  return useQuery({
    queryKey: weatherKeys.dataList(params),
    queryFn: () => weatherApi.getData(params),
    ...options,
  });
}

/**
 * useHourlyWeather hook for fetching hourly weather forecast
 *
 * @param params - Optional parameters for location and forecast days
 * @param options - Optional React Query options
 * @returns Query result with hourly weather data array
 *
 * @example
 * const { data: forecast } = useHourlyWeather({ days: 3 });
 */
export function useHourlyWeather(
  params?: HourlyWeatherParams,
  options?: Omit<UseQueryOptions<WeatherData[], ApiError>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: weatherKeys.hourlyList(params),
    queryFn: () => weatherApi.getHourlyForecast(params),
    // Weather data doesn't change fast - 30 minutes stale time
    staleTime: 30 * 60 * 1000,
    ...options,
  });
}

/**
 * useWeatherStats hook for fetching aggregated weather statistics
 *
 * @param params - Optional date range parameters
 * @param options - Optional React Query options
 * @returns Query result with weather statistics
 *
 * @example
 * const { data: stats } = useWeatherStats({ start_date: '2026-01-01', end_date: '2026-01-31' });
 */
export function useWeatherStats(
  params?: DateRangeParams,
  options?: Omit<UseQueryOptions<WeatherStats, ApiError>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: weatherKeys.statsByRange(params),
    queryFn: () => weatherApi.getStats(params),
    ...options,
  });
}
