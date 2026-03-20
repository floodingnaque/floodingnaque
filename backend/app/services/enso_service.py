"""
ENSO (El Niño–Southern Oscillation) Index Service.

Fetches and engineers ENSO-related climate indices as predictive features
for inter-annual flood variability in Metro Manila (Parañaque City).

Indices Supported
-----------------
- **ONI** (Oceanic Niño Index): 3-month running mean of SST anomalies in
  Niño 3.4 region.  Primary index used by NOAA/CPC for ENSO classification.
- **SOI** (Southern Oscillation Index): Standardised sea-level pressure
  difference between Tahiti and Darwin.
- **MEI.v2** (Multivariate ENSO Index): Combines SST, SLP, surface wind,
  and OLR into a single index.

ENSO strongly modulates Philippine rainfall:
- **El Niño** (ONI ≥ +0.5): Suppresses Southwest Monsoon → drier conditions
- **La Niña** (ONI ≤ −0.5): Enhances rainfall / typhoon frequency → wetter

Data Sources
------------
- NOAA CPC: https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt
- BoM SOI: http://www.bom.gov.au/climate/enso/soi_monthly.txt
- NOAA PSL MEI: https://psl.noaa.gov/enso/mei/data/meiv2.data

Author: Floodingnaque Team
Date: 2026-03-02
"""

import csv
import io
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ── URLs ────────────────────────────────────────────────────────────────────
ONI_URL = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"
SOI_URL = "http://www.bom.gov.au/climate/enso/soi_monthly.txt"
MEI_URL = "https://psl.noaa.gov/enso/mei/data/meiv2.data"

# ── ENSO classification thresholds (based on ONI) ───────────────────────────
ENSO_THRESHOLDS = {
    "strong_el_nino": 1.5,
    "moderate_el_nino": 1.0,
    "weak_el_nino": 0.5,
    "neutral_upper": 0.5,
    "neutral_lower": -0.5,
    "weak_la_nina": -1.0,
    "moderate_la_nina": -1.5,
}

# ── Season names used in ONI data ───────────────────────────────────────────
SEASON_MAP = {
    "DJF": 1,
    "JFM": 2,
    "FMA": 3,
    "MAM": 4,
    "AMJ": 5,
    "MJJ": 6,
    "JJA": 7,
    "JAS": 8,
    "ASO": 9,
    "SON": 10,
    "OND": 11,
    "NDJ": 12,
}


# ═════════════════════════════════════════════════════════════════════════════
# Data Fetching
# ═════════════════════════════════════════════════════════════════════════════


def _fetch_text(url: str, timeout: int = 30) -> str:
    """Fetch plain-text data from a URL with error handling."""
    import requests  # lazy to avoid import cost at module level

    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response.text
    except Exception as e:
        logger.error(f"Failed to fetch ENSO data from {url}: {e}")
        raise


def fetch_oni_data() -> pd.DataFrame:
    """
    Fetch the Oceanic Niño Index from NOAA CPC.

    Returns a DataFrame with columns: year, month, oni
    (one row per bimonthly season, mapped to the centre month).
    """
    text = _fetch_text(ONI_URL)
    rows: List[Dict[str, Any]] = []

    for line in text.strip().splitlines():
        parts = line.split()
        if len(parts) < 4:
            continue
        try:
            season = parts[0]
            year = int(parts[1])
            oni_value = float(parts[-1])  # APTS column is last
            month = SEASON_MAP.get(season)
            if month is not None:
                rows.append({"year": year, "month": month, "oni": oni_value})
        except (ValueError, IndexError):
            continue

    df = pd.DataFrame(rows)
    if df.empty:
        logger.warning("ONI data is empty after parsing")
    else:
        logger.info(f"Fetched ONI data: {len(df)} records, {df['year'].min()}-{df['year'].max()}")
    return df


def fetch_soi_data() -> pd.DataFrame:
    """
    Fetch the Southern Oscillation Index from BoM.

    Returns DataFrame with columns: year, month, soi
    """
    text = _fetch_text(SOI_URL)
    rows: List[Dict[str, Any]] = []

    in_data = False
    for line in text.strip().splitlines():
        line = line.strip()
        # SOI file has header lines; data lines start with a 4-digit year
        if re.match(r"^\d{4}", line):
            in_data = True
        if not in_data:
            continue

        parts = line.split()
        if len(parts) < 13:
            continue
        try:
            year = int(parts[0])
            for m in range(1, 13):
                val = float(parts[m])
                if val != 999.9:  # 999.9 = missing
                    rows.append({"year": year, "month": m, "soi": val})
        except (ValueError, IndexError):
            continue

    df = pd.DataFrame(rows)
    if not df.empty:
        logger.info(f"Fetched SOI data: {len(df)} records, {df['year'].min()}-{df['year'].max()}")
    return df


def fetch_mei_data() -> pd.DataFrame:
    """
    Fetch the Multivariate ENSO Index v2 from NOAA PSL.

    Returns DataFrame with columns: year, month, mei
    """
    text = _fetch_text(MEI_URL)
    rows: List[Dict[str, Any]] = []

    for line in text.strip().splitlines():
        parts = line.split()
        if len(parts) < 13:
            continue
        try:
            year = int(parts[0])
            for m in range(1, 13):
                val = float(parts[m])
                if val != -999.0:
                    rows.append({"year": year, "month": m, "mei": val})
        except (ValueError, IndexError):
            continue

    df = pd.DataFrame(rows)
    if not df.empty:
        logger.info(f"Fetched MEI data: {len(df)} records, {df['year'].min()}-{df['year'].max()}")
    return df


# ═════════════════════════════════════════════════════════════════════════════
# Feature Engineering
# ═════════════════════════════════════════════════════════════════════════════


def classify_enso_phase(oni: float) -> str:
    """
    Classify ENSO phase from ONI value.

    Returns one of: strong_el_nino, moderate_el_nino, weak_el_nino,
    neutral, weak_la_nina, moderate_la_nina, strong_la_nina
    """
    if oni >= ENSO_THRESHOLDS["strong_el_nino"]:
        return "strong_el_nino"
    elif oni >= ENSO_THRESHOLDS["moderate_el_nino"]:
        return "moderate_el_nino"
    elif oni >= ENSO_THRESHOLDS["weak_el_nino"]:
        return "weak_el_nino"
    elif oni > ENSO_THRESHOLDS["neutral_lower"]:
        return "neutral"
    elif oni > ENSO_THRESHOLDS["weak_la_nina"]:
        return "weak_la_nina"
    elif oni > ENSO_THRESHOLDS["moderate_la_nina"]:
        return "moderate_la_nina"
    else:
        return "strong_la_nina"


def encode_enso_phase(phase: str) -> int:
    """
    Ordinal-encode ENSO phase for ML models.

    Encoding: strong_la_nina=-3 … neutral=0 … strong_el_nino=+3
    This preserves the natural ordering and physical meaning.
    """
    encoding = {
        "strong_la_nina": -3,
        "moderate_la_nina": -2,
        "weak_la_nina": -1,
        "neutral": 0,
        "weak_el_nino": 1,
        "moderate_el_nino": 2,
        "strong_el_nino": 3,
    }
    return encoding.get(phase, 0)


def compute_enso_lag_features(
    df: pd.DataFrame,
    oni_col: str = "oni",
    lags: Tuple[int, ...] = (1, 2, 3, 6),
) -> pd.DataFrame:
    """
    Compute lagged ENSO features capturing delayed teleconnection effects.

    ENSO influence on Philippine rainfall has a lag of 1-3 months, and
    preconditions up to 6 months ahead can signal upcoming monsoon changes.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain year, month, and the ONI column, sorted chronologically.
    oni_col : str
        Column name for the ONI values.
    lags : tuple of int
        Lag periods in months.

    Returns
    -------
    pd.DataFrame with additional columns: oni_lag1, oni_lag2, etc.
    """
    df = df.copy()
    for lag in lags:
        df[f"{oni_col}_lag{lag}"] = df[oni_col].shift(lag)

    # Rate of change (month-over-month)
    df[f"{oni_col}_delta"] = df[oni_col].diff()

    # 3-month rolling mean for smoothing
    df[f"{oni_col}_3m_avg"] = df[oni_col].rolling(window=3, min_periods=1).mean()

    return df


def add_enso_features(
    df: pd.DataFrame,
    year_col: str = "year",
    month_col: str = "month",
    oni_data: Optional[pd.DataFrame] = None,
    soi_data: Optional[pd.DataFrame] = None,
    include_lags: bool = True,
) -> pd.DataFrame:
    """
    Merge ENSO indices into a training/inference DataFrame.

    Adds the following columns:
    - oni: Oceanic Niño Index value
    - enso_phase: Categorical ENSO phase string
    - enso_phase_encoded: Ordinal-encoded ENSO phase (−3 to +3)
    - soi: Southern Oscillation Index (if available)
    - oni_lag1 … oni_lag6: Lagged ONI values (if include_lags=True)
    - oni_delta: Month-over-month ONI change
    - oni_3m_avg: 3-month rolling average ONI
    - enso_rainfall_modifier: Expected rainfall multiplier for Philippines

    Parameters
    ----------
    df : pd.DataFrame
        Must contain year and month columns.
    year_col, month_col : str
        Column names for temporal keys.
    oni_data : pd.DataFrame, optional
        Pre-fetched ONI data. Fetched from NOAA if None.
    soi_data : pd.DataFrame, optional
        Pre-fetched SOI data. Fetched from BoM if None.
    include_lags : bool
        Whether to compute lagged features.

    Returns
    -------
    pd.DataFrame with ENSO features merged in.
    """
    df = df.copy()

    # ── Ensure year/month columns exist ─────────────────────────────────────
    if year_col not in df.columns or month_col not in df.columns:
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
            if year_col not in df.columns:
                df[year_col] = df["date"].dt.year
            if month_col not in df.columns:
                df[month_col] = df["date"].dt.month
        else:
            logger.warning("Cannot add ENSO features: no year/month or date columns")
            return df

    # ── Fetch ONI data ──────────────────────────────────────────────────────
    if oni_data is None:
        try:
            oni_data = fetch_oni_data()
        except Exception as e:
            logger.error(f"Failed to fetch ONI data: {e}")
            return df

    if oni_data.empty:
        logger.warning("ONI data is empty - skipping ENSO feature engineering")
        return df

    # ── Merge ONI ───────────────────────────────────────────────────────────
    oni_data = oni_data.rename(columns={"year": year_col, "month": month_col})
    df = df.merge(oni_data, on=[year_col, month_col], how="left")

    # ── Classify ENSO phase ─────────────────────────────────────────────────
    df["enso_phase"] = df["oni"].apply(lambda x: classify_enso_phase(x) if pd.notna(x) else "unknown")
    df["enso_phase_encoded"] = df["enso_phase"].apply(encode_enso_phase)

    # ── Rainfall modifier (empirical for Metro Manila) ──────────────────────
    # La Niña → wetter (×1.15–1.30), El Niño → drier (×0.75–0.90)
    rainfall_modifiers = {
        "strong_la_nina": 1.30,
        "moderate_la_nina": 1.20,
        "weak_la_nina": 1.10,
        "neutral": 1.00,
        "weak_el_nino": 0.90,
        "moderate_el_nino": 0.85,
        "strong_el_nino": 0.75,
        "unknown": 1.00,
    }
    df["enso_rainfall_modifier"] = df["enso_phase"].map(rainfall_modifiers)

    # ── Merge SOI ───────────────────────────────────────────────────────────
    if soi_data is None:
        try:
            soi_data = fetch_soi_data()
        except Exception:
            soi_data = pd.DataFrame()

    if not soi_data.empty:
        soi_data = soi_data.rename(columns={"year": year_col, "month": month_col})
        df = df.merge(soi_data, on=[year_col, month_col], how="left")
    else:
        df["soi"] = np.nan

    # ── Lagged features ─────────────────────────────────────────────────────
    if include_lags and "oni" in df.columns:
        df = df.sort_values([year_col, month_col])
        df = compute_enso_lag_features(df, oni_col="oni")

    # ── Fill NaNs in ENSO columns ───────────────────────────────────────────
    enso_cols = [c for c in df.columns if c.startswith(("oni", "soi", "enso_", "mei"))]
    for col in enso_cols:
        if df[col].dtype in ("float64", "float32", "int64"):
            df[col] = df[col].fillna(0.0)

    logger.info(f"Added {len(enso_cols)} ENSO features to dataset ({len(df)} rows)")
    return df


# ═════════════════════════════════════════════════════════════════════════════
# ENSO Feature List for Training Config
# ═════════════════════════════════════════════════════════════════════════════

ENSO_FEATURE_NAMES = [
    "oni",
    "enso_phase_encoded",
    "enso_rainfall_modifier",
    "soi",
    "oni_lag1",
    "oni_lag2",
    "oni_lag3",
    "oni_lag6",
    "oni_delta",
    "oni_3m_avg",
]


def get_enso_feature_names(include_lags: bool = True) -> List[str]:
    """Return the list of ENSO feature column names."""
    if include_lags:
        return ENSO_FEATURE_NAMES
    return ["oni", "enso_phase_encoded", "enso_rainfall_modifier", "soi"]


# ═════════════════════════════════════════════════════════════════════════════
# Convenience: current ENSO state for real-time inference
# ═════════════════════════════════════════════════════════════════════════════


def get_current_enso_state() -> Dict[str, Any]:
    """
    Get the current ENSO state for real-time prediction enrichment.

    Returns a dict with oni, soi, enso_phase, and the rainfall modifier
    suitable for direct injection into a prediction input dictionary.
    """
    now = datetime.now(timezone.utc)
    current_year = now.year
    current_month = now.month

    state: Dict[str, Any] = {
        "oni": 0.0,
        "soi": 0.0,
        "enso_phase": "unknown",
        "enso_phase_encoded": 0,
        "enso_rainfall_modifier": 1.0,
        "timestamp": now.isoformat(),
    }

    try:
        oni_df = fetch_oni_data()
        if not oni_df.empty:
            match = oni_df[(oni_df["year"] == current_year) & (oni_df["month"] == current_month)]
            if match.empty:
                # Fall back to most recent available
                match = oni_df.sort_values(["year", "month"]).tail(1)
            if not match.empty:
                oni_val = float(match.iloc[0]["oni"])
                phase = classify_enso_phase(oni_val)
                state["oni"] = oni_val
                state["enso_phase"] = phase
                state["enso_phase_encoded"] = encode_enso_phase(phase)
                rainfall_modifiers = {
                    "strong_la_nina": 1.30,
                    "moderate_la_nina": 1.20,
                    "weak_la_nina": 1.10,
                    "neutral": 1.00,
                    "weak_el_nino": 0.90,
                    "moderate_el_nino": 0.85,
                    "strong_el_nino": 0.75,
                    "unknown": 1.00,
                }
                state["enso_rainfall_modifier"] = rainfall_modifiers.get(phase, 1.0)
    except Exception as e:
        logger.warning(f"Could not fetch current ONI state: {e}")

    try:
        soi_df = fetch_soi_data()
        if not soi_df.empty:
            match = soi_df[(soi_df["year"] == current_year) & (soi_df["month"] == current_month)]
            if match.empty:
                match = soi_df.sort_values(["year", "month"]).tail(1)
            if not match.empty:
                state["soi"] = float(match.iloc[0]["soi"])
    except Exception:  # nosec B110
        pass  # SOI is optional supplementary data

    logger.info(f"Current ENSO state: {state['enso_phase']} (ONI={state['oni']:.2f})")
    return state
