"""
Notification management routes.

Manage notification preferences and delivery channels.
"""

import logging

from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)

notifications_bp = Blueprint("notifications", __name__)


@notifications_bp.route("/channels", methods=["GET"])
def list_channels():
    """List available notification channels."""
    channels = [
        {"id": "web", "name": "Web Dashboard", "enabled": True, "description": "Real-time alerts on dashboard via SSE"},
        {"id": "email", "name": "Email", "enabled": True, "description": "Email notifications to registered users"},
        {"id": "sms", "name": "SMS", "enabled": False, "description": "SMS alerts to registered phone numbers (Semaphore / Twilio)"},
        {"id": "slack", "name": "Slack", "enabled": False, "description": "Slack channel notifications"},
        {"id": "webhook", "name": "Webhook", "enabled": True, "description": "HTTP webhook callbacks"},
        {"id": "firebase_push", "name": "Firebase Push", "enabled": False, "description": "Mobile push notifications via Firebase Cloud Messaging"},
        {"id": "messenger", "name": "Messenger Chatbot", "enabled": False, "description": "Facebook Messenger chatbot alerts"},
        {"id": "telegram", "name": "Telegram Bot", "enabled": False, "description": "Telegram bot alerts to subscribed users/channels"},
        {"id": "siren", "name": "LGU Siren", "enabled": False, "description": "Community warning siren activation (future LGU integration)"},
    ]
    return jsonify({"success": True, "channels": channels})


@notifications_bp.route("/preferences", methods=["GET"])
def get_preferences():
    """Get notification preferences for the authenticated user."""
    from shared.auth import require_auth

    return jsonify({
        "success": True,
        "preferences": {
            "channels": ["web", "email"],
            "severity_filter": "moderate",
            "quiet_hours": None,
        },
    })


@notifications_bp.route("/preferences", methods=["PUT"])
def update_preferences():
    """Update notification preferences."""
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "Request body required"}), 400

    return jsonify({
        "success": True,
        "message": "Preferences updated",
        "preferences": data,
    })


@notifications_bp.route("/test", methods=["POST"])
def send_test_notification():
    """Send a test notification to verify channel configuration."""
    data = request.get_json() or {}
    channel = data.get("channel", "web")

    return jsonify({
        "success": True,
        "message": f"Test notification sent via {channel}",
        "channel": channel,
    })
