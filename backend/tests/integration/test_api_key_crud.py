"""
Integration tests for API Key CRUD endpoints.

Tests the API key lifecycle:
- POST   /api/v1/api-keys          — create a new key
- GET    /api/v1/api-keys          — list user's keys (masked)
- DELETE /api/v1/api-keys/<id>     — revoke a key
- POST   /api/v1/api-keys/<id>/rotate — rotate a key
"""

import json
from unittest.mock import patch

import pytest

API_PREFIX = "/api/v1/api-keys"


@pytest.fixture
def auth_token(app):
    """Generate a JWT token for an authenticated user."""
    from app.core import security

    with app.app_context():
        return security.create_access_token(user_id=1, email="user@test.com", role="user")


@pytest.fixture
def other_user_token(app):
    """Generate a JWT token for a different user."""
    from app.core import security

    with app.app_context():
        return security.create_access_token(user_id=2, email="other@test.com", role="user")


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


class TestCreateAPIKey:
    """Tests for POST /api-keys endpoint."""

    def test_create_api_key_success(self, client, auth_token):
        """User can create a new API key."""
        resp = client.post(
            API_PREFIX,
            headers=_auth_header(auth_token),
            json={"name": "My Test Key", "scopes": "predict"},
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["success"] is True
        assert "key" in data["data"]  # Raw key shown once
        assert data["data"]["prefix"] is not None
        assert data["data"]["name"] == "My Test Key"
        assert "predict" in data["data"]["scopes"]

    def test_create_api_key_with_expiry(self, client, auth_token):
        """User can create a key with expiration."""
        resp = client.post(
            API_PREFIX,
            headers=_auth_header(auth_token),
            json={"name": "Expiring Key", "scopes": "predict", "expires_in_days": 30},
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["data"]["expires_at"] is not None

    def test_create_api_key_multiple_scopes(self, client, auth_token):
        """User can create a key with multiple scopes."""
        resp = client.post(
            API_PREFIX,
            headers=_auth_header(auth_token),
            json={"name": "Multi Scope Key", "scopes": "predict,dashboard,alerts"},
        )
        assert resp.status_code == 201
        data = resp.get_json()
        scopes = data["data"]["scopes"]
        assert "predict" in scopes
        assert "dashboard" in scopes
        assert "alerts" in scopes

    def test_create_api_key_invalid_scope(self, client, auth_token):
        """Invalid scopes are rejected."""
        resp = client.post(
            API_PREFIX,
            headers=_auth_header(auth_token),
            json={"name": "Bad Key", "scopes": "invalid_scope"},
        )
        assert resp.status_code == 400

    def test_create_api_key_missing_name(self, client, auth_token):
        """Name is required."""
        resp = client.post(
            API_PREFIX,
            headers=_auth_header(auth_token),
            json={"scopes": "predict"},
        )
        assert resp.status_code == 400

    def test_create_api_key_invalid_expiry(self, client, auth_token):
        """Expiry days must be 1-365."""
        resp = client.post(
            API_PREFIX,
            headers=_auth_header(auth_token),
            json={"name": "Bad Expiry", "expires_in_days": 999},
        )
        assert resp.status_code == 400

    def test_create_api_key_requires_auth(self, client):
        """Unauthenticated requests are rejected."""
        resp = client.post(
            API_PREFIX,
            content_type="application/json",
            data=json.dumps({"name": "Test"}),
        )
        assert resp.status_code == 401


class TestListAPIKeys:
    """Tests for GET /api-keys endpoint."""

    def test_list_keys_empty(self, client, auth_token):
        """List returns empty when user has no keys."""
        resp = client.get(API_PREFIX, headers=_auth_header(auth_token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert isinstance(data["data"], list)

    def test_list_keys_after_creation(self, client, auth_token):
        """Listed keys do not include the raw key value."""
        # Create a key first
        client.post(
            API_PREFIX,
            headers=_auth_header(auth_token),
            json={"name": "Visible Key"},
        )

        resp = client.get(API_PREFIX, headers=_auth_header(auth_token))
        assert resp.status_code == 200
        data = resp.get_json()
        keys = data["data"]
        assert len(keys) >= 1
        # Raw key must NOT be in list responses
        for k in keys:
            assert "key" not in k

    def test_list_keys_isolation(self, client, auth_token, other_user_token):
        """Users only see their own keys."""
        # User 1 creates a key
        client.post(
            API_PREFIX,
            headers=_auth_header(auth_token),
            json={"name": "User1 Key"},
        )

        # User 2 should see an empty list
        resp = client.get(API_PREFIX, headers=_auth_header(other_user_token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["data"]) == 0


class TestRevokeAPIKey:
    """Tests for DELETE /api-keys/<id> endpoint."""

    def test_revoke_key_success(self, client, auth_token):
        """Owner can revoke their key."""
        create_resp = client.post(
            API_PREFIX,
            headers=_auth_header(auth_token),
            json={"name": "To Revoke"},
        )
        key_id = create_resp.get_json()["data"]["id"]

        resp = client.delete(f"{API_PREFIX}/{key_id}", headers=_auth_header(auth_token))
        assert resp.status_code == 200

    def test_revoke_key_not_found(self, client, auth_token):
        """Revoking a nonexistent key returns 404."""
        resp = client.delete(f"{API_PREFIX}/99999", headers=_auth_header(auth_token))
        assert resp.status_code == 404

    def test_revoke_key_owned_by_other(self, client, auth_token, other_user_token):
        """Users cannot revoke keys belonging to other users."""
        create_resp = client.post(
            API_PREFIX,
            headers=_auth_header(auth_token),
            json={"name": "User1 Private Key"},
        )
        key_id = create_resp.get_json()["data"]["id"]

        resp = client.delete(f"{API_PREFIX}/{key_id}", headers=_auth_header(other_user_token))
        assert resp.status_code == 404  # Not found (not theirs)

    def test_revoke_already_revoked(self, client, auth_token):
        """Revoking an already-revoked key returns 400."""
        create_resp = client.post(
            API_PREFIX,
            headers=_auth_header(auth_token),
            json={"name": "Double Revoke"},
        )
        key_id = create_resp.get_json()["data"]["id"]

        client.delete(f"{API_PREFIX}/{key_id}", headers=_auth_header(auth_token))
        resp = client.delete(f"{API_PREFIX}/{key_id}", headers=_auth_header(auth_token))
        assert resp.status_code == 400


class TestRotateAPIKey:
    """Tests for POST /api-keys/<id>/rotate endpoint."""

    def test_rotate_key_success(self, client, auth_token):
        """Rotating a key revokes the old one and creates a new one."""
        create_resp = client.post(
            API_PREFIX,
            headers=_auth_header(auth_token),
            json={"name": "Rotatable Key", "scopes": "predict,dashboard"},
        )
        old_data = create_resp.get_json()["data"]
        old_key = old_data["key"]
        key_id = old_data["id"]

        resp = client.post(f"{API_PREFIX}/{key_id}/rotate", headers=_auth_header(auth_token))
        assert resp.status_code == 200
        new_data = resp.get_json()["data"]
        assert "key" in new_data
        assert new_data["key"] != old_key
        assert new_data["name"] == "Rotatable Key"
        assert "predict" in new_data["scopes"]

    def test_rotate_key_not_found(self, client, auth_token):
        """Rotating a nonexistent key returns 404."""
        resp = client.post(f"{API_PREFIX}/99999/rotate", headers=_auth_header(auth_token))
        assert resp.status_code == 404
