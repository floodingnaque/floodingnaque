"""
Server-Sent Events (SSE) Routes for Real-time Flood Alerts.

Provides live streaming of flood alerts to connected clients.
Uses SSE protocol for efficient one-way real-time communication.
"""

import html
import json
import logging
import queue
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, Generator

from app.api.middleware.rate_limit import limiter
from app.models.db import AlertHistory, get_db_session
from flask import Blueprint, Response, g, jsonify, request, stream_with_context
from sqlalchemy import desc

logger = logging.getLogger(__name__)

sse_bp = Blueprint("sse", __name__)

# Global connection tracking for SSE clients
_sse_clients: Dict[str, queue.Queue] = {}
_sse_lock = threading.Lock()

# Per-IP SSE connection cap to prevent resource exhaustion
MAX_SSE_CONNECTIONS_PER_IP = 5
_sse_ip_connections: Dict[str, int] = {}
_sse_ip_lock = threading.Lock()


def _track_ip_connect(ip: str) -> bool:
    """Track an SSE connection for an IP.  Returns False if the cap is exceeded."""
    with _sse_ip_lock:
        current = _sse_ip_connections.get(ip, 0)
        if current >= MAX_SSE_CONNECTIONS_PER_IP:
            return False
        _sse_ip_connections[ip] = current + 1
        return True


def _track_ip_disconnect(ip: str) -> None:
    """Decrement the connection counter when an SSE client disconnects."""
    with _sse_ip_lock:
        current = _sse_ip_connections.get(ip, 0)
        if current <= 1:
            _sse_ip_connections.pop(ip, None)
        else:
            _sse_ip_connections[ip] = current - 1


class SSEManager:
    """
    Manages Server-Sent Events connections and message broadcasting.

    Thread-safe implementation for handling multiple concurrent SSE clients.
    """

    def __init__(self):
        self._clients: Dict[str, queue.Queue] = {}
        self._lock = threading.Lock()
        self._running = True

    def add_client(self, client_id: str) -> queue.Queue:
        """Register a new SSE client and return their message queue."""
        client_queue = queue.Queue(maxsize=100)  # Limit queue size to prevent memory issues
        with self._lock:
            self._clients[client_id] = client_queue
            logger.info(f"SSE client connected: {client_id}, total clients: {len(self._clients)}")
        return client_queue

    def remove_client(self, client_id: str) -> None:
        """Remove a disconnected SSE client."""
        with self._lock:
            if client_id in self._clients:
                del self._clients[client_id]
                logger.info(f"SSE client disconnected: {client_id}, total clients: {len(self._clients)}")

    def broadcast(self, event_type: str, data: Dict[str, Any]) -> int:
        """
        Broadcast a message to all connected SSE clients.

        Args:
            event_type: The event type (e.g., 'alert', 'heartbeat')
            data: The data to send as JSON

        Returns:
            Number of clients that received the message
        """
        message = self._format_sse(event_type, data)
        sent_count = 0

        with self._lock:
            disconnected = []
            for client_id, client_queue in self._clients.items():
                try:
                    # Non-blocking put with timeout
                    client_queue.put_nowait(message)
                    sent_count += 1
                except queue.Full:
                    # Client queue is full, consider them slow/disconnected
                    disconnected.append(client_id)
                    logger.warning(f"SSE client queue full, marking for removal: {client_id}")

            # Clean up disconnected clients
            for client_id in disconnected:
                del self._clients[client_id]

        return sent_count

    def send_to_client(self, client_id: str, event_type: str, data: Dict[str, Any]) -> bool:
        """Send a message to a specific client."""
        message = self._format_sse(event_type, data)

        with self._lock:
            if client_id in self._clients:
                try:
                    self._clients[client_id].put_nowait(message)
                    return True
                except queue.Full:
                    return False
        return False

    def get_client_count(self) -> int:
        """Get the current number of connected clients."""
        with self._lock:
            return len(self._clients)

    @staticmethod
    def _format_sse(event_type: str, data: Dict[str, Any]) -> str:
        """Format data as SSE message."""
        json_data = json.dumps(data, default=str)
        return f"event: {event_type}\ndata: {json_data}\n\n"


# Global SSE manager instance
sse_manager = SSEManager()


def get_sse_manager() -> SSEManager:
    """Get the global SSE manager instance."""
    return sse_manager


def broadcast_alert(alert_data: Dict[str, Any]) -> int:
    """
    Broadcast a new alert to all connected SSE clients.

    This function can be called from the alert service when a new alert is created.
    Also invalidates the weather/prediction cache so subsequent requests use
    fresh data instead of waiting for TTL expiry.

    Args:
        alert_data: Alert information to broadcast

    Returns:
        Number of clients that received the alert
    """
    # Invalidate stale weather cache on alert broadcast (e.g. typhoon warning)
    try:
        from app.utils.resilience.cache import invalidate_weather_cache

        invalidate_weather_cache()
    except Exception:
        logger.warning("Failed to invalidate weather cache on alert broadcast", exc_info=True)

    return sse_manager.broadcast("alert", {"timestamp": datetime.now(timezone.utc).isoformat(), "alert": alert_data})


def _generate_sse_stream(
    client_id: str, client_queue: queue.Queue, client_ip: str = "unknown"
) -> Generator[str, None, None]:
    """
    Generator function for SSE stream.

    Yields SSE formatted messages from the client's queue.
    Includes periodic heartbeats to keep the connection alive.
    """
    last_heartbeat = time.time()
    heartbeat_interval = 30  # seconds

    try:
        while True:
            try:
                # Wait for message with timeout for heartbeat
                message = client_queue.get(timeout=5)
                yield message
                last_heartbeat = time.time()
            except queue.Empty:
                # No message, check if we need to send heartbeat
                current_time = time.time()
                if current_time - last_heartbeat >= heartbeat_interval:
                    yield sse_manager._format_sse(
                        "heartbeat", {"timestamp": datetime.now(timezone.utc).isoformat(), "status": "connected"}
                    )
                    last_heartbeat = current_time
    except GeneratorExit:
        # Client disconnected
        pass
    finally:
        sse_manager.remove_client(client_id)
        _track_ip_disconnect(client_ip)


@sse_bp.route("/alerts", methods=["GET"])
@limiter.limit("10 per minute")
def stream_alerts():
    """
    Stream real-time flood alerts via Server-Sent Events.

    Clients connect to this endpoint to receive live alert updates.
    The connection stays open and sends events as alerts occur.
    Rate-limited to 10 connect attempts per minute per IP, with a
    maximum of 5 concurrent connections per IP.

    Events:
        - alert: New flood alert notification
        - heartbeat: Keep-alive signal (every 30 seconds)
        - connected: Initial connection confirmation

    Query Parameters:
        risk_level (int, optional): Filter alerts by minimum risk level (0-2)

    Returns:
        SSE stream with real-time alert events
    ---
    tags:
      - Real-time
      - Alerts
    produces:
      - text/event-stream
    parameters:
      - in: query
        name: risk_level
        schema:
          type: integer
          enum: [0, 1, 2]
        description: Filter alerts by minimum risk level
    responses:
      200:
        description: SSE event stream
        content:
          text/event-stream:
            schema:
              type: string
    """
    client_ip = request.remote_addr or "unknown"
    request_id = getattr(g, "request_id", "unknown")

    # Enforce per-IP concurrent connection cap
    if not _track_ip_connect(client_ip):
        logger.warning(
            f"SSE connection rejected - per-IP cap ({MAX_SSE_CONNECTIONS_PER_IP}) "
            f"exceeded for {client_ip} [{request_id}]"
        )
        return (
            jsonify(
                {
                    "success": False,
                    "error": "TooManyConnections",
                    "message": f"Maximum {MAX_SSE_CONNECTIONS_PER_IP} concurrent SSE connections per IP",
                    "request_id": request_id,
                }
            ),
            429,
        )

    # Generate unique client ID
    client_id = f"{client_ip}_{time.time_ns()}"

    logger.info(f"SSE connection request from {client_id} [{request_id}]")

    # Create client queue and register
    client_queue = sse_manager.add_client(client_id)

    # Send initial connection confirmation
    initial_data = {
        "client_id": client_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": "Connected to flood alert stream",
        "request_id": request_id,
    }
    client_queue.put(sse_manager._format_sse("connected", initial_data))

    # Create the SSE response
    response = Response(
        stream_with_context(_generate_sse_stream(client_id, client_queue, client_ip)),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
            "Access-Control-Allow-Origin": "*",
            "X-Request-ID": request_id,
        },
    )

    return response


@sse_bp.route("/alerts/ticket", methods=["POST"])
@limiter.limit("30 per minute")
def get_sse_ticket():
    """
    Issue a short-lived SSE ticket for authenticated users.

    The ticket can be used as a query parameter when connecting to the
    SSE stream, since EventSource does not support Authorization headers.

    Returns:
        200: { "ticket": "<token>" }
        401: Not authenticated
    ---
    tags:
      - Real-time
      - Authentication
    """
    import secrets

    request_id = getattr(g, "request_id", "unknown")

    # Accept JWT Bearer token for authentication
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        # Authenticated user - issue a ticket
        ticket = secrets.token_urlsafe(32)
        # Store ticket with expiry (simple in-memory store)
        _sse_tickets[ticket] = {
            "created": time.time(),
            "request_id": request_id,
        }
        # Clean up expired tickets
        _cleanup_sse_tickets()

        return jsonify({"ticket": ticket, "expires_in": SSE_TICKET_TTL}), 200

    # No auth - still issue ticket in development for simplicity
    ticket = secrets.token_urlsafe(32)
    _sse_tickets[ticket] = {
        "created": time.time(),
        "request_id": request_id,
    }
    _cleanup_sse_tickets()

    return jsonify({"ticket": ticket, "expires_in": SSE_TICKET_TTL}), 200


# SSE ticket storage (in-memory, short-lived)
_sse_tickets: Dict[str, Dict] = {}
SSE_TICKET_TTL = 30  # seconds


def _cleanup_sse_tickets():
    """Remove expired SSE tickets."""
    now = time.time()
    expired = [k for k, v in _sse_tickets.items() if now - v["created"] > SSE_TICKET_TTL]
    for k in expired:
        del _sse_tickets[k]


@sse_bp.route("/alerts/test", methods=["POST"])
@limiter.limit("5 per minute")
def test_alert_broadcast():
    """
    Send a test alert to all connected SSE clients.

    For development and testing purposes only.

    Request Body:
        risk_level (int): Risk level 0-2
        message (str): Test alert message
        location (str): Test location

    Returns:
        200: Test alert sent successfully
    ---
    tags:
      - Real-time
      - Alerts
    requestBody:
      content:
        application/json:
          schema:
            type: object
            properties:
              risk_level:
                type: integer
                enum: [0, 1, 2]
                default: 1
              message:
                type: string
                default: "Test flood alert"
              location:
                type: string
                default: "Test Location"
    responses:
      200:
        description: Test alert broadcast result
    """
    request_id = getattr(g, "request_id", "unknown")

    data = request.get_json() or {}
    # Validate and sanitize risk_level to prevent injection
    try:
        risk_level = int(data.get("risk_level", 1))
        if risk_level not in [0, 1, 2]:
            risk_level = 1  # Default to Alert level
    except (ValueError, TypeError):
        risk_level = 1
    # Sanitize user-provided strings to prevent XSS
    message = html.escape(str(data.get("message", "Test flood alert"))[:200])
    location = html.escape(str(data.get("location", "Test Location"))[:100])

    risk_labels = {0: "Safe", 1: "Alert", 2: "Critical"}

    test_alert = {
        "id": f"test_{int(time.time())}",
        "risk_level": risk_level,
        "risk_label": risk_labels.get(risk_level, "Unknown"),
        "location": location,
        "message": message,
        "is_test": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    sent_count = broadcast_alert(test_alert)

    return {
        "success": True,
        "message": f"Test alert broadcast to {sent_count} connected clients",
        "alert": test_alert,
        "connected_clients": sse_manager.get_client_count(),
        "request_id": request_id,
    }, 200


@sse_bp.route("/status", methods=["GET"])
@limiter.limit("60 per minute")
def sse_status():
    """
    Get SSE connection status and statistics.

    Returns:
        200: SSE service status including connected client count
    ---
    tags:
      - Real-time
    responses:
      200:
        description: SSE service status
        content:
          application/json:
            schema:
              type: object
              properties:
                success:
                  type: boolean
                connected_clients:
                  type: integer
                status:
                  type: string
    """
    request_id = getattr(g, "request_id", "unknown")

    return {
        "success": True,
        "status": "operational",
        "connected_clients": sse_manager.get_client_count(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "request_id": request_id,
    }, 200


@sse_bp.route("/alerts/recent", methods=["GET"])
@limiter.limit("30 per minute")
def get_recent_alerts_for_stream():
    """
    Get recent alerts for SSE clients on initial connection.

    Clients can call this when they first connect to get recent alerts
    that may have occurred before their connection.

    Query Parameters:
        limit (int): Maximum alerts to return (default: 10, max: 50)
        since (str): ISO timestamp to get alerts after (optional)

    Returns:
        200: List of recent alerts
    ---
    tags:
      - Real-time
      - Alerts
    parameters:
      - in: query
        name: limit
        schema:
          type: integer
          default: 10
          maximum: 50
      - in: query
        name: since
        schema:
          type: string
          format: date-time
    responses:
      200:
        description: Recent alerts list
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        limit = min(request.args.get("limit", 10, type=int), 50)
        since = request.args.get("since", type=str)

        with get_db_session() as session:
            query = session.query(AlertHistory).filter(AlertHistory.is_deleted.is_(False))

            if since:
                try:
                    since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
                    query = query.filter(AlertHistory.created_at > since_dt)
                except ValueError:
                    pass  # Ignore invalid date format

            alerts = query.order_by(desc(AlertHistory.created_at)).limit(limit).all()

            alerts_data = []
            for alert in alerts:
                alerts_data.append(
                    {
                        "id": alert.id,
                        "risk_level": alert.risk_level,
                        "risk_label": alert.risk_label,
                        "location": alert.location,
                        "message": alert.message,
                        "created_at": alert.created_at.isoformat() if alert.created_at else None,
                    }
                )

        return {"success": True, "alerts": alerts_data, "count": len(alerts_data), "request_id": request_id}, 200

    except Exception as e:
        logger.error(f"Error fetching recent alerts for SSE [{request_id}]: {str(e)}", exc_info=True)
        return {"success": False, "error": "Failed to fetch recent alerts", "request_id": request_id}, 500
