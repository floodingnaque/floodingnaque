"""Evacuation service — nearest-center finder and safe routing.

Provides Haversine distance calculation, nearest active evacuation
center lookup, and safe route generation via OSRM (with simulation
fallback).
"""

import logging
import math
import os
from typing import Any, Dict, List

import requests as http_requests
from app.models.community_report import CommunityReport
from app.models.db import get_db_session
from app.models.evacuation_center import EvacuationCenter

logger = logging.getLogger(__name__)

_R_EARTH_KM = 6371.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return great-circle distance in kilometres between two points."""
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2
    return _R_EARTH_KM * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def get_nearest_centers(lat: float, lon: float, limit: int = 3) -> List[Dict[str, Any]]:
    """Return the *limit* nearest active evacuation centers with available capacity.

    Each result includes:
      - center (serialized EvacuationCenter)
      - distance_km
      - available_slots / occupancy_pct
      - google_maps_url (walking directions deep-link)
    """
    with get_db_session() as session:
        centers = (
            session.query(EvacuationCenter)
            .filter(
                EvacuationCenter.is_active.is_(True),
                EvacuationCenter.is_deleted.is_(False),
            )
            .all()
        )

        # Filter out full centers and compute distances
        results: List[Dict[str, Any]] = []
        for c in centers:
            if c.capacity_current >= c.capacity_total:
                continue  # full — skip

            dist = haversine_km(lat, lon, c.latitude, c.longitude)
            google_url = (
                f"https://www.google.com/maps/dir/?api=1"
                f"&origin={lat},{lon}"
                f"&destination={c.latitude},{c.longitude}"
                f"&travelmode=walking"
            )
            results.append(
                {
                    "center": c.to_dict(),
                    "distance_km": round(dist, 2),
                    "available_slots": c.available_slots,
                    "occupancy_pct": c.occupancy_pct,
                    "google_maps_url": google_url,
                }
            )

        # Sort by distance ascending
        results.sort(key=lambda r: r["distance_km"])
        return results[:limit]


def get_safe_route(
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float,
    avoid_flooded: bool = True,
) -> Dict[str, Any]:
    """Fetch a walking route from OSRM, with simulation fallback.

    Args:
        origin_lat, origin_lon: Starting point.
        dest_lat, dest_lon: Destination point.
        avoid_flooded: If True, count nearby flood reports in the route
            bounding box (actual segment avoidance deferred to OSRM penalty
            weights in a future iteration).

    Returns:
        dict with ``geometry`` (GeoJSON), ``distance_m``, ``duration_s``,
        ``flood_segments_avoided``.
    """
    osrm_base = os.getenv("OSRM_BASE_URL", "http://router.project-osrm.org")
    flood_count = 0

    # Count flooded segments in the bounding box
    if avoid_flooded:
        flood_count = _count_flood_reports_in_bbox(
            origin_lat,
            origin_lon,
            dest_lat,
            dest_lon,
        )

    # ── Try OSRM ────────────────────────────────────────────────────────
    try:
        url = (
            f"{osrm_base}/route/v1/driving/"
            f"{origin_lon},{origin_lat};{dest_lon},{dest_lat}"
            f"?overview=full&geometries=geojson&steps=true"
        )
        resp = http_requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if data.get("code") == "Ok" and data.get("routes"):
            route = data["routes"][0]
            return {
                "geometry": route.get("geometry"),
                "distance_m": route.get("distance", 0),
                "duration_s": route.get("duration", 0),
                "flood_segments_avoided": flood_count,
            }
    except Exception as exc:
        logger.info("OSRM request failed (%s) — using simulation fallback", exc)

    # ── Simulation fallback: direct line ────────────────────────────────
    direct_km = haversine_km(origin_lat, origin_lon, dest_lat, dest_lon)
    walking_speed_kmh = 5.0
    duration_s = (direct_km / walking_speed_kmh) * 3600

    geometry = {
        "type": "LineString",
        "coordinates": [
            [origin_lon, origin_lat],
            [dest_lon, dest_lat],
        ],
    }

    return {
        "geometry": geometry,
        "distance_m": round(direct_km * 1000, 1),
        "duration_s": round(duration_s, 1),
        "flood_segments_avoided": flood_count,
    }


def _count_flood_reports_in_bbox(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> int:
    """Count recent non-rejected Alert/Critical reports within a bounding box."""
    from datetime import datetime, timedelta, timezone

    min_lat = min(lat1, lat2)
    max_lat = max(lat1, lat2)
    min_lon = min(lon1, lon2)
    max_lon = max(lon1, lon2)

    # Expand bbox slightly (≈200 m)
    padding = 0.002
    min_lat -= padding
    max_lat += padding
    min_lon -= padding
    max_lon += padding

    cutoff = datetime.now(timezone.utc) - timedelta(hours=6)

    try:
        with get_db_session() as session:
            count = (
                session.query(CommunityReport)
                .filter(
                    CommunityReport.is_deleted.is_(False),
                    CommunityReport.created_at >= cutoff,
                    CommunityReport.risk_label.in_(["Alert", "Critical"]),
                    CommunityReport.status != "rejected",
                    CommunityReport.latitude.between(min_lat, max_lat),
                    CommunityReport.longitude.between(min_lon, max_lon),
                )
                .count()
            )
            return count
    except Exception as exc:
        logger.warning("Flood report count query failed: %s", exc)
        return 0
