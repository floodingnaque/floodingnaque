# Frontend Architecture

> **Stack** — React 19 · TypeScript 5.9 · Vite 7 · Tailwind CSS 4  
> **Last updated** — February 2026

---

## Directory Layout

```
src/
├── app/                 # Page components (one folder per route)
├── assets/              # Static images and icons
├── components/
│   ├── feedback/        # Shared feedback UI (spinners, errors, modals)
│   └── ui/              # shadcn/ui primitives (button, card, dialog, …)
├── config/              # API endpoint map and base URL config
├── features/            # Feature modules (auth, dashboard, flooding, …)
│   └── <feature>/
│       ├── components/  # Feature-specific React components
│       ├── hooks/       # React-Query hooks wrapping the service layer
│       ├── services/    # API call functions using the shared Axios client
│       └── utils/       # (optional) Pure helpers
├── hooks/               # Shared custom hooks (media queries)
├── lib/                 # Core utilities (api-client, sentry, toast, security)
├── providers/           # React context providers (Query, Theme)
├── state/               # Zustand stores (auth, UI, alerts)
├── styles/              # Global CSS (Tailwind base)
├── test/                # Test helpers and MSW setup
├── tests/               # Unit / integration tests
└── types/               # TypeScript type definitions (API contracts)
```

---

## Routing

**React Router v6** with declarative `<Routes>` in `App.tsx`.  
All page components are **lazy-loaded** (`React.lazy` + `<Suspense>`).

| Path | Page | Guard |
|------|------|-------|
| `/` | `DashboardPage` | `ProtectedRoute` |
| `/predict` | `PredictPage` | `ProtectedRoute` |
| `/alerts` | `AlertsPage` | `ProtectedRoute` |
| `/history` | `HistoryPage` | `ProtectedRoute` |
| `/reports` | `ReportsPage` | `ProtectedRoute` |
| `/settings` | `SettingsPage` | `ProtectedRoute` |
| `/admin` | `AdminPage` | `ProtectedRoute` + admin role |
| `/login` | `LoginPage` | Public |
| `*` | `NotFoundFallback` | Public |

`ProtectedRoute` reads `isAuthenticated` from the Zustand auth store and redirects unauthenticated users to `/login`, preserving the intended destination in `location.state`.

---

## State Management

### Client State — Zustand

Three stores in `state/stores/`, each with granular selector hooks:

| Store | Persisted? | Purpose |
|-------|-----------|---------|
| `useAuthStore` | `localStorage` (`auth-storage`) | User profile, JWT access / refresh tokens |
| `useUIStore` | `localStorage` (`ui-storage`) | Sidebar collapsed state, light/dark theme |
| `useAlertStore` | No (ephemeral) | Live SSE alerts (max 50), unread count |

### Server State — TanStack React Query

All data fetching goes through React Query. Configuration lives in `providers/QueryProvider.tsx`:
- Stale time: **5 min**
- GC time: **10 min**
- Retry: **1 attempt**
- DevTools enabled in development

---

## Provider Hierarchy

```
<StrictMode>
  <BrowserRouter>
    <QueryProvider>          ← TanStack React Query client + DevTools
      <ThemeProvider>        ← Syncs theme from uiStore ↔ <html> class
        <App />
      </ThemeProvider>
    </QueryProvider>
  </BrowserRouter>
</StrictMode>
```

---

## Feature Modules

Each feature is self-contained under `features/<name>/` with barrel exports via `index.ts`.

### auth
- **Components**: `LoginForm`, `RegisterForm`, `ProtectedRoute`
- **Hooks**: `useAuth` — login / register / logout / profile mutations + queries
- **Service**: `authApi` — credential endpoints

### dashboard
- **Components**: `StatsCards`, `RecentActivity`, `RecentAlerts`, `QuickActions`
- **Hooks**: `useDashboardStats` (1 min stale, 5 min refetch)
- **Service**: `dashboardApi`

### flooding
- **Components**: `PredictionForm` (react-hook-form + Zod), `PredictionResult`, `RiskDisplay`
- **Hooks**: `usePrediction` (mutation)
- **Service**: `predictionApi`
- **Utils**: `temperature.ts` — Kelvin ↔ Celsius conversion

### alerts
- **Components**: `AlertCard`, `AlertList`, `AlertBadge`, `LiveAlertsBanner`, `ConnectionStatus`
- **Hooks**: `useAlerts`, `useRecentAlerts`, `useAlertHistory` (queries); `useAcknowledgeAlert`, `useAcknowledgeAll` (mutations); `useAlertStream` (SSE with auto-reconnect — max 10 attempts, 5 s delay)
- **Service**: `alertsApi`

### weather
- **Components**: `WeatherChart`, `WeatherTable`, `WeatherStatsCards`, `DateRangeFilter`
- **Hooks**: `useWeatherData`, `useHourlyWeather`, `useWeatherStats`
- **Service**: `weatherApi`

### map
- **Components**: `FloodMap` (Leaflet/react-leaflet), `RiskMarkers`, `LocationPicker`
- No hooks or services — renders geo data passed from parent

### reports
- **Components**: `ReportGenerator`
- **Hooks**: `useExportPDF`, `useExportCSV`, `useReportExport`
- **Service**: `reportsApi`

---

## Shared Components

### `components/ui/` (shadcn/ui)

20 primitives built on **Radix UI** + **class-variance-authority** + **tailwind-merge**:

`alert` · `alert-dialog` · `avatar` · `badge` · `button` · `card` · `checkbox` · `dialog` · `dropdown-menu` · `input` · `label` · `select` · `separator` · `sheet` · `skeleton` · `sonner` · `switch` · `table` · `tabs` · `visually-hidden`

### `components/feedback/`

`ErrorBoundary` · `RouteErrorBoundary` · `NotFoundFallback` · `ErrorDisplay` · `LoadingSpinner` · `LoadingSpinnerInline` · `PageLoader` · `EmptyState` · `ConnectionStatus` · `ConfirmDialog`

---

## Shared Hooks

Defined in `hooks/useMediaQuery.ts`:

| Hook | Media Query |
|------|-------------|
| `useMediaQuery(query)` | Generic CSS media query tracker |
| `useIsMobile()` | `max-width: 767px` |
| `useIsTablet()` | `min-width: 768px` |
| `useIsDesktop()` | `min-width: 1024px` |
| `usePrefersDarkMode()` | `prefers-color-scheme: dark` |
| `usePrefersReducedMotion()` | `prefers-reduced-motion: reduce` |

---

## Lib Layer

| Module | Purpose |
|--------|---------|
| `api-client.ts` | Axios instance with Bearer-token injection and 401 refresh queue |
| `utils.ts` | `cn()` Tailwind class merge, `truncate()`, `formatRelativeTime()` |
| `sentry.ts` | `initSentry()` — opt-in via `VITE_SENTRY_DSN` env var |
| `security.ts` | `sanitizeInput()` XSS defense-in-depth, URL validation |
| `toast.ts` | `showToast.success/error/info/warning` — Sonner wrapper |

---

## API Config

Defined in `config/api.config.ts`:

| Constant | Content |
|----------|---------|
| `API_CONFIG` | `baseUrl` from `VITE_API_BASE_URL`, 30 s timeout |
| `API_ENDPOINTS` | Named paths: auth, predict, data, alerts, SSE, dashboard, export |
| `getEndpointUrl(key)` | Resolves absolute endpoint URL |
| `getSseUrl()` | SSE stream URL |

---

## Type System

All API types live in `types/api/`:

| File | Key Types |
|------|-----------|
| `common.ts` | `ApiResponse<T>`, `ApiError`, `PaginatedResponse<T>`, `PaginationParams` |
| `auth.ts` | `LoginRequest`, `TokenResponse`, `User`, `UserRole` |
| `prediction.ts` | `PredictionRequest`, `PredictionResponse`, `RiskLevel` (0–2), `RISK_CONFIGS` |
| `weather.ts` | `WeatherData`, `WeatherSource`, `WeatherStats` |
| `alert.ts` | `Alert`, `SSEAlertEvent`, `AlertHistory` |
| `index.ts` | `DashboardStats`, `ExportOptions`, `ExportResponse` |

---

## Key Patterns

| Concern | Approach |
|---------|----------|
| Forms | `react-hook-form` + Zod schema validation |
| Real-time | Server-Sent Events via `useAlertStream` |
| Code splitting | `React.lazy()` per page |
| Error handling | `ErrorBoundary` (component) + Axios interceptor + Sentry |
| Notifications | Sonner toasts |
| Icons | Lucide React |
| Map | Leaflet / react-leaflet |
