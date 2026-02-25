"""
Security Headers Middleware.

Adds security headers to all responses to protect against common web vulnerabilities.
Implements OWASP-recommended security headers for industry-standard protection.
"""

import logging
import os

from app.core.config import is_debug_mode
from flask import Flask, request

logger = logging.getLogger(__name__)


def add_security_headers(response):
    """
    Add comprehensive security headers to response.

    Headers added (OWASP recommended):
    - X-Content-Type-Options: Prevents MIME type sniffing
    - X-Frame-Options: Prevents clickjacking
    - X-XSS-Protection: Enables browser XSS filter (legacy browsers)
    - Strict-Transport-Security: Enforces HTTPS
    - Content-Security-Policy: Restricts resource loading
    - Referrer-Policy: Controls referrer information
    - Permissions-Policy: Controls browser features
    - Cross-Origin-Embedder-Policy: Protects against Spectre-like attacks
    - Cross-Origin-Opener-Policy: Isolates browsing context
    - Cross-Origin-Resource-Policy: Controls cross-origin resource sharing

    Args:
        response: Flask response object

    Returns:
        Modified response with security headers
    """
    is_production = not is_debug_mode()  # Use centralized check

    # === Core Security Headers ===

    # Prevent MIME type sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"

    # Prevent clickjacking - deny all framing
    response.headers["X-Frame-Options"] = "DENY"

    # Enable browser XSS filter (for legacy browsers)
    response.headers["X-XSS-Protection"] = "1; mode=block"

    # Referrer Policy - send referrer only for same-origin requests
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # Permissions Policy - disable unnecessary browser features
    response.headers["Permissions-Policy"] = (
        "accelerometer=(), ambient-light-sensor=(), autoplay=(), battery=(), camera=(), "
        "cross-origin-isolated=(), display-capture=(), document-domain=(), encrypted-media=(), "
        "execution-while-not-rendered=(), execution-while-out-of-viewport=(), fullscreen=(), "
        "geolocation=(), gyroscope=(), keyboard-map=(), magnetometer=(), microphone=(), midi=(), "
        "navigation-override=(), payment=(), picture-in-picture=(), publickey-credentials-get=(), "
        "screen-wake-lock=(), sync-xhr=(), usb=(), web-share=(), xr-spatial-tracking=()"
    )

    # === Cross-Origin Isolation Headers ===

    # Cross-Origin-Embedder-Policy - require explicit opt-in for cross-origin resources
    # Use 'unsafe-none' for API that needs to be embedded, 'require-corp' for full isolation
    coep_policy = os.getenv("COEP_POLICY", "unsafe-none")
    response.headers["Cross-Origin-Embedder-Policy"] = coep_policy

    # Cross-Origin-Opener-Policy - isolate browsing context
    coop_policy = os.getenv("COOP_POLICY", "same-origin-allow-popups")
    response.headers["Cross-Origin-Opener-Policy"] = coop_policy

    # Cross-Origin-Resource-Policy - control cross-origin resource access
    corp_policy = os.getenv("CORP_POLICY", "cross-origin")  # API needs cross-origin access
    response.headers["Cross-Origin-Resource-Policy"] = corp_policy

    # === HTTPS Enforcement ===

    # Enforce HTTPS (1 year, include subdomains)
    # Only add in production to avoid issues during development
    if os.getenv("ENABLE_HTTPS", "False").lower() == "true" or is_production:
        hsts_max_age = int(os.getenv("HSTS_MAX_AGE", "31536000"))  # Default 1 year
        hsts_include_subdomains = os.getenv("HSTS_INCLUDE_SUBDOMAINS", "True").lower() == "true"
        hsts_preload = os.getenv("HSTS_PRELOAD", "False").lower() == "true"

        hsts_value = f"max-age={hsts_max_age}"
        if hsts_include_subdomains:
            hsts_value += "; includeSubDomains"
        if hsts_preload:
            hsts_value += "; preload"

        response.headers["Strict-Transport-Security"] = hsts_value

    # === Content Security Policy ===

    # CSP - adjust based on your needs
    # This is a restrictive policy; you may need to relax it for your frontend
    # CSP Reporting endpoint for monitoring policy violations
    csp_report_uri = os.getenv("CSP_REPORT_URI", "")
    csp_report_to = os.getenv("CSP_REPORT_TO", "")

    default_csp = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self'; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )

    # Add reporting directives if configured
    if csp_report_uri:
        default_csp += f"; report-uri {csp_report_uri}"
    if csp_report_to:
        default_csp += f"; report-to {csp_report_to}"
        # Also add Report-To header for newer browsers
        response.headers["Report-To"] = csp_report_to

    csp_policy = os.getenv("CSP_POLICY", default_csp)
    response.headers["Content-Security-Policy"] = csp_policy

    # === Cache Control ===

    # Cache control for API responses - prevent caching of sensitive data
    if "Cache-Control" not in response.headers:
        # Check if this is a static/cacheable endpoint
        cacheable_paths = ["/api/docs", "/health", "/status"]
        if any(request.path.startswith(path) for path in cacheable_paths):
            response.headers["Cache-Control"] = "public, max-age=60"
        else:
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"

    return response


def setup_security_headers(app: Flask):
    """
    Setup security headers middleware for Flask app.

    Args:
        app: Flask application instance
    """
    app.after_request(add_security_headers)
    logger.info("Security headers middleware enabled")


def get_cors_origins():
    """
    Get allowed CORS origins from environment.

    Returns:
        list: List of allowed origins
    """
    origins_str = os.getenv("CORS_ORIGINS", "")

    if not origins_str:
        # Default to allowing localhost for development
        if is_debug_mode():  # Use centralized check
            logger.warning(
                "CORS: using permissive debug origins — "
                "set CORS_ORIGINS explicitly for production"
            )
            return ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5000"]
        else:
            # In production, must explicitly set CORS_ORIGINS
            return []

    return [origin.strip() for origin in origins_str.split(",") if origin.strip()]


def setup_cors(app: Flask, cors_instance):
    """
    Configure CORS with security settings.

    Args:
        app: Flask application instance
        cors_instance: Flask-CORS instance
    """
    origins = get_cors_origins()

    if origins:
        cors_instance.init_app(
            app,
            origins=origins,
            methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
            allow_headers=[
                "Content-Type",
                "Authorization",
                "X-API-Key",
                "X-Request-ID",
                "X-CSRF-Token",
                "Accept",
                "Origin",
            ],
            expose_headers=[
                "X-Request-ID",
                "X-RateLimit-Limit",
                "X-RateLimit-Remaining",
                "X-RateLimit-Reset",
                "X-Trace-ID",
            ],
            supports_credentials=True,
            max_age=600,  # Cache preflight for 10 minutes
        )
        logger.info(f"CORS configured for origins: {origins}")
    else:
        logger.warning("No CORS origins configured - all origins will be blocked in production")


def validate_cors_origin(request_origin: str) -> bool:
    """
    Validate if a request origin is allowed.

    Args:
        request_origin: The Origin header value from the request

    Returns:
        bool: True if origin is allowed
    """
    if not request_origin:
        return False

    allowed_origins = get_cors_origins()
    if not allowed_origins:
        return False

    # Normalize origins for comparison
    request_origin = request_origin.rstrip("/")

    for allowed in allowed_origins:
        allowed = allowed.rstrip("/")
        if request_origin == allowed:
            return True
        # Support wildcard subdomains (e.g., *.floodingnaque.com)
        if allowed.startswith("*."):
            domain = allowed[2:]
            if request_origin.endswith(domain) or request_origin.endswith("." + domain):
                return True

    return False
