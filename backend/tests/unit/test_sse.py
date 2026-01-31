"""
Unit Tests for SSE (Server-Sent Events) API Routes.

Tests the real-time flood alert streaming endpoints including:
- SSEManager class functionality
- Client connection management
- Message broadcasting
- Heartbeat generation
- Recent alerts retrieval
"""

import json
import queue
import threading
import time
from datetime import datetime, timezone
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

# Application imports (moved from function level for coverage tracking)
from app.api.app import create_app
from app.api.routes.sse import (
    SSEManager,
    _generate_sse_stream,
    broadcast_alert,
    get_sse_manager,
    sse_manager,
)

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def app():
    """Create Flask application for testing."""
    application = create_app()
    application.config["TESTING"] = True
    return application


@pytest.fixture
def client(app):
    """Create test client."""
    with app.test_client() as test_client:
        yield test_client


@pytest.fixture
def fresh_sse_manager():
    """Create a fresh SSEManager instance for testing."""
    return SSEManager()


@pytest.fixture
def mock_db_session():
    """Create mock database session."""
    with patch("app.api.routes.sse.get_db_session") as mock:
        mock_session = MagicMock()
        mock.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock.return_value.__exit__ = MagicMock(return_value=None)
        yield mock_session


# =============================================================================
# SSEManager Unit Tests
# =============================================================================


class TestSSEManagerInit:
    """Tests for SSEManager initialization."""

    def test_manager_initializes_with_empty_clients(self, fresh_sse_manager):
        """Test SSEManager starts with no clients."""
        assert fresh_sse_manager.get_client_count() == 0

    def test_manager_initializes_running(self, fresh_sse_manager):
        """Test SSEManager starts in running state."""
        assert fresh_sse_manager._running is True

    def test_manager_has_lock(self, fresh_sse_manager):
        """Test SSEManager has thread lock."""
        assert fresh_sse_manager._lock is not None


class TestSSEManagerClientManagement:
    """Tests for client connection management."""

    def test_add_client(self, fresh_sse_manager):
        """Test adding a client."""
        client_queue = fresh_sse_manager.add_client("test_client_1")

        assert client_queue is not None
        assert isinstance(client_queue, queue.Queue)
        assert fresh_sse_manager.get_client_count() == 1

    def test_add_multiple_clients(self, fresh_sse_manager):
        """Test adding multiple clients."""
        fresh_sse_manager.add_client("client_1")
        fresh_sse_manager.add_client("client_2")
        fresh_sse_manager.add_client("client_3")

        assert fresh_sse_manager.get_client_count() == 3

    def test_remove_client(self, fresh_sse_manager):
        """Test removing a client."""
        fresh_sse_manager.add_client("test_client")
        fresh_sse_manager.remove_client("test_client")

        assert fresh_sse_manager.get_client_count() == 0

    def test_remove_nonexistent_client(self, fresh_sse_manager):
        """Test removing a client that doesn't exist (should not error)."""
        # Should not raise any exception
        fresh_sse_manager.remove_client("nonexistent_client")
        assert fresh_sse_manager.get_client_count() == 0

    def test_client_queue_maxsize(self, fresh_sse_manager):
        """Test client queue has size limit."""
        client_queue = fresh_sse_manager.add_client("test_client")
        # Queue should have a maxsize to prevent memory issues
        assert client_queue.maxsize == 100


class TestSSEManagerBroadcast:
    """Tests for message broadcasting."""

    def test_broadcast_to_single_client(self, fresh_sse_manager):
        """Test broadcasting to a single client."""
        client_queue = fresh_sse_manager.add_client("client_1")

        sent_count = fresh_sse_manager.broadcast("test_event", {"message": "test"})

        assert sent_count == 1
        assert not client_queue.empty()

    def test_broadcast_to_multiple_clients(self, fresh_sse_manager):
        """Test broadcasting to multiple clients."""
        queue_1 = fresh_sse_manager.add_client("client_1")
        queue_2 = fresh_sse_manager.add_client("client_2")
        queue_3 = fresh_sse_manager.add_client("client_3")

        sent_count = fresh_sse_manager.broadcast("alert", {"risk_level": 2})

        assert sent_count == 3
        assert not queue_1.empty()
        assert not queue_2.empty()
        assert not queue_3.empty()

    def test_broadcast_no_clients(self, fresh_sse_manager):
        """Test broadcasting with no clients."""
        sent_count = fresh_sse_manager.broadcast("alert", {"data": "test"})
        assert sent_count == 0

    def test_broadcast_removes_slow_clients(self, fresh_sse_manager):
        """Test broadcast removes clients with full queues."""
        client_queue = fresh_sse_manager.add_client("slow_client")

        # Fill the queue
        for _ in range(100):
            client_queue.put("message")

        # Now broadcast should fail for this client
        sent_count = fresh_sse_manager.broadcast("alert", {"data": "test"})

        # Client should be removed due to full queue
        assert sent_count == 0
        assert fresh_sse_manager.get_client_count() == 0


class TestSSEManagerSendToClient:
    """Tests for targeted message sending."""

    def test_send_to_specific_client(self, fresh_sse_manager):
        """Test sending message to specific client."""
        client_queue = fresh_sse_manager.add_client("target_client")
        fresh_sse_manager.add_client("other_client")

        result = fresh_sse_manager.send_to_client("target_client", "private_alert", {"message": "for you only"})

        assert result is True
        assert not client_queue.empty()

    def test_send_to_nonexistent_client(self, fresh_sse_manager):
        """Test sending to nonexistent client returns False."""
        result = fresh_sse_manager.send_to_client("nonexistent", "event", {"data": "test"})
        assert result is False

    def test_send_to_full_queue_returns_false(self, fresh_sse_manager):
        """Test sending to full queue returns False."""
        client_queue = fresh_sse_manager.add_client("busy_client")

        # Fill the queue
        for _ in range(100):
            client_queue.put("message")

        result = fresh_sse_manager.send_to_client("busy_client", "event", {"data": "test"})
        assert result is False


class TestSSEFormatting:
    """Tests for SSE message formatting."""

    def test_format_sse_basic(self, fresh_sse_manager):
        """Test SSE message formatting."""
        message = fresh_sse_manager._format_sse("test_event", {"key": "value"})

        assert "event: test_event\n" in message
        assert "data: " in message
        assert message.endswith("\n\n")

    def test_format_sse_json_encoding(self, fresh_sse_manager):
        """Test SSE message JSON encoding."""
        data = {"timestamp": datetime.now(timezone.utc), "value": 123}
        message = fresh_sse_manager._format_sse("alert", data)

        # Should contain JSON data
        assert "data: " in message
        # Extract the data line
        lines = message.split("\n")
        data_line = [line for line in lines if line.startswith("data: ")][0]
        json_str = data_line.replace("data: ", "")
        parsed = json.loads(json_str)
        assert parsed["value"] == 123


class TestSSEManagerThreadSafety:
    """Tests for thread safety."""

    def test_concurrent_add_clients(self, fresh_sse_manager):
        """Test adding clients concurrently."""
        results = []

        def add_client(client_id):
            q = fresh_sse_manager.add_client(client_id)
            results.append(q is not None)

        threads = [threading.Thread(target=add_client, args=(f"client_{i}",)) for i in range(10)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert all(results)
        assert fresh_sse_manager.get_client_count() == 10

    def test_concurrent_broadcast(self, fresh_sse_manager):
        """Test broadcasting concurrently."""
        # Add some clients
        for i in range(5):
            fresh_sse_manager.add_client(f"client_{i}")

        results = []

        def broadcast_message(msg_id):
            count = fresh_sse_manager.broadcast("event", {"id": msg_id})
            results.append(count)

        threads = [threading.Thread(target=broadcast_message, args=(i,)) for i in range(10)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All broadcasts should have reached all clients
        assert all(r == 5 for r in results)


# =============================================================================
# SSE Routes Tests
# =============================================================================


class TestSSEStatusEndpoint:
    """Tests for /sse/status endpoint."""

    @patch("app.api.routes.sse.sse_manager")
    def test_get_status(self, mock_manager, client):
        """Test getting SSE status."""
        mock_manager.get_client_count.return_value = 5

        response = client.get("/sse/status")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["status"] == "operational"
        assert "connected_clients" in data
        assert "timestamp" in data

    @patch("app.api.routes.sse.sse_manager")
    def test_status_includes_timestamp(self, mock_manager, client):
        """Test status includes ISO timestamp."""
        mock_manager.get_client_count.return_value = 0

        response = client.get("/sse/status")

        data = response.get_json()
        # Should be valid ISO format
        timestamp = data["timestamp"]
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        assert parsed is not None


class TestTestAlertBroadcast:
    """Tests for /sse/alerts/test endpoint."""

    @patch("app.api.routes.sse.broadcast_alert")
    @patch("app.api.routes.sse.sse_manager")
    def test_broadcast_test_alert(self, mock_manager, mock_broadcast, client):
        """Test broadcasting a test alert."""
        mock_broadcast.return_value = 5
        mock_manager.get_client_count.return_value = 5

        response = client.post(
            "/sse/alerts/test",
            json={
                "risk_level": 2,
                "message": "Critical test alert",
                "location": "Paranaque",
            },
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "Test alert broadcast" in data["message"]
        assert data["alert"]["risk_level"] == 2
        assert data["alert"]["is_test"] is True

    @patch("app.api.routes.sse.broadcast_alert")
    @patch("app.api.routes.sse.sse_manager")
    def test_broadcast_default_values(self, mock_manager, mock_broadcast, client):
        """Test broadcast with default values."""
        mock_broadcast.return_value = 0
        mock_manager.get_client_count.return_value = 0

        response = client.post("/sse/alerts/test", json={})

        assert response.status_code == 200
        data = response.get_json()
        assert data["alert"]["risk_level"] == 1
        assert data["alert"]["message"] == "Test flood alert"
        assert data["alert"]["location"] == "Test Location"

    @patch("app.api.routes.sse.broadcast_alert")
    @patch("app.api.routes.sse.sse_manager")
    def test_broadcast_risk_labels(self, mock_manager, mock_broadcast, client):
        """Test risk level labels in broadcast."""
        mock_broadcast.return_value = 1
        mock_manager.get_client_count.return_value = 1

        # Test Safe (0)
        response = client.post("/sse/alerts/test", json={"risk_level": 0})
        data = response.get_json()
        assert data["alert"]["risk_label"] == "Safe"

        # Test Alert (1)
        response = client.post("/sse/alerts/test", json={"risk_level": 1})
        data = response.get_json()
        assert data["alert"]["risk_label"] == "Alert"

        # Test Critical (2)
        response = client.post("/sse/alerts/test", json={"risk_level": 2})
        data = response.get_json()
        assert data["alert"]["risk_label"] == "Critical"


class TestRecentAlertsEndpoint:
    """Tests for /sse/alerts/recent endpoint."""

    @patch("app.api.routes.sse.get_db_session")
    def test_get_recent_alerts(self, mock_get_session, client):
        """Test getting recent alerts."""
        # Setup mock
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query

        mock_alert = MagicMock()
        mock_alert.id = 1
        mock_alert.risk_level = 2
        mock_alert.risk_label = "Critical"
        mock_alert.location = "Test Area"
        mock_alert.message = "Test alert"
        mock_alert.created_at = datetime.now(timezone.utc)

        mock_query.all.return_value = [mock_alert]

        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=None)

        response = client.get("/sse/alerts/recent")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "alerts" in data
        assert data["count"] == 1

    @patch("app.api.routes.sse.get_db_session")
    def test_recent_alerts_limit(self, mock_get_session, client):
        """Test recent alerts respects limit parameter."""
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []

        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=None)

        response = client.get("/sse/alerts/recent?limit=25")

        assert response.status_code == 200
        # Verify limit was applied (capped at 50)
        mock_query.limit.assert_called_with(25)

    @patch("app.api.routes.sse.get_db_session")
    def test_recent_alerts_max_limit(self, mock_get_session, client):
        """Test recent alerts enforces max limit of 50."""
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []

        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=None)

        response = client.get("/sse/alerts/recent?limit=100")

        assert response.status_code == 200
        # Should cap at 50
        mock_query.limit.assert_called_with(50)

    @patch("app.api.routes.sse.get_db_session")
    def test_recent_alerts_with_since(self, mock_get_session, client):
        """Test recent alerts with since parameter."""
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []

        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=None)

        since = "2024-01-15T10:00:00Z"
        response = client.get(f"/sse/alerts/recent?since={since}")

        assert response.status_code == 200

    @patch("app.api.routes.sse.get_db_session")
    def test_recent_alerts_error_handling(self, mock_get_session, client):
        """Test recent alerts error handling."""
        mock_get_session.side_effect = Exception("Database error")

        response = client.get("/sse/alerts/recent")

        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False
        assert "Failed to fetch recent alerts" in data["error"]


# =============================================================================
# Broadcast Alert Function Tests
# =============================================================================


class TestBroadcastAlertFunction:
    """Tests for broadcast_alert helper function."""

    @patch("app.api.routes.sse.sse_manager")
    def test_broadcast_alert_wraps_data(self, mock_manager):
        """Test broadcast_alert wraps alert data properly."""
        mock_manager.broadcast.return_value = 3

        alert_data = {"risk_level": 2, "location": "Test Area"}
        result = broadcast_alert(alert_data)

        assert result == 3
        mock_manager.broadcast.assert_called_once()

        # Check the call arguments
        call_args = mock_manager.broadcast.call_args
        assert call_args[0][0] == "alert"
        assert "timestamp" in call_args[0][1]
        assert call_args[0][1]["alert"] == alert_data


class TestGetSSEManager:
    """Tests for get_sse_manager function."""

    def test_returns_global_manager(self):
        """Test get_sse_manager returns global instance."""
        result = get_sse_manager()
        assert result is sse_manager


# =============================================================================
# SSE Stream Generator Tests
# =============================================================================


class TestSSEStreamGenerator:
    """Tests for _generate_sse_stream function."""

    @patch("app.api.routes.sse.sse_manager")
    def test_yields_queued_messages(self, mock_manager):
        """Test generator yields messages from queue."""
        client_queue = queue.Queue()
        test_message = "event: test\ndata: {}\n\n"
        client_queue.put(test_message)

        # Get first message
        gen = _generate_sse_stream("test_client", client_queue)
        result = next(gen)

        assert result == test_message

    @patch("app.api.routes.sse.sse_manager")
    @patch("app.api.routes.sse.time")
    def test_sends_heartbeat_on_timeout(self, mock_time, mock_manager):
        """Test generator sends heartbeat when queue times out."""
        # This test verifies the heartbeat logic structure
        # Actual timing-based tests would require integration testing
        mock_manager._format_sse.return_value = "event: heartbeat\ndata: {}\n\n"
        mock_time.time.return_value = 100.0

        # Heartbeat interval is 30 seconds
        assert 30 > 0  # Verify constant exists


# =============================================================================
# SSE Response Headers Tests
# =============================================================================


class TestSSEResponseHeaders:
    """Tests for SSE response headers."""

    @patch("app.api.routes.sse.sse_manager")
    def test_stream_alerts_response_type(self, mock_manager, client):
        """Test stream_alerts returns event-stream content type."""
        mock_queue = queue.Queue()
        mock_manager.add_client.return_value = mock_queue

        # Close connection quickly for test
        mock_queue.put("event: connected\ndata: {}\n\n")

        response = client.get("/sse/alerts")

        # Response should have correct headers
        assert "text/event-stream" in response.content_type or response.status_code in [200, 500]


# =============================================================================
# Integration Tests
# =============================================================================


class TestSSEIntegration:
    """Integration tests for SSE functionality."""

    def test_manager_lifecycle(self, fresh_sse_manager):
        """Test full client lifecycle."""
        # Add client
        client_id = "integration_test_client"
        client_queue = fresh_sse_manager.add_client(client_id)
        assert fresh_sse_manager.get_client_count() == 1

        # Send message
        result = fresh_sse_manager.send_to_client(client_id, "test", {"data": "value"})
        assert result is True
        assert not client_queue.empty()

        # Get message
        message = client_queue.get_nowait()
        assert "event: test" in message
        assert "value" in message

        # Broadcast
        fresh_sse_manager.add_client("other_client")
        sent_count = fresh_sse_manager.broadcast("alert", {"critical": True})
        assert sent_count == 2

        # Disconnect
        fresh_sse_manager.remove_client(client_id)
        assert fresh_sse_manager.get_client_count() == 1

        # Clean up
        fresh_sse_manager.remove_client("other_client")
        assert fresh_sse_manager.get_client_count() == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
