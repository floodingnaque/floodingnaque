"""
Alert management routes.

Endpoints:
  GET  /api/v1/alerts/          — List active alerts
  POST /api/v1/alerts/          — Create a new alert
  GET  /api/v1/alerts/<id>      — Get alert details
  PUT  /api/v1/alerts/<id>      — Update alert status
  GET  /api/v1/alerts/history   — Get alert history
  GET  /api/v1/alerts/recent    — Get recent alerts
  GET  /api/v1/alerts/stats     — Get alert statistics
  POST /api/v1/alerts/resolve   — Resolve/dismiss an alert
"""

import logging
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)

alerts_bp = Blueprint("alerts", __name__)


@alerts_bp.route("/", methods=["GET"])
def list_alerts():
    """List active alerts with optional filtering."""
    severity = request.args.get("severity")
    status = request.args.get("status", "active")
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    try:
        from app.services.alert_manager import AlertManager
        manager = AlertManager.get_instance()
        result = manager.list_alerts(
            severity=severity, status=status, page=page, per_page=per_page
        )
        return jsonify({"success": True, **result})
    except Exception as e:
        logger.error("List alerts failed: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


@alerts_bp.route("/", methods=["POST"])
def create_alert():
    """
    Create a new flood alert.

    Body:
      {
        "severity": "high",
        "title": "Flash Flood Warning — Barangay San Isidro",
        "message": "Heavy rainfall detected...",
        "affected_areas": ["San Isidro", "BF Homes"],
        "flood_probability": 0.82,
        "channels": ["web", "sms", "email"]
      }
    """
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "Request body required"}), 400

    required = ["severity", "title", "message"]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"success": False, "error": f"Missing fields: {missing}"}), 422

    try:
        from app.services.alert_manager import AlertManager
        manager = AlertManager.get_instance()
        alert = manager.create_alert(data)

        # Publish alert event
        from shared.messaging import EventBus
        bus = EventBus()
        bus.publish("alert.triggered", alert)

        return jsonify({"success": True, "alert": alert}), 201
    except Exception as e:
        logger.error("Create alert failed: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


@alerts_bp.route("/<alert_id>", methods=["GET"])
def get_alert(alert_id):
    """Get alert details by ID."""
    try:
        from app.services.alert_manager import AlertManager
        manager = AlertManager.get_instance()
        alert = manager.get_alert(alert_id)
        if not alert:
            return jsonify({"success": False, "error": "Alert not found"}), 404
        return jsonify({"success": True, "alert": alert})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@alerts_bp.route("/<alert_id>", methods=["PUT"])
def update_alert(alert_id):
    """Update alert status (acknowledge, resolve, escalate)."""
    data = request.get_json()
    try:
        from app.services.alert_manager import AlertManager
        manager = AlertManager.get_instance()
        alert = manager.update_alert(alert_id, data)
        return jsonify({"success": True, "alert": alert})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@alerts_bp.route("/history", methods=["GET"])
def alert_history():
    """Get historical alerts with date range filtering."""
    days = request.args.get("days", 30, type=int)
    try:
        from app.services.alert_manager import AlertManager
        manager = AlertManager.get_instance()
        history = manager.get_history(days=days)
        return jsonify({"success": True, "history": history, "period_days": days})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@alerts_bp.route("/recent", methods=["GET"])
def recent_alerts():
    """Get the most recent alerts."""
    limit = request.args.get("limit", 10, type=int)
    try:
        from app.services.alert_manager import AlertManager
        manager = AlertManager.get_instance()
        alerts = manager.get_recent(limit=limit)
        return jsonify({"success": True, "alerts": alerts, "count": len(alerts)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@alerts_bp.route("/stats", methods=["GET"])
def alert_stats():
    """Get alert statistics."""
    try:
        from app.services.alert_manager import AlertManager
        manager = AlertManager.get_instance()
        stats = manager.get_stats()
        return jsonify({"success": True, "stats": stats})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@alerts_bp.route("/resolve", methods=["POST"])
def resolve_alert():
    """Resolve/dismiss an alert."""
    data = request.get_json()
    alert_id = data.get("alert_id") if data else None
    if not alert_id:
        return jsonify({"success": False, "error": "alert_id required"}), 400

    try:
        from app.services.alert_manager import AlertManager
        manager = AlertManager.get_instance()
        result = manager.resolve_alert(alert_id, data.get("reason", ""))
        return jsonify({"success": True, "result": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
