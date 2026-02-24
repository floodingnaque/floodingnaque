# Floodingnaque — Frontend

Real-time flood prediction and alert dashboard for Parañaque City, Philippines.

## Tech Stack

| Layer          | Technology                                |
| -------------- | ----------------------------------------- |
| Framework      | React 19 + TypeScript 5.9                 |
| Build          | Vite 7                                    |
| Server State   | TanStack Query (React Query) v5           |
| Client State   | Zustand v5                                |
| Styling        | Tailwind CSS 4 + shadcn/ui                |
| Routing        | React Router 7                            |
| Forms          | React Hook Form + Zod                     |
| Charts         | Recharts 3                                |
| Maps           | Leaflet + React Leaflet                   |
| HTTP           | Axios                                     |
| Testing        | Vitest + Testing Library + Playwright      |
| Monitoring     | Sentry (optional, via env var)            |

## Getting Started

### Prerequisites

- **Node.js 18+** (LTS recommended)
- Backend running at `http://localhost:5000` (see `backend/README.md`)

### Installation

```bash
cd frontend
npm install
cp .env.example .env.development   # adjust values as needed
npm run dev                         # http://localhost:3000
```

### Available Scripts

| Command               | Description                        |
| --------------------- | ---------------------------------- |
| `npm run dev`         | Start development server (port 3000) |
| `npm run build`       | Build for production (`tsc` + Vite) |
| `npm run preview`     | Preview production build locally   |
| `npm run test`        | Run unit tests (Vitest)            |
| `npm run test:watch`  | Run tests in watch mode            |
| `npm run test:ui`     | Open Vitest UI                     |
| `npm run test:coverage` | Run tests with coverage report   |
| `npm run lint`        | Lint with ESLint                   |
| `npm run e2e`         | Run Playwright end-to-end tests    |
| `npm run e2e:headed`  | Run e2e tests in headed browser    |
| `npm run e2e:ui`      | Open Playwright UI                 |

## Project Structure

```
src/
├── app/               # Page components (file-based routing convention)
│   ├── layout.tsx     #   App shell (sidebar, header, SSE alerts)
│   ├── page.tsx       #   Dashboard (index route)
│   ├── login/         #   /login
│   ├── predict/       #   /predict
│   ├── alerts/        #   /alerts
│   ├── history/       #   /history
│   ├── reports/       #   /reports
│   ├── settings/      #   /settings
│   └── admin/         #   /admin
├── components/
│   ├── feedback/      # ErrorBoundary, LoadingSpinner, EmptyState, etc.
│   └── ui/            # shadcn/ui primitives (Button, Card, Dialog…)
├── config/            # API endpoint config
├── features/          # Feature modules (see below)
│   ├── alerts/        #   components · hooks · services
│   ├── auth/          #   LoginForm · ProtectedRoute · useAuth
│   ├── dashboard/     #   StatsCards · RecentActivity · useDashboard
│   ├── flooding/      #   PredictionForm · RiskDisplay · usePrediction
│   ├── map/           #   FloodMap · RiskMarkers · LocationPicker
│   ├── reports/       #   ReportGenerator · useReports
│   └── weather/       #   WeatherChart · WeatherTable · useWeather
├── hooks/             # Shared hooks (useMediaQuery, useIsMobile…)
├── lib/               # Utilities (api-client, sentry, security, toast)
├── providers/         # QueryProvider · ThemeProvider
├── state/             # Zustand stores (auth, alerts, UI)
├── styles/            # Global CSS
├── test/              # Test setup + render helpers
├── tests/             # Integration tests + MSW mocks
└── types/             # TypeScript type definitions (api/)
```

Each **feature module** is self-contained with its own `components/`, `hooks/`, and `services/` directories, plus a barrel `index.ts`.

## Environment Variables

Copy `.env.example` to `.env.development` for local dev, or `.env.local` for overrides.

| Variable                  | Description                          | Default                | Required |
| ------------------------- | ------------------------------------ | ---------------------- | -------- |
| `VITE_API_BASE_URL`       | Backend API URL                      | `http://localhost:5000`| Yes      |
| `VITE_SSE_URL`            | SSE endpoint URL                     | `http://localhost:5000/api/v1/sse` | Yes |
| `VITE_APP_NAME`           | Application name                     | `Floodingnaque`        | No       |
| `VITE_APP_VERSION`        | App version tag                      | `1.0.0`                | No       |
| `VITE_MAP_DEFAULT_LAT`    | Map center latitude                  | `14.4793`              | No       |
| `VITE_MAP_DEFAULT_LNG`    | Map center longitude                 | `121.0198`             | No       |
| `VITE_MAP_DEFAULT_ZOOM`   | Map default zoom level               | `13`                   | No       |
| `VITE_ENABLE_SSE`         | Enable live alert stream             | `true`                 | No       |
| `VITE_SENTRY_DSN`         | Sentry error tracking DSN            | —                      | No       |
| `VITE_SENTRY_ENVIRONMENT` | Sentry environment tag               | `production`           | No       |

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for Vercel deployment, monitoring setup, and rollback.

## Documentation

| Document | Description |
| -------- | ----------- |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Production deployment & monitoring |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Development workflow & coding guidelines |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System architecture & data flow |
| [docs/API.md](docs/API.md) | Backend API integration reference |
| [CHANGELOG.md](CHANGELOG.md) | Release history |

## License

See the root [LICENSE](../LICENSE) file.
