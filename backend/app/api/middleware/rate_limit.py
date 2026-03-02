"""Rate Limiting Middleware.

Provides rate limiting for API endpoints to prevent abuse and ensure fair usage.
Supports multiple backends (memory, Redis), API key-based limits, burst allowances,
and IP reputation-based adaptive limiting.
"""

import os
import threading
import time
from functools import wraps
from typing import Callable, Optional

from app.utils.logging import get_logger
from app.utils.rate_limit_tiers import (
    get_anonymous_limits,
    get_api_key_tier,
    get_rate_limit_for_key,
    get_reputation_manager,
    get_tier_limits,
)
from flask import g, has_request_context, jsonify, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

logger = get_logger(__name__)

# Check if rate limiting is enabled
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "True").lower() == "true"

# Get storage URI from environment
# Supports: memory://, redis://host:port, memcached://host:port
RATE_LIMIT_STORAGE = os.getenv("RATE_LIMIT_STORAGE_URL", "memory://")

# Default limits from environment
DEFAULT_LIMIT = os.getenv("RATE_LIMIT_DEFAULT", "100")
WINDOW_SECONDS = os.getenv("RATE_LIMIT_WINDOW_SECONDS", "3600")

# Burst allowance configuration
BURST_ENABLED = os.getenv("RATE_LIMIT_BURST_ENABLED", "True").lower() == "true"
BURST_MULTIPLIER = float(os.getenv("RATE_LIMIT_BURST_MULTIPLIER", "2.0"))
BURST_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_BURST_WINDOW", "10"))

# Internal service bypass configuration
INTERNAL_API_TOKEN = os.getenv("INTERNAL_API_TOKEN", "")
INTERNAL_BYPASS_ENABLED = os.getenv("RATE_LIMIT_INTERNAL_BYPASS_ENABLED", "True").lower() == "true"
INTERNAL_BYPASS_IPS = set(filter(None, os.getenv("RATE_LIMIT_INTERNAL_BYPASS_IPS", "127.0.0.1,::1").split(",")))

# Burst tracking (in-memory, for more sophisticated use Redis)
_burst_tracker: dict = {}
_burst_tracker_lock = threading.Lock()


def get_rate_limit_key():
    """
    Get rate limit key - uses API key hash if authenticated, otherwise IP address.

    This provides:
    - Per-API-key limits for authenticated users (more generous)
    - Per-IP limits for anonymous users (more restrictive)
    - Bypass for internal services (returns exempt key)
    """
    # Check for internal service bypass first
    if is_internal_service_request():
        return "internal:exempt"

    # Check if authenticated via API key
    api_key_hash = getattr(g, "api_key_hash", None)
    if api_key_hash:
        return f"api_key:{api_key_hash}"

    # Fall back to IP address for anonymous users
    return get_remote_address()


def is_internal_service_request() -> bool:
    """
    Check if the current request is from an internal service.

    Internal service requests are identified by:
    1. Valid X-Internal-Token header matching INTERNAL_API_TOKEN
    2. Request from whitelisted internal IPs
    3. Feature flag 'rate_limit_internal_bypass' enabled for segment

    Returns:
        bool: True if request is from internal service
    """
    if not INTERNAL_BYPASS_ENABLED:
        return False

    # Check internal token header
    internal_token = request.headers.get("X-Internal-Token")
    if internal_token and INTERNAL_API_TOKEN and internal_token == INTERNAL_API_TOKEN:
        logger.debug("Internal service detected via token")
        return True

    # Check whitelisted IPs
    client_ip = get_remote_address()
    if client_ip in INTERNAL_BYPASS_IPS:
        logger.debug(f"Internal service detected via whitelisted IP: {client_ip}")
        return True

    # Check feature flag for segment-based bypass
    try:
        from app.services.feature_flags import is_internal_service

        segment = getattr(g, "user_segment", None)
        if is_internal_service(segment):
            logger.debug("Internal service detected via feature flag")
            return True
    except ImportError:
        pass

    return False


def get_rate_limit_key_ip_only():
    """Get rate limit key based only on IP address."""
    return get_remote_address()


# Create limiter instance with flexible key function
limiter = Limiter(
    key_func=get_rate_limit_key,
    default_limits=[f"{DEFAULT_LIMIT} per {WINDOW_SECONDS} seconds"],
    storage_uri=RATE_LIMIT_STORAGE,
    enabled=RATE_LIMIT_ENABLED,
    strategy="fixed-window",  # Options: fixed-window, fixed-window-elastic-expiry, moving-window
    headers_enabled=True,  # Add X-RateLimit-* headers
    header_name_mapping={
        "LIMIT": "X-RateLimit-Limit",
        "REMAINING": "X-RateLimit-Remaining",
        "RESET": "X-RateLimit-Reset",
    },
)


def get_limiter():
    """Get the limiter instance."""
    return limiter


def init_rate_limiter(app):
    """
    Initialize rate limiter with Flask app.

    Args:
        app: Flask application instance
    """
    limiter.init_app(app)

    storage_type = "Redis" if "redis" in RATE_LIMIT_STORAGE else "Memory"

    if RATE_LIMIT_ENABLED:
        logger.info(
            f"Rate limiting enabled: {DEFAULT_LIMIT} requests per {WINDOW_SECONDS}s " f"(storage: {storage_type})"
        )
    else:
        logger.info("Rate limiting is disabled")

    return limiter


# Predefined rate limit decorators for common use cases
# These now support both IP and API key-based limiting


def rate_limit_standard():
    """Standard rate limit for general endpoints: 100 per hour, 20 per minute."""
    return limiter.limit("100 per hour;20 per minute")


def rate_limit_strict():
    """Strict rate limit for sensitive endpoints: 30 per hour, 5 per minute."""
    return limiter.limit("30 per hour;5 per minute")


def rate_limit_auth():
    """
    Very strict rate limit for authentication/login endpoints.

    Provides protection against brute force attacks:
    - 5 attempts per minute
    - 20 attempts per hour
    - 100 attempts per day

    Uses IP-only limiting to prevent credential stuffing attacks.
    """
    return limiter.limit("5 per minute;20 per hour;100 per day", key_func=get_rate_limit_key_ip_only)


def rate_limit_password_reset():
    """
    Very strict rate limit for password reset endpoints.

    Prevents abuse of password reset functionality:
    - 3 attempts per minute
    - 10 attempts per hour
    - 50 attempts per day
    """
    return limiter.limit("3 per minute;10 per hour;50 per day", key_func=get_rate_limit_key_ip_only)


def rate_limit_relaxed():
    """Relaxed rate limit for public endpoints: 200 per hour, 50 per minute."""
    return limiter.limit("200 per hour;50 per minute")


def rate_limit_by_ip_only(limit_string):
    """Rate limit based on IP only, ignoring API key."""
    return limiter.limit(limit_string, key_func=get_rate_limit_key_ip_only)


def rate_limit_authenticated_only(limit_string):
    """
    Higher rate limit for authenticated users only.

    Unauthenticated users get the default stricter limit.
    """

    def dynamic_limit():
        if getattr(g, "authenticated", False):
            return limit_string
        # More restrictive for anonymous
        return "30 per hour;5 per minute"

    return limiter.limit(dynamic_limit)


# Specific limits for different endpoint types
# Authenticated users get 2x the limit
ENDPOINT_LIMITS = {
    "predict": "60 per hour;10 per minute",  # ML predictions (resource intensive)
    "predict_auth": "120 per hour;20 per minute",  # Authenticated prediction limit
    "ingest": "30 per hour;5 per minute",  # Data ingestion (external APIs)
    "ingest_auth": "60 per hour;10 per minute",  # Authenticated ingest limit
    "data": "120 per hour;30 per minute",  # Data retrieval
    "data_auth": "240 per hour;60 per minute",  # Authenticated data limit
    "status": "300 per hour;60 per minute",  # Health checks (relaxed)
    "docs": "200 per hour;40 per minute",  # Documentation
    # Auth-specific limits (very strict for security)
    "auth_login": "5 per minute;20 per hour;100 per day",
    "auth_register": "3 per minute;10 per hour;30 per day",
    "auth_reset": "3 per minute;10 per hour;50 per day",
    "auth_token": "10 per minute;30 per hour",
}


def get_endpoint_limit(endpoint_name, *, as_callable: bool = True):
    """
    Get the rate limit for an endpoint.

    Returns a callable (default) so Flask-Limiter evaluates within a request
    context. When a plain string is needed (e.g., for introspection), set
    as_callable=False.
    """

    def _resolve_limit():
        # If no request context (module import), fall back to default limit
        if not has_request_context():
            return ENDPOINT_LIMITS.get(f"{endpoint_name}_auth", f"{DEFAULT_LIMIT} per {WINDOW_SECONDS} seconds")

        api_key_hash = getattr(g, "api_key_hash", None)

        if api_key_hash:
            try:
                return get_rate_limit_for_key(api_key_hash, "per_minute")
            except Exception:
                return ENDPOINT_LIMITS.get(f"{endpoint_name}_auth", f"{DEFAULT_LIMIT} per {WINDOW_SECONDS} seconds")

        return get_anonymous_limits()

    return _resolve_limit if as_callable else _resolve_limit()


def get_current_rate_limit_info():
    """
    Get current rate limit information for the request.

    Returns:
        dict: Rate limit information
    """
    try:
        from flask import g

        api_key_hash = getattr(g, "api_key_hash", None)

        info = {
            "key_type": "api_key" if api_key_hash else "ip",
            "authenticated": getattr(g, "authenticated", False),
            "storage": "redis" if "redis" in RATE_LIMIT_STORAGE else "memory",
            "enabled": RATE_LIMIT_ENABLED,
            "burst_enabled": BURST_ENABLED,
        }

        # Add tier information if authenticated
        if api_key_hash:
            tier_name = get_api_key_tier(api_key_hash)
            tier = get_tier_limits(tier_name)
            info["tier"] = tier_name
            info["limits"] = {
                "per_minute": tier.requests_per_minute,
                "per_hour": tier.requests_per_hour,
                "per_day": tier.requests_per_day,
                "burst_capacity": tier.burst_capacity,
            }
        else:
            info["tier"] = "anonymous"
            info["limits"] = {
                "per_minute": 2,
                "per_hour": 20,
                "per_day": 100,
                "burst_capacity": 5,
            }

        return info
    except RuntimeError:
        # Outside of request context
        return {
            "key_type": "unknown",
            "authenticated": False,
            "storage": "redis" if "redis" in RATE_LIMIT_STORAGE else "memory",
            "enabled": RATE_LIMIT_ENABLED,
            "burst_enabled": BURST_ENABLED,
        }


# ============================================================================
# Burst Allowance Implementation
# ============================================================================


def check_burst_allowance(key: str) -> bool:
    """
    Check if a request can use burst allowance.

    Burst allowance allows temporary spikes in traffic above the normal rate limit.

    Args:
        key: Rate limit key (API key hash or IP)

    Returns:
        bool: True if burst is allowed
    """
    if not BURST_ENABLED:
        return False

    now = time.time()

    # Get burst capacity based on tier (read-only, outside lock)
    api_key_hash = getattr(g, "api_key_hash", None) if has_request_context() else None
    if api_key_hash:
        tier_name = get_api_key_tier(api_key_hash)
        tier = get_tier_limits(tier_name)
        burst_capacity = tier.burst_capacity
    else:
        burst_capacity = 5  # Anonymous burst capacity

    with _burst_tracker_lock:
        # Clean up old entries
        _cleanup_burst_tracker()

        # Get or create burst tracker for this key
        if key not in _burst_tracker:
            _burst_tracker[key] = {
                "requests": [],
                "burst_used": 0,
            }

        tracker = _burst_tracker[key]

        # Count requests in burst window
        window_start = now - BURST_WINDOW_SECONDS
        tracker["requests"] = [t for t in tracker["requests"] if t > window_start]

        # Check if within burst capacity
        if len(tracker["requests"]) < burst_capacity:
            tracker["requests"].append(now)
            return True

    return False


def _cleanup_burst_tracker():
    """Remove old entries from burst tracker.

    Must be called while holding ``_burst_tracker_lock``.
    """
    now = time.time()
    cutoff = now - BURST_WINDOW_SECONDS * 2

    keys_to_remove = []
    for key, tracker in _burst_tracker.items():
        if not tracker["requests"] or max(tracker["requests"]) < cutoff:
            keys_to_remove.append(key)

    for key in keys_to_remove:
        del _burst_tracker[key]


def get_burst_stats() -> dict:
    """Get burst allowance statistics."""
    with _burst_tracker_lock:
        active = len(_burst_tracker)
    return {
        "enabled": BURST_ENABLED,
        "multiplier": BURST_MULTIPLIER,
        "window_seconds": BURST_WINDOW_SECONDS,
        "active_trackers": active,
    }


# ============================================================================
# Enhanced Rate Limit Decorators with IP Reputation
# ============================================================================


def rate_limit_with_reputation(base_limit: str, endpoint_type: str = "default"):
    """
    Rate limit decorator with IP reputation integration.

    Adjusts rate limits based on IP reputation score.

    Args:
        base_limit: Base rate limit string
        endpoint_type: Type of endpoint for logging

    Returns:
        Rate limit decorator
    """

    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check IP reputation first
            ip_address = get_remote_address()
            manager = get_reputation_manager()

            is_blocked, remaining = manager.is_blocked(ip_address)
            if is_blocked:
                logger.warning(f"Blocked IP {ip_address} attempted to access {endpoint_type}")
                return create_rate_limit_response(
                    message="Your IP has been temporarily blocked due to suspicious activity",
                    retry_after=remaining,
                    blocked=True,
                )

            return f(*args, **kwargs)

        # Apply the actual rate limit
        return limiter.limit(base_limit)(decorated_function)

    return decorator


def rate_limit_endpoint(endpoint_type: str, auth_multiplier: float = 2.0):
    """
    Endpoint-specific rate limiting with authentication awareness.

    Authenticated users get auth_multiplier times the limit.

    Args:
        endpoint_type: Type of endpoint (predict, ingest, data, etc.)
        auth_multiplier: Multiplier for authenticated users

    Returns:
        Rate limit decorator
    """

    def dynamic_limit():
        base_limit = ENDPOINT_LIMITS.get(endpoint_type, f"{DEFAULT_LIMIT} per {WINDOW_SECONDS} seconds")

        if not has_request_context():
            return base_limit

        api_key_hash = getattr(g, "api_key_hash", None)
        ip_address = get_remote_address()

        # Check IP reputation
        manager = get_reputation_manager()
        reputation_multiplier = manager.get_rate_limit_multiplier(ip_address)

        if api_key_hash:
            # Authenticated - use tier-based limits
            auth_limit = ENDPOINT_LIMITS.get(f"{endpoint_type}_auth", base_limit)
            return _apply_multiplier(auth_limit, reputation_multiplier)
        else:
            # Anonymous - apply stricter limits
            return _apply_multiplier(base_limit, reputation_multiplier * 0.5)

    return limiter.limit(dynamic_limit)


def _apply_multiplier(limit_str: str, multiplier: float) -> str:
    """Apply a multiplier to a rate limit string."""
    if multiplier == 1.0:
        return limit_str

    # Handle compound limits (e.g., "60 per hour;10 per minute")
    parts = limit_str.split(";")
    adjusted_parts = []

    for part in parts:
        part = part.strip()
        # Parse "N per period" format
        tokens = part.split()
        if len(tokens) >= 3:
            try:
                count = int(tokens[0])
                adjusted_count = max(1, int(count * multiplier))
                adjusted_parts.append(f"{adjusted_count} {' '.join(tokens[1:])}")
            except ValueError:
                adjusted_parts.append(part)
        else:
            adjusted_parts.append(part)

    return ";".join(adjusted_parts)


def create_rate_limit_response(
    message: str = "Rate limit exceeded",
    retry_after: Optional[int] = None,
    limit: Optional[int] = None,
    remaining: int = 0,
    blocked: bool = False,
) -> tuple:
    """
    Create a standardized rate limit error response.

    Returns RFC 7807 Problem Details compliant response.
    """
    request_id = getattr(g, "request_id", "unknown") if has_request_context() else "unknown"

    response = {
        "success": False,
        "error": {
            "type": "/errors/rate-limit" if not blocked else "/errors/blocked",
            "title": "Rate Limit Exceeded" if not blocked else "IP Blocked",
            "status": 429,
            "detail": message,
            "code": "RATE_LIMIT_EXCEEDED" if not blocked else "IP_BLOCKED",
            "request_id": request_id,
        },
    }

    # Add rate limit details
    if retry_after is not None:
        response["error"]["retry_after_seconds"] = retry_after
    if limit is not None:
        response["error"]["limit"] = limit
    response["error"]["remaining"] = remaining

    # Add helpful message
    if not blocked:
        response["error"]["help"] = (
            "You have exceeded your rate limit. Please wait before making more requests. "
            "Consider using an API key for higher limits."
        )
    else:
        response["error"]["help"] = (
            "Your IP has been blocked due to suspicious activity. "
            "If you believe this is an error, please contact support."
        )

    headers = {}
    if retry_after is not None:
        headers["Retry-After"] = str(retry_after)

    return jsonify(response), 429, headers


def setup_rate_limit_error_handler(app):
    """
    Setup custom error handler for rate limit exceeded errors.

    Args:
        app: Flask application instance
    """

    @app.errorhandler(429)
    def rate_limit_exceeded_handler(e):
        # Record rate limit hit in reputation system
        ip_address = get_remote_address()
        manager = get_reputation_manager()
        manager.record_rate_limit_hit(ip_address)

        # Get retry-after if available
        retry_after = getattr(e, "description", {}).get("retry_after")
        if retry_after is None:
            retry_after = 60  # Default 1 minute

        return create_rate_limit_response(
            message=str(e.description) if isinstance(e.description, str) else "Rate limit exceeded",
            retry_after=retry_after,
        )

    logger.info("Rate limit error handler configured")


# ============================================================================
# Dynamic Rate Limit with Burst Support
# ============================================================================


def rate_limit_with_burst(base_limit: str):
    """
    Rate limit decorator that supports burst allowance.

    Args:
        base_limit: Base rate limit string (e.g., "100 per hour")

    Returns:
        Rate limit decorator

    Usage:
        @rate_limit_with_burst("60 per hour")
        def my_endpoint():
            ...
    """

    def dynamic_limit():
        key = get_rate_limit_key()

        # Check if burst is available
        if check_burst_allowance(key):
            # Parse and multiply the limit
            parts = base_limit.split()
            if len(parts) >= 3:
                base_count = int(parts[0])
                burst_count = int(base_count * BURST_MULTIPLIER)
                return f"{burst_count} {' '.join(parts[1:])}"

        return base_limit

    return limiter.limit(dynamic_limit)


def rate_limit_tiered(endpoint_type: str = "default"):
    """
    Tiered rate limit decorator based on user's subscription tier.

    Applies different rate limits based on API key tier:
    - free: 5/min, 100/hour, 1000/day
    - basic: 20/min, 500/hour, 10000/day
    - pro: 100/min, 2000/hour, 50000/day
    - enterprise: 500/min, 10000/hour, 250000/day
    - unlimited: No practical limit

    Anonymous users get stricter limits (2/min, 20/hour).

    Args:
        endpoint_type: Type of endpoint for logging

    Returns:
        Rate limit decorator

    Usage:
        @rate_limit_tiered('predict')
        def predict_endpoint():
            ...
    """

    def dynamic_limit():
        if not has_request_context():
            return "100 per hour;20 per minute"  # Default fallback

        api_key_hash = getattr(g, "api_key_hash", None)
        ip_address = get_remote_address()

        # Check IP reputation first
        manager = get_reputation_manager()
        is_blocked, remaining = manager.is_blocked(ip_address)
        if is_blocked:
            # Return extremely strict limit for blocked IPs
            return "1 per day"

        # Get reputation multiplier
        reputation_multiplier = manager.get_rate_limit_multiplier(ip_address)

        if api_key_hash:
            # Authenticated - use tier-based limits
            tier_name = get_api_key_tier(api_key_hash)
            tier = get_tier_limits(tier_name)
            base_limit = f"{tier.requests_per_hour} per hour;{tier.requests_per_minute} per minute"
            return _apply_multiplier(base_limit, reputation_multiplier)
        else:
            # Anonymous - stricter limits
            anonymous_limit = get_anonymous_limits(ip_address)
            return _apply_multiplier(anonymous_limit, reputation_multiplier * 0.8)

    return limiter.limit(dynamic_limit)
