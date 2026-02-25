"""
API Error Classes.

Custom exception classes for API error handling following RFC 7807 Problem Details.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class AppException(Exception):
    """Base application exception class following RFC 7807 Problem Details."""

    def __init__(
        self,
        message: str,
        status_code: int = 400,
        error_code: str = None,
        details: Optional[Dict[str, Any]] = None,
        errors: Optional[List[Dict[str, Any]]] = None,
        instance: Optional[str] = None,
        help_url: Optional[str] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        self.errors = errors or []
        self.instance = instance
        self.help_url = help_url
        self.timestamp = datetime.now(timezone.utc).isoformat() + "Z"
        super().__init__(self.message)

    def to_dict(self, include_debug: bool = False) -> dict:
        """
        Convert exception to RFC 7807 Problem Details format.

        Args:
            include_debug: Include debug details (traceback, etc.)
        """
        response = {
            "success": False,
            "error": {
                "type": f'/errors/{self.error_code.lower().replace("error", "")}',
                "title": self._get_title(),
                "status": self.status_code,
                "detail": self.message,
                "code": self.error_code,
                "timestamp": self.timestamp,
            },
        }

        if self.instance:
            response["error"]["instance"] = self.instance

        if self.help_url:
            response["error"]["help_url"] = self.help_url

        if self.errors:
            response["error"]["errors"] = self.errors

        if self.details and include_debug:
            response["error"]["debug"] = self.details

        return response

    def _get_title(self) -> str:
        """Get human-readable title for error type."""
        titles = {
            "ValidationError": "Validation Failed",
            "NotFoundError": "Resource Not Found",
            "UnauthorizedError": "Authentication Required",
            "AuthenticationError": "Authentication Required",
            "ForbiddenError": "Access Denied",
            "AuthorizationError": "Access Denied",
            "ConflictError": "Resource Conflict",
            "RateLimitExceededError": "Rate Limit Exceeded",
            "RateLimitError": "Rate Limit Exceeded",
            "InternalServerError": "Internal Server Error",
            "ServiceUnavailableError": "Service Unavailable",
            "BadRequestError": "Bad Request",
            "ModelError": "Model Processing Error",
            "ExternalServiceError": "External Service Error",
            "ExternalAPIError": "External API Error",
            "DatabaseError": "Database Error",
            "ConfigurationError": "Configuration Error",
        }
        return titles.get(self.error_code, "Error")


class ValidationError(AppException):
    """Validation error exception with field-level details."""

    def __init__(self, message: str = "Validation failed", field_errors: Optional[List[Dict[str, str]]] = None):
        super().__init__(message, 400, "ValidationError", errors=field_errors or [])

    @classmethod
    def from_fields(cls, field_errors: Dict[str, str]) -> "ValidationError":
        """Create from field error dictionary."""
        errors = [{"field": field, "message": msg, "code": "invalid_value"} for field, msg in field_errors.items()]
        return cls("Validation failed for one or more fields", field_errors=errors)


class NotFoundError(AppException):
    """Resource not found exception."""

    def __init__(self, message: str = "Resource not found", resource_type: str = None, resource_id: str = None):
        details = {}
        if resource_type:
            details["resource_type"] = resource_type
        if resource_id:
            details["resource_id"] = resource_id
        super().__init__(message, 404, "NotFoundError", details=details)


class UnauthorizedError(AppException):
    """Unauthorized access exception."""

    def __init__(self, message: str = "Authentication required", auth_scheme: str = "Bearer"):
        super().__init__(message, 401, "UnauthorizedError", details={"scheme": auth_scheme})


class ForbiddenError(AppException):
    """Forbidden access exception."""

    def __init__(self, message: str = "Access denied", required_permission: str = None):
        details = {"required_permission": required_permission} if required_permission else {}
        super().__init__(message, 403, "ForbiddenError", details=details)


class ConflictError(AppException):
    """Resource conflict exception."""

    def __init__(self, message: str = "Resource conflict", conflicting_field: str = None):
        details = {"conflicting_field": conflicting_field} if conflicting_field else {}
        super().__init__(message, 409, "ConflictError", details=details)


class RateLimitExceededError(AppException):
    """Rate limit exceeded exception."""

    def __init__(
        self, message: str = "Rate limit exceeded", retry_after: int = None, limit: int = None, remaining: int = 0
    ):
        details = {"retry_after_seconds": retry_after, "limit": limit, "remaining": remaining}
        super().__init__(message, 429, "RateLimitExceededError", details=details)
        self.retry_after = retry_after


class BadRequestError(AppException):
    """Bad request exception."""

    def __init__(self, message: str = "Invalid request"):
        super().__init__(message, 400, "BadRequestError")


class InternalServerError(AppException):
    """Internal server error exception."""

    def __init__(self, message: str = "An unexpected error occurred", error_id: str = None):
        details = {"error_id": error_id} if error_id else {}
        super().__init__(message, 500, "InternalServerError", details=details)


class ServiceUnavailableError(AppException):
    """Service unavailable exception."""

    def __init__(self, message: str = "Service temporarily unavailable", retry_after: int = None):
        details = {"retry_after_seconds": retry_after} if retry_after else {}
        super().__init__(message, 503, "ServiceUnavailableError", details=details)
        self.retry_after = retry_after


class ModelError(AppException):
    """ML Model processing error."""

    def __init__(
        self,
        message: str = "Model processing failed",
        model_name: str = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_details = details.copy() if details else {}
        if model_name:
            error_details["model_name"] = model_name
        super().__init__(message, 500, "ModelError", details=error_details if error_details else None)


class ExternalServiceError(AppException):
    """External service error."""

    def __init__(self, message: str = "External service error", service_name: str = None, is_retryable: bool = True):
        details = {"service_name": service_name, "retryable": is_retryable}
        super().__init__(message, 502, "ExternalServiceError", details=details)


# Aliases for backward compatibility with core/exceptions.py
class AuthenticationError(AppException):
    """Authentication error (alias for UnauthorizedError)."""

    def __init__(self, message: str = "Authentication required"):
        super().__init__(message, 401, "AuthenticationError")


class AuthorizationError(AppException):
    """Authorization error (alias for ForbiddenError)."""

    def __init__(self, message: str = "Permission denied"):
        super().__init__(message, 403, "AuthorizationError")


class RateLimitError(AppException):
    """Rate limit error (alias for RateLimitExceededError)."""

    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = None):
        details = {"retry_after_seconds": retry_after} if retry_after else {}
        super().__init__(message, 429, "RateLimitError", details=details)
        self.retry_after = retry_after


class ExternalAPIError(AppException):
    """External API error (alias for ExternalServiceError)."""

    def __init__(self, message: str, api_name: str = None, original_error: str = None):
        details = {}
        if api_name:
            details["api_name"] = api_name
        if original_error:
            details["original_error"] = original_error
        super().__init__(message, 502, "ExternalAPIError", details=details)


class DatabaseError(AppException):
    """Database operation error."""

    def __init__(self, message: str = "Database operation failed", operation: str = None):
        details = {"operation": operation} if operation else {}
        super().__init__(message, 500, "DatabaseError", details=details)


class ConfigurationError(AppException):
    """Application configuration error."""

    def __init__(self, message: str = "Configuration error", config_key: str = None):
        details = {"config_key": config_key} if config_key else {}
        super().__init__(message, 500, "ConfigurationError", details=details)
