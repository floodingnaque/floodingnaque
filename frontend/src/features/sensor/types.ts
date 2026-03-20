/**
 * Sensor Feature Types
 *
 * Type definitions for sensor data input and weather observations.
 */

/** Payload for creating a new weather observation via POST /api/v1/data/data */
export interface SensorSubmitPayload {
  temperature?: number; // Kelvin
  humidity?: number; // 0-100%
  precipitation?: number; // mm
  wind_speed?: number; // m/s
  pressure?: number; // hPa
  source?: string;
  timestamp?: string; // ISO 8601
}

/** A single hourly weather reading from GET /api/v1/data/hourly */
export interface HourlyReading {
  timestamp: string;
  temperature: number;
  humidity: number;
  precipitation: number;
  wind_speed: number | null;
  pressure: number | null;
  source: string;
}

/** Response from GET /api/v1/data/hourly */
export interface HourlyResponse {
  data: HourlyReading[];
  count: number;
  start_date: string;
  end_date: string;
  request_id: string;
}

/** Form values (user-facing, Celsius) before conversion to Kelvin payload */
export interface SensorFormValues {
  date: string;
  time: string;
  rainfall: string;
  riverLevel: string;
  temperature: string;
  humidity: string;
  pressure: string;
  windSpeed: string;
  source: string;
}

/** Static data source metadata for the Data Sources tab */
export interface DataSourceInfo {
  name: string;
  icon: React.ElementType;
  status: "online" | "delayed" | "offline";
  lastSync: string;
}
