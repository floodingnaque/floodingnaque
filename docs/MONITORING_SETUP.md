# Monitoring Setup Guide

> Last updated: 2025-07

## Overview

Floodingnaque uses a full observability stack for production monitoring:

| Service      | Version | Port  | Purpose                       |
| ------------ | ------- | ----- | ----------------------------- |
| Prometheus   | latest  | 9090  | Metrics collection & alerting |
| Grafana      | 10.2.3  | 3000  | Dashboards & visualization    |
| Alertmanager | 0.27.0  | 9093  | Alert routing & deduplication |
| Jaeger       | 1.54    | 16686 | Distributed tracing           |

## Quick Start

```bash
# Production with observability
docker compose -f compose.production.yaml -f compose.observability.yaml up -d

# Staging with observability
docker compose -f compose.staging.yaml -f compose.observability.yaml up -d
```

## Architecture

```
┌─────────────┐    scrape     ┌────────────┐    push     ┌──────────────┐
│  Prometheus  │──────────────│  Exporters  │            │ Alertmanager  │
│  :9090       │              │  (7 jobs)   │            │  :9093        │
└──────┬───────┘              └─────────────┘            └───────┬───────┘
       │ datasource                                             │ email
       ▼                                                        ▼
┌─────────────┐                                        ┌───────────────┐
│   Grafana   │                                        │  SMTP (Gmail) │
│   :3000     │                                        └───────────────┘
└─────────────┘

┌─────────────┐    traces     ┌─────────────┐
│  Backend    │──────────────│   Jaeger     │
│  :5000      │              │   :16686     │
└─────────────┘              └──────────────┘
```

## Prometheus Scrape Targets

Configured in `monitoring/prometheus.yml` (15s scrape interval):

| Job                 | Target             | Port | Metrics Path |
| ------------------- | ------------------ | ---- | ------------ |
| `prometheus`        | localhost          | 9090 | /metrics     |
| `floodingnaque-api` | backend            | 5000 | /metrics     |
| `postgres`          | postgres_exporter  | 9187 | /metrics     |
| `pgbouncer`         | pgbouncer_exporter | 9127 | /metrics     |
| `redis`             | redis_exporter     | 9121 | /metrics     |
| `nginx`             | nginx-exporter     | 9113 | /metrics     |
| `celery-worker`     | celery-exporter    | 9808 | /metrics     |

## Alert Rules

40+ alert rules defined in `monitoring/alerts/floodingnaque.yml`, organized by group:

### API Health (5 rules)

- **APIDown** — Backend unreachable for 1 minute
- **HighErrorRate** — >5% HTTP 5xx responses
- **CriticalErrorRate** — >10% error rate
- **SlowResponses** — p95 latency exceeds threshold
- **SLA Violations** — Uptime below SLA target

### ML Predictions (6 rules)

- **HighPredictionLatency** — Prediction response time degraded
- **NoPredictions** — Zero predictions in evaluation window
- **ModelAccuracyDegraded** — Accuracy below threshold
- **ModelFeatureDefaultRate** — Too many features falling back to defaults
- **PredictionConfidenceDropped** — Average confidence below threshold
- **WeatherAPIFailureRate** — Weather data source failures

### Circuit Breaker (1 rule)

- **CircuitBreakerOpen** — External service circuit open for >2 minutes

### Database (5 rules)

- **DBPoolExhaustion** — Connection pool usage >85%
- **DBPoolOverflow** — Pool overflow connections active
- **SlowDatabaseQueries** — p95 query time >500ms
- **PostgreSQLDown** — Database unreachable
- **PgBouncerDown** — Connection pooler unreachable

### Cache / Redis (2 rules)

- **RedisDown** — Redis unreachable
- **LowCacheHitRate** — Cache hit rate below 50%

### Celery Workers (6 rules)

- **CeleryWorkerDown** — No active Celery workers
- **CeleryHighTaskFailureRate** — >10% task failure rate
- **CeleryQueueBacklog** — >50 tasks queued
- **ModelRetrainingFailed** — Auto-retrain task failed
- **NoTasksProcessed** — Zero tasks in evaluation window
- **DeadLetterQueueGrowing** — >10 items in DLQ

### Infrastructure (8 rules)

- **HighMemoryUsage** — Container memory >1.5GB
- **TargetDown** — Any scrape target unreachable
- **NginxDown** — Reverse proxy unreachable
- **TLSCertExpiringSoon** — Certificate expires in <14 days
- **HighCPUUsage** — Sustained high CPU utilization
- **HostDiskSpaceCritical** — Disk usage >85%
- **DatabaseBackupStale** — Last backup >25 hours ago
- **PrometheusStorageHigh** — TSDB >8GB

### Model Drift (3 rules)

- **ModelDriftCritical** — PSI >0.20 (population stability index)
- **ModelDriftStatusCritical** — Drift monitor reports critical status
- **DriftCheckStale** — No drift check in >24 hours

### Watchdog (1 rule)

- Deadman switch — always-firing alert to verify Alertmanager is alive

## Alertmanager Configuration

Configured in `monitoring/alertmanager/alertmanager.yml`.

### SMTP Setup

Set these environment variables before starting:

```bash
ALERTMANAGER_SMTP_HOST=smtp.gmail.com:587
ALERTMANAGER_SMTP_FROM=alerts@floodingnaque.com
ALERTMANAGER_SMTP_USERNAME=<your-gmail>
ALERTMANAGER_SMTP_PASSWORD=<app-password>
ALERTMANAGER_NOTIFY_EMAIL=team@floodingnaque.com
```

> **Note**: Use a Gmail App Password, not your account password. Enable 2FA first.

### Alert Routing

| Severity | Group Wait | Repeat Interval | Receiver          |
| -------- | ---------- | --------------- | ----------------- |
| Critical | 10s        | 1h              | critical-receiver |
| Warning  | 30s        | 4h              | default-receiver  |
| Watchdog | immediate  | 1m              | watchdog (null)   |

**Inhibition**: Critical alerts suppress warnings with the same `alertname` and `instance`.

## Grafana Dashboards

5 pre-built dashboards auto-provisioned from `monitoring/grafana/dashboards/`:

| Dashboard            | File                        | Purpose                          |
| -------------------- | --------------------------- | -------------------------------- |
| API Overview         | `api-overview.json`         | Request rates, latency, errors   |
| Database Metrics     | `database-metrics.json`     | Pool usage, query performance    |
| Error Tracking       | `error-tracking.json`       | Error rates by type and endpoint |
| ML Model Performance | `ml-model-performance.json` | Prediction latency, confidence   |
| Performance Analysis | `performance-analysis.json` | System-wide performance view     |

Access Grafana at `http://localhost:3000` (default credentials: admin/admin).

Datasources are auto-provisioned as read-only via `monitoring/grafana/provisioning/`.

## Jaeger Tracing

Access at `http://localhost:16686`. The backend sends OpenTelemetry traces with correlation IDs (W3C Trace Context).

Storage: In-memory Badger (default). For production persistence, configure an Elasticsearch backend.

## File Structure

```
monitoring/
├── prometheus.yml                    # Scrape configuration
├── alerts/
│   └── floodingnaque.yml             # All alert rules (40+)
├── alertmanager/
│   └── alertmanager.yml              # Routing & receivers
└── grafana/
    ├── dashboards/                   # 5 JSON dashboards
    │   ├── api-overview.json
    │   ├── database-metrics.json
    │   ├── error-tracking.json
    │   ├── ml-model-performance.json
    │   └── performance-analysis.json
    └── provisioning/                 # Auto-provisioned datasources
```
