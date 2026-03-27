/**
 * API Configuration for Floodingnaque Frontend
 *
 * Centralizes all API-related configuration including base URLs,
 * timeouts, and endpoint definitions.
 */

/**
 * API Endpoints organized by feature domain
 */
export const API_ENDPOINTS = {
  auth: {
    login: "/api/v1/auth/login",
    register: "/api/v1/auth/register",
    refresh: "/api/v1/auth/refresh",
    logout: "/api/v1/auth/logout",
    me: "/api/v1/auth/me",
    passwordResetRequest: "/api/v1/auth/password-reset/request",
    passwordResetConfirm: "/api/v1/auth/password-reset/confirm",
  },
  users: {
    reputation: "/api/v1/users/me/reputation",
    recalculateReputation: "/api/v1/users/me/reputation/recalculate",
    leaderboard: "/api/v1/users/reputation/leaderboard",
  },
  predict: {
    predict: "/api/v1/predict",
    predictByLocation: "/api/v1/predict/location",
    forecastMap: "/api/v1/predict/forecast-map",
    simulate: "/api/v1/predict/simulate",
  },
  data: {
    weather: "/api/v1/data/data",
    hourly: "/api/v1/data/hourly",
    reliability: "/api/v1/aggregation/reliability",
  },
  alerts: {
    list: "/api/v1/alerts",
    recent: "/api/v1/alerts/recent",
    simulateSms: "/api/v1/alerts/simulate-sms",
    coverage: "/api/v1/alerts/coverage",
    smsDeliveryWebhook: "/api/v1/alerts/sms/delivery-status",
  },
  sse: {
    alerts: "/api/v1/sse/alerts",
  },
  dashboard: {
    stats: "/api/v1/dashboard/stats",
  },
  health: {
    status: "/api/v1/health",
    live: "/api/v1/health/live",
  },
  predictions: {
    list: "/api/v1/predictions",
    stats: "/api/v1/predictions/stats",
    recent: "/api/v1/predictions/recent",
  },
  tides: {
    current: "/api/v1/tides/current",
    extremes: "/api/v1/tides/extremes",
    prediction: "/api/v1/tides/prediction",
    status: "/api/v1/tides/status",
  },
  pagasa: {
    precipitation: "/api/v1/pagasa/precipitation",
    barangayPrecipitation: "/api/v1/pagasa/precipitation",
    advisory: "/api/v1/pagasa/advisory",
    barangays: "/api/v1/pagasa/barangays",
    status: "/api/v1/pagasa/status",
  },
  gis: {
    hazardMap: "/api/v1/gis/hazard-map",
    elevation: "/api/v1/gis/elevation",
    drainage: "/api/v1/gis/drainage",
    barangayDetail: "/api/v1/gis/barangay",
    barangays: "/api/v1/gis/barangays",
    floodZones: "/api/v1/gis/flood-zones",
    evacuationCenters: "/api/v1/gis/evacuation-centers",
    floodDepth: "/api/v1/gis/flood-depth",
    invalidateCache: "/api/v1/gis/barangays/invalidate-cache",
  },
  lgu: {
    incidents: "/api/v1/lgu/incidents",
    incidentStats: "/api/v1/lgu/incidents/stats",
    incidentAnalytics: "/api/v1/lgu/incidents/analytics",
    aar: "/api/v1/lgu/aar",
    broadcasts: "/api/v1/lgu/broadcasts",
  },
  models: {
    list: "/api/models",
    version: "/api/version",
    history: "/api/models/history",
    featureImportance: "/api/models/feature-importance",
    calibration: "/api/models/calibration",
  },
  export: {
    weather: "/api/v1/export/weather",
    weatherCount: "/api/v1/export/weather/count",
    predictions: "/api/v1/export/predictions",
    predictionsCount: "/api/v1/export/predictions/count",
    alerts: "/api/v1/export/alerts",
    alertsCount: "/api/v1/export/alerts/count",
    modelMetrics: "/api/v1/export/model-metrics",
    disasterPreparedness: "/api/v1/export/disaster-preparedness",
  },
  admin: {
    users: "/api/v1/admin/users",
    logs: "/api/v1/admin/logs",
    logStats: "/api/v1/admin/logs/stats",
    logsBulkDelete: "/api/v1/admin/logs/bulk-delete",
    storage: "/api/v1/admin/logs/storage",
    storageCleanupCount: "/api/v1/admin/logs/storage/cleanup-count",
    purgeDeleted: "/api/v1/admin/logs/purge-deleted",
    models: "/api/v1/admin/models",
    modelRetrain: "/api/v1/admin/models/retrain",
    modelRetrainStatus: "/api/v1/admin/models/retrain/status",
    modelRollback: "/api/v1/admin/models/rollback",
    modelComparison: "/api/v1/admin/models/comparison",
    featureFlags: "/api/v1/feature-flags",
    upload: "/api/v1/upload",
    reportsBulkDelete: "/api/v1/reports/admin/bulk-delete",
    alertsBulkDelete: "/api/v1/alerts/admin/bulk-delete",
    // Security & Audit
    auditLogs: "/api/v1/admin/security/audit-logs",
    auditStats: "/api/v1/admin/security/audit-stats",
    securityPosture: "/api/v1/admin/security/security-posture",
    // Monitoring
    monitoring: "/api/v1/admin/monitoring",
    monitoringUptime: "/api/v1/admin/monitoring/uptime",
    monitoringApiResponses: "/api/v1/admin/monitoring/api-responses",
    monitoringPredictionDrift: "/api/v1/admin/monitoring/prediction-drift",
    monitoringAlertDelivery: "/api/v1/admin/monitoring/alert-delivery",
  },
  communityReports: {
    list: "/api/v1/reports",
    submit: "/api/v1/reports",
    detail: "/api/v1/reports",
    verify: "/api/v1/reports",
    confirm: "/api/v1/reports",
    flag: "/api/v1/reports",
    stats: "/api/v1/reports/stats",
    density: "/api/v1/reports/density",
  },
  evacuation: {
    centers: "/api/v1/evacuation/centers",
    nearest: "/api/v1/evacuation/nearest",
    route: "/api/v1/evacuation/route",
    alert: "/api/v1/evacuation/alert",
    capacityStream: "/api/v1/evacuation/capacity-stream",
  },
  aggregation: {
    riverReadings: "/api/v1/aggregation/river/readings",
    riverStation: "/api/v1/aggregation/river/stations",
  },
  push: {
    vapidPublicKey: "/api/v1/push/vapid-public-key",
    subscribe: "/api/v1/push/subscribe",
    unsubscribe: "/api/v1/push/unsubscribe",
  },
} as const;

/**
 * Resolve the API base URL.
 *
 * In production / staging the env var MUST be set - a hardcoded
 * localhost fallback would silently bake the wrong URL into the
 * Vite bundle.  In development, requests use the Vite proxy
 * (configured in vite.config.ts) so an empty base URL is correct.
 */
function resolveBaseUrl(): string {
  const envUrl = import.meta.env.VITE_API_BASE_URL;
  if (envUrl) return envUrl;

  if (import.meta.env.PROD) {
    throw new Error(
      "VITE_API_BASE_URL is not set. " +
        "Production / staging builds require this environment variable.",
    );
  }

  // Dev-only fallback: empty string routes through the Vite dev proxy
  // (vite.config.ts proxies /api → http://localhost:5000), avoiding
  // cross-origin issues between localhost:3000 and localhost:5000.
  return "";
}

/**
 * Main API configuration object
 */
export const API_CONFIG = {
  /** Base URL for API requests */
  baseUrl: resolveBaseUrl(),

  /** SSE URL for real-time events */
  sseUrl:
    import.meta.env.VITE_SSE_URL ||
    import.meta.env.VITE_API_BASE_URL ||
    resolveBaseUrl(),

  /** Default request timeout in milliseconds */
  timeout: 30000,

  /** Per-use-case timeout presets (ms) */
  timeouts: {
    /** Polling and dashboard endpoints - fail fast */
    polling: 10_000,
    /** Default for most requests */
    default: 30_000,
    /** Prediction and upload endpoints - allow more time */
    heavy: 60_000,
  },

  /** All API endpoints */
  endpoints: API_ENDPOINTS,
} as const;

/**
 * Type-safe endpoint path builder
 */
export type EndpointKeys = keyof typeof API_ENDPOINTS;
export type EndpointPath<K extends EndpointKeys> =
  keyof (typeof API_ENDPOINTS)[K];

/**
 * Get the full URL for an endpoint
 */
export function getEndpointUrl<K extends EndpointKeys>(
  domain: K,
  endpoint: EndpointPath<K>,
): string {
  return `${API_CONFIG.baseUrl}${API_ENDPOINTS[domain][endpoint]}`;
}

/**
 * Get the SSE URL for real-time events
 */
export function getSseUrl(endpoint: keyof typeof API_ENDPOINTS.sse): string {
  return `${API_CONFIG.sseUrl}${API_ENDPOINTS.sse[endpoint]}`;
}

/**
 * Parse and validate a numeric environment variable.
 * Returns the fallback when the value is missing or not a valid number.
 */
function safeNumericEnv(value: string | undefined, fallback: number): number {
  if (value === undefined || value === "") return fallback;
  const parsed = Number(value);
  if (Number.isNaN(parsed)) {
    console.warn(
      `[api.config] Invalid numeric env value "${value}", using fallback ${fallback}`,
    );
    return fallback;
  }
  return parsed;
}

/**
 * Map default configuration.
 * Values are validated at runtime to prevent NaN coordinates.
 */
export const MAP_CONFIG = {
  defaultLat: safeNumericEnv(import.meta.env.VITE_MAP_DEFAULT_LAT, 14.4793),
  defaultLng: safeNumericEnv(import.meta.env.VITE_MAP_DEFAULT_LNG, 121.0198),
  defaultZoom: safeNumericEnv(import.meta.env.VITE_MAP_DEFAULT_ZOOM, 13),
} as const;

export default API_CONFIG;
