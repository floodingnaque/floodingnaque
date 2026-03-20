# Docker Secrets Setup Guide

This guide explains how to configure Docker Secrets for the Floodingnaque production deployment using the `_FILE` suffix pattern.

## Overview

Docker Secrets provide a secure way to store and manage sensitive data such as:

- Database credentials
- API keys
- Encryption keys
- Service passwords

### Benefits of Docker Secrets

| Benefit            | Description                                                         |
| ------------------ | ------------------------------------------------------------------- |
| **Security**       | Secrets are never exposed in `docker inspect`, logs, or environment |
| **Memory-only**    | Secrets are stored in tmpfs, never written to disk                  |
| **Access Control** | Only services that explicitly need a secret can access it           |
| **Rotation**       | Secrets can be updated without rebuilding containers                |
| **Auditability**   | Clear separation between configuration and secrets                  |

## The `_FILE` Suffix Pattern

Instead of passing secrets directly as environment variables:

```yaml
# ❌ Insecure - secret visible in docker inspect
environment:
  - SECRET_KEY=my-super-secret-key
```

We use the `_FILE` suffix pattern:

```yaml
# ✅ Secure - secret read from file
environment:
  - SECRET_KEY_FILE=/run/secrets/secret_key
secrets:
  - secret_key
```

The application reads the file contents at runtime, keeping secrets out of the environment.

## Quick Start

### 1. Create Secrets Directory

```bash
cd /path/to/floodingnaque
mkdir -p secrets
```

### 2. Generate Secrets

```bash
cd secrets

# Generate cryptographic keys
python -c "import secrets; print(secrets.token_hex(32), end='')" > secret_key.txt
python -c "import secrets; print(secrets.token_hex(32), end='')" > jwt_secret_key.txt
python -c "import secrets; print(secrets.token_hex(32), end='')" > model_signing_key.txt

# Add your database URL (from Supabase dashboard)
echo -n "postgresql://postgres.xxxx:password@aws-0-region.pooler.supabase.com:6543/postgres?sslmode=require" > database_url.txt

# Add your Redis URL (from Redis Cloud)
echo -n "redis://default:password@host.redis-cloud.com:port" > redis_url.txt

# Add API keys
echo -n "your-openweathermap-api-key" > owm_api_key.txt

# PgBouncer passwords (if using pgbouncer profile)
echo -n "your-db-password" > pgbouncer_db_password.txt
echo -n "your-admin-password" > pgbouncer_admin_password.txt
echo -n "your-stats-password" > pgbouncer_stats_password.txt
```

### 3. Set Permissions

```bash
chmod 600 secrets/*.txt
```

### 4. Deploy

```bash
docker compose -f compose.production.yaml up -d
```

## Secret Files Reference

| Secret File                    | Environment Variable            | Used By         | Description                  |
| ------------------------------ | ------------------------------- | --------------- | ---------------------------- |
| `secret_key.txt`               | `SECRET_KEY_FILE`               | backend         | Flask session encryption     |
| `jwt_secret_key.txt`           | `JWT_SECRET_KEY_FILE`           | backend         | JWT token signing            |
| `database_url.txt`             | `DATABASE_URL_FILE`             | backend, celery | PostgreSQL connection string |
| `redis_url.txt`                | `REDIS_URL_FILE`                | backend, celery | Redis connection string      |
| `owm_api_key.txt`              | `OWM_API_KEY_FILE`              | backend         | OpenWeatherMap API           |
| `model_signing_key.txt`        | `MODEL_SIGNING_KEY_FILE`        | backend         | ML model verification        |
| `pgbouncer_db_password.txt`    | `DB_PASSWORD_FILE`              | pgbouncer       | Database password            |
| `pgbouncer_admin_password.txt` | `PGBOUNCER_ADMIN_PASSWORD_FILE` | pgbouncer       | Admin console                |
| `pgbouncer_stats_password.txt` | `PGBOUNCER_STATS_PASSWORD_FILE` | pgbouncer       | Stats user                   |

## How It Works

### Application-Level (Python)

The `backend/app/utils/secrets.py` module provides the `get_secret()` function:

```python
from app.utils.secrets import get_secret

# Checks SECRET_KEY_FILE first, then SECRET_KEY env var
secret_key = get_secret("SECRET_KEY")

# With a default value
api_key = get_secret("API_KEY", default="dev-key")

# Required secrets raise ValueError if not found
db_url = get_secret("DATABASE_URL", required=True)
```

### Container-Level (Shell)

The PgBouncer entrypoint script (`pgbouncer/entrypoint.sh`) uses:

```bash
read_secret() {
    local var_name="$1"
    local default_value="$2"
    local file_var_name="${var_name}_FILE"

    # Check for _FILE variable first
    eval "local file_path=\${$file_var_name:-}"
    if [ -n "$file_path" ] && [ -f "$file_path" ]; then
        cat "$file_path" | tr -d '\n\r'
        return
    fi

    # Fall back to direct environment variable
    eval "local env_value=\${$var_name:-}"
    if [ -n "$env_value" ]; then
        echo "$env_value"
        return
    fi

    echo "$default_value"
}

# Usage
DB_PASSWORD=$(read_secret "DB_PASSWORD" "fallback")
```

## Docker Compose Configuration

### Secrets Definition (Top-Level)

```yaml
secrets:
  secret_key:
    file: ./secrets/secret_key.txt
  jwt_secret_key:
    file: ./secrets/jwt_secret_key.txt
  database_url:
    file: ./secrets/database_url.txt
```

### Service Configuration

```yaml
services:
  backend:
    environment:
      - SECRET_KEY_FILE=/run/secrets/secret_key
      - JWT_SECRET_KEY_FILE=/run/secrets/jwt_secret_key
      - DATABASE_URL_FILE=/run/secrets/database_url
    secrets:
      - secret_key
      - jwt_secret_key
      - database_url
```

## Fallback Behavior

The implementation supports graceful fallback:

1. **Check `{VAR}_FILE`** - If set and file exists, read from file
2. **Check `{VAR}`** - Fall back to direct environment variable
3. **Use Default** - Use provided default value (if any)
4. **Raise Error** - If `required=True` and no value found

This allows the same codebase to work in:

- **Production**: Secrets mounted as files
- **Development**: Environment variables in `.env` files
- **Testing**: Mocked values

## Docker Swarm Deployments

For Docker Swarm, create secrets using the Docker CLI:

```bash
# Create secrets from files
docker secret create secret_key ./secrets/secret_key.txt
docker secret create jwt_secret_key ./secrets/jwt_secret_key.txt
docker secret create database_url ./secrets/database_url.txt

# Or from stdin (more secure, no file on disk)
echo -n "my-secret" | docker secret create secret_key -

# Deploy the stack
docker stack deploy -c compose.production.yaml floodingnaque
```

## Security Best Practices

### DO ✅

- Use `echo -n` to avoid trailing newlines in secret files
- Set `chmod 600` on all secret files
- Use `.gitignore` to prevent committing secrets
- Rotate secrets periodically
- Use different secrets for different environments
- Validate secrets exist before deploying

### DON'T ❌

- Commit secret files to version control
- Log or print secret values
- Share secrets between environments
- Use weak or default passwords
- Store secrets in Dockerfiles or docker-compose.yaml

## Verification

### Check Secret Files Format

```bash
# Verify no trailing newlines (last byte should NOT be 0a)
for f in secrets/*.txt; do
    echo -n "$f: "
    xxd "$f" | tail -1
done
```

### Verify Secrets Are Mounted

```bash
# Check that secrets are available in container
docker compose -f compose.production.yaml exec backend ls -la /run/secrets/
```

### Test Secret Reading

```bash
# Verify backend can read secrets
docker compose -f compose.production.yaml exec backend python -c "
from app.utils.secrets import get_secret, validate_secrets
print(validate_secrets(['SECRET_KEY', 'DATABASE_URL']))
"
```

## Troubleshooting

### Secret Not Found

```
ValueError: Required secret SECRET_KEY not found
```

**Solution**: Ensure the secret file exists and the service has it in its `secrets:` list.

### Empty Secret Value

Check for trailing newlines:

```bash
cat -A secrets/secret_key.txt
# Should show: your-secret-value$
# NOT: your-secret-value^M$ or your-secret-value$\n
```

### Permission Denied

```bash
chmod 600 secrets/*.txt
# For containers, ensure the file is readable by the container user
```

### Secret File Not Mounted

Verify in docker-compose.yaml:

1. Secret is defined in top-level `secrets:` section
2. Service references the secret in its `secrets:` list
3. Environment variable points to `/run/secrets/<secret_name>`

## Migration from Environment Variables

To migrate from environment variables to Docker Secrets:

1. **Create secret files** from your `.env.production` values
2. **Add secrets** to `compose.production.yaml`
3. **Add `_FILE` suffixes** to environment variables
4. **Test in staging** before production deployment
5. **Remove secrets** from `.env.production` (keep non-sensitive config)

The application will automatically prefer file-based secrets over environment variables.

## Related Documentation

- [Docker Secrets Documentation](https://docs.docker.com/engine/swarm/secrets/)
- [Docker Compose Secrets](https://docs.docker.com/compose/use-secrets/)
- [12-Factor App: Config](https://12factor.net/config)
