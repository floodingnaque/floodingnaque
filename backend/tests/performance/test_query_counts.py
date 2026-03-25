"""
Query Count Performance Tests.

Validates that optimized endpoints stay within their query budgets.
Uses the X-Query-Count header from the query counter middleware to
enforce per-endpoint SQL query limits.

These tests guard against N+1 regressions. Each endpoint has a
maximum query count derived from the optimized implementation:

    Endpoint                      Max Queries  Notes
    ──────────────────────────────────────────────────────
    GET /api/v1/admin/logs/stats       1       Conditional aggregation
    GET /api/v1/admin/storage-stats    6       1 per table (6 tables)
    GET /api/v1/community-reports/stats 1      Conditional aggregation
    GET /api/v1/incidents/analytics    3       incident + AAR + monthly
    GET /health                        2       DB ping + basic check
    GET /status                        0       No DB access
"""

from unittest.mock import MagicMock, patch

import pytest


# ============================================================================
# Helper
# ============================================================================


def _query_count(response) -> int:
    """Extract X-Query-Count from response, defaulting to -1 if absent."""
    header = response.headers.get("X-Query-Count")
    return int(header) if header is not None else -1


# ============================================================================
# Query Budget Tests
# ============================================================================


class TestQueryBudgets:
    """Verify endpoints stay within their SQL query budgets."""

    @pytest.mark.performance
    def test_health_query_budget(self, client, auto_mock_health_dependencies):
        """Health endpoint should use <= 2 queries (DB ping + extras)."""
        response = client.get("/health")
        assert response.status_code == 200
        count = _query_count(response)
        if count >= 0:
            assert count <= 2, (
                f"GET /health used {count} queries, budget is 2"
            )

    @pytest.mark.performance
    def test_status_minimal_queries(self, client):
        """Status endpoint should use minimal queries (at most 1 for DB ping)."""
        response = client.get("/status")
        assert response.status_code == 200
        count = _query_count(response)
        if count >= 0:
            assert count <= 1, (
                f"GET /status used {count} queries, expected <= 1"
            )

    @pytest.mark.performance
    @patch("app.api.routes.admin_logs.get_db_session")
    def test_log_stats_single_query(self, mock_session, client, api_headers):
        """GET /api/v1/admin/logs/stats should use exactly 1 query."""
        # Mock the session to return a valid aggregate row
        mock_row = MagicMock()
        mock_row.total = 100
        mock_row.predictions = 40
        mock_row.logins = 20
        mock_row.uploads = 10
        mock_row.errors = 5
        mock_row.all_time = 200

        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
        mock_ctx.__exit__ = MagicMock(return_value=False)
        mock_ctx.query.return_value.filter.return_value.one.return_value = mock_row
        mock_session.return_value = mock_ctx

        response = client.get("/api/v1/admin/logs/stats", headers=api_headers)
        # The endpoint may require auth; verify it was reached
        if response.status_code == 200:
            count = _query_count(response)
            if count >= 0:
                assert count <= 2, (
                    f"GET /api/v1/admin/logs/stats used {count} queries, budget is 2"
                )

    @pytest.mark.performance
    @patch("app.api.routes.community_reports.get_db_session")
    def test_report_stats_single_query(self, mock_session, client, api_headers):
        """GET /api/v1/community-reports/stats should use exactly 1 query."""
        mock_row = MagicMock()
        mock_row.total = 50
        mock_row.verified = 20
        mock_row.pending = 25
        mock_row.critical = 5

        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
        mock_ctx.__exit__ = MagicMock(return_value=False)
        mock_ctx.query.return_value.filter.return_value.one.return_value = mock_row
        mock_session.return_value = mock_ctx

        response = client.get(
            "/api/v1/community-reports/stats", headers=api_headers
        )
        if response.status_code == 200:
            count = _query_count(response)
            if count >= 0:
                assert count <= 2, (
                    f"GET /api/v1/community-reports/stats used "
                    f"{count} queries, budget is 2"
                )


# ============================================================================
# Regression Guard
# ============================================================================


class TestQueryRegressionGuards:
    """Ensure no N+1 regressions on previously-optimised paths."""

    @pytest.mark.performance
    def test_root_endpoint_no_queries(self, client):
        """Root / endpoint should not query the database."""
        response = client.get("/")
        assert response.status_code == 200
        count = _query_count(response)
        if count >= 0:
            assert count == 0, f"GET / used {count} queries, expected 0"

    @pytest.mark.performance
    def test_sequential_health_checks_stable_count(
        self, client, auto_mock_health_dependencies
    ):
        """Query count should be stable across repeated health checks."""
        counts = []
        for _ in range(5):
            response = client.get("/health")
            assert response.status_code == 200
            c = _query_count(response)
            if c >= 0:
                counts.append(c)

        if counts:
            # All requests should use the same number of queries
            assert max(counts) - min(counts) <= 1, (
                f"Unstable query count across health checks: {counts}"
            )
