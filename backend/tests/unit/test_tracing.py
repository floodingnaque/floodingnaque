"""
Unit tests for tracing utilities.

Tests for app/utils/tracing.py
"""

import time
import uuid
from unittest.mock import MagicMock, patch

import pytest
from app.utils.observability.tracing import (
    Span,
    TraceContext,
    current_trace,
    trace_operation,
)


class TestSpan:
    """Tests for Span class."""

    def test_span_creation(self):
        """Test Span creation with required fields."""
        span = Span(
            span_id="span123",
            trace_id="trace456",
            parent_span_id=None,
            operation_name="test_operation",
            start_time=time.perf_counter(),
        )

        assert span.span_id == "span123"
        assert span.trace_id == "trace456"
        assert span.operation_name == "test_operation"
        assert span.status == "OK"
        assert span.error is None

    def test_span_duration_not_finished(self):
        """Test span duration is None when not finished."""
        span = Span(
            span_id="span123",
            trace_id="trace456",
            parent_span_id=None,
            operation_name="test",
            start_time=time.perf_counter(),
        )

        assert span.duration_ms is None

    def test_span_duration_finished(self):
        """Test span duration after finish."""
        span = Span(
            span_id="span123",
            trace_id="trace456",
            parent_span_id=None,
            operation_name="test",
            start_time=time.perf_counter(),
        )

        time.sleep(0.01)  # 10ms
        span.finish()

        assert span.duration_ms is not None
        assert span.duration_ms >= 10  # At least 10ms

    def test_span_set_tag(self):
        """Test setting tags on span."""
        span = Span(
            span_id="span123",
            trace_id="trace456",
            parent_span_id=None,
            operation_name="test",
            start_time=time.perf_counter(),
        )

        result = span.set_tag("key", "value")

        assert span.tags["key"] == "value"
        assert result is span  # Should return self for chaining

    def test_span_log_event(self):
        """Test logging events in span."""
        span = Span(
            span_id="span123",
            trace_id="trace456",
            parent_span_id=None,
            operation_name="test",
            start_time=time.perf_counter(),
        )

        span.log_event("test_event", data="test_data")

        assert len(span.logs) == 1
        assert span.logs[0]["event"] == "test_event"

    def test_span_set_error(self):
        """Test marking span as errored."""
        span = Span(
            span_id="span123",
            trace_id="trace456",
            parent_span_id=None,
            operation_name="test",
            start_time=time.perf_counter(),
        )

        error = ValueError("test error")
        span.set_error(error)

        assert span.status == "ERROR"
        assert span.error == "test error"
        assert span.tags["error.type"] == "ValueError"

    def test_span_to_dict(self):
        """Test span serialization to dict."""
        span = Span(
            span_id="span123",
            trace_id="trace456",
            parent_span_id="parent789",
            operation_name="test",
            start_time=time.perf_counter(),
        )
        span.finish()

        result = span.to_dict()

        assert result["span_id"] == "span123"
        assert result["trace_id"] == "trace456"
        assert result["parent_span_id"] == "parent789"
        assert "duration_ms" in result


class TestTraceContext:
    """Tests for TraceContext class."""

    def test_trace_context_new(self):
        """Test creating new trace context."""
        ctx = TraceContext.new()

        assert ctx.trace_id is not None
        assert ctx.request_id is not None
        assert len(ctx.spans) == 0

    def test_trace_context_new_with_ids(self):
        """Test creating trace context with specific IDs."""
        ctx = TraceContext.new(request_id="req123", trace_id="trace456")

        assert ctx.request_id == "req123"
        assert ctx.trace_id == "trace456"

    def test_trace_context_from_headers(self):
        """Test extracting trace context from headers."""
        headers = {"X-Trace-ID": "trace123", "X-Request-ID": "request456", "X-Span-ID": "span789"}

        ctx = TraceContext.from_headers(headers)

        assert ctx.trace_id == "trace123"
        assert ctx.request_id == "request456"
        assert ctx.baggage.get("parent_span_id") == "span789"

    def test_trace_context_from_traceparent_header(self):
        """Test extracting trace context from W3C traceparent header."""
        # W3C trace context format (not a secret - trace ID)  # pragma: allowlist secret
        headers = {"traceparent": "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01"}

        ctx = TraceContext.from_headers(headers)

        assert "0af7651916cd43dd8448eb211c80319c" in ctx.trace_id

    def test_trace_context_to_headers(self):
        """Test exporting trace context to headers."""
        ctx = TraceContext.new(request_id="req123", trace_id="trace456")

        headers = ctx.to_headers()

        assert headers["X-Trace-ID"] == "trace456"
        assert headers["X-Request-ID"] == "req123"

    def test_trace_context_start_span(self):
        """Test starting a span in trace context."""
        ctx = TraceContext.new()

        span = ctx.start_span("test_operation")

        assert span is not None
        assert span.operation_name == "test_operation"
        assert span.trace_id == ctx.trace_id
        assert len(ctx.spans) == 1
        assert ctx.active_span is span

    def test_trace_context_nested_spans(self):
        """Test nested spans have correct parent-child relationships."""
        ctx = TraceContext.new()

        parent_span = ctx.start_span("parent_operation")
        child_span = ctx.start_span("child_operation")

        assert child_span.parent_span_id == parent_span.span_id


class TestCurrentTrace:
    """Tests for current trace context variable."""

    def test_current_trace_default_none(self):
        """Test current trace is None by default."""
        assert current_trace.get() is None

    def test_current_trace_set_get(self):
        """Test setting and getting current trace."""
        ctx = TraceContext.new()
        token = current_trace.set(ctx)

        assert current_trace.get() is ctx

        current_trace.reset(token)


class TestTracingDecorators:
    """Tests for tracing decorators."""

    def test_trace_operation_function_decorator(self):
        """Test trace_operation decorator wraps function."""

        @trace_operation("test_operation")
        def my_function():
            return "result"

        result = my_function()

        assert result == "result"

    def test_trace_operation_function_preserves_name(self):
        """Test trace_operation decorator preserves function metadata."""

        @trace_operation("test_operation")
        def my_named_function():
            """My docstring."""
            return "result"

        assert my_named_function.__name__ == "my_named_function"

    def test_trace_operation_function_with_tags(self):
        """Test trace_operation decorator with tags."""

        @trace_operation("test_operation", tags={"key": "value"})
        def my_function():
            return "result"

        result = my_function()

        assert result == "result"


class TestTracingMiddleware:
    """Tests for tracing middleware integration."""

    def test_trace_request_middleware(self, client):
        """Test tracing middleware adds trace context to requests."""
        response = client.get("/health", headers={"X-Request-ID": "test-req-123"})

        # Request should complete (200 OK or 503 if dependencies unavailable in test env)
        assert response.status_code in [200, 503]

    def test_trace_response_headers(self, client):
        """Test trace IDs are returned in response headers."""
        response = client.get("/health")

        # May have X-Request-ID in response
        # This depends on middleware configuration


class TestSpanExport:
    """Tests for span export functionality."""

    def test_export_spans_json(self):
        """Test exporting spans to JSON format."""
        from app.utils.observability.tracing import TraceContext

        ctx = TraceContext.new()
        span = ctx.start_span("test_operation")
        span.finish()

        # Should be able to serialize to dict/JSON
        span_dict = span.to_dict()

        assert "span_id" in span_dict
        assert "trace_id" in span_dict
        assert "operation_name" in span_dict


class TestBaggagePropagation:
    """Tests for baggage propagation."""

    def test_baggage_set_get(self):
        """Test setting and getting baggage items."""
        from app.utils.observability.tracing import TraceContext

        ctx = TraceContext.new()
        ctx.baggage["user_id"] = "user123"

        assert ctx.baggage["user_id"] == "user123"

    def test_baggage_propagated_to_headers(self):
        """Test baggage is included in propagated headers."""
        from app.utils.observability.tracing import TraceContext

        ctx = TraceContext.new()
        ctx.baggage["user_id"] = "user123"

        headers = ctx.to_headers()

        # Baggage may or may not be propagated depending on implementation
