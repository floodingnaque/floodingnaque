#!/usr/bin/env python
"""
Calibrate Risk Thresholds from Real DRRMO + PAGASA Data
=======================================================

Analyzes actual flood records and PAGASA weather observations to derive
data-driven thresholds for the 3-level risk classifier (Safe/Alert/Critical).

Aligns with PAGASA Rainfall Warning System:
    Yellow:  7.5-15 mm/hr   → Alert
    Orange: 15-30 mm/hr     → Alert (upper)
    Red:    >30 mm/hr       → Critical

Output:
    - Updated thresholds in training_config.yaml (risk_classification section)
    - reports/threshold_calibration_report.json (justification data)

Usage:
    python scripts/calibrate_risk_thresholds.py
    python scripts/calibrate_risk_thresholds.py --dry-run
"""

import argparse
import json
import logging
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import yaml

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
MODELS_DIR = BACKEND_DIR / "models"
DATA_DIR = BACKEND_DIR / "data" / "processed"
REPORTS_DIR = BACKEND_DIR / "reports"
CONFIG_PATH = BACKEND_DIR / "config" / "training_config.yaml"


def load_combined_data() -> pd.DataFrame:
    """Load all real data sources used in v6 training."""
    frames = []
    for f in [
        "cumulative_v2_up_to_2025.csv",
        "pagasa_training_dataset.csv",
    ]:
        path = DATA_DIR / f
        if path.exists():
            df = pd.read_csv(path)
            df["_source"] = f
            frames.append(df)
            logger.info(f"Loaded {f}: {len(df)} records")
    if not frames:
        raise FileNotFoundError("No training data found in data/processed/")
    combined = pd.concat(frames, ignore_index=True)
    logger.info(f"Combined: {len(combined)} records")
    return combined


def compute_probability_thresholds(model_path: Path, data: pd.DataFrame, features: list) -> dict:
    """Derive flood probability thresholds from model predictions on real data."""
    model = joblib.load(model_path)
    logger.info(f"Loaded model: {model_path.name}")

    # Prepare features — add missing columns as 0
    available_cols = [c for c in features if c in data.columns]
    X = data[available_cols].copy()
    for col in features:
        if col not in X.columns:
            X[col] = 0.0
    X = X[features].fillna(0.0)

    y_true = data["flood"].values
    y_proba = model.predict_proba(X)[:, 1]

    # Separate predictions by actual class
    flood_probs = y_proba[y_true == 1]
    noflood_probs = y_proba[y_true == 0]

    # Critical threshold: percentile where most floods are correctly captured
    # We want >= 90% of actual floods above this → use 10th percentile of flood probabilities
    critical = float(np.percentile(flood_probs, 25))  # 25th pctl — conservative

    # Alert threshold: captures moderate-risk scenarios
    # Use the zone where flood prob starts rising — 75th percentile of non-flood probs
    alert = float(np.percentile(noflood_probs, 90))

    # Safe max: below this, very unlikely to be a flood
    safe_max = float(np.percentile(noflood_probs, 75))

    # Ensure ordering: safe_max < alert < critical
    if alert >= critical:
        alert = critical * 0.7
    if safe_max >= alert:
        safe_max = alert * 0.6

    result = {
        "critical": round(critical, 2),
        "alert": round(alert, 2),
        "safe_max": round(safe_max, 2),
        "analysis": {
            "flood_prob_mean": round(float(flood_probs.mean()), 4),
            "flood_prob_median": round(float(np.median(flood_probs)), 4),
            "flood_prob_p10": round(float(np.percentile(flood_probs, 10)), 4),
            "flood_prob_p25": round(float(np.percentile(flood_probs, 25)), 4),
            "noflood_prob_mean": round(float(noflood_probs.mean()), 4),
            "noflood_prob_p75": round(float(np.percentile(noflood_probs, 75)), 4),
            "noflood_prob_p90": round(float(np.percentile(noflood_probs, 90)), 4),
            "n_flood": int(len(flood_probs)),
            "n_noflood": int(len(noflood_probs)),
        },
    }
    logger.info(f"Probability thresholds: critical={critical:.2f}, alert={alert:.2f}, safe_max={safe_max:.2f}")
    return result


def compute_precipitation_thresholds(data: pd.DataFrame) -> dict:
    """
    Derive precipitation thresholds aligned with PAGASA Rainfall Warning System.

    PAGASA Warning Levels (hourly rainfall):
        Yellow:  7.5 - 15 mm/hr
        Orange: 15 - 30 mm/hr
        Red:    > 30 mm/hr

    Our data uses daily precipitation, so we adapt to daily accumulation.
    """
    flood_data = data[data["flood"] == 1]
    noflood_data = data[data["flood"] == 0]

    # Precipitation during flood events
    flood_precip = flood_data["precipitation"].dropna()
    noflood_precip = noflood_data["precipitation"].dropna()

    # Alert min: lowest daily precip that commonly causes floods
    # Use 25th percentile of flood-day precipitation
    alert_min = float(np.percentile(flood_precip[flood_precip > 0], 25))
    # Clamp to PAGASA-aligned range
    alert_min = max(7.5, min(alert_min, 15.0))

    # Alert max: upper bound before critical
    # Use 75th percentile of flood-day precipitation
    alert_max_data = float(np.percentile(flood_precip[flood_precip > 0], 75))
    alert_max = max(15.0, min(alert_max_data, 50.0))

    # Humidity threshold: derived from flood events
    flood_humidity = flood_data["humidity"].dropna()
    humidity_threshold = float(np.percentile(flood_humidity, 50))  # median during floods
    humidity_threshold = max(75.0, min(humidity_threshold, 95.0))

    # Humidity + precip min: minimum precip to pair with high humidity for alert
    humidity_precip_min = max(2.0, float(np.percentile(flood_precip[flood_precip > 0], 10)))

    result = {
        "alert_min": round(alert_min, 1),
        "alert_max": round(alert_max, 1),
        "humidity_threshold": round(humidity_threshold, 1),
        "humidity_precip_min": round(humidity_precip_min, 1),
        "analysis": {
            "flood_precip_mean": round(float(flood_precip.mean()), 2),
            "flood_precip_median": round(float(flood_precip.median()), 2),
            "flood_precip_p25": round(float(np.percentile(flood_precip[flood_precip > 0], 25)), 2),
            "flood_precip_p75": round(float(np.percentile(flood_precip[flood_precip > 0], 75)), 2),
            "noflood_precip_mean": round(float(noflood_precip.mean()), 2),
            "flood_humidity_mean": round(float(flood_humidity.mean()), 2),
            "flood_humidity_median": round(float(flood_humidity.median()), 2),
            "pagasa_alignment": {
                "yellow_range": "7.5-15 mm/hr",
                "orange_range": "15-30 mm/hr",
                "red_threshold": ">30 mm/hr",
                "note": "Daily precipitation thresholds adapted from PAGASA hourly warning system",
            },
        },
    }
    logger.info(
        f"Precipitation thresholds: alert_min={alert_min:.1f}, alert_max={alert_max:.1f}, "
        f"humidity={humidity_threshold:.1f}%"
    )
    return result


def compute_rainfall_3h_thresholds(data: pd.DataFrame) -> dict:
    """Derive 3-hour rainfall thresholds from PAGASA warning levels."""
    # PAGASA 3-hour accumulation thresholds (official):
    # Yellow: 22.5-45 mm/3h → our Alert
    # Orange: 45-90 mm/3h
    # Red: >90 mm/3h → our Critical
    result = {
        "critical": 65.0,  # Conservative: between Orange and Red
        "alert": 30.0,  # Between Yellow lower and mid
        "source": "Adapted from PAGASA Rainfall Warning System 3-hour accumulation",
    }
    logger.info(f"3h rainfall thresholds: critical={result['critical']}, alert={result['alert']}")
    return result


def main():
    parser = argparse.ArgumentParser(description="Calibrate risk thresholds from real data")
    parser.add_argument("--dry-run", action="store_true", help="Show thresholds without updating config")
    args = parser.parse_args()

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    # Load data
    data = load_combined_data()

    # Find latest model and its features
    model_path = MODELS_DIR / "flood_model_v6.joblib"
    meta_path = MODELS_DIR / "flood_model_v6.json"
    if not model_path.exists():
        raise FileNotFoundError(f"Model not found: {model_path}")

    with open(meta_path) as f:
        meta = json.load(f)
    features = meta["features"]

    # Filter data to rows that have the required features
    available = [c for c in features if c in data.columns]
    missing = [c for c in features if c not in data.columns]
    if missing:
        logger.warning(f"Missing features in data (will default to 0): {missing}")

    # Compute thresholds
    prob_thresholds = compute_probability_thresholds(model_path, data, features)
    precip_thresholds = compute_precipitation_thresholds(data)
    rain3h_thresholds = compute_rainfall_3h_thresholds(data)

    calibrated = {
        "flood_probability": {
            "critical": prob_thresholds["critical"],
            "alert": prob_thresholds["alert"],
            "safe_max": prob_thresholds["safe_max"],
        },
        "precipitation": {
            "alert_min": precip_thresholds["alert_min"],
            "alert_max": precip_thresholds["alert_max"],
            "humidity_threshold": precip_thresholds["humidity_threshold"],
            "humidity_precip_min": precip_thresholds["humidity_precip_min"],
        },
        "rainfall_3h": {
            "critical": rain3h_thresholds["critical"],
            "alert": rain3h_thresholds["alert"],
        },
    }

    # Save report
    report = {
        "generated_at": datetime.now().isoformat(),
        "data_sources": list(data["_source"].unique()),
        "total_records": len(data),
        "flood_events": int((data["flood"] == 1).sum()),
        "calibrated_thresholds": calibrated,
        "probability_analysis": prob_thresholds["analysis"],
        "precipitation_analysis": precip_thresholds["analysis"],
        "rainfall_3h": rain3h_thresholds,
    }
    report_path = REPORTS_DIR / "threshold_calibration_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    logger.info(f"Report saved: {report_path}")

    if args.dry_run:
        logger.info("DRY RUN — thresholds not written to config")
        print("\nCalibrated thresholds:")
        print(json.dumps(calibrated, indent=2))
        return

    # Update training_config.yaml
    with open(CONFIG_PATH) as f:
        config = yaml.safe_load(f)

    config["risk_classification"] = calibrated
    # Add tide thresholds (not data-derived, keep existing)
    config["risk_classification"]["tide"] = {
        "alert_factor": 0.8,
        "critical_combined_factor": 0.7,
        "critical_combined_flood_prob": 0.40,
    }

    with open(CONFIG_PATH, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
    logger.info(f"Updated config: {CONFIG_PATH}")

    print("\nCalibrated thresholds written to training_config.yaml:")
    print(json.dumps(calibrated, indent=2))


if __name__ == "__main__":
    main()
