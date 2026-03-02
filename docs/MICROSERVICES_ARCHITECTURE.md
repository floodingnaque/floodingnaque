# Microservices Architecture — Floodingnaque

## Overview

The monolithic Flask backend has been decomposed into **5 independent microservices**, each owning a distinct bounded context of the flood prediction system. All services communicate through an **API Gateway** (nginx) for external traffic and **Redis pub/sub** for asynchronous inter-service events.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              API Gateway (nginx:80)                             │
│  /api/v1/weather/* → :5001  │  /api/v1/predict/* → :5002  │  /api/v1/alerts/*  │
│  /api/v1/auth/*    → :5004  │  /api/v1/dashboard/* → :5005                     │
└───────┬───────────────┬──────────────┬──────────────┬──────────────┬────────────┘
        │               │              │              │              │
   ┌────▼────┐    ┌─────▼─────┐  ┌─────▼─────┐  ┌────▼────┐  ┌─────▼─────┐
   │ Weather │    │    ML     │  │   Alert   │  │  User   │  │ Dashboard │
   │Collector│    │Prediction │  │Notification│  │ Mgmt   │  │    API    │
   │  :5001  │    │   :5002   │  │   :5003   │  │  :5004  │  │   :5005   │
   └────┬────┘    └─────┬─────┘  └─────┬─────┘  └────┬────┘  └─────┬─────┘
        │               │              │              │              │
        └───────────────┴──────┬───────┴──────────────┘              │
                               │                                     │
                    ┌──────────▼──────────┐               ┌──────────▼──┐
                    │   PostgreSQL :5432  │               │ Redis :6379 │
                    │   (shared DB)      │               │ (cache/pub) │
                    └────────────────────┘               └─────────────┘
```

## Services

### 1. Weather Data Collector (`services/weather-collector/`, port 5001)

| Aspect | Detail |
|--------|--------|
| **Responsibility** | Collects weather data from external APIs (Meteostat, Google Weather, PAGASA, WorldTides, MMDA) on scheduled intervals |
| **Key Routes** | `GET /api/v1/weather/current`, `POST /api/v1/weather/ingest`, `GET /api/v1/weather/tides`, `GET /api/v1/weather/data` |
| **Events Published** | `weather.data.collected`, `weather.tides.collected`, `weather.data.ingested` |
| **Scheduling** | APScheduler — weather every 15 min, tides every 60 min |

### 2. ML Prediction (`services/ml-prediction/`, port 5002)

| Aspect | Detail |
|--------|--------|
| **Responsibility** | Loads trained ML models (XGBoost, LightGBM, RandomForest), runs flood risk predictions, manages model versioning and A/B testing |
| **Key Routes** | `POST /api/v1/predict/`, `GET /api/v1/predict/recent`, `POST /api/v1/predict/batch`, `GET /api/v1/models/` |
| **Events Published** | `prediction.completed`, `model.retrain.started` |
| **Events Consumed** | `weather.data.collected` (triggers automatic prediction) |
| **Resources** | Large — CPU/memory intensive for ML inference |

### 3. Alert Notification (`services/alert-notification/`, port 5003)

| Aspect | Detail |
|--------|--------|
| **Responsibility** | Manages flood alert lifecycle, dispatches notifications via email/SMS/Slack/webhook, provides SSE stream for real-time frontend updates |
| **Key Routes** | `POST /api/v1/alerts/`, `GET /api/v1/alerts/active`, `GET /api/v1/alerts/stream` (SSE), `POST /api/v1/webhooks/` |
| **Events Published** | `alert.triggered` |
| **Events Consumed** | `prediction.completed` (auto-creates alerts for high-risk predictions) |
| **Channels** | Web push, Email (SMTP), SMS (Twilio), Slack webhook |

### 4. User Management (`services/user-management/`, port 5004)

| Aspect | Detail |
|--------|--------|
| **Responsibility** | User registration, authentication (JWT), role-based access control, profile management |
| **Key Routes** | `POST /api/v1/auth/register`, `POST /api/v1/auth/login`, `GET /api/v1/users/me`, `GET /api/v1/admin/users` |
| **Auth** | JWT access + refresh tokens, bcrypt password hashing |
| **RBAC** | Roles: `user`, `analyst`, `admin` |

### 5. Dashboard API (`services/dashboard-api/`, port 5005)

| Aspect | Detail |
|--------|--------|
| **Responsibility** | Aggregates data from all other services to power the frontend dashboard — summary views, statistics, activity feed, data export, GIS map layers |
| **Key Routes** | `GET /api/v1/dashboard/summary`, `GET /api/v1/dashboard/predictions/`, `GET /api/v1/dashboard/export/`, `GET /api/v1/dashboard/gis/risk-zones` |
| **Pattern** | Backend-for-Frontend (BFF) — makes parallel calls to downstream services |
| **Caching** | Redis with configurable TTL to reduce downstream load |

## Shared Package (`services/shared/`)

Common utilities imported by all services:

| Module | Purpose |
|--------|---------|
| `config.py` | `BaseServiceConfig` dataclass — reads env vars, Docker secrets (`_FILE` pattern), service URLs |
| `database.py` | SQLAlchemy engine singleton, `get_db_session()` context manager |
| `auth.py` | JWT creation/verification, `@require_auth` and `@require_role()` decorators, inter-service tokens |
| `health.py` | Blueprint factory for `/health`, `/health/live`, `/health/ready`, `/status` |
| `messaging.py` | `EventBus` (Redis pub/sub), `ServiceClient` (HTTP with circuit breaker + retry), client factories |
| `errors.py` | `ServiceError` hierarchy, RFC 7807 Problem Details formatting |
| `tracing.py` | W3C Trace Context propagation across services |
| `discovery.py` | `ServiceRegistry` with Redis backend, heartbeat loop |

## Communication Patterns

### Synchronous (HTTP)

Inter-service HTTP calls use the `ServiceClient` from `shared/messaging.py`:
- **Circuit breaker** (CLOSED → OPEN after 5 failures, HALF_OPEN after 30s)
- **Retry** with exponential backoff (3 attempts)
- **Timeout** (5s connect, 15s read)
- **Service authentication** via short-lived JWT (`create_service_token()`)

### Asynchronous (Redis Pub/Sub)

Event-driven communication for non-blocking workflows:

```
weather-collector  ──▶  weather.data.collected  ──▶  ml-prediction
ml-prediction      ──▶  prediction.completed    ──▶  alert-notification
alert-notification ──▶  alert.triggered         ──▶  (logged / dashboard)
```

### API Gateway (nginx)

Path-based routing with:
- **Rate limiting** — auth endpoints: 10 req/s, general API: 30 req/s, predictions: 5 req/s
- **SSE support** — unbuffered proxy for `/api/v1/alerts/stream`
- **CORS** — preflight handling for all `/api/*` routes
- **Error pages** — RFC 7807 JSON error responses for 429, 502, 503, 504
- **Request tracing** — `X-Request-ID` header propagation

## Deployment

### Development

```bash
docker compose -f compose.microservices.yaml up -d --build
```

### With Connection Pooling

```bash
docker compose -f compose.microservices.yaml --profile pgbouncer up -d
```

### Scaling Individual Services

```bash
# Scale ML prediction to 3 replicas for load
docker compose -f compose.microservices.yaml up -d --scale ml-prediction=3
```

### Environment Variables

All services share these core variables (set in `.env` or compose env):

| Variable | Required | Description |
|----------|----------|-------------|
| `POSTGRES_PASSWORD` | Yes | Database password |
| `JWT_SECRET` | Yes (prod) | Shared JWT signing secret |
| `REDIS_URL` | No | Redis connection string (default: `redis://redis:6379/0`) |
| `LOG_LEVEL` | No | Logging level (default: `INFO`) |

Service-specific variables are documented in each service's compose section.

## Fault Isolation

Each service is independently deployable and restartable. Failures are isolated:

- **Weather service down** → Predictions continue using cached data, dashboard shows stale weather
- **ML service down** → Weather collection continues, alerts use last known risk level
- **Alert service down** → Predictions complete normally, alerts queue in Redis for later delivery
- **User service down** → Dashboard and predictions work for existing authenticated sessions
- **Dashboard service down** → Individual service APIs remain fully operational

## Directory Structure

```
services/
├── shared/                          # Shared utilities package
│   ├── __init__.py
│   ├── config.py                    # BaseServiceConfig
│   ├── database.py                  # SQLAlchemy session management
│   ├── auth.py                      # JWT + RBAC decorators
│   ├── health.py                    # Health check blueprint
│   ├── messaging.py                 # EventBus + ServiceClient
│   ├── errors.py                    # Error hierarchy
│   ├── tracing.py                   # W3C Trace Context
│   └── discovery.py                 # Service registry
├── weather-collector/               # Port 5001
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   └── app/
│       ├── __init__.py
│       ├── routes/
│       │   ├── weather.py
│       │   ├── ingest.py
│       │   ├── tides.py
│       │   └── data.py
│       └── services/
│           └── collector.py
├── ml-prediction/                   # Port 5002
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   └── app/
│       ├── __init__.py
│       ├── routes/
│       │   ├── predict.py
│       │   ├── models.py
│       │   └── batch.py
│       └── services/
│           └── predictor.py
├── alert-notification/              # Port 5003
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   └── app/
│       ├── __init__.py
│       ├── routes/
│       │   ├── alerts.py
│       │   ├── sse.py
│       │   ├── webhooks.py
│       │   └── notifications.py
│       └── services/
│           └── alert_manager.py
├── user-management/                 # Port 5004
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   └── app/
│       ├── __init__.py
│       ├── routes/
│       │   ├── auth.py
│       │   ├── users.py
│       │   └── admin.py
│       └── services/
│           └── user_service.py
└── dashboard-api/                   # Port 5005
    ├── Dockerfile
    ├── requirements.txt
    ├── main.py
    └── app/
        ├── __init__.py
        ├── routes/
        │   ├── dashboard.py
        │   ├── predictions.py
        │   ├── aggregation.py
        │   ├── export.py
        │   ├── performance.py
        │   └── gis.py
        └── services/
            └── dashboard_service.py
```
