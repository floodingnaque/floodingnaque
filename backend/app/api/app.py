"""
Floodingnaque API Application.

Flask application factory with modular route blueprints.
Industry-standard security hardening applied.
"""

import json
import logging
import os
import uuid
from datetime import datetime, timezone

from app.api.middleware import get_cors_origins, init_rate_limiter, setup_request_logging, setup_security_headers
from app.api.middleware.request_logger import setup_request_logging_middleware
from app.api.routes.alerts import alerts_bp
from app.api.routes.batch import batch_bp
from app.api.routes.celery import celery_bp
from app.api.routes.csp_report import csp_report_bp
from app.api.routes.dashboard import dashboard_bp
from app.api.routes.data import data_bp
from app.api.routes.export import export_bp
from app.api.routes.feature_flags import feature_flags_bp
from app.api.routes.graphql import graphql_bp, init_graphql_route
from app.api.routes.health import health_bp
from app.api.routes.health_k8s import health_k8s_bp
from app.api.routes.ingest import ingest_bp
from app.api.routes.models import models_bp
from app.api.routes.performance import performance_bp, setup_response_time_tracking
from app.api.routes.predict import predict_bp
from app.api.routes.predictions import predictions_bp
from app.api.routes.rate_limits import rate_limits_bp
from app.api.routes.security_txt import security_txt_bp
from app.api.routes.sse import sse_bp
from app.api.routes.tides import tides_bp
from app.api.routes.upload import upload_bp
from app.api.routes.users import users_bp
from app.api.routes.v1 import v1_bp
from app.api.routes.versioning import versioning_bp
from app.api.routes.webhooks import webhooks_bp
from app.api.swagger_config import init_swagger
from app.core.config import get_config, load_env
from app.core.exceptions import AppException
from app.models.db import init_db
from app.services import scheduler as scheduler_module
from app.utils.correlation import (
    CorrelationContext,
    clear_correlation_context,
    set_correlation_context,
)
from app.utils.logging import clear_request_context, set_request_context
from app.utils.metrics import init_prometheus_metrics
from app.utils.sentry import init_sentry
from app.utils.session_config import init_session
from app.utils.startup_health import validate_startup_health
from app.utils.tracing import TraceContext, clear_current_trace, get_current_trace, set_current_trace
from app.utils.utils import setup_logging
from flask import Flask, g, jsonify, request
from flask_compress import Compress
from flask_cors import CORS

# Initialize module-level logger
logger = logging.getLogger(__name__)

# Initialize extensions (without app binding)
compress = Compress()
cors = CORS()


def create_app(config_override: dict = None) -> Flask:
    """
    Flask application factory.

    Creates and configures the Flask application with all middleware,
    blueprints, and extensions.

    Args:
        config_override: Optional dictionary of configuration overrides

    Returns:
        Flask: Configured Flask application instance
    """
    # Load environment variables first
    load_env()

    # Setup logging
    setup_logging()

    # Create Flask app
    app = Flask(__name__)

    # Get configuration
    config = get_config()

    # Apply Flask configuration
    app.config.update(
        SECRET_KEY=config.SECRET_KEY,
        DEBUG=config.DEBUG,
        JSON_SORT_KEYS=False,
        MAX_CONTENT_LENGTH=int(os.getenv("MAX_CONTENT_LENGTH_MB", 1)) * 1024 * 1024,
        JSONIFY_PRETTYPRINT_REGULAR=config.DEBUG,
    )

    # Apply any configuration overrides (useful for testing)
    if config_override:
        app.config.update(config_override)

    # ==========================================
    # Request ID & Tracing Middleware
    # ==========================================

    @app.before_request
    def setup_request_tracing():
        """Setup request ID, correlation IDs, and distributed tracing."""
        import time

        g.request_start_time = time.perf_counter()

        # Extract or create correlation context from headers (W3C compatible)
        corr_ctx = CorrelationContext.from_headers(
            dict(request.headers),
            service_name=os.getenv("SERVICE_NAME", "floodingnaque-api"),
            service_version=os.getenv("APP_VERSION", "2.0.0"),
        )

        # Store in Flask g context
        g.request_id = corr_ctx.request_id
        g.trace_id = corr_ctx.trace_id
        g.correlation_id = corr_ctx.correlation_id
        g.span_id = corr_ctx.span_id

        # Set correlation context for logging
        set_correlation_context(corr_ctx)

        # Also set legacy trace context for backward compatibility
        trace_ctx = TraceContext.from_headers(dict(request.headers))
        set_current_trace(trace_ctx)

        # Set request context for legacy logging
        set_request_context(
            request_id=corr_ctx.request_id, trace_id=corr_ctx.trace_id, correlation_id=corr_ctx.correlation_id
        )

        # Start root span for this request
        span = trace_ctx.start_span(
            f"{request.method} {request.path}",
            tags={
                "http.method": request.method,
                "http.url": request.url,
                "http.route": request.path,
                "http.user_agent": request.headers.get("User-Agent", "unknown")[:200],
                "http.remote_addr": request.remote_addr,
                "correlation_id": corr_ctx.correlation_id,
            },
        )
        g.root_span = span

    @app.after_request
    def add_tracing_headers(response):
        """Add tracing and correlation headers to response."""
        # Add correlation headers for client-side tracing
        if hasattr(g, "correlation_id"):
            response.headers["X-Correlation-ID"] = g.correlation_id
        if hasattr(g, "request_id"):
            response.headers["X-Request-ID"] = g.request_id
        if hasattr(g, "trace_id"):
            response.headers["X-Trace-ID"] = g.trace_id
        if hasattr(g, "span_id"):
            response.headers["X-Span-ID"] = g.span_id

        # Finish root span and log trace if errors
        if hasattr(g, "root_span"):
            import time

            g.root_span.set_tag("http.status_code", response.status_code)
            if hasattr(g, "request_start_time"):
                duration_ms = (time.perf_counter() - g.request_start_time) * 1000
                g.root_span.set_tag("http.duration_ms", round(duration_ms, 2))

            trace_ctx = get_current_trace()
            if trace_ctx:
                trace_ctx.finish_span(g.root_span)

                # Log trace summary for errors or slow requests
                if response.status_code >= 400 or (hasattr(g, "request_start_time") and duration_ms > 1000):
                    logger.warning(
                        f"Request completed: {request.method} {request.path} - {response.status_code}",
                        extra={"trace_summary": trace_ctx.get_summary()},
                    )

        return response

    @app.teardown_request
    def cleanup_request_context(exception=None):
        """Cleanup request context after each request."""
        if exception and hasattr(g, "root_span"):
            g.root_span.set_error(exception)
        clear_current_trace()
        clear_correlation_context()
        clear_request_context()

    # ==========================================
    # Initialize Extensions
    # ==========================================

    # Compression (gzip responses)
    compress.init_app(app)
    logger.info("Response compression enabled")

    # CORS (Cross-Origin Resource Sharing)
    cors_origins = get_cors_origins()
    if cors_origins:
        cors.init_app(
            app,
            origins=cors_origins,
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
            max_age=600,
        )
        logger.info(f"CORS configured for: {cors_origins}")
    else:
        cors.init_app(app)
        if not config.DEBUG:
            logger.warning("No CORS origins configured - restricting cross-origin requests")

    # Rate limiting
    init_rate_limiter(app)
    logger.info(f"Rate limiting {'enabled' if config.RATE_LIMIT_ENABLED else 'disabled'}")

    # ==========================================
    # Initialize Server-Side Sessions (Redis in production)
    # ==========================================

    session_enabled = init_session(app)
    if session_enabled:
        logger.info("Server-side session storage initialized")
    else:
        logger.warning("Using default Flask sessions (not recommended for production)")

    # ==========================================
    # Initialize Security
    # ==========================================

    # Add security headers
    setup_security_headers(app)

    # Request logging middleware
    setup_request_logging(app)
    setup_request_logging_middleware(app)

    # Initialize Sentry for error tracking (if configured)
    sentry_dsn = os.getenv("SENTRY_DSN")
    if sentry_dsn:
        init_sentry(app)
        logger.info("Sentry error tracking initialized")

    # Initialize Prometheus metrics
    init_prometheus_metrics(app)

    # ==========================================
    # Initialize Database
    # ==========================================

    init_db()
    logger.info("Database initialized")

    # ==========================================
    # Register Blueprints
    # ==========================================

    # Core routes (no prefix - infrastructure endpoints)
    app.register_blueprint(health_bp)
    app.register_blueprint(health_k8s_bp)
    app.register_blueprint(security_txt_bp)
    app.register_blueprint(csp_report_bp)

    # API v1 routes (with /api/v1 prefix)
    API_V1_PREFIX = "/api/v1"

    # Register models_bp without prefix - provides /api/version, /api/models, /api/docs
    app.register_blueprint(models_bp)

    app.register_blueprint(ingest_bp, url_prefix=f"{API_V1_PREFIX}/ingest")
    app.register_blueprint(predict_bp, url_prefix=f"{API_V1_PREFIX}/predict")
    app.register_blueprint(data_bp, url_prefix=f"{API_V1_PREFIX}/data")
    app.register_blueprint(webhooks_bp, url_prefix=f"{API_V1_PREFIX}/webhooks")
    app.register_blueprint(batch_bp, url_prefix=f"{API_V1_PREFIX}/batch")
    app.register_blueprint(export_bp, url_prefix=f"{API_V1_PREFIX}/export")
    app.register_blueprint(celery_bp, url_prefix=f"{API_V1_PREFIX}/tasks")
    app.register_blueprint(rate_limits_bp, url_prefix=f"{API_V1_PREFIX}/rate-limits")
    app.register_blueprint(tides_bp, url_prefix=f"{API_V1_PREFIX}/tides")
    app.register_blueprint(graphql_bp, url_prefix=f"{API_V1_PREFIX}/graphql")
    app.register_blueprint(performance_bp, url_prefix=f"{API_V1_PREFIX}/performance")
    app.register_blueprint(users_bp, url_prefix=f"{API_V1_PREFIX}/auth")
    app.register_blueprint(alerts_bp, url_prefix=f"{API_V1_PREFIX}/alerts")
    app.register_blueprint(dashboard_bp, url_prefix=f"{API_V1_PREFIX}/dashboard")
    app.register_blueprint(predictions_bp, url_prefix=f"{API_V1_PREFIX}/predictions")
    app.register_blueprint(sse_bp, url_prefix=f"{API_V1_PREFIX}/sse")
    app.register_blueprint(upload_bp, url_prefix=f"{API_V1_PREFIX}/upload")
    app.register_blueprint(versioning_bp)  # No prefix - routes contain full paths like /api/models/versions
    app.register_blueprint(feature_flags_bp, url_prefix=f"{API_V1_PREFIX}/feature-flags")

    # Backward-compatible routes (shorter URL prefixes for legacy/test compatibility)
    # These register the same blueprints with different names and prefixes
    app.register_blueprint(tides_bp, url_prefix="/tides", name="tides_compat")
    app.register_blueprint(dashboard_bp, url_prefix="/api/dashboard", name="dashboard_compat")
    app.register_blueprint(export_bp, url_prefix="/api/export", name="export_compat")
    app.register_blueprint(sse_bp, url_prefix="/sse", name="sse_compat")

    # V1 API blueprint (backward compatible endpoints)
    app.register_blueprint(v1_bp, url_prefix="/api/v1", name="v1_api")

    logger.info("All blueprints registered")

    # ==========================================
    # Response Time Tracking
    # ==========================================

    if os.getenv("RESPONSE_TIME_TRACKING_ENABLED", "True").lower() == "true":
        setup_response_time_tracking(app)
        logger.info("Response time tracking enabled")

    # ==========================================
    # Initialize GraphQL Route
    # ==========================================

    init_graphql_route(app)

    # ==========================================
    # Swagger/OpenAPI Documentation
    # ==========================================

    if os.getenv("FEATURE_API_DOCS_ENABLED", "True").lower() == "true":
        init_swagger(app)
        logger.info("Swagger documentation enabled at /apidocs")

    # ==========================================
    # Error Handlers (RFC 7807 Problem Details)
    # ==========================================

    def _build_error_response(
        error_code: str, title: str, message: str, status_code: int, details: dict = None
    ) -> tuple:
        """Build standardized RFC 7807 error response."""
        request_id = getattr(g, "request_id", "unknown")
        trace_id = getattr(g, "trace_id", None)

        response = {
            "success": False,
            "error": {
                "type": f'/errors/{error_code.lower().replace("_", "-")}',
                "title": title,
                "status": status_code,
                "detail": message,
                "code": error_code,
                "request_id": request_id,
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            },
        }

        if trace_id:
            response["error"]["trace_id"] = trace_id

        if details and config.DEBUG:
            response["error"]["debug"] = details

        logger.error(
            f"API Error: {error_code} - {message}",
            extra={
                "error_code": error_code,
                "status_code": status_code,
                "request_id": request_id,
                "trace_id": trace_id,
            },
        )

        return jsonify(response), status_code

    @app.errorhandler(AppException)
    def handle_app_exception(error):
        """Handle custom application exceptions."""
        response = error.to_dict(include_debug=config.DEBUG)
        response["error"]["request_id"] = getattr(g, "request_id", "unknown")
        if hasattr(g, "trace_id"):
            response["error"]["trace_id"] = g.trace_id

        logger.error(
            f"AppException: {error.error_code} - {error.message}",
            extra={"error_code": error.error_code, "status_code": error.status_code},
        )

        resp = jsonify(response)
        if hasattr(error, "retry_after") and error.retry_after:
            resp.headers["Retry-After"] = str(error.retry_after)

        return resp, error.status_code

    @app.errorhandler(json.JSONDecodeError)
    def handle_json_decode_error(error):
        """Handle JSON decode errors (malformed JSON)."""
        return _build_error_response(
            "BAD_REQUEST",
            "Invalid JSON",
            f"Failed to parse JSON: {str(error)}",
            400,
        )

    @app.errorhandler(400)
    def bad_request(error):
        """Handle 400 Bad Request errors."""
        return _build_error_response(
            "BAD_REQUEST",
            "Bad Request",
            str(error.description) if hasattr(error, "description") else "Invalid request",
            400,
        )

    @app.errorhandler(401)
    def unauthorized(error):
        """Handle 401 Unauthorized errors."""
        return _build_error_response(
            "UNAUTHORIZED", "Authentication Required", "Authentication is required to access this resource", 401
        )

    @app.errorhandler(403)
    def forbidden(error):
        """Handle 403 Forbidden errors."""
        return _build_error_response(
            "FORBIDDEN", "Access Denied", "You do not have permission to access this resource", 403
        )

    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 Not Found errors."""
        return _build_error_response("NOT_FOUND", "Resource Not Found", "The requested resource was not found", 404)

    @app.errorhandler(405)
    def method_not_allowed(error):
        """Handle 405 Method Not Allowed errors."""
        return _build_error_response(
            "METHOD_NOT_ALLOWED", "Method Not Allowed", "The HTTP method is not allowed for this endpoint", 405
        )

    @app.errorhandler(422)
    def unprocessable_entity(error):
        """Handle 422 Unprocessable Entity errors."""
        return _build_error_response(
            "UNPROCESSABLE_ENTITY",
            "Validation Error",
            str(error.description) if hasattr(error, "description") else "Request validation failed",
            422,
        )

    @app.errorhandler(429)
    def rate_limit_exceeded(error):
        """Handle 429 Rate Limit Exceeded errors."""
        return _build_error_response(
            "RATE_LIMIT_EXCEEDED", "Too Many Requests", "Rate limit exceeded. Please slow down your requests.", 429
        )

    @app.errorhandler(500)
    def internal_server_error(error):
        """Handle 500 Internal Server Error."""
        error_id = str(uuid.uuid4())[:8]
        logger.exception(f"Internal server error [{error_id}]: {error}")

        message = "An unexpected error occurred"
        if config.DEBUG:
            message = str(error)

        return _build_error_response(
            "INTERNAL_ERROR",
            "Internal Server Error",
            message,
            500,
            details={"error_id": error_id} if not config.DEBUG else {"error_id": error_id, "exception": str(error)},
        )

    @app.errorhandler(502)
    def bad_gateway(error):
        """Handle 502 Bad Gateway errors."""
        return _build_error_response("BAD_GATEWAY", "Bad Gateway", "Error communicating with upstream service", 502)

    @app.errorhandler(503)
    def service_unavailable(error):
        """Handle 503 Service Unavailable errors."""
        return _build_error_response(
            "SERVICE_UNAVAILABLE", "Service Unavailable", "The service is temporarily unavailable", 503
        )

    @app.errorhandler(504)
    def gateway_timeout(error):
        """Handle 504 Gateway Timeout errors."""
        return _build_error_response("GATEWAY_TIMEOUT", "Gateway Timeout", "Upstream service timed out", 504)

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        """Catch-all handler for unexpected exceptions."""
        error_id = str(uuid.uuid4())[:8]
        logger.exception(f"Unexpected error [{error_id}]: {error}")

        return _build_error_response(
            "INTERNAL_ERROR",
            "Internal Server Error",
            "An unexpected error occurred" if not config.DEBUG else str(error),
            500,
            details={"error_id": error_id},
        )

    # ==========================================
    # Startup Tasks
    # ==========================================

    with app.app_context():
        # Validate configuration
        warnings = config.validate()
        for warning in warnings:
            logger.warning(f"Configuration warning: {warning}")

        # ==========================================
        # Environment Variable Validation
        # ==========================================
        # Validate all required environment variables on startup
        env = os.getenv("APP_ENV", "development")
        is_production = env in ("production", "prod", "staging", "stage")
        env_validation_enabled = os.getenv("ENV_VALIDATION_ENABLED", "True").lower() == "true"

        if env_validation_enabled:
            try:
                from app.utils.env_validation import validate_all_env_vars

                env_report = validate_all_env_vars(raise_on_critical=is_production, log_results=True)

                if not env_report.is_valid:
                    logger.error(f"Environment validation failed: {env_report.get_summary()}")
                elif env_report.has_warnings:
                    logger.warning(f"Environment validation completed with warnings: {env_report.get_summary()}")
                else:
                    logger.info("Environment validation passed")
            except Exception as e:
                if is_production:
                    logger.critical(f"Environment validation error: {e}")
                    raise
                else:
                    logger.warning(f"Environment validation error (non-critical in development): {e}")

        # ==========================================
        # Startup Health Validation
        # ==========================================
        # Perform comprehensive health checks during startup
        # In production, raise on critical failures to fail fast
        startup_check_enabled = os.getenv("STARTUP_HEALTH_CHECK", "True").lower() == "true"

        if startup_check_enabled:
            try:
                health_report = validate_startup_health(
                    check_env=True,
                    check_model=True,
                    check_database_conn=True,
                    check_redis_conn=True,
                    raise_on_failure=is_production,  # Fail fast in production
                    log_results=True,
                )

                if not health_report.is_healthy:
                    logger.error(f"Startup health validation failed: {health_report.summary}")
                elif health_report.has_warnings:
                    logger.warning(f"Startup completed with warnings: {health_report.summary}")
                else:
                    logger.info("Startup health validation passed")

            except RuntimeError as e:
                # Critical failure in production - re-raise to prevent startup
                logger.critical(f"CRITICAL: Application startup blocked - {e}")
                raise
            except Exception as e:
                # Non-critical health check failure - log and continue
                logger.warning(f"Startup health check encountered an error: {e}")

        # Log startup info
        logger.info(f"Floodingnaque API initialized - Environment: {env}")
        logger.info(f"Debug mode: {config.DEBUG}")

        # Start scheduler if enabled
        scheduler_enabled = os.getenv("SCHEDULER_ENABLED", "True").lower() == "true"
        if scheduler_enabled:
            try:
                scheduler_module.start()
                logger.info("Background scheduler started")
            except Exception as e:
                logger.error(f"Failed to start scheduler: {e}")

    return app


# Create a default app instance for Gunicorn and testing
app = None


def get_app():
    """Get or create the Flask app instance."""
    global app
    if app is None:
        app = create_app()
    return app
