"""SMS service - evacuation alert dispatch with simulation fallback.

Supports Semaphore (primary) and Vonage (fallback) APIs.  When no API
keys are configured, runs in simulation mode: logs the message and
returns ``{"status": "simulated"}``.
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import requests as http_requests
from app.models.db import User, get_db_session
from app.models.evacuation_alert_log import EvacuationAlertLog
from app.services.evacuation_service import get_nearest_centers

logger = logging.getLogger(__name__)

# ── In-memory cooldown tracker (keyed by user ID) ───────────────────────
_sms_cooldowns: Dict[int, datetime] = {}


def _get_cooldown_minutes() -> int:
    return int(os.getenv("SMS_COOLDOWN_MINUTES", "30"))


def _is_on_cooldown(user_id: int) -> bool:
    """Check if the user was recently alerted (in-memory or Redis)."""
    redis_url = os.getenv("REDIS_URL", "")
    if redis_url:
        try:
            from urllib.parse import urlparse

            import redis

            parsed = urlparse(redis_url)
            r = redis.Redis(
                host=parsed.hostname or "localhost",
                port=parsed.port or 6379,
                password=parsed.password,
                socket_timeout=3,
            )
            key = f"sms_cooldown:{user_id}"
            if r.get(key):
                return True
            r.setex(key, timedelta(minutes=_get_cooldown_minutes()), "1")
            return False
        except Exception as exc:
            logger.debug("Redis cooldown check failed: %s - using in-memory", exc)

    # In-memory fallback
    now = datetime.now(timezone.utc)
    last = _sms_cooldowns.get(user_id)
    if last and now - last < timedelta(minutes=_get_cooldown_minutes()):
        return True
    _sms_cooldowns[user_id] = now
    return False


def send_sms(phone_number: str, message: str) -> Dict[str, Any]:
    """Send an SMS via Semaphore → Vonage → simulation fallback.

    Returns a dict with at least ``status`` (sent / failed / simulated).
    """
    # ── Semaphore (primary) ──────────────────────────────────────────────
    semaphore_key = os.getenv("SEMAPHORE_API_KEY", "")
    if semaphore_key:
        try:
            resp = http_requests.post(
                "https://api.semaphore.co/api/v4/messages",
                data={"apikey": semaphore_key, "number": phone_number, "message": message},
                timeout=15,
            )
            resp.raise_for_status()
            logger.info("SMS sent via Semaphore to %s", phone_number)
            return {"status": "sent", "provider": "semaphore", "phone": phone_number}
        except Exception as exc:
            logger.warning("Semaphore SMS failed: %s - trying Vonage", exc)

    # ── Vonage (fallback) ────────────────────────────────────────────────
    vonage_key = os.getenv("VONAGE_API_KEY", "")
    vonage_secret = os.getenv("VONAGE_API_SECRET", "")
    if vonage_key and vonage_secret:
        try:
            resp = http_requests.post(
                "https://rest.nexmo.com/sms/json",
                data={
                    "api_key": vonage_key,
                    "api_secret": vonage_secret,
                    "to": phone_number,
                    "from": "FLOODINGNAQUE",
                    "text": message,
                },
                timeout=15,
            )
            resp.raise_for_status()
            logger.info("SMS sent via Vonage to %s", phone_number)
            return {"status": "sent", "provider": "vonage", "phone": phone_number}
        except Exception as exc:
            logger.warning("Vonage SMS failed: %s - falling back to simulation", exc)

    # ── Simulation mode ──────────────────────────────────────────────────
    logger.info("[SMS SIMULATION] To: %s | Message: %s", phone_number, message[:100])
    return {"status": "simulated", "phone": phone_number, "message": message}


def build_evacuation_sms(
    barangay: str,
    risk_label: str,
    center_name: str,
    distance_km: float,
    available_slots: int,
    google_maps_url: str,
) -> str:
    """Build the standard evacuation alert SMS text."""
    return (
        f"[FLOODINGNAQUE ALERT] {risk_label} flood risk in {barangay}.\n"
        f"Nearest evacuation center: {center_name} ({distance_km:.1f} km).\n"
        f"Available slots: {available_slots}.\n"
        f"Directions: {google_maps_url}\n"
        f"Emergency hotline: Parañaque DRRMO 8 888-8988."
    )


def dispatch_evacuation_sms(barangay: str, risk_label: str) -> int:
    """Dispatch SMS alerts to all users with phone numbers.

    Applies per-user cooldown to avoid duplicate alerts.  Logs every
    dispatch attempt to :class:`EvacuationAlertLog`.

    Args:
        barangay: Affected barangay name.
        risk_label: Risk classification (Safe / Alert / Critical).

    Returns:
        Number of SMS messages dispatched (including simulated).
    """
    # Find nearest center for the barangay centroid (approximate)
    from app.services.gis_service import BARANGAY_META

    meta = None
    for key, m in BARANGAY_META.items():
        if m.get("name", "").lower() == barangay.lower() or key.lower() == barangay.lower():
            meta = m
            break

    center_info: Optional[Dict[str, Any]] = None
    if meta:
        centers = get_nearest_centers(meta["lat"], meta["lon"], limit=1)
        if centers:
            center_info = centers[0]

    # Build template parts
    center_name = center_info["center"]["name"] if center_info else "See DRRMO for details"
    distance_km = center_info["distance_km"] if center_info else 0.0
    available_slots = center_info["available_slots"] if center_info else 0
    google_maps_url = center_info.get("google_maps_url", "") if center_info else ""

    message = build_evacuation_sms(
        barangay=barangay,
        risk_label=risk_label,
        center_name=center_name,
        distance_km=distance_km,
        available_slots=available_slots,
        google_maps_url=google_maps_url,
    )

    dispatched = 0

    with get_db_session() as session:
        # Query all users with phone numbers
        users = (
            session.query(User)
            .filter(
                User.is_deleted.is_(False),
                User.is_active.is_(True),
                User.phone_number.isnot(None),
                User.phone_number != "",
            )
            .all()
        )

        for user in users:
            if _is_on_cooldown(user.id):
                logger.debug("Skipping user %d - on SMS cooldown", user.id)
                continue

            result = send_sms(user.phone_number, message)

            # Log to audit table
            log_entry = EvacuationAlertLog(
                user_id=user.id,
                center_id=center_info["center"]["id"] if center_info else None,
                sms_status=result.get("status", "failed"),
                channel="sms",
                barangay=barangay,
                risk_label=risk_label,
                message_text=message,
            )
            session.add(log_entry)
            dispatched += 1

    logger.info("Dispatched %d evacuation SMS for %s (%s)", dispatched, barangay, risk_label)
    return dispatched
