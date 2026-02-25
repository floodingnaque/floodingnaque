"""API Response Utilities.

Standardized response formatting functions for consistent API responses.
Follows RFC 7807 Problem Details format for errors.

Security: Implements comprehensive sanitization to prevent information
disclosure through error messages, stack traces, and exception details
(CWE-209, CWE-497).
"""

import html
import logging
import re
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple

from flask import Response, g, jsonify

if TYPE_CHECKING:
    from app.utils.api_errors import AppException

logger = logging.getLogger(__name__)

# Patterns that might indicate sensitive information in error messages
_SENSITIVE_PATTERNS = [
    r"password",
    r"secret",
    r"token",
    r"key",
    r"credential",
    r"auth",
    r"/[a-zA-Z]:/",  # Windows paths
    r"/home/",  # Unix home paths
    r"/usr/",  # Unix system paths
    r"\\\\[a-zA-Z]",  # UNC paths
    r"postgresql://",  # Database connection strings
    r"mysql://",
    r"mongodb://",
    r"redis://",
    r"amqp://",
]

# Patterns that indicate stack trace content (CWE-209)
_STACK_TRACE_PATTERNS = [
    r"Traceback \(most recent call last\)",  # Python traceback header
    r"File \"[^\"]+\", line \d+",  # Python stack frame
    r"^\s*at\s+[\w.$]+\(",  # Java/JS style stack trace
    r"Exception in thread",  # Java exception
    r"\.py\", line \d+, in \w+",  # Python file references
    r"raise \w+Error",  # Python raise statements
    r"Error:\s+\w+Error:",  # Chained exceptions
]

# Fields that should never be exposed to clients
_DANGEROUS_FIELDS = {
    "debug",
    "stack_trace",
    "stacktrace",
    "traceback",
    "exception",
    "exception_type",
    "exception_message",
    "exc_info",
    "error_details",
    "internal_error",
    "system_error",
}


def _sanitize_error_message(message: str) -> str:
    """
    Sanitize error message to prevent information disclosure.

    Detects and removes stack traces, sensitive patterns, and
    other information that could aid attackers (CWE-209, CWE-497).

    Args:
        message: Raw error message

    Returns:
        Sanitized error message safe for client consumption
    """
    if not message:
        return message

    # HTML escape to prevent XSS
    sanitized = html.escape(str(message))

    # Check for stack trace patterns first (most dangerous for info disclosure)
    for pattern in _STACK_TRACE_PATTERNS:
        if re.search(pattern, sanitized, re.MULTILINE):
            # Log the original for debugging, return generic message
            logger.debug(
                "Sanitized stack trace from error message",
                extra={"original_length": len(message)},
            )
            return "An internal error occurred. Please contact support with your request ID."

    # Check for sensitive patterns
    message_lower = sanitized.lower()
    for pattern in _SENSITIVE_PATTERNS:
        if re.search(pattern, message_lower, re.IGNORECASE):
            # If sensitive pattern detected, return generic message
            logger.debug(
                "Sanitized potentially sensitive error message",
                extra={"pattern_matched": pattern},
            )
            return "An error occurred. Please contact support with your request ID."

    # Truncate overly long messages that might contain stack traces
    if len(sanitized) > 500:
        logger.debug("Truncated long error message", extra={"original_length": len(sanitized)})
        return sanitized[:500] + "..."

    return sanitized


def _sanitize_details(details: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize details dictionary to prevent information exposure.

    Removes or sanitizes values that might contain sensitive information
    such as exception messages, stack traces, or system paths.

    Args:
        details: Raw details dictionary

    Returns:
        Sanitized details dictionary safe for client consumption
    """
    if not details:
        return {}

    # Keys that are known to potentially contain exception info
    sensitive_keys = {
        "error",
        "exception",
        "traceback",
        "stack_trace",
        "error_type",
        "import_error",
        "exc_info",
        "exc_type",
        "exc_value",
        "exc_traceback",
    }

    sanitized = {}
    for key, value in details.items():
        # Remove dangerous fields entirely
        if key.lower() in _DANGEROUS_FIELDS or key in _DANGEROUS_FIELDS:
            logger.debug("Removed dangerous field from details")
            continue

        key_lower = key.lower()

        # Check if key suggests exception/error content
        if key_lower in sensitive_keys or "error" in key_lower or "exception" in key_lower:
            # Replace with generic message
            logger.debug("Sanitized sensitive key in details")
            if isinstance(value, str):
                sanitized[key] = "Error details logged server-side"
            elif isinstance(value, dict):
                sanitized[key] = {"message": "Error details logged server-side"}
            else:
                sanitized[key] = "Error details logged server-side"
        elif isinstance(value, str):
            # Sanitize string values
            sanitized[key] = _sanitize_error_message(value)
        elif isinstance(value, dict):
            # Recursively sanitize nested dicts
            sanitized[key] = _sanitize_details(value)
        elif isinstance(value, list):
            # Sanitize list items
            sanitized[key] = [
                (
                    _sanitize_error_message(item)
                    if isinstance(item, str)
                    else _sanitize_details(item) if isinstance(item, dict) else item
                )
                for item in value
            ]
        else:
            # Pass through non-string primitive values
            sanitized[key] = value

    return sanitized


def _sanitize_errors_list(errors: list) -> list:
    """
    Sanitize a list of field-level errors to prevent information exposure.

    Each error item is expected to be a dict with fields like:
    - field: The field name (safe)
    - message: The error message (needs sanitization)
    - code: Error code (safe)

    Args:
        errors: Raw list of error dictionaries

    Returns:
        Sanitized list of errors safe for client consumption
    """
    if not errors:
        return []

    sanitized = []
    for error in errors:
        if isinstance(error, dict):
            sanitized_error = {}
            for key, value in error.items():
                # Skip dangerous fields
                if key.lower() in _DANGEROUS_FIELDS or key in _DANGEROUS_FIELDS:
                    logger.debug("Removed dangerous field from error list")
                    continue

                if key in ("message", "detail", "error") and isinstance(value, str):
                    # Sanitize message fields
                    sanitized_error[key] = _sanitize_error_message(value)
                elif isinstance(value, str):
                    # Other string fields - basic sanitization
                    sanitized_error[key] = html.escape(value)
                elif isinstance(value, dict):
                    # Recursively sanitize nested dicts
                    sanitized_error[key] = _sanitize_details(value)
                else:
                    sanitized_error[key] = value
            sanitized.append(sanitized_error)
        elif isinstance(error, str):
            sanitized.append(_sanitize_error_message(error))
        else:
            sanitized.append(error)

    return sanitized


def _remove_dangerous_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove all dangerous fields that could expose stack traces or sensitive info.

    This is a final safety net to ensure no dangerous fields slip through.

    Args:
        data: Dictionary to clean

    Returns:
        Dictionary with dangerous fields removed
    """
    if not isinstance(data, dict):
        return data

    cleaned = {}
    for key, value in data.items():
        # Skip dangerous fields
        if key.lower() in _DANGEROUS_FIELDS or key in _DANGEROUS_FIELDS:
            logger.debug("Removed dangerous field from response")
            continue

        # Recursively clean nested dicts
        if isinstance(value, dict):
            cleaned[key] = _remove_dangerous_fields(value)
        elif isinstance(value, list):
            cleaned[key] = [_remove_dangerous_fields(item) if isinstance(item, dict) else item for item in value]
        else:
            cleaned[key] = value

    return cleaned


def _validate_no_stack_trace(response: Dict[str, Any]) -> None:
    """
    Final validation to ensure no stack trace patterns exist in response.

    Args:
        response: Response dictionary to validate

    Raises:
        AssertionError: If stack trace patterns are detected (only in debug mode)
    """
    if __debug__:
        response_str = str(response)
        for pattern in _STACK_TRACE_PATTERNS:
            if re.search(pattern, response_str, re.MULTILINE):
                logger.error("Stack trace pattern detected in final response")
                raise AssertionError("Stack trace pattern detected in sanitized response")


def _get_request_context() -> Dict[str, Optional[str]]:
    """
    Get request and trace IDs from Flask g context.

    Returns:
        Dictionary with request_id and trace_id (may be None)
    """
    return {
        "request_id": getattr(g, "request_id", None),
        "trace_id": getattr(g, "trace_id", None),
    }


def api_success(
    data: Any = None,
    message: Optional[str] = None,
    status_code: int = 200,
    request_id: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> tuple:
    """
    Create a standardized success response.

    Args:
        data: Response data payload
        message: Optional success message
        status_code: HTTP status code (default: 200)
        request_id: Request identifier for tracing (auto-detected if None)
        meta: Optional metadata (pagination, etc.)

    Returns:
        Tuple of (response_dict, status_code)
    """
    ctx = _get_request_context()

    response = {
        "success": True,
        "request_id": request_id or ctx.get("request_id"),
    }

    if ctx.get("trace_id"):
        response["trace_id"] = ctx["trace_id"]

    if data is not None:
        response["data"] = data

    if message:
        response["message"] = message

    if meta:
        response["meta"] = meta

    return jsonify(response), status_code


def api_error(
    error_code: str,
    message: str,
    status_code: int = 400,
    request_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    errors: Optional[list] = None,
    help_url: Optional[str] = None,
) -> tuple:
    """
    Create a standardized RFC 7807 error response.

    All inputs are sanitized to prevent information disclosure through
    error messages, stack traces, or exception details (CWE-209, CWE-497).

    Args:
        error_code: Error code identifier
        message: Human-readable error message
        status_code: HTTP status code (default: 400)
        request_id: Request identifier for tracing (auto-detected if None)
        details: Optional additional error details
        errors: Optional list of field-level errors
        help_url: Optional URL for more information

    Returns:
        Tuple of (response_dict, status_code)
    """
    ctx = _get_request_context()
    req_id = request_id or ctx.get("request_id")
    trace_id = ctx.get("trace_id")

    # Sanitize error message to prevent information disclosure
    safe_message = _sanitize_error_message(message)

    response = {
        "success": False,
        "error": {
            "type": f'/errors/{error_code.lower().replace("error", "").replace("_", "-")}',
            "title": _get_error_title(error_code),
            "status": status_code,
            "detail": safe_message,
            "code": error_code,
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        },
    }

    if req_id:
        response["error"]["request_id"] = req_id

    if trace_id:
        response["error"]["trace_id"] = trace_id

    if details:
        # Sanitize details to prevent information exposure
        response["error"]["details"] = _sanitize_details(details)

    if errors:
        # Sanitize errors list to prevent stack trace exposure (CWE-209)
        response["error"]["errors"] = _sanitize_errors_list(errors)

    if help_url:
        response["error"]["help_url"] = help_url

    # Final safety check: remove any dangerous fields
    response = _remove_dangerous_fields(response)

    logger.warning(
        f"API Error [{req_id}]: {error_code}",
        extra={
            "error_code": error_code,
            "status_code": status_code,
            "request_id": req_id,
        },
    )

    return jsonify(response), status_code


def api_error_from_exception(
    exception: "AppException",
    request_id: Optional[str] = None,
    include_debug: bool = False,
) -> Tuple[Response, int]:
    """
    Create a standardized RFC 7807 error response from an AppException.

    SECURITY: This function implements defense-in-depth sanitization to prevent
    stack trace exposure (CWE-209). Debug details are NEVER included in client
    responses - they are logged server-side only.

    Args:
        exception: The AppException instance
        request_id: Request tracking ID (auto-detected if None)
        include_debug: Deprecated - debug details are never sent to clients

    Returns:
        Tuple of (Flask JSON response, status code)
    """
    ctx = _get_request_context()

    # Log full exception details server-side for debugging
    # This keeps sensitive info in logs, not in client responses
    logger.info(
        f"Processing exception: {exception.error_code}",
        extra={
            "error_code": exception.error_code,
            "status_code": exception.status_code,
            "has_details": bool(getattr(exception, "details", None)),
        },
    )

    if include_debug and hasattr(exception, "details") and exception.details:
        logger.debug(
            f"Exception details (server-side only): {exception.error_code}",
            extra={"exception_details": exception.details},
        )

    # SECURITY LAYER 1: Get base response without debug info
    # Force include_debug=False to prevent any debug details
    response = exception.to_dict(include_debug=False)

    # SECURITY LAYER 2: Ensure proper structure
    if "error" not in response:
        response["error"] = {}

    # SECURITY LAYER 3: Set request tracking IDs
    response["error"]["request_id"] = request_id or ctx.get("request_id")
    if ctx.get("trace_id"):
        response["error"]["trace_id"] = ctx["trace_id"]

    # SECURITY LAYER 4: Sanitize the error detail message
    if "detail" in response.get("error", {}):
        original_detail = response["error"]["detail"]
        response["error"]["detail"] = _sanitize_error_message(original_detail)
        if original_detail != response["error"]["detail"]:
            logger.debug("Sanitized error detail message")

    # SECURITY LAYER 5: Sanitize details dict if present
    if "details" in response.get("error", {}):
        original_details = response["error"]["details"]
        response["error"]["details"] = _sanitize_details(original_details)
        logger.debug("Sanitized error details dictionary")

    # SECURITY LAYER 6: Sanitize errors list if present
    if "errors" in response.get("error", {}):
        original_errors = response["error"]["errors"]
        response["error"]["errors"] = _sanitize_errors_list(original_errors)
        logger.debug("Sanitized error list")

    # SECURITY LAYER 7: Remove all dangerous fields
    # This is the final safety net to catch anything that slipped through
    response = _remove_dangerous_fields(response)

    # SECURITY LAYER 8: Explicitly remove known dangerous fields
    # Even after sanitization, defensively remove these
    dangerous_keys = list(_DANGEROUS_FIELDS)
    for key in dangerous_keys:
        if key in response.get("error", {}):
            logger.warning(f"Removed dangerous field that survived sanitization: {key}")
            response["error"].pop(key, None)

    # SECURITY LAYER 9: Final validation before sending response
    _validate_no_stack_trace(response)

    logger.warning(
        f"API Exception [{response['error'].get('request_id')}]: {exception.error_code}",
        extra={
            "error_code": exception.error_code,
            "status_code": exception.status_code,
            "request_id": response["error"].get("request_id"),
        },
    )

    resp = jsonify(response)

    # Add Retry-After header if applicable
    retry_after = getattr(exception, "retry_after", None)
    if retry_after:
        resp.headers["Retry-After"] = str(retry_after)

    return resp, exception.status_code


def _get_error_title(error_code: str) -> str:
    """
    Get human-readable title for error code.

    Args:
        error_code: Error code string

    Returns:
        Human-readable error title
    """
    titles = {
        "VALIDATION_ERROR": "Validation Failed",
        "ValidationError": "Validation Failed",
        "NOT_FOUND": "Resource Not Found",
        "NotFoundError": "Resource Not Found",
        "UNAUTHORIZED": "Authentication Required",
        "UnauthorizedError": "Authentication Required",
        "FORBIDDEN": "Access Denied",
        "ForbiddenError": "Access Denied",
        "CONFLICT": "Resource Conflict",
        "ConflictError": "Resource Conflict",
        "RATE_LIMIT_EXCEEDED": "Rate Limit Exceeded",
        "RateLimitExceededError": "Rate Limit Exceeded",
        "BAD_REQUEST": "Bad Request",
        "BadRequestError": "Bad Request",
        "INTERNAL_ERROR": "Internal Server Error",
        "InternalServerError": "Internal Server Error",
        "SERVICE_UNAVAILABLE": "Service Unavailable",
        "ServiceUnavailableError": "Service Unavailable",
        "MODEL_ERROR": "Model Processing Error",
        "ModelError": "Model Processing Error",
        "EXTERNAL_SERVICE_ERROR": "External Service Error",
        "ExternalServiceError": "External Service Error",
        "DATABASE_ERROR": "Database Error",
        "DatabaseError": "Database Error",
    }
    return titles.get(error_code, "Error")


def api_created(
    data: Any = None,
    message: str = "Resource created successfully",
    location: Optional[str] = None,
    request_id: Optional[str] = None,
) -> tuple:
    """
    Create a standardized response for created resources (201 Created).

    Args:
        data: Response data payload
        message: Success message
        location: URI of created resource
        request_id: Request identifier for tracing (auto-detected if None)

    Returns:
        Tuple of (response_dict, 201, headers)
    """
    ctx = _get_request_context()

    response = {"success": True, "message": message, "request_id": request_id or ctx.get("request_id")}

    if ctx.get("trace_id"):
        response["trace_id"] = ctx["trace_id"]

    if data is not None:
        response["data"] = data

    headers = {}
    if location:
        headers["Location"] = location

    return jsonify(response), 201, headers


def api_accepted(
    data: Any = None, message: str = "Request accepted for processing", request_id: Optional[str] = None
) -> tuple:
    """
    Create a standardized response for accepted requests (202 Accepted).

    Args:
        data: Response data payload
        message: Success message
        request_id: Request identifier for tracing (auto-detected if None)

    Returns:
        Tuple of (response_dict, 202)
    """
    ctx = _get_request_context()

    response = {"success": True, "message": message, "request_id": request_id or ctx.get("request_id")}

    if ctx.get("trace_id"):
        response["trace_id"] = ctx["trace_id"]

    if data is not None:
        response["data"] = data

    return jsonify(response), 202


def api_no_content() -> tuple:
    """
    Create a 204 No Content response.

    Returns:
        Tuple of ('', 204)
    """
    return "", 204


def api_paginated(data: list, page: int, page_size: int, total: int, request_id: Optional[str] = None) -> tuple:
    """
    Create a standardized paginated response.

    Args:
        data: List of items for current page
        page: Current page number (1-indexed)
        page_size: Number of items per page
        total: Total number of items
        request_id: Request identifier for tracing

    Returns:
        Tuple of (response_dict, 200)
    """
    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0

    meta = {
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        }
    }

    return api_success(data=data, request_id=request_id, meta=meta)
