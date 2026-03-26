"""
Redis Caching Module for Floodingnaque API.

Provides caching utilities for frequently accessed data to improve performance.
Supports both Redis (production) and simple in-memory caching (development).
"""

import hashlib
import json
import logging
import os
from datetime import timedelta
from functools import wraps
from typing import Any, Callable, Optional, Union

from app.utils.secrets import get_secret

logger = logging.getLogger(__name__)

# Redis client singleton
_redis_client = None
_cache_enabled = None


def init_redis():
    """
    Eagerly initialize Redis connection at app startup.

    Call from create_app() to avoid lazy initialization race conditions
    and first-request latency. Falls back gracefully if Redis is not
    configured or unavailable.
    """
    client = get_redis_client()
    if client:
        logger.info("Redis connection pre-warmed at startup")
    else:
        logger.info("Redis not available - caching disabled")
    return client


def get_redis_client():
    """
    Get or create a Redis client connection.

    Returns:
        Redis client or None if Redis is not configured/available
    """
    global _redis_client, _cache_enabled

    if _cache_enabled is False:
        return None

    if _redis_client is not None:
        return _redis_client

    redis_url = get_secret("REDIS_URL") or get_secret("RATE_LIMIT_STORAGE_URL") or ""

    if not redis_url or "redis" not in redis_url.lower():
        _cache_enabled = False
        logger.info("Redis caching not configured (REDIS_URL not set)")
        return None

    try:
        from urllib.parse import urlparse

        import redis

        parsed = urlparse(redis_url)
        _redis_client = redis.Redis(
            host=parsed.hostname or "localhost",
            port=parsed.port or 6379,
            password=parsed.password,
            db=int(parsed.path[1:]) if parsed.path and len(parsed.path) > 1 else 0,
            socket_timeout=5,
            socket_connect_timeout=5,
            decode_responses=True,  # Return strings instead of bytes
        )

        # Test connection
        _redis_client.ping()
        _cache_enabled = True
        logger.info(f"Redis caching enabled: {parsed.hostname}:{parsed.port}")
        return _redis_client

    except ImportError:
        _cache_enabled = False
        logger.warning("redis package not installed - caching disabled")
        return None
    except Exception as e:
        _cache_enabled = False
        logger.warning(f"Redis connection failed - caching disabled: {e}")
        return None


def is_cache_enabled() -> bool:
    """Check if caching is enabled."""
    get_redis_client()  # Initialize
    return _cache_enabled is True


def _make_cache_key(prefix: str, *args, **kwargs) -> str:
    """
    Generate a cache key from prefix and arguments.

    Args:
        prefix: Cache key prefix (e.g., 'weather', 'prediction')
        *args: Positional arguments to include in key
        **kwargs: Keyword arguments to include in key

    Returns:
        str: Unique cache key
    """
    key_parts = [prefix]

    if args:
        key_parts.extend([str(arg) for arg in args])

    if kwargs:
        sorted_kwargs = sorted(kwargs.items())
        key_parts.extend([f"{k}={v}" for k, v in sorted_kwargs])

    key_string = ":".join(key_parts)

    # Hash if key is too long
    if len(key_string) > 200:
        key_hash = hashlib.md5(key_string.encode(), usedforsecurity=False).hexdigest()
        return f"{prefix}:{key_hash}"

    return key_string


def cache_get(key: str) -> Optional[Any]:
    """
    Get a value from cache.

    Args:
        key: Cache key

    Returns:
        Cached value or None if not found/expired
    """
    client = get_redis_client()
    if not client:
        return None

    try:
        value = client.get(f"floodingnaque:{key}")
        if value:
            return json.loads(value)
        return None
    except Exception as e:
        logger.debug(f"Cache get error: {e}")
        return None


def cache_set(key: str, value: Any, ttl: Union[int, timedelta] = 300) -> bool:
    """
    Set a value in cache.

    Args:
        key: Cache key
        value: Value to cache (must be JSON serializable)
        ttl: Time to live in seconds or timedelta

    Returns:
        bool: True if successful
    """
    client = get_redis_client()
    if not client:
        return False

    try:
        if isinstance(ttl, timedelta):
            ttl = int(ttl.total_seconds())

        serialized = json.dumps(value)
        client.setex(f"floodingnaque:{key}", ttl, serialized)
        return True
    except Exception as e:
        logger.debug(f"Cache set error: {e}")
        return False


def cache_delete(key: str) -> bool:
    """
    Delete a value from cache.

    Args:
        key: Cache key

    Returns:
        bool: True if successful
    """
    client = get_redis_client()
    if not client:
        return False

    try:
        client.delete(f"floodingnaque:{key}")
        return True
    except Exception as e:
        logger.debug(f"Cache delete error: {e}")
        return False


def cache_clear_pattern(pattern: str) -> int:
    """
    Clear all cache keys matching a pattern.

    Args:
        pattern: Key pattern (e.g., 'weather:*')

    Returns:
        int: Number of keys deleted
    """
    client = get_redis_client()
    if not client:
        return 0

    try:
        keys = list(client.scan_iter(f"floodingnaque:{pattern}"))
        if keys:
            return client.delete(*keys)
        return 0
    except Exception as e:
        logger.debug(f"Cache clear pattern error: {e}")
        return 0


def cached(prefix: str, ttl: Union[int, timedelta] = 300, key_builder: Optional[Callable] = None):
    """
    Decorator to cache function results.

    Args:
        prefix: Cache key prefix
        ttl: Time to live in seconds or timedelta
        key_builder: Optional custom key builder function

    Usage:
        @cached('weather', ttl=300)
        def get_weather(lat, lon):
            ...

        @cached('prediction', ttl=timedelta(minutes=5))
        def predict_flood(features):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                cache_key = _make_cache_key(prefix, *args, **kwargs)

            # Try to get from cache
            cached_value = cache_get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit: {cache_key}")
                # Reconstruct Flask response tuple if cached as such
                if isinstance(cached_value, dict) and cached_value.get("__flask_response__"):
                    from flask import jsonify

                    return jsonify(cached_value["data"]), cached_value["status"]
                return cached_value

            # Execute function
            result = func(*args, **kwargs)

            # Cache result - handle Flask response tuples (Response, status_code)
            if result is not None:
                to_cache = result
                if isinstance(result, tuple) and len(result) == 2:
                    resp_obj, status_code = result
                    if hasattr(resp_obj, "get_json"):
                        to_cache = {"__flask_response__": True, "data": resp_obj.get_json(), "status": status_code}
                cache_set(cache_key, to_cache, ttl)
                logger.debug(f"Cache set: {cache_key}")

            return result

        return wrapper

    return decorator


def get_cache_stats() -> dict:
    """
    Get cache statistics.

    Returns:
        dict: Cache statistics including connection status, memory usage, etc.
    """
    client = get_redis_client()
    if not client:
        return {"enabled": False, "connected": False, "reason": "Redis not configured"}

    try:
        info = client.info("memory")
        keys_count = len(list(client.scan_iter("floodingnaque:*", count=1000)))

        return {
            "enabled": True,
            "connected": True,
            "used_memory_human": info.get("used_memory_human", "unknown"),
            "used_memory_peak_human": info.get("used_memory_peak_human", "unknown"),
            "keys_count": keys_count,
        }
    except Exception:
        logger.error("Error getting cache stats", exc_info=True)
        return {"enabled": True, "connected": False, "error": "Failed to retrieve cache statistics"}


# ============================================================================
# Cache Warming
# ============================================================================

_warm_cache_functions: dict = {}
_cache_warm_stats = {
    "last_warm_time": None,
    "warmed_keys": 0,
    "warm_duration_ms": 0,
}


def register_cache_warmer(name: str, ttl: Union[int, timedelta] = 300):
    """
    Decorator to register a function for cache warming.

    Args:
        name: Unique name for this cache warmer
        ttl: Time to live for cached values

    Usage:
        @register_cache_warmer('recent_predictions', ttl=600)
        def warm_recent_predictions():
            # Return dict of {cache_key: value} pairs to cache
            return {'prediction:recent': get_recent_predictions()}
    """

    def decorator(func: Callable) -> Callable:
        _warm_cache_functions[name] = {
            "func": func,
            "ttl": ttl.total_seconds() if isinstance(ttl, timedelta) else ttl,
        }
        logger.debug(f"Registered cache warmer: {name}")
        return func

    return decorator


def warm_cache(warmers: Optional[list] = None) -> dict:
    """
    Execute cache warming functions.

    Args:
        warmers: List of warmer names to execute (None = all)

    Returns:
        dict: Warming results with statistics
    """
    import time

    start_time = time.time()

    results = {
        "success": [],
        "failed": [],
        "skipped": [],
    }

    warmers_to_run = warmers or list(_warm_cache_functions.keys())

    for name in warmers_to_run:
        if name not in _warm_cache_functions:
            results["skipped"].append({"name": name, "reason": "not_registered"})
            continue

        warmer = _warm_cache_functions[name]
        try:
            cache_data = warmer["func"]()

            if isinstance(cache_data, dict):
                for key, value in cache_data.items():
                    cache_set(key, value, warmer["ttl"])
                results["success"].append(
                    {
                        "name": name,
                        "keys_cached": len(cache_data),
                    }
                )
            else:
                results["failed"].append(
                    {
                        "name": name,
                        "reason": "warmer_must_return_dict",
                    }
                )
        except Exception as e:
            logger.error(f"Cache warming failed for {name}: {e}")
            results["failed"].append(
                {
                    "name": name,
                    "reason": "Cache warming operation failed",
                }
            )

    duration_ms = (time.time() - start_time) * 1000

    # Update stats
    _cache_warm_stats["last_warm_time"] = time.time()
    _cache_warm_stats["warmed_keys"] = sum(r.get("keys_cached", 0) for r in results["success"])
    _cache_warm_stats["warm_duration_ms"] = round(duration_ms, 2)

    results["duration_ms"] = round(duration_ms, 2)
    results["total_keys"] = _cache_warm_stats["warmed_keys"]

    logger.info(
        f"Cache warming complete: {len(results['success'])} succeeded, "
        f"{len(results['failed'])} failed, {results['total_keys']} keys cached "
        f"in {duration_ms:.2f}ms"
    )

    return results


def get_cache_warm_stats() -> dict:
    """Get cache warming statistics."""
    return {
        **_cache_warm_stats,
        "registered_warmers": list(_warm_cache_functions.keys()),
    }


def schedule_cache_warming(interval_seconds: int = 300):
    """
    Schedule periodic cache warming (for use with APScheduler).

    Args:
        interval_seconds: Interval between warming cycles

    Returns:
        Callable: Function to be scheduled
    """

    def warm_job():
        try:
            warm_cache()
        except Exception as e:
            logger.error(f"Scheduled cache warming failed: {e}")

    return warm_job


# ============================================================================
# Event-driven Cache Invalidation
# ============================================================================


def invalidate_weather_cache() -> int:
    """
    Invalidate all cached weather data.

    Call this when an alert is broadcast (e.g. typhoon warning) so that
    subsequent predictions use fresh data instead of waiting for TTL expiry.

    Returns:
        int: Number of cache keys deleted
    """
    deleted = 0
    for pattern in ("weather:*", "prediction:*"):
        deleted += cache_clear_pattern(pattern)
    if deleted:
        logger.info(f"Event-driven cache invalidation: cleared {deleted} weather/prediction key(s)")
    return deleted


# ============================================================================
# Prediction Cache Helpers
# ============================================================================


def cache_prediction_result(weather_hash: str, prediction: dict, ttl: int = 300) -> bool:
    """
    Cache a prediction result.

    Args:
        weather_hash: Hash of weather input data
        prediction: Prediction result dict
        ttl: Time to live in seconds

    Returns:
        bool: True if cached successfully
    """
    key = f"prediction:{weather_hash}"
    return cache_set(key, prediction, ttl)


def get_cached_prediction(weather_hash: str) -> Optional[dict]:
    """
    Get a cached prediction result.

    Args:
        weather_hash: Hash of weather input data

    Returns:
        dict: Cached prediction or None
    """
    key = f"prediction:{weather_hash}"
    return cache_get(key)


def make_weather_hash(weather_data: dict) -> str:
    """
    Create a hash of weather input data for cache key.

    Args:
        weather_data: Weather input dictionary

    Returns:
        str: Hash string
    """
    import hashlib

    # Round values to reduce cache misses from floating point differences
    normalized = {
        "temperature": round(weather_data.get("temperature", 0), 1),
        "humidity": round(weather_data.get("humidity", 0), 1),
        "precipitation": round(weather_data.get("precipitation", 0), 1),
    }
    key_str = json.dumps(normalized, sort_keys=True)
    return hashlib.md5(key_str.encode(), usedforsecurity=False).hexdigest()[:16]
