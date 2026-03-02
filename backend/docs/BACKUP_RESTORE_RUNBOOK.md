# Database Backup & Restore Runbook

## Overview

This runbook covers backup and restore procedures for the Floodingnaque
PostgreSQL database (Supabase-hosted). Follow these procedures to recover
from data loss, bad migrations, or disaster scenarios.

---

## Backup Locations

| Type | Location | Retention |
|------|----------|-----------|
| Automated daily | Docker volume `floodingnaque-backups-production` → `/app/backups/` | 30 days |
| Pre-deploy | Same volume, created before each production deploy | 30 days |
| Manual | Created on-demand via CLI | Until manually deleted |

---

## 1. Creating a Manual Backup

### Via Docker Compose (Production)

```bash
# SSH into production server
ssh deploy@your-server

cd /opt/floodingnaque

# Full backup (compressed)
docker compose -f compose.production.yaml exec backend \
  python -m scripts.backup_database --postgres --verbose

# Schema-only backup
docker compose -f compose.production.yaml exec backend \
  python -m scripts.backup_database --postgres --verbose --no-compress

# Dry run (see what would happen)
docker compose -f compose.production.yaml exec backend \
  python -m scripts.backup_database --postgres --dry-run
```

### Via Shell Script (Direct Access)

```bash
# Requires DATABASE_URL environment variable
export DATABASE_URL="postgresql://user:pass@host:port/dbname"

./backend/scripts/backup_database.sh             # Full backup
./backend/scripts/backup_database.sh --schema-only  # Schema only
./backend/scripts/backup_database.sh --list         # List backups
```

---

## 2. Listing Available Backups

```bash
# Inside the container
docker compose -f compose.production.yaml exec backend \
  ls -lht /app/backups/

# Via shell script
docker compose -f compose.production.yaml exec backend \
  bash /app/scripts/backup_database.sh --list
```

---

## 3. Verifying Backup Integrity

```bash
# Test gzip integrity and inspect SQL content
docker compose -f compose.production.yaml exec backend \
  bash /app/scripts/backup_database.sh --verify /app/backups/latest_full.sql.gz

# Or verify a specific backup
docker compose -f compose.production.yaml exec backend \
  bash /app/scripts/backup_database.sh --verify /app/backups/floodingnaque_backup_20260301_020000_full.sql.gz
```

---

## 4. Restoring from Backup

### CRITICAL: Pre-Restore Checklist

- [ ] Confirm you have the correct backup file
- [ ] Verify backup integrity (step 3 above)
- [ ] Create a fresh backup of the current state BEFORE restoring
- [ ] Notify the team - this will cause downtime
- [ ] Stop all application traffic (scale down or enable maintenance mode)

### Step-by-Step Restore Procedure

```bash
# 1. SSH into production server
ssh deploy@your-server
cd /opt/floodingnaque

# 2. Create a safety backup of current state
docker compose -f compose.production.yaml exec backend \
  python -m scripts.backup_database --postgres --verbose
echo "Safety backup created. Proceeding with restore..."

# 3. Stop application services (keep database accessible)
docker compose -f compose.production.yaml stop backend celery-worker celery-beat

# 4. Restore the backup
#    Option A: Via shell script (interactive, requires confirmation)
docker compose -f compose.production.yaml exec backend \
  bash /app/scripts/backup_database.sh --restore /app/backups/YOUR_BACKUP_FILE.sql.gz

#    Option B: Manual restore with psql
docker compose -f compose.production.yaml exec backend bash -c '
  gunzip -c /app/backups/YOUR_BACKUP_FILE.sql.gz | \
  psql "$DATABASE_URL"
'

# 5. Run any pending migrations after restore
docker compose -f compose.production.yaml exec backend \
  alembic upgrade head

# 6. Restart application services
docker compose -f compose.production.yaml up -d backend celery-worker celery-beat

# 7. Verify health
curl -f https://api.floodingnaque.com/health
curl -f https://api.floodingnaque.com/health/ready
```

### Restoring to a Specific Migration Version

If you need to roll back to a specific Alembic migration version:

```bash
# List migration history
docker compose -f compose.production.yaml exec backend \
  alembic history --verbose

# Downgrade to a specific revision
docker compose -f compose.production.yaml exec backend \
  alembic downgrade <revision_id>
```

---

## 5. Disaster Recovery

### Scenario: Complete Host Failure

1. Provision a new server with Docker installed
2. Clone the repository: `git clone ... /opt/floodingnaque`
3. Restore secrets: copy `secrets/` directory from secure storage
4. Restore `.env.production` from secure storage
5. Restore CA certificate to `backend/certs/prod-ca-2021.crt`
6. Restore the latest backup from offsite storage (see W6 offsite config)
7. Start services: `docker compose -f compose.production.yaml up -d`
8. Restore DB: follow step 4 above
9. Verify health endpoints

### Scenario: Bad Migration

1. Create a backup of current (broken) state
2. Identify the last good migration: `alembic history`
3. Downgrade: `alembic downgrade <last_good_revision>`
4. Fix the migration file
5. Re-apply: `alembic upgrade head`

### Scenario: Data Corruption

1. Stop application traffic
2. Create backup of corrupted state (for analysis)
3. Restore from the most recent known-good backup
4. Re-run migrations if needed
5. Check data integrity with application health checks
6. Resume traffic

---

## 6. Automated Backup Schedule

Backups are triggered automatically by Celery Beat:

| Task | Schedule | Description |
|------|----------|-------------|
| `database_backup` | Daily at 02:00 UTC | Full compressed PostgreSQL backup |
| Retention cleanup | After each backup | Keeps last 30 backups (configurable via `BACKUP_RETENTION_COUNT`) |

Monitor backup health via:
- Celery task logs: check `celery-worker` container logs
- Backup directory contents: `ls -lht /app/backups/` inside the container

---

## 7. Offsite Backup (Recommended)

See the backup sidecar service in `compose.production.yaml` for S3/GCS
offsite backup configuration. Configure with:

```env
BACKUP_S3_BUCKET=your-backup-bucket
BACKUP_S3_PREFIX=floodingnaque/db/
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
```

---

## Contacts

- **Database Admin**: Check `.env.production` for Supabase project URL
- **On-Call**: See team communication channels
- **Supabase Dashboard**: https://supabase.com/dashboard
