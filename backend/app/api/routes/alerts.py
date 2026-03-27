"""
Alert Routes.

Provides API endpoints for retrieving alerts and alert history.
"""

import json
import logging
import math
from datetime import datetime, timedelta, timezone
from functools import wraps

from app.api.middleware.auth import require_auth
from app.api.middleware.rate_limit import limiter
from app.models.db import AlertHistory, get_db_session
from app.services.alerts import get_alert_system
from app.utils.api_constants import (
    HTTP_BAD_REQUEST,
    HTTP_INTERNAL_ERROR,
    HTTP_NOT_FOUND,
    HTTP_OK,
)
from app.utils.api_responses import api_error
from flask import Blueprint, g, jsonify, request
from sqlalchemy import desc, func

logger = logging.getLogger(__name__)

alerts_bp = Blueprint("alerts", __name__)


@alerts_bp.route("", methods=["GET"])
@limiter.limit("60 per minute")
def get_alerts():
    """
    Get list of alerts with pagination and filtering.

    Query Parameters:
        page (int): Page number, 1-based (default: 1)
        limit (int): Maximum number of alerts to return (default: 20, max: 500)
        risk_level (int): Filter by risk level (0=Safe, 1=Alert, 2=Critical)
        status (str): Filter by delivery status (delivered/pending/failed)
        acknowledged (str): Filter by acknowledgement (true/false)
        start_date (str): Filter alerts after this date (ISO format)
        end_date (str): Filter alerts before this date (ISO format)

    Returns:
        200: List of alerts with pagination info
    ---
    tags:
      - Alerts
    parameters:
      - in: query
        name: page
        type: integer
        default: 1
      - in: query
        name: limit
        type: integer
        default: 20
      - in: query
        name: risk_level
        type: integer
        enum: [0, 1, 2]
      - in: query
        name: status
        type: string
        enum: [delivered, pending, failed]
      - in: query
        name: acknowledged
        type: string
        enum: [true, false]
    responses:
      200:
        description: List of alerts
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        # Parse query parameters - page-based pagination
        page = max(request.args.get("page", 1, type=int), 1)
        limit = min(max(request.args.get("limit", 20, type=int), 1), 500)
        offset = (page - 1) * limit
        risk_level = request.args.get("risk_level", type=int)
        status = request.args.get("status", type=str)
        acknowledged_param = request.args.get("acknowledged", type=str)
        start_date = request.args.get("start_date", type=str)
        end_date = request.args.get("end_date", type=str)

        with get_db_session() as session:
            query = session.query(AlertHistory).filter(AlertHistory.is_deleted.is_(False))

            # Apply filters
            if risk_level is not None:
                if risk_level not in [0, 1, 2]:
                    return api_error("ValidationError", "Risk level must be 0, 1, or 2", HTTP_BAD_REQUEST, request_id)
                query = query.filter(AlertHistory.risk_level == risk_level)

            if status:
                valid_statuses = ["delivered", "pending", "failed"]
                if status not in valid_statuses:
                    return api_error(
                        "ValidationError", f"Status must be one of: {valid_statuses}", HTTP_BAD_REQUEST, request_id
                    )
                query = query.filter(AlertHistory.delivery_status == status)

            if acknowledged_param is not None:
                ack_bool = acknowledged_param.lower() in ("true", "1", "yes")
                query = query.filter(AlertHistory.acknowledged == ack_bool)

            if start_date:
                try:
                    start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
                    query = query.filter(AlertHistory.created_at >= start_dt)
                except ValueError:
                    return api_error("ValidationError", "Invalid start_date format", HTTP_BAD_REQUEST, request_id)

            if end_date:
                try:
                    end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                    query = query.filter(AlertHistory.created_at <= end_dt)
                except ValueError:
                    return api_error("ValidationError", "Invalid end_date format", HTTP_BAD_REQUEST, request_id)

            # Get total count, then paginate
            total = query.count()
            pages = max(math.ceil(total / limit), 1)

            alerts = query.order_by(desc(AlertHistory.created_at)).offset(offset).limit(limit).all()

            # Format response to match PaginatedResponse<Alert>
            alerts_data = []
            for alert in alerts:
                created_iso = alert.created_at.isoformat() if alert.created_at else None
                alert_entry = {
                    "id": alert.id,
                    "risk_level": alert.risk_level,
                    "risk_label": alert.risk_label,
                    "location": alert.location,
                    "message": alert.message,
                    "delivery_status": alert.delivery_status,
                    "delivery_channel": alert.delivery_channel,
                    "delivered_at": alert.delivered_at.isoformat() if alert.delivered_at else None,
                    "created_at": created_iso,
                    "triggered_at": created_iso,
                    "acknowledged": bool(alert.acknowledged),
                    "acknowledged_at": alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
                    # Smart alert fields
                    "confidence_score": alert.confidence_score,
                    "rainfall_3h": alert.rainfall_3h,
                    "escalation_state": alert.escalation_state,
                    "contributing_factors": (
                        json.loads(alert.contributing_factors) if alert.contributing_factors else []
                    ),
                }
                alerts_data.append(alert_entry)

        return (
            jsonify(
                {
                    "success": True,
                    "data": alerts_data,
                    "total": total,
                    "page": page,
                    "limit": limit,
                    "pages": pages,
                    "request_id": request_id,
                }
            ),
            HTTP_OK,
        )

    except Exception as e:
        logger.error(f"Error fetching alerts [{request_id}]: {str(e)}", exc_info=True)
        return api_error("FetchFailed", "Failed to fetch alerts", HTTP_INTERNAL_ERROR, request_id)


@alerts_bp.route("/<int:alert_id>", methods=["GET"])
@limiter.limit("60 per minute")
def get_alert_by_id(alert_id):
    """
    Get a specific alert by ID.

    Returns:
        200: Alert details
        404: Alert not found
    ---
    tags:
      - Alerts
    parameters:
      - in: path
        name: alert_id
        type: integer
        required: true
    responses:
      200:
        description: Alert details
      404:
        description: Not found
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        with get_db_session() as session:
            alert = (
                session.query(AlertHistory)
                .filter(AlertHistory.id == alert_id, AlertHistory.is_deleted.is_(False))
                .first()
            )

            if not alert:
                return api_error("NotFound", f"Alert with id {alert_id} not found", HTTP_NOT_FOUND, request_id)

            alert_data = {
                "id": alert.id,
                "prediction_id": alert.prediction_id,
                "risk_level": alert.risk_level,
                "risk_label": alert.risk_label,
                "location": alert.location,
                "recipients": alert.recipients,
                "message": alert.message,
                "delivery_status": alert.delivery_status,
                "delivery_channel": alert.delivery_channel,
                "error_message": alert.error_message,
                "delivered_at": alert.delivered_at.isoformat() if alert.delivered_at else None,
                "created_at": alert.created_at.isoformat() if alert.created_at else None,
                # Smart alert fields
                "confidence_score": alert.confidence_score,
                "rainfall_3h": alert.rainfall_3h,
                "escalation_state": alert.escalation_state,
                "escalation_reason": alert.escalation_reason,
                "suppressed": alert.suppressed,
                "contributing_factors": (json.loads(alert.contributing_factors) if alert.contributing_factors else []),
            }

        return jsonify({"success": True, "data": alert_data, "request_id": request_id}), HTTP_OK

    except Exception as e:
        logger.error(f"Error fetching alert {alert_id} [{request_id}]: {str(e)}", exc_info=True)
        return api_error("FetchFailed", "Failed to fetch alert", HTTP_INTERNAL_ERROR, request_id)


@alerts_bp.route("/<int:alert_id>/acknowledge", methods=["PATCH"])
@limiter.limit("30 per minute")
@require_auth
def acknowledge_alert(alert_id):
    """
    Acknowledge a single alert.

    Returns:
        200: Alert acknowledged successfully
        404: Alert not found
    ---
    tags:
      - Alerts
    parameters:
      - in: path
        name: alert_id
        type: integer
        required: true
    responses:
      200:
        description: Alert acknowledged
      404:
        description: Not found
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        with get_db_session() as session:
            alert = (
                session.query(AlertHistory)
                .filter(AlertHistory.id == alert_id, AlertHistory.is_deleted.is_(False))
                .first()
            )

            if not alert:
                return api_error("NotFound", f"Alert with id {alert_id} not found", HTTP_NOT_FOUND, request_id)

            if alert.acknowledged:
                return (
                    jsonify({"success": True, "message": "Alert already acknowledged", "request_id": request_id}),
                    HTTP_OK,
                )

            alert.acknowledged = True
            alert.acknowledged_at = datetime.now(timezone.utc)

        logger.info(f"Alert {alert_id} acknowledged [{request_id}]")
        return jsonify({"success": True, "message": "Alert acknowledged", "request_id": request_id}), HTTP_OK

    except Exception as e:
        logger.error(f"Error acknowledging alert {alert_id} [{request_id}]: {str(e)}", exc_info=True)
        return api_error("AcknowledgeFailed", "Failed to acknowledge alert", HTTP_INTERNAL_ERROR, request_id)


@alerts_bp.route("/acknowledge-all", methods=["POST"])
@limiter.limit("10 per minute")
@require_auth
def acknowledge_all_alerts():
    """
    Acknowledge all pending (unacknowledged) alerts.

    Returns:
        200: Count of acknowledged alerts
    ---
    tags:
      - Alerts
    responses:
      200:
        description: All pending alerts acknowledged
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        with get_db_session() as session:
            now = datetime.now(timezone.utc)
            updated = (
                session.query(AlertHistory)
                .filter(
                    AlertHistory.is_deleted.is_(False),
                    AlertHistory.acknowledged.is_(False),
                )
                .update({"acknowledged": True, "acknowledged_at": now}, synchronize_session="fetch")
            )

        logger.info(f"Acknowledged {updated} alerts [{request_id}]")
        return (
            jsonify(
                {
                    "success": True,
                    "message": f"Acknowledged {updated} alert(s)",
                    "acknowledged_count": updated,
                    "request_id": request_id,
                }
            ),
            HTTP_OK,
        )

    except Exception as e:
        logger.error(f"Error acknowledging all alerts [{request_id}]: {str(e)}", exc_info=True)
        return api_error("AcknowledgeFailed", "Failed to acknowledge alerts", HTTP_INTERNAL_ERROR, request_id)


@alerts_bp.route("/history", methods=["GET"])
@limiter.limit("30 per minute")
def get_alert_history():
    """
    Get alert history with summary statistics.

    Query Parameters:
        days (int): Number of days of history to retrieve (default: 7, max: 90)
        risk_level (int): Filter by risk level (optional)

    Returns:
        200: Alert history with summary statistics
    ---
    tags:
      - Alerts
    parameters:
      - in: query
        name: days
        type: integer
        default: 7
      - in: query
        name: risk_level
        type: integer
    responses:
      200:
        description: Alert history with statistics
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        days = min(request.args.get("days", 7, type=int), 90)
        risk_level = request.args.get("risk_level", type=int)

        if days < 1:
            return api_error("ValidationError", "Days must be at least 1", HTTP_BAD_REQUEST, request_id)

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

        with get_db_session() as session:
            query = session.query(AlertHistory).filter(
                AlertHistory.is_deleted.is_(False), AlertHistory.created_at >= cutoff_date
            )

            if risk_level is not None:
                query = query.filter(AlertHistory.risk_level == risk_level)

            alerts = query.order_by(desc(AlertHistory.created_at)).all()

            # Calculate summary statistics
            total_alerts = len(alerts)
            risk_distribution = {0: 0, 1: 0, 2: 0}
            status_distribution = {"delivered": 0, "pending": 0, "failed": 0}

            alerts_data = []
            for alert in alerts:
                if alert.risk_level in risk_distribution:
                    risk_distribution[alert.risk_level] += 1
                if alert.delivery_status in status_distribution:
                    status_distribution[alert.delivery_status] += 1

                alerts_data.append(
                    {
                        "id": alert.id,
                        "risk_level": alert.risk_level,
                        "risk_label": alert.risk_label,
                        "location": alert.location,
                        "message": alert.message,
                        "delivery_status": alert.delivery_status,
                        "delivery_channel": alert.delivery_channel,
                        "recipients": alert.recipients,
                        "acknowledged": alert.acknowledged,
                        "created_at": alert.created_at.isoformat() if alert.created_at else None,
                        # Smart alert fields
                        "confidence_score": alert.confidence_score,
                        "rainfall_3h": alert.rainfall_3h,
                        "escalation_state": alert.escalation_state,
                    }
                )

        return (
            jsonify(
                {
                    "success": True,
                    "summary": {
                        "total_alerts": total_alerts,
                        "days": days,
                        "risk_distribution": {
                            "safe": risk_distribution[0],
                            "alert": risk_distribution[1],
                            "critical": risk_distribution[2],
                        },
                        "status_distribution": status_distribution,
                    },
                    "alerts": alerts_data,
                    "request_id": request_id,
                }
            ),
            HTTP_OK,
        )

    except Exception as e:
        logger.error(f"Error fetching alert history [{request_id}]: {str(e)}", exc_info=True)
        return api_error("FetchFailed", "Failed to fetch alert history", HTTP_INTERNAL_ERROR, request_id)


@alerts_bp.route("/recent", methods=["GET"])
@limiter.limit("60 per minute")
def get_recent_alerts():
    """
    Get the most recent alerts (last 24 hours or limit).

    Query Parameters:
        limit (int): Maximum number of alerts (default: 10, max: 100)

    Returns:
        200: List of recent alerts
    ---
    tags:
      - Alerts
    parameters:
      - in: query
        name: limit
        type: integer
        default: 10
    responses:
      200:
        description: Recent alerts
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        limit = min(request.args.get("limit", 10, type=int), 100)

        # Use alert system's method for recent alerts
        alert_system = get_alert_system()
        alerts = alert_system.get_alert_history(limit=limit)

        return jsonify({"success": True, "data": alerts, "count": len(alerts), "request_id": request_id}), HTTP_OK

    except Exception as e:
        logger.error(f"Error fetching recent alerts [{request_id}]: {str(e)}", exc_info=True)
        return api_error("FetchFailed", "Failed to fetch recent alerts", HTTP_INTERNAL_ERROR, request_id)


@alerts_bp.route("/simulate-sms", methods=["POST"])
@limiter.limit("10 per minute")
@require_auth
def simulate_sms():
    """
    Simulate an SMS alert (always runs in sandbox mode).

    Request Body (JSON):
        phone (str): Philippine mobile number (required)
        message (str): Custom message (optional)
        risk_level (int): Risk level 0-2 (optional, default: 1)

    Returns:
        200: Simulation result
        400: Invalid input
    ---
    tags:
      - Alerts
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        body = request.get_json(silent=True) or {}
        phone = body.get("phone", "").strip()
        risk_level = body.get("risk_level", 1)
        custom_message = body.get("message", "").strip()

        if not phone:
            return api_error(
                "ValidationError",
                "Phone number is required",
                HTTP_BAD_REQUEST,
                request_id,
            )

        if risk_level not in (0, 1, 2):
            return api_error(
                "ValidationError",
                "risk_level must be 0, 1, or 2",
                HTTP_BAD_REQUEST,
                request_id,
            )

        risk_labels = {0: "Safe", 1: "Alert", 2: "Critical"}
        message = custom_message or (
            f"[SIMULATION] Floodingnaque Flood {risk_labels[risk_level]} – "
            f"Risk level {risk_level} detected in Parañaque City. "
            "This is a simulated alert for demo purposes only."
        )

        # Normalize PH number via alert system helper
        alert_system = get_alert_system()
        normalized = alert_system._normalize_ph_number(phone)

        logger.info(f"SMS simulation requested [{request_id}]: " f"phone={normalized}, risk_level={risk_level}")

        return (
            jsonify(
                {
                    "success": True,
                    "data": {
                        "status": "sandbox",
                        "phone": normalized,
                        "message": message,
                        "risk_level": risk_level,
                        "risk_label": risk_labels[risk_level],
                        "simulated_at": datetime.now(timezone.utc).isoformat(),
                    },
                    "request_id": request_id,
                }
            ),
            HTTP_OK,
        )

    except Exception as e:
        logger.error(f"Error simulating SMS [{request_id}]: {str(e)}", exc_info=True)
        return api_error(
            "SimulationFailed",
            "Failed to simulate SMS alert",
            HTTP_INTERNAL_ERROR,
            request_id,
        )


@alerts_bp.route("/stats", methods=["GET"])
@limiter.limit("30 per minute")
def get_alert_stats():
    """
    Get alert statistics for dashboard.

    Returns:
        200: Alert statistics including counts by risk level and status
    ---
    tags:
      - Alerts
    responses:
      200:
        description: Alert statistics
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)

        with get_db_session() as session:
            # Total alerts all time
            total_all_time = session.query(AlertHistory).filter(AlertHistory.is_deleted.is_(False)).count()

            # Alerts today
            alerts_today = (
                session.query(AlertHistory)
                .filter(AlertHistory.is_deleted.is_(False), AlertHistory.created_at >= today)
                .count()
            )

            # Alerts this week
            alerts_week = (
                session.query(AlertHistory)
                .filter(AlertHistory.is_deleted.is_(False), AlertHistory.created_at >= week_ago)
                .count()
            )

            # Alerts this month
            alerts_month = (
                session.query(AlertHistory)
                .filter(AlertHistory.is_deleted.is_(False), AlertHistory.created_at >= month_ago)
                .count()
            )

            # Critical alerts (risk level 2) in last 24 hours
            critical_24h = (
                session.query(AlertHistory)
                .filter(
                    AlertHistory.is_deleted.is_(False),
                    AlertHistory.risk_level == 2,
                    AlertHistory.created_at >= datetime.now(timezone.utc) - timedelta(hours=24),
                )
                .count()
            )

            # Most recent alert
            latest_alert = (
                session.query(AlertHistory)
                .filter(AlertHistory.is_deleted.is_(False))
                .order_by(desc(AlertHistory.created_at))
                .first()
            )

            latest_alert_data = None
            if latest_alert:
                latest_alert_data = {
                    "id": latest_alert.id,
                    "risk_level": latest_alert.risk_level,
                    "risk_label": latest_alert.risk_label,
                    "location": latest_alert.location,
                    "created_at": latest_alert.created_at.isoformat() if latest_alert.created_at else None,
                }

        return (
            jsonify(
                {
                    "success": True,
                    "stats": {
                        "total_all_time": total_all_time,
                        "alerts_today": alerts_today,
                        "alerts_this_week": alerts_week,
                        "alerts_this_month": alerts_month,
                        "critical_last_24h": critical_24h,
                        "latest_alert": latest_alert_data,
                    },
                    "request_id": request_id,
                }
            ),
            HTTP_OK,
        )

    except Exception as e:
        logger.error(f"Error fetching alert stats [{request_id}]: {str(e)}", exc_info=True)
        return api_error("FetchFailed", "Failed to fetch alert statistics", HTTP_INTERNAL_ERROR, request_id)


# ── Admin helpers ───────────────────────────────────────────────────────


def _require_admin(f):
    """Decorator that requires admin role after authentication."""

    @wraps(f)
    @require_auth
    def decorated(*args, **kwargs):
        if getattr(g, "current_user_role", None) != "admin":
            return api_error("Forbidden", "Admin access required", 403)
        return f(*args, **kwargs)

    return decorated


# ── POST /admin/bulk-delete - Admin bulk soft-delete alerts ─────────────


@alerts_bp.route("/admin/bulk-delete", methods=["POST"])
@_require_admin
def admin_bulk_delete_alerts():
    """
    Admin bulk soft-delete alert history records.

    Request Body:
    {
        "older_than_days": 30,     // Delete alerts older than N days
        "risk_level": null,        // Optional: filter by risk level (0/1/2)
        "delivery_status": null,   // Optional: filter by status (delivered/failed/pending)
        "confirm": true            // Required
    }

    Maximum 5000 records per request.
    """
    MAX_BULK = 5000

    try:
        data = request.get_json(silent=True) or {}

        if not data.get("confirm"):
            return api_error("ConfirmRequired", "Bulk delete requires confirm=true", HTTP_BAD_REQUEST)

        older_than_days = data.get("older_than_days")
        risk_level = data.get("risk_level")
        delivery_status = data.get("delivery_status")

        if older_than_days is None and risk_level is None and delivery_status is None:
            return api_error("ValidationError", "At least one filter is required", HTTP_BAD_REQUEST)

        with get_db_session() as session:
            query = session.query(AlertHistory).filter(AlertHistory.is_deleted.is_(False))

            if older_than_days is not None:
                cutoff = datetime.now(timezone.utc) - timedelta(days=int(older_than_days))
                query = query.filter(AlertHistory.created_at < cutoff)

            if risk_level is not None:
                query = query.filter(AlertHistory.risk_level == int(risk_level))

            if delivery_status:
                query = query.filter(AlertHistory.delivery_status == delivery_status)

            total_count = query.count()

            if total_count == 0:
                return jsonify({"success": True, "deleted_count": 0, "message": "No matching records found"}), HTTP_OK

            if total_count > MAX_BULK:
                return api_error(
                    "TooManyRecords",
                    f"Query matches {total_count} records, exceeds max of {MAX_BULK}. Add stricter filters.",
                    HTTP_BAD_REQUEST,
                )

            now = datetime.now(timezone.utc)
            deleted = query.update({"is_deleted": True, "deleted_at": now}, synchronize_session="fetch")

        logger.info("Admin bulk-deleted %d alert history records", deleted)
        return (
            jsonify(
                {
                    "success": True,
                    "deleted_count": deleted,
                    "message": f"Successfully deleted {deleted} alert(s)",
                }
            ),
            HTTP_OK,
        )

    except Exception as e:
        logger.error(f"Admin bulk delete alerts failed: {e}", exc_info=True)
        return api_error("DeleteFailed", "Failed to bulk delete alerts", HTTP_INTERNAL_ERROR)


# ---------------------------------------------------------------------------
# Alert Coverage - per-barangay delivery statistics
# ---------------------------------------------------------------------------


@alerts_bp.route("/coverage", methods=["GET"])
@limiter.limit("30 per minute")
def get_alert_coverage():
    """
    Get per-barangay alert delivery coverage statistics.

    Shows how many alerts were delivered vs pending vs failed,
    grouped by delivery channel, for the specified time window.

    Query Parameters:
        hours (int): Lookback window in hours (default: 24, max: 720)

    Returns:
        200: Coverage statistics with per-barangay and per-channel breakdown
    ---
    tags:
      - Alerts
    parameters:
      - in: query
        name: hours
        type: integer
        default: 24
    responses:
      200:
        description: Alert coverage statistics
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        hours = min(max(request.args.get("hours", 24, type=int), 1), 720)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

        with get_db_session() as session:
            alerts = (
                session.query(AlertHistory)
                .filter(AlertHistory.is_deleted.is_(False), AlertHistory.created_at >= cutoff)
                .all()
            )

            # Aggregate per-barangay
            barangay_stats: dict = {}
            channel_stats: dict = {}
            total_delivered = 0
            total_failed = 0
            total_pending = 0
            delivery_times = []

            for alert in alerts:
                # Extract barangay from location field
                location = (alert.location or "Unknown").strip()
                if location not in barangay_stats:
                    barangay_stats[location] = {
                        "delivered": 0,
                        "pending": 0,
                        "failed": 0,
                        "partial": 0,
                        "total": 0,
                        "risk_levels": {0: 0, 1: 0, 2: 0},
                    }

                bs = barangay_stats[location]
                bs["total"] += 1
                status = alert.delivery_status or "pending"
                if status in bs:
                    bs[status] += 1
                rl = alert.risk_level
                if rl in bs["risk_levels"]:
                    bs["risk_levels"][rl] += 1

                # Channel breakdown
                channel = alert.delivery_channel or "web"
                if channel not in channel_stats:
                    channel_stats[channel] = {"delivered": 0, "failed": 0, "pending": 0, "total": 0}
                channel_stats[channel]["total"] += 1
                if status == "delivered":
                    channel_stats[channel]["delivered"] += 1
                    total_delivered += 1
                elif status == "failed":
                    channel_stats[channel]["failed"] += 1
                    total_failed += 1
                else:
                    channel_stats[channel]["pending"] += 1
                    total_pending += 1

                # Time-to-delivery
                if alert.delivered_at and alert.created_at:
                    delta = (alert.delivered_at - alert.created_at).total_seconds()
                    if delta >= 0:
                        delivery_times.append(delta)

            total_alerts = total_delivered + total_failed + total_pending
            delivery_rate = round(total_delivered / total_alerts * 100, 1) if total_alerts > 0 else 0.0

            # Median time-to-delivery
            median_delivery_sec = None
            if delivery_times:
                delivery_times.sort()
                mid = len(delivery_times) // 2
                median_delivery_sec = round(delivery_times[mid], 1)

            # Per-barangay delivery percentage
            for loc, bs in barangay_stats.items():
                bs["delivery_pct"] = round(bs["delivered"] / bs["total"] * 100, 1) if bs["total"] > 0 else 0.0

        return (
            jsonify(
                {
                    "success": True,
                    "coverage": {
                        "hours": hours,
                        "total_alerts": total_alerts,
                        "total_delivered": total_delivered,
                        "total_failed": total_failed,
                        "total_pending": total_pending,
                        "delivery_rate_pct": delivery_rate,
                        "median_delivery_seconds": median_delivery_sec,
                    },
                    "barangays": barangay_stats,
                    "channels": channel_stats,
                    "request_id": request_id,
                }
            ),
            HTTP_OK,
        )

    except Exception as e:
        logger.error(f"Error fetching alert coverage [{request_id}]: {e}", exc_info=True)
        return api_error("FetchFailed", "Failed to fetch alert coverage", HTTP_INTERNAL_ERROR, request_id)


# ---------------------------------------------------------------------------
# SMS Delivery Confirmation Webhook (Semaphore callback)
# ---------------------------------------------------------------------------


@alerts_bp.route("/sms/delivery-status", methods=["POST"])
@limiter.limit("300 per minute")
def sms_delivery_webhook():
    """
    Receive SMS delivery status callbacks from Semaphore.

    Semaphore sends POST requests when SMS delivery status changes.
    Updates the corresponding AlertHistory record's delivery_status.

    Request Body (form-encoded or JSON):
        message_id (str): Semaphore message ID
        status (str): pending / sent / failed
        recipient (str): Phone number

    Returns:
        200: Acknowledged
    ---
    tags:
      - Alerts
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        # Semaphore sends form-encoded or JSON
        if request.content_type and "json" in request.content_type:
            data = request.get_json(silent=True) or {}
        else:
            data = request.form.to_dict()

        message_id = data.get("message_id", "")
        status = data.get("status", "").lower()
        recipient = data.get("recipient", "")

        if not message_id or not status:
            return jsonify({"success": False, "error": "message_id and status required"}), HTTP_BAD_REQUEST

        # Map Semaphore statuses to our status model
        status_map = {
            "sent": "delivered",
            "delivered": "delivered",
            "failed": "failed",
            "pending": "pending",
            "queued": "pending",
        }
        mapped_status = status_map.get(status, "pending")

        logger.info(
            "SMS delivery webhook [%s]: message_id=%s status=%s recipient=%s",
            request_id,
            message_id,
            mapped_status,
            recipient,
        )

        # Update the most recent SMS alert for this recipient (best-effort match)
        if recipient:
            try:
                with get_db_session() as session:
                    recent_sms = (
                        session.query(AlertHistory)
                        .filter(
                            AlertHistory.is_deleted.is_(False),
                            AlertHistory.delivery_channel == "sms",
                            AlertHistory.created_at >= datetime.now(timezone.utc) - timedelta(hours=24),
                        )
                        .order_by(desc(AlertHistory.created_at))
                        .first()
                    )
                    if recent_sms:
                        recent_sms.delivery_status = mapped_status
                        if mapped_status == "delivered":
                            recent_sms.delivered_at = datetime.now(timezone.utc)
                        logger.info("Updated alert %d delivery_status → %s", recent_sms.id, mapped_status)
            except Exception as db_err:
                logger.warning("SMS webhook DB update failed: %s", db_err)

        return jsonify({"success": True, "acknowledged": True}), HTTP_OK

    except Exception as e:
        logger.error("SMS delivery webhook error [%s]: %s", request_id, e, exc_info=True)
        return jsonify({"success": False, "error": "Internal error"}), HTTP_INTERNAL_ERROR
