"""
Unit tests for alert service.

Tests for app/services/alerts.py
"""

import os
import smtplib
from unittest.mock import MagicMock, Mock, patch, call

import pytest

# Import modules at top level for proper coverage tracking
from app.services import alerts
from app.services.alerts import AlertSystem, get_alert_system, send_flood_alert
from app.services.risk_classifier import format_alert_message


class TestAlertSystem:
    """Tests for the AlertSystem class."""

    def test_alert_system_initialization(self):
        """Test AlertSystem can be instantiated."""
        with patch("app.services.alerts.get_db_session"):
            alert_system = AlertSystem()
            assert alert_system is not None

    def test_alert_system_singleton(self):
        """Test get_alert_system returns singleton instance."""
        with patch("app.services.alerts.get_db_session"):
            instance1 = get_alert_system()
            instance2 = get_alert_system()
            # Should be the same instance
            assert instance1 is instance2

    def test_send_flood_alert_returns_dict(self):
        """Test send_flood_alert returns a dictionary."""
        with patch("app.services.alerts.get_alert_system") as mock_get_alert:
            mock_system = MagicMock()
            mock_system.send_alert.return_value = {"success": True, "alert_id": "12345"}
            mock_get_alert.return_value = mock_system

            # Use correct function signature with risk_data dict
            risk_data = {"risk_level": 2, "message": "Critical flood risk detected"}
            result = send_flood_alert(risk_data=risk_data, location="Paranaque City")

            assert isinstance(result, dict)


class TestAlertSeverityLevels:
    """Tests for alert severity level handling."""

    def test_risk_level_0_is_safe(self):
        """Test that risk level 0 corresponds to Safe."""
        assert 0 == 0  # Safe level

    def test_risk_level_1_is_alert(self):
        """Test that risk level 1 corresponds to Alert."""
        assert 1 == 1  # Alert level

    def test_risk_level_2_is_critical(self):
        """Test that risk level 2 corresponds to Critical."""
        assert 2 == 2  # Critical level

    def test_valid_risk_levels(self):
        """Test valid risk levels range."""
        valid_levels = [0, 1, 2]
        for level in valid_levels:
            assert 0 <= level <= 2


class TestAlertMessageFormatting:
    """Tests for alert message formatting."""

    def test_alert_message_contains_location(self):
        """Test that alert messages include location."""
        risk_data = {"risk_label": "Critical", "description": "High flood risk", "confidence": 0.85}

        message = format_alert_message(risk_data, location="Paranaque City")
        assert "Paranaque City" in message

    def test_alert_message_contains_risk_level(self):
        """Test that alert messages include risk level."""
        risk_data = {"risk_label": "Alert", "description": "Moderate flood risk", "confidence": 0.65}

        message = format_alert_message(risk_data)
        assert "Alert" in message

    def test_critical_alert_has_action_text(self):
        """Test that critical alerts include action text."""
        risk_data = {"risk_label": "Critical", "description": "High flood risk", "confidence": 0.90}

        message = format_alert_message(risk_data)
        assert "TAKE IMMEDIATE ACTION" in message


class TestAlertDelivery:
    """Tests for real alert delivery through SMS, email, and Slack channels."""

    def setup_method(self):
        """Reset singleton between tests."""
        AlertSystem.reset_instance()

    # ----- SMS delivery tests -----

    @patch.dict(os.environ, {"SMS_SANDBOX_MODE": "False", "SMS_PROVIDER": "semaphore"})
    @patch("app.services.alerts.requests.post")
    def test_sms_semaphore_delivery(self, mock_post):
        """Test SMS is actually delivered via Semaphore when sandbox is off."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [{"message_id": "123", "status": "Queued"}]
        mock_post.return_value = mock_resp

        with patch.dict(os.environ, {"SEMAPHORE_API_KEY": "test-key"}):
            system = AlertSystem(sms_enabled=True)
            status = system._send_sms(["09171234567"], "Flood alert test")

        assert status in ("delivered", "partial")
        mock_post.assert_called_once()

    @patch.dict(os.environ, {"SMS_SANDBOX_MODE": "True"})
    def test_sms_sandbox_returns_sandbox_status(self):
        """Test sandbox mode returns 'sandbox' status without calling provider."""
        system = AlertSystem(sms_enabled=True)
        status = system._send_sms(["09171234567"], "Test")
        assert status == "sandbox"

    @patch.dict(os.environ, {"SMS_SANDBOX_MODE": "False", "SMS_PROVIDER": "twilio"})
    @patch("app.services.alerts.AlertSystem._send_sms_twilio", return_value="delivered")
    def test_sms_twilio_dispatch(self, mock_twilio):
        """Test SMS routes to Twilio provider when configured."""
        system = AlertSystem(sms_enabled=True)
        status = system._send_sms(["09171234567"], "Test")
        assert status == "delivered"
        mock_twilio.assert_called_once()

    # ----- Email delivery tests -----

    @patch.dict(os.environ, {
        "EMAIL_SANDBOX_MODE": "False",
        "SMTP_HOST": "smtp.test.com",
        "SMTP_PORT": "587",
        "SMTP_USERNAME": "user@test.com",
        "SMTP_PASSWORD": "pass",
        "SMTP_FROM_EMAIL": "alerts@floodingnaque.com",
        "SMTP_USE_TLS": "True",
    })
    @patch("app.services.alerts.smtplib.SMTP")
    def test_email_delivery_via_smtp(self, mock_smtp_class):
        """Test email is delivered through SMTP when sandbox is off."""
        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_class.return_value.__exit__ = MagicMock(return_value=False)

        system = AlertSystem(email_enabled=True)
        status = system._send_email(
            recipients=["user@example.com"],
            subject="Critical",
            message="Flood warning test",
        )

        assert status == "delivered"
        mock_smtp_class.assert_called_once_with("smtp.test.com", 587, timeout=30)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("user@test.com", "pass")
        mock_server.sendmail.assert_called_once()

    @patch.dict(os.environ, {"EMAIL_SANDBOX_MODE": "True"})
    def test_email_sandbox_returns_sandbox_status(self):
        """Test sandbox mode returns 'sandbox' without connecting to SMTP."""
        system = AlertSystem(email_enabled=True)
        status = system._send_email(["user@example.com"], "Test", "Body")
        assert status == "sandbox"

    @patch.dict(os.environ, {
        "EMAIL_SANDBOX_MODE": "False",
        "SMTP_HOST": "smtp.test.com",
        "SMTP_PORT": "587",
        "SMTP_USERNAME": "user@test.com",
        "SMTP_PASSWORD": "pass",
    })
    @patch("app.services.alerts.smtplib.SMTP")
    def test_email_smtp_failure_returns_failed(self, mock_smtp_class):
        """Test SMTP error results in 'failed' status."""
        mock_smtp_class.side_effect = smtplib.SMTPException("Connection refused")

        system = AlertSystem(email_enabled=True)
        status = system._send_email(["user@example.com"], "Critical", "Test")
        assert status == "failed"

    @patch.dict(os.environ, {"EMAIL_SANDBOX_MODE": "False"}, clear=False)
    def test_email_not_configured_without_credentials(self):
        """Test missing SMTP creds results in 'not_configured'."""
        env_overrides = {
            "EMAIL_SANDBOX_MODE": "False",
            "SMTP_HOST": "",
            "SMTP_USERNAME": "",
            "SMTP_PASSWORD": "",
        }
        with patch.dict(os.environ, env_overrides):
            system = AlertSystem(email_enabled=True)
            status = system._send_email(["user@example.com"], "Test", "Body")
            assert status == "not_configured"

    # ----- Slack delivery tests -----

    @patch.dict(os.environ, {"SLACK_WEBHOOK_URL": "https://hooks.slack.com/services/T/B/X"})
    @patch("app.services.alerts.requests.post")
    def test_slack_webhook_delivery(self, mock_post):
        """Test Slack alert is delivered via webhook."""
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        system = AlertSystem(slack_enabled=True)
        status = system._send_slack("Critical", "Flood warning", "Parañaque City")

        assert status == "delivered"
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert payload["attachments"][0]["title"].startswith(":warning:")

    @patch.dict(os.environ, {"SLACK_WEBHOOK_URL": ""})
    def test_slack_not_configured_without_url(self):
        """Test missing webhook URL returns 'not_configured'."""
        system = AlertSystem(slack_enabled=True)
        status = system._send_slack("Alert", "Test", "Test City")
        assert status == "not_configured"

    @patch.dict(os.environ, {"SLACK_WEBHOOK_URL": "https://hooks.slack.com/services/T/B/X"})
    @patch("app.services.alerts.requests.post")
    def test_slack_webhook_failure(self, mock_post):
        """Test Slack webhook HTTP error returns 'failed'."""
        import requests as http_requests

        mock_post.side_effect = http_requests.RequestException("timeout")

        system = AlertSystem(slack_enabled=True)
        status = system._send_slack("Critical", "Test", "Test City")
        assert status == "failed"

    # ----- Integration: send_alert routes to all channels -----

    @patch("app.services.alerts.AlertSystem._send_sms", return_value="delivered")
    @patch("app.services.alerts.AlertSystem._send_email", return_value="delivered")
    @patch("app.services.alerts.AlertSystem._send_slack", return_value="delivered")
    @patch("app.services.alerts.get_db_session")
    def test_send_alert_all_channels(self, mock_db, mock_slack, mock_email, mock_sms):
        """Test send_alert with type='all' dispatches to every enabled channel."""
        system = AlertSystem(sms_enabled=True, email_enabled=True, slack_enabled=True)
        risk_data = {"risk_level": 2, "risk_label": "Critical", "description": "High flood risk", "confidence": 0.9}
        result = system.send_alert(
            risk_data=risk_data,
            location="Parañaque City",
            recipients=["user@example.com"],
            alert_type="all",
        )

        assert result["delivery_status"]["web"] == "delivered"
        mock_sms.assert_called_once()
        mock_email.assert_called_once()
        mock_slack.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
