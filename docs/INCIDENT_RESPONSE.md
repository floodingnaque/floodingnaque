# Incident Response Runbook — Floodingnaque

## Overview

This document provides step-by-step procedures for diagnosing and resolving production incidents in the Floodingnaque flood prediction system. Follow each section from **Diagnosis → Mitigation → Resolution → Post-Incident**.

---

## 1. API Down / Unresponsive

### Symptoms

- Health check at `/health` returns non-200 or times out
- Prometheus alert: `APIDown` or `TargetDown`
- Users report "Connection refused" or 502/503 errors

### Diagnosis

```bash
# Check container status
docker compose -f compose.production.yaml ps

# Check backend logs (last 100 lines)
docker compose -f compose.production.yaml logs --tail=100 backend

# Check if Gunicorn workers are alive
docker compose -f compose.production.yaml exec backend ps aux | grep gunicorn

# Check health endpoint directly
curl -s http://localhost:5000/health | jq .
```

### Mitigation

```bash
# Restart the backend service
docker compose -f compose.production.yaml restart backend

# If restart fails, full recreate
docker compose -f compose.production.yaml up -d --force-recreate backend
```

### Resolution

1. Check for OOM kills: `docker inspect backend | grep -i oom`
2. Review logs for unhandled exceptions
3. Check if a bad deployment occurred — rollback if needed (see DEPLOYMENT_RUNBOOK.md)
4. Verify database connectivity: `curl http://localhost:5000/health` should show `database: healthy`

---

## 2. Database Connection Exhaustion

### Symptoms

- Prometheus alert: `DBPoolExhaustion` or `DBPoolOverflow`
- Slow API responses across all endpoints
- Logs show: `QueuePool limit reached` or `TimeoutError`

### Diagnosis

```bash
# Check current pool status
curl -s http://localhost:5000/api/v1/admin/monitoring | jq '.data.database'

# Check PgBouncer stats
docker compose -f compose.production.yaml exec pgbouncer pgbouncer -R

# PostgreSQL active connections
docker compose -f compose.production.yaml exec postgres \
  psql -U floodingnaque -c "SELECT count(*) FROM pg_stat_activity WHERE state = 'active';"
```

### Mitigation

```bash
# Kill idle connections via PgBouncer
docker compose -f compose.production.yaml exec pgbouncer pgbouncer -R

# Restart PgBouncer to release all pooled connections
docker compose -f compose.production.yaml restart pgbouncer

# If needed, restart backend to reset SQLAlchemy pool
docker compose -f compose.production.yaml restart backend
```

### Resolution

1. Review `SLOW_QUERY_THRESHOLD_MS` logs for long-running queries
2. Check for missing indexes on frequently queried columns
3. Consider increasing `DB_POOL_SIZE` (default: 3, max recommended: 10)
4. Check for connection leaks — unclosed `get_db_session()` calls

---

## 3. Model Accuracy Degradation

### Symptoms

- Prometheus alert: `ModelAccuracyDegraded` (accuracy < 70%)
- Prometheus alert: `PredictionConfidenceDropped` (avg confidence < 60%)
- Prediction drift detected at `/api/v1/admin/monitoring/prediction-drift`

### Diagnosis

```bash
# Check current model metadata
curl -s http://localhost:5000/api/v1/admin/models/ | jq .

# Check prediction drift stats
curl -s http://localhost:5000/api/v1/admin/monitoring/prediction-drift?minutes=1440 | jq .

# Review feature default rate
curl -s http://localhost:5000/api/v1/admin/monitoring | jq '.data.predictions'
```

### Mitigation

1. **Rollback to previous model** if degradation is sudden:
   ```bash
   curl -X POST http://localhost:5000/api/v1/admin/models/rollback \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"version": "v5"}'
   ```
2. Check if input data quality changed (weather API returning defaults)

### Resolution

1. Retrain with latest data: `python scripts/train_progressive_v6.py --grid-search --cv-folds 10`
2. Run sensitivity analysis: `python scripts/sensitivity_analysis.py --cv-folds 5`
3. Compare model versions: `python scripts/compare_models.py`
4. Update thesis report: `python scripts/generate_thesis_report.py`

---

## 4. Weather API Outage

### Symptoms

- Prometheus alert: `WeatherAPIFailureRate` (>30% failure rate)
- Prometheus alert: `CircuitBreakerOpen` for weather APIs
- Predictions using default/stale weather data

### Diagnosis

```bash
# Check circuit breaker states
curl -s http://localhost:5000/health | jq '.circuit_breakers'

# Check weather API response times
curl -s http://localhost:5000/api/v1/admin/monitoring/api-responses?minutes=60 | jq .
```

### Expected Behavior (Fallback Chain)

The system automatically falls through: **Meteostat → OpenWeatherMap → Google Earth Engine**

If all APIs fail, the system uses cached data (Redis TTL-based) or safe defaults. Predictions will show lower confidence but continue functioning.

### Resolution

1. Check API key validity for each provider
2. Verify external service status pages
3. Monitor circuit breaker recovery (auto half-open after cooldown)
4. If prolonged outage, consider manual weather data ingestion

---

## 5. Redis Failure

### Symptoms

- Prometheus alert: `RedisDown`
- API responses slower (no caching)
- Rate limiting may not work correctly
- Session storage fallback to filesystem

### Diagnosis

```bash
# Check Redis container
docker compose -f compose.production.yaml exec redis redis-cli ping

# Check Redis memory usage
docker compose -f compose.production.yaml exec redis redis-cli info memory

# Check connection count
docker compose -f compose.production.yaml exec redis redis-cli info clients
```

### Mitigation

```bash
# Restart Redis
docker compose -f compose.production.yaml restart redis
```

### Expected Degradation

- **Caching**: Disabled — all requests hit database directly
- **Rate limiting**: Falls back to in-memory (per-worker, less accurate)
- **Sessions**: Falls back to filesystem storage
- **Celery**: Broker unavailable — background tasks queued until recovery

---

## 6. SSL Certificate Expiry

### Symptoms

- Prometheus alert: `TLSCertExpiringSoon` (<14 days)
- Browser warnings about insecure connection

### Resolution

```bash
# Check certificate expiry
openssl s_client -connect yourdomain.com:443 2>/dev/null | openssl x509 -noout -dates

# Renew with certbot (if using Let's Encrypt)
docker compose -f compose.production.yaml exec nginx certbot renew

# Reload Nginx to pick up new cert
docker compose -f compose.production.yaml exec nginx nginx -s reload
```

---

## 7. DDoS / Rate Limit Breach

### Symptoms

- Prometheus alert: `HighErrorRate` with many 429 responses
- Abnormal traffic patterns in Grafana
- Legitimate users unable to access the system

### Mitigation

```bash
# Check top IPs hitting rate limits
docker compose -f compose.production.yaml logs backend | grep "429" | \
  awk '{print $NF}' | sort | uniq -c | sort -rn | head -20

# Block IP at Nginx level (immediate)
# Add to nginx/conf.d/blocklist.conf:
# deny 1.2.3.4;
docker compose -f compose.production.yaml exec nginx nginx -s reload
```

### Resolution

1. Review rate limit configuration in `app/api/middleware/rate_limit.py`
2. Consider implementing IP-based blocking at the CDN/WAF level
3. Review auth lockout tracking at `/api/v1/admin/security`

---

## 8. Celery Dead Letter Queue Growing

### Symptoms

- Prometheus alert: `CeleryDeadLetterQueueGrowing` (>10 entries for 30min)

### Diagnosis

```bash
# Check DLQ contents
curl -s http://localhost:5000/api/v1/admin/monitoring/celery/dlq \
  -H "Authorization: Bearer $TOKEN" | jq .
```

### Resolution

1. Review failed task details (exception messages)
2. Fix underlying issue (bad data, missing dependency, etc.)
3. Replay entries: `POST /api/v1/admin/monitoring/celery/dlq/replay`
4. Clear if unrecoverable: `DELETE /api/v1/admin/monitoring/celery/dlq`

---

## Post-Incident Checklist

- [ ] Root cause identified and documented
- [ ] Fix deployed and verified
- [ ] Affected users notified (if applicable)
- [ ] Monitoring alerts verified (didn't miss anything)
- [ ] After-action report created in the system
- [ ] Runbook updated if procedures changed
