"""
PAGASA Radar Routes.

API endpoints for accessing radar-based precipitation estimates
from PAGASA for Parañaque City barangays.
"""

import logging
from datetime import datetime, timezone

from app.api.middleware.rate_limit import limiter
from app.services.pagasa_radar_service import get_pagasa_radar_service
from app.utils.api_constants import HTTP_BAD_REQUEST, HTTP_INTERNAL_ERROR, HTTP_NOT_FOUND, HTTP_OK
from app.utils.api_responses import api_error
from flask import Blueprint, g, jsonify, request

logger = logging.getLogger(__name__)

pagasa_bp = Blueprint("pagasa", __name__)


@pagasa_bp.route("/precipitation", methods=["GET"])
@limiter.limit("60 per minute")
def get_city_precipitation():
    """
    Get radar-based precipitation estimates for all barangays in Parañaque City.

    Returns per-barangay rainfall data calibrated against PAGASA AWS observations.

    Returns:
        200: City-wide precipitation summary with per-barangay breakdown
    ---
    tags:
      - PAGASA Radar
      - Weather
    responses:
      200:
        description: Precipitation estimates for all barangays
        content:
          application/json:
            schema:
              type: object
              properties:
                success:
                  type: boolean
                data:
                  type: object
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        service = get_pagasa_radar_service()
        data = service.get_city_precipitation()

        return {
            "success": True,
            "data": data,
            "request_id": request_id,
        }, HTTP_OK

    except Exception as exc:
        logger.error(f"Error fetching PAGASA precipitation [{request_id}]: {exc}", exc_info=True)
        return api_error("InternalError", "Failed to fetch precipitation data", HTTP_INTERNAL_ERROR, request_id)


@pagasa_bp.route("/precipitation/<barangay_key>", methods=["GET"])
@limiter.limit("120 per minute")
def get_barangay_precipitation(barangay_key: str):
    """
    Get radar precipitation estimate for a specific barangay.

    Args:
        barangay_key: Barangay identifier (e.g. 'bf_homes', 'la_huerta')

    Returns:
        200: Precipitation data for the specified barangay
        404: Barangay not found
    ---
    tags:
      - PAGASA Radar
      - Weather
    parameters:
      - in: path
        name: barangay_key
        required: true
        schema:
          type: string
        description: Barangay identifier
        examples:
          bf_homes:
            value: bf_homes
          la_huerta:
            value: la_huerta
    responses:
      200:
        description: Barangay precipitation data
      404:
        description: Barangay not found
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        service = get_pagasa_radar_service()
        data = service.get_barangay_precipitation(barangay_key)

        if data is None:
            return api_error(
                "NotFound",
                f"Barangay '{barangay_key}' not found. Use list endpoint for valid keys.",
                HTTP_NOT_FOUND,
                request_id,
            )

        return {
            "success": True,
            "data": data,
            "request_id": request_id,
        }, HTTP_OK

    except Exception as exc:
        logger.error(f"Error fetching barangay precipitation [{request_id}]: {exc}", exc_info=True)
        return api_error("InternalError", "Failed to fetch barangay precipitation", HTTP_INTERNAL_ERROR, request_id)


@pagasa_bp.route("/advisory", methods=["GET"])
@limiter.limit("30 per minute")
def get_rainfall_advisory():
    """
    Get the latest PAGASA rainfall advisory for Metro Manila / NCR.

    Returns:
        200: Current rainfall advisory
    ---
    tags:
      - PAGASA Radar
      - Weather
    responses:
      200:
        description: Rainfall advisory data
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        service = get_pagasa_radar_service()
        data = service.get_rainfall_advisory()

        return {
            "success": True,
            "data": data,
            "request_id": request_id,
        }, HTTP_OK

    except Exception as exc:
        logger.error(f"Error fetching rainfall advisory [{request_id}]: {exc}", exc_info=True)
        return api_error("InternalError", "Failed to fetch rainfall advisory", HTTP_INTERNAL_ERROR, request_id)


@pagasa_bp.route("/barangays", methods=["GET"])
@limiter.limit("120 per minute")
def list_barangays():
    """
    List all supported barangays with their coordinates.

    Returns:
        200: List of barangay keys and coordinates
    ---
    tags:
      - PAGASA Radar
    responses:
      200:
        description: List of barangays
    """
    request_id = getattr(g, "request_id", "unknown")

    from app.services.pagasa_radar_service import PARANAQUE_BARANGAYS

    barangays = [
        {"key": k, "name": v["name"], "lat": v["lat"], "lon": v["lon"]}
        for k, v in PARANAQUE_BARANGAYS.items()
    ]

    return {
        "success": True,
        "barangays": barangays,
        "count": len(barangays),
        "request_id": request_id,
    }, HTTP_OK


@pagasa_bp.route("/status", methods=["GET"])
@limiter.limit("60 per minute")
def pagasa_status():
    """
    Check PAGASA radar service status.

    Returns:
        200: Service status
    ---
    tags:
      - PAGASA Radar
      - Health
    responses:
      200:
        description: PAGASA service status
    """
    request_id = getattr(g, "request_id", "unknown")

    service = get_pagasa_radar_service()
    return {
        "success": True,
        "enabled": service.is_enabled(),
        "service": "pagasa_radar",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "request_id": request_id,
    }, HTTP_OK
