"""
Webhook dispatch routes.

Enables third-party integrations to receive alert notifications
via registered webhook URLs.
"""

import logging
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)

webhooks_bp = Blueprint("webhooks", __name__)


@webhooks_bp.route("/register", methods=["POST"])
def register_webhook():
    """
    Register a webhook URL to receive alert notifications.

    Body:
      {
        "url": "https://example.com/webhook",
        "events": ["alert.triggered", "alert.resolved"],
        "secret": "webhook-signing-secret"
      }
    """
    data = request.get_json()
    if not data or "url" not in data:
        return jsonify({"success": False, "error": "url is required"}), 400

    try:
        from app.services.alert_manager import AlertManager
        manager = AlertManager.get_instance()
        result = manager.register_webhook(data)
        return jsonify({"success": True, "webhook": result}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@webhooks_bp.route("/list", methods=["GET"])
def list_webhooks():
    """List registered webhooks."""
    try:
        from app.services.alert_manager import AlertManager
        manager = AlertManager.get_instance()
        webhooks = manager.list_webhooks()
        return jsonify({"success": True, "webhooks": webhooks})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@webhooks_bp.route("/<webhook_id>", methods=["DELETE"])
def delete_webhook(webhook_id):
    """Delete a registered webhook."""
    try:
        from app.services.alert_manager import AlertManager
        manager = AlertManager.get_instance()
        manager.delete_webhook(webhook_id)
        return jsonify({"success": True, "message": "Webhook deleted"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
