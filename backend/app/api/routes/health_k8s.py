"""
Kubernetes Health Probe Endpoints.

Provides liveness and readiness probes for Kubernetes deployments.
"""

from datetime import datetime, timezone

from app.api.middleware.rate_limit import limiter
from app.utils.api_constants import HTTP_OK, HTTP_SERVICE_UNAVAILABLE
from app.utils.observability.logging import get_logger
from flask import Blueprint, g, jsonify

logger = get_logger(__name__)

health_k8s_bp = Blueprint("health_k8s", __name__)


@health_k8s_bp.route("/health/live", methods=["GET"])
@limiter.exempt  # Don't rate limit health checks
def liveness_probe():
    """
    Kubernetes liveness probe.

    Returns minimal health status - if this fails, the container should be restarted.
    Only checks if the application is responsive.

    Returns:
        Liveness status
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        # Basic liveness check - just check if app is running
        return (
            jsonify(
                {
                    "status": "healthy",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "probe": "liveness",
                    "request_id": request_id,
                }
            ),
            HTTP_OK,
        )

    except Exception as e:
        logger.error(f"Liveness probe failed [{request_id}]: {str(e)}")
        return (
            jsonify(
                {
                    "status": "unhealthy",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "probe": "liveness",
                    "error": "Application not responding",
                    "request_id": request_id,
                }
            ),
            HTTP_SERVICE_UNAVAILABLE,
        )


@health_k8s_bp.route("/health/ready", methods=["GET"])
@limiter.exempt  # Don't rate limit health checks
def readiness_probe():
    """
    Kubernetes readiness probe.

    Returns readiness status - if this fails, the container should be removed from service.
    Checks if the application is ready to serve traffic.

    Returns:
        Readiness status with dependency checks
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        checks = {
            "api": "ready",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "probe": "readiness",
            "request_id": request_id,
        }

        # Check database connectivity
        try:
            from app.api.routes.health import check_database_health

            db_status = check_database_health()
            checks["database"] = "ready" if db_status == "healthy" else "not_ready"
        except Exception as e:
            logger.warning(f"Database readiness check failed [{request_id}]: {e}")
            checks["database"] = "not_ready"

        # Check model availability
        try:
            from app.api.routes.health import check_model_health

            model_status = check_model_health()
            checks["model"] = "ready" if model_status == "healthy" else "not_ready"
        except Exception as e:
            logger.warning(f"Model readiness check failed [{request_id}]: {e}")
            checks["model"] = "not_ready"

        # Determine overall readiness
        overall_ready = all(status == "ready" for status in checks.values() if isinstance(status, str))

        status_code = HTTP_OK if overall_ready else HTTP_SERVICE_UNAVAILABLE

        return (
            jsonify({"status": "ready" if overall_ready else "not_ready", "checks": checks, "request_id": request_id}),
            status_code,
        )

    except Exception as e:
        logger.error(f"Readiness probe failed [{request_id}]: {str(e)}")
        return (
            jsonify(
                {
                    "status": "not_ready",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "probe": "readiness",
                    "error": "Readiness check failed",
                    "request_id": request_id,
                }
            ),
            HTTP_SERVICE_UNAVAILABLE,
        )
