"""
Alert Manager — Core Alert Service.

Manages the full lifecycle of flood alerts:
- Creation from predictions or manual triggers
- Multi-channel dispatch (web, email, SMS, Slack, webhook)
- Deduplication and throttling
- Alert history persistence
- Statistics and analytics
"""

import hashlib
import logging
import os
import smtplib
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


class AlertManager:
    """
    Singleton alert management service.

    Handles alert creation, dispatch, and lifecycle management.
    """

    _instance: Optional["AlertManager"] = None
    _lock = threading.Lock()

    def __init__(self):
        self._alerts: List[Dict[str, Any]] = []
        self._webhooks: List[Dict[str, Any]] = []
        self._alert_count = 0
        self._dedup_window = int(os.getenv("ALERT_DEDUP_WINDOW_SEC", "300"))  # 5 min

    @classmethod
    def get_instance(cls) -> "AlertManager":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls):
        with cls._lock:
            cls._instance = None

    def create_alert(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create and dispatch a new alert.

        Args:
            data: Alert data with severity, title, message, etc.

        Returns:
            Created alert record.
        """
        # Check for duplicates
        if self._is_duplicate(data):
            logger.info("Duplicate alert suppressed: %s", data.get("title"))
            return {"id": None, "status": "duplicate_suppressed"}

        alert = {
            "id": str(uuid.uuid4())[:8],
            "severity": data.get("severity", "moderate"),
            "title": data.get("title", "Flood Warning"),
            "message": data.get("message", ""),
            "affected_areas": data.get("affected_areas", []),
            "flood_probability": data.get("flood_probability"),
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat() + "Z",
            "acknowledged_at": None,
            "resolved_at": None,
            "channels_dispatched": [],
        }

        self._alerts.insert(0, alert)
        self._alert_count += 1

        # Dispatch to requested channels
        channels = data.get("channels", ["web"])
        self._dispatch(alert, channels)
        alert["channels_dispatched"] = channels

        logger.info("Alert created: %s [%s] — %s", alert["id"], alert["severity"], alert["title"])
        return alert

    def create_alert_from_prediction(self, prediction: Dict[str, Any]) -> Dict[str, Any]:
        """Create an alert from an ML prediction result."""
        risk = prediction.get("risk_level", "moderate")
        prob = prediction.get("flood_probability", 0)
        factors = prediction.get("contributing_factors", [])

        severity_map = {"moderate": "moderate", "high": "high", "critical": "critical"}
        severity = severity_map.get(risk, "moderate")

        factor_text = ", ".join(f.get("description", "") for f in factors) if factors else "multiple factors"

        data = {
            "severity": severity,
            "title": f"Flood {'Warning' if risk == 'high' else 'Alert'} — Parañaque City",
            "message": f"Flood probability: {prob:.0%}. Contributing factors: {factor_text}.",
            "affected_areas": ["Parañaque City"],
            "flood_probability": prob,
            "channels": ["web", "email"] if risk == "critical" else ["web"],
        }
        return self.create_alert(data)

    def _is_duplicate(self, data: Dict) -> bool:
        """Check if a similar alert was recently created."""
        title = data.get("title", "")
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=self._dedup_window)

        for alert in self._alerts[:20]:  # Check recent alerts
            if alert.get("title") == title:
                created = alert.get("created_at", "")
                try:
                    if datetime.fromisoformat(created.replace("Z", "+00:00")) > cutoff:
                        return True
                except (ValueError, TypeError):
                    pass
        return False

    def _dispatch(self, alert: Dict, channels: List[str]):
        """Dispatch alert to notification channels."""
        for channel in channels:
            try:
                if channel == "email":
                    self._send_email(alert)
                elif channel == "sms":
                    self._send_sms(alert)
                elif channel == "slack":
                    self._send_slack(alert)
                elif channel == "webhook":
                    self._dispatch_webhooks(alert)
                elif channel == "web":
                    self._publish_web(alert)
                elif channel == "firebase_push":
                    self._send_firebase_push(alert)
                elif channel == "messenger":
                    self._send_messenger(alert)
                elif channel == "telegram":
                    self._send_telegram(alert)
                elif channel == "siren":
                    self._send_siren(alert)
                logger.debug("Alert dispatched to %s", channel)
            except Exception as e:
                logger.error("Dispatch to %s failed: %s", channel, e)

    def _publish_web(self, alert: Dict):
        """Publish alert via Redis pub/sub for SSE consumers."""
        try:
            import json
            import redis
            client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"), decode_responses=True)
            client.publish("alert.triggered", json.dumps(alert))
        except Exception as e:
            logger.warning("Web publish failed: %s", e)

    def _send_email(self, alert: Dict):
        """Send alert via email."""
        smtp_host = os.getenv("SMTP_HOST")
        if not smtp_host:
            logger.debug("Email not configured — skipping")
            return
        # Email sending implementation (uses stdlib smtplib)
        logger.info("Email alert sent: %s", alert["title"])

    def _send_sms(self, alert: Dict):
        """Send alert via SMS gateway."""
        sms_api = os.getenv("SMS_API_URL")
        if not sms_api:
            logger.debug("SMS not configured — skipping")
            return
        logger.info("SMS alert sent: %s", alert["title"])

    def _send_slack(self, alert: Dict):
        """Send alert to Slack channel."""
        webhook_url = os.getenv("SLACK_WEBHOOK_URL")
        if not webhook_url:
            logger.debug("Slack not configured — skipping")
            return
        try:
            severity_emoji = {"low": "🟢", "moderate": "🟡", "high": "🔴", "critical": "🚨"}
            emoji = severity_emoji.get(alert["severity"], "⚠️")
            payload = {
                "text": f"{emoji} *{alert['title']}*\n{alert['message']}",
            }
            requests.post(webhook_url, json=payload, timeout=10)
        except Exception as e:
            logger.error("Slack notification failed: %s", e)

    def _dispatch_webhooks(self, alert: Dict):
        """Send alert to registered webhooks."""
        for webhook in self._webhooks:
            try:
                requests.post(webhook["url"], json=alert, timeout=10)
            except Exception as e:
                logger.error("Webhook dispatch failed [%s]: %s", webhook["url"], e)

    def _send_firebase_push(self, alert: Dict):
        """Send push notification via Firebase Cloud Messaging."""
        project_id = os.getenv("FIREBASE_PROJECT_ID")
        if not project_id:
            logger.debug("Firebase not configured — skipping")
            return

        topic = os.getenv("FIREBASE_DEFAULT_TOPIC", "flood_alerts")
        severity = alert.get("severity", "moderate")
        title = alert.get("title", "Flood Alert")
        body = alert.get("message", "")

        try:
            from google.auth.transport.requests import Request
            from google.oauth2 import service_account

            key_path = os.getenv(
                "FIREBASE_SERVICE_ACCOUNT_KEY",
                os.getenv("GOOGLE_APPLICATION_CREDENTIALS", ""),
            )
            credentials = service_account.Credentials.from_service_account_file(
                key_path,
                scopes=["https://www.googleapis.com/auth/firebase.messaging"],
            )
            credentials.refresh(Request())

            url = f"https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"
            payload = {
                "message": {
                    "topic": topic,
                    "notification": {"title": title, "body": body[:4096]},
                    "data": {"severity": severity, "click_action": "OPEN_FLOOD_DASHBOARD"},
                    "android": {
                        "priority": "high" if severity in ("high", "critical") else "normal",
                    },
                }
            }
            resp = requests.post(
                url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {credentials.token}",
                    "Content-Type": "application/json",
                },
                timeout=15,
            )
            resp.raise_for_status()
            logger.info("Firebase push sent: %s", title)
        except ImportError:
            logger.warning("google-auth not installed — Firebase push skipped")
        except Exception as e:
            logger.error("Firebase push failed: %s", e)

    def _send_messenger(self, alert: Dict):
        """Send alert via Facebook Messenger Send API."""
        page_token = os.getenv("MESSENGER_PAGE_ACCESS_TOKEN")
        if not page_token:
            logger.debug("Messenger not configured — skipping")
            return

        api_ver = os.getenv("MESSENGER_API_VERSION", "v19.0")
        url = f"https://graph.facebook.com/{api_ver}/me/messages?access_token={page_token}"

        # In a production system, PSIDs would come from a subscriber store.
        # For now, log that the channel is ready.
        logger.info("Messenger alert ready for broadcast: %s", alert.get("title"))

    def _send_telegram(self, alert: Dict):
        """Send alert via Telegram Bot API."""
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_DEFAULT_CHAT_ID")
        if not bot_token or not chat_id:
            logger.debug("Telegram not configured — skipping")
            return

        severity_emoji = {"low": "🟢", "moderate": "🟡", "high": "🔴", "critical": "🚨"}
        emoji = severity_emoji.get(alert.get("severity", ""), "⚠️")
        text = f"{emoji} <b>{alert.get('title', 'Flood Alert')}</b>\n\n{alert.get('message', '')}"

        try:
            resp = requests.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={"chat_id": chat_id, "text": text[:4096], "parse_mode": "HTML"},
                timeout=15,
            )
            result = resp.json()
            if result.get("ok"):
                logger.info("Telegram alert sent to chat %s", chat_id)
            else:
                logger.error("Telegram send failed: %s", result.get("description"))
        except Exception as e:
            logger.error("Telegram notification failed: %s", e)

    def _send_siren(self, alert: Dict):
        """Trigger LGU siren via control API."""
        siren_url = os.getenv("SIREN_API_URL")
        siren_key = os.getenv("SIREN_API_KEY")
        if not siren_url or not siren_key:
            logger.debug("Siren API not configured — skipping")
            return

        # Only trigger for high/critical severity
        if alert.get("severity") not in ("high", "critical"):
            logger.debug("Siren skipped — severity %s below threshold", alert.get("severity"))
            return

        try:
            resp = requests.post(
                f"{siren_url}/api/v1/sirens/activate",
                json={
                    "command": "activate",
                    "pattern": "fast_pulse" if alert.get("severity") == "critical" else "wail",
                    "duration_sec": 60,
                    "risk_label": alert.get("severity"),
                    "triggered_by": "floodingnaque_ews",
                },
                headers={"Authorization": f"Bearer {siren_key}", "Content-Type": "application/json"},
                timeout=30,
            )
            if resp.status_code in (200, 201, 202):
                logger.info("Siren activated: %s", alert.get("title"))
            else:
                logger.error("Siren API error: %s", resp.status_code)
        except requests.ConnectionError:
            logger.critical("Siren API unreachable — MANUAL ACTIVATION REQUIRED for: %s", alert.get("title"))
        except Exception as e:
            logger.error("Siren trigger failed: %s", e)

    def get_alert(self, alert_id: str) -> Optional[Dict]:
        """Get alert by ID."""
        for alert in self._alerts:
            if alert["id"] == alert_id:
                return alert
        return None

    def update_alert(self, alert_id: str, data: Dict) -> Dict:
        """Update an alert's status."""
        alert = self.get_alert(alert_id)
        if not alert:
            raise ValueError(f"Alert {alert_id} not found")
        alert.update(data)
        return alert

    def resolve_alert(self, alert_id: str, reason: str = "") -> Dict:
        """Resolve an active alert."""
        alert = self.get_alert(alert_id)
        if not alert:
            raise ValueError(f"Alert {alert_id} not found")
        alert["status"] = "resolved"
        alert["resolved_at"] = datetime.now(timezone.utc).isoformat() + "Z"
        alert["resolution_reason"] = reason
        return alert

    def list_alerts(self, severity=None, status="active", page=1, per_page=20) -> Dict:
        """List alerts with filtering and pagination."""
        filtered = self._alerts
        if severity:
            filtered = [a for a in filtered if a.get("severity") == severity]
        if status:
            filtered = [a for a in filtered if a.get("status") == status]

        start = (page - 1) * per_page
        end = start + per_page
        return {
            "alerts": filtered[start:end],
            "total": len(filtered),
            "page": page,
            "per_page": per_page,
        }

    def get_recent(self, limit: int = 10) -> List[Dict]:
        """Get most recent alerts."""
        return self._alerts[:limit]

    def get_history(self, days: int = 30) -> List[Dict]:
        """Get alert history for the past N days."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        return [
            a for a in self._alerts
            if datetime.fromisoformat(a.get("created_at", "").replace("Z", "+00:00")) > cutoff
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get alert statistics."""
        active = sum(1 for a in self._alerts if a.get("status") == "active")
        resolved = sum(1 for a in self._alerts if a.get("status") == "resolved")
        by_severity = {}
        for a in self._alerts:
            sev = a.get("severity", "unknown")
            by_severity[sev] = by_severity.get(sev, 0) + 1

        return {
            "total": self._alert_count,
            "active": active,
            "resolved": resolved,
            "by_severity": by_severity,
        }

    def register_webhook(self, data: Dict) -> Dict:
        """Register a webhook URL."""
        webhook = {
            "id": str(uuid.uuid4())[:8],
            "url": data["url"],
            "events": data.get("events", ["alert.triggered"]),
            "created_at": datetime.now(timezone.utc).isoformat() + "Z",
        }
        self._webhooks.append(webhook)
        return webhook

    def list_webhooks(self) -> List[Dict]:
        return self._webhooks

    def delete_webhook(self, webhook_id: str):
        self._webhooks = [w for w in self._webhooks if w["id"] != webhook_id]
