"""
Shared health check module for Floodingnaque microservices.

Provides standardized health check endpoints that every service
registers. Supports Kubernetes liveness/readiness probes.
"""

import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from flask import Blueprint, jsonify

logger = logging.getLogger(__name__)

# Service start time for uptime calculation
_start_time = time.time()


def create_health_blueprint(service_name: str, version: str = "1.0.0") -> Blueprint:
    """
    Create a standardized health check blueprint for a service.

    Registers:
      GET /health       - Full health report
      GET /health/live  - Kubernetes liveness probe (always 200 if process alive)
      GET /health/ready - Kubernetes readiness probe (checks dependencies)
      GET /status       - Simple status string

    Args:
        service_name: Name of the microservice
        version: Service version string

    Returns:
        Flask Blueprint with health routes
    """
    health_bp = Blueprint("health", __name__)

    # Optional dependency checkers registered by the service
    _dependency_checks: Dict[str, callable] = {}

    def register_check(name: str, check_fn: callable):
        """Register a dependency health check function."""
        _dependency_checks[name] = check_fn

    # Attach register_check to blueprint for external use
    health_bp.register_dependency_check = register_check

    @health_bp.route("/health")
    def health():
        """Full health report with dependency checks."""
        uptime = time.time() - _start_time
        dependencies = {}
        overall_healthy = True

        for dep_name, check_fn in _dependency_checks.items():
            try:
                result = check_fn()
                dependencies[dep_name] = {
                    "status": "healthy" if result else "unhealthy",
                    "ok": bool(result),
                }
                if not result:
                    overall_healthy = False
            except Exception as e:
                dependencies[dep_name] = {
                    "status": "unhealthy",
                    "ok": False,
                    "error": str(e),
                }
                overall_healthy = False

        response = {
            "service": service_name,
            "version": version,
            "status": "healthy" if overall_healthy else "degraded",
            "uptime_seconds": round(uptime, 2),
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "environment": os.getenv("APP_ENV", "development"),
            "dependencies": dependencies,
        }

        status_code = 200 if overall_healthy else 503
        return jsonify(response), status_code

    @health_bp.route("/health/live")
    def liveness():
        """Kubernetes liveness probe - process is alive."""
        return jsonify({"status": "alive", "service": service_name}), 200

    @health_bp.route("/health/ready")
    def readiness():
        """Kubernetes readiness probe - ready to accept traffic."""
        for dep_name, check_fn in _dependency_checks.items():
            try:
                if not check_fn():
                    return jsonify({
                        "status": "not_ready",
                        "service": service_name,
                        "failed_check": dep_name,
                    }), 503
            except Exception as e:
                return jsonify({
                    "status": "not_ready",
                    "service": service_name,
                    "failed_check": dep_name,
                    "error": str(e),
                }), 503

        return jsonify({"status": "ready", "service": service_name}), 200

    @health_bp.route("/status")
    def status():
        """Simple status endpoint."""
        return jsonify({
            "service": service_name,
            "status": "running",
            "version": version,
        })

    return health_bp
