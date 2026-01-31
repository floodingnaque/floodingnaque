"""Enhanced Input Validation and Sanitization Module

Provides comprehensive validation for all API inputs with security hardening.

Security Features:
- HTML/XSS sanitization with bleach
- Path traversal prevention
- Null byte injection protection
- Unicode normalization
- JSON schema validation
- SQL injection pattern detection
"""

import html
import logging
import re
import unicodedata
import warnings
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, List, Optional

import bleach
import validators
from app.utils.api_errors import ValidationError
from flask import g, jsonify, request

logger = logging.getLogger(__name__)


# Per-endpoint body size limits (in bytes)
ENDPOINT_SIZE_LIMITS = {
    "predict": 10 * 1024,  # 10 KB - prediction payload should be small
    "ingest": 10 * 1024,  # 10 KB - coordinates only
    "data": 1 * 1024,  # 1 KB - query params only
    "models": 1 * 1024,  # 1 KB - query params only
    "default": 100 * 1024,  # 100 KB - default limit
}

# Dangerous patterns to detect in inputs
DANGEROUS_PATTERNS = {
    "sql_injection": [
        r"(?:'\s*(?:OR|AND)\s*'?\d*'?\s*=\s*'?\d*)",  # OR/AND injection
        r"(?:;\s*(?:DROP|DELETE|INSERT|UPDATE|ALTER|CREATE|TRUNCATE))",  # Statement injection
        r"(?:UNION\s+(?:ALL\s+)?SELECT)",  # UNION injection
        r"(?:--\s*$|/\*.*\*/)",  # Comment injection
        r"(?:EXEC(?:UTE)?\s+|xp_)",  # Stored procedure
        r"(?:WAITFOR\s+DELAY|BENCHMARK\s*\()",  # Time-based
    ],
    "xss": [
        r"<script[^>]*>.*?</script>",  # Script tags
        r"javascript:\s*",  # javascript: URIs
        r"on\w+\s*=",  # Event handlers (simplified)
        r"<iframe[^>]*>",  # iframes
        r"<object[^>]*>",  # Object tags
        r"<embed[^>]*>",  # Embed tags
        r"expression\s*\(",  # CSS expressions
    ],
    "path_traversal": [
        r"\.\.[/\\]",  # Directory traversal
        r"[/\\]etc[/\\](?:passwd|shadow)",  # Unix sensitive files
        r"[/\\](?:windows|winnt)[/\\]",  # Windows paths
        r"%2e%2e[/\\]",  # URL-encoded traversal
        r"%252e%252e[/\\]",  # Double URL-encoded
    ],
    "command_injection": [
        r"[;&|`$]\s*(?:cat|ls|dir|rm|del|type|wget|curl|bash|sh|cmd)",
        r"\$\(.*\)",  # Command substitution
        r"`[^`]*`",  # Backtick execution
        r"\|\s*\w+",  # Pipe to command
    ],
}

# Compiled regex patterns for performance
_compiled_patterns: Dict[str, List[re.Pattern]] = {}


def _get_compiled_patterns(category: str) -> List[re.Pattern]:
    """Get compiled regex patterns for a category (cached)."""
    if category not in _compiled_patterns:
        patterns = DANGEROUS_PATTERNS.get(category, [])
        _compiled_patterns[category] = [re.compile(p, re.IGNORECASE | re.DOTALL) for p in patterns]
    return _compiled_patterns[category]


def validate_request_size(max_size: Optional[int] = None, endpoint_name: Optional[str] = None):
    """
    Decorator to validate request body size per-endpoint.

    This provides defense-in-depth against memory exhaustion attacks
    by enforcing stricter limits than the global MAX_CONTENT_LENGTH.

    Args:
        max_size: Maximum body size in bytes. If None, uses endpoint default.
        endpoint_name: Name of endpoint for looking up default limit.

    Returns:
        Decorator function
    """

    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Determine size limit
            limit = max_size
            if limit is None:
                name = endpoint_name or f.__name__
                limit = ENDPOINT_SIZE_LIMITS.get(name, ENDPOINT_SIZE_LIMITS["default"])

            # Check content length header first (fast path)
            content_length = request.content_length
            if content_length and content_length > limit:
                request_id = getattr(g, "request_id", "unknown")
                logger.warning(
                    f"Request body too large for {f.__name__} [{request_id}]: "
                    f"{content_length} bytes (limit: {limit})"
                )
                return (
                    jsonify(
                        {
                            "error": "Request too large",
                            "message": f"Request body exceeds endpoint limit of {limit // 1024}KB",
                            "request_id": request_id,
                        }
                    ),
                    413,
                )

            # Also check actual data size (handles chunked encoding)
            if request.data and len(request.data) > limit:
                request_id = getattr(g, "request_id", "unknown")
                logger.warning(
                    f"Request data too large for {f.__name__} [{request_id}]: "
                    f"{len(request.data)} bytes (limit: {limit})"
                )
                return (
                    jsonify(
                        {
                            "error": "Request too large",
                            "message": f"Request body exceeds endpoint limit of {limit // 1024}KB",
                            "request_id": request_id,
                        }
                    ),
                    413,
                )

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def sanitize_input(
    value: str,
    normalize_unicode: bool = True,
    remove_null_bytes: bool = True,
    strip_html: bool = True,
    check_patterns: Optional[List[str]] = None,
) -> str:
    """
    Comprehensive input sanitization.

    Security measures:
    - Unicode normalization (NFC) to prevent homoglyph attacks
    - Null byte removal to prevent injection
    - HTML/script stripping to prevent XSS
    - Dangerous pattern detection

    Args:
        value: Input string to sanitize
        normalize_unicode: Normalize unicode to NFC form
        remove_null_bytes: Remove null bytes and control characters
        strip_html: Remove HTML tags and scripts
        check_patterns: List of pattern categories to check

    Returns:
        Sanitized string

    Raises:
        ValidationError: If dangerous patterns detected
    """
    if not isinstance(value, str):
        value = str(value)

    # Unicode normalization (prevents homoglyph attacks)
    if normalize_unicode:
        value = unicodedata.normalize("NFC", value)

    # Remove null bytes and control characters (except newline, tab)
    if remove_null_bytes:
        value = "".join(char for char in value if char in "\n\r\t" or (ord(char) >= 32 and ord(char) != 127))

    # Strip HTML/scripts
    if strip_html:
        value = bleach.clean(value, tags=[], strip=True)
        # Remove javascript: and other dangerous protocols (XSS prevention)
        value = re.sub(r"javascript\s*:", "", value, flags=re.IGNORECASE)
        value = re.sub(r"vbscript\s*:", "", value, flags=re.IGNORECASE)
        value = re.sub(r"data\s*:", "", value, flags=re.IGNORECASE)
        # Remove event handlers that might have survived
        value = re.sub(r"on\w+\s*=", "", value, flags=re.IGNORECASE)

    # Check for dangerous patterns
    if check_patterns:
        for category in check_patterns:
            patterns = _get_compiled_patterns(category)
            for pattern in patterns:
                if pattern.search(value):
                    logger.warning(f"Dangerous pattern detected in input: category={category}")
                    raise ValidationError(
                        "Input contains potentially dangerous content",
                        field_errors=[
                            {
                                "field": "input",
                                "message": "Invalid characters or patterns detected",
                                "code": "dangerous_content",
                            }
                        ],
                    )

    return value


def check_path_traversal(path: str) -> bool:
    """
    Check if a path contains traversal attempts.

    Args:
        path: Path string to check

    Returns:
        bool: True if safe, raises ValidationError if not
    """
    # Normalize path separators
    normalized = path.replace("\\", "/")

    # Check for common traversal patterns
    patterns = _get_compiled_patterns("path_traversal")
    for pattern in patterns:
        if pattern.search(normalized):
            raise ValidationError(
                "Path traversal attempt detected",
                field_errors=[{"field": "path", "message": "Invalid path characters", "code": "path_traversal"}],
            )

    # Check for encoded characters
    if "%" in path:
        import urllib.parse

        try:
            decoded = urllib.parse.unquote(path)
            if decoded != path:
                # Re-check decoded path
                return check_path_traversal(decoded)
        except Exception:
            raise ValidationError("Invalid URL encoding in path")

    return True


def validate_json_schema(schema: Dict[str, Any]):
    """
    Decorator to validate request JSON against a schema.

    Schema format:
    {
        'type': 'object',
        'properties': {
            'field_name': {
                'type': 'string',  # string, number, integer, boolean, array, object
                'required': True,
                'min_length': 1,
                'max_length': 100,
                'pattern': r'^[a-z]+$',
                'min': 0,
                'max': 100,
                'enum': ['value1', 'value2'],
                'sanitize': True,  # Apply sanitization
                'check_patterns': ['sql_injection', 'xss'],  # Pattern checks
            }
        },
        'additional_properties': False  # Reject unknown fields
    }

    Args:
        schema: JSON schema definition

    Returns:
        Decorator function
    """

    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                data = request.get_json(force=True)
            except Exception:
                return (
                    jsonify(
                        {
                            "error": "Invalid JSON",
                            "message": "Request body must be valid JSON",
                            "request_id": getattr(g, "request_id", "unknown"),
                        }
                    ),
                    400,
                )

            if data is None:
                data = {}

            errors = []
            validated_data = {}

            properties = schema.get("properties", {})
            additional_allowed = schema.get("additional_properties", True)

            # Check for unknown fields
            if not additional_allowed:
                unknown = set(data.keys()) - set(properties.keys())
                if unknown:
                    errors.append(
                        {"field": ", ".join(unknown), "message": "Unknown fields not allowed", "code": "unknown_field"}
                    )

            # Validate each field
            for field_name, field_schema in properties.items():
                value = data.get(field_name)
                required = field_schema.get("required", False)

                # Check required
                if value is None:
                    if required:
                        errors.append({"field": field_name, "message": f"{field_name} is required", "code": "required"})
                    continue

                # Type validation
                field_type = field_schema.get("type", "any")
                try:
                    value = _validate_field_type(value, field_type, field_name)
                except ValidationError:
                    # Use a safe, generic error message instead of exception details
                    errors.append(
                        {
                            "field": field_name,
                            "message": f"Invalid type for {field_name}, expected {field_type}",
                            "code": "type_error",
                        }
                    )
                    continue

                # String-specific validations
                if field_type == "string" and isinstance(value, str):
                    # Sanitize if requested
                    if field_schema.get("sanitize", False):
                        check_patterns = field_schema.get("check_patterns", [])
                        try:
                            value = sanitize_input(value, check_patterns=check_patterns)
                        except ValidationError:
                            # Use a safe, generic error message instead of exception details
                            errors.append(
                                {
                                    "field": field_name,
                                    "message": f"Input sanitization failed for {field_name}",
                                    "code": "sanitization_failed",
                                }
                            )
                            continue

                    # Length checks
                    min_len = field_schema.get("min_length", 0)
                    max_len = field_schema.get("max_length", float("inf"))
                    if len(value) < min_len:
                        errors.append(
                            {"field": field_name, "message": f"Minimum length is {min_len}", "code": "min_length"}
                        )
                    if len(value) > max_len:
                        errors.append(
                            {"field": field_name, "message": f"Maximum length is {max_len}", "code": "max_length"}
                        )

                    # Pattern check
                    pattern = field_schema.get("pattern")
                    if pattern and not re.match(pattern, value):
                        errors.append({"field": field_name, "message": "Invalid format", "code": "pattern"})

                # Numeric validations
                if field_type in ("number", "integer"):
                    min_val = field_schema.get("min")
                    max_val = field_schema.get("max")
                    if min_val is not None and value < min_val:
                        errors.append(
                            {"field": field_name, "message": f"Minimum value is {min_val}", "code": "min_value"}
                        )
                    if max_val is not None and value > max_val:
                        errors.append(
                            {"field": field_name, "message": f"Maximum value is {max_val}", "code": "max_value"}
                        )

                # Enum validation - sanitize enum values in error message
                enum_values = field_schema.get("enum")
                if enum_values and value not in enum_values:
                    # Limit displayed enum values to prevent information disclosure
                    safe_enum_display = str(enum_values[:5]) if len(enum_values) > 5 else str(enum_values)
                    errors.append(
                        {
                            "field": html.escape(str(field_name)),
                            "message": f"Must be one of the allowed values",
                            "code": "enum",
                        }
                    )

                validated_data[field_name] = value

            if errors:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": {
                                "type": "/errors/validation",
                                "title": "Validation Failed",
                                "status": 400,
                                "detail": "One or more fields failed validation",
                                "errors": errors,
                                "request_id": getattr(g, "request_id", "unknown"),
                            },
                        }
                    ),
                    400,
                )

            # Store validated data in request context
            g.validated_data = validated_data

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def _validate_field_type(value: Any, expected_type: str, field_name: str) -> Any:
    """Validate and coerce field to expected type."""
    if expected_type == "string":
        if not isinstance(value, str):
            return str(value)
        return value
    elif expected_type == "integer":
        if isinstance(value, bool):  # bool is subclass of int
            raise ValidationError(f"{field_name} must be an integer")
        if isinstance(value, int):
            return value
        try:
            return int(value)
        except (ValueError, TypeError):
            raise ValidationError(f"{field_name} must be an integer")
    elif expected_type == "number":
        if isinstance(value, bool):
            raise ValidationError(f"{field_name} must be a number")
        if isinstance(value, (int, float)):
            return float(value)
        try:
            return float(value)
        except (ValueError, TypeError):
            raise ValidationError(f"{field_name} must be a number")
    elif expected_type == "boolean":
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            if value.lower() in ("true", "1", "yes"):
                return True
            if value.lower() in ("false", "0", "no"):
                return False
        raise ValidationError(f"{field_name} must be a boolean")
    elif expected_type == "array":
        if not isinstance(value, list):
            raise ValidationError(f"{field_name} must be an array")
        return value
    elif expected_type == "object":
        if not isinstance(value, dict):
            raise ValidationError(f"{field_name} must be an object")
        return value
    else:
        return value  # 'any' type


class InputValidator:
    """Comprehensive input validation for flood prediction system."""

    # Weather data constraints
    TEMPERATURE_MIN_KELVIN = 173.15  # -100°C
    TEMPERATURE_MAX_KELVIN = 333.15  # +60°C
    HUMIDITY_MIN = 0.0
    HUMIDITY_MAX = 100.0
    PRECIPITATION_MIN = 0.0
    PRECIPITATION_MAX = 500.0  # mm (extreme but possible)
    WIND_SPEED_MIN = 0.0
    WIND_SPEED_MAX = 150.0  # m/s (extreme)
    PRESSURE_MIN = 870.0  # hPa (record low)
    PRESSURE_MAX = 1085.0  # hPa (record high)

    # Location constraints
    LATITUDE_MIN = -90.0
    LATITUDE_MAX = 90.0
    LONGITUDE_MIN = -180.0
    LONGITUDE_MAX = 180.0

    # String length limits
    MAX_STRING_LENGTH = 500
    MAX_TEXT_LENGTH = 5000

    @staticmethod
    def validate_float(
        value: Any,
        field_name: str,
        min_val: Optional[float] = None,
        max_val: Optional[float] = None,
        required: bool = True,
    ) -> Optional[float]:
        """
        Validate a float value with range checking.

        Args:
            value: Value to validate
            field_name: Name of the field (for error messages)
            min_val: Minimum allowed value
            max_val: Maximum allowed value
            required: Whether the field is required

        Returns:
            Validated float or None if not required and not provided

        Raises:
            ValidationError: If validation fails
        """
        import math

        if value is None:
            if required:
                raise ValidationError(f"{field_name} is required")
            return None

        try:
            float_val = float(value)
        except (ValueError, TypeError):
            raise ValidationError(f"{field_name} must be a valid number")

        # Check for NaN and infinity
        if math.isnan(float_val):
            raise ValidationError(f"{field_name} must be a valid number, not NaN")

        if math.isinf(float_val):
            raise ValidationError(f"{field_name} must be a finite number, not infinity")

        if min_val is not None and float_val < min_val:
            raise ValidationError(f"{field_name} must be >= {min_val}, got {float_val}")

        if max_val is not None and float_val > max_val:
            raise ValidationError(f"{field_name} must be <= {max_val}, got {float_val}")

        return float_val

    @staticmethod
    def validate_integer(
        value: Any, field_name: str, min_val: Optional[int] = None, max_val: Optional[int] = None, required: bool = True
    ) -> Optional[int]:
        """Validate an integer value with range checking."""
        if value is None:
            if required:
                raise ValidationError(f"{field_name} is required")
            return None

        try:
            int_val = int(value)
        except (ValueError, TypeError):
            raise ValidationError(f"{field_name} must be a valid integer")

        if min_val is not None and int_val < min_val:
            raise ValidationError(f"{field_name} must be >= {min_val}")

        if max_val is not None and int_val > max_val:
            raise ValidationError(f"{field_name} must be <= {max_val}")

        return int_val

    @staticmethod
    def validate_int(
        value: Any,
        field_name: str,
        min_val: Optional[int] = None,
        max_val: Optional[int] = None,
        required: bool = True,
    ) -> Optional[int]:
        """Alias for validate_integer for convenience."""
        return InputValidator.validate_integer(value, field_name, min_val, max_val, required)

    @staticmethod
    def validate_string(
        value: Any,
        field_name: str,
        max_length: Optional[int] = None,
        pattern: Optional[str] = None,
        required: bool = True,
        sanitize: bool = True,
    ) -> Optional[str]:
        """Validate and sanitize string input."""
        if value is None:
            if required:
                raise ValidationError(f"{field_name} is required")
            return None

        if not isinstance(value, str):
            value = str(value)

        # Sanitize HTML/scripts if requested
        if sanitize:
            value = bleach.clean(value, tags=[], strip=True)

        # Check length
        if max_length and len(value) > max_length:
            raise ValidationError(f"{field_name} exceeds maximum length of {max_length} characters")

        # Check pattern
        if pattern and not re.match(pattern, value):
            raise ValidationError(f"{field_name} format is invalid")

        return value.strip()

    @classmethod
    def validate_temperature(cls, temp: Any, required: bool = True) -> Optional[float]:
        """Validate temperature in Kelvin."""
        return cls.validate_float(temp, "temperature", cls.TEMPERATURE_MIN_KELVIN, cls.TEMPERATURE_MAX_KELVIN, required)

    @classmethod
    def validate_humidity(cls, humidity: Any, required: bool = True) -> Optional[float]:
        """Validate humidity percentage."""
        return cls.validate_float(humidity, "humidity", cls.HUMIDITY_MIN, cls.HUMIDITY_MAX, required)

    @classmethod
    def validate_precipitation(cls, precip: Any, required: bool = True) -> Optional[float]:
        """Validate precipitation in mm."""
        return cls.validate_float(precip, "precipitation", cls.PRECIPITATION_MIN, cls.PRECIPITATION_MAX, required)

    @classmethod
    def validate_wind_speed(cls, wind: Any, required: bool = False) -> Optional[float]:
        """Validate wind speed in m/s."""
        return cls.validate_float(wind, "wind_speed", cls.WIND_SPEED_MIN, cls.WIND_SPEED_MAX, required)

    @classmethod
    def validate_pressure(cls, pressure: Any, required: bool = False) -> Optional[float]:
        """Validate atmospheric pressure in hPa."""
        return cls.validate_float(pressure, "pressure", cls.PRESSURE_MIN, cls.PRESSURE_MAX, required)

    @classmethod
    def validate_latitude(cls, lat: Any, required: bool = True) -> Optional[float]:
        """Validate latitude."""
        return cls.validate_float(lat, "latitude", cls.LATITUDE_MIN, cls.LATITUDE_MAX, required)

    @classmethod
    def validate_longitude(cls, lon: Any, required: bool = True) -> Optional[float]:
        """Validate longitude."""
        return cls.validate_float(lon, "longitude", cls.LONGITUDE_MIN, cls.LONGITUDE_MAX, required)

    @classmethod
    def validate_coordinates(cls, lat: Any, lon: Any) -> tuple:
        """Validate geographic coordinates."""
        validated_lat = cls.validate_latitude(lat)
        validated_lon = cls.validate_longitude(lon)
        return (validated_lat, validated_lon)

    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email address format."""
        return validators.email(email) is True

    @staticmethod
    def validate_url(url: str) -> bool:
        """Validate URL format."""
        return validators.url(url) is True

    @staticmethod
    def validate_datetime(dt_str: str, fmt: str = "%Y-%m-%dT%H:%M:%S") -> datetime:
        """Validate and parse datetime string."""
        try:
            return datetime.strptime(dt_str, fmt)
        except ValueError:
            # Try ISO format
            try:
                return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            except ValueError:
                raise ValidationError(f"Invalid datetime format: {dt_str}")

    @classmethod
    def validate_weather_data(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate complete weather data input.

        Args:
            data: Dictionary with weather parameters

        Returns:
            Validated and sanitized dictionary

        Raises:
            ValidationError: If validation fails
        """
        validated = {}

        # Required fields
        validated["temperature"] = cls.validate_temperature(data.get("temperature"))
        validated["humidity"] = cls.validate_humidity(data.get("humidity"))
        validated["precipitation"] = cls.validate_precipitation(data.get("precipitation"))

        # Optional fields
        if "wind_speed" in data:
            validated["wind_speed"] = cls.validate_wind_speed(data.get("wind_speed"), required=False)

        if "pressure" in data:
            validated["pressure"] = cls.validate_pressure(data.get("pressure"), required=False)

        if "location_lat" in data:
            validated["location_lat"] = cls.validate_latitude(data.get("location_lat"), required=False)

        if "location_lon" in data:
            validated["location_lon"] = cls.validate_longitude(data.get("location_lon"), required=False)

        if "source" in data:
            validated["source"] = cls.validate_string(data.get("source"), "source", max_length=50, required=False)

        return validated

    @classmethod
    def validate_prediction_input(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate prediction request input.

        Args:
            data: Dictionary with prediction parameters

        Returns:
            Validated dictionary

        Raises:
            ValidationError: If validation fails
        """
        validated = cls.validate_weather_data(data)

        # Optional model version
        if "model_version" in data:
            validated["model_version"] = cls.validate_integer(
                data.get("model_version"), "model_version", min_val=1, required=False
            )

        return validated

    @staticmethod
    def sanitize_sql_input(value: str) -> str:
        """
        DEPRECATED: This function is scheduled for removal in v3.0.

        Security Note:
        This function provides minimal additional security and should NOT be
        relied upon for SQL injection prevention. Always use parameterized
        queries (SQLAlchemy ORM or bound parameters) instead.

        The function exists only as a legacy defense-in-depth measure.

        Migration Guide:
        Instead of:
            sanitized = InputValidator.sanitize_sql_input(user_input)
            query = f"SELECT * FROM users WHERE name = '{sanitized}'"

        Use parameterized queries:
            session.query(User).filter(User.name == user_input).all()
            # OR
            session.execute(text("SELECT * FROM users WHERE name = :name"), {"name": user_input})

        Args:
            value: Input string to sanitize

        Returns:
            Sanitized string (with dangerous patterns removed)

        Warning:
            This is NOT a substitute for parameterized queries!
            Will be removed in v3.0 - migrate to parameterized queries.
        """
        warnings.warn(
            "sanitize_sql_input is deprecated and will be removed in v3.0. "
            "Use parameterized queries instead. See function docstring for migration guide.",
            DeprecationWarning,
            stacklevel=2,
        )
        # Remove potentially dangerous characters
        dangerous_chars = ["--", ";", "/*", "*/", "xp_", "sp_", "DROP", "DELETE", "INSERT", "UPDATE"]
        cleaned = value
        for char in dangerous_chars:
            cleaned = cleaned.replace(char, "")
        return cleaned

    @staticmethod
    def validate_pagination(limit: Any, offset: Any, max_limit: int = 1000) -> tuple:
        """Validate pagination parameters."""
        try:
            limit = int(limit) if limit is not None else 100
            offset = int(offset) if offset is not None else 0
        except (ValueError, TypeError):
            raise ValidationError("Invalid pagination parameters")

        if limit < 1 or limit > max_limit:
            raise ValidationError(f"Limit must be between 1 and {max_limit}")

        if offset < 0:
            raise ValidationError("Offset must be >= 0")

        return (limit, offset)


# Convenience functions
def validate_weather_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate weather data - convenience wrapper."""
    return InputValidator.validate_weather_data(data)


def validate_prediction_input(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate prediction input - convenience wrapper."""
    return InputValidator.validate_prediction_input(data)


def validate_coordinates(lat: Any, lon: Any) -> tuple:
    """Validate coordinates - convenience wrapper."""
    return InputValidator.validate_coordinates(lat, lon)
