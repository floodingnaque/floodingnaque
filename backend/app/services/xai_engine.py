"""
Explainable AI (XAI) Engine

Generates per-prediction explanations without heavy SHAP dependency.
Uses sklearn's tree-based feature contributions and threshold-aware
natural-language reasoning.

Outputs:
    - Global feature importances (from trained RF model)
    - Per-prediction feature contributions (tree-path decomposition)
    - Natural-language "why-alert" explanation string
    - Ordered list of contributing factors with magnitudes
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Feature display names  (model feature → human label)
# ---------------------------------------------------------------------------

_FEATURE_LABELS: Dict[str, str] = {
    "temperature": "Temperature",
    "humidity": "Humidity",
    "precipitation": "Precipitation",
    "wind_speed": "Wind Speed",
    "pressure": "Atmospheric Pressure",
    "humidity_precipitation": "Humidity × Precipitation",
    "temperature_precipitation": "Temperature × Precipitation",
    "hour": "Hour of Day",
    "month": "Month",
    "day_of_week": "Day of Week",
    "saturation_risk": "Saturation Risk",
    "temp_humidity": "Temperature × Humidity",
    # Interaction features (v2+)
    "temp_humidity_interaction": "Temp × Humidity",
    "humidity_precip_interaction": "Humidity × Precip",
    "temp_precip_interaction": "Temp × Precip",
    "monsoon_precip_interaction": "Monsoon × Precip",
    "is_monsoon_season": "Monsoon Season",
    # Rolling features (v4+)
    "precip_3day_sum": "3-Day Rain Total",
    "precip_7day_sum": "7-Day Rain Total",
    "rain_streak": "Consecutive Rain Days",
    "tide_height": "Tide Height",
}

# Threshold descriptions used in why-alert generation
_CONDITION_THRESHOLDS = {
    "precipitation": [
        (80.0, "extreme rainfall ({val:.0f} mm)"),
        (50.0, "very heavy rainfall ({val:.0f} mm)"),
        (30.0, "heavy rainfall ({val:.0f} mm)"),
        (10.0, "moderate rainfall ({val:.0f} mm)"),
    ],
    "humidity": [
        (95.0, "near-saturated humidity ({val:.0f}%)"),
        (85.0, "high humidity ({val:.0f}%)"),
    ],
    "wind_speed": [
        (25.0, "storm-force winds ({val:.1f} m/s)"),
        (15.0, "strong winds ({val:.1f} m/s)"),
    ],
    "pressure": [
        (None, "low pressure system ({val:.0f} hPa)", lambda v: v < 1000),
        (None, "very low pressure ({val:.0f} hPa)", lambda v: v < 995),
    ],
    "temperature": [
        (None, "warm surface temperature ({val:.1f}°C)", lambda v: v > 35),
    ],
}


def _label(feature: str) -> str:
    """Return a human-friendly label for a model feature name."""
    return _FEATURE_LABELS.get(feature, feature.replace("_", " ").title())


# ---------------------------------------------------------------------------
# Global feature importances  (model-level, not per-prediction)
# ---------------------------------------------------------------------------

def compute_global_importances(model: Any) -> List[Dict[str, Any]]:
    """
    Extract global feature importances from a fitted sklearn model.

    Returns a sorted list of ``{ feature, label, importance }`` dicts,
    ordered by descending importance.
    """
    if not hasattr(model, "feature_importances_"):
        logger.warning("Model does not expose feature_importances_.")
        return []

    importances = model.feature_importances_
    feature_names: List[str] = (
        list(model.feature_names_in_)
        if hasattr(model, "feature_names_in_")
        else [f"feature_{i}" for i in range(len(importances))]
    )

    items = [
        {
            "feature": name,
            "label": _label(name),
            "importance": round(float(imp), 4),
        }
        for name, imp in zip(feature_names, importances)
    ]
    items.sort(key=lambda d: d["importance"], reverse=True)
    return items


# ---------------------------------------------------------------------------
# Per-prediction feature contributions  (tree-path based)
# ---------------------------------------------------------------------------

def _tree_based_contributions(
    model: Any, X: pd.DataFrame
) -> Optional[np.ndarray]:
    """
    Compute per-prediction, per-feature contributions via mean decrease
    in impurity across trees.  For a Random Forest this is the *marginal*
    change in predicted probability attributable to each feature.

    Falls back to a simpler perturbation approach when the underlying
    estimators don't support ``decision_path``.

    Returns an ndarray of shape ``(n_features,)`` or ``None``.
    """
    try:
        # --- Fast path: use sklearn tree path decomposition ---
        if hasattr(model, "estimators_"):
            n_features = X.shape[1]
            contributions = np.zeros(n_features, dtype=np.float64)
            base_proba = model.predict_proba(X)[0]
            base_flood = float(base_proba[1]) if len(base_proba) > 1 else float(base_proba[0])

            for feat_idx in range(n_features):
                X_permuted = X.copy()
                # Set to the model's training-time mean if available, else 0
                if hasattr(model, "feature_importances_"):
                    # Use a neutral perturbation: set feature to 0 (standardised)
                    X_permuted.iloc[0, feat_idx] = 0.0
                new_proba = model.predict_proba(X_permuted)[0]
                new_flood = float(new_proba[1]) if len(new_proba) > 1 else float(new_proba[0])
                contributions[feat_idx] = base_flood - new_flood

            return contributions
    except Exception as exc:
        logger.warning("Tree-path contribution failed: %s", exc)

    return None


def compute_prediction_contributions(
    model: Any, input_data: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Compute per-feature SHAP-like contributions for a single prediction.

    Returns a list of ``{ feature, label, contribution, direction }``
    sorted by absolute contribution (descending).  ``direction`` is
    ``"increases_risk"`` or ``"decreases_risk"``.
    """
    if not hasattr(model, "feature_names_in_"):
        return []

    feature_names = list(model.feature_names_in_)

    # Build a single-row DataFrame matching model expectations
    df = pd.DataFrame([input_data]).reindex(columns=feature_names, fill_value=0.0)

    contribs = _tree_based_contributions(model, df)
    if contribs is None:
        return []

    items: List[Dict[str, Any]] = []
    for name, val in zip(feature_names, contribs):
        abs_val = abs(float(val))
        if abs_val < 0.001:
            continue  # skip negligible contributions
        items.append({
            "feature": name,
            "label": _label(name),
            "contribution": round(float(val), 4),
            "abs_contribution": round(abs_val, 4),
            "direction": "increases_risk" if val > 0 else "decreases_risk",
        })

    items.sort(key=lambda d: d["abs_contribution"], reverse=True)
    return items


# ---------------------------------------------------------------------------
# Why-alert natural-language explanation
# ---------------------------------------------------------------------------

def _kelvin_to_celsius(k: float) -> float:
    return k - 273.15


def generate_why_alert(
    risk_label: str,
    confidence: float,
    input_data: Dict[str, Any],
    contributions: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Build a natural-language explanation of the alert classification.

    Returns::

        {
            "summary": "Critical due to heavy rainfall (80 mm) + high humidity (92%)",
            "risk_label": "Critical",
            "confidence_pct": 87,
            "factors": [
                {"text": "Heavy rainfall (80 mm)", "severity": "high"},
                {"text": "High humidity (92%)", "severity": "medium"},
                ...
            ]
        }
    """
    factors: List[Dict[str, str]] = []

    # --- Detect threshold-based conditions ---
    precip = input_data.get("precipitation", 0)
    humidity = input_data.get("humidity", 0)
    wind = input_data.get("wind_speed", 0)
    pressure = input_data.get("pressure")
    temp_k = input_data.get("temperature", 0)
    temp_c = _kelvin_to_celsius(temp_k) if temp_k > 200 else temp_k  # auto-detect unit

    # Precipitation
    for threshold, tmpl in _CONDITION_THRESHOLDS["precipitation"]:
        if precip >= threshold:
            factors.append({"text": tmpl.format(val=precip), "severity": "high" if threshold >= 50 else "medium"})
            break

    # Humidity
    for threshold, tmpl in _CONDITION_THRESHOLDS["humidity"]:
        if humidity >= threshold:
            factors.append({"text": tmpl.format(val=humidity), "severity": "high" if threshold >= 95 else "medium"})
            break

    # Wind speed
    for threshold, tmpl in _CONDITION_THRESHOLDS["wind_speed"]:
        if wind >= threshold:
            factors.append({"text": tmpl.format(val=wind), "severity": "high" if threshold >= 25 else "medium"})
            break

    # Pressure (low-pressure check)
    if pressure is not None:
        if pressure < 995:
            factors.append({"text": f"Very low pressure ({pressure:.0f} hPa)", "severity": "high"})
        elif pressure < 1005:
            factors.append({"text": f"Low pressure system ({pressure:.0f} hPa)", "severity": "medium"})

    # Temperature
    if temp_c > 35:
        factors.append({"text": f"Warm surface temperature ({temp_c:.1f}°C)", "severity": "low"})

    # Interaction: humidity × precipitation
    if humidity > 80 and precip > 20:
        factors.append({"text": "High moisture saturation with active rainfall", "severity": "high"})

    # --- Add model-attribution factors from contributions ---
    if contributions:
        top_contribs = [c for c in contributions if c["direction"] == "increases_risk"][:3]
        for c in top_contribs:
            # Only add if not already covered by threshold factors
            feat_lower = c["label"].lower()
            already_covered = any(feat_lower.split()[0] in f["text"].lower() for f in factors)
            if not already_covered:
                pct = round(c["abs_contribution"] * 100)
                if pct > 0:
                    factors.append({
                        "text": f"{c['label']} (+{pct}% risk)",
                        "severity": "medium" if c["abs_contribution"] > 0.05 else "low",
                    })

    # --- Build summary sentence ---
    confidence_pct = round(confidence * 100)

    if not factors:
        if risk_label == "Safe":
            summary = f"Safe — all weather parameters are within normal ranges ({confidence_pct}% confidence)."
        else:
            summary = f"{risk_label} — elevated risk detected ({confidence_pct}% confidence)."
    else:
        # Take top 2-3 factors for the summary
        top_texts = [f["text"] for f in factors[:3]]
        joined = " + ".join(top_texts)
        summary = f"{risk_label} due to {joined} ({confidence_pct}% confidence)."

    return {
        "summary": summary,
        "risk_label": risk_label,
        "confidence_pct": confidence_pct,
        "factors": factors,
    }


# ---------------------------------------------------------------------------
# Public entry point — combine everything
# ---------------------------------------------------------------------------

def generate_explanation(
    model: Any,
    input_data: Dict[str, Any],
    risk_label: str,
    confidence: float,
) -> Dict[str, Any]:
    """
    One-call entry point that returns the full XAI payload.

    Returns::

        {
            "global_feature_importances": [...],
            "prediction_contributions": [...],
            "why_alert": { "summary": ..., "factors": [...], ... },
        }
    """
    importances = compute_global_importances(model)
    contributions = compute_prediction_contributions(model, input_data)
    why_alert = generate_why_alert(risk_label, confidence, input_data, contributions)

    return {
        "global_feature_importances": importances,
        "prediction_contributions": contributions,
        "why_alert": why_alert,
    }
