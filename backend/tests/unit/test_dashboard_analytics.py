"""
Unit Tests for Dashboard Analytics Service.

Tests the DashboardAnalytics class for dashboard statistics,
time-series data, flood risk trends, and performance metrics.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock, patch

import pytest

# Application imports (moved from function level for coverage tracking)
from app.services.dashboard_analytics import (
    DashboardAnalytics,
    _dashboard_analytics,
    get_dashboard_analytics,
)

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    return MagicMock()


@pytest.fixture
def mock_weather_stats():
    """Create mock weather statistics result."""
    # Simulates: (total_records, days_with_data, avg_temp, avg_humidity, avg_precip, max_precip, earliest, latest)
    return (100, 15, 298.5, 75.5, 10.25, 50.0, datetime.now(timezone.utc), datetime.now(timezone.utc))


@pytest.fixture
def mock_prediction_stats():
    """Create mock prediction statistics result."""
    # Simulates: (total, flood_predictions, safe_count, alert_count, critical_count, avg_confidence)
    return (500, 50, 350, 100, 50, 0.8765)


@pytest.fixture
def mock_alert_stats():
    """Create mock alert statistics result."""
    # Simulates: (total_alerts, delivered, failed, pending)
    return (100, 85, 5, 10)


@pytest.fixture
def mock_time_series_results():
    """Create mock time series results."""
    now = datetime.now(timezone.utc)
    return [
        (now - timedelta(days=2), 5.5, 24),
        (now - timedelta(days=1), 10.2, 24),
        (now, 7.8, 12),
    ]


@pytest.fixture
def mock_risk_trend_results():
    """Create mock risk trend results."""
    today = datetime.now(timezone.utc).date()
    yesterday = today - timedelta(days=1)
    return [
        (today, 0, 50),  # Safe
        (today, 1, 30),  # Alert
        (today, 2, 10),  # Critical
        (yesterday, 0, 60),
        (yesterday, 1, 25),
        (yesterday, 2, 5),
    ]


@pytest.fixture
def mock_performance_metrics():
    """Create mock performance metrics result."""
    # (total, avg_rt, p50, p95, p99, errors, success)
    return (1000, 45.5, 30.0, 100.0, 200.0, 10, 990)


# =============================================================================
# DashboardAnalytics Initialization Tests
# =============================================================================


class TestDashboardAnalyticsInitialization:
    """Tests for DashboardAnalytics initialization."""

    @patch("app.services.dashboard_analytics.get_router")
    def test_init_creates_router(self, mock_get_router):
        """Test that initialization creates a router."""
        mock_get_router.return_value = MagicMock()
        analytics = DashboardAnalytics()

        mock_get_router.assert_called_once()
        assert analytics.router is not None

    @patch("app.services.dashboard_analytics.get_router")
    def test_get_dashboard_analytics_singleton(self, mock_get_router):
        """Test singleton pattern for get_dashboard_analytics."""
        # Reset singleton
        import app.services.dashboard_analytics as module

        module._dashboard_analytics = None

        mock_get_router.return_value = MagicMock()

        instance1 = get_dashboard_analytics()
        instance2 = get_dashboard_analytics()

        assert instance1 is instance2


# =============================================================================
# get_dashboard_stats Tests
# =============================================================================


class TestGetDashboardStats:
    """Tests for get_dashboard_stats method."""

    @patch("app.services.dashboard_analytics.get_router")
    def test_returns_complete_structure(
        self, mock_get_router, mock_session, mock_weather_stats, mock_prediction_stats, mock_alert_stats
    ):
        """Test that dashboard stats returns complete structure."""
        mock_get_router.return_value = MagicMock()
        analytics = DashboardAnalytics()

        # Setup mock session
        mock_session.execute.side_effect = [
            MagicMock(fetchone=Mock(return_value=mock_weather_stats)),
            MagicMock(fetchone=Mock(return_value=mock_prediction_stats)),
            MagicMock(fetchone=Mock(return_value=mock_alert_stats)),
        ]

        # Call without decorator (directly pass session)
        result = analytics.get_dashboard_stats.__wrapped__(analytics, session=mock_session, days=30)

        assert "period_days" in result
        assert "weather" in result
        assert "predictions" in result
        assert "alerts" in result
        assert "generated_at" in result

    @patch("app.services.dashboard_analytics.get_router")
    def test_weather_stats_structure(
        self, mock_get_router, mock_session, mock_weather_stats, mock_prediction_stats, mock_alert_stats
    ):
        """Test weather stats structure."""
        mock_get_router.return_value = MagicMock()
        analytics = DashboardAnalytics()

        mock_session.execute.side_effect = [
            MagicMock(fetchone=Mock(return_value=mock_weather_stats)),
            MagicMock(fetchone=Mock(return_value=mock_prediction_stats)),
            MagicMock(fetchone=Mock(return_value=mock_alert_stats)),
        ]

        result = analytics.get_dashboard_stats.__wrapped__(analytics, session=mock_session)

        weather = result["weather"]
        assert weather["total_records"] == 100
        assert weather["days_with_data"] == 15
        assert weather["avg_temperature_k"] == 298.5
        assert weather["avg_humidity_pct"] == 75.5
        assert weather["avg_precipitation_mm"] == 10.25
        assert weather["max_precipitation_mm"] == 50.0

    @patch("app.services.dashboard_analytics.get_router")
    def test_prediction_stats_structure(
        self, mock_get_router, mock_session, mock_weather_stats, mock_prediction_stats, mock_alert_stats
    ):
        """Test prediction stats structure."""
        mock_get_router.return_value = MagicMock()
        analytics = DashboardAnalytics()

        mock_session.execute.side_effect = [
            MagicMock(fetchone=Mock(return_value=mock_weather_stats)),
            MagicMock(fetchone=Mock(return_value=mock_prediction_stats)),
            MagicMock(fetchone=Mock(return_value=mock_alert_stats)),
        ]

        result = analytics.get_dashboard_stats.__wrapped__(analytics, session=mock_session)

        predictions = result["predictions"]
        assert predictions["total"] == 500
        assert predictions["flood_predictions"] == 50
        assert predictions["safe_count"] == 350
        assert predictions["alert_count"] == 100
        assert predictions["critical_count"] == 50
        assert predictions["avg_confidence"] == 0.8765

    @patch("app.services.dashboard_analytics.get_router")
    def test_alert_stats_structure(
        self, mock_get_router, mock_session, mock_weather_stats, mock_prediction_stats, mock_alert_stats
    ):
        """Test alert stats structure."""
        mock_get_router.return_value = MagicMock()
        analytics = DashboardAnalytics()

        mock_session.execute.side_effect = [
            MagicMock(fetchone=Mock(return_value=mock_weather_stats)),
            MagicMock(fetchone=Mock(return_value=mock_prediction_stats)),
            MagicMock(fetchone=Mock(return_value=mock_alert_stats)),
        ]

        result = analytics.get_dashboard_stats.__wrapped__(analytics, session=mock_session)

        alerts = result["alerts"]
        assert alerts["total"] == 100
        assert alerts["delivered"] == 85
        assert alerts["failed"] == 5
        assert alerts["pending"] == 10

    @patch("app.services.dashboard_analytics.get_router")
    def test_handles_null_values(self, mock_get_router, mock_session):
        """Test handling of NULL values from database."""
        mock_get_router.return_value = MagicMock()
        analytics = DashboardAnalytics()

        # All NULL values
        null_stats = (0, 0, None, None, None, None, None, None)
        null_predictions = (0, None, None, None, None, None)
        null_alerts = (0, None, None, None)

        mock_session.execute.side_effect = [
            MagicMock(fetchone=Mock(return_value=null_stats)),
            MagicMock(fetchone=Mock(return_value=null_predictions)),
            MagicMock(fetchone=Mock(return_value=null_alerts)),
        ]

        result = analytics.get_dashboard_stats.__wrapped__(analytics, session=mock_session)

        assert result["weather"]["total_records"] == 0
        assert result["weather"]["avg_temperature_k"] is None
        assert result["predictions"]["total"] == 0
        assert result["predictions"]["avg_confidence"] is None
        assert result["alerts"]["total"] == 0

    @patch("app.services.dashboard_analytics.get_router")
    def test_custom_days_parameter(
        self, mock_get_router, mock_session, mock_weather_stats, mock_prediction_stats, mock_alert_stats
    ):
        """Test custom days parameter."""
        mock_get_router.return_value = MagicMock()
        analytics = DashboardAnalytics()

        mock_session.execute.side_effect = [
            MagicMock(fetchone=Mock(return_value=mock_weather_stats)),
            MagicMock(fetchone=Mock(return_value=mock_prediction_stats)),
            MagicMock(fetchone=Mock(return_value=mock_alert_stats)),
        ]

        result = analytics.get_dashboard_stats.__wrapped__(analytics, session=mock_session, days=7)

        assert result["period_days"] == 7


# =============================================================================
# get_time_series_data Tests
# =============================================================================


class TestGetTimeSeriesData:
    """Tests for get_time_series_data method."""

    @patch("app.services.dashboard_analytics.get_router")
    def test_returns_list_of_dicts(self, mock_get_router, mock_session, mock_time_series_results):
        """Test that time series returns list of dictionaries."""
        mock_get_router.return_value = MagicMock()
        analytics = DashboardAnalytics()

        mock_session.execute.return_value = MagicMock(fetchall=Mock(return_value=mock_time_series_results))

        result = analytics.get_time_series_data.__wrapped__(analytics, session=mock_session, metric="precipitation")

        assert isinstance(result, list)
        assert len(result) == 3
        for item in result:
            assert "period" in item
            assert "value" in item
            assert "sample_count" in item

    @patch("app.services.dashboard_analytics.get_router")
    def test_data_point_structure(self, mock_get_router, mock_session, mock_time_series_results):
        """Test structure of individual data points."""
        mock_get_router.return_value = MagicMock()
        analytics = DashboardAnalytics()

        mock_session.execute.return_value = MagicMock(fetchall=Mock(return_value=mock_time_series_results))

        result = analytics.get_time_series_data.__wrapped__(analytics, session=mock_session)

        first_point = result[0]
        assert first_point["value"] == 5.5
        assert first_point["sample_count"] == 24

    @patch("app.services.dashboard_analytics.get_router")
    def test_default_parameters(self, mock_get_router, mock_session):
        """Test default parameter values."""
        mock_get_router.return_value = MagicMock()
        analytics = DashboardAnalytics()

        mock_session.execute.return_value = MagicMock(fetchall=Mock(return_value=[]))

        analytics.get_time_series_data.__wrapped__(analytics, session=mock_session)

        # Verify SQL was executed
        mock_session.execute.assert_called_once()

    @patch("app.services.dashboard_analytics.get_router")
    def test_metric_options(self, mock_get_router, mock_session):
        """Test different metric options."""
        mock_get_router.return_value = MagicMock()
        analytics = DashboardAnalytics()

        mock_session.execute.return_value = MagicMock(fetchall=Mock(return_value=[]))

        metrics = ["precipitation", "temperature", "humidity", "wind_speed", "pressure"]
        for metric in metrics:
            analytics.get_time_series_data.__wrapped__(analytics, session=mock_session, metric=metric)

        assert mock_session.execute.call_count == len(metrics)

    @patch("app.services.dashboard_analytics.get_router")
    def test_interval_options(self, mock_get_router, mock_session):
        """Test different interval options."""
        mock_get_router.return_value = MagicMock()
        analytics = DashboardAnalytics()

        mock_session.execute.return_value = MagicMock(fetchall=Mock(return_value=[]))

        intervals = ["hour", "day", "week", "month"]
        for interval in intervals:
            analytics.get_time_series_data.__wrapped__(analytics, session=mock_session, interval=interval)

        assert mock_session.execute.call_count == len(intervals)

    @patch("app.services.dashboard_analytics.get_router")
    def test_custom_date_range(self, mock_get_router, mock_session):
        """Test custom date range parameters."""
        mock_get_router.return_value = MagicMock()
        analytics = DashboardAnalytics()

        mock_session.execute.return_value = MagicMock(fetchall=Mock(return_value=[]))

        start = datetime.now(timezone.utc) - timedelta(days=7)
        end = datetime.now(timezone.utc)

        analytics.get_time_series_data.__wrapped__(analytics, session=mock_session, start_date=start, end_date=end)

        # Verify call was made with correct parameters
        call_args = mock_session.execute.call_args
        assert call_args is not None

    @patch("app.services.dashboard_analytics.get_router")
    def test_handles_empty_results(self, mock_get_router, mock_session):
        """Test handling of empty results."""
        mock_get_router.return_value = MagicMock()
        analytics = DashboardAnalytics()

        mock_session.execute.return_value = MagicMock(fetchall=Mock(return_value=[]))

        result = analytics.get_time_series_data.__wrapped__(analytics, session=mock_session)

        assert result == []


# =============================================================================
# get_flood_risk_trend Tests
# =============================================================================


class TestGetFloodRiskTrend:
    """Tests for get_flood_risk_trend method."""

    @patch("app.services.dashboard_analytics.get_router")
    def test_returns_daily_risk_distributions(self, mock_get_router, mock_session, mock_risk_trend_results):
        """Test that risk trend returns daily distributions."""
        mock_get_router.return_value = MagicMock()
        analytics = DashboardAnalytics()

        mock_session.execute.return_value = MagicMock(fetchall=Mock(return_value=mock_risk_trend_results))

        result = analytics.get_flood_risk_trend.__wrapped__(analytics, session=mock_session)

        assert isinstance(result, list)
        assert len(result) == 2  # Two days

    @patch("app.services.dashboard_analytics.get_router")
    def test_daily_data_structure(self, mock_get_router, mock_session, mock_risk_trend_results):
        """Test structure of daily data."""
        mock_get_router.return_value = MagicMock()
        analytics = DashboardAnalytics()

        mock_session.execute.return_value = MagicMock(fetchall=Mock(return_value=mock_risk_trend_results))

        result = analytics.get_flood_risk_trend.__wrapped__(analytics, session=mock_session)

        for day_data in result:
            assert "date" in day_data
            assert "safe" in day_data
            assert "alert" in day_data
            assert "critical" in day_data

    @patch("app.services.dashboard_analytics.get_router")
    def test_risk_level_counts(self, mock_get_router, mock_session, mock_risk_trend_results):
        """Test that risk level counts are correct."""
        mock_get_router.return_value = MagicMock()
        analytics = DashboardAnalytics()

        mock_session.execute.return_value = MagicMock(fetchall=Mock(return_value=mock_risk_trend_results))

        result = analytics.get_flood_risk_trend.__wrapped__(analytics, session=mock_session)

        # Find today's data
        today = datetime.now(timezone.utc).date().isoformat()
        today_data = next((d for d in result if d["date"] == today), None)

        if today_data:
            assert today_data["safe"] == 50
            assert today_data["alert"] == 30
            assert today_data["critical"] == 10

    @patch("app.services.dashboard_analytics.get_router")
    def test_custom_days_parameter(self, mock_get_router, mock_session):
        """Test custom days parameter."""
        mock_get_router.return_value = MagicMock()
        analytics = DashboardAnalytics()

        mock_session.execute.return_value = MagicMock(fetchall=Mock(return_value=[]))

        analytics.get_flood_risk_trend.__wrapped__(analytics, session=mock_session, days=14)

        mock_session.execute.assert_called_once()

    @patch("app.services.dashboard_analytics.get_router")
    def test_handles_empty_results(self, mock_get_router, mock_session):
        """Test handling of empty results."""
        mock_get_router.return_value = MagicMock()
        analytics = DashboardAnalytics()

        mock_session.execute.return_value = MagicMock(fetchall=Mock(return_value=[]))

        result = analytics.get_flood_risk_trend.__wrapped__(analytics, session=mock_session)

        assert result == []


# =============================================================================
# get_partition_stats Tests
# =============================================================================


class TestGetPartitionStats:
    """Tests for get_partition_stats method."""

    @patch("app.services.dashboard_analytics.get_router")
    def test_returns_partition_list(self, mock_get_router, mock_session):
        """Test that partition stats returns list."""
        mock_get_router.return_value = MagicMock()
        analytics = DashboardAnalytics()

        mock_partition_data = [
            ("weather_data_2024_01", 10000, "100 MB", "20 MB", "120 MB"),
            ("weather_data_2024_02", 8000, "80 MB", "16 MB", "96 MB"),
        ]
        mock_session.execute.return_value = MagicMock(fetchall=Mock(return_value=mock_partition_data))

        result = analytics.get_partition_stats.__wrapped__(analytics, session=mock_session)

        assert isinstance(result, list)
        assert len(result) == 2

    @patch("app.services.dashboard_analytics.get_router")
    def test_partition_structure(self, mock_get_router, mock_session):
        """Test structure of partition data."""
        mock_get_router.return_value = MagicMock()
        analytics = DashboardAnalytics()

        mock_partition_data = [("weather_data_2024_01", 10000, "100 MB", "20 MB", "120 MB")]
        mock_session.execute.return_value = MagicMock(fetchall=Mock(return_value=mock_partition_data))

        result = analytics.get_partition_stats.__wrapped__(analytics, session=mock_session)

        partition = result[0]
        assert partition["partition_name"] == "weather_data_2024_01"
        assert partition["row_count"] == 10000
        assert partition["table_size"] == "100 MB"
        assert partition["index_size"] == "20 MB"
        assert partition["total_size"] == "120 MB"

    @patch("app.services.dashboard_analytics.get_router")
    def test_custom_table_name(self, mock_get_router, mock_session):
        """Test custom table name parameter."""
        mock_get_router.return_value = MagicMock()
        analytics = DashboardAnalytics()

        mock_session.execute.return_value = MagicMock(fetchall=Mock(return_value=[]))

        analytics.get_partition_stats.__wrapped__(analytics, session=mock_session, table_name="predictions")

        call_args = mock_session.execute.call_args
        assert "predictions" in str(call_args)

    @patch("app.services.dashboard_analytics.get_router")
    def test_handles_database_error(self, mock_get_router, mock_session):
        """Test handling of database errors."""
        mock_get_router.return_value = MagicMock()
        analytics = DashboardAnalytics()

        mock_session.execute.side_effect = Exception("Database error")

        result = analytics.get_partition_stats.__wrapped__(analytics, session=mock_session)

        assert result == []


# =============================================================================
# get_performance_metrics Tests
# =============================================================================


class TestGetPerformanceMetrics:
    """Tests for get_performance_metrics method."""

    @patch("app.services.dashboard_analytics.get_router")
    def test_returns_complete_metrics(self, mock_get_router, mock_session, mock_performance_metrics):
        """Test that performance metrics returns complete structure."""
        mock_get_router.return_value = MagicMock()
        analytics = DashboardAnalytics()

        mock_session.execute.return_value = MagicMock(fetchone=Mock(return_value=mock_performance_metrics))

        result = analytics.get_performance_metrics.__wrapped__(analytics, session=mock_session)

        assert "period_hours" in result
        assert "total_requests" in result
        assert "avg_response_time_ms" in result
        assert "p50_response_time_ms" in result
        assert "p95_response_time_ms" in result
        assert "p99_response_time_ms" in result
        assert "error_count" in result
        assert "success_count" in result
        assert "error_rate" in result
        assert "generated_at" in result

    @patch("app.services.dashboard_analytics.get_router")
    def test_metrics_values(self, mock_get_router, mock_session, mock_performance_metrics):
        """Test metrics values are correct."""
        mock_get_router.return_value = MagicMock()
        analytics = DashboardAnalytics()

        mock_session.execute.return_value = MagicMock(fetchone=Mock(return_value=mock_performance_metrics))

        result = analytics.get_performance_metrics.__wrapped__(analytics, session=mock_session)

        assert result["total_requests"] == 1000
        assert result["avg_response_time_ms"] == 45.5
        assert result["p50_response_time_ms"] == 30.0
        assert result["p95_response_time_ms"] == 100.0
        assert result["p99_response_time_ms"] == 200.0
        assert result["error_count"] == 10
        assert result["success_count"] == 990
        assert result["error_rate"] == 1.0  # 10/1000 * 100 = 1.0%

    @patch("app.services.dashboard_analytics.get_router")
    def test_custom_hours_parameter(self, mock_get_router, mock_session, mock_performance_metrics):
        """Test custom hours parameter."""
        mock_get_router.return_value = MagicMock()
        analytics = DashboardAnalytics()

        mock_session.execute.return_value = MagicMock(fetchone=Mock(return_value=mock_performance_metrics))

        result = analytics.get_performance_metrics.__wrapped__(analytics, session=mock_session, hours=48)

        assert result["period_hours"] == 48

    @patch("app.services.dashboard_analytics.get_router")
    def test_handles_null_values(self, mock_get_router, mock_session):
        """Test handling of NULL values."""
        mock_get_router.return_value = MagicMock()
        analytics = DashboardAnalytics()

        null_metrics = (0, None, None, None, None, None, None)
        mock_session.execute.return_value = MagicMock(fetchone=Mock(return_value=null_metrics))

        result = analytics.get_performance_metrics.__wrapped__(analytics, session=mock_session)

        assert result["total_requests"] == 0
        assert result["avg_response_time_ms"] is None
        assert result["error_rate"] == 0.0  # No errors out of no requests

    @patch("app.services.dashboard_analytics.get_router")
    def test_error_rate_calculation(self, mock_get_router, mock_session):
        """Test error rate calculation."""
        mock_get_router.return_value = MagicMock()
        analytics = DashboardAnalytics()

        # 50 errors out of 200 requests = 25%
        metrics_with_errors = (200, 50.0, 40.0, 80.0, 150.0, 50, 150)
        mock_session.execute.return_value = MagicMock(fetchone=Mock(return_value=metrics_with_errors))

        result = analytics.get_performance_metrics.__wrapped__(analytics, session=mock_session)

        assert result["error_rate"] == 25.0


# =============================================================================
# Integration-like Tests
# =============================================================================


class TestDashboardAnalyticsIntegration:
    """Integration-style tests for DashboardAnalytics."""

    @patch("app.services.dashboard_analytics.get_router")
    def test_multiple_methods_same_instance(
        self, mock_get_router, mock_session, mock_weather_stats, mock_prediction_stats, mock_alert_stats
    ):
        """Test calling multiple methods on same instance."""
        mock_get_router.return_value = MagicMock()
        analytics = DashboardAnalytics()

        # Setup for get_dashboard_stats
        mock_session.execute.side_effect = [
            MagicMock(fetchone=Mock(return_value=mock_weather_stats)),
            MagicMock(fetchone=Mock(return_value=mock_prediction_stats)),
            MagicMock(fetchone=Mock(return_value=mock_alert_stats)),
            MagicMock(fetchall=Mock(return_value=[])),  # For time series
            MagicMock(fetchall=Mock(return_value=[])),  # For risk trend
        ]

        # Call multiple methods
        stats = analytics.get_dashboard_stats.__wrapped__(analytics, session=mock_session)
        time_series = analytics.get_time_series_data.__wrapped__(analytics, session=mock_session)
        risk_trend = analytics.get_flood_risk_trend.__wrapped__(analytics, session=mock_session)

        assert stats is not None
        assert time_series is not None
        assert risk_trend is not None

    @patch("app.services.dashboard_analytics.get_router")
    def test_stats_include_timestamp(
        self, mock_get_router, mock_session, mock_weather_stats, mock_prediction_stats, mock_alert_stats
    ):
        """Test that stats include generation timestamp."""
        mock_get_router.return_value = MagicMock()
        analytics = DashboardAnalytics()

        mock_session.execute.side_effect = [
            MagicMock(fetchone=Mock(return_value=mock_weather_stats)),
            MagicMock(fetchone=Mock(return_value=mock_prediction_stats)),
            MagicMock(fetchone=Mock(return_value=mock_alert_stats)),
        ]

        result = analytics.get_dashboard_stats.__wrapped__(analytics, session=mock_session)

        assert "generated_at" in result
        # Verify it's a valid ISO timestamp
        timestamp = result["generated_at"]
        assert "T" in timestamp


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
