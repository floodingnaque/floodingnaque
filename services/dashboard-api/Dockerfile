# ─────────────────────────────────────────────────
# Dashboard API Service — Multi-stage Dockerfile
# ─────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Production stage ────────────────────────────
FROM python:3.12-slim AS production

LABEL maintainer="floodingnaque-team"
LABEL service="dashboard-api"

RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

WORKDIR /app

COPY --from=builder /install /usr/local
COPY . .
COPY ../shared /app/shared

RUN chown -R appuser:appuser /app

USER appuser

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=5005 \
    SERVICE_NAME=dashboard-api

EXPOSE 5005

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5005/health')" || exit 1

CMD ["python", "main.py"]

# ── Development stage ───────────────────────────
FROM production AS development

USER root
RUN pip install --no-cache-dir debugpy watchdog flask-debugtoolbar
USER appuser

ENV FLASK_DEBUG=true

CMD ["python", "-m", "debugpy", "--listen", "0.0.0.0:5685", "main.py"]
