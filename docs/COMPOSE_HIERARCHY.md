# Docker Compose Hierarchy

> Last updated: 2025-07

## Overview

Floodingnaque uses 7 Compose files with a shared-anchor base pattern. The base `compose.yaml` defines YAML anchors (`x-*`) that downstream files reference via the `include` directive (requires Docker Compose v2.20+).

## File Map

```
compose.yaml                    ← Base anchors (x-backend-base, x-redis-base, etc.)
├── compose.development.yaml    ← Dev: Supabase + hot-reload
├── compose.staging.yaml        ← Staging: Supabase + model signing
├── compose.production.yaml     ← Full stack: PgBouncer, Nginx, monitoring profiles
├── compose.observability.yaml  ← Grafana + Alertmanager + Jaeger overlay
├── compose.microservices.yaml  ← 5-service decomposition (experimental)
└── compose.mlflow.yaml         ← MLflow tracking server
```

## Usage

```bash
# Local development (PostgreSQL + Redis + backend)
docker compose up -d --build

# Development with Supabase
docker compose -f compose.development.yaml up -d --build

# Staging
docker compose -f compose.staging.yaml up -d

# Production (full stack)
docker compose -f compose.production.yaml up -d

# Production + monitoring
docker compose -f compose.production.yaml -f compose.observability.yaml up -d

# Production with Nginx reverse proxy
docker compose -f compose.production.yaml --profile nginx up -d

# Production with Prometheus monitoring
docker compose -f compose.production.yaml --profile monitoring up -d

# Microservices (experimental)
docker compose -f compose.microservices.yaml up -d

# MLflow experiment tracking
docker compose -f compose.mlflow.yaml up -d

# Hot-reload (Compose v2.22+)
docker compose watch
```

## Base Anchors — compose.yaml

The base file defines shared YAML anchors used by all environment files:

| Anchor                | Purpose                                   |
| --------------------- | ----------------------------------------- |
| `x-backend-base`      | Backend service template (Flask/Gunicorn) |
| `x-redis-base`        | Redis configuration template              |
| `x-postgres-base`     | PostgreSQL configuration template         |
| Healthcheck templates | Reusable health check definitions         |

**Never edit `compose.yaml` anchors without checking all downstream files.**

## Environment Files

### compose.development.yaml

- **Database**: Supabase (external)
- **Features**: Hot-reload, debug mode
- **Ports**: Backend :5000
- **Includes**: compose.yaml

### compose.staging.yaml

- **Database**: Supabase (external)
- **Features**: Model signature verification enabled (`REQUIRE_MODEL_SIGNATURE=True`)
- **Overlay**: Supports `-f compose.observability.yaml` for monitoring
- **Includes**: compose.yaml

### compose.production.yaml

- **Database**: Supabase PostgreSQL with SSL `verify-full`
- **Connection pooling**: PgBouncer (transaction mode, pool=20, max=45)
- **Cache**: Redis Cloud (Azure West US)
- **Reverse proxy**: Nginx with TLS (optional, `--profile nginx`)
- **Monitoring**: Prometheus (optional, `--profile monitoring`)
- **Secrets**: Docker Secrets support (recommended)
- **Includes**: compose.yaml

### compose.observability.yaml

- **Services**: Grafana (10.2.3), Alertmanager (0.27.0), Jaeger (1.54)
- **Ports**: Grafana :3000, Alertmanager :9093, Jaeger :16686
- **Networks**: Creates `floodingnaque-observability`, references external `floodingnaque-monitoring-production`
- **Volumes**: `grafana_data`, `alertmanager_data`, `jaeger_data`
- **Includes**: compose.yaml
- **See**: [MONITORING_SETUP.md](MONITORING_SETUP.md) for full details

### compose.microservices.yaml

Experimental 5-service decomposition:

| Service            | Port | Purpose                |
| ------------------ | ---- | ---------------------- |
| weather-collector  | 5001 | Weather data ingestion |
| ml-prediction      | 5002 | Model inference API    |
| alert-notification | 5003 | Alert delivery engine  |
| user-management    | 5004 | Auth & user CRUD       |
| dashboard-api      | 5005 | Dashboard aggregation  |

Shared infrastructure: PostgreSQL, PgBouncer, Redis, Nginx API Gateway.

### compose.mlflow.yaml

- **Service**: MLflow tracking server
- **Port**: 5001
- **Purpose**: Local ML experiment tracking and model registry
- **Usage**: `docker compose -f compose.mlflow.yaml up -d`

## Network Topology

```
                    ┌─ compose.production.yaml ─────────────────────┐
                    │                                               │
Internet ──→ Nginx :443 ──→ Backend :5000 ──→ PgBouncer :6432     │
                    │            │                  │                │
                    │            ├──→ Redis :6379   ├──→ Supabase   │
                    │            │                                   │
                    │            └──→ Celery Worker                  │
                    └───────────────────────────────────────────────┘

                    ┌─ compose.observability.yaml ──────────────────┐
                    │                                               │
                    │  Prometheus :9090 ──→ Alertmanager :9093      │
                    │       │                                       │
                    │       └──→ Grafana :3000                      │
                    │                                               │
                    │  Jaeger :16686 (traces from Backend)          │
                    └───────────────────────────────────────────────┘
```

## Docker Secrets (Production)

Production uses Docker Secrets (`/run/secrets/*`) for sensitive configuration. The entrypoint validates these are mounted:

| Secret              | Required | Purpose                 |
| ------------------- | -------- | ----------------------- |
| `secret_key`        | Yes      | Flask session signing   |
| `jwt_secret_key`    | Yes      | JWT token signing       |
| `database_url`      | Yes      | PostgreSQL connection   |
| `redis_url`         | Yes      | Redis connection        |
| `owm_api_key`       | Yes      | OpenWeatherMap API      |
| `model_signing_key` | Yes      | HMAC model verification |

The backend's `get_secret("KEY")` helper checks `KEY_FILE` env var first, falls back to `KEY`.

## Connection Budget

| Environment | PgBouncer Pool | Max DB Connections | Supabase Limit |
| ----------- | -------------- | ------------------ | -------------- |
| Development | N/A (direct)   | ~5                 | ~60 (Free)     |
| Staging     | N/A (direct)   | ~10                | ~60 (Free)     |
| Production  | 20             | 45                 | ~60 (Free)     |

Budget: 45 via PgBouncer + 5 admin + 10 headroom = 60 total.
