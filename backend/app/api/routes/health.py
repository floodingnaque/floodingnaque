"""
Health and Status Routes.

Provides endpoints for health checks and API status monitoring.
Includes dependency health checks for database connections.
"""

import logging
import os
import platform
import sys
import time
from dataclasses import dataclass

from app.api.middleware.rate_limit import get_endpoint_limit, limiter
from app.models.db import get_db_session, get_pool_status
from app.services.predict import get_current_model_info
from app.services.scheduler import scheduler
from app.utils.observability.sentry import is_sentry_enabled
from flask import Blueprint, jsonify, request
from sqlalchemy import text

logger = logging.getLogger(__name__)

# Health Check SLA Configuration
HEALTH_CHECK_RESPONSE_TIME_SLA_MS = int(os.getenv("HEALTH_CHECK_RESPONSE_TIME_SLA_MS", "1000"))
HEALTH_CHECK_DB_TIMEOUT_MS = int(os.getenv("HEALTH_CHECK_DB_TIMEOUT_SECONDS", "5")) * 1000


@dataclass
class SLAStatus:
    """SLA compliance status for health checks."""

    within_sla: bool
    response_time_ms: float
    sla_threshold_ms: int
    message: str


def check_sla_compliance(response_time_ms: float) -> SLAStatus:
    """Check if response time meets SLA threshold."""
    within_sla = response_time_ms <= HEALTH_CHECK_RESPONSE_TIME_SLA_MS

    if within_sla:
        message = f"Response time {response_time_ms:.2f}ms is within SLA ({HEALTH_CHECK_RESPONSE_TIME_SLA_MS}ms)"
    else:
        message = f"Response time {response_time_ms:.2f}ms EXCEEDS SLA ({HEALTH_CHECK_RESPONSE_TIME_SLA_MS}ms)"

    return SLAStatus(
        within_sla=within_sla,
        response_time_ms=response_time_ms,
        sla_threshold_ms=HEALTH_CHECK_RESPONSE_TIME_SLA_MS,
        message=message,
    )


health_bp = Blueprint("health", __name__)


def check_database_health() -> dict:
    """
    Check database connection health.

    Returns:
        dict: Database health status with latency
    """
    try:
        start = time.time()
        with get_db_session() as session:
            # Execute a simple query to test connection
            session.execute(text("SELECT 1"))
        latency_ms = (time.time() - start) * 1000

        return {"status": "healthy", "connected": True, "latency_ms": round(latency_ms, 2)}
    except Exception:
        logger.error("Database health check failed", exc_info=True)
        # Don't expose raw exception details in response - log only
        return {"status": "unhealthy", "connected": False, "error": "Database connection failed"}


def check_external_api_health() -> dict:
    """
    Check circuit breaker status for external APIs.

    Returns:
        dict: External API circuit breaker status
    """
    try:
        from app.utils.resilience.circuit_breaker import meteostat_breaker, openweathermap_breaker, weatherstack_breaker

        return {
            "openweathermap": openweathermap_breaker.get_status(),
            "weatherstack": weatherstack_breaker.get_status(),
            "meteostat": meteostat_breaker.get_status(),
        }
    except ImportError:
        return {"status": "circuit_breaker_not_available"}


def check_redis_health() -> dict:
    """
    Check Redis connection health if Redis is being used.

    Returns:
        dict: Redis health status or indication that Redis is not in use
    """
    storage_url = os.getenv("RATE_LIMIT_STORAGE_URL", "memory://")

    if "redis" not in storage_url.lower():
        return {"status": "not_configured", "message": "Redis not in use"}

    try:
        from urllib.parse import urlparse

        import redis

        parsed = urlparse(storage_url)
        start = time.time()

        r = redis.Redis(
            host=parsed.hostname or "localhost",
            port=parsed.port or 6379,
            password=parsed.password,
            socket_timeout=5,
            socket_connect_timeout=5,
        )

        if r.ping():
            latency_ms = (time.time() - start) * 1000
            return {"status": "healthy", "connected": True, "latency_ms": round(latency_ms, 2)}
        else:
            return {"status": "unhealthy", "connected": False, "error": "Ping failed"}

    except ImportError:
        return {"status": "unavailable", "error": "redis package not installed"}
    except Exception:
        logger.error("Redis health check failed", exc_info=True)
        # Don't expose raw exception details in response - log only
        return {"status": "unhealthy", "connected": False, "error": "Redis connection failed"}


def check_cache_health() -> dict:
    """
    Check cache system health.

    Returns:
        dict: Cache health status
    """
    try:
        from app.utils.resilience.cache import get_cache_stats

        return get_cache_stats()
    except ImportError:
        return {"status": "not_available", "message": "Cache module not available"}
    except Exception:
        logger.error("Cache health check failed", exc_info=True)
        # Don't expose raw exception details in response - log only
        return {"status": "error", "error": "Cache check failed"}


@health_bp.route("/", methods=["GET"])
def root():
    """
    Root endpoint - API information.

    Returns basic API information and available endpoints.

    Returns:
        200: API information object
    ---
    tags:
      - Health
    produces:
      - application/json
    responses:
      200:
        description: API information
        schema:
          type: object
          properties:
            name:
              type: string
              example: Floodingnaque API
            version:
              type: string
              example: "2.0.0"
            description:
              type: string
            endpoints:
              type: object
            documentation:
              type: string
    """
    return (
        jsonify(
            {
                "name": "Floodingnaque API",
                "version": "2.0.0",
                "description": "Flood prediction API with weather data ingestion",
                "endpoints": {
                    "status": "/status",
                    "health": "/health",
                    "ingest": "/ingest",
                    "data": "/data",
                    "predict": "/predict",
                    "docs": "/api/docs",
                },
                "documentation": f"{request.url_root}api/docs",
            }
        ),
        200,
    )


@health_bp.route("/status", methods=["GET"])
@limiter.limit(get_endpoint_limit("status"))
def status():
    """
    Quick health check endpoint.

    Returns basic health status with database connectivity and model status.
    Use /health for comprehensive health information.

    Returns:
        200: System is healthy
        503: System is degraded (database not connected)
    ---
    tags:
      - Health
    produces:
      - application/json
    responses:
      200:
        description: System healthy
        schema:
          type: object
          properties:
            status:
              type: string
              enum: [running]
            database:
              type: string
              enum: [healthy, unhealthy]
            database_latency_ms:
              type: number
            model:
              type: string
              enum: [loaded, not found]
            model_version:
              type: string
            model_accuracy:
              type: number
      503:
        description: System degraded
    """
    model_info = get_current_model_info()
    model_status = "loaded" if model_info else "not found"

    # Check database health
    db_health = check_database_health()

    response = {
        "status": "running",
        "database": db_health["status"],
        "database_latency_ms": db_health.get("latency_ms"),
        "model": model_status,
    }

    if model_info and model_info.get("metadata"):
        response["model_version"] = model_info["metadata"].get("version")
        response["model_accuracy"] = model_info["metadata"].get("metrics", {}).get("accuracy")

    # Set appropriate HTTP status based on health
    http_status = 200 if db_health["connected"] else 503

    return jsonify(response), http_status


@health_bp.route("/health", methods=["GET"])
@limiter.limit(get_endpoint_limit("status"))
def health():
    """
    Comprehensive health check endpoint with SLA monitoring.

    Returns detailed health status including all dependencies:
    - Database connection and pool status
    - Redis connection (if configured)
    - Cache system status
    - ML model availability and version
    - External API circuit breakers
    - Scheduler status
    - Sentry monitoring status
    - Response time SLA compliance

    Returns:
        200: All systems healthy
        503: One or more systems degraded
    ---
    tags:
      - Health
    produces:
      - application/json
    responses:
      200:
        description: Detailed health status
        schema:
          type: object
          properties:
            status:
              type: string
              enum: [healthy, degraded]
            timestamp:
              type: string
              format: date-time
            sla:
              type: object
              properties:
                within_sla:
                  type: boolean
                response_time_ms:
                  type: number
                threshold_ms:
                  type: integer
            checks:
              type: object
              properties:
                database:
                  type: object
                database_pool:
                  type: object
                redis:
                  type: object
                cache:
                  type: object
                model_available:
                  type: boolean
                scheduler_running:
                  type: boolean
                sentry_enabled:
                  type: boolean
            model:
              type: object
            system:
              type: object
      503:
        description: System degraded
    """
    start_time = time.perf_counter()

    model_info = get_current_model_info()
    model_available = model_info is not None

    # Check database health
    db_health = check_database_health()

    # Check external API circuit breakers
    external_apis = check_external_api_health()

    # Check Redis health (if configured)
    redis_health = check_redis_health()

    # Check cache health
    cache_health = check_cache_health()

    # Get database pool status
    pool_status = get_pool_status()

    # Determine overall health status
    redis_ok = redis_health.get("status") in ("healthy", "not_configured")
    is_healthy = db_health["connected"] and model_available and redis_ok

    # Calculate response time and SLA compliance
    response_time_ms = (time.perf_counter() - start_time) * 1000
    sla_status = check_sla_compliance(response_time_ms)

    if not sla_status.within_sla:
        logger.warning(sla_status.message)

    response = {
        "status": "healthy" if is_healthy else "degraded",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "sla": {
            "within_sla": sla_status.within_sla,
            "response_time_ms": round(sla_status.response_time_ms, 2),
            "threshold_ms": sla_status.sla_threshold_ms,
            "message": sla_status.message,
        },
        "checks": {
            "database": db_health,
            "database_pool": pool_status,
            "redis": redis_health,
            "cache": cache_health,
            "model_available": model_available,
            "scheduler_running": scheduler.running if hasattr(scheduler, "running") else False,
            "external_apis": external_apis,
            "sentry_enabled": is_sentry_enabled(),
        },
        # System info sanitized to avoid information disclosure
        "system": {
            "python_version": ".".join(sys.version.split()[0].split(".")[:2]),  # Major.minor only
        },
    }

    if model_info:
        model_path = model_info.get("model_path", "")
        model_file = os.path.basename(model_path) if model_path else None
        file_size_bytes = None
        checksum = model_info.get("checksum")
        if model_path and os.path.isfile(model_path):
            file_size_bytes = os.path.getsize(model_path)

        response["model"] = {
            "loaded": True,
            "type": model_info.get("model_type"),
            "features_count": len(model_info.get("features", [])),
            "model_file": model_file,
            "file_size_bytes": file_size_bytes,
            "checksum": checksum,
        }
        if model_info.get("metadata"):
            metadata = model_info["metadata"]
            response["model"]["version"] = metadata.get("version")
            response["model"]["created_at"] = metadata.get("created_at")
            response["model"]["metrics"] = metadata.get("metrics", {})
            response["model"]["training_data"] = metadata.get("training_data", {})
            response["model"]["model_parameters"] = metadata.get("model_parameters", {})
    else:
        response["model"] = {"loaded": False}

    # Set appropriate HTTP status
    http_status = 200 if is_healthy else 503

    return jsonify(response), http_status


@health_bp.route("/live", methods=["GET"])
@limiter.limit(get_endpoint_limit("status"))
def liveness():
    """
    Kubernetes liveness probe endpoint.

    Simple endpoint for Kubernetes to check if the service is alive.
    Always returns 200 if the service is running.

    Returns:
        200: Service is alive
    ---
    tags:
      - Health
      - Kubernetes
    produces:
      - application/json
    responses:
      200:
        description: Service is alive
        schema:
          type: object
          properties:
            status:
              type: string
              example: alive
            timestamp:
              type: string
              format: date-time
    """
    return jsonify({"status": "alive", "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}), 200


@health_bp.route("/ready", methods=["GET"])
@limiter.limit(get_endpoint_limit("status"))
def readiness():
    """
    Kubernetes readiness probe endpoint.

    Checks if the service is ready to accept traffic:
    - Database must be connected
    - ML model must be available

    Returns:
        200: Service is ready
        503: Service is not ready
    ---
    tags:
      - Health
      - Kubernetes
    produces:
      - application/json
    responses:
      200:
        description: Service is ready
        schema:
          type: object
          properties:
            status:
              type: string
              example: ready
            timestamp:
              type: string
              format: date-time
            checks:
              type: object
              properties:
                database:
                  type: string
                model_available:
                  type: boolean
      503:
        description: Service is not ready
    """
    # Check database connectivity
    db_health = check_database_health()

    # Check if model is available
    model_info = get_current_model_info()
    model_available = model_info is not None

    is_ready = db_health["connected"] and model_available

    response = {
        "status": "ready" if is_ready else "not_ready",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "checks": {"database": db_health["status"], "model_available": model_available},
    }

    http_status = 200 if is_ready else 503
    return jsonify(response), http_status
