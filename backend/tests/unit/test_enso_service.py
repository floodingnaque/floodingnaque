"""
Tests for ENSO Service - climate index fetching and feature engineering.
"""

import numpy as np
import pandas as pd
import pytest
from app.services.enso_service import (
    ENSO_FEATURE_NAMES,
    add_enso_features,
    classify_enso_phase,
    compute_enso_lag_features,
    encode_enso_phase,
    get_current_enso_state,
    get_enso_feature_names,
)

# ═════════════════════════════════════════════════════════════════════════════
# ENSO Phase Classification
# ═════════════════════════════════════════════════════════════════════════════


class TestClassifyEnsoPhase:
    """Tests for ENSO phase classification from ONI values."""

    def test_strong_el_nino(self):
        assert classify_enso_phase(2.0) == "strong_el_nino"
        assert classify_enso_phase(1.5) == "strong_el_nino"

    def test_moderate_el_nino(self):
        assert classify_enso_phase(1.2) == "moderate_el_nino"
        assert classify_enso_phase(1.0) == "moderate_el_nino"

    def test_weak_el_nino(self):
        assert classify_enso_phase(0.7) == "weak_el_nino"
        assert classify_enso_phase(0.5) == "weak_el_nino"

    def test_neutral(self):
        assert classify_enso_phase(0.3) == "neutral"
        assert classify_enso_phase(0.0) == "neutral"
        assert classify_enso_phase(-0.3) == "neutral"

    def test_weak_la_nina(self):
        assert classify_enso_phase(-0.7) == "weak_la_nina"

    def test_moderate_la_nina(self):
        assert classify_enso_phase(-1.2) == "moderate_la_nina"

    def test_strong_la_nina(self):
        assert classify_enso_phase(-2.0) == "strong_la_nina"
        assert classify_enso_phase(-1.5) == "strong_la_nina"


class TestEncodeEnsoPhase:
    """Tests for ordinal encoding of ENSO phases."""

    def test_encoding_range(self):
        assert encode_enso_phase("strong_la_nina") == -3
        assert encode_enso_phase("neutral") == 0
        assert encode_enso_phase("strong_el_nino") == 3

    def test_unknown_phase(self):
        assert encode_enso_phase("unknown") == 0

    def test_monotonic_ordering(self):
        phases = [
            "strong_la_nina",
            "moderate_la_nina",
            "weak_la_nina",
            "neutral",
            "weak_el_nino",
            "moderate_el_nino",
            "strong_el_nino",
        ]
        values = [encode_enso_phase(p) for p in phases]
        assert values == sorted(values)


# ═════════════════════════════════════════════════════════════════════════════
# Lag Features
# ═════════════════════════════════════════════════════════════════════════════


class TestComputeEnsoLagFeatures:
    """Tests for lagged ONI feature computation."""

    def test_lag_columns_created(self):
        df = pd.DataFrame(
            {
                "year": range(2020, 2024),
                "month": [1, 2, 3, 4],
                "oni": [0.5, 0.8, 1.0, 0.3],
            }
        )
        result = compute_enso_lag_features(df)
        assert "oni_lag1" in result.columns
        assert "oni_lag2" in result.columns
        assert "oni_lag3" in result.columns
        assert "oni_lag6" in result.columns
        assert "oni_delta" in result.columns
        assert "oni_3m_avg" in result.columns

    def test_lag_values(self):
        df = pd.DataFrame(
            {
                "year": [2020] * 4,
                "month": [1, 2, 3, 4],
                "oni": [0.5, 0.8, 1.0, 0.3],
            }
        )
        result = compute_enso_lag_features(df, lags=(1,))
        assert result["oni_lag1"].iloc[1] == 0.5
        assert result["oni_lag1"].iloc[2] == 0.8


# ═════════════════════════════════════════════════════════════════════════════
# Feature Merging
# ═════════════════════════════════════════════════════════════════════════════


class TestAddEnsoFeatures:
    """Tests for merging ENSO features into a DataFrame."""

    def _make_oni_data(self):
        return pd.DataFrame(
            {
                "year": [2023, 2023, 2023],
                "month": [6, 7, 8],
                "oni": [0.5, 0.8, 1.2],
            }
        )

    def test_adds_columns(self):
        df = pd.DataFrame(
            {
                "year": [2023, 2023],
                "month": [6, 7],
                "temperature": [30, 31],
                "flood": [0, 1],
            }
        )
        result = add_enso_features(df, oni_data=self._make_oni_data(), include_lags=False)
        assert "oni" in result.columns
        assert "enso_phase" in result.columns
        assert "enso_phase_encoded" in result.columns
        assert "enso_rainfall_modifier" in result.columns

    def test_from_date_column(self):
        df = pd.DataFrame(
            {
                "date": pd.to_datetime(["2023-06-15", "2023-07-20"]),
                "temperature": [30, 31],
                "flood": [0, 1],
            }
        )
        result = add_enso_features(df, oni_data=self._make_oni_data(), include_lags=False)
        assert "oni" in result.columns

    def test_missing_columns_unchanged(self):
        df = pd.DataFrame({"x": [1, 2], "y": [3, 4]})
        result = add_enso_features(df, oni_data=self._make_oni_data())
        assert len(result) == 2  # No crash, just returns unchanged


class TestGetEnsoFeatureNames:
    """Tests for feature name helpers."""

    def test_with_lags(self):
        names = get_enso_feature_names(include_lags=True)
        assert "oni_lag1" in names
        assert "oni" in names

    def test_without_lags(self):
        names = get_enso_feature_names(include_lags=False)
        assert "oni_lag1" not in names
        assert "oni" in names
