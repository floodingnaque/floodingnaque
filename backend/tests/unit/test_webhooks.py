"""
Unit tests for webhooks routes.

Tests webhook management functionality for flood alerts.
"""

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock, patch

import pytest


class TestRegisterWebhook:
    """Tests for webhook registration endpoint."""

    @pytest.fixture
    def valid_webhook_data(self):
        """Create valid webhook registration data."""
        return {"url": "https://example.com/webhook", "events": ["flood_detected", "critical_risk"]}

    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session."""
        with patch("app.api.routes.webhooks.get_db_session") as mock:
            session = MagicMock()
            mock.return_value.__enter__ = Mock(return_value=session)
            mock.return_value.__exit__ = Mock(return_value=False)
            yield session

    def test_register_webhook_success(self, client, valid_webhook_data, mock_db_session):
        """Test successful webhook registration."""
        mock_webhook = MagicMock()
        mock_webhook.id = 1
        mock_db_session.add = Mock()
        mock_db_session.commit = Mock()

        with patch("app.api.routes.webhooks.require_api_key", lambda f: f):
            with patch("app.api.routes.webhooks.limiter.limit", lambda x: lambda f: f):
                with patch("app.api.routes.webhooks.Webhook") as MockWebhook:
                    MockWebhook.return_value = mock_webhook

                    response = client.post(
                        "/api/v1/webhooks/register",
                        data=json.dumps(valid_webhook_data),
                        content_type="application/json",
                    )

        assert response.status_code == 201
        data = response.get_json()
        assert "webhook_id" in data
        assert data["url"] == valid_webhook_data["url"]
        assert data["events"] == valid_webhook_data["events"]

    def test_register_webhook_missing_url(self, client):
        """Test webhook registration with missing URL."""
        with patch("app.api.routes.webhooks.require_api_key", lambda f: f):
            with patch("app.api.routes.webhooks.limiter.limit", lambda x: lambda f: f):
                response = client.post(
                    "/api/v1/webhooks/register",
                    data=json.dumps({"events": ["flood_detected"]}),
                    content_type="application/json",
                )

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_register_webhook_missing_events(self, client):
        """Test webhook registration with missing events."""
        with patch("app.api.routes.webhooks.require_api_key", lambda f: f):
            with patch("app.api.routes.webhooks.limiter.limit", lambda x: lambda f: f):
                response = client.post(
                    "/api/v1/webhooks/register",
                    data=json.dumps({"url": "https://example.com/webhook"}),
                    content_type="application/json",
                )

        assert response.status_code == 400

    def test_register_webhook_invalid_url(self, client):
        """Test webhook registration with invalid URL format."""
        with patch("app.api.routes.webhooks.require_api_key", lambda f: f):
            with patch("app.api.routes.webhooks.limiter.limit", lambda x: lambda f: f):
                response = client.post(
                    "/api/v1/webhooks/register",
                    data=json.dumps({"url": "invalid-url", "events": ["flood_detected"]}),
                    content_type="application/json",
                )

        assert response.status_code == 400
        data = response.get_json()
        assert "Invalid URL" in data["error"]

    def test_register_webhook_invalid_event(self, client):
        """Test webhook registration with invalid event type."""
        with patch("app.api.routes.webhooks.require_api_key", lambda f: f):
            with patch("app.api.routes.webhooks.limiter.limit", lambda x: lambda f: f):
                response = client.post(
                    "/api/v1/webhooks/register",
                    data=json.dumps({"url": "https://example.com/webhook", "events": ["invalid_event"]}),
                    content_type="application/json",
                )

        assert response.status_code == 400
        data = response.get_json()
        assert "Invalid event" in data["error"]

    def test_register_webhook_empty_events(self, client):
        """Test webhook registration with empty events list."""
        with patch("app.api.routes.webhooks.require_api_key", lambda f: f):
            with patch("app.api.routes.webhooks.limiter.limit", lambda x: lambda f: f):
                response = client.post(
                    "/api/v1/webhooks/register",
                    data=json.dumps({"url": "https://example.com/webhook", "events": []}),
                    content_type="application/json",
                )

        assert response.status_code == 400

    def test_register_webhook_with_custom_secret(self, client, mock_db_session):
        """Test webhook registration with custom secret."""
        mock_webhook = MagicMock()
        mock_webhook.id = 1

        with patch("app.api.routes.webhooks.require_api_key", lambda f: f):
            with patch("app.api.routes.webhooks.limiter.limit", lambda x: lambda f: f):
                with patch("app.api.routes.webhooks.Webhook") as MockWebhook:
                    MockWebhook.return_value = mock_webhook

                    response = client.post(
                        "/api/v1/webhooks/register",
                        data=json.dumps(
                            {
                                "url": "https://example.com/webhook",
                                "events": ["flood_detected"],
                                "secret": "my_custom_secret",
                            }
                        ),
                        content_type="application/json",
                    )

        assert response.status_code == 201
        data = response.get_json()
        assert data["secret"] == "my_custom_secret"


class TestListWebhooks:
    """Tests for listing webhooks endpoint."""

    @pytest.fixture
    def mock_webhooks(self):
        """Create mock webhook list."""
        webhooks = []
        for i in range(3):
            webhook = MagicMock()
            webhook.id = i + 1
            webhook.url = f"https://example{i}.com/webhook"
            webhook.events = '["flood_detected"]'
            webhook.is_active = True
            webhook.failure_count = 0
            webhook.last_triggered_at = datetime.now(timezone.utc)
            webhook.created_at = datetime.now(timezone.utc)
            webhooks.append(webhook)
        return webhooks

    def test_list_webhooks_success(self, client, mock_webhooks):
        """Test successful webhook listing."""
        with patch("app.api.routes.webhooks.require_api_key", lambda f: f):
            with patch("app.api.routes.webhooks.limiter.limit", lambda x: lambda f: f):
                with patch("app.api.routes.webhooks.get_db_session") as mock_session:
                    session = MagicMock()
                    mock_session.return_value.__enter__ = Mock(return_value=session)
                    mock_session.return_value.__exit__ = Mock(return_value=False)

                    mock_query = MagicMock()
                    mock_query.filter_by.return_value = mock_query
                    mock_query.all.return_value = mock_webhooks
                    session.query.return_value = mock_query

                    response = client.get("/api/v1/webhooks/list")

        assert response.status_code == 200
        data = response.get_json()
        assert "webhooks" in data
        assert "count" in data
        assert data["count"] == 3

    def test_list_webhooks_empty(self, client):
        """Test listing webhooks when none exist."""
        with patch("app.api.routes.webhooks.require_api_key", lambda f: f):
            with patch("app.api.routes.webhooks.limiter.limit", lambda x: lambda f: f):
                with patch("app.api.routes.webhooks.get_db_session") as mock_session:
                    session = MagicMock()
                    mock_session.return_value.__enter__ = Mock(return_value=session)
                    mock_session.return_value.__exit__ = Mock(return_value=False)

                    mock_query = MagicMock()
                    mock_query.filter_by.return_value = mock_query
                    mock_query.all.return_value = []
                    session.query.return_value = mock_query

                    response = client.get("/api/v1/webhooks/list")

        assert response.status_code == 200
        data = response.get_json()
        assert data["count"] == 0


class TestUpdateWebhook:
    """Tests for updating webhook endpoint."""

    @pytest.fixture
    def mock_webhook(self):
        """Create mock webhook."""
        webhook = MagicMock()
        webhook.id = 1
        webhook.url = "https://example.com/webhook"
        webhook.events = '["flood_detected"]'
        webhook.is_active = True
        webhook.updated_at = datetime.now(timezone.utc)
        return webhook

    def test_update_webhook_success(self, client, mock_webhook):
        """Test successful webhook update."""
        with patch("app.api.routes.webhooks.require_api_key", lambda f: f):
            with patch("app.api.routes.webhooks.limiter.limit", lambda x: lambda f: f):
                with patch("app.api.routes.webhooks.get_db_session") as mock_session:
                    session = MagicMock()
                    mock_session.return_value.__enter__ = Mock(return_value=session)
                    mock_session.return_value.__exit__ = Mock(return_value=False)

                    mock_query = MagicMock()
                    mock_query.filter_by.return_value = mock_query
                    mock_query.first.return_value = mock_webhook
                    session.query.return_value = mock_query

                    response = client.put(
                        "/api/v1/webhooks/1",
                        data=json.dumps({"url": "https://new-url.com/webhook"}),
                        content_type="application/json",
                    )

        assert response.status_code == 200
        data = response.get_json()
        assert "message" in data
        assert "updated successfully" in data["message"]

    def test_update_webhook_not_found(self, client):
        """Test updating non-existent webhook."""
        with patch("app.api.routes.webhooks.require_api_key", lambda f: f):
            with patch("app.api.routes.webhooks.limiter.limit", lambda x: lambda f: f):
                with patch("app.api.routes.webhooks.get_db_session") as mock_session:
                    session = MagicMock()
                    mock_session.return_value.__enter__ = Mock(return_value=session)
                    mock_session.return_value.__exit__ = Mock(return_value=False)

                    mock_query = MagicMock()
                    mock_query.filter_by.return_value = mock_query
                    mock_query.first.return_value = None
                    session.query.return_value = mock_query

                    response = client.put(
                        "/api/v1/webhooks/999",
                        data=json.dumps({"url": "https://new-url.com/webhook"}),
                        content_type="application/json",
                    )

        assert response.status_code == 404

    def test_update_webhook_invalid_url(self, client, mock_webhook):
        """Test updating webhook with invalid URL."""
        with patch("app.api.routes.webhooks.require_api_key", lambda f: f):
            with patch("app.api.routes.webhooks.limiter.limit", lambda x: lambda f: f):
                with patch("app.api.routes.webhooks.get_db_session") as mock_session:
                    session = MagicMock()
                    mock_session.return_value.__enter__ = Mock(return_value=session)
                    mock_session.return_value.__exit__ = Mock(return_value=False)

                    mock_query = MagicMock()
                    mock_query.filter_by.return_value = mock_query
                    mock_query.first.return_value = mock_webhook
                    session.query.return_value = mock_query

                    response = client.put(
                        "/api/v1/webhooks/1", data=json.dumps({"url": "invalid-url"}), content_type="application/json"
                    )

        assert response.status_code == 400

    def test_update_webhook_no_data(self, client):
        """Test updating webhook with no data."""
        with patch("app.api.routes.webhooks.require_api_key", lambda f: f):
            with patch("app.api.routes.webhooks.limiter.limit", lambda x: lambda f: f):
                response = client.put("/api/v1/webhooks/1", content_type="application/json")

        assert response.status_code == 400


class TestDeleteWebhook:
    """Tests for deleting webhook endpoint."""

    def test_delete_webhook_success(self, client):
        """Test successful webhook deletion."""
        mock_webhook = MagicMock()
        mock_webhook.id = 1

        with patch("app.api.routes.webhooks.require_api_key", lambda f: f):
            with patch("app.api.routes.webhooks.limiter.limit", lambda x: lambda f: f):
                with patch("app.api.routes.webhooks.get_db_session") as mock_session:
                    session = MagicMock()
                    mock_session.return_value.__enter__ = Mock(return_value=session)
                    mock_session.return_value.__exit__ = Mock(return_value=False)

                    mock_query = MagicMock()
                    mock_query.filter_by.return_value = mock_query
                    mock_query.first.return_value = mock_webhook
                    session.query.return_value = mock_query

                    response = client.delete("/api/v1/webhooks/1")

        assert response.status_code == 200
        data = response.get_json()
        assert "deleted successfully" in data["message"]

    def test_delete_webhook_not_found(self, client):
        """Test deleting non-existent webhook."""
        with patch("app.api.routes.webhooks.require_api_key", lambda f: f):
            with patch("app.api.routes.webhooks.limiter.limit", lambda x: lambda f: f):
                with patch("app.api.routes.webhooks.get_db_session") as mock_session:
                    session = MagicMock()
                    mock_session.return_value.__enter__ = Mock(return_value=session)
                    mock_session.return_value.__exit__ = Mock(return_value=False)

                    mock_query = MagicMock()
                    mock_query.filter_by.return_value = mock_query
                    mock_query.first.return_value = None
                    session.query.return_value = mock_query

                    response = client.delete("/api/v1/webhooks/999")

        assert response.status_code == 404


class TestToggleWebhook:
    """Tests for toggling webhook status endpoint."""

    def test_toggle_webhook_enable(self, client):
        """Test enabling a disabled webhook."""
        mock_webhook = MagicMock()
        mock_webhook.id = 1
        mock_webhook.is_active = False

        with patch("app.api.routes.webhooks.require_api_key", lambda f: f):
            with patch("app.api.routes.webhooks.limiter.limit", lambda x: lambda f: f):
                with patch("app.api.routes.webhooks.get_db_session") as mock_session:
                    session = MagicMock()
                    mock_session.return_value.__enter__ = Mock(return_value=session)
                    mock_session.return_value.__exit__ = Mock(return_value=False)

                    mock_query = MagicMock()
                    mock_query.filter_by.return_value = mock_query
                    mock_query.first.return_value = mock_webhook
                    session.query.return_value = mock_query

                    response = client.post("/api/v1/webhooks/1/toggle")

        assert response.status_code == 200
        data = response.get_json()
        assert "is_active" in data

    def test_toggle_webhook_disable(self, client):
        """Test disabling an enabled webhook."""
        mock_webhook = MagicMock()
        mock_webhook.id = 1
        mock_webhook.is_active = True

        with patch("app.api.routes.webhooks.require_api_key", lambda f: f):
            with patch("app.api.routes.webhooks.limiter.limit", lambda x: lambda f: f):
                with patch("app.api.routes.webhooks.get_db_session") as mock_session:
                    session = MagicMock()
                    mock_session.return_value.__enter__ = Mock(return_value=session)
                    mock_session.return_value.__exit__ = Mock(return_value=False)

                    mock_query = MagicMock()
                    mock_query.filter_by.return_value = mock_query
                    mock_query.first.return_value = mock_webhook
                    session.query.return_value = mock_query

                    response = client.post("/api/v1/webhooks/1/toggle")

        assert response.status_code == 200

    def test_toggle_webhook_not_found(self, client):
        """Test toggling non-existent webhook."""
        with patch("app.api.routes.webhooks.require_api_key", lambda f: f):
            with patch("app.api.routes.webhooks.limiter.limit", lambda x: lambda f: f):
                with patch("app.api.routes.webhooks.get_db_session") as mock_session:
                    session = MagicMock()
                    mock_session.return_value.__enter__ = Mock(return_value=session)
                    mock_session.return_value.__exit__ = Mock(return_value=False)

                    mock_query = MagicMock()
                    mock_query.filter_by.return_value = mock_query
                    mock_query.first.return_value = None
                    session.query.return_value = mock_query

                    response = client.post("/api/v1/webhooks/999/toggle")

        assert response.status_code == 404


class TestWebhookEventTypes:
    """Tests for webhook event type validation."""

    def test_all_valid_events(self, client):
        """Test registration with all valid event types."""
        valid_events = ["flood_detected", "critical_risk", "high_risk", "medium_risk", "low_risk"]

        mock_webhook = MagicMock()
        mock_webhook.id = 1

        with patch("app.api.routes.webhooks.require_api_key", lambda f: f):
            with patch("app.api.routes.webhooks.limiter.limit", lambda x: lambda f: f):
                with patch("app.api.routes.webhooks.get_db_session") as mock_session:
                    session = MagicMock()
                    mock_session.return_value.__enter__ = Mock(return_value=session)
                    mock_session.return_value.__exit__ = Mock(return_value=False)

                    with patch("app.api.routes.webhooks.Webhook") as MockWebhook:
                        MockWebhook.return_value = mock_webhook

                        response = client.post(
                            "/api/v1/webhooks/register",
                            data=json.dumps({"url": "https://example.com/webhook", "events": valid_events}),
                            content_type="application/json",
                        )

        assert response.status_code == 201


class TestWebhookErrorHandling:
    """Tests for webhook error handling."""

    def test_database_error_on_register(self, client):
        """Test webhook registration handles database errors."""
        with patch("app.api.routes.webhooks.require_api_key", lambda f: f):
            with patch("app.api.routes.webhooks.limiter.limit", lambda x: lambda f: f):
                with patch("app.api.routes.webhooks.get_db_session") as mock_session:
                    mock_session.side_effect = Exception("Database error")

                    response = client.post(
                        "/api/v1/webhooks/register",
                        data=json.dumps({"url": "https://example.com/webhook", "events": ["flood_detected"]}),
                        content_type="application/json",
                    )

        assert response.status_code == 500

    def test_database_error_on_list(self, client):
        """Test webhook listing handles database errors."""
        with patch("app.api.routes.webhooks.require_api_key", lambda f: f):
            with patch("app.api.routes.webhooks.limiter.limit", lambda x: lambda f: f):
                with patch("app.api.routes.webhooks.get_db_session") as mock_session:
                    mock_session.side_effect = Exception("Database error")

                    response = client.get("/api/v1/webhooks/list")

        assert response.status_code == 500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
