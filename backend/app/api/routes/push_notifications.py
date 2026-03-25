"""Push Notification Endpoints.

Manages Web Push subscriptions and delivers push notifications
for flood alerts via the VAPID protocol.
"""

import json
import logging

from app.api.middleware.auth import require_auth
from app.api.middleware.body_size import validate_json_body_size
from app.api.middleware.rate_limit import rate_limit_with_burst
from app.core.config import Config
from app.models.db import get_db_session
from app.models.push_subscription import PushSubscription
from app.utils.api_responses import api_error, api_success
from flask import Blueprint, g, request

logger = logging.getLogger(__name__)

push_notifications_bp = Blueprint("push_notifications", __name__)


def _get_vapid_config() -> tuple[str, str, dict[str, str | int]]:
    """Return (private_key, public_key, claims) from Config."""
    cfg = Config.get_instance()
    return (
        cfg.VAPID_PRIVATE_KEY,
        cfg.VAPID_PUBLIC_KEY,
        {"sub": cfg.VAPID_EMAIL},
    )


def _validate_subscription_json(subscription: dict) -> str | None:
    """Validate push subscription has required fields. Returns error message or None."""
    if not isinstance(subscription, dict):
        return "subscription must be an object"
    if not subscription.get("endpoint") or not isinstance(subscription["endpoint"], str):
        return "subscription.endpoint is required"
    keys = subscription.get("keys")
    if not isinstance(keys, dict):
        return "subscription.keys is required"
    if not keys.get("p256dh") or not isinstance(keys["p256dh"], str):
        return "subscription.keys.p256dh is required"
    if not keys.get("auth") or not isinstance(keys["auth"], str):
        return "subscription.keys.auth is required"
    return None


@push_notifications_bp.route("/vapid-public-key", methods=["GET"])
def get_vapid_key():
    """Return the VAPID public key so browsers can subscribe to push."""
    _, public_key, _ = _get_vapid_config()
    if not public_key:
        return api_error("PUSH_NOT_CONFIGURED", "Push notifications are not configured", 503)
    return api_success({"public_key": public_key})


@push_notifications_bp.route("/subscribe", methods=["POST"])
@require_auth
@rate_limit_with_burst("10 per minute")
@validate_json_body_size(max_size_kb=10)
def subscribe():
    """Save a push subscription from the browser."""
    data = request.get_json(silent=True)
    if not data:
        return api_error("INVALID_REQUEST", "Request body is required", 400)

    subscription = data.get("subscription")
    if not subscription:
        return api_error("INVALID_SUBSCRIPTION", "Valid push subscription required", 400)

    validation_error = _validate_subscription_json(subscription)
    if validation_error:
        return api_error("INVALID_SUBSCRIPTION", validation_error, 400)

    user_id = g.current_user_id
    endpoint = subscription["endpoint"]

    with get_db_session() as session:
        existing = (
            session.query(PushSubscription)
            .filter_by(user_id=user_id, endpoint=endpoint, is_deleted=False)
            .first()
        )

        if existing:
            existing.subscription_json = json.dumps(subscription)
        else:
            session.add(
                PushSubscription(
                    user_id=user_id,
                    endpoint=endpoint,
                    subscription_json=json.dumps(subscription),
                )
            )

    return api_success({"subscribed": True}, status_code=201)


@push_notifications_bp.route("/unsubscribe", methods=["DELETE"])
@require_auth
@rate_limit_with_burst("10 per minute")
@validate_json_body_size(max_size_kb=10)
def unsubscribe():
    """Remove a push subscription (soft-delete)."""
    data = request.get_json(silent=True)
    if not data:
        return api_error("INVALID_REQUEST", "Request body is required", 400)

    endpoint = data.get("endpoint")
    if not endpoint:
        return api_error("INVALID_REQUEST", "Endpoint is required", 400)

    user_id = g.current_user_id

    with get_db_session() as session:
        sub = (
            session.query(PushSubscription)
            .filter_by(user_id=user_id, endpoint=endpoint, is_deleted=False)
            .first()
        )
        if sub:
            sub.soft_delete()

    return api_success({"unsubscribed": True})


def _record_push_metrics(delivered: int, failed: int, expired: int) -> None:
    """Record push delivery Prometheus metrics if available."""
    try:
        from app.utils.observability.metrics import get_metrics

        metrics = get_metrics()
        if metrics and hasattr(metrics, "push_delivered_total"):
            metrics.push_delivered_total.inc(delivered)
            metrics.push_failed_total.inc(failed)
            metrics.push_expired_total.inc(expired)
    except Exception:
        pass


def send_push_to_barangay(barangay_id: str, payload: dict) -> dict:
    """Send push notification to all subscribed users in a barangay.

    Called by the alert system when risk level reaches Alert or Critical.
    Returns delivery stats.
    """
    from pywebpush import WebPushException, webpush

    private_key, _, claims = _get_vapid_config()
    if not private_key:
        logger.warning("VAPID_PRIVATE_KEY not set — push notifications disabled")
        return {"delivered": 0, "failed": 0, "reason": "not_configured"}

    with get_db_session() as session:
        subscriptions = (
            session.query(PushSubscription)
            .filter_by(barangay_id=barangay_id, is_deleted=False)
            .all()
        )

        expired_ids = []
        delivered = 0
        failed = 0
        for sub in subscriptions:
            try:
                webpush(
                    subscription_info=json.loads(sub.subscription_json),
                    data=json.dumps(payload),
                    vapid_private_key=private_key,
                    vapid_claims=claims,
                )
                delivered += 1
            except WebPushException as e:
                logger.warning("Push failed for sub %s: %s", sub.id, e)
                failed += 1
                if hasattr(e, "response") and e.response is not None and e.response.status_code == 410:
                    expired_ids.append(sub.id)
            except Exception as e:
                logger.warning("Unexpected push error for sub %s: %s", sub.id, e)
                failed += 1

        if expired_ids:
            for expired_sub in session.query(PushSubscription).filter(PushSubscription.id.in_(expired_ids)):
                expired_sub.soft_delete()

    _record_push_metrics(delivered, failed - len(expired_ids), len(expired_ids))

    logger.info(
        "Push sent to barangay %s: %d delivered, %d failed, %d expired",
        barangay_id,
        delivered,
        failed,
        len(expired_ids),
    )
    return {"delivered": delivered, "failed": failed, "expired": len(expired_ids)}


def send_push_citywide(payload: dict) -> dict:
    """Send push to ALL subscribed users across all barangays."""
    from pywebpush import WebPushException, webpush

    private_key, _, claims = _get_vapid_config()
    if not private_key:
        logger.warning("VAPID_PRIVATE_KEY not set — push notifications disabled")
        return {"delivered": 0, "failed": 0, "reason": "not_configured"}

    with get_db_session() as session:
        subscriptions = session.query(PushSubscription).filter_by(is_deleted=False).all()

        expired_ids = []
        delivered = 0
        failed = 0
        for sub in subscriptions:
            try:
                webpush(
                    subscription_info=json.loads(sub.subscription_json),
                    data=json.dumps(payload),
                    vapid_private_key=private_key,
                    vapid_claims=claims,
                )
                delivered += 1
            except WebPushException as e:
                logger.warning("Push failed for sub %s: %s", sub.id, e)
                failed += 1
                if hasattr(e, "response") and e.response is not None and e.response.status_code == 410:
                    expired_ids.append(sub.id)
            except Exception as e:
                logger.warning("Unexpected push error for sub %s: %s", sub.id, e)
                failed += 1

        if expired_ids:
            for expired_sub in session.query(PushSubscription).filter(PushSubscription.id.in_(expired_ids)):
                expired_sub.soft_delete()

    _record_push_metrics(delivered, failed - len(expired_ids), len(expired_ids))

    logger.info(
        "Citywide push: %d delivered, %d failed, %d expired",
        delivered,
        failed,
        len(expired_ids),
    )
    return {"delivered": delivered, "failed": failed, "expired": len(expired_ids)}
