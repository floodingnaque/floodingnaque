"""
Server-Sent Events (SSE) routes for real-time alerts.

Provides a persistent HTTP connection for the dashboard
to receive real-time flood alerts without polling.
"""

import json
import logging
import os
import time
from datetime import datetime, timezone

from flask import Blueprint, Response, jsonify, request, stream_with_context

logger = logging.getLogger(__name__)

sse_bp = Blueprint("sse", __name__)


@sse_bp.route("/alerts", methods=["GET"])
def stream_alerts():
    """
    Server-Sent Events stream for real-time flood alerts.

    The client connects with EventSource and receives alerts
    as they are created. Uses Redis pub/sub as the message broker.
    """

    def event_stream():
        """Generator that yields SSE events from Redis pub/sub."""
        try:
            import redis
            client = redis.from_url(
                os.getenv("REDIS_URL", "redis://localhost:6379/0"),
                decode_responses=True,
            )
            pubsub = client.pubsub()
            pubsub.subscribe("alert.triggered")

            # Send initial heartbeat
            yield f"event: connected\ndata: {json.dumps({'status': 'connected', 'service': 'alert-notification'})}\n\n"

            for message in pubsub.listen():
                if message["type"] == "message":
                    yield f"event: alert\ndata: {message['data']}\n\n"

                # Send heartbeat every 30 seconds to keep connection alive
                yield f": heartbeat {datetime.now(timezone.utc).isoformat()}\n\n"

        except Exception as e:
            logger.error("SSE stream error: %s", e)
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return Response(
        stream_with_context(event_stream()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@sse_bp.route("/test", methods=["POST"])
def test_sse():
    """Send a test SSE event (for development/testing)."""
    try:
        import redis
        client = redis.from_url(
            os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            decode_responses=True,
        )
        test_alert = {
            "event": "alert.triggered",
            "data": {
                "id": "test-alert",
                "severity": "moderate",
                "title": "Test Alert",
                "message": "This is a test alert from the notification service",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }
        client.publish("alert.triggered", json.dumps(test_alert))
        return jsonify({"success": True, "message": "Test event published"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
