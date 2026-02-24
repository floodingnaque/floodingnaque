export interface PredictionRequest {
  temperature: number; // Kelvin
  humidity: number; // Percentage 0-100
  precipitation: number; // mm
  wind_speed: number; // m/s
  pressure?: number; // hPa (optional)
}

/**
 * Location-based prediction request.
 * Sends coordinates and the backend fetches weather data automatically.
 */
export interface LocationPredictionRequest {
  latitude: number; // Decimal degrees
  longitude: number; // Decimal degrees
}

export interface PredictionResponse {
  prediction: 0 | 1;
  probability: number;
  risk_level: RiskLevel;
  risk_label: RiskLabel;
  confidence: number;
  model_version: string;
  features_used: string[];
  timestamp: string;
  request_id: string;
  /** Weather data fetched from API (present in location-based predictions) */
  weather_data?: {
    temperature: number; // Kelvin
    humidity: number;
    precipitation: number;
    wind_speed?: number;
    pressure?: number;
    source: string;
  };
}

export type RiskLevel = 0 | 1 | 2;
export type RiskLabel = 'Safe' | 'Alert' | 'Critical';

export interface RiskConfig {
  level: RiskLevel;
  label: RiskLabel;
  color: string;
  bgColor: string;
  icon: string;
}

export const RISK_CONFIGS: Record<RiskLevel, RiskConfig> = {
  0: {
    level: 0,
    label: 'Safe',
    color: 'text-green-600',
    bgColor: 'bg-green-100',
    icon: 'CheckCircle',
  },
  1: {
    level: 1,
    label: 'Alert',
    color: 'text-amber-600',
    bgColor: 'bg-amber-100',
    icon: 'AlertTriangle',
  },
  2: {
    level: 2,
    label: 'Critical',
    color: 'text-red-600',
    bgColor: 'bg-red-100',
    icon: 'XCircle',
  },
};
