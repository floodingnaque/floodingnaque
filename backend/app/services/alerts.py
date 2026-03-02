"""
Alert System Module for Flood Detection and Early Warning.

Multi-channel notification support:
    - Web Dashboard (SSE real-time)
    - SMS (Semaphore / Twilio)
    - Email (SMTP)
    - Slack (Incoming Webhook)
    - Firebase Push Notifications (FCM)
    - Facebook Messenger Chatbot
    - Telegram Bot
    - LGU Siren Trigger (future hardware)

Aligned with research objectives for Parañaque City.
Alerts are persisted to database to prevent data loss on restart.
"""

import json
import logging
import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional, TYPE_CHECKING

import requests
from app.core.constants import DEFAULT_LATITUDE, DEFAULT_LOCATION_NAME, DEFAULT_LONGITUDE
from app.models.db import AlertHistory, get_db_session
from app.services.channels.email_alerts import EmailAlertChannel
from app.services.channels.firebase_push import FirebasePushChannel
from app.services.channels.messenger_bot import MessengerBotChannel
from app.services.channels.siren_trigger import SirenTriggerChannel
from app.services.channels.telegram_bot import TelegramBotChannel
from app.services.risk_classifier import format_alert_message

if TYPE_CHECKING:
    from app.services.smart_alert_evaluator import SmartAlertDecision

logger = logging.getLogger(__name__)

# Parañaque City coordinates - sourced from central constants
PARANAQUE_COORDS: Dict[str, Any] = {
    "lat": DEFAULT_LATITUDE,
    "lon": DEFAULT_LONGITUDE,
    "name": DEFAULT_LOCATION_NAME,
    "region": "Metro Manila",
    "country": "Philippines",
}


class AlertSystem:
    """
    Alert system for flood warnings.

    This class manages flood alert notifications through various channels
    (web, SMS, email, Slack) and maintains alert history.
    """

    _instance: Optional["AlertSystem"] = None

    # All supported channel identifiers
    SUPPORTED_CHANNELS = (
        "web", "sms", "email", "slack",
        "firebase_push", "messenger", "telegram", "siren",
    )

    def __init__(
        self,
        sms_enabled: bool = False,
        email_enabled: bool = False,
        slack_enabled: bool = False,
        firebase_push_enabled: bool = False,
        messenger_enabled: bool = False,
        telegram_enabled: bool = False,
        siren_enabled: bool = False,
    ):
        """
        Initialize alert system.

        Args:
            sms_enabled: Enable SMS notifications (requires SMS gateway API)
            email_enabled: Enable email notifications (requires SMTP config)
            slack_enabled: Enable Slack notifications (requires SLACK_WEBHOOK_URL)
            firebase_push_enabled: Enable Firebase push notifications (requires FCM config)
            messenger_enabled: Enable Facebook Messenger bot (requires Page token)
            telegram_enabled: Enable Telegram bot (requires bot token)
            siren_enabled: Enable LGU siren trigger (requires siren API)
        """
        self.sms_enabled = sms_enabled
        self.email_enabled = email_enabled
        self.slack_enabled = slack_enabled
        self.firebase_push_enabled = firebase_push_enabled
        self.messenger_enabled = messenger_enabled
        self.telegram_enabled = telegram_enabled
        self.siren_enabled = siren_enabled

        # Instantiate pluggable channel objects
        self._firebase_channel = FirebasePushChannel()
        self._messenger_channel = MessengerBotChannel()
        self._telegram_channel = TelegramBotChannel()
        self._siren_channel = SirenTriggerChannel()
        self._email_channel = EmailAlertChannel()

        # In-memory cache for recent alerts (performance optimization)
        self._alert_cache: List[Dict[str, Any]] = []

    @classmethod
    def get_instance(
        cls,
        sms_enabled: bool = False,
        email_enabled: bool = False,
        slack_enabled: bool = False,
        firebase_push_enabled: bool = False,
        messenger_enabled: bool = False,
        telegram_enabled: bool = False,
        siren_enabled: bool = False,
    ) -> "AlertSystem":
        """
        Get or create the singleton AlertSystem instance.

        This provides a controlled way to access the alert system
        instead of using a global mutable variable.

        Args:
            sms_enabled: Enable SMS notifications
            email_enabled: Enable email notifications
            slack_enabled: Enable Slack notifications
            firebase_push_enabled: Enable Firebase push notifications
            messenger_enabled: Enable Messenger chatbot
            telegram_enabled: Enable Telegram bot
            siren_enabled: Enable LGU siren trigger

        Returns:
            AlertSystem: The singleton instance
        """
        if cls._instance is None:
            cls._instance = cls(
                sms_enabled=sms_enabled,
                email_enabled=email_enabled,
                slack_enabled=slack_enabled,
                firebase_push_enabled=firebase_push_enabled,
                messenger_enabled=messenger_enabled,
                telegram_enabled=telegram_enabled,
                siren_enabled=siren_enabled,
            )
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """
        Reset the singleton instance (useful for testing).
        """
        cls._instance = None

    def send_alert(
        self,
        risk_data: Dict[str, Any],
        location: Optional[str] = None,
        recipients: Optional[List[str]] = None,
        alert_type: str = "web",
        smart_decision: Optional["SmartAlertDecision"] = None,
    ) -> Dict[str, Any]:
        """
        Send flood alert notification.

        Args:
            risk_data: Risk classification data from risk_classifier
            location: Location name (default: Parañaque City)
            recipients: List of phone numbers or email addresses
            alert_type: 'web', 'sms', 'email', or 'all'
            smart_decision: Optional SmartAlertDecision from smart evaluator

        Returns:
            dict: Alert delivery status
        """
        if not location:
            location = PARANAQUE_COORDS["name"]

        risk_label = risk_data.get("risk_label", "Unknown")

        # Format alert message
        message = format_alert_message(risk_data, location)

        # Create alert record
        alert_record = {
            "timestamp": datetime.now().isoformat(),
            "location": location,
            "risk_level": risk_data.get("risk_level"),
            "risk_label": risk_label,
            "message": message,
            "delivery_status": {},
        }

        # Attach smart alert metadata
        if smart_decision:
            alert_record["confidence_score"] = smart_decision.confidence
            alert_record["rainfall_3h"] = smart_decision.rainfall_3h
            alert_record["escalation_state"] = smart_decision.escalation_state
            alert_record["escalation_reason"] = smart_decision.escalation_reason
            alert_record["suppressed"] = smart_decision.was_suppressed
            alert_record["contributing_factors"] = smart_decision.contributing_factors

        # If suppressed by smart alert logic, persist but skip dispatch
        if smart_decision and smart_decision.was_suppressed:
            alert_record["delivery_status"]["suppressed"] = "suppressed"
            self._persist_alert(alert_record)
            logger.info(
                "Alert suppressed by smart logic for %s: %s",
                location, smart_decision.contributing_factors,
            )
            return alert_record

        # Send based on alert type
        if alert_type in ["web", "all"]:
            alert_record["delivery_status"]["web"] = "delivered"
            logger.info(f"Web alert sent: {risk_label} for {location}")

        # Broadcast to all connected SSE clients (primary real-time channel)
        if alert_type in ["web", "all"]:
            try:
                from app.api.routes.sse import broadcast_alert

                client_count = broadcast_alert(alert_record)
                alert_record["delivery_status"]["sse"] = "delivered"
                logger.info(
                    f"SSE broadcast: {risk_label} for {location} → {client_count} clients"
                )
            except Exception as sse_exc:
                logger.error(f"SSE broadcast failed: {sse_exc}")
                alert_record["delivery_status"]["sse"] = "failed"

        if alert_type in ["sms", "all"] and self.sms_enabled and recipients:
            sms_status = self._send_sms(recipients, message)
            alert_record["delivery_status"]["sms"] = sms_status
            logger.info(f"SMS alert sent: {risk_label} for {location}")

        # Auto-trigger SMS for Critical risk conditions regardless of alert_type
        # This ensures community alerts reach residents even if only 'web' was requested.
        if (
            risk_data.get("risk_level") == 2
            and self.sms_enabled
            and alert_type not in ["sms", "all"]
            and recipients
        ):
            sms_status = self._send_sms(recipients, message)
            alert_record["delivery_status"]["sms_critical_auto"] = sms_status
            logger.info(
                f"Auto SMS (Critical) sent: {risk_label} for {location} → {sms_status}"
            )

        if alert_type in ["email", "all"] and self.email_enabled and recipients:
            email_status = self._send_email(recipients, risk_label, message)
            alert_record["delivery_status"]["email"] = email_status
            logger.info(f"Email alert sent: {risk_label} for {location}")

        if alert_type in ["slack", "all"] and self.slack_enabled:
            slack_status = self._send_slack(risk_label, message, location)
            alert_record["delivery_status"]["slack"] = slack_status
            logger.info(f"Slack alert sent: {risk_label} for {location}")

        # --- New multi-channel dispatch ---

        if alert_type in ["firebase_push", "all"] and self.firebase_push_enabled:
            fcm_status = self._firebase_channel.dispatch(
                message=message, risk_label=risk_label, location=location,
                recipients=recipients,
            )
            alert_record["delivery_status"]["firebase_push"] = fcm_status
            logger.info(f"Firebase push sent: {risk_label} for {location} → {fcm_status}")

        if alert_type in ["messenger", "all"] and self.messenger_enabled:
            messenger_status = self._messenger_channel.dispatch(
                message=message, risk_label=risk_label, location=location,
                recipients=recipients,
            )
            alert_record["delivery_status"]["messenger"] = messenger_status
            logger.info(f"Messenger alert sent: {risk_label} for {location} → {messenger_status}")

        if alert_type in ["telegram", "all"] and self.telegram_enabled:
            telegram_status = self._telegram_channel.dispatch(
                message=message, risk_label=risk_label, location=location,
                recipients=recipients,
            )
            alert_record["delivery_status"]["telegram"] = telegram_status
            logger.info(f"Telegram alert sent: {risk_label} for {location} → {telegram_status}")

        if alert_type in ["siren", "all"] and self.siren_enabled:
            siren_status = self._siren_channel.dispatch(
                message=message, risk_label=risk_label, location=location,
                recipients=recipients,
            )
            alert_record["delivery_status"]["siren"] = siren_status
            logger.info(f"Siren trigger: {risk_label} for {location} → {siren_status}")

        # Auto-trigger multi-channel for Critical risk
        if risk_data.get("risk_level") == 2 and alert_type not in ["all"]:
            if self.firebase_push_enabled and "firebase_push" not in alert_record["delivery_status"]:
                auto_fcm = self._firebase_channel.dispatch(
                    message=message, risk_label=risk_label, location=location,
                    recipients=recipients,
                )
                alert_record["delivery_status"]["firebase_push_critical_auto"] = auto_fcm
            if self.telegram_enabled and "telegram" not in alert_record["delivery_status"]:
                auto_tg = self._telegram_channel.dispatch(
                    message=message, risk_label=risk_label, location=location,
                    recipients=recipients,
                )
                alert_record["delivery_status"]["telegram_critical_auto"] = auto_tg
            if self.siren_enabled and "siren" not in alert_record["delivery_status"]:
                auto_siren = self._siren_channel.dispatch(
                    message=message, risk_label=risk_label, location=location,
                    recipients=recipients,
                )
                alert_record["delivery_status"]["siren_critical_auto"] = auto_siren

        # Store in history (persist to database)
        self._persist_alert(alert_record)

        return alert_record

    def _persist_alert(self, alert_record: Dict[str, Any], prediction_id: Optional[int] = None) -> None:
        """
        Persist alert to database for durability.

        Args:
            alert_record: Alert data to persist
            prediction_id: Optional ID of related prediction
        """
        try:
            # Determine escalation_state for DB
            escalation_state = alert_record.get("escalation_state", "initial")
            if escalation_state in ("critical",) and alert_record.get("escalation_reason") == "persisted_30min":
                escalation_state = "auto_escalated"
            elif escalation_state in ("critical", "alert"):
                escalation_state = "escalated" if alert_record.get("escalation_reason") else "initial"

            # Serialise contributing factors
            factors = alert_record.get("contributing_factors")
            factors_json = json.dumps(factors) if factors else None

            with get_db_session() as session:
                db_alert = AlertHistory(
                    prediction_id=prediction_id,
                    risk_level=alert_record.get("risk_level", 0),
                    risk_label=alert_record.get("risk_label", "Unknown"),
                    location=alert_record.get("location"),
                    recipients=json.dumps(alert_record.get("recipients", [])),
                    message=alert_record.get("message"),
                    delivery_status=self._get_primary_status(alert_record.get("delivery_status", {})),
                    delivery_channel=self._get_delivery_channels(alert_record.get("delivery_status", {})),
                    delivered_at=datetime.now() if alert_record.get("delivery_status") else None,
                    # Smart alert fields
                    confidence_score=alert_record.get("confidence_score"),
                    rainfall_3h=alert_record.get("rainfall_3h"),
                    escalation_state=escalation_state,
                    escalation_reason=alert_record.get("escalation_reason"),
                    suppressed=alert_record.get("suppressed", False),
                    contributing_factors=factors_json,
                )
                session.add(db_alert)

            # Update in-memory cache
            self._alert_cache.append(alert_record)
            # Keep cache size limited
            if len(self._alert_cache) > 100:
                self._alert_cache = self._alert_cache[-100:]

            logger.debug(f"Alert persisted to database: {alert_record.get('risk_label')}")
        except Exception as e:
            logger.error(f"Failed to persist alert to database: {str(e)}")
            # Still keep in memory cache as fallback
            self._alert_cache.append(alert_record)

    def _get_primary_status(self, delivery_status: Dict[str, str]) -> str:
        """Get primary delivery status from all channels."""
        if not delivery_status:
            return "pending"
        if "delivered" in delivery_status.values():
            return "delivered"
        if "failed" in delivery_status.values():
            return "failed"
        return "pending"

    def _get_delivery_channels(self, delivery_status: Dict[str, str]) -> str:
        """Get comma-separated list of delivery channels used."""
        return ",".join(delivery_status.keys()) if delivery_status else ""

    def _send_sms(self, recipients: List[str], message: str) -> str:
        """
        Send SMS notification via configured SMS provider.

        Supports:
        - Semaphore (Philippines - affordable local provider)
        - Twilio (International)

        Args:
            recipients: List of phone numbers (Philippine format: 09XXXXXXXXX or +639XXXXXXXXX)
            message: Alert message

        Returns:
            str: Delivery status ('delivered', 'failed', 'sandbox', 'not_configured')
        """
        provider = os.getenv("SMS_PROVIDER", "semaphore").lower()
        sandbox_mode = os.getenv("SMS_SANDBOX_MODE", "False").lower() == "true"

        if sandbox_mode:
            logger.info(f"[SANDBOX] SMS would be sent to {recipients}: {message[:50]}...")
            return "sandbox"

        if provider == "semaphore":
            return self._send_sms_semaphore(recipients, message)
        elif provider == "twilio":
            return self._send_sms_twilio(recipients, message)
        else:
            logger.warning(f"Unknown SMS provider: {provider}")
            return "not_configured"

    def _send_sms_semaphore(self, recipients: List[str], message: str) -> str:
        """
        Send SMS via Semaphore API (Philippines).

        Semaphore is an affordable SMS gateway for the Philippines.
        API docs: https://semaphore.co/docs

        Args:
            recipients: List of Philippine phone numbers
            message: Alert message (max 160 chars for 1 credit)

        Returns:
            str: Delivery status
        """
        api_key = os.getenv("SEMAPHORE_API_KEY")
        sender_name = os.getenv("SEMAPHORE_SENDER_NAME", "FloodAlert")

        if not api_key:
            logger.error("SEMAPHORE_API_KEY not configured")
            return "not_configured"

        api_url = "https://api.semaphore.co/api/v4/messages"
        success_count = 0
        fail_count = 0

        for recipient in recipients:
            # Normalize Philippine phone number format
            phone = self._normalize_ph_number(recipient)

            try:
                payload = {"apikey": api_key, "number": phone, "message": message, "sendername": sender_name}

                response = requests.post(api_url, data=payload, timeout=30)

                if response.status_code == 200:
                    result = response.json()
                    if isinstance(result, list) and len(result) > 0:
                        logger.info(f"SMS sent to {phone} via Semaphore: {result[0].get('message_id', 'OK')}")
                        success_count += 1
                    else:
                        logger.warning(f"Semaphore response unexpected: {result}")
                        success_count += 1  # Still count as success if 200
                else:
                    logger.error(f"Semaphore SMS failed for {phone}: {response.status_code} - {response.text}")
                    fail_count += 1

            except requests.exceptions.Timeout:
                logger.error(f"Semaphore SMS timeout for {phone}")
                fail_count += 1
            except requests.exceptions.RequestException as e:
                logger.error(f"Semaphore SMS error for {phone}: {str(e)}")
                fail_count += 1

        if fail_count == 0:
            return "delivered"
        elif success_count > 0:
            return "partial"
        else:
            return "failed"

    def _normalize_ph_number(self, phone: str) -> str:
        """
        Normalize Philippine phone number to format required by Semaphore.

        Accepts: 09XXXXXXXXX, +639XXXXXXXXX, 639XXXXXXXXX
        Returns: 09XXXXXXXXX format
        """
        phone = phone.strip().replace(" ", "").replace("-", "")

        if phone.startswith("+63"):
            phone = "0" + phone[3:]
        elif phone.startswith("63"):
            phone = "0" + phone[2:]
        elif phone.startswith("9") and len(phone) == 10:
            phone = "0" + phone

        return phone

    def _send_sms_twilio(self, recipients: List[str], message: str) -> str:
        """
        Send SMS via Twilio API (International).

        Args:
            recipients: List of phone numbers in E.164 format
            message: Alert message

        Returns:
            str: Delivery status
        """
        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        from_number = os.getenv("TWILIO_FROM_NUMBER")

        if not all([account_sid, auth_token, from_number]):
            logger.error("Twilio credentials not fully configured")
            return "not_configured"

        api_url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
        success_count = 0
        fail_count = 0

        for recipient in recipients:
            try:
                payload = {"To": recipient, "From": from_number, "Body": message}

                response = requests.post(api_url, data=payload, auth=(account_sid, auth_token), timeout=30)

                if response.status_code in [200, 201]:
                    result = response.json()
                    logger.info(f"SMS sent to {recipient} via Twilio: {result.get('sid', 'OK')}")
                    success_count += 1
                else:
                    logger.error(f"Twilio SMS failed for {recipient}: {response.status_code} - {response.text}")
                    fail_count += 1

            except requests.exceptions.RequestException as e:
                logger.error(f"Twilio SMS error for {recipient}: {str(e)}")
                fail_count += 1

        if fail_count == 0:
            return "delivered"
        elif success_count > 0:
            return "partial"
        else:
            return "failed"

    def _send_email(self, recipients: List[str], subject: str, message: str) -> str:
        """
        Send email notification via SMTP (Brevo/SendGrid/other).

        Args:
            recipients: List of email addresses
            subject: Email subject (risk label)
            message: Alert message

        Returns:
            str: Delivery status ('delivered', 'failed', 'sandbox', 'not_configured')
        """
        sandbox_mode = os.getenv("EMAIL_SANDBOX_MODE", "False").lower() == "true"

        if sandbox_mode:
            logger.info(f"[SANDBOX] Email would be sent to {recipients}: {subject}")
            return "sandbox"

        # Get SMTP configuration
        smtp_host = os.getenv("SMTP_HOST")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_username = os.getenv("SMTP_USERNAME")
        smtp_password = os.getenv("SMTP_PASSWORD")
        smtp_from = os.getenv("SMTP_FROM_EMAIL", "alerts@floodingnaque.com")
        use_tls = os.getenv("SMTP_USE_TLS", "True").lower() == "true"

        if not all([smtp_host, smtp_username, smtp_password]):
            logger.error("SMTP credentials not fully configured")
            return "not_configured"

        success_count = 0
        fail_count = 0

        for recipient in recipients:
            try:
                # Create email message
                msg = MIMEMultipart("alternative")
                msg["Subject"] = f"[Floodingnaque Alert] {subject}"
                msg["From"] = smtp_from
                msg["To"] = recipient

                # Plain text version
                text_part = MIMEText(message, "plain", "utf-8")
                msg.attach(text_part)

                # HTML version with styling
                html_message = self._format_html_email(subject, message)
                html_part = MIMEText(html_message, "html", "utf-8")
                msg.attach(html_part)

                # Connect and send
                with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
                    if use_tls:
                        server.starttls()
                    server.login(smtp_username, smtp_password)
                    server.sendmail(smtp_from, recipient, msg.as_string())

                logger.info(f"Email sent to {recipient}: {subject}")
                success_count += 1

            except smtplib.SMTPAuthenticationError as e:
                logger.error(f"SMTP authentication failed: {str(e)}")
                fail_count += 1
            except smtplib.SMTPException as e:
                logger.error(f"SMTP error for {recipient}: {str(e)}")
                fail_count += 1
            except Exception as e:
                logger.error(f"Email error for {recipient}: {str(e)}")
                fail_count += 1

        if fail_count == 0:
            return "delivered"
        elif success_count > 0:
            return "partial"
        else:
            return "failed"

    def _format_html_email(self, risk_label: str, message: str) -> str:
        """
        Format alert message as HTML email.

        Args:
            risk_label: Risk level label (Safe, Alert, Critical)
            message: Plain text message

        Returns:
            str: HTML formatted email
        """
        # Determine color based on risk level
        color_map = {"Safe": "#28a745", "Alert": "#ffc107", "Critical": "#dc3545"}
        color = color_map.get(risk_label, "#6c757d")

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5;">
            <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <div style="background-color: {color}; color: white; padding: 20px; text-align: center;">
                    <h1 style="margin: 0; font-size: 24px;">Flood Risk Alert: {risk_label}</h1>
                </div>
                <div style="padding: 20px;">
                    <pre style="white-space: pre-wrap; font-family: Arial, sans-serif; line-height: 1.6; margin: 0;">{message}</pre>
                </div>
                <div style="background-color: #f8f9fa; padding: 15px; text-align: center; font-size: 12px; color: #6c757d;">
                    <p style="margin: 0;">Floodingnaque Early Warning System</p>
                    <p style="margin: 5px 0 0 0;">Parañaque City, Philippines</p>
                </div>
            </div>
        </body>
        </html>
        """
        return html

    def _send_slack(self, risk_label: str, message: str, location: str) -> str:
        """
        Send a Slack notification via an Incoming Webhook.

        Requires the ``SLACK_WEBHOOK_URL`` environment variable to be set
        to a valid Slack Incoming Webhook URL.

        Args:
            risk_label: Risk level label (Safe, Alert, Critical)
            message: Plain text alert message
            location: Location string for the alert

        Returns:
            str: Delivery status ('delivered', 'failed', 'not_configured')
        """
        webhook_url = os.getenv("SLACK_WEBHOOK_URL", "").strip()
        if not webhook_url:
            logger.error("SLACK_WEBHOOK_URL not configured - cannot send Slack alert")
            return "not_configured"

        color_map = {"Safe": "#28a745", "Alert": "#ffc107", "Critical": "#dc3545"}
        color = color_map.get(risk_label, "#6c757d")

        payload = {
            "attachments": [
                {
                    "color": color,
                    "title": f":warning: Flood Risk Alert - {risk_label}",
                    "text": message,
                    "fields": [
                        {"title": "Location", "value": location, "short": True},
                        {"title": "Risk Level", "value": risk_label, "short": True},
                    ],
                    "footer": "Floodingnaque Early Warning System",
                }
            ]
        }

        try:
            resp = requests.post(webhook_url, json=payload, timeout=10)
            resp.raise_for_status()
            logger.info(f"Slack alert delivered: {risk_label} for {location}")
            return "delivered"
        except requests.RequestException as exc:
            logger.error(f"Slack webhook failed: {exc}")
            return "failed"

    def get_alert_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent alert history from database."""
        try:
            with get_db_session() as session:
                alerts = session.query(AlertHistory).order_by(AlertHistory.created_at.desc()).limit(limit).all()

                return [
                    {
                        "id": alert.id,
                        "timestamp": alert.created_at.isoformat() if alert.created_at else None,
                        "location": alert.location,
                        "risk_level": alert.risk_level,
                        "risk_label": alert.risk_label,
                        "message": alert.message,
                        "delivery_status": alert.delivery_status,
                        "delivery_channel": alert.delivery_channel,
                    }
                    for alert in alerts
                ]
        except Exception as e:
            logger.error(f"Failed to fetch alert history from database: {str(e)}")
            # Fallback to in-memory cache
            return self._alert_cache[-limit:]

    def get_alerts_by_risk_level(self, risk_level: int) -> List[Dict[str, Any]]:
        """Get alerts filtered by risk level from database."""
        try:
            with get_db_session() as session:
                alerts = (
                    session.query(AlertHistory)
                    .filter(AlertHistory.risk_level == risk_level)
                    .order_by(AlertHistory.created_at.desc())
                    .limit(100)
                    .all()
                )

                return [
                    {
                        "id": alert.id,
                        "timestamp": alert.created_at.isoformat() if alert.created_at else None,
                        "location": alert.location,
                        "risk_level": alert.risk_level,
                        "risk_label": alert.risk_label,
                        "message": alert.message,
                        "delivery_status": alert.delivery_status,
                    }
                    for alert in alerts
                ]
        except Exception as e:
            logger.error(f"Failed to fetch alerts by risk level: {str(e)}")
            # Fallback to in-memory cache
            return [alert for alert in self._alert_cache if alert.get("risk_level") == risk_level]


def get_alert_system(
    sms_enabled: bool = False,
    email_enabled: bool = False,
    slack_enabled: bool = False,
    firebase_push_enabled: bool = False,
    messenger_enabled: bool = False,
    telegram_enabled: bool = False,
    siren_enabled: bool = False,
) -> AlertSystem:
    """
    Get the alert system instance using dependency injection pattern.

    This function provides controlled access to the AlertSystem singleton,
    replacing direct access to global mutable state.

    Args:
        sms_enabled: Enable SMS notifications
        email_enabled: Enable email notifications
        slack_enabled: Enable Slack notifications
        firebase_push_enabled: Enable Firebase push notifications
        messenger_enabled: Enable Messenger chatbot
        telegram_enabled: Enable Telegram bot
        siren_enabled: Enable LGU siren trigger

    Returns:
        AlertSystem: The alert system instance
    """
    return AlertSystem.get_instance(
        sms_enabled=sms_enabled,
        email_enabled=email_enabled,
        slack_enabled=slack_enabled,
        firebase_push_enabled=firebase_push_enabled,
        messenger_enabled=messenger_enabled,
        telegram_enabled=telegram_enabled,
        siren_enabled=siren_enabled,
    )


def send_flood_alert(
    risk_data: Dict[str, Any],
    location: Optional[str] = None,
    recipients: Optional[List[str]] = None,
    alert_type: str = "web",
    smart_decision: Optional["SmartAlertDecision"] = None,
) -> Dict[str, Any]:
    """
    Convenience function to send flood alert.

    Args:
        risk_data: Risk classification data
        location: Location name
        recipients: List of recipients
        alert_type: 'web', 'sms', 'email', or 'all'
        smart_decision: Optional SmartAlertDecision from smart evaluator

    Returns:
        dict: Alert delivery status
    """
    alert_system = get_alert_system()
    return alert_system.send_alert(risk_data, location, recipients, alert_type, smart_decision)
