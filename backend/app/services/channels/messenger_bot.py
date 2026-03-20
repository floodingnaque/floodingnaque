"""
Facebook Messenger Chatbot Notification Channel.

Sends flood alerts to subscribed users via the Facebook Messenger
Send API.  Users subscribe through the Messenger bot and their
PSIDs (Page-Scoped IDs) are stored for broadcast alerts.

Required environment variables:
    MESSENGER_PAGE_ACCESS_TOKEN - Facebook Page long-lived access token
    MESSENGER_VERIFY_TOKEN      - Webhook verification token (for setup)

Optional:
    MESSENGER_SANDBOX_MODE - Set to "True" to skip real delivery
    MESSENGER_API_VERSION  - Graph API version (default: v19.0)
"""

import logging
import os
from typing import Any, Dict, List, Optional

import requests
from app.services.channels.base import NotificationChannel

logger = logging.getLogger(__name__)


class MessengerBotChannel(NotificationChannel):
    """Deliver flood alerts via Facebook Messenger Send API."""

    channel_id = "messenger"
    display_name = "Messenger Chatbot"

    def __init__(self, sandbox: bool = False):
        super().__init__(sandbox=sandbox)
        self._page_token = os.getenv("MESSENGER_PAGE_ACCESS_TOKEN", "")
        self._api_version = os.getenv("MESSENGER_API_VERSION", "v19.0")

    def is_configured(self) -> bool:
        return bool(self._page_token)

    # ------------------------------------------------------------------
    # Messenger template helpers
    # ------------------------------------------------------------------

    _COLOR_EMOJI = {"Safe": "🟢", "Alert": "🟡", "Critical": "🔴"}

    def _build_generic_template(self, risk_label: str, location: str, message: str) -> Dict[str, Any]:
        """Build a Messenger Generic Template for rich alert cards."""
        emoji = self._COLOR_EMOJI.get(risk_label, "⚠️")
        dashboard_url = os.getenv("FRONTEND_URL", "https://floodingnaque.com")

        return {
            "attachment": {
                "type": "template",
                "payload": {
                    "template_type": "generic",
                    "elements": [
                        {
                            "title": f"{emoji} Flood {risk_label} - {location}",
                            "subtitle": message[:80],
                            "buttons": [
                                {
                                    "type": "web_url",
                                    "url": f"{dashboard_url}/dashboard",
                                    "title": "Open Dashboard",
                                },
                                {
                                    "type": "postback",
                                    "title": "More Details",
                                    "payload": f"FLOOD_DETAILS_{risk_label}",
                                },
                            ],
                        }
                    ],
                },
            }
        }

    def _build_text_message(self, risk_label: str, location: str, message: str) -> Dict[str, str]:
        """Fallback plain-text message."""
        emoji = self._COLOR_EMOJI.get(risk_label, "⚠️")
        return {
            "text": (
                f"{emoji} *Flood {risk_label}* - {location}\n\n" f"{message[:2000]}\n\n" "Reply STOP to unsubscribe."
            )
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
        Send alert to Messenger users.

        ``recipients`` should be a list of Messenger PSIDs
        (Page-Scoped User IDs).
        """
        if not recipients:
            logger.warning("MessengerBotChannel.send called with no PSIDs")
            return "failed"

        url = f"https://graph.facebook.com/{self._api_version}/me/messages" f"?access_token={self._page_token}"

        use_template = (extra or {}).get("use_template", True)
        msg_payload = (
            self._build_generic_template(risk_label, location, message)
            if use_template
            else self._build_text_message(risk_label, location, message)
        )

        success = 0
        fail = 0

        for psid in recipients:
            body = {
                "recipient": {"id": psid},
                "message": msg_payload,
                "messaging_type": "MESSAGE_TAG",
                "tag": "CONFIRMED_EVENT_UPDATE",
            }

            try:
                resp = requests.post(url, json=body, timeout=15)
                if resp.status_code == 200:
                    success += 1
                    logger.info("Messenger alert sent to PSID %s", psid)
                else:
                    fail += 1
                    logger.error(
                        "Messenger send failed for PSID %s: %s - %s",
                        psid,
                        resp.status_code,
                        resp.text[:200],
                    )
            except requests.RequestException as exc:
                fail += 1
                logger.error("Messenger request error for %s: %s", psid, exc)

        if fail == 0:
            return "delivered"
        elif success > 0:
            return "partial"
        return "failed"

    # ------------------------------------------------------------------
    # Webhook verification (used during Facebook app setup)
    # ------------------------------------------------------------------

    @staticmethod
    def verify_webhook(mode: str, token: str, challenge: str) -> Optional[str]:
        """
        Handle Facebook webhook verification GET request.

        Returns the ``hub.challenge`` value if the token matches,
        otherwise *None*.
        """
        verify_token = os.getenv("MESSENGER_VERIFY_TOKEN", "")
        if mode == "subscribe" and token == verify_token:
            logger.info("Messenger webhook verified successfully")
            return challenge
        logger.warning("Messenger webhook verification failed")
        return None
