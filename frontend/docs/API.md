# API Integration

This document describes how the frontend communicates with the Floodingnaque backend API.

## Configuration

All endpoint paths are defined in `src/config/api.config.ts`. The base URL comes from the `VITE_API_BASE_URL` environment variable (default: `http://localhost:5000`).

```ts
import { API_CONFIG, getEndpointUrl } from '@/config/api.config';

// Full URL for an endpoint
getEndpointUrl('auth', 'login');
// → "http://localhost:5000/api/v1/auth/login"
```

## HTTP Client

`src/lib/api-client.ts` exports a configured Axios instance with:

- **Request interceptor** — attaches `Authorization: Bearer <token>` from `authStore`.
- **Response interceptor** — on 401, silently refreshes the token and retries the original request. Concurrent requests are queued during refresh.
- **Typed helpers** — `api.get<T>()`, `api.post<T>()`, `api.put<T>()`, `api.patch<T>()`, `api.delete<T>()` that unwrap AxiosResponse and return `T` directly.
- **Timeout** — 30 seconds.

## Endpoints

### Authentication

| Method | Endpoint | Request Body | Response | Auth |
|--------|----------|-------------|----------|------|
| POST | `/api/v1/auth/login` | `LoginRequest` | `TokenResponse` | No |
| POST | `/api/v1/auth/register` | `RegisterRequest` | `TokenResponse` | No |
| POST | `/api/v1/auth/refresh` | `RefreshTokenRequest` | `TokenResponse` | No |
| POST | `/api/v1/auth/logout` | — | — | Yes |
| GET | `/api/v1/auth/me` | — | `User` | Yes |

**Types:**

```ts
interface LoginRequest {
  email: string;
  password: string;
}

interface RegisterRequest {
  email: string;
  password: string;
  name: string;
}

interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: 'Bearer';
  expires_in: number;
}

interface User {
  id: number;
  email: string;
  name: string;
  role: 'user' | 'admin';
  is_active: boolean;
  created_at: string;
  updated_at?: string;
}
```

### Flood Prediction

| Method | Endpoint | Request Body | Response | Auth |
|--------|----------|-------------|----------|------|
| POST | `/api/v1/predict` | `PredictionRequest` | `PredictionResponse` | Yes |

**Types:**

```ts
interface PredictionRequest {
  temperature: number;   // Kelvin
  humidity: number;       // 0–100 %
  precipitation: number;  // mm
  wind_speed: number;     // m/s
  pressure?: number;      // hPa (optional)
}

interface PredictionResponse {
  prediction: 0 | 1;
  probability: number;
  risk_level: 0 | 1 | 2;     // Safe | Alert | Critical
  risk_label: string;
  confidence: number;
  model_version: string;
  features_used: string[];
  timestamp: string;
  request_id: string;
}
```

### Weather Data

| Method | Endpoint | Query Params | Response | Auth |
|--------|----------|-------------|----------|------|
| GET | `/api/v1/data/data` | `WeatherDataParams` | `PaginatedResponse<WeatherData>` | Yes |
| GET | `/api/v1/data/hourly` | `HourlyWeatherParams` | `WeatherData[]` | Yes |

**Types:**

```ts
interface WeatherData {
  id: number;
  temperature: number;
  humidity: number;
  precipitation: number;
  wind_speed: number;
  pressure: number;
  recorded_at: string;
  source: 'OWM' | 'Manual' | 'Meteostat' | 'Google';
  created_at: string;
}

interface WeatherDataParams {
  limit?: number;
  page?: number;
  sort_by?: string;
  order?: 'asc' | 'desc';
  start_date?: string;
  end_date?: string;
  source?: string;
}
```

### Alerts

| Method | Endpoint | Query Params | Response | Auth |
|--------|----------|-------------|----------|------|
| GET | `/api/v1/alerts` | `AlertParams` | `PaginatedResponse<Alert>` | Yes |
| GET | `/api/v1/alerts/recent` | — | `Alert[]` | Yes |

**Types:**

```ts
interface Alert {
  id: number;
  risk_level: 0 | 1 | 2;
  message: string;
  location?: string;
  latitude?: number;
  longitude?: number;
  triggered_at: string;
  expires_at?: string;
  acknowledged: boolean;
  created_at: string;
  updated_at?: string;
}

interface AlertParams {
  limit?: number;
  page?: number;
  risk_level?: number;
  acknowledged?: boolean;
  start_date?: string;
  end_date?: string;
}
```

### Dashboard

| Method | Endpoint | Response | Auth |
|--------|----------|----------|------|
| GET | `/api/v1/dashboard/stats` | `DashboardStats` | Yes |

**Types:**

```ts
interface DashboardStats {
  totalPredictions: number;
  activeAlerts: number;
  highRiskAreas: number;
  systemHealth: {
    status: 'healthy' | 'degraded' | 'unhealthy';
    uptime: number;
    lastCheck: string;
  };
  recentActivity: {
    predictions24h: number;
    alertsTriggered24h: number;
    usersActive24h: number;
  };
}
```

### Export

| Method | Endpoint | Query Params | Response | Auth |
|--------|----------|-------------|----------|------|
| GET | `/api/v1/export/weather` | `ExportOptions` | Blob (file) | Yes |
| GET | `/api/v1/export/predictions` | `ExportOptions` | Blob (file) | Yes |

### Server-Sent Events (SSE)

| Endpoint | Event Types | Auth |
|----------|------------|------|
| `/api/v1/sse/alerts` | `alert`, `heartbeat`, `connection` | Yes (token as query param) |

**Event payloads:**

```ts
// 'alert' event
interface SSEAlertData {
  alert: Alert;
  timestamp: string;
}

// 'heartbeat' event
interface SSEHeartbeatData {
  timestamp: string;
  connections: number;
}

// 'connection' event
interface SSEConnectionData {
  status: 'connected' | 'disconnected';
  client_id: string;
}
```

## Common Response Wrappers

```ts
// Single resource
interface ApiResponse<T> {
  success: boolean;
  data: T;
  message?: string;
  request_id: string;
}

// Paginated list
interface PaginatedResponse<T> {
  success: boolean;
  data: T[];
  total: number;
  page: number;
  limit: number;
  pages: number;
  request_id: string;
}
```

## Error Format

All API errors are normalised to:

```ts
interface ApiError {
  code: string;
  message: string;
  status?: number;
  details?: Record<string, unknown>;
  field_errors?: FieldError[];
  retry_after?: number;
}

interface FieldError {
  field: string;
  message: string;
}
```

## Service Layer

Each feature module has an API service file that wraps `api-client`:

| Feature | Service File | Key Functions |
|---------|-------------|---------------|
| Auth | `features/auth/services/authApi.ts` | `login()`, `register()`, `refresh()`, `getMe()`, `logout()` |
| Flooding | `features/flooding/services/predictionApi.ts` | `predict()` |
| Alerts | `features/alerts/services/alertsApi.ts` | `getAlerts()`, `getRecentAlerts()` |
| Weather | `features/weather/services/weatherApi.ts` | `getWeatherData()`, `getHourlyData()` |
| Dashboard | `features/dashboard/services/dashboardApi.ts` | `getDashboardStats()` |
| Reports | `features/reports/services/reportsApi.ts` | `exportWeather()`, `exportPredictions()` |

These services are consumed by React Query hooks in each feature's `hooks/` directory.
