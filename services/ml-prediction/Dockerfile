# syntax=docker/dockerfile:1
# =====================================================
# ML Prediction Service — Dockerfile
# =====================================================

ARG PYTHON_VERSION=3.13
FROM python:${PYTHON_VERSION}-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

RUN python -m venv /opt/venv

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
        build-essential g++ gcc gfortran libpq-dev libffi-dev

WORKDIR /build
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && pip install -r requirements.txt

# ── Production stage ──────────────────────────────────────────────────────
FROM python:${PYTHON_VERSION}-slim-bookworm AS production

LABEL maintainer="Floodingnaque Team" \
      service="ml-prediction" \
      version="1.0.0"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH="/opt/venv/bin:$PATH" \
    SERVICE_NAME=ml-prediction \
    PORT=5002

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
        curl libpq5 libgomp1 && \
    rm -rf /var/lib/apt/lists/*

RUN groupadd -r appuser && useradd -r -g appuser -d /app appuser

COPY --from=builder /opt/venv /opt/venv
WORKDIR /app
COPY . .
COPY ../shared /app/shared

# Model directory (mount or bake in)
RUN mkdir -p /app/models && chown -R appuser:appuser /app

USER appuser

EXPOSE 5002

HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=30s \
    CMD curl -f http://localhost:5002/health || exit 1

CMD ["gunicorn", "--bind", "0.0.0.0:5002", "--workers", "2", "--threads", "2", "--timeout", "120", "main:create_app()"]

# ── Development ───────────────────────────────────────────────────────────
FROM production AS development
ENV FLASK_DEBUG=True
CMD ["python", "main.py"]
