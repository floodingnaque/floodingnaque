"""
Shared error handling for Floodingnaque microservices.

All services use RFC 7807 Problem Details for HTTP APIs
to ensure consistent error response formatting.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from flask import g, jsonify

logger = logging.getLogger(__name__)


class ServiceError(Exception):
    """Base exception for microservice errors."""

    def __init__(self, message: str, status_code: int = 500, error_code: str = "INTERNAL_ERROR"):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(message)

    def to_response(self):
        """Convert to RFC 7807 JSON response."""
        request_id = getattr(g, "request_id", str(uuid.uuid4())[:8])
        response = {
            "success": False,
            "error": {
                "type": f"/errors/{self.error_code.lower().replace('_', '-')}",
                "title": self.error_code.replace("_", " ").title(),
                "status": self.status_code,
                "detail": self.message,
                "code": self.error_code,
                "request_id": request_id,
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            },
        }
        return jsonify(response), self.status_code


class NotFoundError(ServiceError):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, 404, "NOT_FOUND")


class ValidationError(ServiceError):
    def __init__(self, message: str = "Validation failed"):
        super().__init__(message, 422, "VALIDATION_ERROR")


class UnauthorizedError(ServiceError):
    def __init__(self, message: str = "Authentication required"):
        super().__init__(message, 401, "UNAUTHORIZED")


class ForbiddenError(ServiceError):
    def __init__(self, message: str = "Access denied"):
        super().__init__(message, 403, "FORBIDDEN")


class ConflictError(ServiceError):
    def __init__(self, message: str = "Resource conflict"):
        super().__init__(message, 409, "CONFLICT")


class ServiceUnavailableError(ServiceError):
    def __init__(self, message: str = "Upstream service unavailable"):
        super().__init__(message, 503, "SERVICE_UNAVAILABLE")


def register_error_handlers(app):
    """Register standardized error handlers on a Flask app."""

    @app.errorhandler(ServiceError)
    def handle_service_error(error):
        return error.to_response()

    @app.errorhandler(400)
    def bad_request(error):
        return ServiceError("Bad request", 400, "BAD_REQUEST").to_response()

    @app.errorhandler(401)
    def unauthorized(error):
        return UnauthorizedError().to_response()

    @app.errorhandler(403)
    def forbidden(error):
        return ForbiddenError().to_response()

    @app.errorhandler(404)
    def not_found(error):
        return NotFoundError().to_response()

    @app.errorhandler(429)
    def rate_limited(error):
        return ServiceError("Rate limit exceeded", 429, "RATE_LIMIT_EXCEEDED").to_response()

    @app.errorhandler(500)
    def internal_error(error):
        error_id = str(uuid.uuid4())[:8]
        logger.exception("Internal error [%s]: %s", error_id, error)
        return ServiceError("Internal server error", 500, "INTERNAL_ERROR").to_response()

    @app.errorhandler(Exception)
    def unexpected_error(error):
        error_id = str(uuid.uuid4())[:8]
        logger.exception("Unexpected error [%s]: %s", error_id, error)
        return ServiceError("An unexpected error occurred", 500, "INTERNAL_ERROR").to_response()
