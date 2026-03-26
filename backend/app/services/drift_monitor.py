"""
Model Drift Monitor for Floodingnaque.

Exports PSI (Population Stability Index) per monitored feature as
Prometheus gauges and logs drift events.  Runs as a scheduled job
alongside the existing auto-retrain pipeline.

Drift thresholds:
    PSI < 0.10  →  No change (stable)
    PSI 0.10–0.20  →  Warning (moderate shift)
    PSI ≥ 0.20  →  Critical (significant shift, triggers retrain)
"""

import logging
import time
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Prometheus gauges - lazily registered so the module can be imported
# even when prometheus_client is not installed.
_drift_gauges_registered = False

# Features monitored for distribution shift
MONITORED_FEATURES = [
    "temperature",
    "humidity",
    "precipitation",
    "precip_3day_sum",
]

PSI_WARNING = 0.10
PSI_CRITICAL = 0.20


def _register_drift_gauges() -> None:
    """Register drift-specific Prometheus gauges (idempotent)."""
    global _drift_gauges_registered
    if _drift_gauges_registered:
        return
    try:
        from prometheus_client import Gauge

        # Per-feature PSI gauge
        _register_drift_gauges.psi_gauge = Gauge(
            "floodingnaque_drift_psi",
            "Population Stability Index per feature",
            ["feature"],
        )

        # Overall drift status: 0=stable, 1=warning, 2=critical
        _register_drift_gauges.drift_status = Gauge(
            "floodingnaque_drift_status",
            "Overall drift status (0=stable, 1=warning, 2=critical)",
        )

        # Timestamp of last drift check
        _register_drift_gauges.last_check = Gauge(
            "floodingnaque_drift_last_check_timestamp",
            "Unix timestamp of last drift check",
        )

        _drift_gauges_registered = True
        logger.debug("Drift Prometheus gauges registered")
    except ImportError:
        logger.debug("prometheus_client not available, drift gauges skipped")


def _set_psi_gauge(feature: str, value: float) -> None:
    """Set PSI gauge for a feature if Prometheus is available."""
    if _drift_gauges_registered and hasattr(_register_drift_gauges, "psi_gauge"):
        _register_drift_gauges.psi_gauge.labels(feature=feature).set(round(value, 4))


def _set_drift_status(status: int) -> None:
    """Set overall drift status gauge."""
    if _drift_gauges_registered and hasattr(_register_drift_gauges, "drift_status"):
        _register_drift_gauges.drift_status.set(status)


def _set_last_check() -> None:
    """Set last check timestamp."""
    if _drift_gauges_registered and hasattr(_register_drift_gauges, "last_check"):
        _register_drift_gauges.last_check.set(time.time())


def compute_psi(reference: list, current: list, n_bins: int = 10) -> float:
    """Compute Population Stability Index between two distributions.

    PSI < 0.10: No change
    PSI 0.10–0.20: Warning
    PSI ≥ 0.20: Significant shift

    Args:
        reference: Reference distribution values.
        current: Current distribution values.
        n_bins: Number of histogram bins.

    Returns:
        PSI value (float). Returns 0.0 on degenerate inputs.
    """
    import numpy as np

    ref = np.array([x for x in reference if x is not None and not np.isnan(x)])
    cur = np.array([x for x in current if x is not None and not np.isnan(x)])

    if len(ref) < n_bins or len(cur) < n_bins:
        return 0.0

    # Use reference quantiles for bin edges (consistent binning)
    breakpoints = np.percentile(ref, np.linspace(0, 100, n_bins + 1))
    breakpoints[0] = -np.inf
    breakpoints[-1] = np.inf
    # Remove duplicate edges
    breakpoints = np.unique(breakpoints)

    ref_counts = np.histogram(ref, bins=breakpoints)[0].astype(float)
    cur_counts = np.histogram(cur, bins=breakpoints)[0].astype(float)

    # Normalise to proportions with epsilon to avoid division by zero
    eps = 1e-6
    ref_pct = ref_counts / ref_counts.sum() + eps
    cur_pct = cur_counts / cur_counts.sum() + eps

    psi = float(np.sum((cur_pct - ref_pct) * np.log(cur_pct / ref_pct)))
    return max(psi, 0.0)


def check_drift(
    reference_data: Optional[Dict[str, list]] = None,
    current_data: Optional[Dict[str, list]] = None,
    features: Optional[List[str]] = None,
) -> Dict:
    """Run drift detection and export results to Prometheus.

    If reference_data / current_data are not provided, the function
    loads the training reference from the latest model metadata and
    compares against recent predictions stored in the database.

    Args:
        reference_data: Dict mapping feature names to reference values.
        current_data: Dict mapping feature names to current values.
        features: Features to monitor (defaults to MONITORED_FEATURES).

    Returns:
        Dict with per-feature PSI values, overall status, and drifted features.
    """
    _register_drift_gauges()

    monitored = features or MONITORED_FEATURES

    # Load data lazily if not provided
    if reference_data is None or current_data is None:
        reference_data, current_data = _load_drift_data(monitored)

    ref_data = reference_data or {}
    cur_data = current_data or {}

    psi_values: Dict[str, float] = {}
    drifted_features: List[str] = []
    overall_status = 0  # 0=stable

    for feat in monitored:
        ref_vals = ref_data.get(feat, [])
        cur_vals = cur_data.get(feat, [])

        if not ref_vals or not cur_vals:
            logger.debug("Skipping drift check for '%s': insufficient data", feat)
            continue

        psi = compute_psi(ref_vals, cur_vals)
        psi_values[feat] = psi
        _set_psi_gauge(feat, psi)

        if psi >= PSI_CRITICAL:
            drifted_features.append(feat)
            overall_status = max(overall_status, 2)
            logger.warning("DRIFT CRITICAL: feature='%s' PSI=%.4f (threshold=%.2f)", feat, psi, PSI_CRITICAL)
        elif psi >= PSI_WARNING:
            overall_status = max(overall_status, 1)
            logger.info("DRIFT WARNING: feature='%s' PSI=%.4f (threshold=%.2f)", feat, psi, PSI_WARNING)
        else:
            logger.debug("Drift stable: feature='%s' PSI=%.4f", feat, psi)

    _set_drift_status(overall_status)
    _set_last_check()

    status_label = {0: "stable", 1: "warning", 2: "critical"}.get(overall_status, "unknown")
    logger.info(
        "Drift check complete: status=%s, features_checked=%d, drifted=%d",
        status_label,
        len(psi_values),
        len(drifted_features),
    )

    return {
        "drift_detected": overall_status >= 2,
        "status": status_label,
        "psi_values": psi_values,
        "drifted_features": drifted_features,
        "features_checked": len(psi_values),
        "thresholds": {"warning": PSI_WARNING, "critical": PSI_CRITICAL},
    }


def _load_drift_data(features: List[str]) -> tuple:
    """Load reference and current data from model metadata and recent predictions.

    Reference data: Training data feature distributions stored in model metadata.
    Current data: Recent weather observations from the database (last 7 days).

    Returns:
        Tuple of (reference_data, current_data) dicts.
    """
    import json
    import os

    reference_data: Dict[str, list] = {}
    current_data: Dict[str, list] = {}

    # --- Reference: load from model metadata ---
    models_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "models")
    metadata_files = (
        sorted(
            [f for f in os.listdir(models_dir) if f.endswith("_metadata.json")],
            reverse=True,
        )
        if os.path.isdir(models_dir)
        else []
    )

    if metadata_files:
        with open(os.path.join(models_dir, metadata_files[0])) as f:
            metadata = json.load(f)

        ref_stats = metadata.get("feature_distributions", {})
        if ref_stats:
            for feat in features:
                if feat in ref_stats:
                    reference_data[feat] = ref_stats[feat]

    # --- Current: load from recent weather observations ---
    try:
        from datetime import datetime, timedelta, timezone

        from app.models.db import WeatherData, get_db_session
        from sqlalchemy import desc

        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        with get_db_session() as session:
            rows = (
                session.query(WeatherData)
                .filter(WeatherData.created_at >= cutoff)
                .order_by(desc(WeatherData.created_at))
                .limit(500)
                .all()
            )
            for feat in features:
                current_data[feat] = [getattr(row, feat, None) for row in rows if getattr(row, feat, None) is not None]
    except Exception as e:
        logger.warning("Could not load current data for drift check: %s", e)

    return reference_data, current_data
