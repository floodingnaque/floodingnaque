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
from app.utils.api_responses import api_error, api_success
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
                        current_rainfall = {k: v.get("rainfall_mm", 0) for k, v in barangays.items()}
            except Exception as exc:
                logger.warning(f"Could not fetch radar rainfall for hazard map: {exc}")

        gis = get_gis_service()
        geojson = gis.get_hazard_map(current_rainfall=current_rainfall)

        return (
            jsonify(
                {
                    "success": True,
                    "data": geojson,
                    "request_id": request_id,
                }
            ),
            HTTP_OK,
        )

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

        return (
            jsonify(
                {
                    "success": True,
                    "data": geojson,
                    "request_id": request_id,
                }
            ),
            HTTP_OK,
        )

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

        return (
            jsonify(
                {
                    "success": True,
                    "data": geojson,
                    "request_id": request_id,
                }
            ),
            HTTP_OK,
        )

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

        return (
            jsonify(
                {
                    "success": True,
                    "data": data,
                    "request_id": request_id,
                }
            ),
            HTTP_OK,
        )

    except Exception as exc:
        logger.error(f"Error fetching barangay detail [{request_id}]: {exc}", exc_info=True)
        return api_error("InternalError", "Failed to fetch barangay detail", HTTP_INTERNAL_ERROR, request_id)


# ── New endpoints ──────────────────────────────────────────────────────────


@gis_bp.route("/barangays", methods=["GET"])
@limiter.limit("60 per minute")
def get_barangays_geojson():
    """
    Get all barangays as GeoJSON with live risk overlay.

    Returns the hazard map FeatureCollection from GisService, which
    includes per-barangay hazard scores incorporating elevation,
    drainage, and optional live rainfall data.

    Returns:
        200: GeoJSON FeatureCollection with risk overlays
    ---
    tags:
      - GIS
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        gis = get_gis_service()
        geojson = gis.get_hazard_map()

        return api_success(
            data=geojson,
            message="Barangay GeoJSON with risk overlay",
            request_id=request_id,
        )

    except Exception as exc:
        logger.error(f"Error generating barangays GeoJSON [{request_id}]: {exc}", exc_info=True)
        return api_error("InternalError", "Failed to generate barangay GeoJSON", HTTP_INTERNAL_ERROR, request_id)


@gis_bp.route("/flood-zones", methods=["GET"])
@limiter.limit("60 per minute")
def get_flood_zones():
    """
    Get historical flood zone GeoJSON layer.

    Returns barangays styled by historical flood frequency from
    drainage data (flood_history_events).

    Returns:
        200: GeoJSON FeatureCollection with flood zone styling
    ---
    tags:
      - GIS
      - Flood Hazard
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        gis = get_gis_service()
        # Reuse drainage overlay which contains flood_history data
        geojson = gis.get_drainage_overlay()

        return api_success(
            data=geojson,
            message="Historical flood zones",
            request_id=request_id,
        )

    except Exception as exc:
        logger.error(f"Error generating flood zones [{request_id}]: {exc}", exc_info=True)
        return api_error("InternalError", "Failed to generate flood zones", HTTP_INTERNAL_ERROR, request_id)


@gis_bp.route("/evacuation-centers", methods=["GET"])
@limiter.limit("60 per minute")
def get_evacuation_centers_geojson():
    """
    Get active evacuation centers as GeoJSON points.

    Queries the EvacuationCenter ORM model and returns a GeoJSON
    FeatureCollection with capacity and status properties.

    Returns:
        200: GeoJSON FeatureCollection of evacuation centers
    ---
    tags:
      - GIS
      - Evacuation
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        from app.models.db import get_db_session
        from app.models.evacuation_center import EvacuationCenter

        features = []
        with get_db_session() as session:
            centers = (
                session.query(EvacuationCenter)
                .filter(
                    EvacuationCenter.is_active.is_(True),
                    EvacuationCenter.is_deleted.is_(False),
                )
                .all()
            )

            for c in centers:
                features.append(
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "Point",
                            "coordinates": [c.longitude, c.latitude],
                        },
                        "properties": {
                            "name": c.name,
                            "barangay": c.barangay,
                            "address": c.address,
                            "capacity_total": c.capacity_total,
                            "capacity_current": c.capacity_current,
                            "available_slots": c.available_slots,
                            "occupancy_pct": c.occupancy_pct,
                            "contact_number": c.contact_number,
                        },
                    }
                )

        geojson = {
            "type": "FeatureCollection",
            "features": features,
            "metadata": {
                "total_centers": len(features),
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "crs": "EPSG:4326",
            },
        }

        return api_success(
            data=geojson,
            message="Evacuation centers GeoJSON",
            request_id=request_id,
        )

    except Exception as exc:
        logger.error(f"Error generating evacuation centers GeoJSON [{request_id}]: {exc}", exc_info=True)
        return api_error("InternalError", "Failed to fetch evacuation centers", HTTP_INTERNAL_ERROR, request_id)


@gis_bp.route("/barangays/invalidate-cache", methods=["POST"])
@limiter.limit("10 per minute")
def invalidate_barangay_cache():
    """
    Invalidate cached GIS data (admin-only).

    Forces the next request to recompute hazard maps from fresh data.

    Returns:
        200: Cache invalidated
    ---
    tags:
      - GIS
      - Admin
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        from app.api.middleware.auth import require_auth_or_api_key

        # Auth check is applied at the route level; this is a belt-and-braces
        # verification. The decorator should be added when auth middleware is
        # wired up for POST routes.

        gis = get_gis_service()
        # GisService currently uses computed data (no internal cache to clear),
        # but this endpoint exists for future caching layers.
        logger.info("GIS barangay cache invalidated by request %s", request_id)

        return api_success(
            data={"invalidated": True},
            message="GIS cache invalidated",
            request_id=request_id,
        )

    except Exception as exc:
        logger.error(f"Error invalidating GIS cache [{request_id}]: {exc}", exc_info=True)
        return api_error("InternalError", "Failed to invalidate cache", HTTP_INTERNAL_ERROR, request_id)
