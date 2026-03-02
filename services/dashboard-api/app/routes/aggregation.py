"""
Dashboard API - Data Aggregation Routes

Cross-service data aggregation and correlation endpoints.
"""

import logging
from flask import Blueprint, current_app, jsonify, request

aggregation_bp = Blueprint("aggregation", __name__)
logger = logging.getLogger(__name__)


@aggregation_bp.route("/weather-risk", methods=["GET"])
def weather_risk_correlation():
    """
    GET /api/v1/dashboard/aggregation/weather-risk?days=7

    Correlate weather observations with predicted flood risk over time.
    Returns time-series data for visualisation.
    """
    from app.services.dashboard_service import DashboardService

    days = int(request.args.get("days", 7))

    try:
        service = DashboardService(current_app)
        data = service.aggregate_weather_risk(days=days)
        return jsonify({"status": "success", "data": data}), 200
    except Exception as e:
        logger.error("Weather-risk aggregation error: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 502


@aggregation_bp.route("/alert-timeline", methods=["GET"])
def alert_timeline():
    """
    GET /api/v1/dashboard/aggregation/alert-timeline?days=30

    Timeline of alert triggers correlated with weather events.
    """
    from app.services.dashboard_service import DashboardService

    days = int(request.args.get("days", 30))

    try:
        service = DashboardService(current_app)
        timeline = service.aggregate_alert_timeline(days=days)
        return jsonify({"status": "success", "data": timeline}), 200
    except Exception as e:
        logger.error("Alert timeline error: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 502


@aggregation_bp.route("/flood-events", methods=["GET"])
def flood_events_summary():
    """
    GET /api/v1/dashboard/aggregation/flood-events?year=2024

    Summary of flood events with aggregated weather, prediction,
    and alert data for each event.
    """
    from app.services.dashboard_service import DashboardService

    year = request.args.get("year")

    try:
        service = DashboardService(current_app)
        events = service.aggregate_flood_events(year=year)
        return jsonify({"status": "success", "data": events}), 200
    except Exception as e:
        logger.error("Flood events aggregation error: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 502


@aggregation_bp.route("/trend", methods=["GET"])
def trend_analysis():
    """
    GET /api/v1/dashboard/aggregation/trend?metric=rainfall&period=90d

    Trend analysis for a given metric over a specified period.
    Metrics: rainfall, temperature, humidity, water_level, risk_score.
    """
    from app.services.dashboard_service import DashboardService

    metric = request.args.get("metric", "rainfall")
    period = request.args.get("period", "90d")
    valid_metrics = {"rainfall", "temperature", "humidity", "water_level", "risk_score"}

    if metric not in valid_metrics:
        return jsonify({
            "status": "error",
            "message": f"Invalid metric. Allowed: {sorted(valid_metrics)}",
        }), 400

    try:
        service = DashboardService(current_app)
        trend = service.get_trend_analysis(metric=metric, period=period)
        return jsonify({"status": "success", "data": trend}), 200
    except Exception as e:
        logger.error("Trend analysis error: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 502
