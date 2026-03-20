"""
Integration tests for DLQ (Dead Letter Queue) management endpoints.

Tests the admin monitoring DLQ endpoints:
- GET  /api/v1/admin/monitoring/celery/dlq       — list DLQ entries
- POST /api/v1/admin/monitoring/celery/dlq/replay — replay oldest entry
- DELETE /api/v1/admin/monitoring/celery/dlq      — clear all entries
"""

import json
from unittest.mock import MagicMock, patch

import pytest

API_PREFIX = "/api/v1/admin/monitoring/celery/dlq"


@pytest.fixture
def admin_token(app):
    """Generate a JWT token with admin role."""
    from app.core import security

    with app.app_context():
        return security.create_access_token(user_id=1, email="admin@test.com", role="admin")


@pytest.fixture
def user_token(app):
    """Generate a JWT token with regular user role."""
    from app.core import security

    with app.app_context():
        return security.create_access_token(user_id=2, email="user@test.com", role="user")


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class TestDLQList:
    """Tests for GET /celery/dlq endpoint."""

    def test_list_dlq_entries_empty(self, client, admin_token):
        """Admin can list DLQ entries when queue is empty."""
        with patch("app.api.routes.admin_monitoring.get_dlq_entries", return_value=[]):
            with patch("app.api.routes.admin_monitoring.get_dlq_count", return_value=0):
                resp = client.get(API_PREFIX, headers=_auth_header(admin_token))
                assert resp.status_code == 200
                data = resp.get_json()
                assert data["success"] is True
                assert data["data"]["total"] == 0
                assert data["data"]["entries"] == []

    def test_list_dlq_entries_with_data(self, client, admin_token):
        """Admin can list DLQ entries with data."""
        entries = [
            {"task_name": "fetch_weather", "task_id": "abc-123", "error": "Timeout"},
            {"task_name": "send_alert", "task_id": "def-456", "error": "SMTP down"},
        ]
        with patch("app.api.routes.admin_monitoring.get_dlq_entries", return_value=entries):
            with patch("app.api.routes.admin_monitoring.get_dlq_count", return_value=2):
                resp = client.get(API_PREFIX, headers=_auth_header(admin_token))
                assert resp.status_code == 200
                data = resp.get_json()
                assert data["data"]["total"] == 2
                assert len(data["data"]["entries"]) == 2

    def test_list_dlq_custom_limit(self, client, admin_token):
        """Admin can pass limit query parameter."""
        with patch("app.api.routes.admin_monitoring.get_dlq_entries", return_value=[]) as mock:
            with patch("app.api.routes.admin_monitoring.get_dlq_count", return_value=0):
                resp = client.get(f"{API_PREFIX}?limit=10", headers=_auth_header(admin_token))
                assert resp.status_code == 200
                mock.assert_called_once_with(limit=10)

    def test_list_dlq_requires_admin(self, client, user_token):
        """Regular users cannot access DLQ endpoints."""
        resp = client.get(API_PREFIX, headers=_auth_header(user_token))
        assert resp.status_code == 403

    def test_list_dlq_requires_auth(self, client):
        """Unauthenticated requests are rejected."""
        resp = client.get(API_PREFIX)
        assert resp.status_code == 401


class TestDLQReplay:
    """Tests for POST /celery/dlq/replay endpoint."""

    def test_replay_dlq_entry_success(self, client, admin_token):
        """Admin can replay an entry from the DLQ."""
        result = {"replayed": True, "task": {"task_name": "fetch_weather", "task_id": "abc-123"}}
        with patch("app.api.routes.admin_monitoring.replay_dlq_entry", return_value=result):
            resp = client.post(f"{API_PREFIX}/replay", headers=_auth_header(admin_token))
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["success"] is True
            assert data["data"]["replayed"] is True

    def test_replay_dlq_empty(self, client, admin_token):
        """Replay returns graceful response when DLQ is empty."""
        result = {"replayed": False, "reason": "DLQ is empty"}
        with patch("app.api.routes.admin_monitoring.replay_dlq_entry", return_value=result):
            resp = client.post(f"{API_PREFIX}/replay", headers=_auth_header(admin_token))
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["data"]["replayed"] is False

    def test_replay_dlq_requires_admin(self, client, user_token):
        """Regular users cannot replay DLQ entries."""
        resp = client.post(f"{API_PREFIX}/replay", headers=_auth_header(user_token))
        assert resp.status_code == 403


class TestDLQClear:
    """Tests for DELETE /celery/dlq endpoint."""

    def test_clear_dlq_success(self, client, admin_token):
        """Admin can clear the DLQ."""
        with patch("app.api.routes.admin_monitoring.clear_dlq", return_value=5):
            resp = client.delete(API_PREFIX, headers=_auth_header(admin_token))
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["success"] is True
            assert data["data"]["cleared"] == 5

    def test_clear_dlq_empty(self, client, admin_token):
        """Clearing an empty DLQ returns 0."""
        with patch("app.api.routes.admin_monitoring.clear_dlq", return_value=0):
            resp = client.delete(API_PREFIX, headers=_auth_header(admin_token))
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["data"]["cleared"] == 0

    def test_clear_dlq_requires_admin(self, client, user_token):
        """Regular users cannot clear the DLQ."""
        resp = client.delete(API_PREFIX, headers=_auth_header(user_token))
        assert resp.status_code == 403
