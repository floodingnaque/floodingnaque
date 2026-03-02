"""
Dashboard API — Export Routes

Data export endpoints for CSV, JSON, and Excel downloads.
"""

import csv
import io
import json
import logging
from datetime import datetime, timezone

from flask import Blueprint, Response, current_app, jsonify, request

export_bp = Blueprint("export", __name__)
logger = logging.getLogger(__name__)


@export_bp.route("/predictions", methods=["GET"])
def export_predictions():
    """
    GET /api/v1/dashboard/export/predictions?format=csv&start_date=2024-01-01

    Export prediction history as CSV or JSON.
    """
    from app.services.dashboard_service import DashboardService

    fmt = request.args.get("format", "csv").lower()
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    risk_level = request.args.get("risk_level")

    if fmt not in ("csv", "json"):
        return jsonify({"status": "error", "message": "Format must be csv or json"}), 400

    try:
        service = DashboardService(current_app)
        data = service.export_predictions(
            start_date=start_date, end_date=end_date, risk_level=risk_level
        )

        if fmt == "csv":
            return _to_csv_response(data, "predictions_export")
        return _to_json_response(data, "predictions_export")

    except Exception as e:
        logger.error("Prediction export error: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 502


@export_bp.route("/weather", methods=["GET"])
def export_weather():
    """
    GET /api/v1/dashboard/export/weather?format=csv&days=30

    Export weather observation history.
    """
    from app.services.dashboard_service import DashboardService

    fmt = request.args.get("format", "csv").lower()
    days = int(request.args.get("days", 30))

    if fmt not in ("csv", "json"):
        return jsonify({"status": "error", "message": "Format must be csv or json"}), 400

    try:
        service = DashboardService(current_app)
        data = service.export_weather(days=days)

        if fmt == "csv":
            return _to_csv_response(data, "weather_export")
        return _to_json_response(data, "weather_export")

    except Exception as e:
        logger.error("Weather export error: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 502


@export_bp.route("/alerts", methods=["GET"])
def export_alerts():
    """
    GET /api/v1/dashboard/export/alerts?format=json&severity=critical

    Export alert history.
    """
    from app.services.dashboard_service import DashboardService

    fmt = request.args.get("format", "csv").lower()
    severity = request.args.get("severity")
    days = int(request.args.get("days", 90))

    if fmt not in ("csv", "json"):
        return jsonify({"status": "error", "message": "Format must be csv or json"}), 400

    try:
        service = DashboardService(current_app)
        data = service.export_alerts(days=days, severity=severity)

        if fmt == "csv":
            return _to_csv_response(data, "alerts_export")
        return _to_json_response(data, "alerts_export")

    except Exception as e:
        logger.error("Alert export error: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 502


@export_bp.route("/report", methods=["GET"])
def export_full_report():
    """
    GET /api/v1/dashboard/export/report?period=30d

    Generate a comprehensive JSON report combining weather,
    predictions, and alerts for the specified period.
    """
    from app.services.dashboard_service import DashboardService

    period = request.args.get("period", "30d")

    try:
        service = DashboardService(current_app)
        report = service.generate_full_report(period=period)
        return _to_json_response(report, "flood_risk_report")

    except Exception as e:
        logger.error("Report generation error: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 502


# ── helpers ─────────────────────────────────────────────────────────

def _to_csv_response(data: list[dict], filename_prefix: str) -> Response:
    """Convert a list of dicts to a CSV download response."""
    if not data:
        return Response("", mimetype="text/csv", status=204)

    si = io.StringIO()
    writer = csv.DictWriter(si, fieldnames=data[0].keys())
    writer.writeheader()
    writer.writerows(data)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"{filename_prefix}_{timestamp}.csv"

    return Response(
        si.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


def _to_json_response(data, filename_prefix: str) -> Response:
    """Create a JSON download response."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"{filename_prefix}_{timestamp}.json"

    return Response(
        json.dumps(data, indent=2, default=str),
        mimetype="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
