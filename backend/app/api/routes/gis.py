"""
GIS Routes for Barangay-Level Flood Hazard Mapping.

Provides GeoJSON endpoints for flood hazard overlays incorporating
elevation, drainage, and real-time precipitation data.
"""

import logging
from datetime import datetime, timezone

from app.api.middleware.rate_limit import limiter
from app.services.gis_service import get_gis_service
from app.utils.api_constants import HTTP_INTERNAL_ERROR, HTTP_NOT_FOUND, HTTP_OK
from app.utils.api_responses import api_error
from flask import Blueprint, g, jsonify, request

logger = logging.getLogger(__name__)

gis_bp = Blueprint("gis", __name__)


@gis_bp.route("/hazard-map", methods=["GET"])
@limiter.limit("60 per minute")
def get_hazard_map():
    """
    Get GeoJSON FeatureCollection of all barangays with flood hazard scores.

    The hazard score is a composite of elevation, drainage capacity,
    proximity to waterways, impervious surface area, and historical
    flood frequency. When PAGASA radar data is available, current
    rainfall is factored in as a dynamic component.

    Query Parameters:
        include_rainfall (bool): Incorporate live PAGASA radar rainfall
            into hazard scoring (default: true)

    Returns:
        200: GeoJSON FeatureCollection
    ---
    tags:
      - GIS
      - Flood Hazard
    parameters:
      - in: query
        name: include_rainfall
        schema:
          type: boolean
          default: true
        description: Include live radar rainfall in hazard scoring
    responses:
      200:
        description: GeoJSON FeatureCollection with hazard overlays
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        include_rainfall = request.args.get("include_rainfall", "true").lower() == "true"

        # Optionally fetch live rainfall from PAGASA radar
        current_rainfall = None
        if include_rainfall:
            try:
                from app.services.pagasa_radar_service import get_pagasa_radar_service

                radar = get_pagasa_radar_service()
                if radar.is_enabled():
                    city_data = radar.get_city_precipitation()
                    if city_data.get("status") == "ok":
                        barangays = city_data.get("barangays", {})
                        current_rainfall = {
                            k: v.get("rainfall_mm", 0) for k, v in barangays.items()
                        }
            except Exception as exc:
                logger.warning(f"Could not fetch radar rainfall for hazard map: {exc}")

        gis = get_gis_service()
        geojson = gis.get_hazard_map(current_rainfall=current_rainfall)

        return jsonify({
            "success": True,
            "data": geojson,
            "request_id": request_id,
        }), HTTP_OK

    except Exception as exc:
        logger.error(f"Error generating hazard map [{request_id}]: {exc}", exc_info=True)
        return api_error("InternalError", "Failed to generate hazard map", HTTP_INTERNAL_ERROR, request_id)


@gis_bp.route("/elevation", methods=["GET"])
@limiter.limit("60 per minute")
def get_elevation_overlay():
    """
    Get GeoJSON elevation overlay for all barangays.

    Polygons are classified into elevation bands (SRTM 30m DEM derived).

    Returns:
        200: GeoJSON FeatureCollection with elevation styling
    ---
    tags:
      - GIS
    responses:
      200:
        description: Elevation overlay GeoJSON
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        gis = get_gis_service()
        geojson = gis.get_elevation_overlay()

        return jsonify({
            "success": True,
            "data": geojson,
            "request_id": request_id,
        }), HTTP_OK

    except Exception as exc:
        logger.error(f"Error generating elevation overlay [{request_id}]: {exc}", exc_info=True)
        return api_error("InternalError", "Failed to generate elevation overlay", HTTP_INTERNAL_ERROR, request_id)


@gis_bp.route("/drainage", methods=["GET"])
@limiter.limit("60 per minute")
def get_drainage_overlay():
    """
    Get GeoJSON drainage capacity overlay for all barangays.

    Polygons are styled by drainage capacity (poor/moderate/good).

    Returns:
        200: GeoJSON FeatureCollection with drainage styling
    ---
    tags:
      - GIS
    responses:
      200:
        description: Drainage overlay GeoJSON
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        gis = get_gis_service()
        geojson = gis.get_drainage_overlay()

        return jsonify({
            "success": True,
            "data": geojson,
            "request_id": request_id,
        }), HTTP_OK

    except Exception as exc:
        logger.error(f"Error generating drainage overlay [{request_id}]: {exc}", exc_info=True)
        return api_error("InternalError", "Failed to generate drainage overlay", HTTP_INTERNAL_ERROR, request_id)


@gis_bp.route("/barangay/<barangay_key>", methods=["GET"])
@limiter.limit("120 per minute")
def get_barangay_detail(barangay_key: str):
    """
    Get comprehensive GIS data for a specific barangay.

    Includes elevation, drainage, hazard scoring, and polygon geometry.

    Args:
        barangay_key: Barangay identifier (e.g. 'bf_homes')

    Returns:
        200: Detailed barangay GIS data
        404: Barangay not found
    ---
    tags:
      - GIS
    parameters:
      - in: path
        name: barangay_key
        required: true
        schema:
          type: string
    responses:
      200:
        description: Barangay GIS detail
      404:
        description: Barangay not found
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        gis = get_gis_service()
        data = gis.get_barangay_detail(barangay_key)

        if data is None:
            return api_error(
                "NotFound",
                f"Barangay '{barangay_key}' not found",
                HTTP_NOT_FOUND,
                request_id,
            )

        return jsonify({
            "success": True,
            "data": data,
            "request_id": request_id,
        }), HTTP_OK

    except Exception as exc:
        logger.error(f"Error fetching barangay detail [{request_id}]: {exc}", exc_info=True)
        return api_error("InternalError", "Failed to fetch barangay detail", HTTP_INTERNAL_ERROR, request_id)
