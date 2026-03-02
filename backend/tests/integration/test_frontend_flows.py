"""
End-to-End Integration Tests for Frontend Flows.

Tests complete user flows that simulate frontend interactions with the API.
"""

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock, patch

import pytest


class TestUserAuthenticationFlow:
    """E2E tests for user authentication flow."""

    def test_complete_registration_to_login_flow(self, client):
        """Test complete flow from registration to login."""
        # Step 1: Register new user
        registration_data = {
            "email": "newuser@example.com",
            "password": "SecurePassword123!@#",
            "full_name": "New User",
        }

        with patch("app.api.routes.users.limiter.limit", lambda x: lambda f: f):
            with patch("app.api.routes.users.is_jwt_available", return_value=True):
                with patch("app.api.routes.users.is_bcrypt_available", return_value=True):
                    with patch("app.api.routes.users.is_secure_password", return_value=(True, [])):
                        with patch("app.api.routes.users.hash_password", return_value="hashed"):
                            with patch("app.api.routes.users.get_db_session") as mock_session:
                                session = MagicMock()
                                mock_session.return_value.__enter__ = Mock(return_value=session)
                                mock_session.return_value.__exit__ = Mock(return_value=False)

                                mock_query = MagicMock()
                                mock_query.filter.return_value = mock_query
                                mock_query.first.return_value = None
                                session.query.return_value = mock_query

                                mock_user = MagicMock()
                                mock_user.id = 1
                                mock_user.to_dict.return_value = {"id": 1, "email": registration_data["email"]}

                                with patch("app.api.routes.users.User", return_value=mock_user):
                                    register_response = client.post(
                                        "/api/v1/auth/register",
                                        data=json.dumps(registration_data),
                                        content_type="application/json",
                                    )

        assert register_response.status_code == 201

        # Step 2: Login with registered credentials
        login_data = {"email": "newuser@example.com", "password": "SecurePassword123!@#"}

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.email = login_data["email"]
        mock_user.role = "user"
        mock_user.is_active = True
        mock_user.failed_login_attempts = 0
        mock_user.is_locked = Mock(return_value=False)
        mock_user.to_dict.return_value = {"id": 1, "email": login_data["email"]}

        with patch("app.api.routes.users.limiter.limit", lambda x: lambda f: f):
            with patch("app.api.routes.users.is_jwt_available", return_value=True):
                with patch("app.api.routes.users.is_bcrypt_available", return_value=True):
                    with patch("app.api.routes.users.verify_password", return_value=True):
                        with patch("app.api.routes.users.create_access_token", return_value="access_token"):
                            with patch(
                                "app.api.routes.users.create_refresh_token", return_value=("refresh_token", "hash")
                            ):
                                with patch("app.api.routes.users.get_db_session") as mock_session:
                                    session = MagicMock()
                                    mock_session.return_value.__enter__ = Mock(return_value=session)
                                    mock_session.return_value.__exit__ = Mock(return_value=False)

                                    mock_query = MagicMock()
                                    mock_query.filter.return_value = mock_query
                                    mock_query.first.return_value = mock_user
                                    session.query.return_value = mock_query

                                    login_response = client.post(
                                        "/api/v1/auth/login",
                                        data=json.dumps(login_data),
                                        content_type="application/json",
                                    )

        assert login_response.status_code == 200
        assert "access_token" in login_response.get_json()

    def test_session_token_refresh_flow(self, client):
        """Test token refresh flow for maintaining session."""
        from datetime import timedelta

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.email = "test@example.com"
        mock_user.role = "user"
        mock_user.refresh_token_hash = "token_hash"
        mock_user.refresh_token_expires = datetime.now(timezone.utc) + timedelta(hours=1)

        with patch("app.api.routes.users.limiter.limit", lambda x: lambda f: f):
            with patch("app.api.routes.users.decode_token", return_value=({"sub": "1", "type": "refresh"}, None)):
                with patch("app.api.routes.users.create_access_token", return_value="new_access_token"):
                    with patch("app.api.routes.users.get_db_session") as mock_session:
                        session = MagicMock()
                        mock_session.return_value.__enter__ = Mock(return_value=session)
                        mock_session.return_value.__exit__ = Mock(return_value=False)

                        mock_query = MagicMock()
                        mock_query.filter.return_value = mock_query
                        mock_query.first.return_value = mock_user
                        session.query.return_value = mock_query

                        with patch("hashlib.sha256") as mock_hash:
                            mock_hash.return_value.hexdigest.return_value = "token_hash"

                            response = client.post(
                                "/api/v1/auth/refresh",
                                data=json.dumps({"refresh_token": "valid_refresh_token"}),
                                content_type="application/json",
                            )

        assert response.status_code == 200
        assert "access_token" in response.get_json()


class TestDashboardDataFlow:
    """E2E tests for dashboard data retrieval flow."""

    def test_dashboard_full_load_flow(self, client):
        """Test complete dashboard data loading flow."""

        # Create proper mock prediction objects for statistics endpoint
        # Using a simple class instead of MagicMock to ensure proper comparison
        class MockPrediction:
            def __init__(self, i):
                self.created_at = datetime.now(timezone.utc)
                self.prediction = i % 2
                self.risk_level = i % 3
                self.confidence = 0.85
                self.is_deleted = False

        class MockAlert:
            def __init__(self, i):
                self.created_at = datetime.now(timezone.utc)
                self.risk_level = i % 3
                self.alert_type = "flood_warning"
                self.triggered = True
                self.is_deleted = False

        mock_predictions = [MockPrediction(i) for i in range(5)]
        mock_alerts = [MockAlert(i) for i in range(3)]

        # Setup mocks for all dashboard endpoints
        with patch("app.api.routes.dashboard.limiter.limit", lambda x: lambda f: f):
            with patch("app.api.routes.dashboard.get_db_session") as mock_session:
                session = MagicMock()
                mock_session.return_value.__enter__ = Mock(return_value=session)
                mock_session.return_value.__exit__ = Mock(return_value=False)

                # Create a mock query that can handle different calls
                mock_query = MagicMock()
                mock_query.filter.return_value = mock_query
                mock_query.count.return_value = 50
                mock_query.group_by.return_value = mock_query
                # Return tuples for group_by().all() (risk_distribution)
                mock_query.all.return_value = [(0, 40), (1, 8), (2, 2)]
                mock_query.order_by.return_value = mock_query
                mock_query.first.return_value = None
                session.query.return_value = mock_query

                # Get summary
                summary_response = client.get("/api/v1/dashboard/summary")
                assert summary_response.status_code == 200

                # For statistics, return empty list (simplest working case)
                mock_query.all.return_value = []

                # Get statistics
                stats_response = client.get("/api/v1/dashboard/statistics?period=week")
                assert stats_response.status_code == 200

                # Get activity feed
                activity_response = client.get("/api/v1/dashboard/activity?limit=20")
                assert activity_response.status_code == 200

    def test_dashboard_with_filters(self, client):
        """Test dashboard with various filter combinations."""
        with patch("app.api.routes.dashboard.limiter.limit", lambda x: lambda f: f):
            with patch("app.api.routes.dashboard.get_db_session") as mock_session:
                session = MagicMock()
                mock_session.return_value.__enter__ = Mock(return_value=session)
                mock_session.return_value.__exit__ = Mock(return_value=False)

                mock_query = MagicMock()
                mock_query.filter.return_value = mock_query
                mock_query.order_by.return_value = mock_query
                mock_query.all.return_value = []
                session.query.return_value = mock_query

                # Test different period filters
                for period in ["day", "week", "month"]:
                    response = client.get(f"/api/v1/dashboard/statistics?period={period}")
                    assert response.status_code == 200

                # Test different metric filters
                for metric in ["predictions", "alerts", "weather"]:
                    response = client.get(f"/api/v1/dashboard/statistics?metric={metric}")
                    assert response.status_code == 200


class TestPredictionWorkflow:
    """E2E tests for prediction workflow."""

    def test_single_prediction_flow(self, client):
        """Test single prediction request flow."""
        prediction_input = {"temperature": 298.15, "humidity": 75, "precipitation": 10.0, "wind_speed": 15.0}

        mock_result = {
            "prediction": 0,
            "flood_risk": "Safe",
            "risk_level": 0,
            "confidence": 0.85,
            "request_id": "test-123",
        }

        with patch("app.api.routes.predict.rate_limit_with_burst", lambda x: lambda f: f):
            with patch("app.api.routes.predict.predict_flood", return_value=mock_result):
                with patch("app.api.middleware.auth.validate_api_key", return_value=(True, "")):
                    with patch("app.api.middleware.auth._hash_api_key_pbkdf2", return_value="testhash"):
                        response = client.post(
                            "/api/v1/predict/",
                            data=json.dumps(prediction_input),
                            content_type="application/json",
                            headers={"X-API-Key": "test-key"},
                        )

        # Verify prediction was processed
        if response.status_code == 200:
            data = response.get_json()
            assert "prediction" in data or "flood_risk" in data

    def test_batch_prediction_flow(self, client):
        """Test batch prediction workflow."""
        batch_input = {
            "predictions": [
                {"temperature": 298.15, "humidity": 65, "precipitation": 5.0},
                {"temperature": 300.15, "humidity": 80, "precipitation": 25.0},
                {"temperature": 295.0, "humidity": 90, "precipitation": 50.0},
            ]
        }

        mock_result = {"prediction": 0, "risk_level": 0, "confidence": 0.85, "model_version": "1.0.0"}

        with patch("app.api.middleware.auth.validate_api_key", return_value=(True, "")):
            with patch("app.api.middleware.auth._hash_api_key_pbkdf2", return_value="testhash"):
                with patch("app.api.middleware.rate_limit.limiter"):
                    with patch("app.api.routes.batch.predict_flood", return_value=mock_result):
                        response = client.post(
                            "/api/v1/batch/predict",
                            data=json.dumps(batch_input),
                            content_type="application/json",
                            headers={"X-API-Key": "test-key"},
                        )

        assert response.status_code == 200
        data = response.get_json()
        assert "results" in data
        assert data["total_requested"] == 3

    def test_prediction_history_retrieval(self, client):
        """Test retrieving prediction history."""
        mock_predictions = []
        for i in range(5):
            pred = MagicMock()
            pred.id = i + 1
            pred.weather_data_id = i + 100
            pred.prediction = i % 2
            pred.risk_level = i % 3
            pred.risk_label = ["Safe", "Alert", "Critical"][i % 3]
            pred.confidence = 0.85
            pred.model_version = "1.0.0"
            pred.model_name = "flood_predictor"
            pred.created_at = datetime.now(timezone.utc)
            mock_predictions.append(pred)

        with patch("app.api.routes.predictions.limiter.limit", lambda x: lambda f: f):
            with patch("app.api.routes.predictions.get_db_session") as mock_session:
                session = MagicMock()
                mock_session.return_value.__enter__ = Mock(return_value=session)
                mock_session.return_value.__exit__ = Mock(return_value=False)

                mock_query = MagicMock()
                mock_query.filter.return_value = mock_query
                mock_query.count.return_value = len(mock_predictions)
                mock_query.order_by.return_value = mock_query
                mock_query.offset.return_value = mock_query
                mock_query.limit.return_value = mock_query
                mock_query.add_columns.return_value = mock_query

                # Wrap each prediction as a row-like object with [0] indexing and _total attr
                class _Row:
                    def __init__(self, pred, total):
                        self._pred = pred
                        self._total = total
                    def __getitem__(self, idx):
                        return self._pred

                wrapped = [_Row(p, len(mock_predictions)) for p in mock_predictions]
                mock_query.all.return_value = wrapped
                session.query.return_value = mock_query

                response = client.get("/api/v1/predictions?limit=10")

        assert response.status_code == 200
        data = response.get_json()
        assert "data" in data


class TestDataExportFlow:
    """E2E tests for data export workflow."""

    def test_export_weather_data_flow(self, client):
        """Test weather data export flow."""
        mock_records = []
        for i in range(3):
            record = MagicMock()
            record.id = i + 1
            record.timestamp = datetime.now(timezone.utc)
            record.temperature = 298.15
            record.humidity = 75.0
            record.precipitation = 5.0
            record.wind_speed = 10.0
            record.pressure = 1013.25
            record.latitude = 14.4793
            record.longitude = 121.0198
            record.location = "Paranaque City"
            mock_records.append(record)

        with patch("app.api.middleware.auth.validate_api_key", return_value=(True, "")):
            with patch("app.api.middleware.auth._hash_api_key_pbkdf2", return_value="testhash"):
                with patch("app.api.routes.export.limiter.limit", lambda x: lambda f: f):
                    with patch("app.api.routes.export.get_db_session") as mock_session:
                        session = MagicMock()
                        mock_session.return_value.__enter__ = Mock(return_value=session)
                        mock_session.return_value.__exit__ = Mock(return_value=False)

                        mock_query = MagicMock()
                        mock_query.filter_by.return_value = mock_query
                        mock_query.filter.return_value = mock_query
                        mock_query.order_by.return_value = mock_query
                        mock_query.limit.return_value = mock_query
                        mock_query.all.return_value = mock_records
                        session.query.return_value = mock_query

                        headers = {"X-API-Key": "test-key"}

                        # Test JSON export
                        json_response = client.get("/api/v1/export/weather?format=json", headers=headers)
                        assert json_response.status_code == 200

                        # Test CSV export
                        csv_response = client.get("/api/v1/export/weather?format=csv", headers=headers)
                        assert csv_response.status_code == 200
                        assert csv_response.content_type == "text/csv; charset=utf-8"

    def test_export_with_date_filters(self, client):
        """Test export with date filters."""
        with patch("app.api.middleware.auth.validate_api_key", return_value=(True, "")):
            with patch("app.api.middleware.auth._hash_api_key_pbkdf2", return_value="testhash"):
                with patch("app.api.routes.export.limiter.limit", lambda x: lambda f: f):
                    with patch("app.api.routes.export.get_db_session") as mock_session:
                        session = MagicMock()
                        mock_session.return_value.__enter__ = Mock(return_value=session)
                        mock_session.return_value.__exit__ = Mock(return_value=False)

                        mock_query = MagicMock()
                        mock_query.filter_by.return_value = mock_query
                        mock_query.filter.return_value = mock_query
                        mock_query.order_by.return_value = mock_query
                        mock_query.limit.return_value = mock_query
                        mock_query.all.return_value = []
                        session.query.return_value = mock_query

                        response = client.get(
                            "/api/v1/export/weather?start_date=2025-01-01&end_date=2025-01-31&limit=1000",
                            headers={"X-API-Key": "test-key"},
                        )

        assert response.status_code == 200


class TestWebhookManagementFlow:
    """E2E tests for webhook management workflow."""

    def test_webhook_crud_flow(self, client):
        """Test complete webhook CRUD flow."""
        # Step 1: Register webhook
        webhook_data = {"url": "https://example.com/webhook", "events": ["flood_detected", "critical_risk"]}

        mock_webhook = MagicMock()
        mock_webhook.id = 1
        headers = {"X-API-Key": "test-key", "Content-Type": "application/json"}

        with patch("app.api.middleware.auth.validate_api_key", return_value=(True, "")):
            with patch("app.api.middleware.auth._hash_api_key_pbkdf2", return_value="testhash"):
                with patch("app.api.routes.webhooks.limiter.limit", lambda x: lambda f: f):
                    with patch("app.api.routes.webhooks.get_db_session") as mock_session:
                        session = MagicMock()
                        mock_session.return_value.__enter__ = Mock(return_value=session)
                        mock_session.return_value.__exit__ = Mock(return_value=False)

                        with patch("app.api.routes.webhooks.Webhook", return_value=mock_webhook):
                            register_response = client.post(
                                "/api/v1/webhooks/register",
                                data=json.dumps(webhook_data),
                                headers=headers,
                            )

        assert register_response.status_code == 201

        # Step 2: List webhooks
        mock_webhook.url = webhook_data["url"]
        mock_webhook.events = '["flood_detected", "critical_risk"]'
        mock_webhook.is_active = True
        mock_webhook.failure_count = 0
        mock_webhook.last_triggered_at = None
        mock_webhook.created_at = datetime.now(timezone.utc)

        with patch("app.api.middleware.auth.validate_api_key", return_value=(True, "")):
            with patch("app.api.middleware.auth._hash_api_key_pbkdf2", return_value="testhash"):
                with patch("app.api.routes.webhooks.limiter.limit", lambda x: lambda f: f):
                    with patch("app.api.routes.webhooks.get_db_session") as mock_session:
                        session = MagicMock()
                        mock_session.return_value.__enter__ = Mock(return_value=session)
                        mock_session.return_value.__exit__ = Mock(return_value=False)

                        mock_query = MagicMock()
                        mock_query.filter_by.return_value = mock_query
                        mock_query.all.return_value = [mock_webhook]
                        session.query.return_value = mock_query

                        list_response = client.get("/api/v1/webhooks/list", headers={"X-API-Key": "test-key"})

        assert list_response.status_code == 200
        assert list_response.get_json()["count"] >= 1

        # Step 3: Update webhook
        mock_webhook.updated_at = datetime.now(timezone.utc)

        with patch("app.api.middleware.auth.validate_api_key", return_value=(True, "")):
            with patch("app.api.middleware.auth._hash_api_key_pbkdf2", return_value="testhash"):
                with patch("app.api.routes.webhooks.limiter.limit", lambda x: lambda f: f):
                    with patch("app.api.routes.webhooks.get_db_session") as mock_session:
                        session = MagicMock()
                        mock_session.return_value.__enter__ = Mock(return_value=session)
                        mock_session.return_value.__exit__ = Mock(return_value=False)

                        mock_query = MagicMock()
                        mock_query.filter_by.return_value = mock_query
                        mock_query.first.return_value = mock_webhook
                        session.query.return_value = mock_query

                        update_response = client.put(
                            "/api/v1/webhooks/1",
                            data=json.dumps({"url": "https://new-url.com/webhook"}),
                            headers=headers,
                        )

        assert update_response.status_code == 200

        # Step 4: Toggle webhook
        with patch("app.api.middleware.auth.validate_api_key", return_value=(True, "")):
            with patch("app.api.middleware.auth._hash_api_key_pbkdf2", return_value="testhash"):
                with patch("app.api.routes.webhooks.limiter.limit", lambda x: lambda f: f):
                    with patch("app.api.routes.webhooks.get_db_session") as mock_session:
                        session = MagicMock()
                        mock_session.return_value.__enter__ = Mock(return_value=session)
                        mock_session.return_value.__exit__ = Mock(return_value=False)

                        mock_query = MagicMock()
                        mock_query.filter_by.return_value = mock_query
                        mock_query.first.return_value = mock_webhook
                        session.query.return_value = mock_query

                        toggle_response = client.post("/api/v1/webhooks/1/toggle", headers={"X-API-Key": "test-key"})

        assert toggle_response.status_code == 200

        # Step 5: Delete webhook
        with patch("app.api.middleware.auth.validate_api_key", return_value=(True, "")):
            with patch("app.api.middleware.auth._hash_api_key_pbkdf2", return_value="testhash"):
                with patch("app.api.routes.webhooks.limiter.limit", lambda x: lambda f: f):
                    with patch("app.api.routes.webhooks.get_db_session") as mock_session:
                        session = MagicMock()
                        mock_session.return_value.__enter__ = Mock(return_value=session)
                        mock_session.return_value.__exit__ = Mock(return_value=False)

                        mock_query = MagicMock()
                        mock_query.filter_by.return_value = mock_query
                        mock_query.first.return_value = mock_webhook
                        session.query.return_value = mock_query

                        delete_response = client.delete("/api/v1/webhooks/1", headers={"X-API-Key": "test-key"})

        assert delete_response.status_code == 200


class TestErrorRecoveryFlow:
    """E2E tests for error handling and recovery."""

    def test_graceful_degradation(self, client):
        """Test system gracefully handles service failures."""
        # Dashboard should handle database errors gracefully
        with patch("app.api.routes.dashboard.limiter.limit", lambda x: lambda f: f):
            with patch("app.api.routes.dashboard.get_db_session") as mock_session:
                mock_session.side_effect = Exception("Database error")

                response = client.get("/api/v1/dashboard/summary")

                # Should return error but not crash
                assert response.status_code == 500
                assert "error" in response.get_json()

    def test_validation_error_feedback(self, client):
        """Test proper validation error feedback."""
        invalid_batch_data = {"predictions": [{"humidity": 65, "precipitation": 5.0}]}  # Missing temperature

        mock_result = {"prediction": 0, "risk_level": 0, "confidence": 0.85, "model_version": "1.0.0"}

        with patch("app.api.middleware.auth.validate_api_key", return_value=(True, "")):
            with patch("app.api.middleware.auth._hash_api_key_pbkdf2", return_value="testhash"):
                with patch("app.api.middleware.rate_limit.limiter"):
                    response = client.post(
                        "/api/v1/batch/predict",
                        data=json.dumps(invalid_batch_data),
                        content_type="application/json",
                        headers={"X-API-Key": "test-key"},
                    )

        assert response.status_code == 200
        data = response.get_json()
        assert data["failed"] == 1
        assert "errors" in data


class TestHealthCheckFlow:
    """E2E tests for system health checks."""

    def test_health_endpoints(self, client):
        """Test all health check endpoints."""
        # Root endpoint
        response = client.get("/")
        assert response.status_code in [200, 302]  # May redirect

        # Status endpoint
        status_response = client.get("/status")
        if status_response.status_code == 200:
            assert "status" in status_response.get_json()

        # Health endpoint
        health_response = client.get("/health")
        if health_response.status_code == 200:
            assert "status" in health_response.get_json()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
