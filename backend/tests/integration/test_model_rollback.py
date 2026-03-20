"""
Integration tests for model rollback validation.

Tests POST /api/v1/admin/models/rollback:
- Validates model file existence
- Validates model has predict method
- Rejects rollback with invalid version
- Requires admin role
"""

import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

API_PREFIX = "/api/v1/admin/models/rollback"


@pytest.fixture
def admin_token(app):
    """Generate a JWT token with admin role."""
    from app.core import security

    with app.app_context():
        return security.create_access_token(user_id=1, email="admin@test.com", role="admin")


@pytest.fixture
def user_token(app):
    """Generate a JWT token with user role."""
    from app.core import security

    with app.app_context():
        return security.create_access_token(user_id=2, email="user@test.com", role="user")


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


class TestModelRollback:
    """Tests for POST /admin/models/rollback endpoint."""

    def test_rollback_requires_version(self, client, admin_token):
        """Missing version field returns 400."""
        resp = client.post(
            API_PREFIX,
            headers=_auth_header(admin_token),
            json={"reason": "no version given"},
        )
        assert resp.status_code == 400

    def test_rollback_missing_file(self, client, admin_token):
        """Rollback to nonexistent model file returns 404."""
        with patch("app.api.routes.admin_models.get_model_metadata", return_value={"version": "v6"}):
            resp = client.post(
                API_PREFIX,
                headers=_auth_header(admin_token),
                json={"version": "v999", "reason": "test"},
            )
            assert resp.status_code == 404

    def test_rollback_invalid_model(self, client, admin_token):
        """Rollback to a file that isn't a valid model returns 400."""
        # Create a temporary file that will fail joblib.load
        with patch("app.api.routes.admin_models.get_model_metadata", return_value={"version": "v6"}):
            with patch("os.path.exists", return_value=True):
                with patch("joblib.load", side_effect=Exception("corrupt file")):
                    resp = client.post(
                        API_PREFIX,
                        headers=_auth_header(admin_token),
                        json={"version": "v_corrupt", "reason": "test"},
                    )
                    assert resp.status_code == 400

    def test_rollback_model_no_predict(self, client, admin_token):
        """Rollback to a model without predict method returns 400."""
        fake_model = MagicMock(spec=[])  # No predict or predict_proba
        del fake_model.predict
        del fake_model.predict_proba

        with patch("app.api.routes.admin_models.get_model_metadata", return_value={"version": "v6"}):
            with patch("os.path.exists", return_value=True):
                with patch("joblib.load", return_value=fake_model):
                    resp = client.post(
                        API_PREFIX,
                        headers=_auth_header(admin_token),
                        json={"version": "v_noop", "reason": "test"},
                    )
                    assert resp.status_code == 400

    def test_rollback_success(self, client, admin_token):
        """Successful rollback returns version info."""
        fake_model = MagicMock()
        fake_model.predict = MagicMock()

        with patch("app.api.routes.admin_models.get_model_metadata", return_value={"version": "v6"}):
            with patch("os.path.exists", return_value=True):
                with patch("joblib.load", return_value=fake_model):
                    with patch.object(MagicMock, "load_model"):
                        # Patch ModelLoader to avoid file system interaction
                        mock_loader = MagicMock()
                        with patch("app.api.routes.admin_models.ModelLoader", return_value=mock_loader):
                            resp = client.post(
                                API_PREFIX,
                                headers=_auth_header(admin_token),
                                json={"version": "v5", "reason": "accuracy regression"},
                            )
                            assert resp.status_code == 200
                            data = resp.get_json()
                            assert data["success"] is True
                            assert data["data"]["current_version"] == "v5"
                            assert data["data"]["previous_version"] == "v6"

    def test_rollback_requires_admin(self, client, user_token):
        """Regular users cannot trigger model rollback."""
        resp = client.post(
            API_PREFIX,
            headers=_auth_header(user_token),
            json={"version": "v5", "reason": "test"},
        )
        assert resp.status_code == 403

    def test_rollback_requires_auth(self, client):
        """Unauthenticated requests are rejected."""
        resp = client.post(
            API_PREFIX,
            content_type="application/json",
            data='{"version": "v5"}',
        )
        assert resp.status_code == 401
