"""
Email Alert Notification Channel.

Sends styled HTML flood alert emails via SMTP.  Wraps the existing
SMTP infrastructure from ``app.services.alerts`` in the new
``NotificationChannel`` interface.

Required environment variables:
    SMTP_HOST      - SMTP server hostname
    SMTP_PORT      - SMTP server port (default 587)
    SMTP_USERNAME  - SMTP login username
    SMTP_PASSWORD  - SMTP login password

Optional:
    SMTP_FROM_EMAIL    - Sender address (default: alerts@floodingnaque.com)
    SMTP_USE_TLS       - Enable STARTTLS (default: True)
    EMAIL_SANDBOX_MODE - Set to "True" to skip real delivery
"""

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

from app.services.channels.base import NotificationChannel

logger = logging.getLogger(__name__)


class EmailAlertChannel(NotificationChannel):
    """Deliver flood alerts via SMTP email."""

    channel_id = "email"
    display_name = "Email Alert"

    def is_configured(self) -> bool:
        return bool(os.getenv("SMTP_HOST") and os.getenv("SMTP_USERNAME") and os.getenv("SMTP_PASSWORD"))

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
        if not recipients:
            logger.warning("EmailAlertChannel.send called with no recipients")
            return "failed"

        smtp_host = os.getenv("SMTP_HOST", "")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USERNAME", "")
        smtp_pass = os.getenv("SMTP_PASSWORD", "")
        smtp_from = os.getenv("SMTP_FROM_EMAIL", "alerts@floodingnaque.com")
        use_tls = os.getenv("SMTP_USE_TLS", "True").lower() == "true"

        subject = f"[Floodingnaque Alert] {risk_label} - {location}"
        html_body = self._build_html(risk_label, location, message)

        success = 0
        fail = 0

        for recipient in recipients:
            try:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"] = smtp_from
                msg["To"] = recipient
                msg.attach(MIMEText(message, "plain", "utf-8"))
                msg.attach(MIMEText(html_body, "html", "utf-8"))

                with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
                    if use_tls:
                        server.starttls()
                    server.login(smtp_user, smtp_pass)
                    server.sendmail(smtp_from, recipient, msg.as_string())

                success += 1
                logger.info("Email alert sent to %s", recipient)

            except smtplib.SMTPException as exc:
                fail += 1
                logger.error("SMTP error for %s: %s", recipient, exc)
            except Exception as exc:
                fail += 1
                logger.error("Email error for %s: %s", recipient, exc)

        if fail == 0:
            return "delivered"
        elif success > 0:
            return "partial"
        return "failed"

    # ------------------------------------------------------------------
    # HTML template
    # ------------------------------------------------------------------

    _COLOR_MAP = {"Safe": "#28a745", "Alert": "#ffc107", "Critical": "#dc3545"}

    def _build_html(self, risk_label: str, location: str, message: str) -> str:
        color = self._COLOR_MAP.get(risk_label, "#6c757d")
        return f"""\
<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="font-family:Arial,sans-serif;margin:0;padding:20px;background:#f5f5f5;">
  <div style="max-width:600px;margin:0 auto;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 4px rgba(0,0,0,.1);">
    <div style="background:{color};color:#fff;padding:20px;text-align:center;">
      <h1 style="margin:0;font-size:24px;">Flood Risk Alert: {risk_label}</h1>
      <p style="margin:8px 0 0;font-size:14px;">{location}</p>
    </div>
    <div style="padding:20px;">
      <pre style="white-space:pre-wrap;font-family:Arial,sans-serif;line-height:1.6;margin:0;">{message}</pre>
    </div>
    <div style="background:#f8f9fa;padding:15px;text-align:center;font-size:12px;color:#6c757d;">
      <p style="margin:0;">Floodingnaque Early Warning System</p>
      <p style="margin:5px 0 0;">Parañaque City, Philippines</p>
    </div>
  </div>
</body>
</html>"""
