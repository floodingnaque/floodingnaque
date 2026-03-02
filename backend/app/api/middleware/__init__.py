"""Middleware package for Floodingnaque API.

Contains:
- auth: API key authentication middleware
- rate_limit: Rate limiting middleware
- security: Security headers middleware
- logging: Request/response logging middleware
- body_size: Per-endpoint request body size validation
"""

from app.api.middleware.auth import optional_api_key, require_api_key
from app.api.middleware.body_size import BodySizeLimits, limit_body_size, validate_json_body_size
from app.api.middleware.logging import add_request_id, request_logger, setup_request_logging
from app.api.middleware.rate_limit import (
    get_endpoint_limit,
    get_limiter,
    init_rate_limiter,
    limiter,
    rate_limit_auth,
    rate_limit_password_reset,
    rate_limit_relaxed,
    rate_limit_standard,
    rate_limit_strict,
    rate_limit_tiered,
)
from app.api.middleware.security import (
    add_security_headers,
    get_cors_origins,
    setup_cors,
    setup_security_headers,
    validate_cors_origin,
)

__all__ = [
    "require_api_key",
    "optional_api_key",
    "limiter",
    "get_limiter",
    "init_rate_limiter",
    "get_endpoint_limit",
    "rate_limit_auth",
    "rate_limit_password_reset",
    "rate_limit_standard",
    "rate_limit_strict",
    "rate_limit_relaxed",
    "rate_limit_tiered",
    "setup_security_headers",
    "add_security_headers",
    "setup_cors",
    "get_cors_origins",
    "validate_cors_origin",
    "setup_request_logging",
    "request_logger",
    "add_request_id",
    "limit_body_size",
    "validate_json_body_size",
    "BodySizeLimits",
]
