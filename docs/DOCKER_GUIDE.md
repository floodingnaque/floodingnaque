# Floodingnaque Docker Systematic Guide

> **Complete reference for containerized deployment across all environments**

This guide covers the full Docker ecosystem for Floodingnaque, including local development, staging, production deployment, monitoring, and troubleshooting.

> **📦 Compose Specification Modernization (February 2026)**
> 
> This project has been updated to follow the modern Docker Compose Specification:
> - **File naming**: `compose.yaml` (replaces `docker-compose.yml`)
> - **CLI syntax**: `docker compose` (space-separated, replaces `docker-compose`)
> - **Project names**: Explicit `name:` property in all compose files
> - **Hot-reload**: `develop.watch` section for automatic file sync
> - **No `version:`**: Removed obsolete `version: '3.8'` key (deprecated in Compose v2+)
> 
> Docker 29.1.5+ and Compose v5.0.1+ required. See [Compose Specification](https://docs.docker.com/compose/compose-file/).

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Quick Start](#quick-start)
3. [Docker Compose Files](#docker-compose-files)
4. [Build System](#build-system)
5. [Environment Configuration](#environment-configuration)
6. [Service Reference](#service-reference)
7. [Networks & Security](#networks--security)
8. [Volume Management](#volume-management)
9. [Profiles & Optional Services](#profiles--optional-services)
10. [Production Deployment](#production-deployment)
11. [Monitoring & Observability](#monitoring--observability)
12. [Database Operations](#database-operations)
13. [Troubleshooting](#troubleshooting)
14. [Commands Reference](#commands-reference)

---

## Architecture Overview

### System Topology

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PRODUCTION ARCHITECTURE                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│    Internet                                                                  │
│        │                                                                    │
│        ▼                                                                    │
│  ┌──────────────┐     ┌─────────────────────────────────────────────────┐  │
│  │   Nginx      │     │              Backend Network                     │  │
│  │   (TLS)      │────▶│  ┌─────────┐  ┌─────────┐  ┌─────────────────┐  │  │
│  │   :80/:443   │     │  │ Backend │  │ Celery  │  │  Celery Beat    │  │  │
│  └──────────────┘     │  │  API    │  │ Worker  │  │  (Scheduler)    │  │  │
│        │              │  │ :5000   │  │         │  │                 │  │  │
│        │              │  └────┬────┘  └────┬────┘  └────────┬────────┘  │  │
│        │              │       │            │                │           │  │
│        │              │       └────────────┴────────────────┘           │  │
│        │              │                    │                            │  │
│        │              └────────────────────┼────────────────────────────┘  │
│        │                                   │                               │
│        │              ┌────────────────────┼────────────────────┐          │
│        │              │    External Services                    │          │
│        │              │  ┌─────────────┐  ┌─────────────────┐   │          │
│        │              │  │  Supabase   │  │  Redis Cloud    │   │          │
│        │              │  │  PostgreSQL │  │  (Azure West)   │   │          │
│        │              │  └─────────────┘  └─────────────────┘   │          │
│        │              └─────────────────────────────────────────┘          │
│        │                                                                   │
│        │              ┌─────────────────────────────────────────┐          │
│        │              │       Monitoring Network (Internal)      │          │
│        └─────────────▶│  ┌──────────┐  ┌──────────┐  ┌───────┐  │          │
│                       │  │ Datadog  │  │Prometheus│  │Grafana│  │          │
│                       │  │  Agent   │  │          │  │       │  │          │
│                       │  └──────────┘  └──────────┘  └───────┘  │          │
│                       └─────────────────────────────────────────┘          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Environment Comparison

| Aspect | Local Dev | Development | Staging | Production |
|--------|-----------|-------------|---------|------------|
| **Database** | Local PostgreSQL | Supabase | Supabase | Supabase |
| **Redis** | Optional | Optional (profile) | Included | Redis Cloud |
| **TLS** | None | None | Optional | Nginx + Let's Encrypt |
| **Workers** | None | None | None | Celery + Beat |
| **Monitoring** | None | None | None | Datadog + Prometheus |
| **Hot Reload** | Yes | Yes | No | No |
| **Debug Mode** | Yes | Yes | No | No |

---

## Quick Start

### Prerequisites

- Docker Engine 29.1.5+
- Docker Compose v5.0.1+
- 4GB RAM minimum (8GB for production)
- Ports: 5000 (API), 5432 (PostgreSQL), 6379 (Redis), 6432 (PgBouncer)

### 1. Local Development (Fastest Setup)

```powershell
# Clone and navigate
cd floodingnaque

# Set required environment variable
$env:POSTGRES_PASSWORD = "your_secure_password_here"

# Copy environment template
Copy-Item backend\.env.example backend\.env.development

# Start services
docker compose up -d --build

# Verify
docker compose ps
curl http://localhost:5000/health
```

### 2. Development with Supabase

```powershell
# Configure Supabase connection in .env.development
# Set DATABASE_URL to your Supabase connection string

# Start (without local database)
docker compose -f compose.development.yaml up -d --build

# With Redis for caching
docker compose -f compose.development.yaml --profile with-redis up -d --build
```

### 3. Staging Environment

```powershell
# Configure backend/.env.staging with your staging Supabase credentials

docker compose -f compose.staging.yaml up -d --build
```

### 4. Production Deployment

```powershell
# Configure backend/.env.production with all production secrets

# Basic production
docker compose -f compose.production.yaml up -d --build

# Full production with all features
docker compose -f compose.production.yaml `
  --profile nginx `
  --profile monitoring `
  up -d --build
```

---

## Docker Compose Files

### File Overview

| File | Purpose | Services | Use Case |
|------|---------|----------|----------|
| `compose.yaml` | Base + Local dev | Backend, PostgreSQL, PgBouncer*, Shared anchors | Quick local testing, base for other files |
| `compose.development.yaml` | Dev with Supabase | Backend, Redis* | Team development |
| `compose.staging.yaml` | Pre-production | Backend, Redis | QA testing |
| `compose.production.yaml` | Full production | All services | Live deployment |
| `compose.mlflow.yaml` | ML tracking | MLflow, PostgreSQL | Experiment tracking |

*\* = Optional via profile*

### Combining Compose Files

```powershell
# Environment-specific files now include compose.yaml automatically
docker compose -f compose.development.yaml up -d
docker compose -f compose.staging.yaml up -d
docker compose -f compose.production.yaml up -d

# Multiple overlays (for ML tracking)
docker compose -f compose.production.yaml -f compose.mlflow.yaml up -d
```

### Compose File Inheritance

All environment-specific compose files use the `include` directive to inherit from `compose.yaml`:

```yaml
# compose.development.yaml (example)
include:
  - compose.yaml

name: floodingnaque-dev

services:
  backend:
    extends:
      file: compose.yaml
      service: backend
    # ... environment-specific overrides
```

**Shared configurations in `compose.yaml`:**

| Anchor | Purpose |
|--------|--------|
| `x-backend-base` | Base build config, restart policy, core env vars |
| `x-backend-healthcheck` | Standard health check configuration |
| `x-redis-healthcheck` / `x-postgres-healthcheck` | Database health checks |
| `x-redis-base` / `x-postgres-base` | Base image + restart policy |
| `x-logging-default` / `x-logging-production` | Log rotation settings (10m/50m) |
| `x-labels-common` | Shared project labels |
| `x-resources-small/medium/large` | CPU/memory limits |
| `x-security-opts` | Security hardening (no-new-privileges) |

> **Requirements:** Docker Compose v2.20+ (for `include` directive support)

---

## Build System

### Multi-Stage Dockerfile

The `backend/Dockerfile` uses a three-stage build:

```
┌─────────────────────────────────────────────────────────────────┐
│                        BUILD STAGES                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌─────────────────┐    ┌────────────────┐  │
│  │   BUILDER   │───▶│   PRODUCTION    │───▶│  DEVELOPMENT   │  │
│  │             │    │                 │    │                │  │
│  │ • Compiles  │    │ • Minimal image │    │ • All of prod  │  │
│  │   deps      │    │ • Non-root user │    │ • + vim, git   │  │
│  │ • venv      │    │ • Tini init     │    │ • + dev deps   │  │
│  │ • ~800MB    │    │ • Gunicorn      │    │ • Flask debug  │  │
│  │             │    │ • ~150MB        │    │ • ~200MB       │  │
│  └─────────────┘    └─────────────────┘    └────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Build Commands

```powershell
# Build for development
docker build --target development -t floodingnaque-api:dev ./backend

# Build for production
docker build --target production -t floodingnaque-api:prod ./backend

# Build with specific Python version
docker build --target production --build-arg PYTHON_VERSION=3.13 -t floodingnaque-api:py313 ./backend

# Build with no cache (clean build)
docker build --no-cache --target production -t floodingnaque-api:fresh ./backend
```

### Image Details

| Target | Base Image | Size | User | Init System |
|--------|------------|------|------|-------------|
| `builder` | python:3.12-slim-bookworm | ~800MB | root | - |
| `production` | python:3.12-slim-bookworm | ~150MB | appuser (1000) | tini |
| `development` | (extends production) | ~200MB | appuser (1000) | - |

### Production Image Features

- **Non-root user**: `appuser:appgroup` (UID/GID 1000)
- **Read-only filesystem**: In production compose
- **Health check**: Built-in `/health` endpoint check
- **Signal handling**: Uses `tini` as PID 1
- **Gunicorn**: Production WSGI server with configurable workers

---

## Environment Configuration

### Environment File Hierarchy

```
backend/
├── .env.example          # Template (committed to git)
├── .env.development      # Local development (gitignored)
├── .env.staging          # Staging environment (gitignored)
└── .env.production       # Production secrets (gitignored)
```

### Critical Variables

#### Required for All Environments

```dotenv
# Application
APP_ENV=development|staging|production
PORT=5000
HOST=0.0.0.0

# Security (generate with: python -c "import secrets; print(secrets.token_urlsafe(32))")
SECRET_KEY=your_32_char_minimum_secret_key
JWT_SECRET_KEY=another_32_char_secret_key

# Database
DATABASE_URL=postgresql://user:pass@host:5432/dbname
```

#### Development-Specific

```dotenv
FLASK_DEBUG=True
LOG_LEVEL=DEBUG
AUTH_BYPASS_ENABLED=False  # NEVER True in prod!
RATE_LIMIT_ENABLED=False
```

#### Production-Specific

```dotenv
# Security
AUTH_BYPASS_ENABLED=False
ENABLE_HTTPS=True
VERIFY_MODEL_INTEGRITY=True
REQUIRE_MODEL_SIGNATURE=True

# Database SSL
DB_SSL_MODE=verify-full
DB_SSL_CA_CERT=/app/certs/prod-ca-2021.crt

# Redis Cloud
REDIS_URL=rediss://default:password@redis-cloud-host:6380/0
CACHE_REDIS_URL=rediss://default:password@redis-cloud-host:6380/1
CELERY_BROKER_URL=rediss://default:password@redis-cloud-host:6380/2

# Monitoring
DD_API_KEY=your_datadog_api_key
DD_SITE=us5.datadoghq.com

# CORS
CORS_ORIGINS=https://floodingnaque.vercel.app,https://www.floodingnaque.com
```

#### PgBouncer Configuration

```dotenv
USE_PGBOUNCER=True
PGBOUNCER_URL=postgresql://postgres:password@pgbouncer:6432/floodingnaque

# Pool settings
PGBOUNCER_POOL_MODE=transaction
PGBOUNCER_MAX_CLIENT_CONN=1000
PGBOUNCER_DEFAULT_POOL_SIZE=25

# Admin credentials
PGBOUNCER_ADMIN_USER=pgbouncer_admin
PGBOUNCER_ADMIN_PASSWORD=secure_admin_password
PGBOUNCER_STATS_USER=pgbouncer_stats
PGBOUNCER_STATS_PASSWORD=secure_stats_password
```

---

## Service Reference

### Backend API

| Property | Development | Production |
|----------|-------------|------------|
| **Image** | `floodingnaque-api:development` | `floodingnaque-api:production-v2.0.0` |
| **Port** | `0.0.0.0:5000` | `127.0.0.1:5000` |
| **Workers** | 1 (Flask dev server) | 4 Gunicorn workers |
| **Memory** | 1GB limit | 2GB limit |
| **CPU** | 1 core limit | 2 cores limit |
| **Volumes** | Code mounted (hot reload) | Data only (no code mount) |

### PostgreSQL (Local)

```yaml
Image: postgres:15.5-alpine
Port: 5432
Health Check: pg_isready -U postgres -d floodingnaque
Volume: postgres_data_dev:/var/lib/postgresql/data
```

### Redis

```yaml
Image: redis:7.2-alpine
Port: 6379
Command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
Health Check: redis-cli ping
Volume: redis_data:/data
```

### PgBouncer

```yaml
Image: floodingnaque-pgbouncer:1.21.0 (custom)
Port: 6432
Pool Mode: transaction
Max Connections: 1000
Default Pool Size: 25
Health Check: pg_isready -h localhost -p 6432
```

### Celery Worker

```yaml
Image: floodingnaque-api:production (same as backend)
Command: celery -A app.services.celery_app worker --loglevel=info --concurrency=2
Memory: 1.5GB limit
Health Check: celery inspect ping
```

### Celery Beat

```yaml
Image: floodingnaque-api:production
Command: celery -A app.services.celery_app beat --loglevel=info
Memory: 512MB limit
Schedule Storage: /tmp/celerybeat-schedule
```

### Nginx

```yaml
Image: nginx:1.25-alpine
Ports: 80 (HTTP), 443 (HTTPS)
Config: ./nginx/floodingnaque.conf
Cert Volume: certbot_conf_prod:/etc/letsencrypt
```

### Datadog Agent

```yaml
Image: gcr.io/datadoghq/agent:7
APM Socket: /var/run/datadog/apm.socket
DogStatsD Socket: /var/run/datadog/dsd.socket
Memory: 512MB limit
```

### Prometheus

```yaml
Image: prom/prometheus:v2.48.0
Port: 127.0.0.1:9090 (internal only)
Config: ./monitoring/prometheus.yml
Retention: 30 days
```

---

## Networks & Security

### Network Topology

```
┌─────────────────────────────────────────────────────────────┐
│                    PRODUCTION NETWORKS                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  floodingnaque-frontend (external access)                   │
│  ├── nginx                                                  │
│  └── certbot                                                │
│                                                             │
│  floodingnaque-backend (internal + nginx access)            │
│  ├── backend                                                │
│  ├── celery-worker                                          │
│  ├── celery-beat                                            │
│  ├── pgbouncer                                              │
│  └── datadog-agent                                          │
│                                                             │
│  floodingnaque-monitoring (internal only)                   │
│  ├── prometheus                                             │
│  ├── datadog-agent                                          │
│  └── (grafana)                                              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Security Features

| Feature | Implementation |
|---------|----------------|
| **Non-root containers** | All services run as non-root users |
| **No new privileges** | `security_opt: no-new-privileges:true` |
| **Read-only filesystem** | Backend in production |
| **Internal networks** | Monitoring network isolated |
| **Localhost binding** | Backend port bound to 127.0.0.1 in prod |
| **TLS termination** | Nginx with Let's Encrypt |
| **Rate limiting** | Nginx + Flask-Limiter |

### Network Configuration

```powershell
# List networks
docker network ls | Select-String "floodingnaque"

# Inspect network
docker network inspect floodingnaque-backend-production

# Create custom network
docker network create --driver bridge floodingnaque-custom
```

---

## Volume Management

### Volume Overview

| Volume | Purpose | Persistence |
|--------|---------|-------------|
| `floodingnaque-models-*` | ML model files (.joblib, .json) | Critical |
| `floodingnaque-data-*` | Application data | Critical |
| `floodingnaque-logs-*` | Application logs | Important |
| `floodingnaque-backups-*` | Database backups | Critical |
| `floodingnaque-uploads-*` | User uploads | Important |
| `postgres_data_*` | PostgreSQL data | Critical |
| `redis_data_*` | Redis persistence | Reconstructable |
| `prometheus_data_*` | Metrics history | Reconstructable |
| `certbot_conf_*` | TLS certificates | Critical |

### Volume Commands

```powershell
# List all Floodingnaque volumes
docker volume ls | Select-String "floodingnaque"

# Inspect volume
docker volume inspect floodingnaque-models-production

# Create backup of volume
docker run --rm `
  -v floodingnaque-data-production:/source:ro `
  -v ${PWD}/backups:/backup `
  alpine tar czf /backup/data-$(Get-Date -Format "yyyyMMdd-HHmmss").tar.gz -C /source .

# Restore volume from backup
docker run --rm `
  -v floodingnaque-data-production:/target `
  -v ${PWD}/backups:/backup:ro `
  alpine sh -c "rm -rf /target/* && tar xzf /backup/data-20240101-120000.tar.gz -C /target"

# Remove unused volumes (CAUTION)
docker volume prune -f
```

### Data Backup Strategy

```powershell
# Complete backup script
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupDir = ".\backups\$timestamp"
New-Item -ItemType Directory -Force -Path $backupDir

# Backup each critical volume
@("models", "data", "logs", "backups") | ForEach-Object {
    docker run --rm `
      -v "floodingnaque-$_-production:/source:ro" `
      -v "${backupDir}:/backup" `
      alpine tar czf "/backup/$_.tar.gz" -C /source .
}

Write-Host "Backup complete: $backupDir"
```

---

## Profiles & Optional Services

### Available Profiles

| Profile | Services | Compose File |
|---------|----------|--------------|
| `with-redis` | Redis | compose.development.yaml |
| `pgbouncer` | PgBouncer | compose.yaml, compose.production.yaml |
| `nginx` | Nginx, Certbot | compose.production.yaml |
| `monitoring` | Prometheus | compose.production.yaml |

### Using Profiles

```powershell
# Single profile
docker compose -f compose.development.yaml --profile with-redis up -d

# Multiple profiles
docker compose -f compose.production.yaml --profile nginx --profile monitoring up -d

# List services including profiles
docker compose -f compose.production.yaml --profile nginx config --services
```

---

## Production Deployment

### Pre-Deployment Checklist

- [ ] `.env.production` configured with all secrets
- [ ] `DD_API_KEY` set for Datadog
- [ ] SSL certificates ready or domain configured for Let's Encrypt
- [ ] Database (Supabase) configured and accessible
- [ ] Redis Cloud configured and accessible
- [ ] CORS origins set correctly
- [ ] Firewall ports open: 80, 443

### Deployment Steps

```powershell
# 1. Pull latest code
git pull origin main

# 2. Build images
docker compose -f compose.production.yaml build

# 3. Stop existing services (graceful)
docker compose -f compose.production.yaml stop

# 4. Start with new images
docker compose -f compose.production.yaml --profile nginx --profile monitoring up -d

# 5. Verify health
docker compose -f compose.production.yaml ps
curl -k https://api.floodingnaque.com/health

# 6. Check logs for errors
docker compose -f compose.production.yaml logs --tail=100 backend
```

### Zero-Downtime Deployment

```powershell
# Scale up new instances
docker compose -f compose.production.yaml up -d --scale backend=2 --no-recreate

# Wait for health check
Start-Sleep -Seconds 60

# Remove old container (assumes container naming)
docker stop floodingnaque-api-prod-old
docker rm floodingnaque-api-prod-old

# Scale back down
docker compose -f compose.production.yaml up -d --scale backend=1
```

### TLS Certificate Setup

```powershell
# Initial certificate (first time only)
docker compose -f compose.production.yaml --profile nginx run --rm certbot `
  certonly --webroot -w /var/www/certbot `
  -d api.floodingnaque.com `
  --email your-email@example.com `
  --agree-tos

# Force renewal
docker compose -f compose.production.yaml --profile nginx run --rm certbot renew --force-renewal

# Reload nginx after renewal
docker compose -f compose.production.yaml --profile nginx exec nginx nginx -s reload
```

---

## Monitoring & Observability

### Health Check Endpoints

| Service | Endpoint | Expected Response |
|---------|----------|-------------------|
| Backend | `GET /health` | `{"status": "healthy"}` |
| Prometheus | `GET /-/healthy` | `Prometheus is Healthy` |
| Datadog | `agent health` | Exit code 0 |

### Prometheus Metrics

Access Prometheus UI (internal): `http://localhost:9090`

```yaml
# Scraped targets
- floodingnaque-api (backend:5000/metrics)
- prometheus (localhost:9090)
```

### Datadog Integration

```yaml
# Environment variables for APM
DD_ENV=production
DD_SERVICE=floodingnaque-api
DD_VERSION=2.0.0
DD_TRACE_AGENT_URL=unix:///var/run/datadog/apm.socket
DD_DOGSTATSD_URL=unix:///var/run/datadog/dsd.socket
```

### Log Aggregation

```powershell
# View all service logs
docker compose -f compose.production.yaml logs -f

# View specific service
docker compose -f compose.production.yaml logs -f backend

# Filter by time
docker compose -f compose.production.yaml logs --since 1h backend

# Export logs
docker compose -f compose.production.yaml logs --no-color > logs-export.txt
```

---

## Database Operations

### Run Migrations

```powershell
# Development
docker compose exec backend alembic upgrade head

# Production
docker compose -f compose.production.yaml exec backend alembic upgrade head

# Check current revision
docker compose exec backend alembic current

# Generate new migration
docker compose exec backend alembic revision --autogenerate -m "Add new table"
```

### Database Shell Access

```powershell
# Local PostgreSQL
docker exec -it floodingnaque-db-dev psql -U postgres -d floodingnaque

# PgBouncer admin
docker exec -it floodingnaque-pgbouncer-prod psql -h localhost -p 6432 -U pgbouncer_admin pgbouncer

# PgBouncer stats
docker exec -it floodingnaque-pgbouncer-prod psql -h localhost -p 6432 -U pgbouncer_stats pgbouncer -c "SHOW POOLS;"
```

### Database Backup (Local PostgreSQL)

```powershell
# Create backup
docker exec floodingnaque-db-dev pg_dump -U postgres floodingnaque > backup.sql

# Restore backup
docker exec -i floodingnaque-db-dev psql -U postgres floodingnaque < backup.sql
```

---

## Troubleshooting

### Common Issues

#### Container Won't Start

```powershell
# Check logs
docker logs floodingnaque-api-prod

# Check exit code
docker inspect floodingnaque-api-prod --format='{{.State.ExitCode}}'

# Verify environment
docker compose -f compose.production.yaml config

# Check for port conflicts
netstat -an | Select-String ":5000"
```

#### Database Connection Failed

```powershell
# Test from backend container
docker exec -it floodingnaque-api-dev python -c "
from app.core.database import engine
print(engine.execute('SELECT 1').fetchone())
"

# Check database health
docker exec -it floodingnaque-db-dev pg_isready -U postgres

# Verify connection string
docker exec -it floodingnaque-api-dev env | Select-String DATABASE_URL
```

#### Redis Connection Issues

```powershell
# Test Redis connectivity
docker exec -it floodingnaque-redis-dev redis-cli ping

# Check Redis info
docker exec -it floodingnaque-redis-dev redis-cli INFO

# Test from backend
docker exec -it floodingnaque-api-dev python -c "
import redis
r = redis.from_url('redis://redis:6379/0')
print(r.ping())
"
```

#### Out of Memory

```powershell
# Check container memory usage
docker stats --no-stream

# Increase limits in compose file or:
docker update --memory=4g floodingnaque-api-prod
```

#### Health Check Failing

```powershell
# Manual health check
docker exec -it floodingnaque-api-prod curl -f http://localhost:5000/health

# Check health status
docker inspect floodingnaque-api-prod --format='{{json .State.Health}}'
```

### Debug Mode

```powershell
# Start with interactive shell
docker compose run --rm backend /bin/bash

# Override entrypoint
docker run -it --entrypoint /bin/bash floodingnaque-api:dev

# Run with more verbose logging
docker compose -f compose.production.yaml run -e LOG_LEVEL=DEBUG backend
```

### Clean Restart

```powershell
# Stop and remove everything
docker compose down -v --remove-orphans

# Remove all floodingnaque images
docker images | Select-String "floodingnaque" | ForEach-Object { 
    $imageName = ($_ -split '\s+')[0] + ":" + ($_ -split '\s+')[1]
    docker rmi $imageName 
}

# Rebuild and start fresh
docker compose up -d --build --force-recreate
```

---

## Commands Reference

### Quick Reference Card

```powershell
# ===== LIFECYCLE =====
docker compose up -d                    # Start all services
docker compose up -d --build           # Build and start
docker compose down                     # Stop and remove
docker compose restart                  # Restart all services
docker compose stop                     # Stop without removing

# ===== INSPECTION =====
docker compose ps                       # List containers
docker compose logs -f                  # Follow all logs
docker compose logs -f backend          # Follow specific service
docker compose top                      # Show processes

# ===== EXECUTION =====
docker compose exec backend bash        # Shell into running container
docker compose run --rm backend bash    # New container with shell
docker compose exec backend python      # Python REPL

# ===== PROFILES =====
docker compose --profile nginx up -d    # Start with profile
docker compose --profile nginx --profile monitoring up -d

# ===== SCALING =====
docker compose up -d --scale backend=3  # Scale service

# ===== CLEANUP =====
docker compose down -v                  # Remove with volumes
docker system prune -af                 # Remove all unused
docker volume prune -f                  # Remove unused volumes
```

### Environment-Specific Commands

```powershell
# Local Development
docker compose up -d --build
docker compose logs -f backend
docker compose exec backend pytest

# Development (Supabase)
docker compose -f compose.development.yaml up -d --build
docker compose -f compose.development.yaml --profile with-redis up -d

# Staging
docker compose -f compose.staging.yaml up -d --build

# Production
docker compose -f compose.production.yaml --profile nginx --profile monitoring up -d --build
docker compose -f compose.production.yaml logs -f backend celery-worker

# MLflow
docker compose -f compose.mlflow.yaml up -d
```

---

## Appendix

### Resource Limits Summary

| Service | CPU Limit | Memory Limit | CPU Reserved | Memory Reserved |
|---------|-----------|--------------|--------------|-----------------|
| Backend (dev) | 1 | 1GB | 0.25 | 256MB |
| Backend (prod) | 2 | 2GB | 0.5 | 512MB |
| Celery Worker | 1.5 | 1.5GB | 0.5 | 512MB |
| Celery Beat | 0.5 | 512MB | 0.1 | 128MB |
| Redis | 0.5 | 512MB | - | - |
| PgBouncer | 0.5 | 256MB | 0.1 | 64MB |
| Datadog Agent | 1 | 512MB | 0.25 | 256MB |
| Prometheus | 0.5 | 512MB | 0.1 | 128MB |
| Nginx | 0.5 | 256MB | 0.1 | 64MB |

### Port Mapping Summary

| Port | Service | Environment |
|------|---------|-------------|
| 80 | Nginx HTTP | Production |
| 443 | Nginx HTTPS | Production |
| 5000 | Backend API | All |
| 5432 | PostgreSQL | Local dev |
| 6379 | Redis | All |
| 6432 | PgBouncer | With profile |
| 9090 | Prometheus | Production (internal) |

### Related Documentation

- [TLS_SETUP.md](TLS_SETUP.md) - Detailed TLS/SSL configuration
- [GIT_WORKFLOW_GUIDE.md](GIT_WORKFLOW_GUIDE.md) - Git branching strategy
- [GGSHIELD_SETUP.md](GGSHIELD_SETUP.md) - Secret scanning setup
- [backend/README.md](../backend/README.md) - Backend-specific documentation

---

*Last updated: February 2026*
