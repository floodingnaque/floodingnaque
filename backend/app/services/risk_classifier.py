"""
Risk Level Classification Module
Converts model predictions to 3-level risk classification: Safe, Alert, Critical
Aligned with research objectives for Parañaque City flood detection system.

Thresholds are calibrated from 5,549 real DRRMO + PAGASA records and aligned
with the PAGASA Rainfall Warning System. See training_config.yaml
risk_classification section and reports/threshold_calibration_report.json.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Calibrated defaults — kept in sync with training_config.yaml risk_classification.
# Data provenance: v6 model on 1,660 flood / 3,889 non-flood records (2022-2025).
_thresholds: Dict[str, Any] = {
    "flood_probability": {"critical": 0.75, "alert": 0.40, "safe_max": 0.10},
    "precipitation": {"alert_min": 7.5, "alert_max": 30.0, "humidity_threshold": 82.0, "humidity_precip_min": 5.0},
    "rainfall_3h": {"critical": 65.0, "alert": 30.0},
    "tide": {"alert_factor": 0.8, "critical_combined_factor": 0.7, "critical_combined_flood_prob": 0.40},
}

_thresholds_loaded = False


def _auto_load_thresholds() -> None:
    """Attempt to load thresholds from training_config.yaml on first use."""
    global _thresholds_loaded
    if _thresholds_loaded:
        return
    _thresholds_loaded = True
    try:
        import yaml

        config_path = Path(__file__).resolve().parents[2] / "config" / "training_config.yaml"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            rc = config.get("risk_classification")
            if rc:
                load_thresholds(rc)
                logger.info("Risk thresholds loaded from %s", config_path)
    except Exception as exc:
        logger.warning("Could not auto-load risk thresholds from YAML, using defaults: %s", exc)


def load_thresholds(config: Optional[Dict[str, Any]] = None) -> None:
    """Load risk classification thresholds from a config dict (e.g. from training_config.yaml)."""
    global _thresholds
    if config is None:
        return
    for section in ("flood_probability", "precipitation", "rainfall_3h", "tide"):
        if section in config:
            _thresholds[section].update(config[section])


# Risk level definitions
RISK_LEVELS = {0: "Safe", 1: "Alert", 2: "Critical"}

RISK_LEVEL_COLORS = {"Safe": "#28a745", "Alert": "#ffc107", "Critical": "#dc3545"}  # Green  # Yellow/Orange  # Red

RISK_LEVEL_DESCRIPTIONS = {
    "Safe": "No immediate flood risk. Normal weather conditions.",
    "Alert": "Moderate flood risk. Monitor conditions closely. Prepare for possible flooding.",
    "Critical": "High flood risk. Immediate action required. Evacuate if necessary.",
}


def classify_risk_level(
    prediction: int,
    probability: Optional[Dict[str, float]] = None,
    precipitation: Optional[float] = None,
    humidity: Optional[float] = None,
    precipitation_3h: Optional[float] = None,
    tide_risk_factor: Optional[float] = None,
) -> Dict[str, any]:
    """
    Classify flood risk into 3 levels: Safe, Alert, Critical

    Classification Logic:
    - Safe (0): Binary prediction = 0 AND low probability of flood
    - Alert (1): Binary prediction = 0 BUT moderate probability OR moderate precipitation
    - Critical (2): Binary prediction = 1 OR high probability of flood

    Enhanced with 3-hour rainfall accumulation and tide risk factor.

    Args:
        prediction: Binary prediction (0 = no flood, 1 = flood)
        probability: Dict with 'no_flood' and 'flood' probabilities
        precipitation: Current precipitation value (mm)
        humidity: Current humidity value (%)
        precipitation_3h: 3-hour rolling rainfall accumulation (mm)
        tide_risk_factor: Tide risk factor 0-1

    Returns:
        dict: Risk classification with level, label, color, description, and confidence
    """

    # Auto-load YAML thresholds on first invocation
    _auto_load_thresholds()

    # Default risk level based on binary prediction
    if prediction == 1:
        # Flood predicted - check if Critical or Alert
        flood_prob = probability.get("flood", 0.5) if probability else 0.5

        fp = _thresholds["flood_probability"]
        if flood_prob >= fp["critical"]:
            risk_level = 2  # Critical
        elif flood_prob >= fp["alert"]:
            risk_level = 1  # Alert
        else:
            risk_level = 1  # Alert (conservative)
    else:
        # No flood predicted - check if Safe or Alert
        flood_prob = probability.get("flood", 0.0) if probability else 0.0

        fp = _thresholds["flood_probability"]
        pp = _thresholds["precipitation"]

        # Consider precipitation and humidity for Alert level
        is_alert_conditions = False
        if precipitation is not None:
            if pp["alert_min"] <= precipitation <= pp["alert_max"]:
                is_alert_conditions = True
        if humidity is not None:
            if humidity > pp["humidity_threshold"] and precipitation and precipitation > pp["humidity_precip_min"]:
                is_alert_conditions = True

        if flood_prob >= fp["safe_max"] or is_alert_conditions:
            risk_level = 1  # Alert
        else:
            risk_level = 0  # Safe

    # 3-hour rainfall accumulation override
    r3 = _thresholds["rainfall_3h"]
    if precipitation_3h is not None:
        if precipitation_3h >= r3["critical"] and risk_level < 2:
            risk_level = 2  # Critical - heavy sustained rainfall
        elif precipitation_3h >= r3["alert"] and risk_level < 1:
            risk_level = 1  # Alert - significant accumulation

    # Tide risk factor override
    td = _thresholds["tide"]
    if tide_risk_factor is not None:
        if tide_risk_factor >= td["alert_factor"] and risk_level < 1:
            risk_level = 1  # Alert - high tide risk
        # Combined high tide + moderate flood probability → escalate
        if (
            tide_risk_factor >= td["critical_combined_factor"]
            and probability
            and probability.get("flood", 0) >= td["critical_combined_flood_prob"]
            and risk_level < 2
        ):
            risk_level = 2  # Critical - compounding risk

    # Get risk label and metadata
    risk_label = RISK_LEVELS[risk_level]

    # Calculate confidence based on probability
    if probability:
        if risk_level == 0:
            confidence = probability.get("no_flood", 0.5)
        elif risk_level == 2:
            confidence = probability.get("flood", 0.5)
        else:
            # Alert level - use the higher probability
            confidence = max(probability.get("flood", 0.0), probability.get("no_flood", 0.0))
    else:
        confidence = 0.5

    return {
        "risk_level": risk_level,
        "risk_label": risk_label,
        "risk_color": RISK_LEVEL_COLORS[risk_label],
        "description": RISK_LEVEL_DESCRIPTIONS[risk_label],
        "confidence": round(confidence, 3),
        "binary_prediction": prediction,
        "probability": probability,
    }


def get_risk_thresholds() -> Dict[str, Dict[str, float]]:
    """
    Get risk classification thresholds for documentation and configuration.

    Returns:
        dict: Threshold definitions for each risk level
    """
    return {
        "Safe": {
            "flood_probability_max": _thresholds["flood_probability"]["safe_max"],
            "precipitation_max": _thresholds["precipitation"]["alert_min"],
            "description": "Normal conditions, minimal flood risk",
        },
        "Alert": {
            "flood_probability_min": _thresholds["flood_probability"]["safe_max"],
            "flood_probability_max": _thresholds["flood_probability"]["critical"],
            "precipitation_min": _thresholds["precipitation"]["alert_min"],
            "precipitation_max": _thresholds["precipitation"]["alert_max"],
            "description": "Moderate risk, monitor conditions",
        },
        "Critical": {
            "flood_probability_min": _thresholds["flood_probability"]["critical"],
            "precipitation_min": _thresholds["precipitation"]["alert_max"],
            "description": "High risk, immediate action required",
        },
    }


def format_alert_message(risk_data: Dict, location: Optional[str] = None) -> str:
    """
    Format alert message for SMS/notification delivery.

    Args:
        risk_data: Risk classification data from classify_risk_level()
        location: Optional location name (e.g., "Parañaque City")

    Returns:
        str: Formatted alert message
    """
    location_str = f" in {location}" if location else ""
    risk_label = risk_data["risk_label"]
    description = risk_data["description"]
    confidence = risk_data["confidence"]

    message = f"FLOOD ALERT{location_str}\n"
    message += f"Risk Level: {risk_label}\n"
    message += f"{description}\n"
    message += f"Confidence: {confidence*100:.1f}%"

    if risk_label == "Critical":
        message += "\n\n⚠️ TAKE IMMEDIATE ACTION"
    elif risk_label == "Alert":
        message += "\n\n⚠️ MONITOR CONDITIONS"

    return message
