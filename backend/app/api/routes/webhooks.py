"""
Webhook Management API.

Endpoints for registering and managing webhooks for flood alerts.
Includes webhook delivery with exponential backoff retry logic.
"""

import hashlib
import hmac
import json
import logging
import os
import secrets
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.api.middleware.auth import require_api_key
from app.api.middleware.rate_limit import limiter
from app.models.db import Webhook, get_db_session
from app.utils.api_constants import HTTP_BAD_REQUEST, HTTP_INTERNAL_ERROR, HTTP_NOT_FOUND, HTTP_OK
from app.utils.api_responses import api_error
from flask import Blueprint, g, jsonify, request

logger = logging.getLogger(__name__)

webhooks_bp = Blueprint("webhooks", __name__)

# Webhook delivery configuration
WEBHOOK_MAX_RETRIES = int(os.getenv("WEBHOOK_MAX_RETRIES", "5"))
WEBHOOK_INITIAL_DELAY_SEC = float(os.getenv("WEBHOOK_INITIAL_DELAY_SEC", "1"))
WEBHOOK_MAX_DELAY_SEC = float(os.getenv("WEBHOOK_MAX_DELAY_SEC", "300"))  # 5 minutes
WEBHOOK_BACKOFF_MULTIPLIER = float(os.getenv("WEBHOOK_BACKOFF_MULTIPLIER", "2"))
WEBHOOK_TIMEOUT_SEC = int(os.getenv("WEBHOOK_TIMEOUT_SEC", "30"))
WEBHOOK_JITTER_FACTOR = float(os.getenv("WEBHOOK_JITTER_FACTOR", "0.1"))  # 10% jitter
WEBHOOK_MAX_FAILURE_COUNT = int(os.getenv("WEBHOOK_MAX_FAILURE_COUNT", "10"))  # Auto-disable after this many failures


@dataclass
class WebhookDeliveryResult:
    """Result of a webhook delivery attempt."""

    success: bool
    status_code: Optional[int] = None
    response_time_ms: float = 0
    error_message: Optional[str] = None
    attempt: int = 1
    next_retry_delay: Optional[float] = None


@dataclass
class WebhookPayload:
    """Webhook payload to be delivered."""

    event_type: str
    data: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    webhook_id: Optional[int] = None
    attempt: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "data": self.data,
            "timestamp": self.timestamp,
            "delivery_attempt": self.attempt,
        }


def calculate_backoff_delay(
    attempt: int,
    initial_delay: float = WEBHOOK_INITIAL_DELAY_SEC,
    multiplier: float = WEBHOOK_BACKOFF_MULTIPLIER,
    max_delay: float = WEBHOOK_MAX_DELAY_SEC,
    jitter_factor: float = WEBHOOK_JITTER_FACTOR,
) -> float:
    """
    Calculate exponential backoff delay with jitter.

    Formula: min(max_delay, initial_delay * (multiplier ^ attempt)) * (1 + random_jitter)

    Args:
        attempt: Current retry attempt (0-indexed)
        initial_delay: Base delay in seconds
        multiplier: Backoff multiplier
        max_delay: Maximum delay cap
        jitter_factor: Random jitter factor (0-1)

    Returns:
        Delay in seconds
    """
    import random

    # Calculate base delay with exponential backoff
    delay = initial_delay * (multiplier**attempt)

    # Cap at max delay
    delay = min(delay, max_delay)

    # Add jitter to prevent thundering herd
    jitter = delay * jitter_factor * random.random()  # nosec B311
    delay += jitter

    return round(delay, 2)


def generate_webhook_signature(payload: str, secret: str) -> str:
    """
    Generate HMAC-SHA256 signature for webhook payload.

    Args:
        payload: JSON string of the payload
        secret: Webhook secret

    Returns:
        Signature string (sha256=...)
    """
    signature = hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"sha256={signature}"


def deliver_webhook(
    webhook_url: str, webhook_secret: str, payload: WebhookPayload, timeout: int = WEBHOOK_TIMEOUT_SEC
) -> WebhookDeliveryResult:
    """
    Attempt to deliver a webhook payload to a URL.

    Args:
        webhook_url: Target URL
        webhook_secret: Secret for signing
        payload: Webhook payload
        timeout: Request timeout in seconds

    Returns:
        WebhookDeliveryResult with delivery status
    """
    import requests

    try:
        # Prepare payload
        payload_json = json.dumps(payload.to_dict())

        # Generate signature
        signature = generate_webhook_signature(payload_json, webhook_secret)

        # Prepare headers
        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Signature": signature,
            "X-Webhook-Event": payload.event_type,
            "X-Webhook-Delivery-Attempt": str(payload.attempt),
            "X-Webhook-Timestamp": payload.timestamp,
            "User-Agent": "Floodingnaque-Webhook/1.0",
        }

        # Send request
        start_time = time.time()
        response = requests.post(webhook_url, data=payload_json, headers=headers, timeout=timeout)
        response_time_ms = (time.time() - start_time) * 1000

        # Check response
        success = 200 <= response.status_code < 300

        return WebhookDeliveryResult(
            success=success,
            status_code=response.status_code,
            response_time_ms=response_time_ms,
            error_message=None if success else f"HTTP {response.status_code}",
            attempt=payload.attempt,
        )

    except requests.exceptions.Timeout:
        return WebhookDeliveryResult(
            success=False, error_message=f"Request timed out after {timeout}s", attempt=payload.attempt
        )
    except requests.exceptions.ConnectionError as e:
        return WebhookDeliveryResult(
            success=False, error_message=f"Connection error: {str(e)[:100]}", attempt=payload.attempt
        )
    except Exception as e:
        return WebhookDeliveryResult(
            success=False, error_message=f"Delivery failed: {str(e)[:100]}", attempt=payload.attempt
        )


def deliver_webhook_with_retry(
    webhook_id: int,
    event_type: str,
    data: Dict[str, Any],
    max_retries: int = WEBHOOK_MAX_RETRIES,
    async_delivery: bool = True,
) -> Optional[WebhookDeliveryResult]:
    """
    Deliver a webhook with exponential backoff retry.

    Args:
        webhook_id: ID of the webhook
        event_type: Type of event
        data: Event data
        max_retries: Maximum number of retry attempts
        async_delivery: If True, deliver in background thread

    Returns:
        WebhookDeliveryResult or None if async
    """

    def _deliver():
        with get_db_session() as session:
            webhook = (
                session.query(Webhook)
                .filter(Webhook.id == webhook_id, Webhook.is_deleted == False, Webhook.is_active == True)
                .first()
            )

            if not webhook:
                logger.warning(f"Webhook {webhook_id} not found or inactive")
                return None

            # Check if webhook should receive this event
            events = json.loads(webhook.events)
            if event_type not in events:
                logger.debug(f"Webhook {webhook_id} not subscribed to event {event_type}")
                return None

            webhook_url = webhook.url
            webhook_secret = webhook.secret

            # Store initial failure count to detect if we need to update
            initial_failure_count = webhook.failure_count

        last_result = None

        for attempt in range(max_retries + 1):
            payload = WebhookPayload(event_type=event_type, data=data, webhook_id=webhook_id, attempt=attempt + 1)

            result = deliver_webhook(webhook_url, webhook_secret, payload)
            last_result = result

            if result.success:
                # Reset failure count on success
                with get_db_session() as session:
                    wh = session.query(Webhook).filter(Webhook.id == webhook_id).first()
                    if wh:
                        wh.failure_count = 0
                        wh.last_triggered_at = datetime.now(timezone.utc)

                logger.info(f"Webhook {webhook_id} delivered successfully on attempt {attempt + 1}")
                return result

            # Calculate next retry delay
            if attempt < max_retries:
                delay = calculate_backoff_delay(attempt)
                result.next_retry_delay = delay
                logger.warning(
                    f"Webhook {webhook_id} delivery failed (attempt {attempt + 1}/{max_retries + 1}): "
                    f"{result.error_message}. Retrying in {delay}s"
                )
                time.sleep(delay)
            else:
                logger.error(
                    f"Webhook {webhook_id} delivery failed after {max_retries + 1} attempts: " f"{result.error_message}"
                )

        # Update failure count after all retries exhausted
        with get_db_session() as session:
            wh = session.query(Webhook).filter(Webhook.id == webhook_id).first()
            if wh:
                wh.failure_count = (wh.failure_count or 0) + 1
                wh.last_triggered_at = datetime.now(timezone.utc)

                # Auto-disable webhook if too many failures
                if wh.failure_count >= WEBHOOK_MAX_FAILURE_COUNT:
                    wh.is_active = False
                    logger.warning(f"Webhook {webhook_id} auto-disabled after {wh.failure_count} consecutive failures")

        return last_result

    if async_delivery:
        thread = threading.Thread(target=_deliver, daemon=True)
        thread.start()
        return None
    else:
        return _deliver()


def broadcast_to_webhooks(event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Broadcast an event to all active webhooks subscribed to it.

    Args:
        event_type: Type of event
        data: Event data

    Returns:
        Summary of broadcast results
    """
    with get_db_session() as session:
        webhooks = session.query(Webhook).filter(Webhook.is_deleted == False, Webhook.is_active == True).all()

        matching_webhooks = []
        for webhook in webhooks:
            events = json.loads(webhook.events)
            if event_type in events:
                matching_webhooks.append(webhook.id)

    # Trigger async delivery for each webhook
    for webhook_id in matching_webhooks:
        deliver_webhook_with_retry(webhook_id, event_type, data, async_delivery=True)

    return {"event_type": event_type, "webhooks_notified": len(matching_webhooks), "webhook_ids": matching_webhooks}


@webhooks_bp.route("/register", methods=["POST"])
@require_api_key
@limiter.limit("10 per hour")
def register_webhook():
    """
    Register a new webhook for flood alerts.

    Creates a new webhook subscription to receive flood alert notifications.
    Webhooks are delivered with exponential backoff retry on failure.

    Request Body:
        url (str): Webhook endpoint URL (required, must start with http:// or https://)
        events (array): List of event types to subscribe to (required)
        secret (str): Custom webhook secret for signature verification (optional)

    Valid Event Types:
        - flood_detected: Any flood detection
        - critical_risk: Risk level 2 (critical)
        - high_risk: Risk level 1+ (alert or critical)
        - medium_risk: Risk level 1 (alert)
        - low_risk: Risk level 0 (safe)

    Returns:
        201: Webhook registered successfully
        400: Invalid request data
        500: Internal server error
    ---
    tags:
      - Webhooks
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - url
            - events
          properties:
            url:
              type: string
              description: Webhook endpoint URL
              example: "https://your-system.com/flood-alert"
            events:
              type: array
              items:
                type: string
                enum: [flood_detected, critical_risk, high_risk, medium_risk, low_risk]
              example: ["flood_detected", "critical_risk"]
            secret:
              type: string
              description: Custom secret for signature verification
    responses:
      201:
        description: Webhook registered successfully
        schema:
          type: object
          properties:
            message:
              type: string
            webhook_id:
              type: integer
            url:
              type: string
            events:
              type: array
              items:
                type: string
            secret:
              type: string
            is_active:
              type: boolean
      400:
        description: Invalid request data
      500:
        description: Internal server error
    security:
      - api_key: []
    """
    try:
        data = request.get_json()

        # Validate required fields
        if not data or "url" not in data or "events" not in data:
            return jsonify({"error": "Missing required fields: url, events"}), 400

        url = data["url"]
        events = data["events"]

        # Validate URL
        if not url.startswith("http://") and not url.startswith("https://"):
            return jsonify({"error": "Invalid URL format. Must start with http:// or https://"}), 400

        # Validate events
        valid_events = ["flood_detected", "critical_risk", "high_risk", "medium_risk", "low_risk"]
        if not isinstance(events, list) or not events:
            return jsonify({"error": "Events must be a non-empty list"}), 400

        for event in events:
            if event not in valid_events:
                return jsonify({"error": f"Invalid event: {event}. Valid events: {valid_events}"}), 400

        # Generate or use provided secret
        secret = data.get("secret") or secrets.token_urlsafe(32)

        # Create webhook
        webhook = Webhook(url=url, events=json.dumps(events), secret=secret, is_active=True)

        with get_db_session() as session:
            session.add(webhook)
            session.commit()
            webhook_id = webhook.id

        logger.info(f"Webhook registered: {url} for events {events}")

        return (
            jsonify(
                {
                    "message": "Webhook registered successfully",
                    "webhook_id": webhook_id,
                    "url": url,
                    "events": events,
                    "secret": secret,
                    "is_active": True,
                }
            ),
            201,
        )

    except Exception as e:
        logger.error(f"Error registering webhook: {e}")
        return jsonify({"error": "Internal server error"}), 500


@webhooks_bp.route("/list", methods=["GET"])
@require_api_key
@limiter.limit("30 per minute")
def list_webhooks():
    """
    List all registered webhooks.

    Returns all non-deleted webhooks with their configuration and status.

    Returns:
        200: List of webhooks
        500: Internal server error
    ---
    tags:
      - Webhooks
    produces:
      - application/json
    responses:
      200:
        description: List of webhooks
        schema:
          type: object
          properties:
            webhooks:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: integer
                  url:
                    type: string
                  events:
                    type: array
                    items:
                      type: string
                  is_active:
                    type: boolean
                  failure_count:
                    type: integer
                  last_triggered_at:
                    type: string
                    format: date-time
                  created_at:
                    type: string
                    format: date-time
            count:
              type: integer
      500:
        description: Internal server error
    security:
      - api_key: []
    """
    try:
        with get_db_session() as session:
            webhooks = session.query(Webhook).filter_by(is_deleted=False).all()

            webhook_list = []
            for webhook in webhooks:
                webhook_list.append(
                    {
                        "id": webhook.id,
                        "url": webhook.url,
                        "events": json.loads(webhook.events),
                        "is_active": webhook.is_active,
                        "failure_count": webhook.failure_count,
                        "last_triggered_at": (
                            webhook.last_triggered_at.isoformat() if webhook.last_triggered_at else None
                        ),
                        "created_at": webhook.created_at.isoformat(),
                    }
                )

        return jsonify({"webhooks": webhook_list, "count": len(webhook_list)}), 200

    except Exception as e:
        logger.error(f"Error listing webhooks: {e}")
        return jsonify({"error": "Internal server error"}), 500


@webhooks_bp.route("/<int:webhook_id>", methods=["PUT"])
@require_api_key
@limiter.limit("30 per minute")
def update_webhook(webhook_id):
    """
    Update a webhook configuration.

    Args:
        webhook_id: ID of the webhook to update

    Request Body (all fields optional):
    {
        "url": "https://new-url.com/webhook",
        "events": ["flood_detected", "critical_risk"],
        "is_active": true
    }

    Returns:
        200: Webhook updated successfully
        404: Webhook not found
    ---
    tags:
      - Webhooks
    parameters:
      - in: path
        name: webhook_id
        type: integer
        required: true
    responses:
      200:
        description: Webhook updated
      404:
        description: Not found
    """
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "No data provided"}), 400

        with get_db_session() as session:
            webhook = session.query(Webhook).filter_by(id=webhook_id, is_deleted=False).first()

            if not webhook:
                return jsonify({"error": "Webhook not found"}), 404

            # Update URL if provided
            if "url" in data:
                url = data["url"]
                if not url.startswith("http://") and not url.startswith("https://"):
                    return jsonify({"error": "Invalid URL format. Must start with http:// or https://"}), 400
                webhook.url = url

            # Update events if provided
            if "events" in data:
                events = data["events"]
                valid_events = ["flood_detected", "critical_risk", "high_risk", "medium_risk", "low_risk"]
                if not isinstance(events, list) or not events:
                    return jsonify({"error": "Events must be a non-empty list"}), 400

                for event in events:
                    if event not in valid_events:
                        return jsonify({"error": f"Invalid event: {event}. Valid events: {valid_events}"}), 400

                webhook.events = json.dumps(events)

            # Update active status if provided
            if "is_active" in data:
                webhook.is_active = bool(data["is_active"])

            # Update secret if provided
            if "secret" in data and data["secret"]:
                webhook.secret = data["secret"]

            webhook.updated_at = datetime.now(timezone.utc)
            session.commit()

            updated_data = {
                "id": webhook.id,
                "url": webhook.url,
                "events": json.loads(webhook.events),
                "is_active": webhook.is_active,
                "updated_at": webhook.updated_at.isoformat(),
            }

        logger.info(f"Webhook updated: {webhook_id}")

        return jsonify({"message": "Webhook updated successfully", "webhook": updated_data}), 200

    except Exception as e:
        logger.error(f"Error updating webhook: {e}")
        return jsonify({"error": "Internal server error"}), 500


@webhooks_bp.route("/<int:webhook_id>", methods=["DELETE"])
@require_api_key
@limiter.limit("10 per hour")
def delete_webhook(webhook_id):
    """
    Delete a webhook.

    Args:
        webhook_id: ID of the webhook to delete

    Returns:
        200: Webhook deleted successfully
        404: Webhook not found
    """
    try:
        with get_db_session() as session:
            webhook = session.query(Webhook).filter_by(id=webhook_id, is_deleted=False).first()

            if not webhook:
                return jsonify({"error": "Webhook not found"}), 404

            # Soft delete
            webhook.is_deleted = True
            webhook.deleted_at = datetime.now(timezone.utc)
            session.commit()

        logger.info(f"Webhook deleted: {webhook_id}")

        return jsonify({"message": "Webhook deleted successfully", "webhook_id": webhook_id}), 200

    except Exception as e:
        logger.error(f"Error deleting webhook: {e}")
        return jsonify({"error": "Internal server error"}), 500


@webhooks_bp.route("/<int:webhook_id>/toggle", methods=["POST"])
@require_api_key
@limiter.limit("30 per minute")
def toggle_webhook(webhook_id):
    """
    Enable or disable a webhook.

    Args:
        webhook_id: ID of the webhook to toggle

    Returns:
        200: Webhook toggled successfully
        404: Webhook not found
    """
    try:
        with get_db_session() as session:
            webhook = session.query(Webhook).filter_by(id=webhook_id, is_deleted=False).first()

            if not webhook:
                return jsonify({"error": "Webhook not found"}), 404

            webhook.is_active = not webhook.is_active
            webhook.updated_at = datetime.now(timezone.utc)
            session.commit()

            new_status = webhook.is_active

        logger.info(f"Webhook {webhook_id} {'enabled' if new_status else 'disabled'}")

        return (
            jsonify(
                {
                    "message": f'Webhook {"enabled" if new_status else "disabled"} successfully',
                    "webhook_id": webhook_id,
                    "is_active": new_status,
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Error toggling webhook: {e}")
        return jsonify({"error": "Internal server error"}), 500


@webhooks_bp.route("/<int:webhook_id>/test", methods=["POST"])
@require_api_key
@limiter.limit("10 per hour")
def test_webhook(webhook_id):
    """
    Send a test event to a webhook.

    Args:
        webhook_id: ID of the webhook to test

    Returns:
        200: Test delivery result
        404: Webhook not found
    ---
    tags:
      - Webhooks
    parameters:
      - in: path
        name: webhook_id
        type: integer
        required: true
    responses:
      200:
        description: Test delivery result
      404:
        description: Not found
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        with get_db_session() as session:
            webhook = session.query(Webhook).filter_by(id=webhook_id, is_deleted=False).first()

            if not webhook:
                return api_error("NotFound", "Webhook not found", HTTP_NOT_FOUND, request_id)

            webhook_url = webhook.url
            webhook_secret = webhook.secret

        # Send test payload
        test_payload = WebhookPayload(
            event_type="test",
            data={
                "message": "This is a test webhook delivery",
                "webhook_id": webhook_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        result = deliver_webhook(webhook_url, webhook_secret, test_payload)

        return (
            jsonify(
                {
                    "success": result.success,
                    "message": (
                        "Test webhook delivered successfully" if result.success else "Test webhook delivery failed"
                    ),
                    "delivery_result": {
                        "status_code": result.status_code,
                        "response_time_ms": round(result.response_time_ms, 2),
                        "error_message": result.error_message,
                    },
                    "request_id": request_id,
                }
            ),
            HTTP_OK,
        )

    except Exception as e:
        logger.error(f"Error testing webhook: {e}")
        return api_error("TestFailed", "Failed to test webhook", HTTP_INTERNAL_ERROR, request_id)


@webhooks_bp.route("/<int:webhook_id>/reset", methods=["POST"])
@require_api_key
@limiter.limit("30 per minute")
def reset_webhook_failures(webhook_id):
    """
    Reset failure count and re-enable a disabled webhook.

    Args:
        webhook_id: ID of the webhook to reset

    Returns:
        200: Webhook reset successfully
        404: Webhook not found
    ---
    tags:
      - Webhooks
    parameters:
      - in: path
        name: webhook_id
        type: integer
        required: true
    responses:
      200:
        description: Webhook reset
      404:
        description: Not found
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        with get_db_session() as session:
            webhook = session.query(Webhook).filter_by(id=webhook_id, is_deleted=False).first()

            if not webhook:
                return api_error("NotFound", "Webhook not found", HTTP_NOT_FOUND, request_id)

            old_failure_count = webhook.failure_count
            old_status = webhook.is_active

            webhook.failure_count = 0
            webhook.is_active = True
            webhook.updated_at = datetime.now(timezone.utc)
            session.commit()

        logger.info(f"Webhook {webhook_id} reset: failures {old_failure_count} -> 0, active {old_status} -> True")

        return (
            jsonify(
                {
                    "success": True,
                    "message": "Webhook reset successfully",
                    "webhook_id": webhook_id,
                    "previous_failure_count": old_failure_count,
                    "previous_status": old_status,
                    "current_status": True,
                    "request_id": request_id,
                }
            ),
            HTTP_OK,
        )

    except Exception as e:
        logger.error(f"Error resetting webhook: {e}")
        return api_error("ResetFailed", "Failed to reset webhook", HTTP_INTERNAL_ERROR, request_id)


@webhooks_bp.route("/trigger", methods=["POST"])
@require_api_key
@limiter.limit("30 per minute")
def trigger_webhook_event():
    """
    Manually trigger a webhook event to all subscribed webhooks.

    Request Body:
    {
        "event_type": "flood_detected",
        "data": {
            "risk_level": 2,
            "location": "Paranaque",
            "message": "Critical flood warning"
        }
    }

    Returns:
        200: Event triggered
    ---
    tags:
      - Webhooks
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - event_type
            - data
    responses:
      200:
        description: Event triggered
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        data = request.get_json()
        if not data:
            return api_error("InvalidRequest", "No data provided", HTTP_BAD_REQUEST, request_id)

        event_type = data.get("event_type")
        event_data = data.get("data", {})

        if not event_type:
            return api_error("ValidationError", "event_type is required", HTTP_BAD_REQUEST, request_id)

        valid_events = ["flood_detected", "critical_risk", "high_risk", "medium_risk", "low_risk", "test"]
        if event_type not in valid_events:
            return api_error(
                "ValidationError", f"Invalid event_type. Valid: {valid_events}", HTTP_BAD_REQUEST, request_id
            )

        result = broadcast_to_webhooks(event_type, event_data)

        return (
            jsonify(
                {
                    "success": True,
                    "message": f'Event "{event_type}" triggered for {result["webhooks_notified"]} webhooks',
                    "broadcast_result": result,
                    "request_id": request_id,
                }
            ),
            HTTP_OK,
        )

    except Exception as e:
        logger.error(f"Error triggering webhook event: {e}")
        return api_error("TriggerFailed", "Failed to trigger webhook event", HTTP_INTERNAL_ERROR, request_id)


@webhooks_bp.route("/config", methods=["GET"])
@limiter.limit("30 per minute")
def get_webhook_config():
    """
    Get webhook system configuration.

    Returns:
        200: Configuration details
    ---
    tags:
      - Webhooks
    responses:
      200:
        description: Webhook configuration
    """
    request_id = getattr(g, "request_id", "unknown")

    return (
        jsonify(
            {
                "success": True,
                "config": {
                    "max_retries": WEBHOOK_MAX_RETRIES,
                    "initial_delay_sec": WEBHOOK_INITIAL_DELAY_SEC,
                    "max_delay_sec": WEBHOOK_MAX_DELAY_SEC,
                    "backoff_multiplier": WEBHOOK_BACKOFF_MULTIPLIER,
                    "timeout_sec": WEBHOOK_TIMEOUT_SEC,
                    "jitter_factor": WEBHOOK_JITTER_FACTOR,
                    "max_failure_count": WEBHOOK_MAX_FAILURE_COUNT,
                    "retry_delays_preview": [calculate_backoff_delay(i) for i in range(WEBHOOK_MAX_RETRIES)],
                },
                "valid_events": ["flood_detected", "critical_risk", "high_risk", "medium_risk", "low_risk"],
                "request_id": request_id,
            }
        ),
        HTTP_OK,
    )
