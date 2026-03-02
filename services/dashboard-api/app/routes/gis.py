"""
Dashboard API - GIS / Map Routes

Geographic Information System endpoints for flood risk map
visualisation in the frontend.
"""

import logging
from flask import Blueprint, current_app, jsonify, request

gis_bp = Blueprint("gis", __name__)
logger = logging.getLogger(__name__)


@gis_bp.route("/risk-zones", methods=["GET"])
def get_risk_zones():
    """
    GET /api/v1/dashboard/gis/risk-zones

    Return GeoJSON FeatureCollection of current flood risk zones
    in the Naque / Manila Bay region.
    """
    from app.services.dashboard_service import DashboardService

    try:
        service = DashboardService(current_app)
        geojson = service.get_risk_zones()
        return jsonify(geojson), 200
    except Exception as e:
        logger.error("Risk zones error: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 502


@gis_bp.route("/stations", methods=["GET"])
def get_weather_stations():
    """
    GET /api/v1/dashboard/gis/stations

    Return GeoJSON FeatureCollection of weather monitoring stations
    with their latest readings.
    """
    from app.services.dashboard_service import DashboardService

    try:
        service = DashboardService(current_app)
        stations = service.get_weather_stations_geojson()
        return jsonify(stations), 200
    except Exception as e:
        logger.error("Weather stations GIS error: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 502


@gis_bp.route("/flood-extent", methods=["GET"])
def get_flood_extent():
    """
    GET /api/v1/dashboard/gis/flood-extent?prediction_id=<id>

    Return the predicted flood extent polygon for a given prediction.
    """
    from app.services.dashboard_service import DashboardService

    prediction_id = request.args.get("prediction_id")
    if not prediction_id:
        return jsonify({
            "status": "error",
            "message": "prediction_id query parameter is required",
        }), 400

    try:
        service = DashboardService(current_app)
        extent = service.get_flood_extent(prediction_id)
        if extent is None:
            return jsonify({"status": "error", "message": "Flood extent not found"}), 404
        return jsonify(extent), 200
    except Exception as e:
        logger.error("Flood extent error: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 502


@gis_bp.route("/heatmap", methods=["GET"])
def get_risk_heatmap():
    """
    GET /api/v1/dashboard/gis/heatmap?resolution=medium

    Return risk intensity heatmap data as an array of
    [lat, lng, intensity] points.
    """
    from app.services.dashboard_service import DashboardService

    resolution = request.args.get("resolution", "medium")

    try:
        service = DashboardService(current_app)
        heatmap = service.get_risk_heatmap(resolution=resolution)
        return jsonify({"status": "success", "data": heatmap}), 200
    except Exception as e:
        logger.error("Risk heatmap error: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 502


@gis_bp.route("/drainage", methods=["GET"])
def get_drainage_network():
    """
    GET /api/v1/dashboard/gis/drainage

    Return GeoJSON of the drainage network (rivers, canals, catchments)
    relevant to flood modelling in Naque.
    """
    from app.services.dashboard_service import DashboardService

    try:
        service = DashboardService(current_app)
        drainage = service.get_drainage_network()
        return jsonify(drainage), 200
    except Exception as e:
        logger.error("Drainage network error: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 502
