"""
Email Service Module.

Provides transactional email sending for account-related operations
(password resets, email verification, etc.) using SMTP.
"""

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


def _get_smtp_config() -> dict:
    """Return SMTP connection parameters from environment."""
    return {
        "host": os.getenv("SMTP_HOST"),
        "port": int(os.getenv("SMTP_PORT", "587")),
        "username": os.getenv("SMTP_USERNAME"),
        "password": os.getenv("SMTP_PASSWORD"),
        "from_email": os.getenv("SMTP_FROM_EMAIL", "noreply@floodingnaque.com"),
        "use_tls": os.getenv("SMTP_USE_TLS", "True").lower() == "true",
    }


def _send_email(recipient: str, subject: str, text_body: str, html_body: str) -> bool:
    """
    Send a single transactional email via SMTP.

    Args:
        recipient: Destination email address.
        subject: Email subject line.
        text_body: Plain-text fallback body.
        html_body: HTML body.

    Returns:
        True if the message was accepted by the SMTP server, False otherwise.
    """
    cfg = _get_smtp_config()
    if not all([cfg["host"], cfg["username"], cfg["password"]]):
        logger.error("SMTP credentials not configured - cannot send email")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = cfg["from_email"]
    msg["To"] = recipient
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(cfg["host"], cfg["port"], timeout=30) as server:
            if cfg["use_tls"]:
                server.starttls()
            server.login(cfg["username"], cfg["password"])
            server.sendmail(cfg["from_email"], recipient, msg.as_string())
        logger.info(f"Email sent to {recipient}: {subject}")
        return True
    except smtplib.SMTPException as exc:
        logger.error(f"SMTP error sending to {recipient}: {exc}")
        return False
    except Exception as exc:
        logger.error(f"Unexpected error sending email to {recipient}: {exc}")
        return False


def send_password_reset_email(email: str, token: str) -> bool:
    """
    Send a password-reset email containing a one-time reset link.

    The link points at the frontend ``/reset-password`` route which will
    POST the token back to ``/api/v1/users/password-reset/confirm``.

    Args:
        email: Recipient email address.
        token: Unhashed reset token (included in the link).

    Returns:
        True if the email was sent successfully.
    """
    frontend_url = os.getenv("FRONTEND_URL", "https://floodingnaque.com")
    reset_link = f"{frontend_url}/reset-password?token={token}&email={email}"

    subject = "[Floodingnaque] Password Reset Request"

    text_body = (
        f"You requested a password reset for your Floodingnaque account.\n\n"
        f"Click the link below to reset your password:\n{reset_link}\n\n"
        f"This link expires in 1 hour.\n\n"
        f"If you did not request this, please ignore this email.\n"
    )

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5;">
      <div style="max-width: 600px; margin: 0 auto; background: #fff; border-radius: 8px;
                  overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
        <div style="background-color: #1a73e8; color: white; padding: 20px; text-align: center;">
          <h1 style="margin: 0; font-size: 24px;">Password Reset</h1>
        </div>
        <div style="padding: 20px; line-height: 1.6;">
          <p>You requested a password reset for your <strong>Floodingnaque</strong> account.</p>
          <p style="text-align: center;">
            <a href="{reset_link}"
               style="display: inline-block; padding: 12px 24px; background-color: #1a73e8;
                      color: white; text-decoration: none; border-radius: 4px; font-weight: bold;">
              Reset Password
            </a>
          </p>
          <p>This link expires in <strong>1 hour</strong>.</p>
          <p style="color: #888; font-size: 13px;">
            If you did not request this, you can safely ignore this email.
          </p>
        </div>
        <div style="background-color: #f8f9fa; padding: 15px; text-align: center;
                    font-size: 12px; color: #6c757d;">
          <p style="margin: 0;">Floodingnaque Early Warning System</p>
          <p style="margin: 5px 0 0 0;">Parañaque City, Philippines</p>
        </div>
      </div>
    </body>
    </html>
    """

    return _send_email(email, subject, text_body, html_body)
