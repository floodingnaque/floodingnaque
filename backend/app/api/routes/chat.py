"""Community Chat Routes - barangay-scoped real-time chat.

Blueprint: /api/v1/chat

Messages are persisted here and broadcast to connected SSE clients
for real-time delivery across all barangay channels.
"""

import collections
import json
import logging
import queue
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, Generator, List, Optional

import bleach
from flask import Blueprint, Response, g, jsonify, request, stream_with_context
from sqlalchemy import desc
from sqlalchemy.sql import func

from app.api.middleware.auth import require_auth
from app.core.config import is_debug_mode
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


# ── Chat SSE Manager ────────────────────────────────────────────────────


# Per-IP connection cap (mirrors alert SSE)
_MAX_CHAT_SSE_PER_IP = 5
_chat_ip_connections: Dict[str, int] = {}
_chat_ip_timestamps: Dict[str, float] = {}  # last activity per IP
_chat_ip_lock = threading.Lock()
_CHAT_IP_STALE_SECONDS = 120  # auto-expire leaked counters after 2 min

# SSE ticket storage (in-memory, short-lived)
_chat_sse_tickets: Dict[str, Dict[str, Any]] = {}
_CHAT_TICKET_TTL = 30  # seconds


def _chat_ip_cleanup_stale() -> None:
    """Remove IP entries that haven't been refreshed recently (leak guard)."""
    now = time.time()
    stale = [
        ip for ip, ts in _chat_ip_timestamps.items()
        if now - ts > _CHAT_IP_STALE_SECONDS
    ]
    for ip in stale:
        _chat_ip_connections.pop(ip, None)
        _chat_ip_timestamps.pop(ip, None)


def _chat_ip_connect(ip: str) -> bool:
    if is_debug_mode():
        return True  # No cap in development
    with _chat_ip_lock:
        _chat_ip_cleanup_stale()
        current = _chat_ip_connections.get(ip, 0)
        if current >= _MAX_CHAT_SSE_PER_IP:
            return False
        _chat_ip_connections[ip] = current + 1
        _chat_ip_timestamps[ip] = time.time()
        return True


def _chat_ip_disconnect(ip: str) -> None:
    if is_debug_mode():
        return
    with _chat_ip_lock:
        current = _chat_ip_connections.get(ip, 0)
        if current <= 1:
            _chat_ip_connections.pop(ip, None)
            _chat_ip_timestamps.pop(ip, None)
        else:
            _chat_ip_connections[ip] = current - 1
            _chat_ip_timestamps[ip] = time.time()


class ChatSSEManager:
    """Per-channel SSE manager for real-time chat delivery.

    Unlike the global alert SSEManager, this routes events to clients
    subscribed to specific channels (barangay IDs).  An ``"all"`` channel
    subscription receives events from every channel (for the operator sidebar).

    Presence tracking: each connected client carries optional user metadata
    (user_id, user_name, user_role) so the manager can broadcast presence
    updates (active user counts) whenever clients join or leave.
    """

    REPLAY_BUFFER_SIZE = 500

    def __init__(self) -> None:
        # channel -> { client_id -> Queue }
        self._channels: Dict[str, Dict[str, queue.Queue]] = {}
        # client_id -> { user_id, user_name, user_role, channel }
        self._client_meta: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._event_id_counter = 0
        self._event_id_lock = threading.Lock()
        self._replay_buffer: collections.deque = collections.deque(
            maxlen=self.REPLAY_BUFFER_SIZE
        )

    def _next_event_id(self) -> int:
        with self._event_id_lock:
            self._event_id_counter += 1
            return self._event_id_counter

    # -- client lifecycle --------------------------------------------------

    def add_client(
        self,
        channel: str,
        client_id: str,
        user_meta: Optional[Dict[str, Any]] = None,
    ) -> queue.Queue:
        client_queue: queue.Queue = queue.Queue(maxsize=100)
        with self._lock:
            if channel not in self._channels:
                self._channels[channel] = {}
            self._channels[channel][client_id] = client_queue
            if user_meta:
                self._client_meta[client_id] = {**user_meta, "channel": channel}
            total = sum(len(c) for c in self._channels.values())
            logger.info("Chat SSE client connected: %s ch=%s (total=%d)", client_id, channel, total)
        return client_queue

    def remove_client(self, channel: str, client_id: str) -> None:
        with self._lock:
            self._client_meta.pop(client_id, None)
            ch = self._channels.get(channel)
            if ch and client_id in ch:
                del ch[client_id]
                if not ch:
                    del self._channels[channel]
                total = sum(len(c) for c in self._channels.values())
                logger.info("Chat SSE client disconnected: %s ch=%s (total=%d)", client_id, channel, total)

    def get_presence(self, channel: str) -> Dict[str, Any]:
        """Return active user list and count for a channel.

        For ``"all"`` or ``"citywide"``, returns users across all channels.
        For a specific barangay, returns users in that channel
        plus operator/admin users watching ``"all"``.
        """
        with self._lock:
            seen_user_ids: Dict[int, Dict[str, Any]] = {}
            # Users directly in the requested channel
            for cid in (self._channels.get(channel) or {}):
                meta = self._client_meta.get(cid)
                if meta and meta.get("user_id"):
                    uid = meta["user_id"]
                    if uid not in seen_user_ids:
                        seen_user_ids[uid] = {
                            "user_id": uid,
                            "user_name": meta.get("user_name", "Unknown"),
                            "user_role": meta.get("user_role", "user"),
                        }
            # For specific barangays, also include operators/admins on "all"
            if channel not in ("all", "citywide"):
                for cid in (self._channels.get("all") or {}):
                    meta = self._client_meta.get(cid)
                    if meta and meta.get("user_id"):
                        uid = meta["user_id"]
                        if uid not in seen_user_ids:
                            seen_user_ids[uid] = {
                                "user_id": uid,
                                "user_name": meta.get("user_name", "Unknown"),
                                "user_role": meta.get("user_role", "user"),
                            }
            # For citywide, include all users across all channels
            if channel == "citywide":
                for ch_clients in self._channels.values():
                    for cid in ch_clients:
                        meta = self._client_meta.get(cid)
                        if meta and meta.get("user_id"):
                            uid = meta["user_id"]
                            if uid not in seen_user_ids:
                                seen_user_ids[uid] = {
                                    "user_id": uid,
                                    "user_name": meta.get("user_name", "Unknown"),
                                    "user_role": meta.get("user_role", "user"),
                                }
            users = list(seen_user_ids.values())
            return {"count": len(users), "users": users}

    # -- broadcasting ------------------------------------------------------

    def broadcast(self, channel: str, event_type: str, data: Dict[str, Any]) -> int:
        """Broadcast an event to all clients in *channel* + ``"all"``."""
        event_id = self._next_event_id()
        message = self._format_sse(event_type, data, event_id)

        if event_type != "heartbeat":
            self._replay_buffer.append((event_id, channel, message))

        sent = 0
        with self._lock:
            for target in (channel, "all"):
                ch = self._channels.get(target)
                if not ch:
                    continue
                dead: List[str] = []
                for cid, cq in ch.items():
                    try:
                        cq.put_nowait(message)
                        sent += 1
                    except queue.Full:
                        dead.append(cid)
                for cid in dead:
                    del ch[cid]
                if not ch:
                    self._channels.pop(target, None)
        return sent

    def get_events_since(self, last_event_id: int, channel: Optional[str] = None) -> List[str]:
        """Return buffered messages since *last_event_id*, optionally filtered by channel."""
        if channel and channel != "all":
            return [msg for eid, ch, msg in self._replay_buffer if eid > last_event_id and ch == channel]
        return [msg for eid, _ch, msg in self._replay_buffer if eid > last_event_id]

    def get_client_count(self) -> int:
        with self._lock:
            return sum(len(c) for c in self._channels.values())

    # -- formatting --------------------------------------------------------

    @staticmethod
    def _format_sse(event_type: str, data: Dict[str, Any], event_id: Optional[int] = None) -> str:
        json_data = json.dumps(data, default=str)
        parts: List[str] = []
        if event_id is not None:
            parts.append(f"id: {event_id}")
        parts.append(f"event: {event_type}")
        parts.append(f"data: {json_data}")
        return "\n".join(parts) + "\n\n"


# Singleton
chat_sse_manager = ChatSSEManager()


def _generate_chat_stream(
    channel: str,
    client_id: str,
    client_queue: queue.Queue,
    client_ip: str = "unknown",
    last_event_id: Optional[int] = None,
) -> Generator[str, None, None]:
    """Generator that yields SSE frames from *client_queue*."""
    last_heartbeat = time.time()
    heartbeat_interval = 30

    try:
        if last_event_id is not None:
            missed = chat_sse_manager.get_events_since(last_event_id, channel)
            if missed:
                logger.info("Chat SSE replaying %d events for %s", len(missed), client_id)
                for msg in missed:
                    yield msg

        while True:
            try:
                message = client_queue.get(timeout=5)
                yield message
                last_heartbeat = time.time()
            except queue.Empty:
                now = time.time()
                if now - last_heartbeat >= heartbeat_interval:
                    hb_id = chat_sse_manager._next_event_id()
                    yield chat_sse_manager._format_sse(
                        "heartbeat",
                        {"timestamp": datetime.now(timezone.utc).isoformat()},
                        event_id=hb_id,
                    )
                    last_heartbeat = now
    except GeneratorExit:
        pass
    finally:
        chat_sse_manager.remove_client(channel, client_id)
        _chat_ip_disconnect(client_ip)
        # Broadcast updated presence after this client leaves
        _broadcast_presence(channel)


def _broadcast_presence(channel: str) -> None:
    """Broadcast a presence event with the current active user list for *channel*."""
    presence = chat_sse_manager.get_presence(channel)
    chat_sse_manager.broadcast(channel, "presence", presence)


def _cleanup_chat_tickets() -> None:
    now = time.time()
    expired = [k for k, v in _chat_sse_tickets.items() if now - v["created"] > _CHAT_TICKET_TTL]
    for k in expired:
        del _chat_sse_tickets[k]


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
    """Write a new message and broadcast via SSE."""
    err = _validate_channel(barangay_id)
    if err:
        return err

    user_id = g.current_user_id
    role = g.current_user_role

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
    if message_type != "text" and role not in ("operator", "admin"):
        message_type = "text"

    report_id = data.get("report_id")

    # Single DB session: look up user + write message
    with get_db_session() as session:
        user = session.query(User).filter(User.id == user_id).first()
        user_name = (user.full_name or user.email) if user else "Unknown"

        # Access check (inline to avoid extra DB call)
        if barangay_id == "citywide" and role not in CITYWIDE_POSTER_ROLES:
            return jsonify({
                "success": False,
                "error": "Only operators and admins can post to City-Wide Broadcast",
            }), 403

        if role == "user" and barangay_id != "citywide":
            profile = (
                session.query(ResidentProfile)
                .filter(ResidentProfile.user_id == user_id)
                .first()
            )
            user_barangay = _normalize_barangay(profile.barangay) if profile and profile.barangay else None
            if barangay_id != user_barangay:
                return jsonify({
                    "success": False,
                    "error": "You can only post in your registered barangay's channel",
                }), 403

        message = ChatMessage(
            barangay_id=barangay_id,
            user_id=user_id,
            user_name=user_name,
            user_role=role,
            content=content,
            message_type=message_type,
            report_id=report_id if report_id else None,
        )
        session.add(message)
        session.flush()
        message_id = str(message.id)
        created_at = message.created_at.isoformat() if message.created_at is not None else None

    # Broadcast to SSE clients
    sent = chat_sse_manager.broadcast(barangay_id, "new_message", {
        "message": {
            "id": message_id,
            "barangay_id": barangay_id,
            "user_id": user_id,
            "user_name": user_name,
            "user_role": role,
            "content": content,
            "message_type": message_type,
            "report_id": report_id if report_id else None,
            "is_pinned": False,
            "created_at": created_at,
        },
    })

    logger.info("Chat message sent | channel=%s user=%s type=%s sse_clients=%d", barangay_id, user_id, message_type, sent)
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

    # Broadcast deletion to SSE clients
    chat_sse_manager.broadcast(barangay_id, "delete_message", {
        "message_id": message_id,
        "channel": barangay_id,
    })

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

    # Broadcast pin toggle to SSE clients
    chat_sse_manager.broadcast(barangay_id, "pin_message", {
        "message_id": message_id,
        "channel": barangay_id,
        "is_pinned": is_pinned,
    })

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
    content = data.get("content", f"[Flood Report] Flood report submitted by {user_info['name']}")

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
        session.flush()
        msg_dict = message.to_dict()

    chat_sse_manager.broadcast(barangay_id, "new_message", {"message": msg_dict})
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
    """Insert a flood_report chat message - called internally, no request context."""
    if not barangay_id or barangay_id not in VALID_BARANGAY_IDS:
        return

    content = f"[Flood Report] Flood report: {flood_depth} at {location}"

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
        session.flush()
        msg_dict = message.to_dict()

    chat_sse_manager.broadcast(barangay_id, "new_message", {"message": msg_dict})


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
                    f"[{alert_data.get('risk_label', 'Alert')}]: "
                    f"{alert_data.get('message', 'Flood risk elevated.')}"
                )[:MAX_MESSAGE_LENGTH],
                message_type="alert",
            )
            session.add(message)
            session.flush()
            msg_dict = message.to_dict()

        # Broadcast the alert message to citywide channel
        chat_sse_manager.broadcast("citywide", "new_message", {"message": msg_dict})
    except Exception as e:
        logger.warning("Failed to post alert to citywide chat: %s", e)


# ── SSE Stream Endpoints ─────────────────────────────────────────────────


@chat_bp.route("/stream/ticket", methods=["POST"])
@require_auth
def get_chat_sse_ticket():
    """Issue a short-lived SSE ticket for chat streaming.

    EventSource doesn't support Authorization headers, so the client
    fetches a ticket first and passes it as a query parameter.
    """
    import secrets

    # Look up display name for presence
    user_name = getattr(g, "current_user_email", "Unknown")
    try:
        with get_db_session() as session:
            u = session.query(User).filter(User.id == g.current_user_id).first()
            if u and u.full_name:
                user_name = u.full_name
    except Exception:
        pass

    ticket = secrets.token_urlsafe(32)
    _chat_sse_tickets[ticket] = {
        "created": time.time(),
        "user_id": g.current_user_id,
        "user_name": user_name,
        "user_role": g.current_user_role,
    }
    _cleanup_chat_tickets()
    return jsonify({"ticket": ticket, "expires_in": _CHAT_TICKET_TTL}), 200


@chat_bp.route("/stream", methods=["GET"])
def stream_chat():
    """SSE stream for real-time chat events.

    Query Parameters:
        channel (str): Barangay ID or ``"all"`` (operator overview).
        ticket  (str): Short-lived auth ticket from ``/stream/ticket``.
        lastEventId (str): Last event ID for reconnection replay.

    Events:
        - connected:      Initial handshake confirmation
        - new_message:     A message was sent ``{ message: ChatMessage }``
        - delete_message:  A message was soft-deleted ``{ message_id, channel }``
        - pin_message:     A message pin was toggled ``{ message_id, channel, is_pinned }``
        - typing:          User typing indicator ``{ user_name, user_role, is_typing, channel }``
        - heartbeat:       Keep-alive (every 30 s)
    """
    channel = request.args.get("channel", "").strip()
    ticket = request.args.get("ticket", "").strip()
    client_ip = request.remote_addr or "unknown"

    # Validate ticket
    ticket_data = _chat_sse_tickets.pop(ticket, None)
    if not ticket_data or (time.time() - ticket_data["created"]) > _CHAT_TICKET_TTL:
        return jsonify({"success": False, "error": "Invalid or expired ticket"}), 401

    # Validate channel
    if channel != "all" and channel not in VALID_BARANGAY_IDS:
        return jsonify({"success": False, "error": f"Invalid channel: {channel}"}), 400

    # Per-IP cap
    if not _chat_ip_connect(client_ip):
        return jsonify({"success": False, "error": "Too many connections"}), 429

    client_id = f"{client_ip}_{time.time_ns()}"

    # Parse Last-Event-ID
    last_event_id: Optional[int] = None
    raw_last = request.headers.get("Last-Event-ID") or request.args.get("lastEventId")
    if raw_last is not None:
        try:
            last_event_id = int(raw_last)
        except (ValueError, TypeError):
            pass

    # Extract user metadata from ticket for presence tracking
    user_meta = {
        "user_id": ticket_data.get("user_id"),
        "user_name": ticket_data.get("user_name", "Unknown"),
        "user_role": ticket_data.get("user_role", "user"),
    }
    client_queue = chat_sse_manager.add_client(channel, client_id, user_meta=user_meta)

    # Send initial "connected" event with presence data
    presence = chat_sse_manager.get_presence(channel)
    conn_id = chat_sse_manager._next_event_id()
    client_queue.put(chat_sse_manager._format_sse(
        "connected",
        {"client_id": client_id, "channel": channel, "timestamp": datetime.now(timezone.utc).isoformat(), "presence": presence},
        event_id=conn_id,
    ))

    # Broadcast updated presence to all existing clients in this channel
    _broadcast_presence(channel)

    response = Response(
        stream_with_context(_generate_chat_stream(channel, client_id, client_queue, client_ip, last_event_id)),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
        },
    )
    return response


@chat_bp.route("/stream/typing", methods=["POST"])
@require_auth
def broadcast_typing():
    """Broadcast a typing indicator to a channel.

    Body: { "channel": "<barangay_id>", "is_typing": true|false }
    """
    data = request.get_json(silent=True) or {}
    channel = data.get("channel", "").strip()
    is_typing = bool(data.get("is_typing", False))

    if channel not in VALID_BARANGAY_IDS:
        return jsonify({"success": False, "error": "Invalid channel"}), 400

    user_info = _get_current_user_info()
    chat_sse_manager.broadcast(channel, "typing", {
        "user_id": user_info["id"],
        "user_name": user_info["name"],
        "user_role": user_info["role"],
        "is_typing": is_typing,
        "channel": channel,
    })
    return jsonify({"success": True}), 200
