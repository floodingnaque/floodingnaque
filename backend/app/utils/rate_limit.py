"""
Rate Limit Utilities - DEPRECATED.

Import directly from ``app.api.middleware.rate_limit`` instead.
This shim is kept only for backward compatibility and will be
removed in a future release.
"""

import warnings

warnings.warn(
    "Importing from app.utils.rate_limit is deprecated. " "Use app.api.middleware.rate_limit instead.",
    DeprecationWarning,
    stacklevel=2,
)

from app.api.middleware.rate_limit import (
    BURST_ENABLED,
    BURST_MULTIPLIER,
    BURST_WINDOW_SECONDS,
    ENDPOINT_LIMITS,
    RATE_LIMIT_ENABLED,
    RATE_LIMIT_STORAGE,
    check_burst_allowance,
    get_burst_stats,
    get_current_rate_limit_info,
    get_endpoint_limit,
    get_limiter,
    init_rate_limiter,
    limiter,
    rate_limit_authenticated_only,
    rate_limit_by_ip_only,
    rate_limit_relaxed,
    rate_limit_standard,
    rate_limit_strict,
    rate_limit_with_burst,
)

__all__ = [
    "limiter",
    "get_limiter",
    "init_rate_limiter",
    "get_endpoint_limit",
    "get_current_rate_limit_info",
    "rate_limit_standard",
    "rate_limit_strict",
    "rate_limit_relaxed",
    "rate_limit_by_ip_only",
    "rate_limit_authenticated_only",
    "rate_limit_with_burst",
    "check_burst_allowance",
    "get_burst_stats",
    "ENDPOINT_LIMITS",
    "RATE_LIMIT_ENABLED",
    "RATE_LIMIT_STORAGE",
    "BURST_ENABLED",
    "BURST_MULTIPLIER",
    "BURST_WINDOW_SECONDS",
]
