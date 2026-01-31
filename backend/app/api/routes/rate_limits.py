"""
Rate Limiting Information Routes.

Provides endpoints for checking rate limiting status and configuration.
"""

import html

from app.utils.api_constants import HTTP_BAD_REQUEST, HTTP_OK
from app.utils.api_responses import api_error, api_success
from app.utils.logging import get_logger
from app.utils.rate_limit import get_current_rate_limit_info, get_endpoint_limit, limiter
from app.utils.rate_limit_tiers import check_rate_limit_status, get_api_key_tier
from flask import Blueprint, g, request

logger = get_logger(__name__)

rate_limits_bp = Blueprint("rate_limits", __name__)


@rate_limits_bp.route("/status", methods=["GET"])
@limiter.exempt  # Don't rate limit rate limit status endpoint
def rate_limit_status():
    """
    Get current rate limiting status for the requesting client.

    Returns:
        Rate limiting information including current tier and limits
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        # Get API key hash if authenticated
        api_key_hash = getattr(g, "api_key_hash", None)

        # Get rate limit status
        status_info = check_rate_limit_status(api_key_hash)

        # Add current request context info
        current_info = get_current_rate_limit_info()

        response = {
            "current_request": {
                "authenticated": current_info["authenticated"],
                "key_type": current_info["key_type"],
                "storage": current_info["storage"],
                "enabled": current_info["enabled"],
            },
            "rate_limiting": status_info,
            "headers_info": {
                "description": "Rate limit headers are included in API responses",
                "headers": {
                    "X-RateLimit-Limit": "Rate limit for the current window",
                    "X-RateLimit-Remaining": "Remaining requests in current window",
                    "X-RateLimit-Reset": "Time when the rate limit window resets (Unix timestamp)",
                },
            },
        }

        return api_success(
            data=response,
            message="Rate limiting status retrieved successfully",
            status_code=HTTP_OK,
            request_id=request_id,
        )

    except Exception as e:
        logger.error(f"Failed to get rate limit status [{request_id}]: {str(e)}")
        return api_error("RateLimitStatusFailed", "Failed to get rate limit status", HTTP_BAD_REQUEST, request_id)


@rate_limits_bp.route("/tiers", methods=["GET"])
@limiter.limit("60/minute")  # Moderate rate limit for tier information
def list_rate_limit_tiers():
    """
    List available rate limiting tiers.

    Query Parameters:
        detailed (bool): Include detailed tier information (default: false)

    Returns:
        List of available rate limiting tiers
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        detailed = request.args.get("detailed", "false").lower() == "true"

        from app.utils.rate_limit_tiers import RATE_LIMIT_TIERS

        tiers = {}
        for tier_name, tier_config in RATE_LIMIT_TIERS.items():
            if detailed:
                tiers[tier_name] = {
                    "name": tier_config.name,
                    "limits": {
                        "per_minute": tier_config.requests_per_minute,
                        "per_hour": tier_config.requests_per_hour,
                        "per_day": tier_config.requests_per_day,
                        "burst_capacity": tier_config.burst_capacity,
                    },
                }
            else:
                tiers[tier_name] = {"name": tier_config.name, "requests_per_minute": tier_config.requests_per_minute}

        return api_success(
            data={
                "tiers": tiers,
                "current_user_tier": (
                    get_api_key_tier(getattr(g, "api_key_hash", None))
                    if getattr(g, "api_key_hash", None)
                    else "anonymous"
                ),
                "detailed": detailed,
            },
            message="Rate limiting tiers retrieved successfully",
            status_code=HTTP_OK,
            request_id=request_id,
        )

    except Exception as e:
        logger.error(f"Failed to list rate limit tiers [{request_id}]: {str(e)}")
        return api_error("TierListFailed", "Failed to list rate limit tiers", HTTP_BAD_REQUEST, request_id)


@rate_limits_bp.route("/endpoint-info", methods=["GET"])
@limiter.limit("60/minute")
def endpoint_rate_limit_info():
    """
    Get rate limit information for specific endpoints.

    Query Parameters:
        endpoint (str, optional): Specific endpoint to check

    Returns:
        Rate limit information for endpoints
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        endpoint = request.args.get("endpoint")

        # Common endpoints to show
        common_endpoints = ["predict", "ingest", "data", "status", "docs"]

        if endpoint:
            # Sanitize endpoint to prevent XSS
            endpoint = html.escape(str(endpoint)[:100])
            # Get info for specific endpoint
            if endpoint not in common_endpoints:
                return api_error(
                    "InvalidEndpoint", "Unknown or invalid endpoint specified", HTTP_BAD_REQUEST, request_id
                )

            limit_string = get_endpoint_limit(endpoint, as_callable=False)

            endpoint_info = {
                "endpoint": endpoint,
                "rate_limit": limit_string,
                "description": _get_endpoint_description(endpoint),
            }
        else:
            # Get info for all common endpoints
            endpoint_info = {}
            for ep in common_endpoints:
                limit_string = get_endpoint_limit(ep, as_callable=False)
                endpoint_info[ep] = {"rate_limit": limit_string, "description": _get_endpoint_description(ep)}

        return api_success(
            data={
                "endpoint_info": endpoint_info,
                "note": "Rate limits vary based on API key tier and authentication status",
            },
            message="Endpoint rate limit information retrieved successfully",
            status_code=HTTP_OK,
            request_id=request_id,
        )

    except Exception as e:
        logger.error(f"Failed to get endpoint rate limit info [{request_id}]: {str(e)}")
        return api_error("EndpointInfoFailed", "Failed to get endpoint rate limit info", HTTP_BAD_REQUEST, request_id)


@rate_limits_bp.route("/test", methods=["GET"])
@limiter.limit("10/minute")
def rate_limit_test():
    """
    Test endpoint to demonstrate rate limiting in action.

    Returns:
        Test response with rate limit headers
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        # This endpoint is rate limited to demonstrate the functionality
        return api_success(
            data={
                "message": "This endpoint is rate limited to demonstrate rate limiting",
                "current_time": (
                    logger.handlers[0].formatter.formatTime(logger.makeRecord("test", 20, "", 0, "", (), None))
                    if logger.handlers
                    else None
                ),
                "request_id": request_id,
                "note": "Check the response headers for X-RateLimit-* information",
            },
            message="Rate limiting test endpoint",
            status_code=HTTP_OK,
            request_id=request_id,
        )

    except Exception as e:
        logger.error(f"Rate limit test failed [{request_id}]: {str(e)}")
        return api_error("RateLimitTestFailed", "Rate limit test failed", HTTP_BAD_REQUEST, request_id)


def _get_endpoint_description(endpoint_name):
    """Get description for an endpoint."""
    descriptions = {
        "predict": "Flood prediction API - ML model inference",
        "ingest": "Data ingestion from external weather APIs",
        "data": "Historical weather and prediction data retrieval",
        "status": "Health check and system status endpoints",
        "docs": "API documentation and Swagger UI",
    }
    return descriptions.get(endpoint_name, "API endpoint")
