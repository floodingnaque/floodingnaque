# Floodingnaque - AI Coding Instructions

## Project Context

**Thesis project** - an academic flood prediction system for Parañaque City built for defense and publication. Prioritize reproducibility (random_state=42, deterministic splits), publication-quality outputs (300 DPI figures), and clear model provenance. The system trains a Random Forest classifier on 3,700+ official DRRMO flood records (2022–2025) with 3-level risk classification (Safe/Alert/Critical).

## Architecture

```
backend/            Flask API (Python 3.12+, Gunicorn), release 2.0.0
  app/api/          36 blueprints under /api/v1, RFC 7807 errors
    routes/         One blueprint per resource, registered in create_app()
                    Includes: predict, alerts, dashboard, users, admin_*,
                    graphql, health, performance, gis, evacuation, sse,
                    tides, webhooks, community_reports, lgu_workflow, etc.
    middleware/     auth, rate_limit, security, body_size, request_logger, logging
    schemas/        Request/response validation (prediction.py, weather.py)
  app/services/     21 modules: ModelLoader singleton, weather fallback chain,
                    risk_classifier, scheduler, celery tasks, model versioning
  app/models/       SQLAlchemy ORM - Alembic-only migrations, soft-delete pattern
  app/core/         Config dataclass, JWT/bcrypt security, RFC 7807 exceptions
  app/utils/        Caching, circuit breakers, W3C tracing, validation, metrics
    observability/  Structured JSON logging (ECS), Sentry, Prometheus, tracing,
                    correlation IDs - 5 modules
  config/           YAML training pipeline config + Pydantic schema validation
  scripts/          30+ CLI scripts (training, preprocessing, evaluation, backup)
  data/raw/         Official DRRMO flood CSV files (2022–2025)
frontend/           React 19 + TypeScript 5.9 + Vite 7
  src/app/          Page components (lazy-loaded per route in App.tsx)
  src/features/     Self-contained feature modules with barrel exports
  src/state/        Zustand stores (authStore, uiStore, alertStore)
  src/lib/          Axios API client with JWT refresh queue, cn() utility
  src/types/api/    Shared types: ApiResponse<T>, PaginatedResponse<T>
  src/components/ui/ shadcn/ui primitives (Radix + Tailwind)
compose.yaml            Base anchors - included by environment-specific files
compose.{env}.yaml      development (Supabase), staging, production overlays
compose.microservices.yaml  5-service decomposition (experimental)
```

## Key Patterns

### Backend

- **App factory**: `create_app()` in `app/api/app.py` - registers 36 blueprints, extensions, W3C tracing hooks, RFC 7807 error handlers. Entry point: `main.py` (also exposes `application` for Gunicorn). Dev startup: `start_server.ps1` from `backend/`.
- **Two config systems**: (1) `app/core/config.py` - `@dataclass Config` singleton for API runtime, reads `.env.{APP_ENV}`, validates production requirements. (2) `config/__init__.py` - YAML hierarchy (`training_config.yaml` → `{env}.yaml` → `FLOODINGNAQUE_*` env vars → resource auto-detection) for ML pipeline, validated by Pydantic models in `config/schema.py`. Supports hot-reload via SIGHUP.
- **ModelLoader singleton** (`app/services/predict.py`): Lazy-loads `.joblib` models with HMAC verification (warns if unsigned). `get_instance()`/`reset_instance()` for testability. Prediction returns `{prediction, risk_level, confidence}`.
- **RiskClassifier** (`app/services/risk_classifier.py`): Maps flood probability + precipitation + humidity → Safe/Alert/Critical. This is the core domain logic.
- **Weather fallback chain**: Meteostat → OpenWeatherMap → Google Earth Engine. Each has sync + async variants and typed dataclasses (`*_types.py`). Circuit breakers protect external calls.
- **Database**: Alembic manages all schema changes. Models use soft-delete (`is_deleted`, `deleted_at`, `soft_delete()`, `restore()`). Session via `get_db_session()` context manager. Engine uses lazy singleton with thread-safe double-checked locking. Driver: pg8000 (Windows) or psycopg2 (Linux), auto-selected by `app/utils/db_connection.py`. SSL mode auto-detected per environment (`require` in dev, `verify-full` in prod). Pool: size=3, overflow=5, recycle=1800s, pre_ping=True.
- **Slow query logging** (`app/utils/query_optimizer.py`): SQLAlchemy event listeners track queries exceeding 100ms threshold (`SLOW_QUERY_THRESHOLD_MS`). Also provides `@cached_query` decorator, `EagerLoader` helper, and `explain_query()` analysis.
- **Session storage** (`app/utils/session_config.py`): Redis in production (signed cookies, 24h TTL), filesystem fallback in dev. Cookie: `floodingnaque_session`, HttpOnly, SameSite=Lax.
- **Observability stack** (`app/utils/observability/`): Structured JSON logging (ECS format) with log sampling (`LOG_SAMPLING_RATE`, errors always pass), Sentry error tracking (`app/utils/observability/sentry.py`), Prometheus metrics at `/metrics`, distributed tracing with correlation IDs.
- **Startup health** (`app/utils/startup_health.py`): Validates env vars, ML model, database, Redis, ML stack versions on boot. Reports healthy/degraded/unhealthy per check with severity levels. Critical failures block startup.
- **Scheduler** (`app/services/scheduler.py`): APScheduler with file-based distributed lock (one Gunicorn worker). Jobs: weather ingestion (60min), smart alert evaluation (5min), expired IP purge (daily), auto-retrain check (30 days). Disabled when `CELERY_BEAT_RUNNING=true`.
- **GraphQL**: Feature-flagged (`GRAPHQL_ENABLED`) at `/graphql` with GraphiQL IDE.
- **Swagger docs**: OpenAPI 3.1.0 via Flasgger at `/apidocs` (`FEATURE_API_DOCS_ENABLED`).
- **Response compression**: Enabled via Flask-Compress.
- **API responses**: `api_success(data)`, `api_error(message, status)`, `api_created(data)` from `app/core/exceptions.py`. Never return raw dicts - always use these helpers.
- **Docker Secrets**: `get_secret("KEY")` checks `KEY_FILE` env var first, falls back to `KEY`.

### Frontend

- **Feature modules**: `src/features/{name}/` with `components/`, `hooks/`, `services/`, barrel `index.ts`. Each is self-contained - import via `@/features/{name}`. Components export skeleton loading variants (e.g., `StatsCards` + `StatsCardsSkeleton`).
- **State split**: Server state → TanStack Query hooks in feature `hooks/` (query keys use factory pattern). Client state → Zustand stores. Never mix - no Zustand for server-fetched data.
- **API client** (`src/lib/api-client.ts`): Axios with 30s timeout, automatic JWT refresh with concurrent retry queue, typed helpers that unwrap `response.data`. Endpoints in `src/config/api.config.ts`. CSRF token attached on mutating requests.
- **Zustand**: Separate `State` and `Actions` interfaces. Granular selector hooks (`useUser()`, `useIsAuthenticated()`) - never `useStore()` directly. `partialize` excludes tokens from localStorage.
- **UI**: shadcn/ui components in `src/components/ui/`, feedback components in `src/components/feedback/`. Compose with `cn()` from `src/lib/cn.ts`. Icons: `lucide-react`. Dark mode via CSS class.
- **Path alias**: `@/` → `src/` in both `vite.config.ts` and `tsconfig.json`.

### ML Training Pipeline

Progressive training demonstrates model evolution for the thesis:

| Version | Data                     | Features Added                                 |
| ------- | ------------------------ | ---------------------------------------------- |
| v1      | 2022 only (~100 records) | 5 core: temp, humidity, precip, monsoon, month |
| v2      | 2022–2023 (~270)         | + interactions: temp×humidity, saturation_risk |
| v3      | 2022–2024 (~1,100)       | + all interaction features                     |
| v4      | Full 2022–2025 (~3,700)  | + rolling features                             |
| v5      | + PAGASA merged          | + PAGASA weather station data                  |
| v6      | + external APIs          | All features combined (best model)             |

Each version saves: `.joblib` model, `.json` metadata (date, params, metrics, feature importance), feature name list. Run `scripts/compare_models.py` for cross-version comparison.

**Key training script**: `scripts/train_progressive_v6.py --grid-search --cv-folds 10`
**Data preprocessing**: `scripts/preprocess_pagasa_data.py` → `scripts/clean_raw_flood_records.py`
**Thesis figures**: `scripts/generate_thesis_report.py` (outputs 300 DPI PNGs to `reports/`)

### Docker Compose Hierarchy

`compose.yaml` defines shared YAML anchors (`x-backend-base`, `x-redis-base`, `x-postgres-base`, healthcheck templates). Environment files **include** the base via the `include` directive (requires Compose v2.20+):

- `compose.development.yaml` - Supabase-connected dev setup
- `compose.staging.yaml` - staging with `OWM_API_KEY`
- `compose.production.yaml` - full stack with PgBouncer, Nginx, monitoring profiles
- `compose.microservices.yaml` - 5-service decomposition (weather-collector :5001, ml-prediction :5002, alert-notification :5003, user-management :5004, dashboard-api :5005)
- `compose.mlflow.yaml` - MLflow tracking server
- `compose.observability.yaml` - Prometheus + Grafana + Alertmanager

Use `docker compose -f compose.{env}.yaml up -d`, never edit `compose.yaml` anchors without checking downstream files.

## Commands

```powershell
# Backend (from backend/)
pip install -r requirements.txt -r requirements-dev.txt
python main.py                                    # Dev server on :5000
.\start_server.ps1                                # PowerShell: activate venv + start server
pytest                                            # All tests (85% coverage enforced)
pytest tests/unit/ -m "not slow"                  # Fast unit tests only
pytest tests/snapshots/ --snapshot-update -v       # Update syrupy snapshots
alembic revision --autogenerate -m "description"  # New migration
alembic upgrade head                              # Apply migrations

# Frontend (from frontend/)
npm install
npm run dev                                       # Dev server on :3000 (proxies /api → :5000)
npm run test                                      # Vitest (75% coverage threshold)
npm run e2e                                       # Playwright
npm run lint                                      # ESLint

# ML Training (from backend/)
python scripts/preprocess_pagasa_data.py                              # Preprocess raw DRRMO data
python scripts/train_progressive_v6.py --grid-search --cv-folds 10   # Progressive training v1→v6
python scripts/generate_thesis_report.py                              # 300 DPI thesis figures
python scripts/compare_models.py                                      # Cross-version comparison
python scripts/validate_model.py                                      # Model validation

# Docker
docker compose up -d --build                      # Local dev (PostgreSQL + Redis + backend)
docker compose -f compose.development.yaml up -d  # Dev with Supabase
docker compose watch                              # Hot-reload (Compose v2.22+)

# Quality
pre-commit run --all-files    # black, isort, flake8, mypy, bandit, eslint, tsc, commitizen
```

## Testing

- **Backend**: pytest with `--strict-markers`. Markers: `unit`, `integration`, `security`, `load`, `model`, `property`, `contract`, `snapshot`, `negative`. Fixtures in `tests/fixtures/` (6 modules: `mock_models`, `mock_services`, `database`, `sample_data`, `infrastructure`, `security_performance`). Session-scoped `app` fixture uses in-memory SQLite with auth bypass. Always call `ModelLoader.reset_instance()` in teardown.
- **Frontend**: Vitest + Testing Library + MSW 2. Use `customRender()` from `src/test/utils.tsx` (wraps `QueryClientProvider` + `MemoryRouter` + `userEvent`). Hook tests use `renderHook()` + `createWrapper()`. MSW handlers in `src/tests/mocks/`. Override per-test with `server.use(http.get(...))`.
- **E2E**: Playwright in `frontend/e2e/`.

## Conventions

- **Commits**: Conventional Commits enforced (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`).
- **Python**: black (line-length 120), isort (black profile), flake8 (max-complexity 15), mypy strict on `app/`, bandit for security.
- **TypeScript**: strict mode, `noUnusedLocals`/`noUnusedParameters`, ESLint.
- **Env vars**: API runtime: `APP_ENV` + `.env.*`. Training: `FLOODINGNAQUE_*` prefix. Feature flags: `FLOODINGNAQUE_FLAG_*`. Frontend: `VITE_*`.
- **Branching**: `main`/`develop` + feature branches. CI on both + PRs.
- **New API route**: Create blueprint in `app/api/routes/`, register in `create_app()`. Apply decorators: `@require_api_key`, `@rate_limit_with_burst`, `@validate_request_size`. Return via `api_success()`/`api_error()`.
- **New frontend feature**: Create `src/features/{name}/` with `components/`, `hooks/`, `services/`, `index.ts` barrel. Add lazy route in `App.tsx`. Server data via TanStack Query hook, not Zustand.
- **Database changes**: Alembic migration only - `alembic revision --autogenerate -m "msg"` then `alembic upgrade head`. Never raw DDL.
- **Model changes**: Retrain via progressive pipeline, compare with `compare_models.py`, regenerate thesis report.
