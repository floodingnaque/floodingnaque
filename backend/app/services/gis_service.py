"""
GIS Service for Barangay-Level Flood Hazard Mapping.

Provides enhanced GIS capabilities incorporating:
- Barangay-level flood hazard mapping overlays
- Elevation data (SRTM-derived) for topographic analysis
- Drainage network data for flow accumulation modeling
- Flood susceptibility scoring per barangay

Data is served as GeoJSON for direct rendering in Leaflet/MapLibre.
"""

import logging
import math
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.core.constants import STUDY_AREA_BOUNDS

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Barangay GIS data - elevation, drainage, and hazard classifications
# ---------------------------------------------------------------------------

# Elevation data approximated from SRTM 30m DEM (NASA Shuttle Radar
# Topography Mission, 2000). Accessed via USGS EarthExplorer / OpenTopography.
# Resolution: ~30m, vertical accuracy ±16m (90% confidence).
# Values represent barangay centroid approximations - not survey-grade.

BARANGAY_ELEVATION: Dict[str, Dict[str, float]] = {
    "baclaran": {"mean_elevation_m": 3.2, "min_elevation_m": 1.0, "slope_pct": 0.3},
    "don_galo": {"mean_elevation_m": 2.8, "min_elevation_m": 0.8, "slope_pct": 0.2},
    "la_huerta": {"mean_elevation_m": 2.5, "min_elevation_m": 0.5, "slope_pct": 0.2},
    "san_dionisio": {"mean_elevation_m": 5.1, "min_elevation_m": 2.5, "slope_pct": 0.5},
    "tambo": {"mean_elevation_m": 2.0, "min_elevation_m": 0.3, "slope_pct": 0.1},
    "vitalez": {"mean_elevation_m": 3.8, "min_elevation_m": 1.5, "slope_pct": 0.3},
    "bf_homes": {"mean_elevation_m": 6.5, "min_elevation_m": 3.0, "slope_pct": 0.8},
    "don_bosco": {"mean_elevation_m": 7.2, "min_elevation_m": 4.0, "slope_pct": 0.9},
    "marcelo_green": {"mean_elevation_m": 5.5, "min_elevation_m": 2.8, "slope_pct": 0.6},
    "merville": {"mean_elevation_m": 8.0, "min_elevation_m": 5.0, "slope_pct": 1.0},
    "moonwalk": {"mean_elevation_m": 4.0, "min_elevation_m": 1.2, "slope_pct": 0.4},
    "san_antonio": {"mean_elevation_m": 5.8, "min_elevation_m": 3.0, "slope_pct": 0.6},
    "san_isidro": {"mean_elevation_m": 7.0, "min_elevation_m": 4.5, "slope_pct": 0.8},
    "san_martin": {"mean_elevation_m": 4.5, "min_elevation_m": 1.8, "slope_pct": 0.4},
    "santo_nino": {"mean_elevation_m": 6.0, "min_elevation_m": 3.5, "slope_pct": 0.7},
    "sucat": {"mean_elevation_m": 9.0, "min_elevation_m": 5.5, "slope_pct": 1.2},
}

# Drainage network proximity and flood history.
# Waterway names: NAMRIA topographic maps, verified against OpenStreetMap.
# Distances: estimated from barangay centroids to nearest mapped waterway.
# Drainage capacity: classified by urbanisation level + DRRMO flood frequency.
# flood_history_events: actual counts from DRRMO flood records 2022-2025
#   (295 total identifiable flood events across Parañaque; 135 records had
#    unresolved barangay attribution and are excluded from per-barangay tallies).
# Parañaque's main waterways: Parañaque River, Wawa River, La Huerta Creek.

BARANGAY_DRAINAGE: Dict[str, Dict[str, Any]] = {
    "baclaran": {
        "nearest_waterway": "Parañaque River",
        "distance_to_waterway_m": 350,
        "drainage_capacity": "poor",
        "flood_history_events": 7,
        "impervious_surface_pct": 85,
    },
    "don_galo": {
        "nearest_waterway": "Manila Bay Coast",
        "distance_to_waterway_m": 200,
        "drainage_capacity": "poor",
        "flood_history_events": 0,
        "impervious_surface_pct": 80,
    },
    "la_huerta": {
        "nearest_waterway": "La Huerta Creek",
        "distance_to_waterway_m": 150,
        "drainage_capacity": "poor",
        "flood_history_events": 2,
        "impervious_surface_pct": 75,
    },
    "san_dionisio": {
        "nearest_waterway": "Parañaque River",
        "distance_to_waterway_m": 500,
        "drainage_capacity": "moderate",
        "flood_history_events": 24,
        "impervious_surface_pct": 70,
    },
    "tambo": {
        "nearest_waterway": "Manila Bay Coast",
        "distance_to_waterway_m": 100,
        "drainage_capacity": "poor",
        "flood_history_events": 2,
        "impervious_surface_pct": 82,
    },
    "vitalez": {
        "nearest_waterway": "Wawa River",
        "distance_to_waterway_m": 400,
        "drainage_capacity": "moderate",
        "flood_history_events": 5,
        "impervious_surface_pct": 72,
    },
    "bf_homes": {
        "nearest_waterway": "BF Homes Canal",
        "distance_to_waterway_m": 300,
        "drainage_capacity": "moderate",
        "flood_history_events": 2,
        "impervious_surface_pct": 78,
    },
    "don_bosco": {
        "nearest_waterway": "Parañaque River",
        "distance_to_waterway_m": 600,
        "drainage_capacity": "good",
        "flood_history_events": 10,
        "impervious_surface_pct": 65,
    },
    "marcelo_green": {
        "nearest_waterway": "Parañaque River",
        "distance_to_waterway_m": 450,
        "drainage_capacity": "moderate",
        "flood_history_events": 11,
        "impervious_surface_pct": 68,
    },
    "merville": {
        "nearest_waterway": "Parañaque River",
        "distance_to_waterway_m": 800,
        "drainage_capacity": "good",
        "flood_history_events": 11,
        "impervious_surface_pct": 55,
    },
    "moonwalk": {
        "nearest_waterway": "BF Homes Canal",
        "distance_to_waterway_m": 250,
        "drainage_capacity": "poor",
        "flood_history_events": 11,
        "impervious_surface_pct": 80,
    },
    "san_antonio": {
        "nearest_waterway": "Parañaque River",
        "distance_to_waterway_m": 500,
        "drainage_capacity": "moderate",
        "flood_history_events": 25,
        "impervious_surface_pct": 70,
    },
    "san_isidro": {
        "nearest_waterway": "Parañaque River",
        "distance_to_waterway_m": 700,
        "drainage_capacity": "good",
        "flood_history_events": 20,
        "impervious_surface_pct": 60,
    },
    "san_martin": {
        "nearest_waterway": "Wawa River",
        "distance_to_waterway_m": 350,
        "drainage_capacity": "moderate",
        "flood_history_events": 3,
        "impervious_surface_pct": 74,
    },
    "santo_nino": {
        "nearest_waterway": "Parañaque River",
        "distance_to_waterway_m": 650,
        "drainage_capacity": "good",
        "flood_history_events": 11,
        "impervious_surface_pct": 58,
    },
    "sucat": {
        "nearest_waterway": "Sucat River",
        "distance_to_waterway_m": 400,
        "drainage_capacity": "moderate",
        "flood_history_events": 4,
        "impervious_surface_pct": 62,
    },
}

# Simplified polygon boundaries (GeoJSON-ready [lon, lat] rings)
BARANGAY_POLYGONS: Dict[str, List[List[float]]] = {
    "baclaran": [
        [121.0040, 14.5280],
        [120.9960, 14.5260],
        [120.9970, 14.5210],
        [121.0040, 14.5200],
        [121.0040, 14.5280],
    ],
    "don_galo": [
        [120.9960, 14.5160],
        [120.9870, 14.5150],
        [120.9880, 14.5090],
        [120.9960, 14.5080],
        [120.9960, 14.5160],
    ],
    "la_huerta": [
        [120.9930, 14.4940],
        [120.9810, 14.4930],
        [120.9820, 14.4850],
        [120.9930, 14.4840],
        [120.9930, 14.4940],
    ],
    "san_dionisio": [
        [121.0120, 14.5110],
        [121.0010, 14.5100],
        [121.0020, 14.5040],
        [121.0120, 14.5030],
        [121.0120, 14.5110],
    ],
    "tambo": [[120.9990, 14.5230], [120.9900, 14.5220], [120.9910, 14.5150], [120.9990, 14.5140], [120.9990, 14.5230]],
    "vitalez": [
        [120.9950, 14.4990],
        [120.9860, 14.4980],
        [120.9870, 14.4920],
        [120.9950, 14.4910],
        [120.9950, 14.4990],
    ],
    "bf_homes": [
        [121.0310, 14.4620],
        [121.0150, 14.4610],
        [121.0160, 14.4480],
        [121.0310, 14.4470],
        [121.0310, 14.4620],
    ],
    "don_bosco": [
        [121.0300, 14.4810],
        [121.0180, 14.4800],
        [121.0190, 14.4720],
        [121.0300, 14.4710],
        [121.0300, 14.4810],
    ],
    "marcelo_green": [
        [121.0150, 14.4860],
        [121.0050, 14.4850],
        [121.0060, 14.4790],
        [121.0150, 14.4780],
        [121.0150, 14.4860],
    ],
    "merville": [
        [121.0410, 14.4770],
        [121.0300, 14.4760],
        [121.0310, 14.4680],
        [121.0410, 14.4670],
        [121.0410, 14.4770],
    ],
    "moonwalk": [
        [121.0160, 14.4590],
        [121.0040, 14.4580],
        [121.0050, 14.4500],
        [121.0160, 14.4490],
        [121.0160, 14.4590],
    ],
    "san_antonio": [
        [121.0200, 14.4720],
        [121.0080, 14.4710],
        [121.0090, 14.4650],
        [121.0200, 14.4640],
        [121.0200, 14.4720],
    ],
    "san_isidro": [
        [121.0360, 14.4550],
        [121.0240, 14.4540],
        [121.0250, 14.4460],
        [121.0360, 14.4450],
        [121.0360, 14.4550],
    ],
    "san_martin": [
        [121.0060, 14.4660],
        [120.9940, 14.4650],
        [120.9950, 14.4570],
        [121.0060, 14.4560],
        [121.0060, 14.4660],
    ],
    "santo_nino": [
        [121.0230, 14.4500],
        [121.0110, 14.4490],
        [121.0120, 14.4410],
        [121.0230, 14.4400],
        [121.0230, 14.4500],
    ],
    "sucat": [[121.0510, 14.4680], [121.0390, 14.4670], [121.0400, 14.4580], [121.0510, 14.4570], [121.0510, 14.4680]],
}

# Barangay metadata (names, centroids)
BARANGAY_META: Dict[str, Dict[str, Any]] = {
    "baclaran": {"name": "Baclaran", "lat": 14.5240, "lon": 121.0010, "population": 36073},
    "don_galo": {"name": "Don Galo", "lat": 14.5120, "lon": 120.9920, "population": 16204},
    "la_huerta": {"name": "La Huerta", "lat": 14.4891, "lon": 120.9876, "population": 50905},
    "san_dionisio": {"name": "San Dionisio", "lat": 14.5070, "lon": 121.0070, "population": 32459},
    "tambo": {"name": "Tambo", "lat": 14.5180, "lon": 120.9950, "population": 30709},
    "vitalez": {"name": "Vitalez", "lat": 14.4950, "lon": 120.9910, "population": 19213},
    "bf_homes": {"name": "BF Homes", "lat": 14.4545, "lon": 121.0234, "population": 93023},
    "don_bosco": {"name": "Don Bosco", "lat": 14.4760, "lon": 121.0240, "population": 72218},
    "marcelo_green": {"name": "Marcelo Green Village", "lat": 14.4820, "lon": 121.0100, "population": 28497},
    "merville": {"name": "Merville", "lat": 14.4720, "lon": 121.0360, "population": 33580},
    "moonwalk": {"name": "Moonwalk", "lat": 14.4540, "lon": 121.0100, "population": 53413},
    "san_antonio": {"name": "San Antonio", "lat": 14.4680, "lon": 121.0140, "population": 38891},
    "san_isidro": {"name": "San Isidro", "lat": 14.4500, "lon": 121.0300, "population": 36542},
    "san_martin": {"name": "San Martin de Porres", "lat": 14.4610, "lon": 121.0000, "population": 40104},
    "santo_nino": {"name": "Santo Niño", "lat": 14.4450, "lon": 121.0170, "population": 33821},
    "sucat": {"name": "Sun Valley (Sucat)", "lat": 14.4625, "lon": 121.0456, "population": 50172},
}


def _compute_hazard_score(
    elevation: Dict[str, float],
    drainage: Dict[str, Any],
    current_rainfall_mm: float = 0.0,
) -> Dict[str, Any]:
    """
    Compute composite flood hazard score for a barangay.

    Scoring factors (0–1 scale, higher = more hazardous):
    1. Elevation factor  - lower elevation ⇒ higher risk
    2. Slope factor      - flatter terrain ⇒ more ponding
    3. Drainage factor   - poorer drainage ⇒ higher risk
    4. Proximity factor  - closer to waterway ⇒ higher risk
    5. Imperviousness    - more impervious surface ⇒ more runoff
    6. History factor    - more historical events ⇒ higher risk
    7. Rainfall factor   - current rainfall contribution (dynamic)

    Returns a composite score and hazard classification.
    """
    # 1. Elevation (min elevation is the flood-critical measure)
    min_elev = elevation.get("min_elevation_m", 5.0)
    # Normalize: 0m → 1.0, 10m → 0.0
    elev_score = max(0, 1.0 - min_elev / 10.0)

    # 2. Slope
    slope = elevation.get("slope_pct", 0.5)
    # Flatter ⇒ worse: 0% → 1.0, 2% → 0.0
    slope_score = max(0, 1.0 - slope / 2.0)

    # 3. Drainage capacity
    drain_map = {"poor": 1.0, "moderate": 0.5, "good": 0.2}
    drain_score = drain_map.get(drainage.get("drainage_capacity", "moderate"), 0.5)

    # 4. Proximity to waterway
    dist = drainage.get("distance_to_waterway_m", 500)
    # 0m → 1.0, 1000m → 0.0
    prox_score = max(0, 1.0 - dist / 1000.0)

    # 5. Impervious surface
    imperv = drainage.get("impervious_surface_pct", 60) / 100.0

    # 6. Historical flood frequency (normalized to max observed = 20)
    hist = min(drainage.get("flood_history_events", 0) / 20.0, 1.0)

    # 7. Current rainfall (dynamic, 0mm → 0, 50mm → 1.0)
    rain_score = min(current_rainfall_mm / 50.0, 1.0) if current_rainfall_mm > 0 else 0.0

    # Weighted composite - research-derived weights
    weights = {
        "elevation": 0.20,
        "slope": 0.10,
        "drainage": 0.20,
        "proximity": 0.15,
        "imperviousness": 0.10,
        "history": 0.15,
        "rainfall": 0.10,
    }

    composite = (
        weights["elevation"] * elev_score
        + weights["slope"] * slope_score
        + weights["drainage"] * drain_score
        + weights["proximity"] * prox_score
        + weights["imperviousness"] * imperv
        + weights["history"] * hist
        + weights["rainfall"] * rain_score
    )

    # Classify
    if composite >= 0.65:
        classification = "high"
        color = "#dc3545"
    elif composite >= 0.40:
        classification = "moderate"
        color = "#ffc107"
    else:
        classification = "low"
        color = "#28a745"

    return {
        "hazard_score": round(composite, 4),
        "classification": classification,
        "color": color,
        "factors": {
            "elevation": round(elev_score, 3),
            "slope": round(slope_score, 3),
            "drainage": round(drain_score, 3),
            "proximity": round(prox_score, 3),
            "imperviousness": round(imperv, 3),
            "history": round(hist, 3),
            "rainfall": round(rain_score, 3),
        },
    }


class GISService:
    """
    GIS service for barangay-level flood hazard mapping.

    Generates GeoJSON FeatureCollections for map overlays incorporating
    elevation, drainage, and real-time precipitation data.
    """

    def get_hazard_map(
        self,
        current_rainfall: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """
        Generate a GeoJSON FeatureCollection of all barangays with
        flood hazard scoring.

        Args:
            current_rainfall: Optional dict mapping barangay_key → rainfall_mm.
                If provided, hazard scores incorporate live rainfall.

        Returns:
            GeoJSON FeatureCollection with hazard properties per feature.
        """
        features: List[Dict[str, Any]] = []

        for key in BARANGAY_META:
            meta = BARANGAY_META[key]
            elev = BARANGAY_ELEVATION.get(key, {})
            drain = BARANGAY_DRAINAGE.get(key, {})
            polygon = BARANGAY_POLYGONS.get(key, [])

            rain_mm = 0.0
            if current_rainfall and key in current_rainfall:
                rain_mm = current_rainfall[key]

            hazard = _compute_hazard_score(elev, drain, rain_mm)

            # Confidence reflects how much live data backs the assessment.
            # Live rainfall → 0.9 (dynamic data available)
            # SmartAlertEvaluator recently evaluated → 0.85
            # Static-only data → 0.7 baseline
            confidence = 0.7
            if rain_mm > 0:
                confidence = 0.9
            else:
                try:
                    from app.services.smart_alert_evaluator import get_smart_evaluator

                    loc_state = get_smart_evaluator().get_location_state(key)
                    if loc_state and loc_state.get("last_evaluated_at"):
                        confidence = 0.85
                except Exception:
                    pass

            feature: Dict[str, Any] = {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [polygon],
                },
                "properties": {
                    "key": key,
                    "name": meta["name"],
                    "population": meta.get("population", 0),
                    "lat": meta["lat"],
                    "lon": meta["lon"],
                    # Elevation data
                    "mean_elevation_m": elev.get("mean_elevation_m", 0),
                    "min_elevation_m": elev.get("min_elevation_m", 0),
                    "slope_pct": elev.get("slope_pct", 0),
                    # Drainage data
                    "nearest_waterway": drain.get("nearest_waterway", ""),
                    "distance_to_waterway_m": drain.get("distance_to_waterway_m", 0),
                    "drainage_capacity": drain.get("drainage_capacity", "unknown"),
                    "impervious_surface_pct": drain.get("impervious_surface_pct", 0),
                    "flood_history_events": drain.get("flood_history_events", 0),
                    # Hazard assessment
                    "hazard_score": hazard["hazard_score"],
                    "hazard_classification": hazard["classification"],
                    "hazard_color": hazard["color"],
                    "hazard_factors": hazard["factors"],
                    # Confidence (0–1): higher when live data is available
                    "confidence": round(confidence, 2),
                    # Current rainfall (if available)
                    "current_rainfall_mm": round(rain_mm, 2),
                },
            }
            features.append(feature)

        return {
            "type": "FeatureCollection",
            "features": features,
            "metadata": {
                "city": "Parañaque City",
                "barangay_count": len(features),
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "crs": "EPSG:4326",
                "data_sources": [
                    "SRTM 30m DEM (elevation)",
                    "NAMRIA drainage network",
                    "PAGASA radar QPE (rainfall)",
                    "Parañaque DRRMO flood records",
                ],
            },
        }

    def get_elevation_overlay(self) -> Dict[str, Any]:
        """
        Generate GeoJSON with elevation-only styling (DEM overlay).

        Each polygon is classified into elevation bands with corresponding colors.
        """
        features: List[Dict[str, Any]] = []

        for key in BARANGAY_META:
            meta = BARANGAY_META[key]
            elev = BARANGAY_ELEVATION.get(key, {})
            polygon = BARANGAY_POLYGONS.get(key, [])

            mean_elev = elev.get("mean_elevation_m", 0)

            # Color based on elevation band (blue=low to brown=high)
            if mean_elev < 3:
                color = "#0571b0"  # Low-lying (< 3m)
                band = "0-3m"
            elif mean_elev < 5:
                color = "#92c5de"  # Low (3-5m)
                band = "3-5m"
            elif mean_elev < 7:
                color = "#f7f7f7"  # Mid (5-7m)
                band = "5-7m"
            elif mean_elev < 9:
                color = "#f4a582"  # Mid-high (7-9m)
                band = "7-9m"
            else:
                color = "#ca0020"  # High (> 9m)
                band = ">9m"

            features.append(
                {
                    "type": "Feature",
                    "geometry": {"type": "Polygon", "coordinates": [polygon]},
                    "properties": {
                        "key": key,
                        "name": meta["name"],
                        "mean_elevation_m": mean_elev,
                        "min_elevation_m": elev.get("min_elevation_m", 0),
                        "elevation_band": band,
                        "color": color,
                    },
                }
            )

        return {
            "type": "FeatureCollection",
            "features": features,
            "metadata": {
                "overlay_type": "elevation",
                "source": "SRTM 30m DEM",
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
        }

    def get_drainage_overlay(self) -> Dict[str, Any]:
        """
        Generate GeoJSON with drainage capacity styling.
        """
        features: List[Dict[str, Any]] = []

        for key in BARANGAY_META:
            meta = BARANGAY_META[key]
            drain = BARANGAY_DRAINAGE.get(key, {})
            polygon = BARANGAY_POLYGONS.get(key, [])

            capacity = drain.get("drainage_capacity", "unknown")
            color_map = {"poor": "#dc3545", "moderate": "#ffc107", "good": "#28a745", "unknown": "#6c757d"}

            features.append(
                {
                    "type": "Feature",
                    "geometry": {"type": "Polygon", "coordinates": [polygon]},
                    "properties": {
                        "key": key,
                        "name": meta["name"],
                        "drainage_capacity": capacity,
                        "nearest_waterway": drain.get("nearest_waterway", ""),
                        "distance_to_waterway_m": drain.get("distance_to_waterway_m", 0),
                        "impervious_surface_pct": drain.get("impervious_surface_pct", 0),
                        "color": color_map.get(capacity, "#6c757d"),
                    },
                }
            )

        return {
            "type": "FeatureCollection",
            "features": features,
            "metadata": {
                "overlay_type": "drainage",
                "source": "NAMRIA / Parañaque DRRMO",
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
        }

    def get_barangay_detail(self, barangay_key: str) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive GIS data for a single barangay.
        """
        if barangay_key not in BARANGAY_META:
            return None

        meta = BARANGAY_META[barangay_key]
        elev = BARANGAY_ELEVATION.get(barangay_key, {})
        drain = BARANGAY_DRAINAGE.get(barangay_key, {})
        polygon = BARANGAY_POLYGONS.get(barangay_key, [])
        hazard = _compute_hazard_score(elev, drain)

        return {
            "key": barangay_key,
            "name": meta["name"],
            "population": meta.get("population", 0),
            "center": {"lat": meta["lat"], "lon": meta["lon"]},
            "polygon": polygon,
            "elevation": elev,
            "drainage": drain,
            "hazard": hazard,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }


# Module-level singleton
_gis_service: Optional[GISService] = None


def get_gis_service() -> GISService:
    """Get the singleton GIS service instance."""
    global _gis_service
    if _gis_service is None:
        _gis_service = GISService()
    return _gis_service
