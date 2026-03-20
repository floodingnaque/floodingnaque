"""
Unit tests for dashboard routes.

Tests dashboard statistics and summary endpoints.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, Mock, patch

import pytest


class TestDashboardSummary:
    """Tests for dashboard summary endpoint."""

    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session."""
        with patch("app.api.routes.dashboard.get_db_session") as mock:
            session = MagicMock()
            mock.return_value.__enter__ = Mock(return_value=session)
            mock.return_value.__exit__ = Mock(return_value=False)
            yield session

    @pytest.fixture
    def mock_latest_weather(self):
        """Create mock latest weather data."""
        weather = MagicMock()
        weather.temperature = 298.15
        weather.humidity = 75.0
        weather.precipitation = 5.0
        weather.timestamp = datetime.now(timezone.utc)
        return weather

    @pytest.fixture
    def mock_latest_prediction(self):
        """Create mock latest prediction."""
        prediction = MagicMock()
        prediction.prediction = 0
        prediction.risk_level = 0
        prediction.risk_label = "Safe"
        prediction.confidence = 0.85
        prediction.created_at = datetime.now(timezone.utc)
        return prediction

    def test_get_dashboard_summary_success(self, client, mock_db_session):
        """Test successful dashboard summary retrieval."""
        # Mock the aggregation row objects returned by .one()
        mock_weather_row = MagicMock()
        mock_weather_row.total = 100
        mock_weather_row.today = 5

        mock_pred_row = MagicMock()
        mock_pred_row.total = 200
        mock_pred_row.today = 10
        mock_pred_row.week = 50

        mock_alert_row = MagicMock()
        mock_alert_row.total = 30
        mock_alert_row.today = 2
        mock_alert_row.critical_24h = 1

        # Build a query mock that handles both .one() and .first()/.all() chains
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.group_by.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [(0, 80), (1, 15), (2, 5)]
        mock_query.first.return_value = None
        # Successive .one() calls return weather, prediction, alert rows
        mock_query.one.side_effect = [mock_weather_row, mock_pred_row, mock_alert_row]

        mock_db_session.query.return_value = mock_query

        with patch("app.api.routes.dashboard.limiter.limit", lambda x: lambda f: f):
            response = client.get("/api/dashboard/summary")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "summary" in data
        assert "weather_data" in data["summary"]
        assert "predictions" in data["summary"]
        assert "alerts" in data["summary"]

    def test_get_dashboard_summary_structure(self, client, mock_db_session):
        """Test dashboard summary response structure."""
        zero_row = MagicMock()
        zero_row.total = 0
        zero_row.today = 0
        zero_row.week = 0
        zero_row.critical_24h = 0

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.group_by.return_value = mock_query
        mock_query.all.return_value = []
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.first.return_value = None
        mock_query.one.side_effect = [zero_row, zero_row, zero_row]
        mock_db_session.query.return_value = mock_query

        with patch("app.api.routes.dashboard.limiter.limit", lambda x: lambda f: f):
            response = client.get("/api/dashboard/summary")

        assert response.status_code == 200
        data = response.get_json()

        # Check structure
        summary = data["summary"]
        assert "weather_data" in summary
        assert "predictions" in summary
        assert "alerts" in summary
        assert "risk_distribution_30d" in summary

        # Check weather_data structure
        weather_data = summary["weather_data"]
        assert "total" in weather_data
        assert "today" in weather_data

        # Check predictions structure
        predictions = summary["predictions"]
        assert "total" in predictions
        assert "today" in predictions
        assert "this_week" in predictions

    def test_get_dashboard_summary_with_request_id(self, client, mock_db_session):
        """Test dashboard summary includes request ID."""
        zero_row = MagicMock()
        zero_row.total = 0
        zero_row.today = 0
        zero_row.week = 0
        zero_row.critical_24h = 0

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.group_by.return_value = mock_query
        mock_query.all.return_value = []
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.first.return_value = None
        mock_query.one.side_effect = [zero_row, zero_row, zero_row]
        mock_db_session.query.return_value = mock_query

        with patch("app.api.routes.dashboard.limiter.limit", lambda x: lambda f: f):
            response = client.get("/api/dashboard/summary")

        assert response.status_code == 200
        data = response.get_json()
        assert "request_id" in data
        assert "generated_at" in data


class TestDashboardStatistics:
    """Tests for dashboard statistics endpoint."""

    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session."""
        with patch("app.api.routes.dashboard.get_db_session") as mock:
            session = MagicMock()
            mock.return_value.__enter__ = Mock(return_value=session)
            mock.return_value.__exit__ = Mock(return_value=False)
            yield session

    def test_get_statistics_default_period(self, client, mock_db_session):
        """Test statistics with default week period."""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.group_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        # Weather aggregation .one() returns a row with aggregation fields
        mock_agg = MagicMock(total=0, avg_temp=None, avg_humidity=None, total_precip=0)
        mock_query.one.return_value = mock_agg
        mock_db_session.query.return_value = mock_query

        with patch("app.api.routes.dashboard.limiter.limit", lambda x: lambda f: f):
            response = client.get("/api/dashboard/statistics")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["period"] == "week"

    def test_get_statistics_day_period(self, client, mock_db_session):
        """Test statistics with day period."""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.group_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        mock_agg = MagicMock(total=0, avg_temp=None, avg_humidity=None, total_precip=0)
        mock_query.one.return_value = mock_agg
        mock_db_session.query.return_value = mock_query

        with patch("app.api.routes.dashboard.limiter.limit", lambda x: lambda f: f):
            response = client.get("/api/dashboard/statistics?period=day")

        assert response.status_code == 200
        data = response.get_json()
        assert data["period"] == "day"

    def test_get_statistics_month_period(self, client, mock_db_session):
        """Test statistics with month period."""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.group_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        mock_agg = MagicMock(total=0, avg_temp=None, avg_humidity=None, total_precip=0)
        mock_query.one.return_value = mock_agg
        mock_db_session.query.return_value = mock_query

        with patch("app.api.routes.dashboard.limiter.limit", lambda x: lambda f: f):
            response = client.get("/api/dashboard/statistics?period=month")

        assert response.status_code == 200
        data = response.get_json()
        assert data["period"] == "month"

    def test_get_statistics_invalid_period(self, client):
        """Test statistics with invalid period."""
        with patch("app.api.routes.dashboard.limiter.limit", lambda x: lambda f: f):
            response = client.get("/api/dashboard/statistics?period=invalid")

        assert response.status_code == 400

    def test_get_statistics_predictions_metric(self, client, mock_db_session):
        """Test statistics with predictions metric filter."""
        mock_pred_row = MagicMock(date_key="2026-03-12", count=1, flood=0, safe=1, alert=0, critical=0)

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.group_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.side_effect = [
            [mock_pred_row],  # pred_groups
            [],  # risk_over_time_rows
        ]
        mock_db_session.query.return_value = mock_query

        with patch("app.api.routes.dashboard.limiter.limit", lambda x: lambda f: f):
            response = client.get("/api/dashboard/statistics?metric=predictions")

        assert response.status_code == 200
        data = response.get_json()
        assert "predictions" in data

    def test_get_statistics_alerts_metric(self, client, mock_db_session):
        """Test statistics with alerts metric filter."""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.group_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        mock_db_session.query.return_value = mock_query

        with patch("app.api.routes.dashboard.limiter.limit", lambda x: lambda f: f):
            response = client.get("/api/dashboard/statistics?metric=alerts")

        assert response.status_code == 200
        data = response.get_json()
        assert "alerts" in data

    def test_get_statistics_weather_metric(self, client, mock_db_session):
        """Test statistics with weather metric filter."""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.group_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        mock_agg = MagicMock(total=0, avg_temp=None, avg_humidity=None, total_precip=0)
        mock_query.one.return_value = mock_agg
        mock_db_session.query.return_value = mock_query

        with patch("app.api.routes.dashboard.limiter.limit", lambda x: lambda f: f):
            response = client.get("/api/dashboard/statistics?metric=weather")

        assert response.status_code == 200
        data = response.get_json()
        assert "weather" in data


class TestDashboardActivity:
    """Tests for dashboard activity endpoint."""

    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session."""
        with patch("app.api.routes.dashboard.get_db_session") as mock:
            session = MagicMock()
            mock.return_value.__enter__ = Mock(return_value=session)
            mock.return_value.__exit__ = Mock(return_value=False)
            yield session

    @pytest.fixture
    def mock_predictions(self):
        """Create mock predictions for activity."""
        predictions = []
        for i in range(5):
            pred = MagicMock()
            pred.id = i + 1
            pred.prediction = 0
            pred.risk_level = 0
            pred.risk_label = "Safe"
            pred.created_at = datetime.now(timezone.utc) - timedelta(hours=i)
            predictions.append(pred)
        return predictions

    @pytest.fixture
    def mock_alerts(self):
        """Create mock alerts for activity."""
        alerts = []
        for i in range(3):
            alert = MagicMock()
            alert.id = i + 100
            alert.risk_level = 1
            alert.risk_label = "Alert"
            alert.location = "Paranaque City"
            alert.delivery_status = "delivered"
            alert.created_at = datetime.now(timezone.utc) - timedelta(hours=i)
            alerts.append(alert)
        return alerts

    def test_get_activity_default_limit(self, client, mock_db_session, mock_predictions, mock_alerts):
        """Test activity feed with default limit."""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query

        # Return different results based on model type
        def limit_side_effect(n):
            mock_limited = MagicMock()
            if mock_db_session.query.call_count % 2 == 1:
                mock_limited.all.return_value = mock_predictions[:n]
            else:
                mock_limited.all.return_value = mock_alerts[:n]
            return mock_limited

        mock_query.limit.side_effect = limit_side_effect
        mock_db_session.query.return_value = mock_query

        with patch("app.api.routes.dashboard.limiter.limit", lambda x: lambda f: f):
            response = client.get("/api/dashboard/activity")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "activity" in data
        assert "count" in data

    def test_get_activity_custom_limit(self, client, mock_db_session):
        """Test activity feed with custom limit."""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        mock_db_session.query.return_value = mock_query

        with patch("app.api.routes.dashboard.limiter.limit", lambda x: lambda f: f):
            response = client.get("/api/dashboard/activity?limit=50")

        assert response.status_code == 200

    def test_get_activity_max_limit(self, client, mock_db_session):
        """Test activity feed respects max limit of 100."""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        mock_db_session.query.return_value = mock_query

        with patch("app.api.routes.dashboard.limiter.limit", lambda x: lambda f: f):
            response = client.get("/api/dashboard/activity?limit=200")

        assert response.status_code == 200

    def test_get_activity_empty(self, client, mock_db_session):
        """Test activity feed when no activity exists."""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        mock_db_session.query.return_value = mock_query

        with patch("app.api.routes.dashboard.limiter.limit", lambda x: lambda f: f):
            response = client.get("/api/dashboard/activity")

        assert response.status_code == 200
        data = response.get_json()
        assert data["count"] == 0


class TestDashboardErrorHandling:
    """Tests for dashboard error handling."""

    def test_summary_database_error(self, client):
        """Test summary handles database errors."""
        with patch("app.api.routes.dashboard.limiter.limit", lambda x: lambda f: f):
            with patch("app.api.routes.dashboard.get_db_session") as mock_session:
                mock_session.side_effect = Exception("Database error")

                response = client.get("/api/dashboard/summary")

        assert response.status_code == 500

    def test_statistics_database_error(self, client):
        """Test statistics handles database errors."""
        with patch("app.api.routes.dashboard.limiter.limit", lambda x: lambda f: f):
            with patch("app.api.routes.dashboard.get_db_session") as mock_session:
                mock_session.side_effect = Exception("Database error")

                response = client.get("/api/dashboard/statistics")

        assert response.status_code == 500

    def test_activity_database_error(self, client):
        """Test activity handles database errors."""
        with patch("app.api.routes.dashboard.limiter.limit", lambda x: lambda f: f):
            with patch("app.api.routes.dashboard.get_db_session") as mock_session:
                mock_session.side_effect = Exception("Database error")

                response = client.get("/api/dashboard/activity")

        assert response.status_code == 500


class TestDashboardRiskDistribution:
    """Tests for risk distribution in dashboard."""

    def test_risk_distribution_all_levels(self, client):
        """Test risk distribution returns all risk levels."""
        with patch("app.api.routes.dashboard.limiter.limit", lambda x: lambda f: f):
            with patch("app.api.routes.dashboard.get_db_session") as mock_session:
                session = MagicMock()
                mock_session.return_value.__enter__ = Mock(return_value=session)
                mock_session.return_value.__exit__ = Mock(return_value=False)

                mock_query = MagicMock()
                mock_query.filter.return_value = mock_query
                mock_query.count.return_value = 100
                mock_query.group_by.return_value = mock_query
                mock_query.all.return_value = [(0, 60), (1, 30), (2, 10)]
                mock_query.order_by.return_value = mock_query
                mock_query.limit.return_value = mock_query
                mock_query.first.return_value = None
                # Successive .one() calls return weather_row, pred_row, alert_row
                zero_row = MagicMock(total=0, today=0, week=0, critical_24h=0)
                mock_query.one.side_effect = [zero_row, zero_row, zero_row]
                session.query.return_value = mock_query

                response = client.get("/api/dashboard/summary")

        assert response.status_code == 200
        data = response.get_json()
        risk_dist = data["summary"]["risk_distribution_30d"]
        assert "safe" in risk_dist
        assert "alert" in risk_dist
        assert "critical" in risk_dist


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
