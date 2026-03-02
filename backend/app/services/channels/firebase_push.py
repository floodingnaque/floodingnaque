"""
Firebase Cloud Messaging (FCM) Push Notification Channel.

Sends mobile push notifications to registered devices via the
Firebase Cloud Messaging HTTP v1 API.

Required environment variables:
    FIREBASE_PROJECT_ID          — GCP / Firebase project ID
    FIREBASE_SERVICE_ACCOUNT_KEY — Path to service account JSON key file
                                   OR the JSON content itself

Optional:
    FIREBASE_SANDBOX_MODE  — Set to "True" to skip real delivery
    FIREBASE_DEFAULT_TOPIC — Default FCM topic (default: "flood_alerts")
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

import requests

from app.services.channels.base import NotificationChannel

logger = logging.getLogger(__name__)


class FirebasePushChannel(NotificationChannel):
    """Send push notifications via Firebase Cloud Messaging (HTTP v1 API)."""

    channel_id = "firebase_push"
    display_name = "Firebase Push Notification"

    def __init__(self, sandbox: bool = False):
        super().__init__(sandbox=sandbox)
        self._project_id = os.getenv("FIREBASE_PROJECT_ID", "")
        self._default_topic = os.getenv("FIREBASE_DEFAULT_TOPIC", "flood_alerts")
        self._access_token: Optional[str] = None
        self._token_expiry: float = 0

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def is_configured(self) -> bool:
        """Check that Firebase credentials are available."""
        return bool(
            self._project_id
            and (
                os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY")
                or os.path.exists(
                    os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
                )
            )
        )

    # ------------------------------------------------------------------
    # Token helper
    # ------------------------------------------------------------------

    def _get_access_token(self) -> str:
        """
        Obtain a short-lived OAuth 2.0 access token for FCM v1 API.

        Uses ``google-auth`` if available, otherwise returns a cached
        token from the environment (for lightweight deployments).
        """
        import time

        if self._access_token and time.time() < self._token_expiry:
            return self._access_token

        try:
            from google.auth.transport.requests import Request
            from google.oauth2 import service_account

            key_path = os.getenv(
                "FIREBASE_SERVICE_ACCOUNT_KEY",
                os.getenv("GOOGLE_APPLICATION_CREDENTIALS", ""),
            )

            if os.path.isfile(key_path):
                credentials = service_account.Credentials.from_service_account_file(
                    key_path,
                    scopes=["https://www.googleapis.com/auth/firebase.messaging"],
                )
            else:
                # Treat the env var value as inline JSON
                info = json.loads(key_path)
                credentials = service_account.Credentials.from_service_account_info(
                    info,
                    scopes=["https://www.googleapis.com/auth/firebase.messaging"],
                )

            credentials.refresh(Request())
            self._access_token = credentials.token
            self._token_expiry = time.time() + 3500  # ~58 min
            return self._access_token  # type: ignore[return-value]

        except ImportError:
            logger.warning(
                "google-auth package not installed — "
                "falling back to FIREBASE_ACCESS_TOKEN env var"
            )
            token = os.getenv("FIREBASE_ACCESS_TOKEN", "")
            if not token:
                raise RuntimeError(
                    "Neither google-auth nor FIREBASE_ACCESS_TOKEN is available"
                )
            return token

    # ------------------------------------------------------------------
    # Severity → Android notification channel mapping
    # ------------------------------------------------------------------

    _SEVERITY_CONFIG: Dict[str, Dict[str, str]] = {
        "Safe": {
            "android_channel": "flood_safe",
            "icon": "ic_flood_safe",
            "color": "#28a745",
            "priority": "default",
        },
        "Alert": {
            "android_channel": "flood_alert",
            "icon": "ic_flood_alert",
            "color": "#ffc107",
            "priority": "high",
        },
        "Critical": {
            "android_channel": "flood_critical",
            "icon": "ic_flood_critical",
            "color": "#dc3545",
            "priority": "high",
        },
    }

    # ------------------------------------------------------------------
    # Core send
    # ------------------------------------------------------------------

    def send(
        self,
        message: str,
        risk_label: str,
        location: str,
        recipients: Optional[List[str]] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Send push notification via FCM HTTP v1 API.

        ``recipients`` may contain:
        * FCM device registration tokens  (sent individually)
        * FCM topic names prefixed with ``/topics/``  (topic message)

        If *recipients* is empty the alert is sent to the default topic.
        """
        access_token = self._get_access_token()
        url = (
            f"https://fcm.googleapis.com/v1/projects/"
            f"{self._project_id}/messages:send"
        )
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; UTF-8",
        }

        sev = self._SEVERITY_CONFIG.get(risk_label, self._SEVERITY_CONFIG["Alert"])

        notification_body = {
            "title": f"Flood {risk_label} — {location}",
            "body": message[:4096],
        }

        data_payload = {
            "risk_label": risk_label,
            "location": location,
            "click_action": "OPEN_FLOOD_DASHBOARD",
            "sound": "flood_alarm" if risk_label == "Critical" else "default",
        }
        if extra:
            data_payload.update({k: str(v) for k, v in extra.items()})

        android_config = {
            "notification": {
                "channel_id": sev["android_channel"],
                "icon": sev["icon"],
                "color": sev["color"],
                "sound": "flood_alarm" if risk_label == "Critical" else "default",
                "default_vibrate_timings": risk_label == "Critical",
            },
            "priority": sev["priority"],
        }

        apns_config = {
            "payload": {
                "aps": {
                    "alert": notification_body,
                    "sound": "flood_alarm.caf" if risk_label == "Critical" else "default",
                    "badge": 1,
                    "content-available": 1,
                }
            },
        }

        targets: List[Dict[str, str]] = []
        if recipients:
            for r in recipients:
                if r.startswith("/topics/"):
                    targets.append({"topic": r.replace("/topics/", "")})
                else:
                    targets.append({"token": r})
        else:
            targets.append({"topic": self._default_topic})

        success = 0
        fail = 0

        for target in targets:
            body: Dict[str, Any] = {
                "message": {
                    **target,
                    "notification": notification_body,
                    "data": data_payload,
                    "android": android_config,
                    "apns": apns_config,
                }
            }

            try:
                resp = requests.post(url, headers=headers, json=body, timeout=15)
                if resp.status_code == 200:
                    success += 1
                    logger.info(
                        "FCM push delivered to %s: %s",
                        target,
                        resp.json().get("name", ""),
                    )
                else:
                    fail += 1
                    logger.error(
                        "FCM push failed for %s: %s — %s",
                        target,
                        resp.status_code,
                        resp.text[:200],
                    )
            except requests.RequestException as exc:
                fail += 1
                logger.error("FCM request error for %s: %s", target, exc)

        if fail == 0:
            return "delivered"
        elif success > 0:
            return "partial"
        return "failed"
