# Scaling Guide — Floodingnaque

## Overview

This guide documents how to scale the Floodingnaque flood prediction system horizontally and vertically to handle increased load. Includes thresholds for when to scale and specific tuning parameters.

---

## 1. When to Scale — Indicators & Thresholds

| Metric                 | Warning Threshold  | Critical Threshold  | Action                          |
| ---------------------- | ------------------ | ------------------- | ------------------------------- |
| API p95 latency        | > 2s for 10min     | > 5s for 5min       | Scale Gunicorn workers          |
| CPU usage              | > 70% sustained    | > 85% sustained     | Vertical or horizontal scale    |
| Memory usage           | > 1.2GB per worker | > 1.5GB per worker  | Increase container memory       |
| DB pool utilization    | > 75%              | > 85%               | Increase pool size or PgBouncer |
| Celery queue depth     | > 50 pending tasks | > 200 pending tasks | Add Celery workers              |
| Redis memory           | > 80% maxmemory    | > 90% maxmemory     | Increase Redis memory           |
| Prediction latency p95 | > 3s               | > 5s                | Scale ML workers                |
| Concurrent SSE clients | > 500              | > 1000              | Dedicated SSE service           |

---

## 2. Horizontal Scaling

### 2.1 Gunicorn Workers

Current config in `gunicorn.conf.py`:

- Workers: `min(CPU_COUNT * 2 + 1, 9)`
- Worker class: `gthread`
- Threads per worker: `2`

**To scale:**

```bash
# Increase workers (set in .env or gunicorn.conf.py)
export GUNICORN_WORKERS=9

# Or override directly
gunicorn main:application -w 9 -k gthread --threads 2
```

**Guidelines:**

- Each worker uses ~200-400MB RAM
- Max recommended: `2 * CPU cores + 1`
- For IO-bound workloads (API), use `gthread` worker class
- For CPU-bound workloads (ML prediction), consider `sync` workers

### 2.2 Celery Workers

Current queues: `ml_tasks`, `data_tasks`, `notification_tasks`

**To scale by queue:**

```bash
# Scale ML task workers (CPU-intensive)
docker compose -f compose.production.yaml up -d --scale celery-ml=3

# Or start dedicated workers per queue
celery -A app.services.celery_app worker -Q ml_tasks -c 2 --max-tasks-per-child=100
celery -A app.services.celery_app worker -Q data_tasks -c 4
celery -A app.services.celery_app worker -Q notification_tasks -c 2
```

**Guidelines:**

- ML tasks: 1-2 workers (CPU-bound, memory-heavy)
- Data tasks: 2-4 workers (IO-bound)
- Notification tasks: 2-4 workers (IO-bound, low latency needed)
- Set `--max-tasks-per-child` to prevent memory leaks

### 2.3 Multi-Instance Backend

For high-availability, run multiple backend instances behind Nginx:

```yaml
# In compose.production.yaml
services:
  backend:
    deploy:
      replicas: 3
    # Ensure only ONE instance runs scheduler
    environment:
      - CELERY_BEAT_RUNNING=true # Only on primary
```

**Important:** Only one instance should run the APScheduler (controlled by `CELERY_BEAT_RUNNING` env var and file-based distributed lock).

---

## 3. Vertical Scaling

### 3.1 Container Memory

```yaml
# In compose.production.yaml
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 2G # Increase from default 1G
        reservations:
          memory: 512M
```

### 3.2 Container CPU

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: "2.0" # Increase from default 1.0
        reservations:
          cpus: "0.5"
```

---

## 4. Database Connection Scaling

### 4.1 SQLAlchemy Pool

Current defaults in `app/models/db.py`:

- `DB_POOL_SIZE`: 3
- `DB_MAX_OVERFLOW`: 5
- `DB_POOL_RECYCLE`: 1800s
- `DB_POOL_TIMEOUT`: 30s

**To scale:**

```bash
# In .env
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
```

**Guidelines:**

- Total connections per instance = `pool_size + max_overflow`
- With 3 backend instances: max 3 × (5 + 10) = 45 connections
- PostgreSQL default `max_connections` = 100
- Keep total < 80% of PostgreSQL max_connections

### 4.2 PgBouncer Tuning

PgBouncer configuration in `pgbouncer/pgbouncer.ini`:

```ini
[pgbouncer]
pool_mode = transaction          ; transaction pooling for high throughput
default_pool_size = 20           ; connections per user/database pair
max_client_conn = 200            ; max client connections to PgBouncer
reserve_pool_size = 5            ; extra connections for burst traffic
reserve_pool_timeout = 3         ; seconds to wait before using reserve
server_idle_timeout = 300        ; close idle server connections after 5min
```

**Scaling guidelines:**

- `default_pool_size` should cover peak concurrent queries
- `max_client_conn` should exceed total backend pool connections
- Monitor via PgBouncer admin console: `SHOW POOLS;`

---

## 5. Cache Scaling (Redis)

### 5.1 Memory Limits

```bash
# In redis.conf or via Docker
maxmemory 512mb                  # Increase as needed
maxmemory-policy allkeys-lru     # Evict least recently used keys
```

### 5.2 Connection Limits

```bash
maxclients 256                   # Default: 10000 (rarely need to change)
```

### 5.3 Monitoring

```bash
# Check memory usage
redis-cli INFO memory

# Check connected clients
redis-cli INFO clients

# Check eviction stats
redis-cli INFO stats | grep evicted
```

**Guidelines:**

- If eviction rate > 0, increase `maxmemory`
- If hit rate < 50%, review cache key TTLs
- Prediction cache: TTL 300s (weather-dependent)
- Weather cache: TTL 600s (API-dependent)

---

## 6. Microservices Decomposition

For extreme scale, decompose into the 5-service architecture defined in `compose.microservices.yaml`:

| Service            | Port | Responsibility        |
| ------------------ | ---- | --------------------- |
| weather-collector  | 5001 | Weather API ingestion |
| ml-prediction      | 5002 | Model inference       |
| alert-notification | 5003 | Alert broadcasting    |
| user-management    | 5004 | Auth & user CRUD      |
| dashboard-api      | 5005 | Dashboard aggregation |

**When to decompose:**

- Prediction latency requirements differ from API latency
- Weather collection needs independent scaling
- Alert delivery needs guaranteed SLA separate from API

---

## 7. Load Testing

Before scaling, baseline with Locust:

```bash
# Run load test
cd backend
locust -f tests/load/locustfile.py --headless \
  -u 100 -r 10 --run-time 5m \
  --host http://localhost:5000

# Key metrics to capture:
# - Requests/sec at target load
# - p95 response time
# - Error rate
# - Resource utilization (CPU, memory, connections)
```

Match scaling decisions to load test results rather than assumptions.
