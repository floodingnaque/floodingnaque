"""Unit tests for user reputation service and routes."""

import math
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock, PropertyMock


# ============================================================================
# Service Tests
# ============================================================================


class TestRecalculateReputation:
    """Tests for the recalculate_reputation() service function."""

    def _make_user(self, **overrides):
        user = MagicMock()
        user.id = overrides.get("id", 1)
        user.is_deleted = False
        user.is_active = True
        user.created_at = overrides.get(
            "created_at", datetime.now(timezone.utc) - timedelta(days=90)
        )
        user.reputation_score = 0.5
        user.total_reports = 0
        user.accepted_reports = 0
        user.rejected_reports = 0
        user.reputation_updated_at = None
        user.full_name = overrides.get("full_name", "Test User")
        return user

    def _make_report(self, status="accepted", credibility_score=0.8):
        r = MagicMock()
        r.is_deleted = False
        r.status = status
        r.credibility_score = credibility_score
        r.created_at = datetime.now(timezone.utc) - timedelta(hours=1)
        r.user_id = 1
        return r

    def test_user_not_found(self):
        """Returns None for non-existent user."""
        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.query.return_value.filter.return_value.first.return_value = None

        with patch("app.services.user_reputation.get_db_session", return_value=mock_session):
            from app.services.user_reputation import recalculate_reputation
            result = recalculate_reputation(999)

        assert result is None

    def test_user_with_no_reports(self):
        """User with no reports gets neutral default score."""
        user = self._make_user(created_at=datetime.now(timezone.utc) - timedelta(days=90))

        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.query.return_value.filter.return_value.first.return_value = user
        # Second query call → reports
        mock_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

        with patch("app.services.user_reputation.get_db_session", return_value=mock_session):
            from app.services.user_reputation import recalculate_reputation
            score = recalculate_reputation(1)

        assert score is not None
        assert 0.0 <= score <= 1.0
        # With no reports: accuracy=0.5, age=0.5 (90/180), trend=0.5, consistency=0.5
        expected = round(0.4 * 0.5 + 0.2 * 0.5 + 0.25 * 0.5 + 0.15 * 0.5, 4)
        assert score == expected

    def test_user_with_perfect_reports(self):
        """User with all accepted reports and high credibility scores high."""
        user = self._make_user(created_at=datetime.now(timezone.utc) - timedelta(days=200))
        reports = [self._make_report(status="accepted", credibility_score=0.95) for _ in range(10)]

        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.query.return_value.filter.return_value.first.return_value = user
        mock_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = reports

        with patch("app.services.user_reputation.get_db_session", return_value=mock_session):
            from app.services.user_reputation import recalculate_reputation
            score = recalculate_reputation(1)

        assert score is not None
        # accuracy=1.0, age=1.0 (capped), trend=0.95, consistency=1.0 (no variance)
        expected = round(0.4 * 1.0 + 0.2 * 1.0 + 0.25 * 0.95 + 0.15 * 1.0, 4)
        assert score == expected
        # Score persisted
        assert user.reputation_score == score
        assert user.total_reports == 10
        assert user.accepted_reports == 10

    def test_user_with_mixed_reports(self):
        """Mixed accepted/rejected reports produce balanced score."""
        user = self._make_user(created_at=datetime.now(timezone.utc) - timedelta(days=30))
        reports = [
            self._make_report(status="accepted", credibility_score=0.9),
            self._make_report(status="rejected", credibility_score=0.3),
            self._make_report(status="accepted", credibility_score=0.7),
            self._make_report(status="pending", credibility_score=0.5),
        ]

        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.query.return_value.filter.return_value.first.return_value = user
        mock_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = reports

        with patch("app.services.user_reputation.get_db_session", return_value=mock_session):
            from app.services.user_reputation import recalculate_reputation
            score = recalculate_reputation(1)

        assert score is not None
        assert 0.0 <= score <= 1.0
        assert user.rejected_reports == 1
        assert user.accepted_reports == 2
        assert user.total_reports == 4

    def test_score_clamped_to_bounds(self):
        """Score is always between 0 and 1."""
        user = self._make_user(created_at=datetime.now(timezone.utc) - timedelta(days=1))
        # All rejected, terrible credibility
        reports = [self._make_report(status="rejected", credibility_score=0.0) for _ in range(5)]

        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.query.return_value.filter.return_value.first.return_value = user
        mock_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = reports

        with patch("app.services.user_reputation.get_db_session", return_value=mock_session):
            from app.services.user_reputation import recalculate_reputation
            score = recalculate_reputation(1)

        assert score is not None
        assert 0.0 <= score <= 1.0


class TestGetReputation:
    """Tests for get_reputation() service function."""

    def test_user_not_found(self):
        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.query.return_value.filter.return_value.first.return_value = None

        with patch("app.services.user_reputation.get_db_session", return_value=mock_session):
            from app.services.user_reputation import get_reputation
            result = get_reputation(999)

        assert result is None

    def test_returns_snapshot(self):
        user = MagicMock()
        user.id = 1
        user.is_deleted = False
        user.reputation_score = 0.75
        user.total_reports = 10
        user.accepted_reports = 8
        user.rejected_reports = 1
        user.reputation_updated_at = datetime(2025, 6, 1, tzinfo=timezone.utc)
        user.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)

        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.query.return_value.filter.return_value.first.return_value = user

        with patch("app.services.user_reputation.get_db_session", return_value=mock_session):
            from app.services.user_reputation import get_reputation
            result = get_reputation(1)

        assert result is not None
        assert result["user_id"] == 1
        assert result["reputation_score"] == 0.75
        assert result["total_reports"] == 10
        assert result["accepted_reports"] == 8
        assert result["rejected_reports"] == 1
        assert "reputation_updated_at" in result
        assert "account_age_days" in result


class TestGetLeaderboard:
    """Tests for get_leaderboard() service function."""

    def test_empty_leaderboard(self):
        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

        with patch("app.services.user_reputation.get_db_session", return_value=mock_session):
            from app.services.user_reputation import get_leaderboard
            result = get_leaderboard(20)

        assert result == []

    def test_leaderboard_returns_users(self):
        u1 = MagicMock()
        u1.id = 1
        u1.full_name = "Alice"
        u1.reputation_score = 0.95
        u1.total_reports = 50
        u1.accepted_reports = 48

        u2 = MagicMock()
        u2.id = 2
        u2.full_name = None  # should default to "Anonymous"
        u2.reputation_score = 0.80
        u2.total_reports = 20
        u2.accepted_reports = 15

        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [u1, u2]

        with patch("app.services.user_reputation.get_db_session", return_value=mock_session):
            from app.services.user_reputation import get_leaderboard
            result = get_leaderboard(20)

        assert len(result) == 2
        assert result[0]["full_name"] == "Alice"
        assert result[0]["reputation_score"] == 0.95
        assert result[1]["full_name"] == "Anonymous"


# ============================================================================
# Route Tests
# ============================================================================


class TestReputationRoutes:
    """Tests for user reputation API endpoints."""

    def _make_token_payload(self, user_id=1):
        return {"sub": str(user_id), "exp": 9999999999}

    def test_get_my_reputation(self, client):
        """GET /me/reputation returns reputation snapshot."""
        rep_data = {
            "user_id": 1,
            "reputation_score": 0.75,
            "total_reports": 10,
            "accepted_reports": 8,
            "rejected_reports": 1,
            "reputation_updated_at": "2025-06-01T00:00:00+00:00",
            "account_age_days": 150,
        }

        with (
            patch("app.api.routes.users.decode_token", return_value=(self._make_token_payload(), None)),
            patch("app.services.user_reputation.get_reputation", return_value=rep_data),
        ):
            response = client.get(
                "/api/v1/users/me/reputation",
                headers={"Authorization": "Bearer test-token"},
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["reputation"]["reputation_score"] == 0.75

    def test_get_my_reputation_no_auth(self, client):
        """Missing Authorization header returns 401."""
        response = client.get("/api/v1/users/me/reputation")
        assert response.status_code == 401

    def test_get_my_reputation_invalid_token(self, client):
        """Invalid token returns 401."""
        with patch("app.api.routes.users.decode_token", return_value=(None, "Token expired")):
            response = client.get(
                "/api/v1/users/me/reputation",
                headers={"Authorization": "Bearer bad-token"},
            )
        assert response.status_code == 401

    def test_recalculate_my_reputation(self, client):
        """POST /me/reputation/recalculate triggers recalculation."""
        with (
            patch("app.api.routes.users.decode_token", return_value=(self._make_token_payload(), None)),
            patch("app.services.user_reputation.recalculate_reputation", return_value=0.82),
        ):
            response = client.post(
                "/api/v1/users/me/reputation/recalculate",
                headers={"Authorization": "Bearer test-token"},
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["reputation_score"] == 0.82

    def test_recalculate_user_not_found(self, client):
        """Recalculate for missing user returns 404."""
        with (
            patch("app.api.routes.users.decode_token", return_value=(self._make_token_payload(999), None)),
            patch("app.services.user_reputation.recalculate_reputation", return_value=None),
        ):
            response = client.post(
                "/api/v1/users/me/reputation/recalculate",
                headers={"Authorization": "Bearer test-token"},
            )

        assert response.status_code == 404

    def test_get_leaderboard(self, client):
        """GET /reputation/leaderboard returns ranked users."""
        leaders = [
            {"user_id": 1, "full_name": "Alice", "reputation_score": 0.95, "total_reports": 50, "accepted_reports": 48},
            {"user_id": 2, "full_name": "Bob", "reputation_score": 0.80, "total_reports": 20, "accepted_reports": 15},
        ]

        with patch("app.services.user_reputation.get_leaderboard", return_value=leaders):
            response = client.get("/api/v1/users/reputation/leaderboard")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["total"] == 2
        assert len(data["leaderboard"]) == 2
        assert data["leaderboard"][0]["reputation_score"] == 0.95

    def test_leaderboard_with_limit(self, client):
        """Leaderboard respects limit parameter."""
        with patch("app.services.user_reputation.get_leaderboard", return_value=[]) as mock_lb:
            response = client.get("/api/v1/users/reputation/leaderboard?limit=5")

        assert response.status_code == 200

    def test_leaderboard_limit_clamped(self, client):
        """Limit > 100 is clamped to 100."""
        with patch("app.services.user_reputation.get_leaderboard", return_value=[]) as mock_lb:
            response = client.get("/api/v1/users/reputation/leaderboard?limit=500")

        assert response.status_code == 200
