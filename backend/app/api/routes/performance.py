"""
Performance Monitoring Routes.

Provides endpoints for monitoring API performance metrics,
cache statistics, and response time percentiles.
"""

import os
import statistics
import time
from collections import deque
from datetime import datetime, timezone

from app.api.middleware.auth import require_api_key
from app.models.db import get_db_session, get_pool_status
from app.utils.cache import (
    get_cache_stats,
    get_cache_warm_stats,
    is_cache_enabled,
    warm_cache,
)
from app.utils.logging import get_logger
from app.utils.query_optimizer import (
    clear_slow_query_log,
    get_database_health,
    get_index_usage_stats,
    get_query_cache_stats,
    get_query_statistics,
    get_slow_queries,
    get_table_statistics,
    get_unused_indexes,
    run_maintenance_recommendations,
)
from app.api.middleware.rate_limit import limiter
from flask import Blueprint, g, jsonify, request

logger = get_logger(__name__)

performance_bp = Blueprint("performance", __name__)

# ============================================================================
# Response Time Tracking
# ============================================================================

# Store response times for percentile calculations
_response_times: deque = deque(maxlen=10000)  # Keep last 10k requests
_endpoint_times: dict = {}  # Per-endpoint tracking
MAX_ENDPOINT_SAMPLES = 1000


def record_response_time(endpoint: str, duration_ms: float):
    """Record a response time for an endpoint."""
    _response_times.append(
        {
            "endpoint": endpoint,
            "duration_ms": duration_ms,
            "timestamp": time.time(),
        }
    )

    # Track per-endpoint
    if endpoint not in _endpoint_times:
        _endpoint_times[endpoint] = deque(maxlen=MAX_ENDPOINT_SAMPLES)
    _endpoint_times[endpoint].append(duration_ms)


def calculate_percentiles(times: list) -> dict:
    """Calculate response time percentiles."""
    if not times:
        return {"p50": 0, "p75": 0, "p90": 0, "p95": 0, "p99": 0}

    sorted_times = sorted(times)
    n = len(sorted_times)

    return {
        "p50": sorted_times[int(n * 0.50)] if n > 0 else 0,
        "p75": sorted_times[int(n * 0.75)] if n > 0 else 0,
        "p90": sorted_times[int(n * 0.90)] if n > 0 else 0,
        "p95": sorted_times[int(n * 0.95)] if n > 0 else 0,
        "p99": sorted_times[int(n * 0.99)] if n > 0 else 0,
    }


def get_response_time_stats() -> dict:
    """Get comprehensive response time statistics."""
    all_times = [r["duration_ms"] for r in _response_times]

    stats = {
        "total_requests_tracked": len(_response_times),
        "overall": {
            "min": round(min(all_times), 2) if all_times else 0,
            "max": round(max(all_times), 2) if all_times else 0,
            "avg": round(statistics.mean(all_times), 2) if all_times else 0,
            "median": round(statistics.median(all_times), 2) if all_times else 0,
            "percentiles": calculate_percentiles(all_times),
        },
        "by_endpoint": {},
    }

    # Per-endpoint stats
    for endpoint, times in _endpoint_times.items():
        times_list = list(times)
        if times_list:
            stats["by_endpoint"][endpoint] = {
                "count": len(times_list),
                "avg": round(statistics.mean(times_list), 2),
                "percentiles": calculate_percentiles(times_list),
            }

    return stats


# ============================================================================
# Performance Dashboard Endpoint
# ============================================================================


@performance_bp.route("/dashboard", methods=["GET"])
@limiter.limit("60 per minute")
def performance_dashboard():
    """
    Get comprehensive performance dashboard.

    Returns:
        Performance metrics including response times, cache stats, and database pool status.
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        dashboard = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": request_id,
            # Response Time Statistics
            "response_times": get_response_time_stats(),
            # Cache Statistics
            "cache": {
                "redis": get_cache_stats(),
                "query_cache": get_query_cache_stats(),
                "warming": get_cache_warm_stats(),
            },
            # Database Pool Status
            "database": {
                "pool": get_pool_status(),
            },
            # Slow Queries
            "slow_queries": {
                "threshold_ms": float(os.getenv("SLOW_QUERY_THRESHOLD_MS", "100")),
                "recent": get_slow_queries(5),
            },
            # System Info
            "system": {
                "environment": os.getenv("APP_ENV", "development"),
                "debug": os.getenv("FLASK_DEBUG", "False").lower() == "true",
            },
        }

        return jsonify(dashboard), 200

    except Exception:
        # Log the full exception details server-side only (not exposed to client)
        logger.error("Error generating performance dashboard", exc_info=True)
        # Return a generic error message without any exception details
        error_response = {
            "error": "PerformanceDashboardError",
            "message": "Failed to generate performance dashboard",
            "request_id": request_id,
        }
        return jsonify(error_response), 500


@performance_bp.route("/response-times", methods=["GET"])
@limiter.limit("60 per minute")
def get_response_times():
    """
    Get response time statistics with percentiles.

    Query Parameters:
        endpoint (str): Filter by specific endpoint
        minutes (int): Time window in minutes (default: 60)
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        endpoint_filter = request.args.get("endpoint")
        minutes = request.args.get("minutes", default=60, type=int)

        # Calculate time cutoff
        cutoff = time.time() - (minutes * 60)

        # Filter response times
        if endpoint_filter:
            times = [
                r["duration_ms"]
                for r in _response_times
                if r["endpoint"] == endpoint_filter and r["timestamp"] >= cutoff
            ]
        else:
            times = [r["duration_ms"] for r in _response_times if r["timestamp"] >= cutoff]

        if not times:
            return (
                jsonify(
                    {
                        "message": "No response time data available for the specified criteria",
                        "request_id": request_id,
                    }
                ),
                200,
            )

        result = {
            "count": len(times),
            "time_window_minutes": minutes,
            "endpoint": endpoint_filter or "all",
            "statistics": {
                "min": round(min(times), 2),
                "max": round(max(times), 2),
                "avg": round(statistics.mean(times), 2),
                "median": round(statistics.median(times), 2),
                "std_dev": round(statistics.stdev(times), 2) if len(times) > 1 else 0,
            },
            "percentiles": calculate_percentiles(times),
            "request_id": request_id,
        }

        return jsonify(result), 200

    except Exception:
        logger.error("Error getting response times", exc_info=True)
        return (
            jsonify(
                {
                    "error": "ResponseTimeError",
                    "message": "Failed to retrieve response times",
                    "request_id": request_id,
                }
            ),
            500,
        )


@performance_bp.route("/cache", methods=["GET"])
@limiter.limit("60 per minute")
def cache_statistics():
    """
    Get detailed cache statistics.

    Returns:
        Redis cache stats, query cache stats, and warming status.
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        stats = {
            "redis": get_cache_stats(),
            "query_cache": get_query_cache_stats(),
            "warming": get_cache_warm_stats(),
            "enabled": is_cache_enabled(),
            "request_id": request_id,
        }

        return jsonify(stats), 200

    except Exception:
        logger.error("Error getting cache statistics", exc_info=True)
        return (
            jsonify(
                {
                    "error": "CacheStatsError",
                    "message": "Failed to retrieve cache statistics",
                    "request_id": request_id,
                }
            ),
            500,
        )


@performance_bp.route("/cache/warm", methods=["POST"])
@limiter.limit("5 per minute")
@require_api_key
def trigger_cache_warming():
    """
    Trigger cache warming manually.

    Request Body (optional):
        warmers (list): List of specific warmer names to run

    Returns:
        Cache warming results.
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        data = request.get_json(silent=True) or {}
        warmers = data.get("warmers")

        results = warm_cache(warmers)
        results["request_id"] = request_id

        return jsonify(results), 200

    except Exception:
        logger.error("Error warming cache", exc_info=True)
        return (
            jsonify(
                {
                    "error": "CacheWarmError",
                    "message": "Failed to warm cache",
                    "request_id": request_id,
                }
            ),
            500,
        )


@performance_bp.route("/slow-queries", methods=["GET"])
@limiter.limit("30 per minute")
@require_api_key
def slow_query_log():
    """
    Get slow query log.

    Query Parameters:
        limit (int): Maximum number of queries to return (default: 20)

    Returns:
        List of slow queries with execution times.
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        limit = request.args.get("limit", default=20, type=int)
        limit = min(limit, 100)  # Cap at 100

        queries = get_slow_queries(limit)

        return (
            jsonify(
                {
                    "slow_queries": queries,
                    "count": len(queries),
                    "threshold_ms": float(os.getenv("SLOW_QUERY_THRESHOLD_MS", "100")),
                    "request_id": request_id,
                }
            ),
            200,
        )

    except Exception:
        logger.error("Error getting slow queries", exc_info=True)
        return (
            jsonify(
                {
                    "error": "SlowQueryError",
                    "message": "Failed to retrieve slow queries",
                    "request_id": request_id,
                }
            ),
            500,
        )


@performance_bp.route("/slow-queries", methods=["DELETE"])
@limiter.limit("5 per minute")
@require_api_key
def clear_slow_queries():
    """
    Clear the slow query log.

    Returns:
        Number of entries cleared.
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        count = clear_slow_query_log()

        return (
            jsonify(
                {
                    "message": "Slow query log cleared",
                    "entries_cleared": count,
                    "request_id": request_id,
                }
            ),
            200,
        )

    except Exception:
        logger.error("Error clearing slow queries", exc_info=True)
        return (
            jsonify(
                {
                    "error": "ClearSlowQueryError",
                    "message": "Failed to clear slow queries",
                    "request_id": request_id,
                }
            ),
            500,
        )


@performance_bp.route("/database", methods=["GET"])
@limiter.limit("30 per minute")
def database_performance():
    """
    Get database performance metrics.

    Returns:
        Database pool status and connection metrics.
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        pool_status = get_pool_status()
        query_stats = get_query_statistics()

        return (
            jsonify(
                {
                    "pool": pool_status,
                    "query_statistics": query_stats,
                    "request_id": request_id,
                }
            ),
            200,
        )

    except Exception:
        logger.error("Error getting database performance", exc_info=True)
        return (
            jsonify(
                {
                    "error": "DatabasePerfError",
                    "message": "Failed to retrieve database performance",
                    "request_id": request_id,
                }
            ),
            500,
        )


@performance_bp.route("/database/health", methods=["GET"])
@limiter.limit("30 per minute")
def database_health():
    """
    Get comprehensive database health check.

    Returns:
        Database health status with recommendations.
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        with get_db_session() as session:
            health = get_database_health(session)
            health["request_id"] = request_id

            return jsonify(health), 200

    except Exception:
        logger.error("Error checking database health", exc_info=True)
        return (
            jsonify(
                {
                    "error": "HealthCheckError",
                    "message": "Failed to check database health",
                    "request_id": request_id,
                }
            ),
            500,
        )


@performance_bp.route("/database/indexes", methods=["GET"])
@limiter.limit("10 per minute")
@require_api_key
def database_index_stats():
    """
    Get database index usage statistics (PostgreSQL only).

    Returns:
        Index usage statistics and unused indexes.
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        with get_db_session() as session:
            index_stats = get_index_usage_stats(session)
            unused_indexes = get_unused_indexes(session)

            return (
                jsonify(
                    {
                        "index_usage": index_stats,
                        "unused_indexes": unused_indexes,
                        "request_id": request_id,
                    }
                ),
                200,
            )

    except Exception:
        logger.error("Error getting index stats", exc_info=True)
        return (
            jsonify(
                {
                    "error": "IndexStatsError",
                    "message": "Failed to retrieve index statistics",
                    "request_id": request_id,
                }
            ),
            500,
        )


@performance_bp.route("/database/tables", methods=["GET"])
@limiter.limit("10 per minute")
@require_api_key
def database_table_stats():
    """
    Get database table statistics (PostgreSQL only).

    Returns:
        Table statistics including row counts and vacuum status.
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        with get_db_session() as session:
            table_stats = get_table_statistics(session)

            return (
                jsonify(
                    {
                        "tables": table_stats,
                        "request_id": request_id,
                    }
                ),
                200,
            )

    except Exception:
        logger.error("Error getting table stats", exc_info=True)
        return (
            jsonify(
                {
                    "error": "TableStatsError",
                    "message": "Failed to retrieve table statistics",
                    "request_id": request_id,
                }
            ),
            500,
        )


@performance_bp.route("/database/maintenance", methods=["GET"])
@limiter.limit("5 per minute")
@require_api_key
def database_maintenance():
    """
    Get database maintenance recommendations.

    Returns:
        List of recommended maintenance SQL commands.
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        with get_db_session() as session:
            recommendations = run_maintenance_recommendations(session)

            return (
                jsonify(
                    {
                        "recommendations": recommendations,
                        "count": len(recommendations),
                        "request_id": request_id,
                    }
                ),
                200,
            )

    except Exception:
        logger.error("Error getting maintenance recommendations", exc_info=True)
        return (
            jsonify(
                {
                    "error": "MaintenanceError",
                    "message": "Failed to get maintenance recommendations",
                    "request_id": request_id,
                }
            ),
            500,
        )


# ============================================================================
# Request Timing Middleware Hook
# ============================================================================


def setup_response_time_tracking(app):
    """
    Set up response time tracking middleware.

    Args:
        app: Flask application instance
    """

    @app.before_request
    def start_timer():
        g.request_start_time = time.time()

    @app.after_request
    def record_request_time(response):
        if hasattr(g, "request_start_time"):
            duration_ms = (time.time() - g.request_start_time) * 1000
            endpoint = request.endpoint or request.path
            record_response_time(endpoint, duration_ms)

            # Add timing header
            response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"

        return response

    logger.info("Response time tracking enabled")
