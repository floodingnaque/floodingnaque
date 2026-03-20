import type { DateRangeParams, PaginationParams } from "./common";

export interface WeatherData {
  id: number;
  temperature: number;
  humidity: number;
  precipitation: number;
  wind_speed: number;
  pressure: number;
  recorded_at: string;
  source: WeatherSource;
  created_at: string;
}

export type WeatherSource = "OWM" | "Manual" | "Meteostat" | "Google";

export interface WeatherDataParams extends PaginationParams, DateRangeParams {
  source?: WeatherSource;
}

export interface HourlyWeatherParams {
  lat?: number;
  lon?: number;
  days?: number;
}

export interface WeatherStats {
  avg_temperature: number;
  avg_humidity: number;
  total_precipitation: number;
  avg_wind_speed: number;
  record_count: number;
  /** Number of records excluded from aggregation due to implausible values */
  flagged_count?: number;
}
