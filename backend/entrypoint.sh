#!/bin/sh
# =====================================================
# Floodingnaque Backend - Docker Entrypoint
# =====================================================
# This script runs before the main application starts.
# It handles:
#   1. SSL CA certificate validation (B2)
#   2. Database migration via Alembic (W1)
#   3. Secrets directory verification (W3)
# =====================================================

set -e

echo "=== Floodingnaque Backend Entrypoint ==="
echo "Environment: ${APP_ENV:-development}"
echo "Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)"

# --------------------------------------------------
# 1. Validate SSL CA certificate if verify-full mode
# --------------------------------------------------
if [ "${DB_SSL_MODE}" = "verify-full" ]; then
    CA_CERT="${DB_SSL_CA_CERT:-/app/certs/prod-ca-2021.crt}"
    if [ ! -f "$CA_CERT" ]; then
        echo "ERROR: DB_SSL_MODE=verify-full but CA certificate not found at: $CA_CERT"
        echo ""
        echo "To fix this:"
        echo "  1. Download your database provider's CA certificate"
        echo "  2. Mount it at $CA_CERT in compose.production.yaml"
        echo "  3. See backend/certs/README.md for details"
        echo ""
        echo "To use encrypted-only mode without certificate verification:"
        echo "  Set DB_SSL_MODE=require instead of verify-full"
        exit 1
    fi
    echo "OK: SSL CA certificate found at $CA_CERT"
fi

# --------------------------------------------------
# 2. Verify Docker Secrets are mounted (production)
# --------------------------------------------------
if [ "${APP_ENV}" = "production" ]; then
    MISSING_SECRETS=""
    for secret_name in secret_key jwt_secret_key database_url redis_url owm_api_key model_signing_key; do
        if [ ! -f "/run/secrets/${secret_name}" ]; then
            MISSING_SECRETS="${MISSING_SECRETS} ${secret_name}"
        fi
    done

    if [ -n "$MISSING_SECRETS" ]; then
        echo "WARNING: Missing Docker secrets:${MISSING_SECRETS}"
        echo "Falling back to environment variables / .env.production"
    else
        echo "OK: All required Docker secrets are mounted"
    fi
fi

# --------------------------------------------------
# 3. Run database migrations (Alembic)
# --------------------------------------------------
if [ "${SKIP_MIGRATIONS:-false}" != "true" ]; then
    # Only the first backend replica should run migrations.
    # Gate behind RUN_MIGRATIONS env var (set on only 1 replica in compose).
    if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
        echo "Running Alembic database migrations..."
        # Use PostgreSQL advisory lock to prevent concurrent migration runs
        # across replicas. Lock ID 73209 is arbitrary but consistent.
        if python -c "
import os, sys
from sqlalchemy import create_engine, text

db_url = os.environ.get('DATABASE_URL', '')
if not db_url:
    print('WARNING: DATABASE_URL not set - running migrations without advisory lock')
    sys.exit(0)

try:
    engine = create_engine(db_url)
    with engine.connect() as conn:
        result = conn.execute(text('SELECT pg_try_advisory_lock(73209)')).scalar()
        if not result:
            print('SKIP: Another replica is running migrations (advisory lock held)')
            sys.exit(2)
        print('OK: Acquired migration advisory lock')
except Exception as e:
    print(f'WARNING: Could not acquire advisory lock ({e}) - proceeding anyway')
" 2>&1; then
            LOCK_STATUS=$?
        else
            LOCK_STATUS=$?
        fi

        if [ "$LOCK_STATUS" = "2" ]; then
            echo "SKIP: Migration lock held by another replica"
        else
            if alembic upgrade head 2>&1; then
                echo "OK: Database migrations applied successfully"
            else
                echo "ERROR: Alembic migration failed - database schema may be inconsistent"
                echo "Set SKIP_MIGRATIONS=true to bypass, or check the migration error above"
                exit 1
            fi
        fi
    else
        echo "SKIP: RUN_MIGRATIONS=false - skipping Alembic migrations"
    fi
else
    echo "SKIP: SKIP_MIGRATIONS=true - skipping Alembic migrations"
fi

# --------------------------------------------------
# 4. Seed default admin account
# --------------------------------------------------
if [ "${SEED_ADMIN:-true}" = "true" ]; then
    echo "Seeding default admin account..."
    if python create_admin.py --env "${APP_ENV:-development}" 2>&1; then
        echo "OK: Admin seed completed"
    else
        echo "WARNING: Admin seed failed (non-fatal) - continuing startup"
    fi
else
    echo "SKIP: SEED_ADMIN=false - skipping admin seed"
fi

echo "=== Entrypoint complete - starting application ==="

# Execute the CMD passed to this entrypoint
exec "$@"
