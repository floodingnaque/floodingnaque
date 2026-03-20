"""
Tests for Spatial Features - barangay-level feature engineering.
"""

import numpy as np
import pandas as pd
import pytest
from app.services.spatial_features import (
    BARANGAY_LAND_USE,
    SPATIAL_FEATURE_NAMES,
    add_spatial_features,
    estimate_flood_depth,
    get_all_barangay_features,
    get_spatial_feature_names,
    get_spatial_features_for_barangay,
)

# ═════════════════════════════════════════════════════════════════════════════
# Single Barangay Features
# ═════════════════════════════════════════════════════════════════════════════


class TestGetSpatialFeaturesForBarangay:
    """Tests for single-barangay spatial feature computation."""

    def test_known_barangay(self):
        features = get_spatial_features_for_barangay("tambo")
        assert "mean_elevation_m" in features
        assert "drainage_score" in features
        assert "flood_susceptibility_index" in features
        assert "absorption_capacity" in features

    def test_all_features_numeric(self):
        features = get_spatial_features_for_barangay("bf_homes")
        for key, val in features.items():
            assert isinstance(val, (int, float)), f"{key} is not numeric: {type(val)}"

    def test_vulnerability_range(self):
        features = get_spatial_features_for_barangay("tambo")
        assert 0 <= features["elev_vulnerability"] <= 1

    def test_susceptibility_range(self):
        features = get_spatial_features_for_barangay("merville")
        assert 0 <= features["flood_susceptibility_index"] <= 1

    def test_coastal_vs_inland(self):
        """Coastal barangays should have higher susceptibility than inland."""
        tambo = get_spatial_features_for_barangay("tambo")  # Coastal, low-lying
        sucat = get_spatial_features_for_barangay("sucat")  # Inland, elevated
        assert tambo["flood_susceptibility_index"] > sucat["flood_susceptibility_index"]

    def test_unknown_barangay_defaults(self):
        features = get_spatial_features_for_barangay("nonexistent_barangay")
        # Should return default values, not crash
        assert "mean_elevation_m" in features


# ═════════════════════════════════════════════════════════════════════════════
# All Barangay Features
# ═════════════════════════════════════════════════════════════════════════════


class TestGetAllBarangayFeatures:
    """Tests for the full barangay features DataFrame."""

    def test_returns_dataframe(self):
        df = get_all_barangay_features()
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

    def test_columns_match_feature_names(self):
        df = get_all_barangay_features()
        for name in SPATIAL_FEATURE_NAMES:
            assert name in df.columns, f"Missing column: {name}"

    def test_all_barangays_present(self):
        df = get_all_barangay_features()
        assert "tambo" in df.index
        assert "bf_homes" in df.index


# ═════════════════════════════════════════════════════════════════════════════
# DataFrame Enrichment
# ═════════════════════════════════════════════════════════════════════════════


class TestAddSpatialFeatures:
    """Tests for merging spatial features into DataFrames."""

    def test_with_barangay_column(self):
        df = pd.DataFrame(
            {
                "barangay": ["tambo", "bf_homes", "sucat"],
                "temperature": [30, 31, 29],
                "flood": [1, 0, 0],
            }
        )
        result = add_spatial_features(df)
        assert "flood_susceptibility_index" in result.columns
        assert len(result) == 3

    def test_with_default_barangay(self):
        df = pd.DataFrame(
            {
                "temperature": [30, 31],
                "flood": [1, 0],
            }
        )
        result = add_spatial_features(df, default_barangay="tambo")
        assert "flood_susceptibility_index" in result.columns

    def test_without_barangay_uses_averages(self):
        df = pd.DataFrame(
            {
                "temperature": [30, 31],
                "flood": [1, 0],
            }
        )
        result = add_spatial_features(df)
        assert "flood_susceptibility_index" in result.columns
        # Should have average values (not NaN)
        assert result["flood_susceptibility_index"].notna().all()


# ═════════════════════════════════════════════════════════════════════════════
# Flood Depth Estimation
# ═════════════════════════════════════════════════════════════════════════════


class TestEstimateFloodDepth:
    """Tests for physics-informed flood depth estimation."""

    def test_returns_depth(self):
        result = estimate_flood_depth("tambo", rainfall_mm=100)
        assert "estimated_depth_m" in result
        assert "classification" in result
        assert result["estimated_depth_m"] >= 0

    def test_more_rain_more_depth(self):
        # Use short duration (3h) so drainage capacity is limited, producing non-zero ponding
        light = estimate_flood_depth("tambo", rainfall_mm=50, duration_hours=3)
        heavy = estimate_flood_depth("tambo", rainfall_mm=500, duration_hours=3)
        assert heavy["estimated_depth_m"] > light["estimated_depth_m"]

    def test_classification_categories(self):
        valid = {"none", "minor", "moderate", "major", "severe"}
        result = estimate_flood_depth("tambo", rainfall_mm=50)
        assert result["classification"] in valid

    def test_antecedent_rainfall_increases_depth(self):
        dry = estimate_flood_depth("tambo", rainfall_mm=50, antecedent_rainfall_mm=0)
        wet = estimate_flood_depth("tambo", rainfall_mm=50, antecedent_rainfall_mm=200)
        assert wet["estimated_depth_m"] >= dry["estimated_depth_m"]

    def test_depth_range(self):
        result = estimate_flood_depth("tambo", rainfall_mm=100)
        low, high = result["depth_range_m"]
        assert low <= result["estimated_depth_m"] <= high


# ═════════════════════════════════════════════════════════════════════════════
# Feature Name Helpers
# ═════════════════════════════════════════════════════════════════════════════


class TestGetSpatialFeatureNames:
    """Tests for feature name list."""

    def test_returns_list(self):
        names = get_spatial_feature_names()
        assert isinstance(names, list)
        assert len(names) == len(SPATIAL_FEATURE_NAMES)

    def test_returns_copy(self):
        names = get_spatial_feature_names()
        names.append("extra")
        assert "extra" not in SPATIAL_FEATURE_NAMES
