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
    for secret_name in secret_key jwt_secret_key database_url; do
        if [ ! -f "/run/secrets/${secret_name}" ]; then
            MISSING_SECRETS="${MISSING_SECRETS} ${secret_name}"
        fi
    done

    if [ -n "$MISSING_SECRETS" ]; then
        echo "WARNING: Missing Docker secrets:${MISSING_SECRETS}"
        echo "Falling back to environment variables / .env.production"
    else
        echo "OK: Required Docker secrets are mounted"
    fi
fi

# --------------------------------------------------
# 3. Run database migrations (Alembic)
# --------------------------------------------------
if [ "${SKIP_MIGRATIONS:-false}" != "true" ]; then
    # Only the first backend replica should run migrations.
    # Use a simple lock via environment variable or file lock.
    if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
        echo "Running Alembic database migrations..."
        if alembic upgrade head 2>&1; then
            echo "OK: Database migrations applied successfully"
        else
            echo "ERROR: Alembic migration failed - database schema may be inconsistent"
            echo "Set SKIP_MIGRATIONS=true to bypass, or check the migration error above"
            exit 1
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
