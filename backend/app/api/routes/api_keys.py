"""
API Key Management Routes.

Provides endpoints for users to create, list, rotate, and revoke
their own API keys for programmatic access.
"""

import logging
from datetime import datetime, timedelta, timezone
from functools import wraps

from app.api.middleware.auth import require_auth
from app.models.api_key import APIKey
from app.models.db import get_db_session
from app.utils.api_constants import HTTP_BAD_REQUEST, HTTP_OK
from app.utils.api_responses import api_error
from flask import Blueprint, g, jsonify, request
from sqlalchemy import and_

logger = logging.getLogger(__name__)

api_keys_bp = Blueprint("api_keys", __name__)

# Maximum keys per user
MAX_KEYS_PER_USER = 10


# ---------------------------------------------------------------------------
# POST /  —  create a new API key
# ---------------------------------------------------------------------------


@api_keys_bp.route("", methods=["POST"])
@api_keys_bp.route("/", methods=["POST"])
@require_auth
def create_api_key():
    """
    Generate a new API key for the authenticated user.

    The raw key is returned **once** in the response. It cannot be retrieved later.

    Request Body:
        name (str, required): Human-readable label for the key
        scopes (str, optional): Comma-separated scopes (default: "predict")
        expires_in_days (int, optional): Days until expiry (default: no expiry)
    """
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    if not name or len(name) > 255:
        return api_error("ValidationError", "name is required (max 255 chars)", HTTP_BAD_REQUEST)

    scopes = data.get("scopes", "predict").strip()
    allowed_scopes = {"predict", "dashboard", "alerts", "data", "admin"}
    for scope in scopes.split(","):
        if scope.strip() not in allowed_scopes:
            return api_error("ValidationError", f"Invalid scope: {scope.strip()}", HTTP_BAD_REQUEST)

    expires_in_days = data.get("expires_in_days")
    expires_at = None
    if expires_in_days is not None:
        try:
            expires_in_days = int(expires_in_days)
            if expires_in_days < 1 or expires_in_days > 365:
                return api_error("ValidationError", "expires_in_days must be 1-365", HTTP_BAD_REQUEST)
            expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)
        except (ValueError, TypeError):
            return api_error("ValidationError", "expires_in_days must be an integer", HTTP_BAD_REQUEST)

    user_id = g.current_user_id

    with get_db_session() as session:
        # Enforce per-user limit
        active_count = (
            session.query(APIKey)
            .filter(
                and_(
                    APIKey.user_id == user_id,
                    APIKey.__table__.c.is_revoked.is_(False),
                    APIKey.__table__.c.is_deleted.is_(False),
                )
            )
            .count()
        )
        if active_count >= MAX_KEYS_PER_USER:
            return api_error(
                "LimitExceeded",
                f"Maximum {MAX_KEYS_PER_USER} active keys per user",
                HTTP_BAD_REQUEST,
            )

        raw_key, key_prefix, key_hash = APIKey.generate_key()

        api_key = APIKey(
            user_id=user_id,
            name=name,
            key_prefix=key_prefix,
            key_hash=key_hash,
            scopes=scopes,
            expires_at=expires_at,
        )
        session.add(api_key)
        session.commit()

        result = api_key.to_dict()
        result["key"] = raw_key  # Shown once only

        logger.info("API key created: %s... for user %d", key_prefix, user_id)

    return jsonify({"success": True, "data": result}), 201


# ---------------------------------------------------------------------------
# GET /  —  list user's API keys (masked)
# ---------------------------------------------------------------------------


@api_keys_bp.route("", methods=["GET"])
@api_keys_bp.route("/", methods=["GET"])
@require_auth
def list_api_keys():
    """List all API keys for the authenticated user (key values masked)."""
    user_id = g.current_user_id

    with get_db_session() as session:
        keys = (
            session.query(APIKey)
            .filter(
                and_(
                    APIKey.user_id == user_id,
                    APIKey.__table__.c.is_deleted.is_(False),
                )
            )
            .order_by(APIKey.created_at.desc())
            .all()
        )
        return (
            jsonify(
                {
                    "success": True,
                    "data": [k.to_dict() for k in keys],
                }
            ),
            HTTP_OK,
        )


# ---------------------------------------------------------------------------
# DELETE /<id>  —  revoke a key
# ---------------------------------------------------------------------------


@api_keys_bp.route("/<int:key_id>", methods=["DELETE"])
@require_auth
def revoke_api_key(key_id: int):
    """Revoke an API key by ID. Only the key owner can revoke."""
    user_id = g.current_user_id

    with get_db_session() as session:
        api_key = (
            session.query(APIKey)
            .filter(
                and_(
                    APIKey.id == key_id,
                    APIKey.user_id == user_id,
                    APIKey.__table__.c.is_deleted.is_(False),
                )
            )
            .first()
        )
        if not api_key:
            return api_error("NotFound", "API key not found", 404)
        if api_key.is_revoked:
            return api_error("ValidationError", "API key already revoked", HTTP_BAD_REQUEST)

        api_key.revoke()
        session.commit()
        logger.info("API key revoked: %s... by user %d", api_key.key_prefix, user_id)

    return jsonify({"success": True, "message": "API key revoked"}), HTTP_OK


# ---------------------------------------------------------------------------
# POST /<id>/rotate  —  revoke old + issue new
# ---------------------------------------------------------------------------


@api_keys_bp.route("/<int:key_id>/rotate", methods=["POST"])
@require_auth
def rotate_api_key(key_id: int):
    """
    Rotate an API key: revokes the old one and creates a new one
    with the same name, scopes, and expiration policy.

    The new raw key is returned once.
    """
    user_id = g.current_user_id

    with get_db_session() as session:
        old_key = (
            session.query(APIKey)
            .filter(
                and_(
                    APIKey.id == key_id,
                    APIKey.user_id == user_id,
                    APIKey.__table__.c.is_deleted.is_(False),
                )
            )
            .first()
        )
        if not old_key:
            return api_error("NotFound", "API key not found", 404)

        # Revoke old
        old_key.revoke()

        # Create new with same metadata
        raw_key, key_prefix, key_hash = APIKey.generate_key()
        new_key = APIKey(
            user_id=user_id,
            name=old_key.name,
            key_prefix=key_prefix,
            key_hash=key_hash,
            scopes=old_key.scopes,
            expires_at=old_key.expires_at,
        )
        session.add(new_key)
        session.commit()

        result = new_key.to_dict()
        result["key"] = raw_key

        logger.info(
            "API key rotated: %s... → %s... for user %d",
            old_key.key_prefix,
            key_prefix,
            user_id,
        )

    return jsonify({"success": True, "data": result}), HTTP_OK
