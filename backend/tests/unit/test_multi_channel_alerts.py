"""
Unit tests for multi-channel alert notification channels.

Tests for:
    - FirebasePushChannel
    - EmailAlertChannel
    - MessengerBotChannel
    - TelegramBotChannel
    - SirenTriggerChannel
    - AlertSystem multi-channel integration
"""

import os
from unittest.mock import MagicMock, Mock, patch

import pytest
from app.services.channels.base import NotificationChannel
from app.services.channels.email_alerts import EmailAlertChannel
from app.services.channels.firebase_push import FirebasePushChannel
from app.services.channels.messenger_bot import MessengerBotChannel
from app.services.channels.siren_trigger import SirenTriggerChannel
from app.services.channels.telegram_bot import TelegramBotChannel

# ---------------------------------------------------------------------------
# Common fixtures
# ---------------------------------------------------------------------------

SAMPLE_ALERT = {
    "message": "Heavy rainfall detected. Flood probability 82%. Evacuate low-lying areas.",
    "risk_label": "Critical",
    "location": "Parañaque City",
}


# ===========================================================================
# Base Channel
# ===========================================================================


class TestNotificationChannelBase:
    """Tests for the abstract NotificationChannel base class."""

    def test_sandbox_mode_returns_sandbox(self):
        """Sandbox dispatch should return 'sandbox' without calling send()."""

        class _Stub(NotificationChannel):
            channel_id = "stub"
            display_name = "Stub"

            def send(self, **kwargs):
                raise AssertionError("send() should not be called in sandbox")

            def is_configured(self):
                return True

        ch = _Stub(sandbox=True)
        result = ch.dispatch(**SAMPLE_ALERT)
        assert result == "sandbox"

    def test_not_configured_returns_not_configured(self):
        class _Stub(NotificationChannel):
            channel_id = "stub"
            display_name = "Stub"

            def send(self, **kwargs):
                raise AssertionError("send() should not be called")

            def is_configured(self):
                return False

        ch = _Stub(sandbox=False)
        result = ch.dispatch(**SAMPLE_ALERT)
        assert result == "not_configured"

    def test_send_exception_returns_failed(self):
        class _Stub(NotificationChannel):
            channel_id = "stub"
            display_name = "Stub"

            def send(self, **kwargs):
                raise RuntimeError("boom")

            def is_configured(self):
                return True

        ch = _Stub(sandbox=False)
        result = ch.dispatch(**SAMPLE_ALERT)
        assert result == "failed"

    def test_get_info(self):
        class _Stub(NotificationChannel):
            channel_id = "stub"
            display_name = "Stub"

            def send(self, **kwargs):
                pass

            def is_configured(self):
                return True

        ch = _Stub(sandbox=True)
        info = ch.get_info()
        assert info["id"] == "stub"
        assert info["name"] == "Stub"
        assert info["configured"] is True
        assert info["sandbox"] is True


# ===========================================================================
# Firebase Push
# ===========================================================================


class TestFirebasePushChannel:
    """Tests for FirebasePushChannel."""

    def test_not_configured_without_env(self, monkeypatch):
        monkeypatch.delenv("FIREBASE_PROJECT_ID", raising=False)
        monkeypatch.delenv("FIREBASE_SERVICE_ACCOUNT_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
        ch = FirebasePushChannel()
        assert ch.is_configured() is False

    def test_configured_with_env(self, monkeypatch):
        monkeypatch.setenv("FIREBASE_PROJECT_ID", "test-project")
        monkeypatch.setenv("FIREBASE_SERVICE_ACCOUNT_KEY", "/path/to/key.json")
        ch = FirebasePushChannel()
        assert ch.is_configured() is True

    def test_sandbox_returns_sandbox(self, monkeypatch):
        monkeypatch.setenv("FIREBASE_PROJECT_ID", "test-project")
        monkeypatch.setenv("FIREBASE_SERVICE_ACCOUNT_KEY", "/path/to/key.json")
        monkeypatch.setenv("FIREBASE_PUSH_SANDBOX_MODE", "True")
        ch = FirebasePushChannel()
        result = ch.dispatch(**SAMPLE_ALERT)
        assert result == "sandbox"

    @patch("app.services.channels.firebase_push.requests.post")
    def test_send_to_topic(self, mock_post, monkeypatch):
        monkeypatch.setenv("FIREBASE_PROJECT_ID", "test-project")
        ch = FirebasePushChannel(sandbox=False)
        ch._access_token = "fake-token"
        ch._token_expiry = 9999999999

        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"name": "projects/test/messages/123"}
        mock_post.return_value = mock_resp

        result = ch.send(**SAMPLE_ALERT)
        assert result == "delivered"
        mock_post.assert_called_once()

    @patch("app.services.channels.firebase_push.requests.post")
    def test_send_to_device_tokens(self, mock_post, monkeypatch):
        monkeypatch.setenv("FIREBASE_PROJECT_ID", "test-project")
        ch = FirebasePushChannel(sandbox=False)
        ch._access_token = "fake-token"
        ch._token_expiry = 9999999999

        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"name": "ok"}
        mock_post.return_value = mock_resp

        result = ch.send(
            **SAMPLE_ALERT,
            recipients=["device_token_1", "device_token_2"],
        )
        assert result == "delivered"
        assert mock_post.call_count == 2

    @patch("app.services.channels.firebase_push.requests.post")
    def test_send_failure(self, mock_post, monkeypatch):
        monkeypatch.setenv("FIREBASE_PROJECT_ID", "test-project")
        ch = FirebasePushChannel(sandbox=False)
        ch._access_token = "fake-token"
        ch._token_expiry = 9999999999

        mock_resp = Mock()
        mock_resp.status_code = 401
        mock_resp.text = "Unauthorized"
        mock_post.return_value = mock_resp

        result = ch.send(**SAMPLE_ALERT)
        assert result == "failed"

    def test_severity_config(self):
        ch = FirebasePushChannel()
        assert "Safe" in ch._SEVERITY_CONFIG
        assert "Alert" in ch._SEVERITY_CONFIG
        assert "Critical" in ch._SEVERITY_CONFIG
        assert ch._SEVERITY_CONFIG["Critical"]["priority"] == "high"


# ===========================================================================
# Email Alert
# ===========================================================================


class TestEmailAlertChannel:
    """Tests for EmailAlertChannel."""

    def test_not_configured_without_env(self, monkeypatch):
        monkeypatch.delenv("SMTP_HOST", raising=False)
        monkeypatch.delenv("SMTP_USERNAME", raising=False)
        monkeypatch.delenv("SMTP_PASSWORD", raising=False)
        ch = EmailAlertChannel()
        assert ch.is_configured() is False

    def test_configured_with_env(self, monkeypatch):
        monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
        monkeypatch.setenv("SMTP_USERNAME", "user")
        monkeypatch.setenv("SMTP_PASSWORD", "pass")
        ch = EmailAlertChannel()
        assert ch.is_configured() is True

    def test_send_no_recipients_returns_failed(self, monkeypatch):
        monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
        monkeypatch.setenv("SMTP_USERNAME", "user")
        monkeypatch.setenv("SMTP_PASSWORD", "pass")
        ch = EmailAlertChannel(sandbox=False)
        result = ch.send(**SAMPLE_ALERT, recipients=None)
        assert result == "failed"

    @patch("app.services.channels.email_alerts.smtplib.SMTP")
    def test_send_success(self, mock_smtp_cls, monkeypatch):
        monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
        monkeypatch.setenv("SMTP_USERNAME", "user")
        monkeypatch.setenv("SMTP_PASSWORD", "pass")

        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = Mock(return_value=mock_server)
        mock_smtp_cls.return_value.__exit__ = Mock(return_value=False)

        ch = EmailAlertChannel(sandbox=False)
        result = ch.send(**SAMPLE_ALERT, recipients=["test@example.com"])
        assert result == "delivered"

    def test_html_template(self):
        ch = EmailAlertChannel()
        html = ch._build_html("Critical", "Parañaque City", "Flood warning!")
        assert "Critical" in html
        assert "#dc3545" in html
        assert "Parañaque City" in html


# ===========================================================================
# Messenger Bot
# ===========================================================================


class TestMessengerBotChannel:
    """Tests for MessengerBotChannel."""

    def test_not_configured_without_env(self, monkeypatch):
        monkeypatch.delenv("MESSENGER_PAGE_ACCESS_TOKEN", raising=False)
        ch = MessengerBotChannel()
        assert ch.is_configured() is False

    def test_configured_with_env(self, monkeypatch):
        monkeypatch.setenv("MESSENGER_PAGE_ACCESS_TOKEN", "test-token")
        ch = MessengerBotChannel()
        assert ch.is_configured() is True

    def test_send_no_psids_returns_failed(self, monkeypatch):
        monkeypatch.setenv("MESSENGER_PAGE_ACCESS_TOKEN", "test-token")
        ch = MessengerBotChannel(sandbox=False)
        result = ch.send(**SAMPLE_ALERT, recipients=None)
        assert result == "failed"

    @patch("app.services.channels.messenger_bot.requests.post")
    def test_send_success(self, mock_post, monkeypatch):
        monkeypatch.setenv("MESSENGER_PAGE_ACCESS_TOKEN", "test-token")
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        ch = MessengerBotChannel(sandbox=False)
        result = ch.send(**SAMPLE_ALERT, recipients=["psid_123", "psid_456"])
        assert result == "delivered"
        assert mock_post.call_count == 2

    @patch("app.services.channels.messenger_bot.requests.post")
    def test_send_partial(self, mock_post, monkeypatch):
        monkeypatch.setenv("MESSENGER_PAGE_ACCESS_TOKEN", "test-token")

        ok = Mock()
        ok.status_code = 200
        fail = Mock()
        fail.status_code = 400
        fail.text = "Error"
        mock_post.side_effect = [ok, fail]

        ch = MessengerBotChannel(sandbox=False)
        result = ch.send(**SAMPLE_ALERT, recipients=["psid_1", "psid_2"])
        assert result == "partial"

    def test_generic_template_structure(self, monkeypatch):
        monkeypatch.setenv("MESSENGER_PAGE_ACCESS_TOKEN", "test-token")
        ch = MessengerBotChannel()
        tmpl = ch._build_generic_template("Alert", "Parañaque City", "Flood warning!")
        assert tmpl["attachment"]["type"] == "template"
        elements = tmpl["attachment"]["payload"]["elements"]
        assert len(elements) == 1
        assert "buttons" in elements[0]

    def test_webhook_verification_success(self, monkeypatch):
        monkeypatch.setenv("MESSENGER_VERIFY_TOKEN", "my-secret")
        result = MessengerBotChannel.verify_webhook("subscribe", "my-secret", "challenge_123")
        assert result == "challenge_123"

    def test_webhook_verification_failure(self, monkeypatch):
        monkeypatch.setenv("MESSENGER_VERIFY_TOKEN", "my-secret")
        result = MessengerBotChannel.verify_webhook("subscribe", "wrong", "challenge_123")
        assert result is None


# ===========================================================================
# Telegram Bot
# ===========================================================================


class TestTelegramBotChannel:
    """Tests for TelegramBotChannel."""

    def test_not_configured_without_env(self, monkeypatch):
        monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
        ch = TelegramBotChannel()
        assert ch.is_configured() is False

    def test_configured_with_env(self, monkeypatch):
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:FAKE")
        ch = TelegramBotChannel()
        assert ch.is_configured() is True

    def test_send_no_chat_id_no_default_returns_failed(self, monkeypatch):
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:FAKE")
        monkeypatch.delenv("TELEGRAM_DEFAULT_CHAT_ID", raising=False)
        ch = TelegramBotChannel(sandbox=False)
        result = ch.send(**SAMPLE_ALERT, recipients=None)
        assert result == "failed"

    @patch("app.services.channels.telegram_bot.requests.post")
    def test_send_success(self, mock_post, monkeypatch):
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:FAKE")
        mock_resp = Mock()
        mock_resp.json.return_value = {"ok": True, "result": {"message_id": 42}}
        mock_post.return_value = mock_resp

        ch = TelegramBotChannel(sandbox=False)
        result = ch.send(**SAMPLE_ALERT, recipients=["-100123456"])
        assert result == "delivered"

    @patch("app.services.channels.telegram_bot.requests.post")
    def test_send_uses_default_chat_id(self, mock_post, monkeypatch):
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:FAKE")
        monkeypatch.setenv("TELEGRAM_DEFAULT_CHAT_ID", "-100999")
        mock_resp = Mock()
        mock_resp.json.return_value = {"ok": True, "result": {"message_id": 1}}
        mock_post.return_value = mock_resp

        ch = TelegramBotChannel(sandbox=False)
        result = ch.send(**SAMPLE_ALERT)
        assert result == "delivered"
        call_kwargs = mock_post.call_args[1]["json"]
        assert call_kwargs["chat_id"] == "-100999"

    def test_html_formatting(self, monkeypatch):
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:FAKE")
        ch = TelegramBotChannel()
        html = ch._format_html("Critical", "Parañaque City", "Flood alert!")
        assert "<b>Flood Critical</b>" in html
        assert "Parañaque City" in html

    def test_handle_start_command(self, monkeypatch):
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:FAKE")
        ch = TelegramBotChannel()
        update = {"message": {"text": "/start", "chat": {"id": 123}}}
        reply = ch.handle_update(update)
        assert reply is not None
        assert "Welcome" in reply

    def test_handle_stop_command(self, monkeypatch):
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:FAKE")
        ch = TelegramBotChannel()
        update = {"message": {"text": "/stop", "chat": {"id": 123}}}
        reply = ch.handle_update(update)
        assert "unsubscribed" in reply

    def test_handle_unknown_command(self, monkeypatch):
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:FAKE")
        ch = TelegramBotChannel()
        update = {"message": {"text": "hello", "chat": {"id": 123}}}
        reply = ch.handle_update(update)
        assert reply is None


# ===========================================================================
# Siren Trigger
# ===========================================================================


class TestSirenTriggerChannel:
    """Tests for SirenTriggerChannel."""

    def test_not_configured_without_env(self, monkeypatch):
        monkeypatch.delenv("SIREN_API_URL", raising=False)
        monkeypatch.delenv("SIREN_API_KEY", raising=False)
        ch = SirenTriggerChannel()
        assert ch.is_configured() is False

    def test_configured_with_env(self, monkeypatch):
        monkeypatch.setenv("SIREN_API_URL", "https://siren.lgu.ph")
        monkeypatch.setenv("SIREN_API_KEY", "key123")
        ch = SirenTriggerChannel()
        assert ch.is_configured() is True

    def test_critical_only_skips_non_critical(self, monkeypatch):
        monkeypatch.setenv("SIREN_API_URL", "https://siren.lgu.ph")
        monkeypatch.setenv("SIREN_API_KEY", "key123")
        monkeypatch.setenv("SIREN_CRITICAL_ONLY", "True")
        ch = SirenTriggerChannel(sandbox=False)
        result = ch.send(
            message="Test",
            risk_label="Alert",
            location="Parañaque City",
        )
        assert result == "skipped"

    @patch("app.services.channels.siren_trigger.requests.post")
    def test_send_critical_success(self, mock_post, monkeypatch):
        monkeypatch.setenv("SIREN_API_URL", "https://siren.lgu.ph")
        monkeypatch.setenv("SIREN_API_KEY", "key123")
        monkeypatch.setenv("SIREN_ZONES", "zone_a,zone_b")

        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"zones_activated": ["zone_a", "zone_b"]}
        mock_post.return_value = mock_resp

        ch = SirenTriggerChannel(sandbox=False)
        result = ch.send(**SAMPLE_ALERT)
        assert result == "delivered"

    @patch("app.services.channels.siren_trigger.requests.post")
    def test_send_api_error(self, mock_post, monkeypatch):
        monkeypatch.setenv("SIREN_API_URL", "https://siren.lgu.ph")
        monkeypatch.setenv("SIREN_API_KEY", "key123")
        monkeypatch.setenv("SIREN_ZONES", "zone_a")

        mock_resp = Mock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        mock_post.return_value = mock_resp

        ch = SirenTriggerChannel(sandbox=False)
        result = ch.send(**SAMPLE_ALERT)
        assert result == "failed"

    @patch("app.services.channels.siren_trigger.requests.post")
    def test_offline_fallback_logging(self, mock_post, monkeypatch):
        import requests as req

        monkeypatch.setenv("SIREN_API_URL", "https://siren.lgu.ph")
        monkeypatch.setenv("SIREN_API_KEY", "key123")
        monkeypatch.setenv("SIREN_ZONES", "zone_a")
        mock_post.side_effect = req.ConnectionError("unreachable")

        ch = SirenTriggerChannel(sandbox=False)
        result = ch.send(**SAMPLE_ALERT)
        assert result == "failed"

    def test_siren_patterns(self):
        ch = SirenTriggerChannel()
        assert "Safe" in ch._SIREN_PATTERNS
        assert "Alert" in ch._SIREN_PATTERNS
        assert "Critical" in ch._SIREN_PATTERNS
        assert ch._SIREN_PATTERNS["Critical"]["pattern"] == "fast_pulse"

    def test_get_info_includes_siren_details(self, monkeypatch):
        monkeypatch.setenv("SIREN_API_URL", "https://siren.lgu.ph")
        monkeypatch.setenv("SIREN_API_KEY", "key123")
        monkeypatch.setenv("SIREN_ZONES", "zone_a,zone_b")
        ch = SirenTriggerChannel()
        info = ch.get_info()
        assert info["id"] == "siren"
        assert info["critical_only"] is True
        assert "zone_a" in info["default_zones"]
        assert "siren_patterns" in info


# ===========================================================================
# AlertSystem multi-channel integration
# ===========================================================================


class TestAlertSystemMultiChannel:
    """Test that AlertSystem dispatches to new channels."""

    def setup_method(self):
        from app.services.alerts import AlertSystem

        AlertSystem.reset_instance()

    def teardown_method(self):
        from app.services.alerts import AlertSystem

        AlertSystem.reset_instance()

    @patch("app.services.alerts.get_db_session")
    def test_supported_channels_list(self, _mock_db):
        from app.services.alerts import AlertSystem

        assert "firebase_push" in AlertSystem.SUPPORTED_CHANNELS
        assert "messenger" in AlertSystem.SUPPORTED_CHANNELS
        assert "telegram" in AlertSystem.SUPPORTED_CHANNELS
        assert "siren" in AlertSystem.SUPPORTED_CHANNELS

    @patch("app.services.alerts.get_db_session")
    def test_channels_instantiated(self, _mock_db):
        from app.services.alerts import AlertSystem

        system = AlertSystem(firebase_push_enabled=True, telegram_enabled=True)
        assert system._firebase_channel is not None
        assert system._telegram_channel is not None
        assert system._messenger_channel is not None
        assert system._siren_channel is not None
        assert system._email_channel is not None

    @patch("app.services.alerts.get_db_session")
    def test_send_alert_firebase(self, _mock_db):
        from app.services.alerts import AlertSystem

        system = AlertSystem(firebase_push_enabled=True)
        system._firebase_channel = MagicMock()
        system._firebase_channel.dispatch.return_value = "delivered"

        risk_data = {"risk_level": 1, "risk_label": "Alert", "description": "Elevated flood risk", "confidence": 0.7}
        result = system.send_alert(risk_data, alert_type="firebase_push")

        system._firebase_channel.dispatch.assert_called_once()
        assert result["delivery_status"]["firebase_push"] == "delivered"

    @patch("app.services.alerts.get_db_session")
    def test_send_alert_telegram(self, _mock_db):
        from app.services.alerts import AlertSystem

        system = AlertSystem(telegram_enabled=True)
        system._telegram_channel = MagicMock()
        system._telegram_channel.dispatch.return_value = "delivered"

        risk_data = {"risk_level": 1, "risk_label": "Alert", "description": "Elevated flood risk", "confidence": 0.7}
        result = system.send_alert(risk_data, alert_type="telegram")

        system._telegram_channel.dispatch.assert_called_once()
        assert result["delivery_status"]["telegram"] == "delivered"

    @patch("app.services.alerts.get_db_session")
    def test_send_alert_messenger(self, _mock_db):
        from app.services.alerts import AlertSystem

        system = AlertSystem(messenger_enabled=True)
        system._messenger_channel = MagicMock()
        system._messenger_channel.dispatch.return_value = "delivered"

        risk_data = {"risk_level": 1, "risk_label": "Alert", "description": "Elevated flood risk", "confidence": 0.7}
        result = system.send_alert(risk_data, alert_type="messenger")

        system._messenger_channel.dispatch.assert_called_once()
        assert result["delivery_status"]["messenger"] == "delivered"

    @patch("app.services.alerts.get_db_session")
    def test_send_alert_siren(self, _mock_db):
        from app.services.alerts import AlertSystem

        system = AlertSystem(siren_enabled=True)
        system._siren_channel = MagicMock()
        system._siren_channel.dispatch.return_value = "delivered"

        risk_data = {"risk_level": 2, "risk_label": "Critical", "description": "Severe flood risk", "confidence": 0.95}
        result = system.send_alert(risk_data, alert_type="siren")

        system._siren_channel.dispatch.assert_called_once()
        assert result["delivery_status"]["siren"] == "delivered"

    @patch("app.services.alerts.get_db_session")
    def test_all_channels_dispatched(self, _mock_db):
        from app.services.alerts import AlertSystem

        system = AlertSystem(
            sms_enabled=False,
            email_enabled=False,
            slack_enabled=False,
            firebase_push_enabled=True,
            messenger_enabled=True,
            telegram_enabled=True,
            siren_enabled=True,
        )
        system._firebase_channel = MagicMock()
        system._firebase_channel.dispatch.return_value = "delivered"
        system._messenger_channel = MagicMock()
        system._messenger_channel.dispatch.return_value = "delivered"
        system._telegram_channel = MagicMock()
        system._telegram_channel.dispatch.return_value = "delivered"
        system._siren_channel = MagicMock()
        system._siren_channel.dispatch.return_value = "delivered"

        risk_data = {"risk_level": 1, "risk_label": "Alert", "description": "Elevated flood risk", "confidence": 0.7}
        result = system.send_alert(risk_data, alert_type="all")

        assert "firebase_push" in result["delivery_status"]
        assert "messenger" in result["delivery_status"]
        assert "telegram" in result["delivery_status"]
        assert "siren" in result["delivery_status"]

    @patch("app.services.alerts.get_db_session")
    def test_critical_auto_trigger(self, _mock_db):
        """Critical risk should auto-trigger firebase, telegram, siren even if alert_type is 'web'."""
        from app.services.alerts import AlertSystem

        system = AlertSystem(
            firebase_push_enabled=True,
            telegram_enabled=True,
            siren_enabled=True,
        )
        system._firebase_channel = MagicMock()
        system._firebase_channel.dispatch.return_value = "delivered"
        system._telegram_channel = MagicMock()
        system._telegram_channel.dispatch.return_value = "delivered"
        system._siren_channel = MagicMock()
        system._siren_channel.dispatch.return_value = "delivered"

        risk_data = {"risk_level": 2, "risk_label": "Critical", "description": "Severe flood risk", "confidence": 0.95}
        result = system.send_alert(risk_data, alert_type="web")

        assert "firebase_push_critical_auto" in result["delivery_status"]
        assert "telegram_critical_auto" in result["delivery_status"]
        assert "siren_critical_auto" in result["delivery_status"]
