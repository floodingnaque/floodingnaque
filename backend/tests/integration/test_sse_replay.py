"""
Integration tests for SSE event replay and event ID tracking.

Tests the SSEManager class and /api/v1/sse/alerts endpoint:
- Event IDs are monotonically increasing
- Replay buffer stores non-heartbeat events
- get_events_since() returns correct subset
- _format_sse includes event ID
- Heartbeats are excluded from replay buffer
"""

import json

import pytest
from app.api.routes.sse import SSEManager


class TestSSEManagerEventIDs:
    """Tests for SSEManager event ID generation."""

    def test_event_ids_are_monotonic(self):
        """Event IDs increase monotonically."""
        mgr = SSEManager()
        ids = [mgr._next_event_id() for _ in range(10)]
        assert ids == list(range(1, 11))

    def test_broadcast_assigns_event_id(self):
        """Broadcast messages include event IDs."""
        mgr = SSEManager()
        client_q = mgr.add_client("test-1")

        mgr.broadcast("alert", {"level": "Critical"})
        msg = client_q.get_nowait()
        assert "id: 1\n" in msg
        assert "event: alert\n" in msg

        mgr.broadcast("alert", {"level": "Safe"})
        msg2 = client_q.get_nowait()
        assert "id: 2\n" in msg2

    def test_send_to_client_assigns_event_id(self):
        """Direct sends also get an event ID."""
        mgr = SSEManager()
        client_q = mgr.add_client("test-1")

        mgr.send_to_client("test-1", "update", {"foo": "bar"})
        msg = client_q.get_nowait()
        assert "id: " in msg


class TestSSEReplayBuffer:
    """Tests for SSEManager replay buffer."""

    def test_replay_buffer_stores_events(self):
        """Non-heartbeat events are stored in the replay buffer."""
        mgr = SSEManager()
        mgr.broadcast("alert", {"level": "Critical"})
        mgr.broadcast("alert", {"level": "Alert"})

        assert len(mgr._replay_buffer) == 2

    def test_heartbeats_excluded_from_buffer(self):
        """Heartbeat events are not stored in the replay buffer."""
        mgr = SSEManager()
        mgr.broadcast("alert", {"level": "Critical"})
        mgr.broadcast("heartbeat", {"ts": "2025-01-15T10:00:00Z"})
        mgr.broadcast("alert", {"level": "Safe"})

        assert len(mgr._replay_buffer) == 2  # Only 2 alerts, no heartbeat

    def test_get_events_since_returns_subset(self):
        """get_events_since returns only events after the given ID."""
        mgr = SSEManager()
        mgr.broadcast("alert", {"n": 1})
        mgr.broadcast("alert", {"n": 2})
        mgr.broadcast("alert", {"n": 3})
        mgr.broadcast("alert", {"n": 4})

        # Get events after ID 2
        events = mgr.get_events_since(2)
        assert len(events) == 2
        assert '"n": 3' in events[0]
        assert '"n": 4' in events[1]

    def test_get_events_since_zero_returns_all(self):
        """last_event_id=0 returns all buffered events."""
        mgr = SSEManager()
        mgr.broadcast("alert", {"n": 1})
        mgr.broadcast("alert", {"n": 2})

        events = mgr.get_events_since(0)
        assert len(events) == 2

    def test_get_events_since_future_returns_empty(self):
        """last_event_id beyond current counter returns empty list."""
        mgr = SSEManager()
        mgr.broadcast("alert", {"n": 1})

        events = mgr.get_events_since(999)
        assert events == []

    def test_replay_buffer_max_size(self):
        """Replay buffer respects REPLAY_BUFFER_SIZE limit."""
        mgr = SSEManager()
        for i in range(SSEManager.REPLAY_BUFFER_SIZE + 50):
            mgr.broadcast("alert", {"n": i})

        assert len(mgr._replay_buffer) == SSEManager.REPLAY_BUFFER_SIZE


class TestSSEFormatting:
    """Tests for SSE message formatting."""

    def test_format_sse_with_event_id(self):
        """_format_sse includes id field when provided."""
        msg = SSEManager._format_sse("alert", {"level": "Critical"}, event_id=42)
        assert "id: 42\n" in msg
        assert "event: alert\n" in msg
        assert "data: " in msg

    def test_format_sse_without_event_id(self):
        """_format_sse omits id field when not provided."""
        msg = SSEManager._format_sse("alert", {"level": "Safe"})
        assert "id:" not in msg
        assert "event: alert\n" in msg

    def test_format_sse_valid_json_data(self):
        """Data field contains valid JSON."""
        data = {"level": "Critical", "barangay": "BF Homes"}
        msg = SSEManager._format_sse("alert", data, event_id=1)
        # Extract data line
        data_line = [line for line in msg.split("\n") if line.startswith("data: ")][0]
        parsed = json.loads(data_line[len("data: ") :])
        assert parsed == data


class TestSSEClientManagement:
    """Tests for SSE client connect/disconnect."""

    def test_add_and_remove_client(self):
        """Clients can be added and removed."""
        mgr = SSEManager()
        q = mgr.add_client("c1")
        assert mgr.get_client_count() == 1

        mgr.remove_client("c1")
        assert mgr.get_client_count() == 0

    def test_broadcast_to_multiple_clients(self):
        """Broadcast sends to all connected clients."""
        mgr = SSEManager()
        q1 = mgr.add_client("c1")
        q2 = mgr.add_client("c2")

        count = mgr.broadcast("alert", {"level": "Alert"})
        assert count == 2
        assert not q1.empty()
        assert not q2.empty()

    def test_remove_nonexistent_client(self):
        """Removing a nonexistent client is a no-op."""
        mgr = SSEManager()
        mgr.remove_client("does-not-exist")  # Should not raise
        assert mgr.get_client_count() == 0
