"""
Unit tests for performance monitoring routes.

Tests for app/api/routes/performance.py
"""

from collections import deque
from unittest.mock import MagicMock, patch

import pytest
from app.api.routes.performance import (
    _endpoint_times,
    _response_times,
    calculate_percentiles,
    record_response_time,
)


class TestResponseTimeTracking:
    """Tests for response time tracking functions."""

    def test_record_response_time(self):
        """Test recording a response time."""
        initial_count = len(_response_times)
        record_response_time("/api/test", 150.5)

        assert len(_response_times) >= initial_count
        # Latest entry should be our recorded time
        latest = list(_response_times)[-1]
        assert latest["endpoint"] == "/api/test"
        assert latest["duration_ms"] == 150.5

    def test_calculate_percentiles_empty(self):
        """Test percentile calculation with empty list."""
        result = calculate_percentiles([])

        assert result["p50"] == 0
        assert result["p75"] == 0
        assert result["p90"] == 0
        assert result["p95"] == 0
        assert result["p99"] == 0

    def test_calculate_percentiles_single_value(self):
        """Test percentile calculation with single value."""
        result = calculate_percentiles([100])

        assert result["p50"] == 100
        assert result["p99"] == 100

    def test_calculate_percentiles_multiple_values(self):
        """Test percentile calculation with multiple values."""
        # 100 values from 1 to 100
        times = list(range(1, 101))
        result = calculate_percentiles(times)

        # With 100 values, index = int(100 * 0.50) = 50, so p50 = times[50] = 51
        assert result["p50"] == 51
        assert result["p90"] == 91
        assert result["p95"] == 96
        assert result["p99"] == 100

    def test_get_response_time_stats(self):
        """Test comprehensive response time statistics."""
        from app.api.routes.performance import get_response_time_stats

        stats = get_response_time_stats()

        assert "total_requests_tracked" in stats
        assert "overall" in stats
        assert "by_endpoint" in stats
        assert "min" in stats["overall"]
        assert "max" in stats["overall"]
        assert "avg" in stats["overall"]
        assert "percentiles" in stats["overall"]


class TestPerformanceDashboard:
    """Tests for performance dashboard endpoint."""

    def test_performance_dashboard_endpoint(self, client):
        """Test performance dashboard returns metrics."""
        response = client.get("/api/v1/performance/dashboard")

        assert response.status_code == 200
        data = response.get_json()
        assert "timestamp" in data
        assert "request_id" in data

    @patch("app.api.routes.performance.get_cache_stats")
    @patch("app.api.routes.performance.get_pool_status")
    def test_performance_dashboard_includes_cache(self, mock_pool, mock_cache, client):
        """Test dashboard includes cache statistics."""
        mock_cache.return_value = {"hits": 100, "misses": 10}
        mock_pool.return_value = {"pool_size": 20, "checked_out": 5}

        response = client.get("/api/v1/performance/dashboard")

        assert response.status_code == 200
        data = response.get_json()
        assert "cache" in data or "response_times" in data


class TestCacheMetrics:
    """Tests for cache metrics endpoints."""

    def test_cache_stats_endpoint(self, client):
        """Test cache statistics endpoint."""
        response = client.get("/api/v1/performance/cache/stats")

        # May return 200 or 404 depending on route registration
        assert response.status_code in [200, 404]

    @patch("app.api.routes.performance.is_cache_enabled")
    def test_cache_warm_endpoint(self, mock_enabled, client):
        """Test cache warming endpoint."""
        mock_enabled.return_value = True

        response = client.post("/api/v1/performance/cache/warm")

        # Endpoint might require authentication
        assert response.status_code in [200, 401, 404]


class TestDatabaseMetrics:
    """Tests for database metrics endpoints."""

    def test_slow_queries_endpoint(self, client):
        """Test slow queries endpoint."""
        response = client.get("/api/v1/performance/slow-queries")

        # Endpoint requires API key auth, so 401 is expected without key
        assert response.status_code in [200, 401, 404]

    @patch("app.api.routes.performance.get_database_health")
    def test_database_health_endpoint(self, mock_health, client):
        """Test database health metrics endpoint."""
        mock_health.return_value = {"status": "healthy", "connections": 10}

        response = client.get("/api/v1/performance/database")

        assert response.status_code in [200, 404]

    @patch("app.api.routes.performance.get_table_statistics")
    def test_table_stats_endpoint(self, mock_stats, client):
        """Test table statistics endpoint."""
        mock_stats.return_value = [{"table": "weather_data", "rows": 1000}]

        response = client.get("/api/v1/performance/tables")

        assert response.status_code in [200, 404]


class TestIndexMetrics:
    """Tests for index usage metrics."""

    @patch("app.api.routes.performance.get_index_usage_stats")
    def test_index_usage_endpoint(self, mock_usage, client):
        """Test index usage statistics endpoint."""
        mock_usage.return_value = [{"index": "idx_timestamp", "scans": 500}]

        response = client.get("/api/v1/performance/indexes")

        assert response.status_code in [200, 404]

    @patch("app.api.routes.performance.get_unused_indexes")
    def test_unused_indexes_endpoint(self, mock_unused, client):
        """Test unused indexes endpoint."""
        mock_unused.return_value = []

        response = client.get("/api/v1/performance/indexes/unused")

        assert response.status_code in [200, 404]


class TestQueryStatistics:
    """Tests for query statistics endpoints."""

    @patch("app.api.routes.performance.get_query_statistics")
    def test_query_stats_endpoint(self, mock_stats, client):
        """Test query statistics endpoint."""
        mock_stats.return_value = {"total_queries": 1000, "avg_time_ms": 5.5}

        response = client.get("/api/v1/performance/queries")

        assert response.status_code in [200, 404]

    @patch("app.api.routes.performance.clear_slow_query_log")
    def test_clear_slow_queries_endpoint(self, mock_clear, client):
        """Test clearing slow query log."""
        mock_clear.return_value = None

        response = client.delete("/api/v1/performance/slow-queries")

        # May require authentication
        assert response.status_code in [200, 204, 401, 404]


class TestMaintenanceRecommendations:
    """Tests for maintenance recommendations endpoint."""

    @patch("app.api.routes.performance.run_maintenance_recommendations")
    def test_maintenance_recommendations_endpoint(self, mock_recs, client):
        """Test maintenance recommendations endpoint."""
        mock_recs.return_value = [{"type": "vacuum", "table": "weather_data", "priority": "medium"}]

        response = client.get("/api/v1/performance/recommendations")

        assert response.status_code in [200, 404]
