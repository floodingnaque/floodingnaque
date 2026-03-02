"""
Dashboard API - Dashboard Routes

Primary dashboard endpoints aggregating data from all microservices
to power the frontend overview.
"""

import logging
from datetime import datetime, timedelta, timezone

from flask import Blueprint, current_app, jsonify, request

dashboard_bp = Blueprint("dashboard", __name__)
logger = logging.getLogger(__name__)


@dashboard_bp.route("/summary", methods=["GET"])
def get_dashboard_summary():
    """
    GET /api/v1/dashboard/summary

    Returns a consolidated summary for the main dashboard view:
    - Latest weather conditions
    - Current flood risk level
    - Active alert count
    - Recent prediction results
    - System health overview
    """
    from app.services.dashboard_service import DashboardService

    try:
        service = DashboardService(current_app)
        summary = service.get_summary()
        return jsonify({"status": "success", "data": summary}), 200
    except Exception as e:
        logger.error("Failed to build dashboard summary: %s", e)
        return jsonify({
            "status": "error",
            "message": "Unable to build dashboard summary",
            "detail": str(e),
        }), 502


@dashboard_bp.route("/statistics", methods=["GET"])
def get_dashboard_statistics():
    """
    GET /api/v1/dashboard/statistics?period=7d

    Returns aggregated statistics over a configurable time window.
    Supported periods: 1d, 7d, 30d, 90d
    """
    from app.services.dashboard_service import DashboardService

    period = request.args.get("period", "7d")
    allowed_periods = {"1d": 1, "7d": 7, "30d": 30, "90d": 90}

    if period not in allowed_periods:
        return jsonify({
            "status": "error",
            "message": f"Invalid period. Allowed: {list(allowed_periods.keys())}",
        }), 400

    days = allowed_periods[period]
    since = datetime.now(timezone.utc) - timedelta(days=days)

    try:
        service = DashboardService(current_app)
        stats = service.get_statistics(since=since, period=period)
        return jsonify({"status": "success", "data": stats, "period": period}), 200
    except Exception as e:
        logger.error("Statistics aggregation failed: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 502


@dashboard_bp.route("/activity", methods=["GET"])
def get_activity_feed():
    """
    GET /api/v1/dashboard/activity?limit=50&offset=0

    Returns a unified activity feed combining events from all services:
    - Weather data ingestion events
    - Prediction completions
    - Alert triggers / acknowledgements
    - User sign-ups
    """
    from app.services.dashboard_service import DashboardService

    limit = min(int(request.args.get("limit", 50)), 200)
    offset = int(request.args.get("offset", 0))

    try:
        service = DashboardService(current_app)
        feed = service.get_activity_feed(limit=limit, offset=offset)
        return jsonify({
            "status": "success",
            "data": feed,
            "pagination": {"limit": limit, "offset": offset},
        }), 200
    except Exception as e:
        logger.error("Activity feed error: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 502


@dashboard_bp.route("/widgets", methods=["GET"])
def get_widget_data():
    """
    GET /api/v1/dashboard/widgets?ids=weather_current,risk_gauge,alert_count

    Returns data for specific dashboard widgets by ID.
    """
    from app.services.dashboard_service import DashboardService

    widget_ids = request.args.get("ids", "").split(",")
    widget_ids = [w.strip() for w in widget_ids if w.strip()]

    if not widget_ids:
        return jsonify({
            "status": "error",
            "message": "Provide widget IDs via ?ids=widget1,widget2",
        }), 400

    try:
        service = DashboardService(current_app)
        widgets = service.get_widget_data(widget_ids)
        return jsonify({"status": "success", "data": widgets}), 200
    except Exception as e:
        logger.error("Widget data error: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 502


@dashboard_bp.route("/overview", methods=["GET"])
def get_system_overview():
    """
    GET /api/v1/dashboard/overview

    High-level system overview: service health, uptime, version info.
    """
    from app.services.dashboard_service import DashboardService

    try:
        service = DashboardService(current_app)
        overview = service.get_system_overview()
        return jsonify({"status": "success", "data": overview}), 200
    except Exception as e:
        logger.error("System overview error: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 502
