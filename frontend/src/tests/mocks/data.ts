/**
 * Mock Data Factories
 *
 * Reusable factory functions for creating test data with sensible defaults.
 * Every factory accepts an optional `overrides` object so individual tests
 * can tweak only the fields they care about.
 */

import type {
  Alert,
  AuthTokens,
  PredictionRequest,
  PredictionResponse,
  RiskLevel,
  TokenResponse,
  User,
  WeatherData,
} from "@/types";

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

let _userId = 100;

/** Create a mock User object */
export function createMockUser(overrides: Partial<User> = {}): User {
  return {
    id: _userId++,
    email: "test@example.com",
    name: "Test User",
    role: "user",
    is_active: true,
    created_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

/** Create an admin user */
export function createMockAdmin(overrides: Partial<User> = {}): User {
  return createMockUser({ role: "admin", name: "Admin User", ...overrides });
}

/** Create mock AuthTokens (camelCase, as used by the Zustand store) */
export function createMockAuthTokens(
  overrides: Partial<AuthTokens> = {},
): AuthTokens {
  return {
    accessToken: "mock-access-token",
    refreshToken: "mock-refresh-token",
    tokenType: "Bearer",
    expiresIn: 3600,
    ...overrides,
  };
}

/** Create a mock TokenResponse (snake_case, as returned by the API) */
export function createMockTokenResponse(
  overrides: Partial<TokenResponse> = {},
): TokenResponse {
  return {
    access_token: "mock-access-token",
    refresh_token: "mock-refresh-token",
    token_type: "Bearer",
    expires_in: 3600,
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// Alerts
// ---------------------------------------------------------------------------

let _alertId = 1000;

/** Create a mock Alert */
export function createMockAlert(overrides: Partial<Alert> = {}): Alert {
  return {
    id: _alertId++,
    risk_level: 1 as RiskLevel,
    message: "Test flood alert – water level rising",
    location: "Manila, Philippines",
    latitude: 14.5995,
    longitude: 120.9842,
    triggered_at: new Date().toISOString(),
    expires_at: new Date(Date.now() + 86_400_000).toISOString(),
    acknowledged: false,
    created_at: new Date().toISOString(),
    ...overrides,
  };
}

/** Create multiple mock alerts at once */
export function createMockAlerts(
  count: number,
  overrides: Partial<Alert> = {},
): Alert[] {
  return Array.from({ length: count }, (_, i) =>
    createMockAlert({ id: _alertId + i, ...overrides }),
  );
}

// ---------------------------------------------------------------------------
// Weather
// ---------------------------------------------------------------------------

let _weatherId = 2000;

/** Create a mock WeatherData record */
export function createMockWeatherData(
  overrides: Partial<WeatherData> = {},
): WeatherData {
  return {
    id: _weatherId++,
    temperature: 298.15, // ~25 °C
    humidity: 75,
    precipitation: 5.5,
    wind_speed: 12.3,
    pressure: 1013.25,
    recorded_at: new Date().toISOString(),
    source: "OWM",
    created_at: new Date().toISOString(),
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// Prediction
// ---------------------------------------------------------------------------

/** Create a mock PredictionRequest */
export function createMockPredictionRequest(
  overrides: Partial<PredictionRequest> = {},
): PredictionRequest {
  return {
    temperature: 298.15,
    humidity: 75,
    precipitation: 10,
    wind_speed: 12,
    pressure: 1013,
    ...overrides,
  };
}

/** Create a mock PredictionResponse */
export function createMockPredictionResponse(
  overrides: Partial<PredictionResponse> = {},
): PredictionResponse {
  return {
    prediction: 1,
    probability: 0.75,
    risk_level: 1 as RiskLevel,
    risk_label: "Alert",
    confidence: 0.85,
    model_version: "v1.0.0",
    features_used: ["temperature", "humidity", "precipitation", "wind_speed"],
    timestamp: new Date().toISOString(),
    request_id: `test-req-${Date.now()}`,
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------

/** Backend dashboard response shape (as returned by /api/v1/dashboard/stats) */
export interface MockBackendDashboardResponse {
  success: boolean;
  summary: {
    weather_data: { total: number; today: number; latest: unknown };
    predictions: {
      total: number;
      today: number;
      this_week: number;
      latest: unknown;
    };
    alerts: { total: number; today: number; critical_24h: number };
    risk_distribution_30d: { safe: number; alert: number; critical: number };
  };
  generated_at: string;
  request_id: string;
}

/** Create mock dashboard statistics in the backend response format */
export function createMockDashboardStats(
  overrides: Partial<MockBackendDashboardResponse["summary"]> = {},
): MockBackendDashboardResponse {
  return {
    success: true,
    summary: {
      weather_data: { total: 5000, today: 24, latest: null },
      predictions: { total: 1234, today: 42, this_week: 200, latest: null },
      alerts: { total: 50, today: 5, critical_24h: 3 },
      risk_distribution_30d: { safe: 800, alert: 300, critical: 100 },
      ...overrides,
    },
    generated_at: new Date().toISOString(),
    request_id: "mock-request-id",
  };
}
