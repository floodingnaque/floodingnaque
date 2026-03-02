"""
Spatial Feature Engineering for Barangay-Level Flood Depth Prediction.

Integrates geospatial attributes — drainage capacity, elevation profiles,
land-use classification, and impervious surface estimates — into ML feature
vectors, enabling the model to produce barangay-specific flood depth
predictions rather than city-wide binary flood/no-flood classifications.

Data Sources
------------
- SRTM 30 m DEM (elevation, slope) — via ``gis_service.py`` lookup tables
- Parañaque CLUP (Comprehensive Land-Use Plan) — simplified classification
- DRRMO flood-history events per barangay
- Drainage capacity assessments (Parañaque Engineering Office)

Usage
-----
::

    from app.services.spatial_features import (
        add_spatial_features,
        SPATIAL_FEATURE_NAMES,
    )

    # Add to training DataFrame
    df = add_spatial_features(df, barangay_col="barangay")

    # Get features for single-row inference
    features = get_spatial_features_for_barangay("tambo")

Author: Floodingnaque Team
Date: 2026-03-02
"""

import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ═════════════════════════════════════════════════════════════════════════════
# Land-Use Classification
# ═════════════════════════════════════════════════════════════════════════════

# Simplified CLUP-based land-use classification for Parañaque barangays.
# Categories: residential, commercial, mixed, industrial, institutional, open_space
# Values represent dominant land-use type and a runoff coefficient (0–1)
# that estimates the fraction of rainfall becoming surface runoff.

BARANGAY_LAND_USE: Dict[str, Dict[str, Any]] = {
    "baclaran": {
        "dominant_use": "commercial",
        "runoff_coefficient": 0.85,
        "green_cover_pct": 5,
        "building_density": "very_high",
    },
    "don_galo": {
        "dominant_use": "mixed",
        "runoff_coefficient": 0.78,
        "green_cover_pct": 10,
        "building_density": "high",
    },
    "la_huerta": {
        "dominant_use": "mixed",
        "runoff_coefficient": 0.75,
        "green_cover_pct": 12,
        "building_density": "high",
    },
    "san_dionisio": {
        "dominant_use": "residential",
        "runoff_coefficient": 0.70,
        "green_cover_pct": 15,
        "building_density": "high",
    },
    "tambo": {
        "dominant_use": "commercial",
        "runoff_coefficient": 0.82,
        "green_cover_pct": 6,
        "building_density": "very_high",
    },
    "vitalez": {
        "dominant_use": "residential",
        "runoff_coefficient": 0.72,
        "green_cover_pct": 14,
        "building_density": "high",
    },
    "bf_homes": {
        "dominant_use": "residential",
        "runoff_coefficient": 0.65,
        "green_cover_pct": 22,
        "building_density": "medium",
    },
    "don_bosco": {
        "dominant_use": "residential",
        "runoff_coefficient": 0.60,
        "green_cover_pct": 25,
        "building_density": "medium",
    },
    "marcelo_green": {
        "dominant_use": "residential",
        "runoff_coefficient": 0.68,
        "green_cover_pct": 18,
        "building_density": "medium",
    },
    "merville": {
        "dominant_use": "residential",
        "runoff_coefficient": 0.55,
        "green_cover_pct": 30,
        "building_density": "low",
    },
    "moonwalk": {
        "dominant_use": "residential",
        "runoff_coefficient": 0.72,
        "green_cover_pct": 12,
        "building_density": "high",
    },
    "san_antonio": {
        "dominant_use": "residential",
        "runoff_coefficient": 0.65,
        "green_cover_pct": 20,
        "building_density": "medium",
    },
    "san_isidro": {
        "dominant_use": "residential",
        "runoff_coefficient": 0.58,
        "green_cover_pct": 28,
        "building_density": "low",
    },
    "san_martin": {
        "dominant_use": "mixed",
        "runoff_coefficient": 0.70,
        "green_cover_pct": 15,
        "building_density": "high",
    },
    "santo_nino": {
        "dominant_use": "residential",
        "runoff_coefficient": 0.60,
        "green_cover_pct": 24,
        "building_density": "medium",
    },
    "sucat": {
        "dominant_use": "mixed",
        "runoff_coefficient": 0.62,
        "green_cover_pct": 22,
        "building_density": "medium",
    },
}

# ── Land-use type numeric encoding ──────────────────────────────────────────
LAND_USE_ENCODING: Dict[str, int] = {
    "commercial": 4,
    "industrial": 3,
    "mixed": 2,
    "residential": 1,
    "institutional": 1,
    "open_space": 0,
}

BUILDING_DENSITY_ENCODING: Dict[str, int] = {
    "very_high": 4,
    "high": 3,
    "medium": 2,
    "low": 1,
    "very_low": 0,
}


# ═════════════════════════════════════════════════════════════════════════════
# Composite Spatial Features
# ═════════════════════════════════════════════════════════════════════════════

def _get_gis_data():
    """Lazily import GIS data dictionaries from gis_service."""
    from app.services.gis_service import (
        BARANGAY_DRAINAGE,
        BARANGAY_ELEVATION,
        BARANGAY_META,
    )
    return BARANGAY_ELEVATION, BARANGAY_DRAINAGE, BARANGAY_META


def get_spatial_features_for_barangay(barangay: str) -> Dict[str, float]:
    """
    Compute all spatial features for a single barangay.

    Returns a flat dict of numeric features suitable for ML model input.

    Parameters
    ----------
    barangay : str
        Barangay key (lowercase with underscores, e.g. "bf_homes").

    Returns
    -------
    dict mapping feature name → numeric value
    """
    BARANGAY_ELEVATION, BARANGAY_DRAINAGE, BARANGAY_META = _get_gis_data()

    elev = BARANGAY_ELEVATION.get(barangay, {})
    drain = BARANGAY_DRAINAGE.get(barangay, {})
    land = BARANGAY_LAND_USE.get(barangay, {})
    meta = BARANGAY_META.get(barangay, {})

    # ── Elevation features ──────────────────────────────────────────────────
    mean_elev = elev.get("mean_elevation_m", 5.0)
    min_elev = elev.get("min_elevation_m", 2.0)
    slope = elev.get("slope_pct", 0.5)

    # Normalised elevation vulnerability (0–1, lower elevation = higher risk)
    elev_vulnerability = max(0.0, 1.0 - min_elev / 10.0)

    # ── Drainage features ───────────────────────────────────────────────────
    drain_cap_map = {"poor": 0.2, "moderate": 0.5, "good": 0.8}
    drainage_score = drain_cap_map.get(drain.get("drainage_capacity", "moderate"), 0.5)
    waterway_dist = drain.get("distance_to_waterway_m", 500)
    waterway_proximity = max(0.0, 1.0 - waterway_dist / 1000.0)
    impervious_pct = drain.get("impervious_surface_pct", 65) / 100.0
    flood_history = drain.get("flood_history_events", 5)

    # ── Land-use features ───────────────────────────────────────────────────
    runoff_coeff = land.get("runoff_coefficient", 0.70)
    green_cover = land.get("green_cover_pct", 15) / 100.0
    land_use_type = LAND_USE_ENCODING.get(land.get("dominant_use", "residential"), 1)
    density = BUILDING_DENSITY_ENCODING.get(land.get("building_density", "medium"), 2)

    # ── Composite indices ───────────────────────────────────────────────────
    # Flood susceptibility index (0–1): higher = more flood-prone
    flood_susceptibility = (
        0.25 * elev_vulnerability
        + 0.20 * (1 - drainage_score)
        + 0.15 * waterway_proximity
        + 0.15 * impervious_pct
        + 0.15 * runoff_coeff
        + 0.10 * min(flood_history / 20.0, 1.0)
    )

    # Absorption capacity: ability of land to absorb rainfall
    absorption_capacity = green_cover * (1 - impervious_pct) * drainage_score

    features = {
        # Raw elevation
        "mean_elevation_m": mean_elev,
        "min_elevation_m": min_elev,
        "slope_pct": slope,
        "elev_vulnerability": elev_vulnerability,
        # Drainage
        "drainage_score": drainage_score,
        "waterway_distance_m": waterway_dist,
        "waterway_proximity": waterway_proximity,
        "impervious_surface_pct": impervious_pct * 100,
        "flood_history_events": flood_history,
        # Land use
        "runoff_coefficient": runoff_coeff,
        "green_cover_pct": green_cover * 100,
        "land_use_encoded": land_use_type,
        "building_density_encoded": density,
        # Composite
        "flood_susceptibility_index": round(flood_susceptibility, 4),
        "absorption_capacity": round(absorption_capacity, 4),
    }

    return features


def get_all_barangay_features() -> pd.DataFrame:
    """
    Compute spatial features for all Parañaque barangays.

    Returns a DataFrame indexed by barangay key with all spatial features.
    """
    BARANGAY_ELEVATION, _, _ = _get_gis_data()

    all_features = {}
    for brgy in BARANGAY_ELEVATION:
        all_features[brgy] = get_spatial_features_for_barangay(brgy)

    df = pd.DataFrame.from_dict(all_features, orient="index")
    df.index.name = "barangay"
    return df


def add_spatial_features(
    df: pd.DataFrame,
    barangay_col: str = "barangay",
    default_barangay: Optional[str] = None,
) -> pd.DataFrame:
    """
    Merge spatial features into a training or inference DataFrame.

    Each row is enriched with elevation, drainage, and land-use features
    based on its barangay value.

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame.
    barangay_col : str
        Column containing barangay identifiers.
    default_barangay : str, optional
        If rows have no barangay value, use this default.

    Returns
    -------
    pd.DataFrame with spatial feature columns appended.
    """
    df = df.copy()

    if barangay_col not in df.columns:
        if default_barangay:
            df[barangay_col] = default_barangay
        else:
            logger.warning(
                f"Column '{barangay_col}' not found and no default. "
                "Using city-wide averages."
            )
            # Use city-wide average spatial features
            avg_features = get_all_barangay_features().mean()
            for col, val in avg_features.items():
                df[col] = val
            return df

    # Normalise barangay names
    df[barangay_col] = (
        df[barangay_col]
        .astype(str)
        .str.lower()
        .str.strip()
        .str.replace(r"\s+", "_", regex=True)
        .str.replace(r"[^a-z_]", "", regex=True)
    )

    # Build lookup
    spatial_df = get_all_barangay_features().reset_index()
    df = df.merge(spatial_df, left_on=barangay_col, right_on="barangay", how="left")

    # Fill missing (unknown barangays) with city-wide average
    avg = spatial_df.drop(columns=["barangay"]).mean()
    for col in SPATIAL_FEATURE_NAMES:
        if col in df.columns:
            df[col] = df[col].fillna(avg.get(col, 0))

    n_matched = df[SPATIAL_FEATURE_NAMES[0]].notna().sum()
    logger.info(
        f"Added {len(SPATIAL_FEATURE_NAMES)} spatial features "
        f"({n_matched}/{len(df)} rows matched barangays)"
    )
    return df


# ═════════════════════════════════════════════════════════════════════════════
# Flood Depth Estimation
# ═════════════════════════════════════════════════════════════════════════════

def estimate_flood_depth(
    barangay: str,
    rainfall_mm: float,
    duration_hours: float = 24.0,
    antecedent_rainfall_mm: float = 0.0,
    tide_height_m: float = 0.0,
) -> Dict[str, Any]:
    """
    Physics-informed flood depth estimate for a barangay.

    Uses a simplified rainfall-runoff model (Rational Method adaptation)
    combined with barangay-specific spatial parameters.

    Parameters
    ----------
    barangay : str
        Barangay key.
    rainfall_mm : float
        Rainfall amount in mm.
    duration_hours : float
        Duration of the rainfall event in hours.
    antecedent_rainfall_mm : float
        Rainfall in the preceding 3 days (saturation indicator).
    tide_height_m : float
        Current tide height (Manila Bay reference, affects coastal barangays).

    Returns
    -------
    dict with estimated depth (m), uncertainty range, classification.
    """
    features = get_spatial_features_for_barangay(barangay)

    runoff_coeff = features["runoff_coefficient"]
    drainage_score = features["drainage_score"]
    min_elev = features["min_elevation_m"]
    imperv = features["impervious_surface_pct"] / 100.0

    # ── Effective rainfall (mm of runoff) ───────────────────────────────────
    # Antecedent moisture increases runoff coefficient
    ami_factor = min(1.0, 1.0 + 0.002 * antecedent_rainfall_mm)
    effective_runoff_coeff = min(0.98, runoff_coeff * ami_factor)
    runoff_mm = rainfall_mm * effective_runoff_coeff

    # ── Drainage removal ────────────────────────────────────────────────────
    # Estimated capacity: good=25mm/hr, moderate=15mm/hr, poor=8mm/hr
    drain_rate_mm_hr = {0.8: 25, 0.5: 15, 0.2: 8}.get(drainage_score, 15)
    drained_mm = drain_rate_mm_hr * duration_hours
    ponding_mm = max(0, runoff_mm - drained_mm)

    # ── Depth estimate ──────────────────────────────────────────────────────
    # Convert ponding (mm over catchment area) to depth at low point
    # Concentration factor: water collects at min-elevation areas
    # Lower elevation → more accumulation
    concentration_factor = 1.0 + max(0, 3.0 - min_elev) * 0.3
    depth_m = (ponding_mm / 1000.0) * concentration_factor

    # ── Tidal influence (coastal barangays) ─────────────────────────────────
    BARANGAY_ELEVATION, BARANGAY_DRAINAGE, _ = _get_gis_data()
    drain_info = BARANGAY_DRAINAGE.get(barangay, {})
    if drain_info.get("nearest_waterway") in ("Manila Bay Coast",) and tide_height_m > 0:
        # High tide reduces drainage capacity and raises baseline
        tidal_addition = max(0, tide_height_m - 0.5) * 0.3
        depth_m += tidal_addition

    # ── Uncertainty bounds ──────────────────────────────────────────────────
    uncertainty = 0.30  # ±30% for simplified model
    depth_low = depth_m * (1 - uncertainty)
    depth_high = depth_m * (1 + uncertainty)

    # ── Classification ──────────────────────────────────────────────────────
    if depth_m < 0.10:
        classification = "none"
    elif depth_m < 0.30:
        classification = "minor"
    elif depth_m < 0.60:
        classification = "moderate"
    elif depth_m < 1.00:
        classification = "major"
    else:
        classification = "severe"

    return {
        "barangay": barangay,
        "estimated_depth_m": round(depth_m, 3),
        "depth_range_m": [round(depth_low, 3), round(depth_high, 3)],
        "classification": classification,
        "inputs": {
            "rainfall_mm": rainfall_mm,
            "duration_hours": duration_hours,
            "antecedent_rainfall_mm": antecedent_rainfall_mm,
            "tide_height_m": tide_height_m,
        },
        "spatial_params": {
            "runoff_coefficient": runoff_coeff,
            "drainage_score": drainage_score,
            "min_elevation_m": min_elev,
            "flood_susceptibility": features["flood_susceptibility_index"],
        },
    }


# ═════════════════════════════════════════════════════════════════════════════
# Feature name list (for training config)
# ═════════════════════════════════════════════════════════════════════════════

SPATIAL_FEATURE_NAMES = [
    "mean_elevation_m",
    "min_elevation_m",
    "slope_pct",
    "elev_vulnerability",
    "drainage_score",
    "waterway_distance_m",
    "waterway_proximity",
    "impervious_surface_pct",
    "flood_history_events",
    "runoff_coefficient",
    "green_cover_pct",
    "land_use_encoded",
    "building_density_encoded",
    "flood_susceptibility_index",
    "absorption_capacity",
]


def get_spatial_feature_names() -> List[str]:
    """Return the list of spatial feature column names."""
    return SPATIAL_FEATURE_NAMES.copy()
