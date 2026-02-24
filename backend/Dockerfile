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
ARG PYTHON_VERSION=3.12

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

# Copy and install Python dependencies
WORKDIR /build
COPY requirements.txt .

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt

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
        tini

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
COPY --chown=appuser:appgroup models/ ./models/
COPY --chown=appuser:appgroup data/synthetic_dataset.csv ./data/
COPY --chown=appuser:appgroup alembic.ini main.py ./

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Use tini as init system for proper signal handling
ENTRYPOINT ["/usr/bin/tini", "--"]

# Default command: Run with Gunicorn (Datadog APM tracing if available)
CMD ["sh", "-c", "\
if command -v ddtrace-run >/dev/null 2>&1; then \
  exec ddtrace-run gunicorn main:application \
    --bind ${HOST}:${PORT} \
    --workers ${GUNICORN_WORKERS} \
    --threads ${GUNICORN_THREADS} \
    --timeout ${GUNICORN_TIMEOUT} \
    --worker-class ${GUNICORN_WORKER_CLASS} \
    --max-requests ${GUNICORN_MAX_REQUESTS} \
    --max-requests-jitter ${GUNICORN_MAX_REQUESTS_JITTER} \
    --access-logfile - \
    --error-logfile - \
    --capture-output \
    --enable-stdio-inheritance \
    --preload; \
else \
  exec gunicorn main:application \
    --bind ${HOST}:${PORT} \
    --workers ${GUNICORN_WORKERS} \
    --threads ${GUNICORN_THREADS} \
    --timeout ${GUNICORN_TIMEOUT} \
    --worker-class ${GUNICORN_WORKER_CLASS} \
    --max-requests ${GUNICORN_MAX_REQUESTS} \
    --max-requests-jitter ${GUNICORN_MAX_REQUESTS_JITTER} \
    --access-logfile - \
    --error-logfile - \
    --capture-output \
    --enable-stdio-inheritance \
    --preload; \
fi"]

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
        vim

# Install development dependencies
COPY requirements-dev.txt ./
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements-dev.txt || true

# Set development environment
ENV APP_ENV=development \
    FLASK_DEBUG=True \
    LOG_LEVEL=DEBUG

# Switch back to non-root user
USER appuser

# Override command for development (with hot reload via Flask)
CMD ["python", "main.py"]
