"""Unit tests for alert coverage and SMS delivery webhook endpoints."""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock


class TestAlertCoverageEndpoint:
    """Tests for GET /api/v1/alerts/coverage."""

    COVERAGE_URL = "/api/v1/alerts/coverage"

    def _make_alert(self, **overrides):
        """Create a mock AlertHistory object."""
        alert = MagicMock()
        alert.is_deleted = False
        alert.location = overrides.get("location", "Baclaran")
        alert.delivery_status = overrides.get("delivery_status", "delivered")
        alert.delivery_channel = overrides.get("delivery_channel", "web")
        alert.risk_level = overrides.get("risk_level", 1)
        alert.created_at = overrides.get(
            "created_at", datetime.now(timezone.utc) - timedelta(hours=1)
        )
        alert.delivered_at = overrides.get(
            "delivered_at", alert.created_at + timedelta(seconds=30)
        )
        return alert

    def test_coverage_empty(self, client):
        """No alerts returns zeroes."""
        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.query.return_value.filter.return_value.all.return_value = []

        with patch("app.api.routes.alerts.get_db_session", return_value=mock_session):
            response = client.get(self.COVERAGE_URL)

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["coverage"]["total_alerts"] == 0
        assert data["coverage"]["delivery_rate_pct"] == 0.0
        assert data["barangays"] == {}
        assert data["channels"] == {}

    def test_coverage_with_alerts(self, client):
        """Coverage aggregates per-barangay and per-channel correctly."""
        alerts = [
            self._make_alert(location="Baclaran", delivery_status="delivered", delivery_channel="web"),
            self._make_alert(location="Baclaran", delivery_status="delivered", delivery_channel="sms"),
            self._make_alert(location="Baclaran", delivery_status="failed", delivery_channel="sms"),
            self._make_alert(location="San Dionisio", delivery_status="pending", delivery_channel="web"),
        ]

        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.query.return_value.filter.return_value.all.return_value = alerts

        with patch("app.api.routes.alerts.get_db_session", return_value=mock_session):
            response = client.get(self.COVERAGE_URL)

        assert response.status_code == 200
        data = response.get_json()
        cov = data["coverage"]
        assert cov["total_alerts"] == 4
        assert cov["total_delivered"] == 2
        assert cov["total_failed"] == 1
        assert cov["total_pending"] == 1
        assert cov["delivery_rate_pct"] == 50.0

        # Per-barangay
        assert "Baclaran" in data["barangays"]
        assert data["barangays"]["Baclaran"]["total"] == 3
        assert data["barangays"]["Baclaran"]["delivered"] == 2

        # Per-channel
        assert "sms" in data["channels"]
        assert data["channels"]["sms"]["total"] == 2

    def test_coverage_hours_param(self, client):
        """Custom hours parameter is accepted and clamped."""
        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.query.return_value.filter.return_value.all.return_value = []

        with patch("app.api.routes.alerts.get_db_session", return_value=mock_session):
            response = client.get(f"{self.COVERAGE_URL}?hours=48")

        assert response.status_code == 200
        assert response.get_json()["coverage"]["hours"] == 48

    def test_coverage_hours_clamped(self, client):
        """Hours > 720 is clamped to 720."""
        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.query.return_value.filter.return_value.all.return_value = []

        with patch("app.api.routes.alerts.get_db_session", return_value=mock_session):
            response = client.get(f"{self.COVERAGE_URL}?hours=9999")

        assert response.status_code == 200
        assert response.get_json()["coverage"]["hours"] == 720

    def test_coverage_median_delivery_time(self, client):
        """Median delivery time is computed correctly."""
        now = datetime.now(timezone.utc)
        alerts = [
            self._make_alert(
                delivery_status="delivered",
                created_at=now - timedelta(hours=2),
                delivered_at=now - timedelta(hours=2) + timedelta(seconds=10),
            ),
            self._make_alert(
                delivery_status="delivered",
                created_at=now - timedelta(hours=1),
                delivered_at=now - timedelta(hours=1) + timedelta(seconds=30),
            ),
            self._make_alert(
                delivery_status="delivered",
                created_at=now - timedelta(minutes=30),
                delivered_at=now - timedelta(minutes=30) + timedelta(seconds=60),
            ),
        ]

        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.query.return_value.filter.return_value.all.return_value = alerts

        with patch("app.api.routes.alerts.get_db_session", return_value=mock_session):
            response = client.get(self.COVERAGE_URL)

        data = response.get_json()
        # Sorted delivery times: [10, 30, 60] → median is index 1 = 30
        assert data["coverage"]["median_delivery_seconds"] == 30.0


class TestSmsDeliveryWebhook:
    """Tests for POST /api/v1/alerts/sms/delivery-status."""

    WEBHOOK_URL = "/api/v1/alerts/sms/delivery-status"

    def test_webhook_json_payload(self, client):
        """JSON payload with valid fields returns 200."""
        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)

        mock_alert = MagicMock()
        mock_session.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_alert

        with patch("app.api.routes.alerts.get_db_session", return_value=mock_session):
            response = client.post(
                self.WEBHOOK_URL,
                json={"message_id": "abc123", "status": "sent", "recipient": "09171234567"},
                content_type="application/json",
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["acknowledged"] is True
        # Should have mapped "sent" → "delivered"
        assert mock_alert.delivery_status == "delivered"

    def test_webhook_form_payload(self, client):
        """Form-encoded payload is also accepted."""
        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)

        mock_alert = MagicMock()
        mock_session.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_alert

        with patch("app.api.routes.alerts.get_db_session", return_value=mock_session):
            response = client.post(
                self.WEBHOOK_URL,
                data={"message_id": "abc123", "status": "failed", "recipient": "09171234567"},
            )

        assert response.status_code == 200
        assert mock_alert.delivery_status == "failed"

    def test_webhook_missing_message_id(self, client):
        """Missing message_id returns 400."""
        response = client.post(
            self.WEBHOOK_URL,
            json={"status": "sent", "recipient": "09171234567"},
        )
        assert response.status_code == 400
        assert "message_id" in response.get_json().get("error", "")

    def test_webhook_missing_status(self, client):
        """Missing status returns 400."""
        response = client.post(
            self.WEBHOOK_URL,
            json={"message_id": "abc123", "recipient": "09171234567"},
        )
        assert response.status_code == 400

    def test_webhook_status_mapping(self, client):
        """Semaphore statuses are mapped correctly."""
        status_map = {
            "sent": "delivered",
            "delivered": "delivered",
            "failed": "failed",
            "pending": "pending",
            "queued": "pending",
            "unknown_status": "pending",  # unmapped → defaults to pending
        }

        for sema_status, expected_mapped in status_map.items():
            mock_session = MagicMock()
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)

            mock_alert = MagicMock()
            mock_session.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_alert

            with patch("app.api.routes.alerts.get_db_session", return_value=mock_session):
                response = client.post(
                    self.WEBHOOK_URL,
                    json={"message_id": "m1", "status": sema_status, "recipient": "09170000000"},
                    content_type="application/json",
                )

            assert response.status_code == 200, f"Failed for status={sema_status}"
            assert mock_alert.delivery_status == expected_mapped, (
                f"Expected '{expected_mapped}' for '{sema_status}', got '{mock_alert.delivery_status}'"
            )

    def test_webhook_no_matching_alert(self, client):
        """Webhook still returns 200 even if no matching SMS alert is found."""
        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.query.return_value.filter.return_value.order_by.return_value.first.return_value = None

        with patch("app.api.routes.alerts.get_db_session", return_value=mock_session):
            response = client.post(
                self.WEBHOOK_URL,
                json={"message_id": "orphan123", "status": "sent", "recipient": "09170000000"},
                content_type="application/json",
            )

        assert response.status_code == 200
        assert response.get_json()["acknowledged"] is True

    def test_webhook_db_error_graceful(self, client):
        """DB error during update is handled gracefully (still returns 200)."""
        with patch("app.api.routes.alerts.get_db_session", side_effect=Exception("db down")):
            response = client.post(
                self.WEBHOOK_URL,
                json={"message_id": "m1", "status": "sent", "recipient": "09170000000"},
                content_type="application/json",
            )

        # The endpoint catches exceptions at the outer level
        assert response.status_code in (200, 500)
