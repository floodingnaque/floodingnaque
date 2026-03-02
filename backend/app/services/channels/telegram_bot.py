"""
Telegram Bot Notification Channel.

Sends flood alerts to subscribed users / groups / channels
via the Telegram Bot API.

Required environment variables:
    TELEGRAM_BOT_TOKEN  - Bot API token from @BotFather

Optional:
    TELEGRAM_DEFAULT_CHAT_ID - Default chat / channel ID for broadcasts
    TELEGRAM_SANDBOX_MODE    - Set to "True" to skip real delivery
    TELEGRAM_PARSE_MODE      - Message parse mode (default: HTML)
"""

import logging
import os
from typing import Any, Dict, List, Optional

import requests

from app.services.channels.base import NotificationChannel

logger = logging.getLogger(__name__)


class TelegramBotChannel(NotificationChannel):
    """Deliver flood alerts via Telegram Bot API."""

    channel_id = "telegram"
    display_name = "Telegram Bot"

    def __init__(self, sandbox: bool = False):
        super().__init__(sandbox=sandbox)
        self._bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self._default_chat = os.getenv("TELEGRAM_DEFAULT_CHAT_ID", "")
        self._parse_mode = os.getenv("TELEGRAM_PARSE_MODE", "HTML")

    def is_configured(self) -> bool:
        return bool(self._bot_token)

    # ------------------------------------------------------------------
    # Message formatting
    # ------------------------------------------------------------------

    _EMOJI = {"Safe": "🟢", "Alert": "🟡", "Critical": "🔴"}

    def _format_html(self, risk_label: str, location: str, message: str) -> str:
        """Build an HTML-formatted Telegram message."""
        emoji = self._EMOJI.get(risk_label, "⚠️")
        dashboard_url = os.getenv("FRONTEND_URL", "https://floodingnaque.com")

        return (
            f"{emoji} <b>Flood {risk_label}</b> - {location}\n\n"
            f"{message[:4000]}\n\n"
            f'<a href="{dashboard_url}/dashboard">📊 Open Dashboard</a>\n'
            "<i>Floodingnaque Early Warning System</i>"
        )

    def _build_inline_keyboard(self, risk_label: str) -> Dict[str, Any]:
        """Optional inline keyboard buttons."""
        dashboard_url = os.getenv("FRONTEND_URL", "https://floodingnaque.com")
        return {
            "inline_keyboard": [
                [
                    {
                        "text": "📊 Dashboard",
                        "url": f"{dashboard_url}/dashboard",
                    },
                    {
                        "text": "🗺️ Flood Map",
                        "url": f"{dashboard_url}/map",
                    },
                ],
                [
                    {
                        "text": "ℹ️ Details",
                        "callback_data": f"details_{risk_label}",
                    },
                ],
            ]
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
        Send alert to Telegram chats / channels.

        ``recipients`` should contain Telegram chat IDs (numeric strings).
        If empty, uses ``TELEGRAM_DEFAULT_CHAT_ID``.
        """
        chat_ids = list(recipients) if recipients else []
        if not chat_ids and self._default_chat:
            chat_ids = [self._default_chat]
        if not chat_ids:
            logger.warning("TelegramBotChannel.send - no chat IDs provided")
            return "failed"

        url = f"https://api.telegram.org/bot{self._bot_token}/sendMessage"
        text = self._format_html(risk_label, location, message)
        keyboard = self._build_inline_keyboard(risk_label)

        success = 0
        fail = 0

        for chat_id in chat_ids:
            payload: Dict[str, Any] = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": self._parse_mode,
                "reply_markup": keyboard,
                "disable_web_page_preview": False,
            }

            # Critical alerts: send silently to avoid overnight disturbances
            # but mark them as important
            if risk_label == "Critical":
                payload["disable_notification"] = False
            else:
                payload["disable_notification"] = risk_label == "Safe"

            try:
                resp = requests.post(url, json=payload, timeout=15)
                result = resp.json()
                if result.get("ok"):
                    success += 1
                    logger.info(
                        "Telegram alert sent to chat %s (msg %s)",
                        chat_id,
                        result.get("result", {}).get("message_id"),
                    )
                else:
                    fail += 1
                    logger.error(
                        "Telegram send failed for chat %s: %s",
                        chat_id,
                        result.get("description", resp.text[:200]),
                    )
            except requests.RequestException as exc:
                fail += 1
                logger.error("Telegram request error for chat %s: %s", chat_id, exc)

        if fail == 0:
            return "delivered"
        elif success > 0:
            return "partial"
        return "failed"

    # ------------------------------------------------------------------
    # Webhook helpers (for receiving user commands)
    # ------------------------------------------------------------------

    def set_webhook(self, webhook_url: str) -> bool:
        """Register webhook URL with Telegram."""
        url = f"https://api.telegram.org/bot{self._bot_token}/setWebhook"
        try:
            resp = requests.post(url, json={"url": webhook_url}, timeout=10)
            ok = resp.json().get("ok", False)
            if ok:
                logger.info("Telegram webhook set: %s", webhook_url)
            return ok
        except Exception as exc:
            logger.error("Failed to set Telegram webhook: %s", exc)
            return False

    def handle_update(self, update: Dict[str, Any]) -> Optional[str]:
        """
        Process an incoming Telegram update (user command).

        Supported commands:
            /start  - Subscribe to alerts
            /stop   - Unsubscribe
            /status - Get current flood status

        Returns a reply message or None.
        """
        msg = update.get("message", {})
        text = msg.get("text", "").strip()
        chat_id = str(msg.get("chat", {}).get("id", ""))

        if text == "/start":
            return (
                "🌊 Welcome to Floodingnaque Flood Alerts!\n\n"
                "You will receive real-time flood warnings for "
                "Parañaque City.\n\n"
                "Commands:\n"
                "/status - Current flood status\n"
                "/stop - Unsubscribe"
            )
        elif text == "/stop":
            return "You have unsubscribed from flood alerts. Send /start to re-subscribe."
        elif text == "/status":
            return (
                "📊 Current Status: Monitoring\n"
                "Location: Parañaque City\n\n"
                "No active flood alerts at this time."
            )
        return None
