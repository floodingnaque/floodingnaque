"""
System Monitoring Routes.

Provides admin-only endpoints for system observability:
- Uptime monitoring
- API response time tracking
- Model prediction drift detection
- Alert delivery confirmation tracking
- Celery Dead Letter Queue management
"""

import logging
from functools import wraps

from app.api.middleware.auth import require_auth
from app.services.monitoring import (
    get_alert_delivery_stats,
    get_api_response_stats,
    get_monitoring_summary,
    get_prediction_drift_stats,
    get_uptime_stats,
)
from app.utils.api_constants import HTTP_OK
from app.utils.api_responses import api_error
from flask import Blueprint, g, jsonify, request

logger = logging.getLogger(__name__)

admin_monitoring_bp = Blueprint("admin_monitoring", __name__)


def require_admin(f):
    """Decorator that requires admin role after authentication."""

    @wraps(f)
    @require_auth
    def decorated(*args, **kwargs):
        if getattr(g, "current_user_role", None) != "admin":
            return api_error("ADMIN_REQUIRED", "Admin access required", 403)
        return f(*args, **kwargs)

    return decorated


# ---------------------------------------------------------------------------
# GET /  —  combined monitoring dashboard
# ---------------------------------------------------------------------------


@admin_monitoring_bp.route("", methods=["GET"])
@admin_monitoring_bp.route("/", methods=["GET"])
@require_admin
def monitoring_dashboard():
    """Return combined monitoring summary (uptime + API + drift + alerts)."""
    try:
        return (
            jsonify(
                {
                    "success": True,
                    "data": get_monitoring_summary(),
                }
            ),
            HTTP_OK,
        )
    except Exception as exc:
        logger.error("Error fetching monitoring summary: %s", exc)
        return api_error("MONITORING_ERROR", f"Failed to fetch monitoring summary: {exc}", 500)


# ---------------------------------------------------------------------------
# GET /uptime  —  uptime statistics
# ---------------------------------------------------------------------------


@admin_monitoring_bp.route("/uptime", methods=["GET"])
@require_admin
def uptime():
    """Return process uptime and health-check history."""
    try:
        return (
            jsonify(
                {
                    "success": True,
                    "data": get_uptime_stats(),
                }
            ),
            HTTP_OK,
        )
    except Exception as exc:
        logger.error("Error fetching uptime stats: %s", exc)
        return api_error("UPTIME_ERROR", f"Failed to fetch uptime: {exc}", 500)


# ---------------------------------------------------------------------------
# GET /api-responses  —  API response tracking
# ---------------------------------------------------------------------------


@admin_monitoring_bp.route("/api-responses", methods=["GET"])
@require_admin
def api_responses():
    """Return API response time statistics.

    Query params:
      minutes (int, default=60): lookback window
    """
    try:
        minutes = request.args.get("minutes", 60, type=int)
        minutes = min(max(minutes, 1), 1440)  # Cap at 24h
        return (
            jsonify(
                {
                    "success": True,
                    "data": get_api_response_stats(minutes=minutes),
                }
            ),
            HTTP_OK,
        )
    except Exception as exc:
        logger.error("Error fetching API response stats: %s", exc)
        return api_error("API_RESPONSE_ERROR", f"Failed to fetch API response stats: {exc}", 500)


# ---------------------------------------------------------------------------
# GET /prediction-drift  —  model prediction drift
# ---------------------------------------------------------------------------


@admin_monitoring_bp.route("/prediction-drift", methods=["GET"])
@require_admin
def prediction_drift():
    """Return prediction drift statistics.

    Query params:
      minutes (int, default=60): lookback window
    """
    try:
        minutes = request.args.get("minutes", 60, type=int)
        minutes = min(max(minutes, 1), 1440)
        return (
            jsonify(
                {
                    "success": True,
                    "data": get_prediction_drift_stats(window_minutes=minutes),
                }
            ),
            HTTP_OK,
        )
    except Exception as exc:
        logger.error("Error fetching prediction drift: %s", exc)
        return api_error("DRIFT_ERROR", f"Failed to fetch prediction drift: {exc}", 500)


# ---------------------------------------------------------------------------
# GET /alert-delivery  —  alert delivery tracking
# ---------------------------------------------------------------------------


@admin_monitoring_bp.route("/alert-delivery", methods=["GET"])
@require_admin
def alert_delivery():
    """Return alert delivery statistics.

    Query params:
      hours (int, default=24): lookback window
    """
    try:
        hours = request.args.get("hours", 24, type=int)
        hours = min(max(hours, 1), 168)  # Cap at 7 days
        return (
            jsonify(
                {
                    "success": True,
                    "data": get_alert_delivery_stats(hours=hours),
                }
            ),
            HTTP_OK,
        )
    except Exception as exc:
        logger.error("Error fetching alert delivery stats: %s", exc)
        return api_error("ALERT_DELIVERY_ERROR", f"Failed to fetch alert delivery stats: {exc}", 500)


# ---------------------------------------------------------------------------
# GET /celery/dlq  —  Dead Letter Queue inspection
# ---------------------------------------------------------------------------


@admin_monitoring_bp.route("/celery/dlq", methods=["GET"])
@require_admin
def celery_dlq():
    """Return dead letter queue entries and count.

    Query params:
      limit (int, default=50): max entries to return (capped at 200)
    """
    try:
        from app.services.celery_app import get_dlq_count, get_dlq_entries

        limit = request.args.get("limit", 50, type=int)
        limit = min(max(limit, 1), 200)

        entries = get_dlq_entries(limit=limit)
        count = get_dlq_count()

        return (
            jsonify(
                {
                    "success": True,
                    "data": {
                        "total": count,
                        "entries": entries,
                    },
                }
            ),
            HTTP_OK,
        )
    except Exception as exc:
        logger.error("Error fetching DLQ: %s", exc)
        return api_error("DLQ_ERROR", f"Failed to fetch dead letter queue: {exc}", 500)


# ---------------------------------------------------------------------------
# POST /celery/dlq/replay  —  replay oldest DLQ entry
# ---------------------------------------------------------------------------


@admin_monitoring_bp.route("/celery/dlq/replay", methods=["POST"])
@require_admin
def celery_dlq_replay():
    """Replay the oldest entry from the dead letter queue."""
    try:
        from app.services.celery_app import replay_dlq_entry

        result = replay_dlq_entry()
        logger.info("Admin %s replayed DLQ entry: %s", getattr(g, "current_user_email", "unknown"), result)

        return (
            jsonify(
                {
                    "success": True,
                    "data": result,
                }
            ),
            HTTP_OK,
        )
    except Exception as exc:
        logger.error("Error replaying DLQ entry: %s", exc)
        return api_error("DLQ_REPLAY_ERROR", f"Failed to replay DLQ entry: {exc}", 500)


# ---------------------------------------------------------------------------
# DELETE /celery/dlq  —  clear all DLQ entries
# ---------------------------------------------------------------------------


@admin_monitoring_bp.route("/celery/dlq", methods=["DELETE"])
@require_admin
def celery_dlq_clear():
    """Clear all entries from the dead letter queue."""
    try:
        from app.services.celery_app import clear_dlq

        count = clear_dlq()
        logger.info("Admin %s cleared DLQ (%d entries)", getattr(g, "current_user_email", "unknown"), count)

        return (
            jsonify(
                {
                    "success": True,
                    "data": {"cleared": count},
                }
            ),
            HTTP_OK,
        )
    except Exception as exc:
        logger.error("Error clearing DLQ: %s", exc)
        return api_error("DLQ_CLEAR_ERROR", f"Failed to clear dead letter queue: {exc}", 500)
