"""
Data Aggregation API Routes.

Provides endpoints for the unified multi-source data aggregation layer,
source health monitoring, and per-category data retrieval.
"""

import logging
from datetime import datetime, timezone

from app.api.middleware.rate_limit import limiter
from app.utils.api_constants import (
    HTTP_BAD_REQUEST,
    HTTP_INTERNAL_ERROR,
    HTTP_OK,
    HTTP_SERVICE_UNAVAILABLE,
)
from app.utils.api_responses import api_error, api_success
from flask import Blueprint, g, jsonify, request

logger = logging.getLogger(__name__)

aggregation_bp = Blueprint("aggregation", __name__)


def _get_request_id() -> str:
    return getattr(g, "request_id", "unknown")


def _get_aggregation_service():
    """Lazy-load the aggregation service."""
    from app.services.data_aggregation_service import get_aggregation_service

    return get_aggregation_service()


# ── Aggregated Data ─────────────────────────────────────────────────────────


@aggregation_bp.route("/all", methods=["GET"])
@limiter.limit("30 per minute")
def get_aggregated_data():
    """
    Get unified multi-source data with reliability scoring.

    Fetches data from all configured sources (PAGASA, MMDA, WorldTides,
    river monitoring) in parallel, applies fallback chains, and returns
    a single envelope with per-source confidence and global reliability.

    Returns:
        200: Aggregated data envelope
        503: Aggregation service disabled
    ---
    tags:
      - Data Aggregation
    responses:
      200:
        description: Unified multi-source data
    """
    request_id = _get_request_id()

    try:
        svc = _get_aggregation_service()
        if not svc.is_enabled():
            return api_error(
                "ServiceDisabled",
                "Data aggregation service is disabled",
                HTTP_SERVICE_UNAVAILABLE,
                request_id,
            )

        data = svc.get_aggregated_data()
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
        logger.error(f"Aggregation error [{request_id}]: {exc}", exc_info=True)
        return api_error("InternalError", "Failed to aggregate data", HTTP_INTERNAL_ERROR, request_id)


# ── Source Health ───────────────────────────────────────────────────────────


@aggregation_bp.route("/health", methods=["GET"])
@limiter.limit("60 per minute")
def get_source_health():
    """
    Check health/availability of all data sources.

    Useful for monitoring dashboards and alerting.

    Returns:
        200: Per-source health status
    ---
    tags:
      - Data Aggregation
      - Health
    responses:
      200:
        description: Source health check results
    """
    request_id = _get_request_id()

    try:
        svc = _get_aggregation_service()
        health = svc.get_source_health()
        return (
            jsonify(
                {
                    "success": True,
                    "data": health,
                    "request_id": request_id,
                }
            ),
            HTTP_OK,
        )

    except Exception as exc:
        logger.error(f"Health check error [{request_id}]: {exc}", exc_info=True)
        return api_error("InternalError", "Failed to check source health", HTTP_INTERNAL_ERROR, request_id)


# ── Per-Category Data ──────────────────────────────────────────────────────


@aggregation_bp.route("/category/<category>", methods=["GET"])
@limiter.limit("60 per minute")
def get_category_data(category: str):
    """
    Get data for a single category with its fallback chain.

    Path Parameters:
        category: rainfall | flood_advisory | tide | river | severe_weather

    Returns:
        200: Category data with source and confidence
        400: Invalid category
    ---
    tags:
      - Data Aggregation
    parameters:
      - in: path
        name: category
        required: true
        schema:
          type: string
          enum: [rainfall, flood_advisory, tide, river, severe_weather]
    responses:
      200:
        description: Category data
      400:
        description: Invalid category
    """
    request_id = _get_request_id()

    valid = {"rainfall", "flood_advisory", "tide", "river", "severe_weather"}
    if category not in valid:
        return api_error(
            "ValidationError",
            f"category must be one of: {sorted(valid)}",
            HTTP_BAD_REQUEST,
            request_id,
        )

    try:
        svc = _get_aggregation_service()
        data = svc.get_category_data(category)
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
        logger.error(f"Category [{category}] error [{request_id}]: {exc}", exc_info=True)
        return api_error("InternalError", f"Failed to fetch {category} data", HTTP_INTERNAL_ERROR, request_id)


# ── MMDA Flood ─────────────────────────────────────────────────────────────


@aggregation_bp.route("/mmda/advisories", methods=["GET"])
@limiter.limit("60 per minute")
def get_mmda_advisories():
    """
    Get MMDA flood advisories for Parañaque.

    Query Parameters:
        all: If 'true', return advisories for all of Metro Manila.

    Returns:
        200: MMDA flood advisories
    ---
    tags:
      - MMDA Flood
      - Data Aggregation
    """
    request_id = _get_request_id()

    try:
        from app.services.mmda_flood_service import get_mmda_flood_service

        svc = get_mmda_flood_service()

        paranaque_only = request.args.get("all", "false").lower() != "true"
        data = svc.get_active_advisories(paranaque_only=paranaque_only)

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
        logger.error(f"MMDA advisories error [{request_id}]: {exc}", exc_info=True)
        return api_error("InternalError", "Failed to fetch MMDA advisories", HTTP_INTERNAL_ERROR, request_id)


@aggregation_bp.route("/mmda/stations", methods=["GET"])
@limiter.limit("60 per minute")
def get_mmda_stations():
    """
    Get MMDA flood monitoring station readings for Parañaque.

    Returns:
        200: Station water-level readings
    ---
    tags:
      - MMDA Flood
      - Data Aggregation
    """
    request_id = _get_request_id()

    try:
        from app.services.mmda_flood_service import get_mmda_flood_service

        svc = get_mmda_flood_service()
        data = svc.get_station_readings()

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
        logger.error(f"MMDA stations error [{request_id}]: {exc}", exc_info=True)
        return api_error("InternalError", "Failed to fetch station readings", HTTP_INTERNAL_ERROR, request_id)


# ── Manila Bay Tide ────────────────────────────────────────────────────────


@aggregation_bp.route("/tide/manila-bay", methods=["GET"])
@limiter.limit("30 per minute")
def get_manila_bay_tide():
    """
    Get current Manila Bay tide height with influence analysis.

    Query Parameters:
        storm_surge: Additional storm surge in metres (default: 0)

    Returns:
        200: Tide height, phase, and flood influence data
    ---
    tags:
      - Tide
      - Data Aggregation
    """
    request_id = _get_request_id()

    try:
        from app.services.manila_bay_tide_service import get_manila_bay_tide_service

        svc = get_manila_bay_tide_service()

        data = svc.get_current_tide()

        storm_surge = request.args.get("storm_surge", default=0.0, type=float)
        if storm_surge > 0:
            influence = svc.get_tide_influence(storm_surge_m=storm_surge)
            data["influence"] = influence.get("influence")

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
        logger.error(f"Manila Bay tide error [{request_id}]: {exc}", exc_info=True)
        return api_error("InternalError", "Failed to fetch tide data", HTTP_INTERNAL_ERROR, request_id)


@aggregation_bp.route("/tide/forecast", methods=["GET"])
@limiter.limit("20 per minute")
def get_tide_forecast():
    """
    Get Manila Bay tide forecast.

    Query Parameters:
        hours: Forecast window in hours (default: 24, max: 72)

    Returns:
        200: Tide height series and extremes
    ---
    tags:
      - Tide
      - Data Aggregation
    """
    request_id = _get_request_id()

    try:
        from app.services.manila_bay_tide_service import get_manila_bay_tide_service

        svc = get_manila_bay_tide_service()

        hours = request.args.get("hours", default=24, type=int)
        hours = max(1, min(hours, 72))

        data = svc.get_tide_forecast(hours=hours)
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
        logger.error(f"Tide forecast error [{request_id}]: {exc}", exc_info=True)
        return api_error("InternalError", "Failed to fetch tide forecast", HTTP_INTERNAL_ERROR, request_id)


# ── River Water Levels ─────────────────────────────────────────────────────


@aggregation_bp.route("/river/readings", methods=["GET"])
@limiter.limit("60 per minute")
def get_river_readings():
    """
    Get current water-level readings for all Parañaque river stations.

    Returns:
        200: Station readings with alarm levels and flood risk score
    ---
    tags:
      - River Monitoring
      - Data Aggregation
    """
    request_id = _get_request_id()

    try:
        from app.services.river_water_level_service import get_river_water_level_service

        svc = get_river_water_level_service()
        data = svc.get_all_readings()

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
        logger.error(f"River readings error [{request_id}]: {exc}", exc_info=True)
        return api_error("InternalError", "Failed to fetch river readings", HTTP_INTERNAL_ERROR, request_id)


@aggregation_bp.route("/river/stations/<station_id>", methods=["GET"])
@limiter.limit("120 per minute")
def get_river_station(station_id: str):
    """
    Get reading for a specific river monitoring station.

    Path Parameters:
        station_id: Station identifier (e.g. 'paranaque_river_upstream')

    Returns:
        200: Station reading
        404: Station not found
    ---
    tags:
      - River Monitoring
      - Data Aggregation
    """
    request_id = _get_request_id()

    try:
        from app.services.river_water_level_service import get_river_water_level_service

        svc = get_river_water_level_service()
        data = svc.get_station_reading(station_id)

        if data.get("status") == "not_found":
            return api_error("NotFound", data.get("message", "Station not found"), 404, request_id)

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
        logger.error(f"River station error [{request_id}]: {exc}", exc_info=True)
        return api_error("InternalError", "Failed to fetch station data", HTTP_INTERNAL_ERROR, request_id)


@aggregation_bp.route("/river/system", methods=["GET"])
@limiter.limit("30 per minute")
def get_river_system():
    """
    Get aggregated status per river system.

    Returns:
        200: Per-river summaries (alarm, levels, risk)
    ---
    tags:
      - River Monitoring
      - Data Aggregation
    """
    request_id = _get_request_id()

    try:
        from app.services.river_water_level_service import get_river_water_level_service

        svc = get_river_water_level_service()
        data = svc.get_river_system_status()

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
        logger.error(f"River system error [{request_id}]: {exc}", exc_info=True)
        return api_error("InternalError", "Failed to fetch river system status", HTTP_INTERNAL_ERROR, request_id)


# ── PAGASA Bulletins ───────────────────────────────────────────────────────


@aggregation_bp.route("/pagasa/bulletins", methods=["GET"])
@limiter.limit("60 per minute")
def get_pagasa_bulletins():
    """
    Get PAGASA rainfall bulletins/advisories.

    Query Parameters:
        all: If 'true', return all advisories (not just Parañaque).

    Returns:
        200: Rainfall advisories
    ---
    tags:
      - PAGASA
      - Data Aggregation
    """
    request_id = _get_request_id()

    try:
        from app.services.pagasa_bulletin_service import get_pagasa_bulletin_service

        svc = get_pagasa_bulletin_service()

        paranaque_only = request.args.get("all", "false").lower() != "true"
        data = svc.get_active_advisories(paranaque_only=paranaque_only)

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
        logger.error(f"PAGASA bulletins error [{request_id}]: {exc}", exc_info=True)
        return api_error("InternalError", "Failed to fetch bulletins", HTTP_INTERNAL_ERROR, request_id)


@aggregation_bp.route("/pagasa/severe-weather", methods=["GET"])
@limiter.limit("60 per minute")
def get_severe_weather():
    """
    Get PAGASA severe weather bulletins (typhoon signals, etc.).

    Returns:
        200: Severe weather bulletins
    ---
    tags:
      - PAGASA
      - Data Aggregation
    """
    request_id = _get_request_id()

    try:
        from app.services.pagasa_bulletin_service import get_pagasa_bulletin_service

        svc = get_pagasa_bulletin_service()
        data = svc.get_combined_status()

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
        logger.error(f"Severe weather error [{request_id}]: {exc}", exc_info=True)
        return api_error("InternalError", "Failed to fetch severe weather data", HTTP_INTERNAL_ERROR, request_id)


# ── Reliability Info ───────────────────────────────────────────────────────


@aggregation_bp.route("/reliability", methods=["GET"])
@limiter.limit("60 per minute")
def get_reliability_info():
    """
    Get data reliability scoring breakdown.

    Returns the global reliability score, per-source confidence,
    and consistency analysis.

    Returns:
        200: Reliability scoring details
    ---
    tags:
      - Data Aggregation
      - Monitoring
    """
    request_id = _get_request_id()

    try:
        svc = _get_aggregation_service()
        data = svc.get_aggregated_data()

        reliability = {
            "global_reliability_score": data.get("reliability_score", 0),
            "sources_available": data.get("sources_available", 0),
            "sources_failed": data.get("sources_failed", 0),
            "warnings": data.get("warnings", []),
            "per_source": {},
        }

        for cat, source_data in data.get("sources", {}).items():
            reliability["per_source"][cat] = {
                "source": source_data.get("source_name"),
                "quality": source_data.get("quality"),
                "confidence": source_data.get("confidence"),
                "latency_ms": source_data.get("latency_ms"),
                "is_fallback": source_data.get("is_fallback"),
            }

        # Include per-source EMA reliability tracking
        from app.services.data_aggregation_service import reliability_snapshot

        ema_snapshot = reliability_snapshot()
        reliability["ema_tracking"] = ema_snapshot

        return (
            jsonify(
                {
                    "success": True,
                    "data": reliability,
                    "request_id": request_id,
                }
            ),
            HTTP_OK,
        )

    except Exception as exc:
        logger.error(f"Reliability info error [{request_id}]: {exc}", exc_info=True)
        return api_error("InternalError", "Failed to compute reliability", HTTP_INTERNAL_ERROR, request_id)
