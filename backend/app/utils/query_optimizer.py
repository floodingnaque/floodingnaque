"""
Database Query Optimization Utilities.

Provides eager loading, query result caching, index hints, and N+1 prevention
for improved database performance.
"""

import hashlib
import json
import logging
import os
import time
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Type

from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Query, Session, joinedload, selectinload

logger = logging.getLogger(__name__)

# ============================================================================
# Query Result Cache (In-Memory with optional Redis backend)
# ============================================================================

_query_cache: Dict[str, Dict[str, Any]] = {}
_cache_stats = {
    "hits": 0,
    "misses": 0,
    "evictions": 0,
}

# Maximum cache entries (in-memory)
MAX_CACHE_ENTRIES = 1000
DEFAULT_CACHE_TTL = 300  # 5 minutes


def _make_query_cache_key(query_str: str, params: Optional[Dict] = None) -> str:
    """Generate a unique cache key for a query."""
    key_data = f"{query_str}:{json.dumps(params or {}, sort_keys=True)}"
    return hashlib.md5(key_data.encode(), usedforsecurity=False).hexdigest()


def _evict_expired_cache():
    """Remove expired entries from cache."""
    global _query_cache
    now = time.time()
    expired_keys = [key for key, value in _query_cache.items() if value.get("expires_at", 0) < now]
    for key in expired_keys:
        del _query_cache[key]
        _cache_stats["evictions"] += 1


def query_cache_get(cache_key: str) -> Optional[Any]:
    """Get a value from query cache."""
    _evict_expired_cache()

    entry = _query_cache.get(cache_key)
    if entry and entry.get("expires_at", 0) > time.time():
        _cache_stats["hits"] += 1
        logger.debug(f"Query cache HIT: {cache_key[:16]}...")
        return entry.get("value")

    _cache_stats["misses"] += 1
    return None


def query_cache_set(cache_key: str, value: Any, ttl: int = DEFAULT_CACHE_TTL) -> None:
    """Set a value in query cache."""
    global _query_cache

    # Evict old entries if cache is full
    if len(_query_cache) >= MAX_CACHE_ENTRIES:
        _evict_expired_cache()
        # If still full, remove oldest entries
        if len(_query_cache) >= MAX_CACHE_ENTRIES:
            oldest_keys = sorted(_query_cache.keys(), key=lambda k: _query_cache[k].get("created_at", 0))[
                : MAX_CACHE_ENTRIES // 10
            ]
            for key in oldest_keys:
                del _query_cache[key]
                _cache_stats["evictions"] += 1

    _query_cache[cache_key] = {
        "value": value,
        "created_at": time.time(),
        "expires_at": time.time() + ttl,
    }
    logger.debug(f"Query cache SET: {cache_key[:16]}... (TTL: {ttl}s)")


def query_cache_invalidate(pattern: Optional[str] = None) -> int:
    """Invalidate cache entries matching a pattern or all entries."""
    global _query_cache

    if pattern is None:
        count = len(_query_cache)
        _query_cache.clear()
        logger.info(f"Query cache cleared: {count} entries removed")
        return count

    # Simple prefix matching
    keys_to_remove = [k for k in _query_cache.keys() if k.startswith(pattern)]
    for key in keys_to_remove:
        del _query_cache[key]

    logger.info(f"Query cache invalidated: {len(keys_to_remove)} entries removed (pattern: {pattern})")
    return len(keys_to_remove)


def get_query_cache_stats() -> Dict[str, Any]:
    """Get query cache statistics."""
    total_requests = _cache_stats["hits"] + _cache_stats["misses"]
    hit_rate = (_cache_stats["hits"] / total_requests * 100) if total_requests > 0 else 0

    return {
        "entries": len(_query_cache),
        "max_entries": MAX_CACHE_ENTRIES,
        "hits": _cache_stats["hits"],
        "misses": _cache_stats["misses"],
        "evictions": _cache_stats["evictions"],
        "hit_rate_percent": round(hit_rate, 2),
    }


# ============================================================================
# Cached Query Decorator
# ============================================================================


def cached_query(ttl: int = DEFAULT_CACHE_TTL, key_prefix: str = ""):
    """
    Decorator to cache query results.

    Usage:
        @cached_query(ttl=300, key_prefix="weather")
        def get_recent_weather(session, limit=100):
            return session.query(WeatherData).limit(limit).all()
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Build cache key from function name, args, and kwargs
            key_parts = [key_prefix or func.__name__]
            key_parts.extend([str(arg) for arg in args[1:]])  # Skip session arg
            key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
            cache_key = _make_query_cache_key(":".join(key_parts))

            # Try cache first
            cached_result = query_cache_get(cache_key)
            if cached_result is not None:
                return cached_result

            # Execute query
            result = func(*args, **kwargs)

            # Cache the result (convert ORM objects to dicts if needed)
            if result is not None:
                # If result is a list of ORM objects, convert to dicts
                if isinstance(result, list) and len(result) > 0:
                    if hasattr(result[0], "to_dict"):
                        cache_value = [r.to_dict() for r in result]
                    elif hasattr(result[0], "__dict__"):
                        cache_value = [{k: v for k, v in r.__dict__.items() if not k.startswith("_")} for r in result]
                    else:
                        cache_value = result
                else:
                    cache_value = result

                query_cache_set(cache_key, cache_value, ttl)

            return result

        return wrapper

    return decorator


# ============================================================================
# Eager Loading Helpers
# ============================================================================


class EagerLoader:
    """
    Helper class for configuring eager loading to prevent N+1 queries.

    Usage:
        loader = EagerLoader(session.query(Prediction))
        loader.join_load('weather_data')
        loader.select_load('alerts')
        results = loader.execute()
    """

    def __init__(self, query: Query):
        self.query = query
        self._join_loads: List[str] = []
        self._select_loads: List[str] = []

    def join_load(self, *relationships: str) -> "EagerLoader":
        """Add joinedload for relationships (one-to-one, many-to-one)."""
        self._join_loads.extend(relationships)
        return self

    def select_load(self, *relationships: str) -> "EagerLoader":
        """Add selectinload for relationships (one-to-many, many-to-many)."""
        self._select_loads.extend(relationships)
        return self

    def build(self) -> Query:
        """Build the query with all eager loading options."""
        for rel in self._join_loads:
            self.query = self.query.options(joinedload(rel))
        for rel in self._select_loads:
            self.query = self.query.options(selectinload(rel))
        return self.query

    def execute(self) -> List:
        """Execute the query with eager loading."""
        return self.build().all()

    def first(self):
        """Execute and return first result."""
        return self.build().first()


def with_eager_loading(
    query: Query, join_load: Optional[List[str]] = None, select_load: Optional[List[str]] = None
) -> Query:
    """
    Apply eager loading options to a query.

    Args:
        query: SQLAlchemy query object
        join_load: Relationships to load with JOIN (one-to-one, many-to-one)
        select_load: Relationships to load with SELECT IN (one-to-many)

    Returns:
        Query with eager loading options applied

    Example:
        query = with_eager_loading(
            session.query(Prediction),
            join_load=['weather_data'],
            select_load=['alerts']
        )
    """
    if join_load:
        for rel in join_load:
            query = query.options(joinedload(rel))
    if select_load:
        for rel in select_load:
            query = query.options(selectinload(rel))
    return query


# ============================================================================
# Slow Query Logging
# ============================================================================

# Global slow query threshold (milliseconds)
SLOW_QUERY_THRESHOLD_MS = float(os.getenv("SLOW_QUERY_THRESHOLD_MS", "100"))

# Slow query log
_slow_queries: List[Dict[str, Any]] = []
MAX_SLOW_QUERY_LOG = 100

import os


def setup_slow_query_logging(engine: Engine, threshold_ms: Optional[float] = None):
    """
    Set up slow query logging for a SQLAlchemy engine.

    Args:
        engine: SQLAlchemy engine instance
        threshold_ms: Slow query threshold in milliseconds (default from env)
    """
    threshold = threshold_ms or SLOW_QUERY_THRESHOLD_MS

    @event.listens_for(engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        conn.info.setdefault("query_start_time", []).append(time.time())

    @event.listens_for(engine, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        start_times = conn.info.get("query_start_time", [])
        if start_times:
            start_time = start_times.pop()
            duration_ms = (time.time() - start_time) * 1000

            if duration_ms >= threshold:
                log_slow_query(statement, parameters, duration_ms)

    logger.info(f"Slow query logging enabled (threshold: {threshold}ms)")


def log_slow_query(statement: str, parameters: Any, duration_ms: float):
    """Log a slow query."""
    global _slow_queries

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "statement": statement[:500],  # Truncate long queries
        "duration_ms": round(duration_ms, 2),
        "parameters": str(parameters)[:200] if parameters else None,
    }

    logger.warning(f"SLOW QUERY ({duration_ms:.2f}ms): {statement[:100]}...")

    # Keep recent slow queries
    _slow_queries.append(entry)
    if len(_slow_queries) > MAX_SLOW_QUERY_LOG:
        _slow_queries = _slow_queries[-MAX_SLOW_QUERY_LOG:]


def get_slow_queries(limit: int = 20) -> List[Dict[str, Any]]:
    """Get recent slow queries."""
    return _slow_queries[-limit:]


def clear_slow_query_log() -> int:
    """Clear the slow query log."""
    global _slow_queries
    count = len(_slow_queries)
    _slow_queries.clear()
    return count


# ============================================================================
# Query Performance Utilities
# ============================================================================


def explain_query(session: Session, query: Query, analyze: bool = True) -> Dict[str, Any]:
    """
    Run EXPLAIN ANALYZE on a query (PostgreSQL).

    Args:
        session: Database session
        query: SQLAlchemy query
        analyze: Whether to run EXPLAIN ANALYZE (includes execution stats)

    Returns:
        Dict with explain plan and parsed statistics
    """
    try:
        # Get the SQL statement
        statement = str(query.statement.compile(compile_kwargs={"literal_binds": True}))

        # Run EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) for detailed output
        # NOTE: EXPLAIN cannot use bind parameters for the target statement,
        # but `statement` is compiled by SQLAlchemy (not user input).
        explain_cmd = "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)" if analyze else "EXPLAIN (FORMAT JSON)"
        result = session.execute(text(f"{explain_cmd} {statement}"))

        # Parse JSON output
        row = result.fetchone()
        if row:
            plan_data = row[0]
            if isinstance(plan_data, list) and len(plan_data) > 0:
                plan = plan_data[0]

                # Extract key metrics
                return {
                    "plan": plan,
                    "execution_time_ms": plan.get("Execution Time"),
                    "planning_time_ms": plan.get("Planning Time"),
                    "total_cost": plan.get("Plan", {}).get("Total Cost"),
                    "rows_returned": (
                        plan.get("Plan", {}).get("Actual Rows") if analyze else plan.get("Plan", {}).get("Plan Rows")
                    ),
                    "shared_hit_blocks": plan.get("Plan", {}).get("Shared Hit Blocks", 0),
                    "shared_read_blocks": plan.get("Plan", {}).get("Shared Read Blocks", 0),
                    "node_type": plan.get("Plan", {}).get("Node Type"),
                    "index_used": _extract_index_from_plan(plan.get("Plan", {})),
                    "warnings": _analyze_plan_for_issues(plan.get("Plan", {})),
                }

        return {"error": "No plan returned"}
    except Exception:
        logger.error("Error running EXPLAIN", exc_info=True)
        # Fallback for SQLite or non-PostgreSQL databases
        return {"error": "Query analysis unavailable", "hint": "EXPLAIN ANALYZE is PostgreSQL-specific"}


def _extract_index_from_plan(plan: Dict) -> Optional[str]:
    """Extract index name from an EXPLAIN plan node."""
    index_name = plan.get("Index Name")
    if index_name:
        return index_name

    # Check child plans
    for child in plan.get("Plans", []):
        index = _extract_index_from_plan(child)
        if index:
            return index

    return None


def _analyze_plan_for_issues(plan: Dict) -> List[str]:
    """
    Analyze an EXPLAIN plan for potential performance issues.

    Returns:
        List of warning messages
    """
    warnings = []

    node_type = plan.get("Node Type", "")

    # Detect sequential scans on large tables
    if node_type == "Seq Scan":
        rows = plan.get("Actual Rows", plan.get("Plan Rows", 0))
        if rows > 1000:
            warnings.append(f"Sequential scan on {rows} rows - consider adding an index")

    # Detect hash joins that might indicate missing indexes
    if node_type == "Hash Join":
        rows = plan.get("Actual Rows", plan.get("Plan Rows", 0))
        if rows > 10000:
            warnings.append("Large hash join detected - verify join indexes")

    # Detect sorts that might be avoidable with proper indexing
    if node_type == "Sort":
        sort_key = plan.get("Sort Key", [])
        if sort_key:
            warnings.append(f"Sort operation on {sort_key} - consider index with sort order")

    # Check child plans recursively
    for child in plan.get("Plans", []):
        warnings.extend(_analyze_plan_for_issues(child))

    return warnings


def get_query_statistics() -> Dict[str, Any]:
    """Get comprehensive query statistics."""
    return {
        "cache": get_query_cache_stats(),
        "slow_queries": {
            "count": len(_slow_queries),
            "threshold_ms": SLOW_QUERY_THRESHOLD_MS,
            "recent": get_slow_queries(5),
        },
    }


def get_index_usage_stats(session: Session) -> List[Dict[str, Any]]:
    """
    Get index usage statistics from PostgreSQL (PostgreSQL only).

    Returns:
        List of index usage information including:
        - Table name
        - Index name
        - Index scans count
        - Tuples read/fetched
    """
    try:
        result = session.execute(
            text(
                """
            SELECT
                schemaname,
                relname as table_name,
                indexrelname as index_name,
                idx_scan as index_scans,
                idx_tup_read as tuples_read,
                idx_tup_fetch as tuples_fetched,
                pg_size_pretty(pg_relation_size(indexrelid)) as index_size
            FROM pg_stat_user_indexes
            ORDER BY idx_scan DESC
            LIMIT 50
        """
            )
        )

        return [
            {
                "schema": row[0],
                "table_name": row[1],
                "index_name": row[2],
                "index_scans": row[3],
                "tuples_read": row[4],
                "tuples_fetched": row[5],
                "index_size": row[6],
            }
            for row in result
        ]
    except Exception:
        logger.error("Error getting index stats", exc_info=True)
        return [{"error": "Failed to retrieve index statistics"}]


def get_unused_indexes(session: Session, min_table_scans: int = 100) -> List[Dict[str, Any]]:
    """
    Find unused or rarely used indexes (PostgreSQL only).

    Args:
        session: Database session
        min_table_scans: Minimum sequential scans to consider table active

    Returns:
        List of potentially unused indexes
    """
    try:
        result = session.execute(
            text(
                f"""
            SELECT
                s.schemaname,
                s.relname AS table_name,
                s.indexrelname AS index_name,
                s.idx_scan AS index_scans,
                t.seq_scan AS table_seq_scans,
                pg_size_pretty(pg_relation_size(s.indexrelid)) AS index_size,
                t.n_live_tup AS table_rows
            FROM pg_stat_user_indexes s
            JOIN pg_stat_user_tables t ON s.relid = t.relid
            WHERE s.idx_scan = 0
                AND t.seq_scan > {min_table_scans}
                AND s.indexrelname NOT LIKE '%_pkey'
            ORDER BY pg_relation_size(s.indexrelid) DESC
            LIMIT 20
        """  # nosec B608
            )
        )

        return [
            {
                "schema": row[0],
                "table_name": row[1],
                "index_name": row[2],
                "index_scans": row[3],
                "table_seq_scans": row[4],
                "index_size": row[5],
                "table_rows": row[6],
                "recommendation": "Consider removing this unused index",
            }
            for row in result
        ]
    except Exception:
        logger.error("Error finding unused indexes", exc_info=True)
        return [{"error": "Failed to find unused indexes"}]


def get_table_statistics(session: Session) -> List[Dict[str, Any]]:
    """
    Get table statistics for performance analysis (PostgreSQL only).

    Returns:
        List of table statistics including row counts, scans, and bloat
    """
    try:
        result = session.execute(
            text(
                """
            SELECT
                schemaname,
                relname AS table_name,
                n_live_tup AS live_rows,
                n_dead_tup AS dead_rows,
                seq_scan AS seq_scans,
                seq_tup_read AS seq_rows_read,
                idx_scan AS index_scans,
                idx_tup_fetch AS index_rows_fetched,
                n_tup_ins AS inserts,
                n_tup_upd AS updates,
                n_tup_del AS deletes,
                last_vacuum,
                last_autovacuum,
                last_analyze,
                last_autoanalyze,
                pg_size_pretty(pg_total_relation_size(relid)) AS total_size
            FROM pg_stat_user_tables
            ORDER BY n_live_tup DESC
            LIMIT 20
        """
            )
        )

        return [
            {
                "schema": row[0],
                "table_name": row[1],
                "live_rows": row[2],
                "dead_rows": row[3],
                "dead_row_ratio": round(row[3] / max(row[2], 1) * 100, 2) if row[2] else 0,
                "seq_scans": row[4],
                "seq_rows_read": row[5],
                "index_scans": row[6],
                "index_rows_fetched": row[7],
                "inserts": row[8],
                "updates": row[9],
                "deletes": row[10],
                "last_vacuum": row[11].isoformat() if row[11] else None,
                "last_autovacuum": row[12].isoformat() if row[12] else None,
                "last_analyze": row[13].isoformat() if row[13] else None,
                "last_autoanalyze": row[14].isoformat() if row[14] else None,
                "total_size": row[15],
                "needs_vacuum": row[3] > row[2] * 0.2 if row[2] else False,
            }
            for row in result
        ]
    except Exception:
        logger.error("Error getting table stats", exc_info=True)
        return [{"error": "Failed to retrieve table statistics"}]


# ============================================================================
# Batch Operations
# ============================================================================


def batch_insert(session: Session, model_class: Type, records: List[Dict], batch_size: int = 1000):
    """
    Efficiently insert records in batches.

    Args:
        session: Database session
        model_class: SQLAlchemy model class
        records: List of dictionaries to insert
        batch_size: Number of records per batch

    Returns:
        int: Total records inserted
    """
    total_inserted = 0

    for i in range(0, len(records), batch_size):
        batch = records[i : i + batch_size]
        objects = [model_class(**record) for record in batch]
        session.bulk_save_objects(objects)
        session.flush()
        total_inserted += len(batch)
        logger.debug(f"Batch inserted {len(batch)} records (total: {total_inserted})")

    return total_inserted


def batch_update(session: Session, model_class: Type, updates: List[Dict], batch_size: int = 1000):
    """
    Efficiently update records in batches.

    Args:
        session: Database session
        model_class: SQLAlchemy model class
        updates: List of dicts with 'id' and fields to update
        batch_size: Number of records per batch

    Returns:
        int: Total records updated
    """
    total_updated = 0

    for i in range(0, len(updates), batch_size):
        batch = updates[i : i + batch_size]
        session.bulk_update_mappings(model_class, batch)
        session.flush()
        total_updated += len(batch)

    return total_updated


# ============================================================================
# Database Health Check Utilities
# ============================================================================


def get_database_health(session: Session) -> Dict[str, Any]:
    """
    Comprehensive database health check.

    Returns:
        Dict with database health metrics and recommendations
    """
    from app.models.db import get_pool_status

    health = {
        "status": "healthy",
        "checks": {},
        "recommendations": [],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # 1. Connection pool health
    try:
        pool_status = get_pool_status()
        health["checks"]["connection_pool"] = pool_status

        if pool_status.get("health_status") == "critical":
            health["status"] = "critical"
            health["recommendations"].append(
                "Connection pool is nearly exhausted. Consider increasing DB_POOL_SIZE or DB_MAX_OVERFLOW."
            )
        elif pool_status.get("health_status") == "warning":
            if health["status"] == "healthy":
                health["status"] = "warning"
            health["recommendations"].append("Connection pool usage is high. Monitor for potential bottlenecks.")
    except Exception:
        logger.error("Error checking connection pool health", exc_info=True)
        health["checks"]["connection_pool"] = {"error": "Unable to check connection pool status"}
        health["status"] = "error"

    # 2. Query cache health
    try:
        cache_stats = get_query_cache_stats()
        health["checks"]["query_cache"] = cache_stats

        hit_rate = cache_stats.get("hit_rate_percent", 0)
        if hit_rate < 50 and cache_stats.get("hits", 0) + cache_stats.get("misses", 0) > 100:
            health["recommendations"].append(
                f"Query cache hit rate is {hit_rate}%. Consider increasing cache TTL or reviewing query patterns."
            )
    except Exception:
        logger.error("Error checking query cache health", exc_info=True)
        health["checks"]["query_cache"] = {"error": "Unable to check query cache status"}

    # 3. Slow queries
    try:
        slow_query_count = len(_slow_queries)
        health["checks"]["slow_queries"] = {
            "count": slow_query_count,
            "threshold_ms": SLOW_QUERY_THRESHOLD_MS,
        }

        if slow_query_count > 10:
            if health["status"] == "healthy":
                health["status"] = "warning"
            health["recommendations"].append(
                f"{slow_query_count} slow queries detected. Review /api/performance/slow-queries for details."
            )
    except Exception:
        logger.error("Error checking slow queries", exc_info=True)
        health["checks"]["slow_queries"] = {"error": "Unable to check slow query status"}

    # 4. Database connectivity (simple query)
    try:
        start = time.time()
        session.execute(text("SELECT 1"))
        latency_ms = (time.time() - start) * 1000

        health["checks"]["connectivity"] = {
            "status": "connected",
            "latency_ms": round(latency_ms, 2),
        }

        if latency_ms > 100:
            health["recommendations"].append(
                f"Database latency is {latency_ms:.0f}ms. Consider optimizing network or using connection pooling."
            )
    except Exception:
        logger.error("Database connectivity check failed", exc_info=True)
        health["checks"]["connectivity"] = {"status": "disconnected", "error": "Unable to connect to database"}
        health["status"] = "critical"

    # 5. Table statistics (PostgreSQL only)
    try:
        table_stats = get_table_statistics(session)
        if isinstance(table_stats, list) and len(table_stats) > 0 and "error" not in table_stats[0]:
            tables_needing_vacuum = [t for t in table_stats if t.get("needs_vacuum")]
            health["checks"]["tables"] = {
                "total_tables": len(table_stats),
                "needs_vacuum": len(tables_needing_vacuum),
            }

            if tables_needing_vacuum:
                health["recommendations"].append(
                    f"{len(tables_needing_vacuum)} tables have high dead row ratios. Consider running VACUUM ANALYZE."
                )
    except Exception:
        logger.error("Error checking table statistics", exc_info=True)
        health["checks"]["tables"] = {"error": "Unable to check table statistics"}

    return health


def run_maintenance_recommendations(session: Session) -> List[str]:
    """
    Get actionable database maintenance recommendations.

    Returns:
        List of SQL commands to run for maintenance
    """
    recommendations = []

    try:
        # Check for tables needing VACUUM
        table_stats = get_table_statistics(session)
        if isinstance(table_stats, list):
            for table in table_stats:
                if table.get("needs_vacuum") and "error" not in table:
                    recommendations.append(f"VACUUM ANALYZE {table.get('schema', 'public')}.{table['table_name']}")

        # Check for unused indexes
        unused = get_unused_indexes(session)
        if isinstance(unused, list):
            for idx in unused:
                if "error" not in idx:
                    recommendations.append(
                        f"-- Consider dropping: DROP INDEX {idx['index_name']} (saves {idx.get('index_size', 'unknown')}) "
                        f"-- Table: {idx['table_name']}, Last used: never"
                    )

        # Recommend REINDEX for fragmented indexes
        index_stats = get_index_usage_stats(session)
        if isinstance(index_stats, list):
            high_usage_indexes = [i for i in index_stats if i.get("index_scans", 0) > 10000 and "error" not in i]
            for idx in high_usage_indexes[:5]:
                recommendations.append(
                    f"-- Consider reindexing high-traffic index: REINDEX INDEX CONCURRENTLY {idx['index_name']}"
                )

        if not recommendations:
            recommendations.append("-- Database is in good health. No maintenance required.")

    except Exception:
        # Log full error details server-side only
        logger.error("Error analyzing database for maintenance", exc_info=True)
        # Return generic message to avoid exposing exception details
        recommendations.append("-- Error analyzing database: Unable to complete analysis")

    return recommendations


def analyze_query_performance(session: Session, query: Query) -> Dict[str, Any]:
    """
    Comprehensive query performance analysis.

    Args:
        session: Database session
        query: SQLAlchemy query to analyze

    Returns:
        Dict with performance metrics, explain plan, and recommendations
    """
    analysis = {
        "query": str(query.statement.compile(compile_kwargs={"literal_binds": True}))[:500],
        "explain": None,
        "recommendations": [],
    }

    # Get explain plan
    explain_result = explain_query(session, query, analyze=True)
    analysis["explain"] = explain_result

    # Add recommendations based on explain
    if "warnings" in explain_result:
        analysis["recommendations"].extend(explain_result["warnings"])

    # Check execution time
    exec_time = explain_result.get("execution_time_ms")
    if exec_time and exec_time > SLOW_QUERY_THRESHOLD_MS:
        analysis["recommendations"].append(
            f"Query execution time ({exec_time:.2f}ms) exceeds threshold ({SLOW_QUERY_THRESHOLD_MS}ms)"
        )

    # Check if index was used
    if not explain_result.get("index_used") and explain_result.get("rows_returned", 0) > 100:
        analysis["recommendations"].append(
            "No index used for this query. Consider adding an index for the filter/sort columns."
        )

    return analysis
