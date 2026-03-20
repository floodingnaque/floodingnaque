# syntax=docker/dockerfile:1
# =====================================================
# Floodingnaque Backend - Production Dockerfile
# Multi-stage build for optimized production image
# =====================================================
# Build: DOCKER_BUILDKIT=1 docker build -t floodingnaque-api:latest .
# Run:   docker run -p 5000:5000 --env-file .env floodingnaque-api:latest
# =====================================================

# ===================
# Build Arguments
# ===================
ARG PYTHON_VERSION=3.13

# =====================================================
# Stage 1: Builder - Install dependencies
# =====================================================
FROM python:${PYTHON_VERSION}-slim-bookworm AS builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/opt/venv/bin:$PATH"

# Create virtual environment
RUN python -m venv /opt/venv

# Install build dependencies (Rust NOT required — cryptography 42+ ships manylinux wheels)
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        g++ \
        gcc \
        gfortran \
        libffi-dev \
        libpq-dev

# Copy and install Python dependencies (production-only — lean image)
WORKDIR /build
COPY requirements-prod.txt .

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip setuptools wheel && \
    pip install -r requirements-prod.txt

# =====================================================
# Stage 2: Production - Minimal runtime image
# =====================================================
FROM python:${PYTHON_VERSION}-slim-bookworm AS production

# Labels for container metadata
LABEL maintainer="Floodingnaque Team" \
      version="2.0.0" \
      description="Floodingnaque Flood Prediction API" \
      org.opencontainers.image.source="https://github.com/floodingnaque/floodingnaque"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    PYTHONPATH=/app \
    PATH="/opt/venv/bin:$PATH" \
    APP_ENV=production \
    PORT=5000 \
    HOST=0.0.0.0 \
    GUNICORN_WORKERS=4 \
    GUNICORN_THREADS=2 \
    GUNICORN_TIMEOUT=120 \
    GUNICORN_WORKER_CLASS=sync \
    GUNICORN_MAX_REQUESTS=1000 \
    GUNICORN_MAX_REQUESTS_JITTER=50

# Install runtime dependencies
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
        curl \
        libpq5 \
        tini && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user and directories
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser && \
    mkdir -p /app/models /app/data /app/logs /app/uploads /app/backups /app/.cache /app/certs && \
    chown -R appuser:appgroup /app

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY --chown=appuser:appgroup alembic/ ./alembic/
COPY --chown=appuser:appgroup app/ ./app/
COPY --chown=appuser:appgroup config/ ./config/
# NOTE: models/ and data/ are volume-mounted at runtime, not baked into the image.
# Mount in compose: ./backend/models:/app/models, ./backend/data:/app/data
COPY --chown=appuser:appgroup alembic.ini main.py gunicorn.conf.py ./

# Copy entrypoint script
COPY --chown=appuser:appgroup entrypoint.sh ./
RUN chmod +x /app/entrypoint.sh

# Copy only the backup script needed for scheduled tasks
# (full scripts/ is excluded via .dockerignore — training/eval scripts not needed in prod)
COPY --chown=appuser:appgroup scripts/backup_database.sh scripts/backup_database.py scripts/purge_expired_ips.py ./scripts/

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Use tini as init system for proper signal handling
ENTRYPOINT ["/usr/bin/tini", "--", "/app/entrypoint.sh"]

# Default command: Run with Gunicorn
# Default command: Run with Gunicorn (config in gunicorn.conf.py)
CMD ["gunicorn", "-c", "gunicorn.conf.py", "main:application"]

# =====================================================
# Stage 3: Development - Full dev environment
# =====================================================
FROM production AS development

# Switch back to root to install dev dependencies
USER root

# Install development tools
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
        git \
        htop \
        vim && \
    rm -rf /var/lib/apt/lists/*

# Install full requirements (includes training packages: shap, matplotlib, etc.)
# plus dev-only tools (pytest, mypy, etc.)
COPY requirements.txt requirements-dev.txt ./
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt && \
    pip install -r requirements-dev.txt

# Set development environment
ENV APP_ENV=development \
    FLASK_DEBUG=True \
    LOG_LEVEL=DEBUG

# Switch back to non-root user
USER appuser

# Override command for development (with hot reload via Flask)
CMD ["python", "main.py"]
