# Frontend Architecture

## Overview

Floodingnaque's frontend is a single-page React application that follows a **feature-based architecture**. Each feature (auth, flooding, alerts, etc.) is self-contained with its own components, hooks, and API services. Shared concerns - UI primitives, state stores, utilities - live in dedicated top-level directories.

## High-Level Diagram

```
┌───────────────────────────────────────────────────────────┐
│                        Browser                            │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ React Application                                   │  │
│  │                                                     │  │
│  │  ┌───────────┐   ┌────────────┐   ┌─────────────┐  │  │
│  │  │   Pages   │──▶│  Features  │──▶│   Hooks     │  │  │
│  │  │ (app/)    │   │ components │   │ (useQuery)  │  │  │
│  │  └───────────┘   └────────────┘   └──────┬──────┘  │  │
│  │                                          │         │  │
│  │                  ┌───────────────────┬────┴─────┐  │  │
│  │                  │                   │          │  │  │
│  │           ┌──────▼──────┐    ┌───────▼───┐ ┌───▼──────┐
│  │           │ TanStack    │    │  Zustand  │ │  API     │
│  │           │ Query Cache │    │  Stores   │ │  Client  │
│  │           └─────────────┘    └───────────┘ └───┬──────┘
│  │                                                │      │
│  └────────────────────────────────────────────────┼──────┘
│                                                   │       │
└───────────────────────────────────────────────────┼───────┘
                                                    │
                                          ┌─────────▼─────────┐
                                          │   Backend API     │
                                          │ (FastAPI / SSE)   │
                                          └───────────────────┘
```

## Data Flow

```
User Action
    │
    ▼
Component ──▶ Hook (useQuery / useMutation)
                 │
                 ├──▶ API Service ──▶ api-client (Axios) ──▶ Backend
                 │                         │
                 │                    Token injection
                 │                    401 → auto refresh
                 │
                 └──▶ Zustand Store (client-only state)
                         │
                         ▼
                    Re-render via selector hooks
```

### Server State - TanStack Query

All data fetched from the backend flows through React Query:

- **Queries** (`useQuery`) - read operations with automatic caching, stale-while-revalidate, and background refetch.
- **Mutations** (`useMutation`) - write operations that invalidate related queries on success.
- **Configuration** - `staleTime: 5 min`, `gcTime: 10 min`, `retry: 1` (set in `QueryProvider`).

Each feature defines its own hooks that wrap React Query. For example, `usePrediction()` in `features/flooding/hooks/` calls `predictionApi.predict()` and manages cache keys internally.

### Client State - Zustand

Three stores handle state that does **not** come from the API:

| Store | File | Persisted | Key State |
|-------|------|-----------|-----------|
| `useAuthStore` | `state/stores/authStore.ts` | Yes (localStorage) | `user`, `accessToken`, `refreshToken`, `isAuthenticated` |
| `useAlertStore` | `state/stores/alertStore.ts` | No | `alerts[]`, `unreadCount`, `connectionStatus` |
| `useUIStore` | `state/stores/uiStore.ts` | Yes (localStorage) | `sidebarOpen`, `sidebarCollapsed`, `theme` |

Selector hooks (e.g., `useUser()`, `useTheme()`, `useLiveAlerts()`) are exported from `state/stores/index.ts` to minimize re-renders.

## Authentication Flow

```
1. User submits LoginForm
       │
       ▼
2. authApi.login(credentials)
       │
       ▼
3. Backend returns { accessToken, refreshToken, user }
       │
       ▼
4. authStore stores tokens + user (persisted to localStorage)
       │
       ▼
5. Axios request interceptor attaches Authorization: Bearer <token>
       │
       ▼
6. On 401 response:
       ├── Attempt silent refresh (authApi.refresh)
       ├── If refresh succeeds → retry original request
       └── If refresh fails → authStore.logout() → redirect to /login
```

`ProtectedRoute` checks `authStore.isAuthenticated` and redirects unauthenticated users to `/login`.

## Real-Time Updates (SSE)

```
useAlertStream() hook
       │
       ▼
EventSource connects to VITE_SSE_URL/alerts
       │
       ├── 'alert' event  → alertStore.addAlert(data)
       ├── 'heartbeat'    → update connectionStatus = 'connected'
       └── error / close  → connectionStatus = 'disconnected'
                            auto-reconnect with exponential backoff
```

- `LiveAlertsBanner` shows unread count from `alertStore`.
- `ConnectionStatus` indicator in the header reflects the SSE connection state.

## Routing

| Route | Page | Auth |
|-------|------|------|
| `/login` | Login / Register | Public |
| `/` | Dashboard | Protected |
| `/predict` | Flood Prediction | Protected |
| `/alerts` | Alert Management | Protected |
| `/history` | Weather History | Protected |
| `/reports` | Report Generation | Protected |
| `/settings` | User Settings | Protected |
| `/admin` | Admin Panel | Protected |
| `*` | 404 Not Found | - |

All protected routes are wrapped in `<ProtectedRoute> → <Layout>`. Pages are **lazy-loaded** via `React.lazy()` for code-splitting.

### Layout Structure

```
<ProtectedRoute>
  <Layout>                    ← sidebar + header + SSE alerts
    <Suspense fallback>
      <Outlet />              ← page component
    </Suspense>
  </Layout>
</ProtectedRoute>
```

## API Layer

All HTTP requests go through `src/lib/api-client.ts`, a configured Axios instance that:

1. **Injects the auth token** via a request interceptor.
2. **Handles 401** by attempting a silent token refresh, queuing concurrent requests.
3. **Normalises errors** into a consistent `ApiError` shape.
4. **Provides typed helpers**: `api.get<T>()`, `api.post<T>()`, etc., that unwrap the Axios response.

Feature-level services (e.g., `alertsApi.ts`, `predictionApi.ts`) use these helpers and are the only files that import `api-client` directly.

## Error Handling

```
                    ┌─────────────────────┐
                    │   ErrorBoundary     │  ← catches render errors
                    │   + Sentry capture  │
                    └─────────┬───────────┘
                              │
               ┌──────────────┼──────────────┐
               ▼              ▼              ▼
         Route Error    API Error      Unhandled
         Boundary       (toast)        Promise
         (per-page)     (via hooks)    (Sentry)
```

- **`ErrorBoundary`** - wraps the entire app; reports to Sentry in production.
- **`RouteErrorBoundary`** - per-route boundary for graceful page-level recovery.
- **API errors** - caught in React Query hooks, shown via Sonner toasts.
- **Sentry** - `initSentry()` in `main.tsx`; `captureException()` in boundaries. No-op when `VITE_SENTRY_DSN` is empty.

## Theming

The app supports **light** and **dark** modes:

- Theme preference stored in `uiStore` (Zustand, persisted).
- `ThemeProvider` applies the `light` or `dark` class to `<html>`.
- Respects system `prefers-color-scheme` as the initial value.
- Tailwind's `dark:` variant used throughout components.

## Build & Deployment

```
npm run build
    │
    ├── tsc -b           (type-check)
    └── vite build       (bundle + tree-shake + code-split)
                │
                ▼
            dist/         (static assets)
                │
                ▼
          Vercel CDN      (auto-deploy on push to main)
```

Vercel configuration lives in `vercel.json` - SPA rewrites, security headers, immutable asset caching. See [DEPLOYMENT.md](../DEPLOYMENT.md) for full details.
