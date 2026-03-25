"""
Prometheus Metrics Module for Floodingnaque API.

Provides application metrics for monitoring and alerting.
Exposes metrics at /metrics endpoint.
"""

import logging
import os
from typing import Optional

from flask import Flask

logger = logging.getLogger(__name__)

# Metrics instance (lazy initialized)
_metrics = None


def init_prometheus_metrics(app: Flask) -> Optional[object]:
    """
    Initialize Prometheus metrics for the Flask application.

    Provides:
    - Request latency histograms
    - Request count by endpoint and status
    - Custom application metrics

    Args:
        app: Flask application instance

    Returns:
        PrometheusMetrics instance or None if initialization fails
    """
    global _metrics

    # Check if metrics are enabled
    metrics_enabled = os.getenv("PROMETHEUS_METRICS_ENABLED", "True").lower() == "true"

    if not metrics_enabled:
        logger.info("Prometheus metrics disabled via PROMETHEUS_METRICS_ENABLED")
        return None

    try:
        from prometheus_flask_exporter import PrometheusMetrics

        # Initialize metrics with custom configuration
        _metrics = PrometheusMetrics(
            app,
            group_by="endpoint",  # Group metrics by endpoint
            default_labels={"application": "floodingnaque", "version": os.getenv("APP_VERSION", "2.0.0")},
            export_defaults=True,  # Export default Flask metrics
            defaults_prefix="floodingnaque",
        )

        # Register custom metrics
        _register_custom_metrics(_metrics)

        logger.info("Prometheus metrics enabled at /metrics")
        return _metrics

    except ImportError:
        logger.warning(
            "prometheus_flask_exporter not installed. " "Install with: pip install prometheus-flask-exporter"
        )
        return None
    except Exception as e:
        logger.error(f"Failed to initialize Prometheus metrics: {e}")
        return None


def _register_custom_metrics(metrics):
    """
    Register custom application metrics.

    Args:
        metrics: PrometheusMetrics instance
    """
    from prometheus_client import Counter, Gauge, Histogram, Info, Summary

    # === Prediction Metrics ===
    # Prediction counter by risk level
    metrics.predictions_total = Counter(
        "floodingnaque_predictions_total", "Total number of flood predictions", ["risk_level", "model_version"]
    )

    # Prediction latency histogram (detailed buckets for SLA monitoring)
    metrics.prediction_duration = Histogram(
        "floodingnaque_prediction_duration_seconds",
        "Time spent on flood prediction",
        buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
    )

    # Prediction latency summary (for percentile calculations)
    metrics.prediction_latency_summary = Summary(
        "floodingnaque_prediction_latency_seconds",
        "Prediction latency summary with quantiles",
    )

    # === External API Metrics ===

    # External API call counter
    metrics.external_api_calls_total = Counter(
        "floodingnaque_external_api_calls_total", "Total external API calls", ["api", "status"]
    )

    # External API latency
    metrics.external_api_duration = Histogram(
        "floodingnaque_external_api_duration_seconds",
        "External API call duration",
        ["api"],
        buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    )

    # Circuit breaker status
    metrics.circuit_breaker_state = Gauge(
        "floodingnaque_circuit_breaker_state", "Circuit breaker state (0=closed, 1=open, 2=half-open)", ["api"]
    )

    # === Database Metrics ===

    # Database query latency
    metrics.db_query_duration = Histogram(
        "floodingnaque_db_query_duration_seconds",
        "Database query duration",
        ["query_type"],
        buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5],
    )

    # Database connection pool gauge
    metrics.db_pool_connections = Gauge(
        "floodingnaque_db_pool_connections",
        "Database connection pool status",
        ["status"],  # checked_out, checked_in, overflow
    )

    # === Cache Metrics ===

    # Cache hit/miss counter
    metrics.cache_operations = Counter(
        "floodingnaque_cache_operations_total",
        "Cache operations",
        ["operation", "result"],  # operation: get/set, result: hit/miss/error
    )

    # Cache hit rate gauge (calculated metric)
    metrics.cache_hit_rate = Gauge(
        "floodingnaque_cache_hit_rate",
        "Current cache hit rate percentage (0-100)",
        ["cache_type"],  # redis, query, memory
    )

    # Cache entries gauge
    metrics.cache_entries = Gauge("floodingnaque_cache_entries", "Number of entries in cache", ["cache_type"])

    # Cache memory usage
    metrics.cache_memory_bytes = Gauge(
        "floodingnaque_cache_memory_bytes", "Cache memory usage in bytes", ["cache_type"]
    )

    # === Alert Metrics ===

    # Alerts sent counter
    metrics.alerts_sent_total = Counter(
        "floodingnaque_alerts_sent_total", "Total alerts sent", ["risk_level", "channel"]
    )

    # === Push Notification Metrics ===

    # Push delivery counters
    metrics.push_delivered_total = Counter(
        "floodingnaque_push_delivered_total", "Total push notifications delivered successfully"
    )
    metrics.push_failed_total = Counter(
        "floodingnaque_push_failed_total", "Total push notifications that failed to deliver"
    )
    metrics.push_expired_total = Counter(
        "floodingnaque_push_expired_total", "Total push subscriptions expired (410 Gone)"
    )

    # === Model Metrics ===

    # Model info
    metrics.model_info = Info("floodingnaque_model", "ML model information")

    # Model accuracy gauge
    metrics.model_accuracy = Gauge("floodingnaque_model_accuracy", "Current model accuracy")

    return metrics


def get_metrics():
    """Get the metrics instance."""
    return _metrics


# === Metric Recording Helpers ===


def record_prediction(risk_level: str, model_version: str, duration: float):
    """
    Record a prediction metric.

    Args:
        risk_level: Risk level (Safe/Alert/Critical)
        model_version: Model version used
        duration: Prediction duration in seconds
    """
    if _metrics:
        _metrics.predictions_total.labels(risk_level=risk_level, model_version=str(model_version)).inc()
        _metrics.prediction_duration.observe(duration)


def record_external_api_call(api: str, status: str, duration: float):
    """
    Record an external API call metric.

    Args:
        api: API name (openweathermap/weatherstack/meteostat)
        status: Call status (success/error/timeout)
        duration: Call duration in seconds
    """
    if _metrics and hasattr(_metrics, "external_api_calls_total"):
        _metrics.external_api_calls_total.labels(api=api, status=status).inc()
        _metrics.external_api_duration.labels(api=api).observe(duration)


def record_circuit_breaker_state(api: str, state: str):
    """
    Record circuit breaker state.

    Args:
        api: API name
        state: State (closed/open/half-open)
    """
    if _metrics and hasattr(_metrics, "circuit_breaker_state"):
        state_value = {"closed": 0, "open": 1, "half-open": 2}.get(state, -1)
        _metrics.circuit_breaker_state.labels(api=api).set(state_value)


def record_db_pool_status(checked_out: int, checked_in: int, overflow: int):
    """
    Record database pool status.

    Args:
        checked_out: Connections checked out
        checked_in: Connections checked in
        overflow: Overflow connections
    """
    if _metrics:
        _metrics.db_pool_connections.labels(status="checked_out").set(checked_out)
        _metrics.db_pool_connections.labels(status="checked_in").set(checked_in)
        _metrics.db_pool_connections.labels(status="overflow").set(overflow)


def record_cache_operation(operation: str, result: str):
    """
    Record cache operation.

    Args:
        operation: Operation type (get/set/delete)
        result: Result (hit/miss/success/error)
    """
    if _metrics:
        _metrics.cache_operations.labels(operation=operation, result=result).inc()


def record_alert_sent(risk_level: str, channel: str):
    """
    Record alert sent.

    Args:
        risk_level: Risk level
        channel: Alert channel (web/sms/email)
    """
    if _metrics:
        _metrics.alerts_sent_total.labels(risk_level=risk_level, channel=channel).inc()


def update_model_info(version: str, accuracy: float, model_type: str):
    """
    Update model information metrics.

    Args:
        version: Model version
        accuracy: Model accuracy (0-1)
        model_type: Model type (e.g., 'RandomForest')
    """
    if _metrics:
        _metrics.model_info.info({"version": str(version), "type": model_type})
        _metrics.model_accuracy.set(accuracy)


def record_prediction_latency(duration: float):
    """
    Record prediction latency in the summary metric.

    Args:
        duration: Prediction duration in seconds
    """
    if _metrics:
        _metrics.prediction_latency_summary.observe(duration)


def update_cache_hit_rate(cache_type: str, hit_rate: float):
    """
    Update cache hit rate gauge.

    Args:
        cache_type: Type of cache (redis/query/memory)
        hit_rate: Hit rate percentage (0-100)
    """
    if _metrics:
        _metrics.cache_hit_rate.labels(cache_type=cache_type).set(hit_rate)


def update_cache_entries(cache_type: str, entries: int):
    """
    Update cache entries gauge.

    Args:
        cache_type: Type of cache (redis/query/memory)
        entries: Number of cache entries
    """
    if _metrics:
        _metrics.cache_entries.labels(cache_type=cache_type).set(entries)


def update_cache_memory(cache_type: str, memory_bytes: int):
    """
    Update cache memory usage gauge.

    Args:
        cache_type: Type of cache (redis/query/memory)
        memory_bytes: Memory usage in bytes
    """
    if _metrics:
        _metrics.cache_memory_bytes.labels(cache_type=cache_type).set(memory_bytes)


def collect_cache_metrics():
    """
    Collect and update all cache metrics from various cache sources.
    Call this periodically (e.g., every 30 seconds) to update gauges.
    """
    if not _metrics:
        return

    try:
        # Query cache metrics
        from app.utils.query_optimizer import get_query_cache_stats

        query_stats = get_query_cache_stats()
        update_cache_hit_rate("query", query_stats.get("hit_rate_percent", 0))
        update_cache_entries("query", query_stats.get("entries", 0))
    except ImportError:
        pass
    except Exception as e:
        logger.debug(f"Error collecting query cache metrics: {e}")

    try:
        # Redis cache metrics
        from app.utils.resilience.cache import get_cache_stats

        redis_stats = get_cache_stats()
        if redis_stats.get("connected"):
            update_cache_entries("redis", redis_stats.get("keys_count", 0))
            # Parse memory from human-readable format (e.g., "1.2M")
            memory_str = redis_stats.get("used_memory_human", "0")
            memory_bytes = _parse_memory_string(memory_str)
            update_cache_memory("redis", memory_bytes)
    except ImportError:
        pass
    except Exception as e:
        logger.debug(f"Error collecting Redis cache metrics: {e}")


def _parse_memory_string(memory_str: str) -> int:
    """
    Parse Redis memory string (e.g., '1.2M', '500K') to bytes.

    Args:
        memory_str: Human-readable memory string

    Returns:
        int: Memory in bytes
    """
    try:
        if not memory_str or memory_str == "0":
            return 0

        memory_str = memory_str.strip().upper()
        multipliers = {
            "K": 1024,
            "M": 1024 * 1024,
            "G": 1024 * 1024 * 1024,
            "B": 1,
        }

        for suffix, multiplier in multipliers.items():
            if memory_str.endswith(suffix):
                return int(float(memory_str[:-1]) * multiplier)

        return int(float(memory_str))
    except (ValueError, TypeError):
        return 0
