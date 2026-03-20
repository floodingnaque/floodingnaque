"""
Common Preprocessing Utilities
==============================

This module provides shared preprocessing functions used by both
preprocess_pagasa_data.py and preprocess_official_flood_records.py.

Extracts common logic to reduce code duplication and ensure consistency
across data preprocessing pipelines.

.. module:: preprocessing_common
   :synopsis: Shared data preprocessing utilities.

.. moduleauthor:: Floodingnaque Team

Features
--------
- Physical value validation and range checking
- Feature engineering (interactions, rolling windows)
- Missing value handling
- Monsoon/seasonal indicators
- Flood risk classification

Example
-------
::

    >>> from preprocessing_common import (
    ...     validate_physical_ranges,
    ...     add_interaction_features,
    ...     add_monsoon_indicators,
    ... )
    >>> df = validate_physical_ranges(df)
    >>> df = add_interaction_features(df)
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# =============================================================================
# Path Constants
# =============================================================================
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
DATA_DIR = BACKEND_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"

# =============================================================================
# Physical Constants and Valid Ranges
# =============================================================================

#: Valid ranges for physical measurements (Metro Manila conditions)
VALID_RANGES: Dict[str, Tuple[float, float]] = {
    "temperature": (15, 45),  # °C - Metro Manila range
    "temperature_kelvin": (288, 318),  # Kelvin
    "humidity": (20, 100),  # %
    "precipitation": (0, 500),  # mm/day (historical max ~450mm typhoon)
    "wind_speed": (0, 50),  # m/s (extreme typhoon)
}

#: Month to season mapping for Philippines
MONTH_TO_SEASON: Dict[int, str] = {
    1: "dry",
    2: "dry",
    3: "dry",
    4: "dry",
    5: "dry",
    6: "wet",
    7: "wet",
    8: "wet",
    9: "wet",
    10: "wet",
    11: "wet",
    12: "dry",
}

#: Monsoon months (June-November)
MONSOON_MONTHS: List[int] = [6, 7, 8, 9, 10, 11]

#: PAGASA Rainfall Intensity Classification (mm/day adapted from mm/hr)
RAINFALL_INTENSITY: Dict[str, Tuple[float, float]] = {
    "none": (0, 0.1),
    "light": (0.1, 7.5),
    "moderate": (7.5, 30),
    "heavy": (30, 75),
    "intense": (75, 150),
    "torrential": (150, float("inf")),
}


# =============================================================================
# Validation Functions
# =============================================================================


def validate_physical_ranges(
    df: pd.DataFrame,
    ranges: Optional[Dict[str, Tuple[float, float]]] = None,
    action: str = "nan",
) -> pd.DataFrame:
    """
    Validate and handle physically impossible values.

    :param df: DataFrame to validate.
    :type df: pd.DataFrame
    :param ranges: Dictionary mapping column names to (min, max) tuples.
                   Defaults to VALID_RANGES.
    :type ranges: Optional[Dict[str, Tuple[float, float]]]
    :param action: Action to take on invalid values:
                   - 'nan': Replace with NaN (default)
                   - 'clip': Clip to valid range
                   - 'drop': Drop rows with invalid values
    :type action: str
    :return: DataFrame with validated values.
    :rtype: pd.DataFrame

    Example
    -------
    ::

        >>> df = validate_physical_ranges(df, action='clip')
    """
    if ranges is None:
        ranges = VALID_RANGES

    df = df.copy()
    validation_issues: Dict[str, int] = {}

    for col, (min_val, max_val) in ranges.items():
        if col not in df.columns:
            continue

        invalid = (df[col] < min_val) | (df[col] > max_val)
        if invalid.any():
            count = invalid.sum()
            validation_issues[col] = count
            logger.warning(f"{col}: {count} values outside valid range [{min_val}, {max_val}]")

            if action == "nan":
                df.loc[invalid, col] = np.nan
            elif action == "clip":
                df[col] = df[col].clip(min_val, max_val)
            elif action == "drop":
                df = df[~invalid]

    if validation_issues:
        logger.info(f"Total validation issues: {sum(validation_issues.values())}")

    return df


def standardize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardize DataFrame column names to lowercase with underscores.

    :param df: DataFrame with columns to standardize.
    :type df: pd.DataFrame
    :return: DataFrame with standardized column names.
    :rtype: pd.DataFrame
    """
    df = df.copy()
    df.columns = [col.lower().strip().replace(" ", "_") for col in df.columns]
    return df


# =============================================================================
# Temporal Feature Engineering
# =============================================================================


def add_monsoon_indicators(df: pd.DataFrame, month_col: str = "month") -> pd.DataFrame:
    """
    Add monsoon season indicators based on month.

    :param df: DataFrame with month column.
    :type df: pd.DataFrame
    :param month_col: Name of the month column.
    :type month_col: str
    :return: DataFrame with monsoon indicators added.
    :rtype: pd.DataFrame

    Columns Added
    -------------
    - season: 'wet' or 'dry'
    - is_monsoon_season: Binary indicator (1 for monsoon months)
    """
    df = df.copy()

    if month_col not in df.columns:
        logger.warning(f"Month column '{month_col}' not found. Skipping monsoon indicators.")
        return df

    df["season"] = df[month_col].map(MONTH_TO_SEASON)
    df["is_monsoon_season"] = df[month_col].isin(MONSOON_MONTHS).astype(int)

    return df


def add_rolling_features(
    df: pd.DataFrame,
    date_col: str = "date",
    precip_col: str = "precipitation",
    humidity_col: str = "humidity",
    temp_col: str = "temperature",
) -> pd.DataFrame:
    """
    Add rolling window features for temporal patterns.

    :param df: DataFrame sorted by date.
    :type df: pd.DataFrame
    :param date_col: Name of date column for sorting.
    :type date_col: str
    :param precip_col: Name of precipitation column.
    :type precip_col: str
    :param humidity_col: Name of humidity column.
    :type humidity_col: str
    :param temp_col: Name of temperature column.
    :type temp_col: str
    :return: DataFrame with rolling features.
    :rtype: pd.DataFrame

    Columns Added
    -------------
    Precipitation features:
        - precip_3day_sum, precip_7day_sum, precip_14day_sum
        - precip_3day_avg, precip_7day_avg
        - precip_max_3day, precip_max_7day
        - precip_lag1, precip_lag2, precip_lag3
        - rain_streak (consecutive rain days)

    Humidity features:
        - humidity_3day_avg, humidity_7day_avg, humidity_lag1

    Temperature features:
        - temp_3day_avg, temp_7day_avg
    """
    df = df.copy()

    if date_col in df.columns:
        df = df.sort_values(date_col)

    # Precipitation rolling features
    if precip_col in df.columns:
        df["precip_3day_sum"] = df[precip_col].rolling(window=3, min_periods=1).sum()
        df["precip_7day_sum"] = df[precip_col].rolling(window=7, min_periods=1).sum()
        df["precip_14day_sum"] = df[precip_col].rolling(window=14, min_periods=1).sum()
        df["precip_3day_avg"] = df[precip_col].rolling(window=3, min_periods=1).mean()
        df["precip_7day_avg"] = df[precip_col].rolling(window=7, min_periods=1).mean()
        df["precip_max_3day"] = df[precip_col].rolling(window=3, min_periods=1).max()
        df["precip_max_7day"] = df[precip_col].rolling(window=7, min_periods=1).max()

        # Lagged features
        df["precip_lag1"] = df[precip_col].shift(1)
        df["precip_lag2"] = df[precip_col].shift(2)
        df["precip_lag3"] = df[precip_col].shift(3)

        # Rain streak (consecutive rain days)
        df["is_rain"] = (df[precip_col] > 0.1).astype(int)
        df["rain_streak"] = df["is_rain"].groupby((df["is_rain"] != df["is_rain"].shift()).cumsum()).cumcount() + 1
        df.loc[df["is_rain"] == 0, "rain_streak"] = 0

    # Humidity rolling features
    if humidity_col in df.columns:
        df["humidity_3day_avg"] = df[humidity_col].rolling(window=3, min_periods=1).mean()
        df["humidity_7day_avg"] = df[humidity_col].rolling(window=7, min_periods=1).mean()
        df["humidity_lag1"] = df[humidity_col].shift(1)

    # Temperature rolling features
    if temp_col in df.columns:
        df["temp_3day_avg"] = df[temp_col].rolling(window=3, min_periods=1).mean()
        df["temp_7day_avg"] = df[temp_col].rolling(window=7, min_periods=1).mean()

    return df


# =============================================================================
# Interaction Features
# =============================================================================


def add_interaction_features(
    df: pd.DataFrame,
    temp_col: str = "temperature",
    humidity_col: str = "humidity",
    precip_col: str = "precipitation",
    monsoon_col: str = "is_monsoon_season",
    wind_col: str = "wind_speed",
    wind_dir_col: str = "wind_direction",
) -> pd.DataFrame:
    """
    Add interaction features between weather variables.

    :param df: DataFrame with weather columns.
    :type df: pd.DataFrame
    :param temp_col: Temperature column name.
    :type temp_col: str
    :param humidity_col: Humidity column name.
    :type humidity_col: str
    :param precip_col: Precipitation column name.
    :type precip_col: str
    :param monsoon_col: Monsoon indicator column name.
    :type monsoon_col: str
    :param wind_col: Wind speed column name.
    :type wind_col: str
    :param wind_dir_col: Wind direction column name.
    :type wind_dir_col: str
    :return: DataFrame with interaction features.
    :rtype: pd.DataFrame

    Columns Added
    -------------
    - temp_humidity_interaction: Temperature * Humidity interaction
    - humidity_precip_interaction: Humidity * log(precipitation)
    - temp_precip_interaction: Temperature * log(precipitation)
    - monsoon_precip_interaction: Monsoon indicator * precipitation
    - wind_rain_interaction: Wind speed * log(precipitation)
    - is_sw_monsoon_wind: SW monsoon wind indicator (180-270°)
    - saturation_risk: High humidity + precipitation indicator
    """
    df = df.copy()

    # Temperature-Humidity interaction (affects evaporation/saturation)
    if all(c in df.columns for c in [temp_col, humidity_col]):
        df["temp_humidity_interaction"] = df[temp_col] * df[humidity_col] / 100

    # Precipitation-Humidity interaction (soil saturation)
    if all(c in df.columns for c in [humidity_col, precip_col]):
        df["humidity_precip_interaction"] = df[humidity_col] * np.log1p(df[precip_col])

    # Temperature-Precipitation interaction
    if all(c in df.columns for c in [temp_col, precip_col]):
        df["temp_precip_interaction"] = df[temp_col] * np.log1p(df[precip_col])

    # Monsoon-Precipitation interaction
    if all(c in df.columns for c in [monsoon_col, precip_col]):
        df["monsoon_precip_interaction"] = df[monsoon_col] * df[precip_col]

    # Wind-Rain interaction (monsoon patterns)
    if all(c in df.columns for c in [wind_col, precip_col]):
        df["wind_rain_interaction"] = df[wind_col] * np.log1p(df[precip_col])

    # Wind direction indicator (SW monsoon from 180-270°)
    if wind_dir_col in df.columns:
        df["is_sw_monsoon_wind"] = ((df[wind_dir_col] >= 180) & (df[wind_dir_col] <= 270)).astype(int)

    # High humidity + high precipitation = extreme flood risk
    if all(c in df.columns for c in [humidity_col, precip_col]):
        df["saturation_risk"] = ((df[humidity_col] > 85) & (df[precip_col] > 20)).astype(int)

    return df


# =============================================================================
# Flood Risk Classification
# =============================================================================


def classify_flood_risk(
    df: pd.DataFrame,
    precip_col: str = "precipitation",
    precip_3day_col: str = "precip_3day_sum",
    rain_streak_col: str = "rain_streak",
) -> pd.DataFrame:
    """
    Classify flood risk based on precipitation thresholds.

    :param df: DataFrame with precipitation data.
    :type df: pd.DataFrame
    :param precip_col: Daily precipitation column.
    :type precip_col: str
    :param precip_3day_col: 3-day cumulative precipitation column.
    :type precip_3day_col: str
    :param rain_streak_col: Consecutive rain days column.
    :type rain_streak_col: str
    :return: DataFrame with flood risk classification.
    :rtype: pd.DataFrame

    Risk Levels
    -----------
    - 0 (LOW): Normal conditions
    - 1 (MODERATE): Elevated flood risk
    - 2 (HIGH): Significant flood risk

    Columns Added
    -------------
    - flood_risk_daily: Risk from daily precipitation
    - flood_risk_cumulative: Risk from 3-day cumulative
    - flood_risk_streak: Risk from consecutive rain days
    - risk_level: Combined maximum risk
    - flood: Binary flood indicator (risk_level >= 1)
    - flood_probability: Estimated flood probability
    """
    df = df.copy()

    # Daily precipitation-based risk
    if precip_col in df.columns:
        daily_conditions = [
            (df[precip_col] < 20),  # Low risk
            (df[precip_col] >= 20) & (df[precip_col] < 50),  # Moderate
            (df[precip_col] >= 50),  # High risk
        ]
        df["flood_risk_daily"] = np.select(daily_conditions, [0, 1, 2], default=0)
    else:
        df["flood_risk_daily"] = 0

    # Cumulative 3-day rainfall risk
    if precip_3day_col in df.columns:
        cum_conditions = [
            (df[precip_3day_col] < 40),
            (df[precip_3day_col] >= 40) & (df[precip_3day_col] < 80),
            (df[precip_3day_col] >= 80),
        ]
        df["flood_risk_cumulative"] = np.select(cum_conditions, [0, 1, 2], default=0)
    else:
        df["flood_risk_cumulative"] = df["flood_risk_daily"]

    # Rain streak-based risk
    if rain_streak_col in df.columns:
        streak_conditions = [
            (df[rain_streak_col] < 3),
            (df[rain_streak_col] >= 3) & (df[rain_streak_col] < 5),
            (df[rain_streak_col] >= 5),
        ]
        df["flood_risk_streak"] = np.select(streak_conditions, [0, 1, 2], default=0)
    else:
        df["flood_risk_streak"] = 0

    # Combined risk level (maximum of all indicators)
    risk_columns = ["flood_risk_daily", "flood_risk_cumulative", "flood_risk_streak"]
    df["risk_level"] = df[risk_columns].max(axis=1)

    # Binary flood indicator
    df["flood"] = (df["risk_level"] >= 1).astype(int)

    # Flood probability estimate
    df["flood_probability"] = (
        0.4 * df["flood_risk_daily"] / 2 + 0.4 * df["flood_risk_cumulative"] / 2 + 0.2 * df["flood_risk_streak"] / 2
    )

    return df


# =============================================================================
# Missing Value Handling
# =============================================================================


def handle_missing_values(
    df: pd.DataFrame,
    numeric_strategy: str = "median",
    categorical_strategy: str = "mode",
    max_missing_ratio: float = 0.5,
) -> pd.DataFrame:
    """
    Handle missing values in DataFrame.

    :param df: DataFrame with missing values.
    :type df: pd.DataFrame
    :param numeric_strategy: Strategy for numeric columns ('median', 'mean', 'zero').
    :type numeric_strategy: str
    :param categorical_strategy: Strategy for categorical columns ('mode', 'unknown').
    :type categorical_strategy: str
    :param max_missing_ratio: Drop columns exceeding this missing ratio.
    :type max_missing_ratio: float
    :return: DataFrame with handled missing values.
    :rtype: pd.DataFrame
    """
    df = df.copy()

    # Drop columns with too many missing values
    missing_ratios = df.isna().mean()
    cols_to_drop = missing_ratios[missing_ratios > max_missing_ratio].index.tolist()
    if cols_to_drop:
        logger.warning(f"Dropping columns with >{max_missing_ratio:.0%} missing: {cols_to_drop}")
        df = df.drop(columns=cols_to_drop)

    # Handle numeric columns
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        if df[col].isna().any():
            if numeric_strategy == "median":
                fill_val = df[col].median()
            elif numeric_strategy == "mean":
                fill_val = df[col].mean()
            else:  # zero
                fill_val = 0
            df[col] = df[col].fillna(fill_val)

    # Handle categorical columns
    categorical_cols = df.select_dtypes(include=["object", "category"]).columns
    for col in categorical_cols:
        if df[col].isna().any():
            if categorical_strategy == "mode":
                mode_val = df[col].mode()
                fill_val = mode_val.iloc[0] if not mode_val.empty else "unknown"
            else:
                fill_val = "unknown"
            df[col] = df[col].fillna(fill_val)

    return df


# =============================================================================
# Heat Index Calculation
# =============================================================================


def calculate_heat_index(temp_c: pd.Series, rh: pd.Series) -> pd.Series:
    """
    Calculate heat index from temperature (°C) and relative humidity (%).

    Uses the simplified Steadman formula for most cases,
    with Rothfusz regression for high temperatures.

    :param temp_c: Temperature in Celsius.
    :type temp_c: pd.Series
    :param rh: Relative humidity in percent.
    :type rh: pd.Series
    :return: Heat index in Celsius.
    :rtype: pd.Series
    """
    # Convert to Fahrenheit for standard formula
    temp_f = temp_c * 9 / 5 + 32

    # Simple formula for most cases
    hi = 0.5 * (temp_f + 61.0 + ((temp_f - 68.0) * 1.2) + (rh * 0.094))

    # Use Rothfusz regression for high temperatures
    mask = hi >= 80
    if mask.any():
        hi_full = (
            -42.379
            + 2.04901523 * temp_f
            + 10.14333127 * rh
            - 0.22475541 * temp_f * rh
            - 0.00683783 * temp_f**2
            - 0.05481717 * rh**2
            + 0.00122874 * temp_f**2 * rh
            + 0.00085282 * temp_f * rh**2
            - 0.00000199 * temp_f**2 * rh**2
        )
        hi = np.where(mask, hi_full, hi)

    # Convert back to Celsius
    return pd.Series((hi - 32) * 5 / 9, index=temp_c.index)


# =============================================================================
# Rainfall Intensity Classification
# =============================================================================


def classify_rainfall_intensity(precipitation: pd.Series) -> pd.Series:
    """
    Classify rainfall intensity based on PAGASA standards.

    :param precipitation: Daily precipitation in mm.
    :type precipitation: pd.Series
    :return: Rainfall intensity classification.
    :rtype: pd.Series
    """
    conditions = [
        (precipitation <= 0.1),
        (precipitation > 0.1) & (precipitation <= 7.5),
        (precipitation > 7.5) & (precipitation <= 30),
        (precipitation > 30) & (precipitation <= 75),
        (precipitation > 75) & (precipitation <= 150),
        (precipitation > 150),
    ]
    choices = ["none", "light", "moderate", "heavy", "intense", "torrential"]

    return pd.Series(np.select(conditions, choices, default="unknown"), index=precipitation.index)


# =============================================================================
# Exported Functions
# =============================================================================

__all__ = [
    # Constants
    "VALID_RANGES",
    "MONTH_TO_SEASON",
    "MONSOON_MONTHS",
    "RAINFALL_INTENSITY",
    "DATA_DIR",
    "PROCESSED_DIR",
    # Validation
    "validate_physical_ranges",
    "standardize_column_names",
    # Temporal features
    "add_monsoon_indicators",
    "add_rolling_features",
    # Interaction features
    "add_interaction_features",
    # Classification
    "classify_flood_risk",
    "classify_rainfall_intensity",
    # Missing values
    "handle_missing_values",
    # Calculations
    "calculate_heat_index",
]
