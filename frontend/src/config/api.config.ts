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
    login: '/api/v1/auth/login',
    register: '/api/v1/auth/register',
    refresh: '/api/v1/auth/refresh',
    logout: '/api/v1/auth/logout',
    me: '/api/v1/auth/me',
  },
  predict: {
    predict: '/api/v1/predict',
    predictByLocation: '/api/v1/predict/location',
  },
  data: {
    weather: '/api/v1/data/data',
    hourly: '/api/v1/data/hourly',
  },
  alerts: {
    list: '/api/v1/alerts',
    recent: '/api/v1/alerts/recent',
  },
  sse: {
    alerts: '/api/v1/sse/alerts',
  },
  dashboard: {
    stats: '/api/v1/dashboard/stats',
  },
  export: {
    weather: '/api/v1/export/weather',
    predictions: '/api/v1/export/predictions',
  },
} as const;

/**
 * Main API configuration object
 */
export const API_CONFIG = {
  /** Base URL for API requests */
  baseUrl: import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000',
  
  /** SSE URL for real-time events */
  sseUrl: import.meta.env.VITE_SSE_URL || import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000',
  
  /** Default request timeout in milliseconds */
  timeout: 30000,
  
  /** All API endpoints */
  endpoints: API_ENDPOINTS,
} as const;

/**
 * Type-safe endpoint path builder
 */
export type EndpointKeys = keyof typeof API_ENDPOINTS;
export type EndpointPath<K extends EndpointKeys> = keyof (typeof API_ENDPOINTS)[K];

/**
 * Get the full URL for an endpoint
 */
export function getEndpointUrl<K extends EndpointKeys>(
  domain: K,
  endpoint: EndpointPath<K>
): string {
  return `${API_CONFIG.baseUrl}${API_ENDPOINTS[domain][endpoint]}`;
}

/**
 * Get the SSE URL for real-time events
 */
export function getSseUrl(endpoint: keyof typeof API_ENDPOINTS.sse): string {
  return `${API_CONFIG.sseUrl}${API_ENDPOINTS.sse[endpoint]}`;
}

export default API_CONFIG;
