/**
 * GraphQL Queries
 *
 * Typed query documents for urql. Only health + weather_data
 * are migrated initially; REST stays primary for all other endpoints.
 */

import { gql } from "urql";

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------

export const HealthQuery = gql`
  query Health {
    health {
      status
      timestamp
      version
    }
  }
`;

export interface HealthQueryResult {
  health: {
    status: string;
    timestamp: string;
    version: string;
  };
}

// ---------------------------------------------------------------------------
// Weather Data
// ---------------------------------------------------------------------------

export const WeatherDataQuery = gql`
  query WeatherData($lat: Float!, $lon: Float!, $limit: Int) {
    weather_data(latitude: $lat, longitude: $lon, limit: $limit) {
      temperature
      humidity
      precipitation
      timestamp
    }
  }
`;

export interface WeatherDataQueryResult {
  weather_data: Array<{
    temperature: number;
    humidity: number;
    precipitation: number;
    timestamp: string;
  }>;
}

export interface WeatherDataQueryVariables {
  lat: number;
  lon: number;
  limit?: number;
}
