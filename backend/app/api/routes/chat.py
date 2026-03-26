"""Community Chat Routes — barangay-scoped real-time chat.

Blueprint: /api/v1/chat

Messages are persisted here; Supabase Realtime broadcasts
every INSERT/UPDATE to subscribed browser clients automatically.
No WebSocket code in Flask.
"""

import logging

import bleach
from flask import Blueprint, g, jsonify, request
from sqlalchemy import desc
from sqlalchemy.sql import func

from app.api.middleware.auth import require_auth
from app.core.chat_constants import (
    BARANGAY_DISPLAY_NAMES,
    CITYWIDE_POSTER_ROLES,
    DEFAULT_MESSAGE_LIMIT,
    MAX_MESSAGE_LENGTH,
    MAX_MESSAGE_LIMIT,
    VALID_BARANGAY_IDS,
    VALID_MESSAGE_TYPES,
)
from app.models.chat_message import ChatMessage
from app.models.db import get_db_session
from app.models.resident_profile import ResidentProfile
from app.models.user import User

logger = logging.getLogger(__name__)
chat_bp = Blueprint("chat", __name__)


# ── Helpers ──────────────────────────────────────────────────────────────


def _get_current_user_info() -> dict:
    """Build a user-info dict from Flask ``g`` context + DB lookup.

    Returns keys: id, name, role, barangay_id.
    """
    user_id = g.current_user_id
    role = g.current_user_role

    with get_db_session() as session:
        user = session.query(User).filter(User.id == user_id).first()
        if not user:
            return {"id": user_id, "name": "Unknown", "role": role, "barangay_id": None}

        name = user.full_name or user.email

        # Barangay comes from the resident profile (1:1 with users)
        profile = (
            session.query(ResidentProfile)
            .filter(ResidentProfile.user_id == user_id)
            .first()
        )
        barangay_id = _normalize_barangay(profile.barangay) if profile and profile.barangay else None

    return {"id": user_id, "name": name, "role": role, "barangay_id": barangay_id}


def _normalize_barangay(raw: str | None) -> str | None:
    """Convert a display barangay name to its slug ID."""
    if not raw:
        return None
    slug = raw.strip().lower().replace(" ", "_").replace("ñ", "n")
    # Handle common variants
    slug = slug.replace("santo_nino", "sto_nino").replace("santo_niño", "sto_nino")
    if slug in VALID_BARANGAY_IDS:
        return slug
    # Fallback: try matching display names
    for bid, display in BARANGAY_DISPLAY_NAMES.items():
        if display.lower() == raw.strip().lower():
            return bid
    return None


def _validate_channel(barangay_id: str):
    """Return a 400 response tuple if channel ID is invalid, else None."""
    if barangay_id not in VALID_BARANGAY_IDS:
        return jsonify({
            "success": False,
            "error": f"Invalid channel: '{barangay_id}'",
            "valid_channels": sorted(VALID_BARANGAY_IDS),
        }), 400
    return None


def _check_read_access(user_info: dict, barangay_id: str):
    """Operators/admins read all; residents read own barangay + citywide."""
    if user_info["role"] in ("operator", "admin"):
        return None
    allowed = {user_info.get("barangay_id"), "citywide"}
    if barangay_id not in allowed:
        return jsonify({"success": False, "error": "Access denied to this channel"}), 403
    return None


def _check_post_access(user_info: dict, barangay_id: str):
    """Residents post own barangay only; citywide is operator/admin only."""
    if barangay_id == "citywide" and user_info["role"] not in CITYWIDE_POSTER_ROLES:
        return jsonify({
            "success": False,
            "error": "Only operators and admins can post to City-Wide Broadcast",
        }), 403

    if (
        user_info["role"] == "user"
        and barangay_id != "citywide"
        and barangay_id != user_info.get("barangay_id")
    ):
        return jsonify({
            "success": False,
            "error": "You can only post in your registered barangay's channel",
        }), 403

    return None


# ── Routes ───────────────────────────────────────────────────────────────


@chat_bp.route("/channels", methods=["GET"])
@require_auth
def list_channels():
    """Return channels the current user can access."""
    user_info = _get_current_user_info()

    if user_info["role"] in ("operator", "admin"):
        channels = [
            {"barangay_id": bid, "display_name": name}
            for bid, name in BARANGAY_DISPLAY_NAMES.items()
        ]
    else:
        user_barangay = user_info.get("barangay_id")
        channels = []
        if user_barangay and user_barangay in BARANGAY_DISPLAY_NAMES:
            channels.append({
                "barangay_id": user_barangay,
                "display_name": BARANGAY_DISPLAY_NAMES[user_barangay],
            })
        channels.append({
            "barangay_id": "citywide",
            "display_name": "City-Wide Broadcast",
        })

    return jsonify({"success": True, "channels": channels, "total": len(channels)})


@chat_bp.route("/citywide/public", methods=["GET"])
def get_public_citywide_messages():
    """Read-only public endpoint for citywide broadcast (no auth required).

    Used by the landing page to show recent announcements to visitors.
    Only returns non-deleted messages from the citywide channel.
    """
    try:
        limit = min(int(request.args.get("limit", DEFAULT_MESSAGE_LIMIT)), MAX_MESSAGE_LIMIT)
    except (ValueError, TypeError):
        limit = DEFAULT_MESSAGE_LIMIT

    with get_db_session() as session:
        messages = (
            session.query(ChatMessage)
            .filter(
                ChatMessage.barangay_id == "citywide",
                ChatMessage.is_deleted.is_(False),
            )
            .order_by(desc(ChatMessage.created_at))
            .limit(limit)
            .all()
        )
        messages_dict = [m.to_dict() for m in reversed(messages)]

    return jsonify({
        "success": True,
        "channel": "citywide",
        "display_name": "City-Wide Broadcast",
        "messages": messages_dict,
        "count": len(messages_dict),
    })


@chat_bp.route("/<barangay_id>/messages", methods=["GET"])
@require_auth
def get_messages(barangay_id: str):
    """Load message history for a channel (paginated, cursor-based)."""
    err = _validate_channel(barangay_id)
    if err:
        return err

    user_info = _get_current_user_info()
    err = _check_read_access(user_info, barangay_id)
    if err:
        return err

    try:
        limit = min(int(request.args.get("limit", DEFAULT_MESSAGE_LIMIT)), MAX_MESSAGE_LIMIT)
    except (ValueError, TypeError):
        limit = DEFAULT_MESSAGE_LIMIT
    before = request.args.get("before")

    with get_db_session() as session:
        query = session.query(ChatMessage).filter(
            ChatMessage.barangay_id == barangay_id,
            ChatMessage.is_deleted.is_(False),
        )
        if before:
            query = query.filter(ChatMessage.created_at < before)

        messages = (
            query
            .order_by(desc(ChatMessage.created_at))
            .limit(limit)
            .all()
        )
        messages_dict = [m.to_dict() for m in reversed(messages)]

    return jsonify({
        "success": True,
        "channel": barangay_id,
        "display_name": BARANGAY_DISPLAY_NAMES.get(barangay_id, barangay_id),
        "messages": messages_dict,
        "count": len(messages_dict),
        "has_more": len(messages_dict) == limit,
    })


@chat_bp.route("/<barangay_id>/messages", methods=["POST"])
@require_auth
def send_message(barangay_id: str):
    """Write a new message. Supabase Realtime broadcasts it automatically."""
    err = _validate_channel(barangay_id)
    if err:
        return err

    user_info = _get_current_user_info()
    err = _check_post_access(user_info, barangay_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}

    content = bleach.clean(str(data.get("content", "")).strip(), tags=[], strip=True)
    if not content:
        return jsonify({"success": False, "error": "Message content cannot be empty"}), 400
    if len(content) > MAX_MESSAGE_LENGTH:
        return jsonify({"success": False, "error": f"Message exceeds {MAX_MESSAGE_LENGTH} characters"}), 400

    message_type = data.get("message_type", "text")
    if message_type not in VALID_MESSAGE_TYPES:
        message_type = "text"
    # Non-text types are operator/admin only
    if message_type != "text" and user_info["role"] not in ("operator", "admin"):
        message_type = "text"

    report_id = data.get("report_id")

    with get_db_session() as session:
        message = ChatMessage(
            barangay_id=barangay_id,
            user_id=user_info["id"],
            user_name=user_info["name"],
            user_role=user_info["role"],
            content=content,
            message_type=message_type,
            report_id=report_id if report_id else None,
        )
        session.add(message)
        session.flush()
        message_id = str(message.id)
        created_at = message.created_at.isoformat() if message.created_at is not None else None

    logger.info("Chat message sent | channel=%s user=%s type=%s", barangay_id, user_info["id"], message_type)
    return jsonify({"success": True, "message_id": message_id, "created_at": created_at}), 201


@chat_bp.route("/<barangay_id>/messages/<message_id>", methods=["DELETE"])
@require_auth
def delete_message(barangay_id: str, message_id: str):
    """Soft-delete a message. Operators and admins only."""
    err = _validate_channel(barangay_id)
    if err:
        return err

    user_info = _get_current_user_info()
    if user_info["role"] not in ("operator", "admin"):
        return jsonify({"success": False, "error": "Only operators and admins can delete messages"}), 403

    with get_db_session() as session:
        message = (
            session.query(ChatMessage)
            .filter(
                ChatMessage.id == message_id,
                ChatMessage.barangay_id == barangay_id,
                ChatMessage.is_deleted.is_(False),
            )
            .first()
        )
        if not message:
            return jsonify({"success": False, "error": "Message not found"}), 404

        message.is_deleted = True
        message.deleted_at = func.now()
        message.deleted_by = user_info["id"]

    return jsonify({"success": True})


@chat_bp.route("/<barangay_id>/messages/<message_id>/pin", methods=["PATCH"])
@require_auth
def toggle_pin(barangay_id: str, message_id: str):
    """Pin/unpin a message. Operators and admins only."""
    err = _validate_channel(barangay_id)
    if err:
        return err

    user_info = _get_current_user_info()
    if user_info["role"] not in ("operator", "admin"):
        return jsonify({"success": False, "error": "Only operators and admins can pin messages"}), 403

    with get_db_session() as session:
        message = (
            session.query(ChatMessage)
            .filter(
                ChatMessage.id == message_id,
                ChatMessage.barangay_id == barangay_id,
                ChatMessage.is_deleted.is_(False),
            )
            .first()
        )
        if not message:
            return jsonify({"success": False, "error": "Message not found"}), 404

        message.is_pinned = not message.is_pinned
        is_pinned = message.is_pinned

    return jsonify({"success": True, "is_pinned": is_pinned})


@chat_bp.route("/flood-report/<int:report_id>", methods=["POST"])
@require_auth
def post_flood_report_to_chat(report_id: int):
    """Post a flood_report message to the user's barangay channel."""
    user_info = _get_current_user_info()
    barangay_id = user_info.get("barangay_id")

    if not barangay_id or barangay_id not in VALID_BARANGAY_IDS:
        return jsonify({"success": False, "error": "User barangay not set or invalid"}), 400

    data = request.get_json(silent=True) or {}
    content = data.get("content", f"🌊 Flood report submitted by {user_info['name']}")

    with get_db_session() as session:
        message = ChatMessage(
            barangay_id=barangay_id,
            user_id=user_info["id"],
            user_name=user_info["name"],
            user_role=user_info["role"],
            content=bleach.clean(content[:MAX_MESSAGE_LENGTH], tags=[], strip=True),
            message_type="flood_report",
            report_id=report_id,
        )
        session.add(message)

    return jsonify({"success": True}), 201


# ── Internal helpers (called from other modules) ─────────────────────────


def post_flood_report_to_chat_internal(
    user_id: int,
    user_name: str,
    user_role: str,
    barangay_id: str | None,
    report_id: int,
    flood_depth: str,
    location: str,
):
    """Insert a flood_report chat message — called internally, no request context."""
    if not barangay_id or barangay_id not in VALID_BARANGAY_IDS:
        return

    content = f"🌊 Flood report: {flood_depth} at {location}"

    with get_db_session() as session:
        message = ChatMessage(
            barangay_id=barangay_id,
            user_id=user_id,
            user_name=user_name,
            user_role=user_role,
            content=content[:MAX_MESSAGE_LENGTH],
            message_type="flood_report",
            report_id=report_id,
        )
        session.add(message)


def post_alert_to_citywide_chat(alert_data: dict):
    """Post a Critical alert as a chat message to the citywide channel."""
    try:
        with get_db_session() as session:
            message = ChatMessage(
                barangay_id="citywide",
                user_id=1,  # System user
                user_name="DRRMO Alert System",
                user_role="admin",
                content=(
                    f"⚠️ {alert_data.get('risk_label', 'Alert')}: "
                    f"{alert_data.get('message', 'Flood risk elevated.')}"
                )[:MAX_MESSAGE_LENGTH],
                message_type="alert",
            )
            session.add(message)
    except Exception as e:
        logger.warning("Failed to post alert to citywide chat: %s", e)
