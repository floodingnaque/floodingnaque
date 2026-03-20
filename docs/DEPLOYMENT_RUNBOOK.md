# Deployment & Rollback Runbook — Floodingnaque

## Overview

Standard operating procedures for deploying new versions and rolling back if issues are detected. All deployments use Docker Compose with zero-downtime rolling updates.

---

## Pre-Deployment Checklist

- [ ] All CI checks pass (tests, lint, type-check, security scan)
- [ ] Database migration tested locally (`alembic upgrade head`)
- [ ] No breaking API changes (or clients updated first)
- [ ] Docker image builds successfully
- [ ] Environment variables updated in production `.env`
- [ ] Backup created (see Backup section below)
- [ ] Team notified of deployment window

---

## 1. Standard Deployment

### Step 1: Create Pre-Deployment Backup

```bash
# Database backup
docker compose -f compose.production.yaml exec postgres \
  pg_dump -U floodingnaque -Fc floodingnaque > backups/pre-deploy-$(date +%Y%m%d_%H%M%S).dump

# Current image tag (for rollback reference)
docker compose -f compose.production.yaml images backend --format json | jq '.[0].Tag'
```

### Step 2: Pull Latest Code & Build

```bash
git pull origin main
docker compose -f compose.production.yaml build --no-cache backend
```

### Step 3: Run Database Migrations

```bash
docker compose -f compose.production.yaml exec backend alembic upgrade head
```

### Step 4: Rolling Restart

```bash
# Gunicorn handles graceful worker restart via SIGHUP
docker compose -f compose.production.yaml up -d --no-deps backend

# Wait for health check to pass
for i in $(seq 1 30); do
  STATUS=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:5000/health)
  if [ "$STATUS" = "200" ]; then echo "✓ Healthy"; break; fi
  echo "Waiting... ($i/30)"
  sleep 2
done
```

### Step 5: Post-Deployment Verification

```bash
# Verify health
curl -s http://localhost:5000/health | jq .

# Verify API version
curl -s http://localhost:5000/api/version | jq .

# Verify model is loaded
curl -s http://localhost:5000/api/v1/admin/models/ \
  -H "Authorization: Bearer $TOKEN" | jq .data.current_model.version

# Check for errors in last 5 minutes
docker compose -f compose.production.yaml logs --since=5m backend | grep -i error | head -20

# Verify Prometheus metrics still flowing
curl -s http://localhost:5000/metrics | head -5
```

---

## 2. Rollback Procedure

### Scenario A: Application Rollback (No Migration Changes)

```bash
# Revert to previous image
git checkout HEAD~1
docker compose -f compose.production.yaml build backend
docker compose -f compose.production.yaml up -d --no-deps backend

# Verify
curl -s http://localhost:5000/health | jq .
```

### Scenario B: Application + Database Rollback

```bash
# 1. Stop the backend to prevent further writes
docker compose -f compose.production.yaml stop backend

# 2. Downgrade database
docker compose -f compose.production.yaml exec postgres \
  alembic downgrade -1

# 3. Revert code
git checkout HEAD~1
docker compose -f compose.production.yaml build backend

# 4. Restart
docker compose -f compose.production.yaml up -d backend
```

### Scenario C: Full Database Restore from Backup

```bash
# 1. Stop all services
docker compose -f compose.production.yaml stop

# 2. Restore database
docker compose -f compose.production.yaml exec -T postgres \
  pg_restore -U floodingnaque -d floodingnaque --clean --if-exists \
  < backups/pre-deploy-YYYYMMDD_HHMMSS.dump

# 3. Restart
docker compose -f compose.production.yaml up -d
```

### Scenario D: Model Rollback Only

```bash
# Via API
curl -X POST http://localhost:5000/api/v1/admin/models/rollback \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"version": "v5"}'
```

---

## 3. Canary Deployment (Optional)

For high-risk deployments, use canary pattern:

### Step 1: Deploy Canary Instance

```bash
# Scale to 2 replicas, one with new code
docker compose -f compose.production.yaml up -d --scale backend=2 backend
```

### Step 2: Monitor Canary Health

Watch for 15-30 minutes:

- Error rate (`HighErrorRate` alert)
- Prediction accuracy (`ModelAccuracyDegraded`)
- Latency p95 (`SlowResponses`)
- Memory/CPU usage

### Step 3: Promote or Rollback

```bash
# If healthy — scale down to 1 with new version
docker compose -f compose.production.yaml up -d --scale backend=1 backend

# If unhealthy — stop canary, keep old
docker compose -f compose.production.yaml up -d --scale backend=1 --no-recreate backend
```

---

## 4. Post-Deployment Monitoring Checklist

Monitor for **30 minutes** after deployment:

- [ ] Health endpoint returns 200
- [ ] No new error spikes in Sentry
- [ ] API response times normal (p95 < 2s)
- [ ] Prediction endpoint working (`POST /api/v1/predict`)
- [ ] SSE connections active (check `/api/v1/sse/alerts`)
- [ ] Celery workers processing tasks
- [ ] Redis caching operational
- [ ] No database migration errors in logs
- [ ] Grafana dashboards show normal metrics
- [ ] Prometheus alerts are not firing unexpectedly

---

## 5. Emergency Contacts & Escalation

| Level | Trigger                      | Action                                                 |
| ----- | ---------------------------- | ------------------------------------------------------ |
| L1    | Single service down          | Restart service, check logs                            |
| L2    | Multiple services affected   | Full restart, check infrastructure                     |
| L3    | Data loss or security breach | Stop all services, restore backup, notify stakeholders |

---

## 6. Deployment Schedule

| Type     | Window                | Approval                  |
| -------- | --------------------- | ------------------------- |
| Hotfix   | Anytime               | Post-deploy review        |
| Standard | Business hours        | Pre-deploy review         |
| Major    | Scheduled maintenance | Full team review + backup |
