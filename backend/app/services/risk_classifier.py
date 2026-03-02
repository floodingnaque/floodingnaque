"""
Risk Level Classification Module
Converts model predictions to 3-level risk classification: Safe, Alert, Critical
Aligned with research objectives for Parañaque City flood detection system.
"""

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

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

    # Default risk level based on binary prediction
    if prediction == 1:
        # Flood predicted - check if Critical or Alert
        flood_prob = probability.get("flood", 0.5) if probability else 0.5

        # Use probability thresholds
        if flood_prob >= 0.75:
            risk_level = 2  # Critical
        elif flood_prob >= 0.50:
            risk_level = 1  # Alert
        else:
            risk_level = 1  # Alert (conservative)
    else:
        # No flood predicted - check if Safe or Alert
        flood_prob = probability.get("flood", 0.0) if probability else 0.0

        # Consider precipitation and humidity for Alert level
        is_alert_conditions = False
        if precipitation is not None:
            # Moderate precipitation (10-30mm) suggests Alert
            if 10.0 <= precipitation <= 30.0:
                is_alert_conditions = True
        if humidity is not None:
            # High humidity (>85%) with some precipitation suggests Alert
            if humidity > 85.0 and precipitation and precipitation > 5.0:
                is_alert_conditions = True

        if flood_prob >= 0.30 or is_alert_conditions:
            risk_level = 1  # Alert
        else:
            risk_level = 0  # Safe

    # 3-hour rainfall accumulation override
    if precipitation_3h is not None:
        if precipitation_3h >= 80.0 and risk_level < 2:
            risk_level = 2  # Critical - heavy sustained rainfall
        elif precipitation_3h >= 50.0 and risk_level < 1:
            risk_level = 1  # Alert - significant accumulation

    # Tide risk factor override
    if tide_risk_factor is not None:
        if tide_risk_factor >= 0.8 and risk_level < 1:
            risk_level = 1  # Alert - high tide risk
        # Combined high tide + moderate flood probability → escalate
        if (
            tide_risk_factor >= 0.7
            and probability
            and probability.get("flood", 0) >= 0.40
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
            "flood_probability_max": 0.30,
            "precipitation_max": 10.0,
            "description": "Normal conditions, minimal flood risk",
        },
        "Alert": {
            "flood_probability_min": 0.30,
            "flood_probability_max": 0.75,
            "precipitation_min": 10.0,
            "precipitation_max": 30.0,
            "description": "Moderate risk, monitor conditions",
        },
        "Critical": {
            "flood_probability_min": 0.75,
            "precipitation_min": 30.0,
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
