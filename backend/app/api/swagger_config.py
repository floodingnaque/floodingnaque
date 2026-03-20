"""Swagger/OpenAPI 3.1 Configuration.

Auto-generated interactive API documentation.
Upgraded to OpenAPI 3.1 specification for better frontend codegen support
and JSON Schema 2020-12 compatibility.
"""

import html
import json
import logging
from functools import wraps

from flasgger import Swagger
from flask import Response, request

logger = logging.getLogger(__name__)

# OpenAPI 3.1.0 Template (latest specification)
# Note: flasgger may still render as 3.0.x, but schema definitions follow 3.1 patterns
SWAGGER_TEMPLATE = {
    "openapi": "3.1.0",
    "info": {
        "title": "Floodingnaque API",
        "description": """Flood prediction and monitoring system for Paranaque City.

## Features
- Real-time flood predictions using ML models
- Historical weather data management
- Alert system with SSE for real-time notifications
- Dashboard analytics and statistics
- User authentication with JWT

## API Versioning
All API endpoints are prefixed with `/api/v1/`.

## Authentication
Most endpoints require authentication via:
- JWT Bearer Token in Authorization header
- API Key in X-API-Key header

## Interactive API Explorer
This documentation provides an interactive API explorer where you can:
- Try out API calls directly from the browser
- View request/response examples
- Generate client code snippets

## Rate Limits
| Endpoint | Limit |
|----------|-------|
| /predict | 60/hour |
| /ingest | 30/hour |
| /data | 100/hour |
| /alerts | 50/hour |

## Response Format
All responses follow a consistent JSON structure:
```json
{
  "success": true,
  "data": { ... },
  "request_id": "uuid-string"
}
```
""",
        "version": "2.1.0",
        "contact": {"name": "Floodingnaque Team", "url": "https://github.com/floodingnaque/floodingnaque"},
        "license": {"name": "MIT", "identifier": "MIT", "url": "https://opensource.org/licenses/MIT"},
        "x-logo": {"url": "/static/logo.png", "altText": "Floodingnaque API"},
    },
    "servers": [
        {"url": "http://localhost:5000", "description": "Local development server"},
        {"url": "https://api.floodingnaque.com", "description": "Production server"},
    ],
    "components": {
        "securitySchemes": {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "JWT Bearer token authentication",
            },
            "APIKeyHeader": {
                "type": "apiKey",
                "name": "X-API-Key",
                "in": "header",
                "description": "API key for authentication",
            },
        },
        "schemas": {
            "Error": {
                "type": "object",
                "description": "Standard error response following RFC 7807 Problem Details",
                "required": ["success", "error"],
                "properties": {
                    "success": {"type": "boolean", "const": False, "description": "Always false for error responses"},
                    "error": {
                        "type": "object",
                        "required": ["type", "title", "status", "detail"],
                        "properties": {
                            "type": {"type": "string", "format": "uri", "description": "Error type URI"},
                            "title": {"type": "string", "description": "Short error title"},
                            "status": {
                                "type": "integer",
                                "minimum": 400,
                                "maximum": 599,
                                "description": "HTTP status code",
                            },
                            "detail": {"type": "string", "description": "Human-readable error description"},
                            "code": {"type": "string", "description": "Application-specific error code"},
                            "request_id": {"type": "string", "format": "uuid", "description": "Request tracking ID"},
                            "timestamp": {"type": "string", "format": "date-time", "description": "Error timestamp"},
                        },
                    },
                },
                "examples": {
                    "validation_error": {
                        "summary": "Validation Error",
                        "value": {
                            "success": False,
                            "error": {
                                "type": "https://api.floodingnaque.com/errors/validation",
                                "title": "Validation Error",
                                "status": 400,
                                "detail": "temperature must be between 173.15 and 333.15 Kelvin",
                                "code": "INVALID_TEMPERATURE",
                                "request_id": "550e8400-e29b-41d4-a716-446655440000",
                                "timestamp": "2026-01-12T10:30:00Z",
                            },
                        },
                    },
                    "rate_limit_error": {
                        "summary": "Rate Limit Exceeded",
                        "value": {
                            "success": False,
                            "error": {
                                "type": "https://api.floodingnaque.com/errors/rate-limit",
                                "title": "Rate Limit Exceeded",
                                "status": 429,
                                "detail": "You have exceeded the rate limit of 60 requests per hour",
                                "code": "RATE_LIMIT_EXCEEDED",
                                "request_id": "550e8400-e29b-41d4-a716-446655440001",
                                "timestamp": "2026-01-12T10:30:00Z",
                            },
                        },
                    },
                },
            },
            "PredictionRequest": {
                "type": "object",
                "description": "Weather data input for flood risk prediction",
                "required": ["temperature", "humidity", "precipitation"],
                "properties": {
                    "temperature": {
                        "type": "number",
                        "minimum": 173.15,
                        "maximum": 333.15,
                        "description": "Temperature in Kelvin (range: 173.15-333.15K, equivalent to -100°C to 60°C)",
                        "examples": [303.15, 298.15, 308.15],
                    },
                    "humidity": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 100,
                        "description": "Relative humidity percentage (0-100%)",
                        "examples": [85.0, 65.0, 95.0],
                    },
                    "precipitation": {
                        "type": "number",
                        "minimum": 0,
                        "description": "Precipitation in mm/hour (must be >= 0)",
                        "examples": [25.5, 0.0, 100.0],
                    },
                    "wind_speed": {
                        "type": "number",
                        "minimum": 0,
                        "description": "Wind speed in m/s (optional)",
                        "examples": [15.0, 5.0, 30.0],
                    },
                    "pressure": {
                        "type": "number",
                        "minimum": 870,
                        "maximum": 1084,
                        "description": "Atmospheric pressure in hPa (optional, range: 870-1084)",
                        "examples": [1010.0, 1005.0, 1020.0],
                    },
                    "model_version": {
                        "type": "string",
                        "pattern": "^v[0-9]+\\.[0-9]+\\.?[0-9]*$",
                        "description": "Specific model version to use (optional, e.g., 'v4.0')",
                        "examples": ["v4.0", "v3.1", "latest"],
                    },
                },
                "examples": {
                    "normal_conditions": {
                        "summary": "Normal Weather Conditions",
                        "description": "Typical day with low flood risk",
                        "value": {
                            "temperature": 303.15,
                            "humidity": 65.0,
                            "precipitation": 5.0,
                            "wind_speed": 10.0,
                            "pressure": 1013.0,
                        },
                    },
                    "heavy_rain": {
                        "summary": "Heavy Rainfall",
                        "description": "Conditions during heavy monsoon rain",
                        "value": {
                            "temperature": 298.15,
                            "humidity": 95.0,
                            "precipitation": 50.0,
                            "wind_speed": 25.0,
                            "pressure": 1000.0,
                        },
                    },
                    "typhoon_conditions": {
                        "summary": "Typhoon Conditions",
                        "description": "Extreme weather during typhoon",
                        "value": {
                            "temperature": 295.15,
                            "humidity": 98.0,
                            "precipitation": 100.0,
                            "wind_speed": 50.0,
                            "pressure": 980.0,
                        },
                    },
                },
            },
            "PredictionResponse": {
                "type": "object",
                "description": "Flood risk prediction result with confidence scores",
                "required": ["success", "data", "request_id"],
                "properties": {
                    "success": {"type": "boolean", "const": True},
                    "data": {
                        "type": "object",
                        "required": ["prediction", "risk_level", "risk_label", "confidence"],
                        "properties": {
                            "prediction": {
                                "type": "integer",
                                "enum": [0, 1],
                                "description": "Binary flood prediction (0=no flood, 1=flood)",
                            },
                            "flood_risk": {
                                "type": "string",
                                "enum": ["low", "high"],
                                "description": "Human-readable binary risk label",
                            },
                            "risk_level": {
                                "type": "integer",
                                "enum": [0, 1, 2],
                                "description": "3-level risk classification (0=Safe, 1=Alert, 2=Critical)",
                            },
                            "risk_label": {
                                "type": "string",
                                "enum": ["Safe", "Alert", "Critical"],
                                "description": "Human-readable 3-level risk label",
                            },
                            "confidence": {
                                "type": "number",
                                "minimum": 0,
                                "maximum": 1,
                                "description": "Model confidence score (0-1)",
                            },
                            "probability": {
                                "type": "number",
                                "minimum": 0,
                                "maximum": 1,
                                "description": "Flood probability (0-1)",
                            },
                            "probabilities": {
                                "type": "object",
                                "description": "Probability distribution across risk levels",
                                "properties": {
                                    "safe": {"type": "number", "minimum": 0, "maximum": 1},
                                    "alert": {"type": "number", "minimum": 0, "maximum": 1},
                                    "critical": {"type": "number", "minimum": 0, "maximum": 1},
                                },
                            },
                            "model_version": {
                                "type": "string",
                                "description": "Version of the model used for prediction",
                            },
                            "cache_hit": {"type": "boolean", "description": "Whether result was served from cache"},
                        },
                    },
                    "request_id": {"type": "string", "format": "uuid"},
                },
                "examples": {
                    "safe_prediction": {
                        "summary": "Safe - Low Risk",
                        "value": {
                            "success": True,
                            "data": {
                                "prediction": 0,
                                "flood_risk": "low",
                                "risk_level": 0,
                                "risk_label": "Safe",
                                "confidence": 0.92,
                                "probability": 0.08,
                                "probabilities": {"safe": 0.85, "alert": 0.12, "critical": 0.03},
                                "model_version": "v4.0",
                                "cache_hit": False,
                            },
                            "request_id": "550e8400-e29b-41d4-a716-446655440000",
                        },
                    },
                    "alert_prediction": {
                        "summary": "Alert - Medium Risk",
                        "value": {
                            "success": True,
                            "data": {
                                "prediction": 1,
                                "flood_risk": "high",
                                "risk_level": 1,
                                "risk_label": "Alert",
                                "confidence": 0.78,
                                "probability": 0.65,
                                "probabilities": {"safe": 0.22, "alert": 0.58, "critical": 0.20},
                                "model_version": "v4.0",
                                "cache_hit": False,
                            },
                            "request_id": "550e8400-e29b-41d4-a716-446655440001",
                        },
                    },
                    "critical_prediction": {
                        "summary": "Critical - High Risk",
                        "value": {
                            "success": True,
                            "data": {
                                "prediction": 1,
                                "flood_risk": "high",
                                "risk_level": 2,
                                "risk_label": "Critical",
                                "confidence": 0.95,
                                "probability": 0.89,
                                "probabilities": {"safe": 0.05, "alert": 0.15, "critical": 0.80},
                                "model_version": "v4.0",
                                "cache_hit": False,
                            },
                            "request_id": "550e8400-e29b-41d4-a716-446655440002",
                        },
                    },
                },
            },
            "Alert": {
                "type": "object",
                "description": "Flood alert notification",
                "required": ["id", "risk_level", "risk_label", "created_at"],
                "properties": {
                    "id": {"type": "integer", "description": "Unique alert identifier"},
                    "risk_level": {"type": "integer", "enum": [0, 1, 2], "description": "Numeric risk level"},
                    "risk_label": {"type": "string", "enum": ["Safe", "Alert", "Critical"]},
                    "location": {"type": "string", "description": "Affected barangay or area"},
                    "message": {"type": "string", "description": "Alert message content"},
                    "delivery_status": {"type": "string", "enum": ["delivered", "pending", "failed"]},
                    "created_at": {"type": "string", "format": "date-time"},
                },
                "examples": {
                    "critical_alert": {
                        "summary": "Critical Flood Alert",
                        "value": {
                            "id": 1234,
                            "risk_level": 2,
                            "risk_label": "Critical",
                            "location": "Barangay San Antonio",
                            "message": "CRITICAL: Flood risk detected. Evacuate low-lying areas immediately.",
                            "delivery_status": "delivered",
                            "created_at": "2026-01-12T14:30:00Z",
                        },
                    }
                },
            },
            "SSEEvent": {
                "type": "object",
                "description": "Server-Sent Event for real-time updates",
                "properties": {
                    "event": {"type": "string", "enum": ["alert", "heartbeat", "connected", "prediction"]},
                    "data": {"type": "object"},
                },
                "examples": {
                    "alert_event": {
                        "summary": "Alert Event",
                        "value": {
                            "event": "alert",
                            "data": {"id": 1234, "risk_level": 2, "message": "Critical flood warning for San Antonio"},
                        },
                    },
                    "heartbeat_event": {
                        "summary": "Heartbeat Event",
                        "value": {"event": "heartbeat", "data": {"timestamp": "2026-01-12T14:30:00Z"}},
                    },
                },
            },
            "IngestRequest": {
                "type": "object",
                "description": "Request to ingest weather data for a location",
                "required": ["lat", "lon"],
                "properties": {
                    "lat": {
                        "type": "number",
                        "minimum": -90,
                        "maximum": 90,
                        "description": "Latitude in decimal degrees",
                        "examples": [14.4793],
                    },
                    "lon": {
                        "type": "number",
                        "minimum": -180,
                        "maximum": 180,
                        "description": "Longitude in decimal degrees",
                        "examples": [121.0198],
                    },
                    "source": {
                        "type": "string",
                        "enum": ["openweathermap", "meteostat", "open-meteo"],
                        "default": "openweathermap",
                        "description": "Weather data source",
                    },
                },
                "examples": {
                    "paranaque_center": {
                        "summary": "Paranaque City Center",
                        "value": {"lat": 14.4793, "lon": 121.0198},
                    },
                    "bf_homes": {
                        "summary": "BF Homes Paranaque",
                        "value": {"lat": 14.4289, "lon": 121.0234, "source": "open-meteo"},
                    },
                },
            },
            "IngestResponse": {
                "type": "object",
                "description": "Weather data ingestion result",
                "properties": {
                    "success": {"type": "boolean"},
                    "data": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"},
                            "temperature": {"type": "number"},
                            "humidity": {"type": "number"},
                            "precipitation": {"type": "number"},
                            "wind_speed": {"type": "number"},
                            "pressure": {"type": "number"},
                            "source": {"type": "string"},
                            "timestamp": {"type": "string", "format": "date-time"},
                        },
                    },
                    "request_id": {"type": "string", "format": "uuid"},
                },
                "examples": {
                    "successful_ingest": {
                        "summary": "Successful Weather Ingest",
                        "value": {
                            "success": True,
                            "data": {
                                "id": 5678,
                                "temperature": 303.15,
                                "humidity": 78.0,
                                "precipitation": 2.5,
                                "wind_speed": 12.0,
                                "pressure": 1010.0,
                                "source": "openweathermap",
                                "timestamp": "2026-01-12T14:00:00Z",
                            },
                            "request_id": "550e8400-e29b-41d4-a716-446655440003",
                        },
                    }
                },
            },
            "HealthResponse": {
                "type": "object",
                "description": "System health check response",
                "properties": {
                    "status": {"type": "string", "enum": ["healthy", "degraded", "unhealthy"]},
                    "version": {"type": "string"},
                    "uptime_seconds": {"type": "number"},
                    "checks": {
                        "type": "object",
                        "properties": {
                            "database": {"$ref": "#/components/schemas/HealthCheck"},
                            "redis": {"$ref": "#/components/schemas/HealthCheck"},
                            "model": {"$ref": "#/components/schemas/HealthCheck"},
                        },
                    },
                },
                "examples": {
                    "healthy_system": {
                        "summary": "All Systems Healthy",
                        "value": {
                            "status": "healthy",
                            "version": "2.1.0",
                            "uptime_seconds": 86400,
                            "checks": {
                                "database": {"status": "healthy", "latency_ms": 5.2},
                                "redis": {"status": "healthy", "latency_ms": 1.1},
                                "model": {"status": "healthy", "version": "v4.0"},
                            },
                        },
                    }
                },
            },
            "HealthCheck": {
                "type": "object",
                "description": "Individual health check result",
                "properties": {
                    "status": {"type": "string", "enum": ["healthy", "unhealthy", "degraded"]},
                    "latency_ms": {"type": "number"},
                    "error": {"type": "string"},
                    "version": {"type": "string"},
                },
            },
            "DashboardStats": {
                "type": "object",
                "description": "Dashboard summary statistics",
                "properties": {
                    "total_predictions": {"type": "integer"},
                    "predictions_today": {"type": "integer"},
                    "active_alerts": {"type": "integer"},
                    "current_risk_level": {"type": "string"},
                    "weather_data_count": {"type": "integer"},
                    "model_version": {"type": "string"},
                    "last_prediction": {"type": "string", "format": "date-time"},
                },
                "examples": {
                    "dashboard_summary": {
                        "summary": "Dashboard Statistics",
                        "value": {
                            "total_predictions": 15420,
                            "predictions_today": 127,
                            "active_alerts": 2,
                            "current_risk_level": "Alert",
                            "weather_data_count": 45000,
                            "model_version": "v4.0",
                            "last_prediction": "2026-01-12T14:25:00Z",
                        },
                    }
                },
            },
            "BatchPredictionRequest": {
                "type": "object",
                "description": "Batch prediction request for multiple data points",
                "required": ["predictions"],
                "properties": {
                    "predictions": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 100,
                        "items": {"$ref": "#/components/schemas/PredictionRequest"},
                    },
                    "return_all_probabilities": {"type": "boolean", "default": False},
                },
                "examples": {
                    "batch_request": {
                        "summary": "Batch of 3 Predictions",
                        "value": {
                            "predictions": [
                                {"temperature": 303.15, "humidity": 65, "precipitation": 5},
                                {"temperature": 298.15, "humidity": 95, "precipitation": 50},
                                {"temperature": 295.15, "humidity": 98, "precipitation": 100},
                            ],
                            "return_all_probabilities": True,
                        },
                    }
                },
            },
        },
        "responses": {
            "BadRequest": {
                "description": "Bad request - invalid input",
                "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}},
            },
            "Unauthorized": {
                "description": "Authentication required",
                "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}},
            },
            "NotFound": {
                "description": "Resource not found",
                "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}},
            },
            "RateLimited": {
                "description": "Rate limit exceeded",
                "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}},
            },
            "InternalError": {
                "description": "Internal server error",
                "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}},
            },
        },
    },
    "security": [{"BearerAuth": []}, {"APIKeyHeader": []}],
    "tags": [
        {"name": "Health", "description": "Health check and system status endpoints"},
        {"name": "Prediction", "description": "Flood prediction endpoints"},
        {"name": "Data", "description": "Historical weather data management"},
        {"name": "Predictions", "description": "Prediction history and analytics"},
        {"name": "Alerts", "description": "Alert management and history"},
        {"name": "Real-time", "description": "Server-Sent Events for live updates"},
        {"name": "Dashboard", "description": "Dashboard summary and statistics"},
        {"name": "Authentication", "description": "User authentication and session management"},
        {"name": "Webhooks", "description": "Webhook management for alerts"},
        {"name": "Export", "description": "Data export endpoints"},
        {"name": "Batch", "description": "Batch processing endpoints"},
        {"name": "Models", "description": "ML model information and management"},
        {"name": "Tasks", "description": "Background task management"},
        {"name": "Tides", "description": "Tide data and predictions"},
        {"name": "Performance", "description": "API performance monitoring"},
    ],
}

SWAGGER_CONFIG = {
    "headers": [],
    "specs": [
        {
            "endpoint": "apispec",
            "route": "/apispec.json",
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/apidocs",
    "openapi": "3.1.0",
    # Swagger UI configuration for better interactivity
    "swagger_ui_config": {
        "docExpansion": "list",
        "defaultModelsExpandDepth": 2,
        "defaultModelExpandDepth": 2,
        "deepLinking": True,
        "displayRequestDuration": True,
        "filter": True,
        "showExtensions": True,
        "showCommonExtensions": True,
        "tryItOutEnabled": True,
        "persistAuthorization": True,
        "syntaxHighlight.theme": "monokai",
    },
}


# Schema validation decorator for request validation
def validate_openapi_schema(schema_name: str):
    """
    Decorator to validate request body against OpenAPI schema.

    Args:
        schema_name: Name of the schema in components/schemas

    Usage:
        @validate_openapi_schema('PredictionRequest')
        def predict():
            ...
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if request.method in ["POST", "PUT", "PATCH"] and request.is_json:
                try:
                    data = request.get_json()
                    schema = SWAGGER_TEMPLATE.get("components", {}).get("schemas", {}).get(schema_name, {})

                    if schema:
                        errors = _validate_against_schema(data, schema)
                        if errors:
                            return {
                                "success": False,
                                "error": {
                                    "type": "https://api.floodingnaque.com/errors/validation",
                                    "title": "Schema Validation Error",
                                    "status": 400,
                                    "detail": "; ".join(errors),
                                    "code": "SCHEMA_VALIDATION_ERROR",
                                },
                            }, 400
                except Exception as e:
                    logger.warning(f"Schema validation error: {e}")
            return f(*args, **kwargs)

        return decorated_function

    return decorator


def _validate_against_schema(data: dict, schema: dict) -> list:
    """
    Validate data against OpenAPI 3.1 schema.

    Args:
        data: Request data to validate
        schema: OpenAPI schema definition

    Returns:
        List of validation error messages
    """
    errors = []

    # Check required fields
    required = schema.get("required", [])
    for field in required:
        if field not in data:
            errors.append(f"Missing required field: {field}")

    # Validate properties
    properties = schema.get("properties", {})
    for field, value in data.items():
        if field not in properties:
            continue  # Allow additional properties by default

        prop_schema = properties[field]
        field_errors = _validate_field(field, value, prop_schema)
        errors.extend(field_errors)

    return errors


def _validate_field(field: str, value, prop_schema: dict) -> list:
    """
    Validate a single field against its schema.

    Args:
        field: Field name
        value: Field value
        prop_schema: Property schema definition

    Returns:
        List of validation error messages
    """
    errors = []
    expected_type = prop_schema.get("type")

    # Type validation
    if expected_type == "number" and not isinstance(value, (int, float)):
        errors.append(f"{field} must be a number")
        return errors
    elif expected_type == "integer" and not isinstance(value, int):
        errors.append(f"{field} must be an integer")
        return errors
    elif expected_type == "string" and not isinstance(value, str):
        errors.append(f"{field} must be a string")
        return errors
    elif expected_type == "boolean" and not isinstance(value, bool):
        errors.append(f"{field} must be a boolean")
        return errors
    elif expected_type == "array" and not isinstance(value, list):
        errors.append(f"{field} must be an array")
        return errors

    # Numeric constraints
    if isinstance(value, (int, float)):
        if "minimum" in prop_schema and value < prop_schema["minimum"]:
            errors.append(f"{field} must be >= {prop_schema['minimum']}")
        if "maximum" in prop_schema and value > prop_schema["maximum"]:
            errors.append(f"{field} must be <= {prop_schema['maximum']}")

    # String constraints
    if isinstance(value, str):
        if "minLength" in prop_schema and len(value) < prop_schema["minLength"]:
            errors.append(f"{field} must have at least {prop_schema['minLength']} characters")
        if "maxLength" in prop_schema and len(value) > prop_schema["maxLength"]:
            errors.append(f"{field} must have at most {prop_schema['maxLength']} characters")
        if "pattern" in prop_schema:
            import re

            if not re.match(prop_schema["pattern"], value):
                errors.append(f"{field} does not match required pattern")

    # Enum validation
    if "enum" in prop_schema and value not in prop_schema["enum"]:
        errors.append(f"{field} must be one of: {prop_schema['enum']}")

    # Array constraints
    if isinstance(value, list):
        if "minItems" in prop_schema and len(value) < prop_schema["minItems"]:
            errors.append(f"{field} must have at least {prop_schema['minItems']} items")
        if "maxItems" in prop_schema and len(value) > prop_schema["maxItems"]:
            errors.append(f"{field} must have at most {prop_schema['maxItems']} items")

    return errors


def init_swagger(app):
    """Initialize Swagger documentation and OpenAPI export."""
    swagger = Swagger(app, template=SWAGGER_TEMPLATE, config=SWAGGER_CONFIG)

    # Add route to export OpenAPI schema as JSON file
    @app.route("/openapi.json", methods=["GET"])
    def export_openapi_schema():
        """Export OpenAPI 3.1 schema as JSON for frontend codegen.
        ---
        tags:
          - Documentation
        produces:
          - application/json
        responses:
          200:
            description: OpenAPI 3.1 specification
            content:
              application/json:
                schema:
                  type: object
        """
        # Get the generated spec from Swagger
        spec = swagger.get_apispecs()

        return Response(
            json.dumps(spec, indent=2, default=str),
            mimetype="application/json",
            headers={
                "Content-Disposition": "attachment; filename=openapi.json",
                "Access-Control-Allow-Origin": "*",
                "Cache-Control": "public, max-age=3600",
            },
        )

    # Add route to export OpenAPI schema as YAML
    @app.route("/openapi.yaml", methods=["GET"])
    def export_openapi_yaml():
        """Export OpenAPI 3.1 schema as YAML.
        ---
        tags:
          - Documentation
        produces:
          - application/x-yaml
        responses:
          200:
            description: OpenAPI 3.1 specification in YAML format
        """
        try:
            import yaml

            spec = swagger.get_apispecs()
            yaml_content = yaml.dump(spec, default_flow_style=False, allow_unicode=True)
            return Response(
                yaml_content,
                mimetype="application/x-yaml",
                headers={
                    "Content-Disposition": "attachment; filename=openapi.yaml",
                    "Access-Control-Allow-Origin": "*",
                },
            )
        except ImportError:
            return {"error": "YAML export not available. Install PyYAML."}, 501

    # Add schema validation endpoint
    @app.route("/api/validate-schema", methods=["POST"])
    def validate_schema_endpoint():
        """Validate request data against an OpenAPI schema.
        ---
        tags:
          - Documentation
        consumes:
          - application/json
        parameters:
          - in: body
            name: body
            required: true
            schema:
              type: object
              required:
                - schema_name
                - data
              properties:
                schema_name:
                  type: string
                  description: Name of the schema to validate against
                  example: PredictionRequest
                data:
                  type: object
                  description: Data to validate
        responses:
          200:
            description: Validation result
            schema:
              type: object
              properties:
                valid:
                  type: boolean
                errors:
                  type: array
                  items:
                    type: string
        """
        req_data = request.get_json()
        raw_schema_name = req_data.get("schema_name")
        data = req_data.get("data", {})

        # Validate and sanitize schema_name to prevent XSS
        # Only allow alphanumeric characters and underscores for schema names
        if raw_schema_name:
            # Strip any potentially malicious content first
            safe_schema_name = str(raw_schema_name)[:100]
            # Only allow safe characters for schema lookup
            if not all(c.isalnum() or c in "_-" for c in safe_schema_name):
                return {"valid": False, "errors": ["Invalid schema name format"]}, 400
        else:
            return {"valid": False, "errors": ["Schema name is required"]}, 400

        schema = SWAGGER_TEMPLATE.get("components", {}).get("schemas", {}).get(safe_schema_name)
        if not schema:
            return {"valid": False, "errors": ["Schema not found"]}, 404

        errors = _validate_against_schema(data, schema)
        # Sanitize error messages to prevent XSS when reflecting validation results
        sanitized_errors = [html.escape(str(err)[:500]) for err in errors]
        # Return sanitized schema name in response
        return {"valid": len(errors) == 0, "errors": sanitized_errors, "schema_name": html.escape(safe_schema_name)}

    return swagger
