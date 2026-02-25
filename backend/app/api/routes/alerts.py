"""
Alert Routes.

Provides API endpoints for retrieving alerts and alert history.
"""

import logging
from datetime import datetime, timedelta, timezone

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
from sqlalchemy import desc

logger = logging.getLogger(__name__)

alerts_bp = Blueprint("alerts", __name__)


@alerts_bp.route("", methods=["GET"])
@limiter.limit("60 per minute")
def get_alerts():
    """
    Get list of alerts with pagination and filtering.

    Query Parameters:
        limit (int): Maximum number of alerts to return (default: 50, max: 500)
        offset (int): Number of records to skip (default: 0)
        risk_level (int): Filter by risk level (0=Safe, 1=Alert, 2=Critical)
        status (str): Filter by delivery status (delivered/pending/failed)
        start_date (str): Filter alerts after this date (ISO format)
        end_date (str): Filter alerts before this date (ISO format)

    Returns:
        200: List of alerts with pagination info
    ---
    tags:
      - Alerts
    parameters:
      - in: query
        name: limit
        type: integer
        default: 50
      - in: query
        name: offset
        type: integer
        default: 0
      - in: query
        name: risk_level
        type: integer
        enum: [0, 1, 2]
      - in: query
        name: status
        type: string
        enum: [delivered, pending, failed]
    responses:
      200:
        description: List of alerts
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        # Parse query parameters
        limit = min(request.args.get("limit", 50, type=int), 500)
        offset = request.args.get("offset", 0, type=int)
        risk_level = request.args.get("risk_level", type=int)
        status = request.args.get("status", type=str)
        start_date = request.args.get("start_date", type=str)
        end_date = request.args.get("end_date", type=str)

        if limit < 1:
            return api_error("ValidationError", "Limit must be at least 1", HTTP_BAD_REQUEST, request_id)

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

            # Get total count
            total = query.count()

            # Order by created_at descending and apply pagination
            query = query.order_by(desc(AlertHistory.created_at))
            query = query.offset(offset).limit(limit)

            alerts = query.all()

            # Format response
            alerts_data = []
            for alert in alerts:
                alerts_data.append(
                    {
                        "id": alert.id,
                        "risk_level": alert.risk_level,
                        "risk_label": alert.risk_label,
                        "location": alert.location,
                        "message": alert.message,
                        "delivery_status": alert.delivery_status,
                        "delivery_channel": alert.delivery_channel,
                        "delivered_at": alert.delivered_at.isoformat() if alert.delivered_at else None,
                        "created_at": alert.created_at.isoformat() if alert.created_at else None,
                    }
                )

        return (
            jsonify(
                {
                    "success": True,
                    "data": alerts_data,
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                    "count": len(alerts_data),
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
            }

        return jsonify({"success": True, "data": alert_data, "request_id": request_id}), HTTP_OK

    except Exception as e:
        logger.error(f"Error fetching alert {alert_id} [{request_id}]: {str(e)}", exc_info=True)
        return api_error("FetchFailed", "Failed to fetch alert", HTTP_INTERNAL_ERROR, request_id)


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
                        "delivery_status": alert.delivery_status,
                        "created_at": alert.created_at.isoformat() if alert.created_at else None,
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
