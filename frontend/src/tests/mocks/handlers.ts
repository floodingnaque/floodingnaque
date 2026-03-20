/**
 * MSW (Mock Service Worker) Request Handlers
 *
 * Defines mock API handlers for all backend endpoints.
 * Used in tests and development for consistent API mocking.
 */

import { API_CONFIG } from "@/config/api.config";
import { delay, http, HttpResponse } from "msw";

const baseUrl = API_CONFIG.baseUrl;

// ============================================================================
// Mock Data Factories
// ============================================================================

/** Generate a mock user */
export const createMockUser = (overrides = {}) => ({
  id: 1,
  email: "test@example.com",
  name: "Test User",
  role: "user" as const,
  is_active: true,
  created_at: "2026-01-01T00:00:00Z",
  ...overrides,
});

/** Generate mock tokens */
export const createMockTokens = () => ({
  access_token: "mock-access-token",
  refresh_token: "mock-refresh-token",
  token_type: "Bearer" as const,
  expires_in: 3600,
});

/** Generate a mock alert */
export const createMockAlert = (overrides = {}) => ({
  id: Math.floor(Math.random() * 1000),
  risk_level: 1 as const,
  message: "Test flood alert",
  location: "Test Location",
  latitude: 14.5995,
  longitude: 120.9842,
  triggered_at: new Date().toISOString(),
  expires_at: new Date(Date.now() + 86400000).toISOString(),
  acknowledged: false,
  created_at: new Date().toISOString(),
  ...overrides,
});

/** Generate mock prediction response */
export const createMockPrediction = (overrides = {}) => ({
  prediction: 1 as const,
  probability: 0.75,
  risk_level: 1 as const,
  risk_label: "Alert" as const,
  confidence: 0.85,
  model_version: "v1.0.0",
  features_used: ["temperature", "humidity", "precipitation", "wind_speed"],
  timestamp: new Date().toISOString(),
  request_id: "test-request-id",
  ...overrides,
});

/** Generate mock weather data */
export const createMockWeatherData = (overrides = {}) => ({
  id: Math.floor(Math.random() * 1000),
  temperature: 298.15,
  humidity: 75,
  precipitation: 5.5,
  wind_speed: 12.3,
  pressure: 1013.25,
  recorded_at: new Date().toISOString(),
  ...overrides,
});

/** Generate mock dashboard stats in the backend response format */
export const createMockDashboardStats = () => ({
  success: true,
  summary: {
    weather_data: { total: 5000, today: 24, latest: null },
    predictions: { total: 1234, today: 42, this_week: 200, latest: null },
    alerts: { total: 50, today: 5, critical_24h: 3 },
    risk_distribution_30d: { safe: 800, alert: 300, critical: 100 },
  },
  generated_at: new Date().toISOString(),
  request_id: "mock-request-id",
});

// ============================================================================
// Auth Handlers
// ============================================================================

export const authHandlers = [
  // Login
  http.post(`${baseUrl}/api/v1/auth/login`, async ({ request }) => {
    await delay(100);
    const body = (await request.json()) as { email: string; password: string };

    if (body.email === "test@example.com" && body.password === "password123") {
      return HttpResponse.json(createMockTokens());
    }

    return HttpResponse.json(
      { code: "INVALID_CREDENTIALS", message: "Invalid email or password" },
      { status: 401 },
    );
  }),

  // Register
  http.post(`${baseUrl}/api/v1/auth/register`, async ({ request }) => {
    await delay(100);
    const body = (await request.json()) as {
      email: string;
      password: string;
      name: string;
    };

    if (body.email === "existing@example.com") {
      return HttpResponse.json(
        { code: "EMAIL_EXISTS", message: "Email already registered" },
        { status: 409 },
      );
    }

    return HttpResponse.json(createMockTokens(), { status: 201 });
  }),

  // Get current user
  http.get(`${baseUrl}/api/v1/auth/me`, async ({ request }) => {
    await delay(50);
    const authHeader = request.headers.get("Authorization");

    if (!authHeader || !authHeader.startsWith("Bearer ")) {
      return HttpResponse.json(
        { code: "UNAUTHORIZED", message: "Not authenticated" },
        { status: 401 },
      );
    }

    return HttpResponse.json(createMockUser());
  }),

  // Refresh token
  http.post(`${baseUrl}/api/v1/auth/refresh`, async () => {
    await delay(50);
    return HttpResponse.json(createMockTokens());
  }),

  // Logout
  http.post(`${baseUrl}/api/v1/auth/logout`, async () => {
    await delay(50);
    return HttpResponse.json({ message: "Logged out successfully" });
  }),
];

// ============================================================================
// Prediction Handlers
// ============================================================================

export const predictionHandlers = [
  http.post(`${baseUrl}/api/v1/predict`, async ({ request }) => {
    await delay(150);
    const body = (await request.json()) as {
      temperature: number;
      humidity: number;
      precipitation: number;
      wind_speed: number;
    };

    // Calculate risk based on input
    let riskLevel: 0 | 1 | 2 = 0;
    let riskLabel: "Safe" | "Alert" | "Critical" = "Safe";
    let probability = 0.2;

    if (body.precipitation > 50 || body.humidity > 90) {
      riskLevel = 2;
      riskLabel = "Critical";
      probability = 0.9;
    } else if (body.precipitation > 20 || body.humidity > 70) {
      riskLevel = 1;
      riskLabel = "Alert";
      probability = 0.6;
    }

    return HttpResponse.json(
      createMockPrediction({
        risk_level: riskLevel,
        risk_label: riskLabel,
        probability,
      }),
    );
  }),
];

// ============================================================================
// Alerts Handlers
// ============================================================================

export const alertsHandlers = [
  // Get alerts list
  http.get(`${baseUrl}/api/v1/alerts`, async ({ request }) => {
    await delay(100);
    const url = new URL(request.url);
    const page = parseInt(url.searchParams.get("page") || "1");
    const limit = parseInt(url.searchParams.get("limit") || "10");

    const alerts = Array.from({ length: limit }, (_, i) =>
      createMockAlert({ id: (page - 1) * limit + i + 1 }),
    );

    return HttpResponse.json({
      success: true,
      data: alerts,
      total: 50,
      page,
      limit,
      pages: Math.ceil(50 / limit),
      request_id: "test-request-id",
    });
  }),

  // Get recent alerts
  http.get(`${baseUrl}/api/v1/alerts/recent`, async ({ request }) => {
    await delay(50);
    const url = new URL(request.url);
    const limit = parseInt(url.searchParams.get("limit") || "10");

    const alerts = Array.from({ length: Math.min(limit, 5) }, (_, i) =>
      createMockAlert({ id: i + 1 }),
    );

    return HttpResponse.json({
      success: true,
      data: alerts,
      request_id: "test-request-id",
    });
  }),

  // Get alert history
  http.get(`${baseUrl}/api/v1/alerts/history`, async () => {
    await delay(100);

    const alerts = Array.from({ length: 10 }, (_, i) =>
      createMockAlert({ id: i + 1 }),
    );

    return HttpResponse.json({
      alerts,
      summary: {
        total: 100,
        by_risk_level: { 0: 50, 1: 35, 2: 15 },
        acknowledged: 75,
        pending: 25,
      },
    });
  }),

  // Acknowledge alert
  http.patch(`${baseUrl}/api/v1/alerts/:id/acknowledge`, async ({ params }) => {
    await delay(50);
    return HttpResponse.json({
      success: true,
      data: null,
      message: `Alert ${params.id} acknowledged`,
      request_id: "test-request-id",
    });
  }),

  // Acknowledge all alerts
  http.post(`${baseUrl}/api/v1/alerts/acknowledge-all`, async () => {
    await delay(100);
    return HttpResponse.json({
      success: true,
      data: { acknowledged_count: 5 },
      request_id: "test-request-id",
    });
  }),
];

// ============================================================================
// Weather Handlers
// ============================================================================

export const weatherHandlers = [
  // Get weather data (also handles stats when ?stats=true)
  http.get(`${baseUrl}/api/v1/data/data`, async ({ request }) => {
    await delay(100);
    const url = new URL(request.url);
    const isStats = url.searchParams.get("stats") === "true";

    // If requesting stats, return aggregated statistics
    if (isStats) {
      return HttpResponse.json({
        success: true,
        data: {
          avg_temperature: 298.15,
          max_temperature: 305.15,
          min_temperature: 293.15,
          avg_humidity: 75,
          total_precipitation: 150.5,
          avg_wind_speed: 12.3,
          data_points: 1000,
          date_range: {
            start: "2026-01-01",
            end: "2026-01-31",
          },
        },
      });
    }

    // Otherwise return paginated weather data
    const page = parseInt(url.searchParams.get("page") || "1");
    const limit = parseInt(url.searchParams.get("limit") || "50");

    const data = Array.from({ length: limit }, (_, i) =>
      createMockWeatherData({ id: (page - 1) * limit + i + 1 }),
    );

    return HttpResponse.json({
      success: true,
      data,
      total: 1000,
      page,
      limit,
      pages: Math.ceil(1000 / limit),
      request_id: "test-request-id",
    });
  }),

  // Get hourly forecast
  http.get(`${baseUrl}/api/v1/data/hourly`, async ({ request }) => {
    await delay(100);
    const url = new URL(request.url);
    const days = parseInt(url.searchParams.get("days") || "1");
    const hoursCount = days * 24;

    const data = Array.from({ length: hoursCount }, (_, i) =>
      createMockWeatherData({
        id: i + 1,
        recorded_at: new Date(Date.now() + i * 3600000).toISOString(),
      }),
    );

    return HttpResponse.json({
      success: true,
      data,
    });
  }),
];

// ============================================================================
// Dashboard Handlers
// ============================================================================

export const dashboardHandlers = [
  http.get(`${baseUrl}/api/v1/dashboard/stats`, async () => {
    await delay(100);
    return HttpResponse.json(createMockDashboardStats());
  }),
];

// ============================================================================
// Export Handlers
// ============================================================================

export const exportHandlers = [
  // Export predictions (PDF, CSV, or JSON) – matches GET /api/v1/export/predictions?format=...
  http.get(`${baseUrl}/api/v1/export/predictions`, async ({ request }) => {
    await delay(200);
    const url = new URL(request.url);
    const format = url.searchParams.get("format") ?? "json";

    if (format === "pdf") {
      const pdfContent = "%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n";
      const blob = new Blob([pdfContent], { type: "application/pdf" });
      return new HttpResponse(blob, {
        headers: {
          "Content-Type": "application/pdf",
          "Content-Disposition":
            'attachment; filename="predictions_report.pdf"',
        },
      });
    }

    if (format === "csv") {
      const csvContent =
        "id,timestamp,prediction,risk_level,confidence\n1,2026-01-01T00:00:00,0.85,high,0.92\n";
      const blob = new Blob([csvContent], { type: "text/csv" });
      return new HttpResponse(blob, {
        headers: {
          "Content-Type": "text/csv",
          "Content-Disposition":
            'attachment; filename="predictions_report.csv"',
        },
      });
    }

    // JSON (default)
    return HttpResponse.json({
      data: [
        {
          id: 1,
          timestamp: "2026-01-01T00:00:00",
          prediction: 0.85,
          risk_level: "high",
          confidence: 0.92,
        },
      ],
      count: 1,
      format: "json",
    });
  }),

  // Export alerts (PDF, CSV, or JSON) – matches GET /api/v1/export/alerts?format=...
  http.get(`${baseUrl}/api/v1/export/alerts`, async ({ request }) => {
    await delay(200);
    const url = new URL(request.url);
    const format = url.searchParams.get("format") ?? "json";

    if (format === "pdf") {
      const pdfContent = "%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n";
      const blob = new Blob([pdfContent], { type: "application/pdf" });
      return new HttpResponse(blob, {
        headers: {
          "Content-Type": "application/pdf",
          "Content-Disposition": 'attachment; filename="alerts_report.pdf"',
        },
      });
    }

    if (format === "csv") {
      const csvContent =
        "id,timestamp,risk_level,message,location\n1,2026-01-01T00:00:00,1,Test alert,Manila\n";
      const blob = new Blob([csvContent], { type: "text/csv" });
      return new HttpResponse(blob, {
        headers: {
          "Content-Type": "text/csv",
          "Content-Disposition": 'attachment; filename="alerts_report.csv"',
        },
      });
    }

    // JSON (default)
    return HttpResponse.json({
      data: [
        {
          id: 1,
          timestamp: "2026-01-01T00:00:00",
          risk_level: 1,
          message: "Test alert",
          location: "Manila",
        },
      ],
      count: 1,
      format: "json",
    });
  }),

  // Export weather (PDF, CSV, or JSON) – matches GET /api/v1/export/weather?format=...
  http.get(`${baseUrl}/api/v1/export/weather`, async ({ request }) => {
    await delay(200);
    const url = new URL(request.url);
    const format = url.searchParams.get("format") ?? "json";

    if (format === "pdf") {
      const pdfContent = "%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n";
      const blob = new Blob([pdfContent], { type: "application/pdf" });
      return new HttpResponse(blob, {
        headers: {
          "Content-Type": "application/pdf",
          "Content-Disposition": 'attachment; filename="weather_report.pdf"',
        },
      });
    }

    if (format === "csv") {
      const csvContent =
        "id,timestamp,temperature,humidity,precipitation\n1,2026-01-01T00:00:00,28.5,75.0,12.3\n";
      const blob = new Blob([csvContent], { type: "text/csv" });
      return new HttpResponse(blob, {
        headers: {
          "Content-Type": "text/csv",
          "Content-Disposition": 'attachment; filename="weather_report.csv"',
        },
      });
    }

    // JSON (default)
    return HttpResponse.json({
      data: [
        {
          id: 1,
          timestamp: "2026-01-01T00:00:00",
          temperature: 28.5,
          humidity: 75.0,
          precipitation: 12.3,
        },
      ],
      count: 1,
      format: "json",
    });
  }),
];

// ============================================================================
// Combined Handlers
// ============================================================================

export const handlers = [
  ...authHandlers,
  ...predictionHandlers,
  ...alertsHandlers,
  ...weatherHandlers,
  ...dashboardHandlers,
  ...exportHandlers,
];

export default handlers;
