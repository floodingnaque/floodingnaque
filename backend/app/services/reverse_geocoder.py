"""Reverse-geocoder service - barangay lookup from coordinates.

Maps a (lat, lon) pair to a Parañaque barangay name using the polygon
boundaries defined in :mod:`app.services.gis_service`.

Uses Shapely for robust point-in-polygon tests when available, with a
pure-Python winding-number fallback.
"""

import logging
from typing import Dict, List, Optional

from app.core.constants import is_within_study_area
from app.services.gis_service import BARANGAY_META, BARANGAY_POLYGONS

logger = logging.getLogger(__name__)

# ── Module-level cache for compiled polygons ─────────────────────────────
_shapely_polygons: Optional[Dict[str, object]] = None
_shapely_available: Optional[bool] = None


def _init_shapely_polygons() -> bool:
    """Compile BARANGAY_POLYGONS into Shapely Polygon objects (once).

    Returns True if Shapely is available and polygons were compiled.
    """
    global _shapely_polygons, _shapely_available

    if _shapely_available is not None:
        return _shapely_available

    try:
        from shapely.geometry import Polygon as ShapelyPolygon

        _shapely_polygons = {}
        for key, ring in BARANGAY_POLYGONS.items():
            if len(ring) >= 4:  # valid closed ring
                # BARANGAY_POLYGONS stores [lon, lat] pairs (GeoJSON order)
                _shapely_polygons[key] = ShapelyPolygon(ring)
        _shapely_available = True
        logger.debug("Shapely polygons compiled for %d barangays", len(_shapely_polygons))
        return True
    except ImportError:
        logger.warning("Shapely not installed - using pure-Python winding-number fallback")
        _shapely_available = False
        return False


def _winding_number(point_lon: float, point_lat: float, ring: List[List[float]]) -> bool:
    """Pure-Python winding-number point-in-polygon test.

    Args:
        point_lon: Test point longitude
        point_lat: Test point latitude
        ring: List of [lon, lat] coordinate pairs forming a closed ring

    Returns:
        True if the point is inside the polygon.
    """
    wn = 0
    n = len(ring) - 1  # last point == first point (closed ring)
    for i in range(n):
        x1, y1 = ring[i]
        x2, y2 = ring[i + 1]
        if y1 <= point_lat:
            if y2 > point_lat:
                # upward crossing
                cross = (x2 - x1) * (point_lat - y1) - (point_lon - x1) * (y2 - y1)
                if cross > 0:
                    wn += 1
        else:
            if y2 <= point_lat:
                # downward crossing
                cross = (x2 - x1) * (point_lat - y1) - (point_lon - x1) * (y2 - y1)
                if cross < 0:
                    wn -= 1
    return wn != 0


def reverse_geocode_barangay(lat: float, lon: float) -> Optional[str]:
    """Return the Parañaque barangay name for the given coordinates.

    Args:
        lat: WGS-84 latitude
        lon: WGS-84 longitude

    Returns:
        Human-readable barangay name (e.g. "BF Homes"), or None if the
        point is outside the study area / not matched to any barangay.
    """
    # Quick bounding-box pre-check
    if not is_within_study_area(lat, lon):
        return None

    use_shapely = _init_shapely_polygons()

    if use_shapely and _shapely_polygons:
        from shapely.geometry import Point

        pt = Point(lon, lat)  # Shapely uses (x, y) = (lon, lat)
        for key, poly in _shapely_polygons.items():
            if poly.contains(pt):  # type: ignore[attr-defined]
                meta = BARANGAY_META.get(key, {})
                return str(meta.get("name", key.replace("_", " ").title()))
        # No polygon match - fall through
        return None

    # Pure-Python fallback
    for key, ring in BARANGAY_POLYGONS.items():
        if len(ring) < 4:
            continue
        if _winding_number(lon, lat, ring):
            meta = BARANGAY_META.get(key, {})
            return str(meta.get("name", key.replace("_", " ").title()))

    return None
