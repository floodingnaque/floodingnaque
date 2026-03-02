"""
Smart Alert Evaluator Module.

Provides intelligent alert logic beyond basic risk classification:
- 3-hour rolling rainfall accumulation tracking
- Composite confidence scoring (model + data quality)
- False alarm reduction via confidence thresholds
- Time-based alert escalation (Alert → Critical after 30 min persistence)
- Cooldown / deduplication to prevent alert spam
- De-escalation after sustained safe conditions

Designed for Parañaque City flood detection system.
"""

import json
import logging
import os
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration (overridable via environment variables)
# ---------------------------------------------------------------------------

# Minimum composite confidence to allow Alert-level alerts through.
# Below this, only Critical alerts are dispatched (false-alarm reduction).
CONFIDENCE_THRESHOLD = float(os.getenv("SMART_ALERT_CONFIDENCE_THRESHOLD", "0.45"))

# 3-hour rolling rainfall thresholds (mm)
RAINFALL_3H_ALERT_THRESHOLD = float(os.getenv("RAINFALL_3H_ALERT_MM", "50.0"))
RAINFALL_3H_CRITICAL_THRESHOLD = float(os.getenv("RAINFALL_3H_CRITICAL_MM", "80.0"))

# Time-based escalation: Alert persists for this many minutes → auto-escalate
ESCALATION_MINUTES = int(os.getenv("ALERT_ESCALATION_MINUTES", "30"))

# De-escalation: Safe for this many minutes → RESOLVED
DEESCALATION_MINUTES = int(os.getenv("ALERT_DEESCALATION_MINUTES", "15"))

# Cooldown: suppress duplicate Critical alerts for this many seconds
ALERT_COOLDOWN_SECONDS = int(os.getenv("ALERT_COOLDOWN_SECONDS", "600"))


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

class EscalationState(str, Enum):
    """Alert lifecycle states."""
    NONE = "none"
    WATCH = "watch"
    ALERT = "alert"
    CRITICAL = "critical"
    RESOLVED = "resolved"


@dataclass
class SmartAlertDecision:
    """Result of the smart alert evaluation pipeline."""

    risk_level: int  # 0, 1, or 2
    risk_label: str  # Safe, Alert, Critical
    confidence: float  # Composite confidence 0-1
    rainfall_3h: float  # Rolling 3-hour accumulation (mm)
    was_suppressed: bool  # True → alert was suppressed (false-alarm reduction)
    escalation_state: str  # EscalationState value
    escalation_reason: Optional[str]  # e.g. "persisted_30min", "rainfall_critical"
    contributing_factors: List[str] = field(default_factory=list)
    original_risk_level: int = 0  # Before smart adjustments

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serialisable dictionary."""
        return asdict(self)


@dataclass
class _LocationAlertState:
    """Internal per-location tracker for escalation state machine."""

    current_level: int = 0
    escalation_state: EscalationState = EscalationState.NONE
    alert_started_at: Optional[datetime] = None
    last_evaluated_at: Optional[datetime] = None
    last_critical_sent_at: Optional[datetime] = None
    consecutive_safe_since: Optional[datetime] = None
    consecutive_alert_count: int = 0
    rolling_rainfall_3h: float = 0.0


# ---------------------------------------------------------------------------
# SmartAlertEvaluator singleton
# ---------------------------------------------------------------------------

class SmartAlertEvaluator:
    """
    Evaluates weather + prediction data to produce smart alert decisions.

    Thread-safe singleton with in-memory state per location.
    For production multi-worker deployment, state should be backed by Redis.
    """

    _instance: Optional["SmartAlertEvaluator"] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._state_lock = threading.Lock()
        # Per-location state: location_name → _LocationAlertState
        self._location_states: Dict[str, _LocationAlertState] = {}

    @classmethod
    def get_instance(cls) -> "SmartAlertEvaluator":
        """Get or create the singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton (for testing)."""
        cls._instance = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def evaluate(
        self,
        risk_classification: Dict[str, Any],
        weather_data: Optional[Dict[str, Any]] = None,
        data_quality: Optional[float] = None,
        location: str = "Parañaque City",
    ) -> SmartAlertDecision:
        """
        Run the full smart-alert evaluation pipeline.

        Args:
            risk_classification: Output from ``classify_risk_level()`` —
                must contain ``risk_level``, ``risk_label``, ``confidence``.
            weather_data: Dict with optional keys ``precipitation``,
                ``precipitation_3h``, ``humidity``, ``tide_risk_factor``.
            data_quality: Data quality score 0-1 from WeatherData model.
            location: Location name for per-location state tracking.

        Returns:
            SmartAlertDecision with final risk level and metadata.
        """
        now = datetime.now(timezone.utc)
        weather_data = weather_data or {}

        original_level = risk_classification.get("risk_level", 0)
        risk_level = original_level
        risk_label = risk_classification.get("risk_label", "Safe")
        model_confidence = risk_classification.get("confidence", 0.5)

        # --- Step 1: Compute 3-hour rolling rainfall accumulation ---------
        rainfall_3h = self._compute_rainfall_3h(weather_data, location)

        # --- Step 2: Compute composite confidence -------------------------
        composite_confidence = self._compute_composite_confidence(
            model_confidence, data_quality
        )

        # --- Step 3: Detect contributing factors --------------------------
        factors = self._detect_contributing_factors(
            weather_data, risk_level, rainfall_3h
        )

        # --- Step 4: Apply rainfall accumulation thresholds ---------------
        risk_level, risk_label, rainfall_reason = self._apply_rainfall_thresholds(
            risk_level, risk_label, rainfall_3h
        )
        if rainfall_reason:
            factors.append(rainfall_reason)

        # --- Step 5: False alarm reduction --------------------------------
        was_suppressed = False
        if risk_level == 1 and composite_confidence < CONFIDENCE_THRESHOLD:
            was_suppressed = True
            factors.append(
                f"Suppressed: confidence {composite_confidence:.0%} < "
                f"threshold {CONFIDENCE_THRESHOLD:.0%}"
            )
            logger.info(
                "Smart alert SUPPRESSED for %s: confidence %.3f < %.3f",
                location, composite_confidence, CONFIDENCE_THRESHOLD,
            )

        # --- Step 6: Escalation / de-escalation state machine -------------
        escalation_state, escalation_reason = self._update_escalation(
            location, risk_level, now
        )

        # Apply escalation override
        if (
            escalation_state == EscalationState.CRITICAL
            and risk_level < 2
            and escalation_reason == "persisted_30min"
        ):
            risk_level = 2
            risk_label = "Critical"
            factors.append(f"Auto-escalated: Alert persisted ≥{ESCALATION_MINUTES} min")

        # --- Step 7: Cooldown check (for Critical) ------------------------
        if risk_level == 2 and not was_suppressed:
            if self._is_in_cooldown(location, now):
                was_suppressed = True
                factors.append(
                    f"Cooldown: duplicate Critical within {ALERT_COOLDOWN_SECONDS}s"
                )
                logger.info(
                    "Smart alert COOLDOWN for %s: duplicate Critical suppressed",
                    location,
                )
            else:
                self._mark_critical_sent(location, now)

        return SmartAlertDecision(
            risk_level=risk_level,
            risk_label=risk_label,
            confidence=round(composite_confidence, 3),
            rainfall_3h=round(rainfall_3h, 1),
            was_suppressed=was_suppressed,
            escalation_state=escalation_state.value,
            escalation_reason=escalation_reason,
            contributing_factors=factors,
            original_risk_level=original_level,
        )

    def get_location_state(self, location: str) -> Optional[Dict[str, Any]]:
        """Return a snapshot of the internal state for a location (debug/API)."""
        with self._state_lock:
            state = self._location_states.get(location)
            if not state:
                return None
            return {
                "current_level": state.current_level,
                "escalation_state": state.escalation_state.value,
                "alert_started_at": (
                    state.alert_started_at.isoformat() if state.alert_started_at else None
                ),
                "last_evaluated_at": (
                    state.last_evaluated_at.isoformat() if state.last_evaluated_at else None
                ),
                "consecutive_alert_count": state.consecutive_alert_count,
                "rolling_rainfall_3h": state.rolling_rainfall_3h,
            }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_or_create_state(self, location: str) -> _LocationAlertState:
        with self._state_lock:
            if location not in self._location_states:
                self._location_states[location] = _LocationAlertState()
            return self._location_states[location]

    def _compute_rainfall_3h(
        self, weather_data: Dict[str, Any], location: str
    ) -> float:
        """
        Compute 3-hour rolling rainfall accumulation.

        Prefers the ``precipitation_3h`` value from satellite sources when
        available, otherwise falls back to querying the last 3 hours of
        WeatherData rows from the database.
        """
        # Fast path: satellite-derived 3h accumulation already present
        precip_3h = weather_data.get("precipitation_3h")
        if precip_3h is not None and precip_3h > 0:
            state = self._get_or_create_state(location)
            state.rolling_rainfall_3h = float(precip_3h)
            return float(precip_3h)

        # Slow path: query DB for the last 3 hours of station data
        try:
            from app.models.db import WeatherData, get_db_session
            from sqlalchemy import func

            cutoff = datetime.now(timezone.utc) - timedelta(hours=3)
            with get_db_session() as session:
                result = (
                    session.query(func.coalesce(func.sum(WeatherData.precipitation), 0.0))
                    .filter(WeatherData.timestamp >= cutoff)
                    .scalar()
                )
                total = float(result) if result else 0.0
        except Exception as exc:
            logger.warning("Failed to query 3h rainfall from DB: %s", exc)
            # Fallback: use current precipitation as rough approximation
            total = float(weather_data.get("precipitation", 0.0))

        state = self._get_or_create_state(location)
        state.rolling_rainfall_3h = total
        return total

    def _compute_composite_confidence(
        self,
        model_confidence: float,
        data_quality: Optional[float],
    ) -> float:
        """
        Composite confidence = weighted blend of model confidence and data
        quality score.

        Weights: model 70%, data quality 30%.
        If data_quality is unavailable, falls back to model confidence alone.
        """
        if data_quality is not None and 0.0 <= data_quality <= 1.0:
            return (model_confidence * 0.7) + (data_quality * 0.3)
        return model_confidence

    def _detect_contributing_factors(
        self,
        weather_data: Dict[str, Any],
        risk_level: int,
        rainfall_3h: float,
    ) -> List[str]:
        """Detect environmental factors contributing to the alert."""
        factors: List[str] = []

        precip = weather_data.get("precipitation", 0)
        if precip and precip > 30:
            factors.append(f"Heavy rainfall ({precip:.1f} mm/h)")
        elif precip and precip > 10:
            factors.append(f"Moderate rainfall ({precip:.1f} mm/h)")

        if rainfall_3h >= RAINFALL_3H_ALERT_THRESHOLD:
            factors.append(f"High 3h accumulation ({rainfall_3h:.1f} mm)")

        humidity = weather_data.get("humidity")
        if humidity and humidity > 85:
            factors.append(f"High humidity ({humidity:.0f}%)")

        tide_risk = weather_data.get("tide_risk_factor")
        if tide_risk and tide_risk > 0.6:
            factors.append(f"Elevated tide risk ({tide_risk:.2f})")

        tide_height = weather_data.get("tide_height")
        if tide_height and tide_height > 1.5:
            factors.append(f"High tide ({tide_height:.2f} m)")

        wind_speed = weather_data.get("wind_speed")
        if wind_speed and wind_speed > 20:
            factors.append(f"Strong winds ({wind_speed:.1f} m/s)")

        return factors

    def _apply_rainfall_thresholds(
        self, risk_level: int, risk_label: str, rainfall_3h: float
    ) -> tuple:
        """
        Force-upgrade risk level based on 3-hour rainfall accumulation
        thresholds, independent of ML model output.

        Returns (new_risk_level, new_risk_label, reason_or_None).
        """
        reason = None
        if rainfall_3h >= RAINFALL_3H_CRITICAL_THRESHOLD and risk_level < 2:
            risk_level = 2
            risk_label = "Critical"
            reason = f"Rainfall ≥{RAINFALL_3H_CRITICAL_THRESHOLD:.0f} mm/3h → Critical"
        elif rainfall_3h >= RAINFALL_3H_ALERT_THRESHOLD and risk_level < 1:
            risk_level = 1
            risk_label = "Alert"
            reason = f"Rainfall ≥{RAINFALL_3H_ALERT_THRESHOLD:.0f} mm/3h → Alert"
        return risk_level, risk_label, reason

    def _update_escalation(
        self, location: str, risk_level: int, now: datetime
    ) -> tuple:
        """
        Update the escalation state machine for a location.

        Returns (EscalationState, reason_or_None).
        """
        state = self._get_or_create_state(location)
        state.last_evaluated_at = now
        reason: Optional[str] = None

        if risk_level >= 2:
            # Already Critical — record it
            state.current_level = 2
            state.escalation_state = EscalationState.CRITICAL
            state.consecutive_safe_since = None
            state.consecutive_alert_count += 1
            reason = "direct_critical"
            return state.escalation_state, reason

        if risk_level == 1:
            # Alert level — check for time-based escalation
            state.consecutive_safe_since = None

            if state.escalation_state in (
                EscalationState.NONE,
                EscalationState.RESOLVED,
                EscalationState.WATCH,
            ):
                # Transition: → ALERT, start the timer
                state.escalation_state = EscalationState.ALERT
                state.alert_started_at = now
                state.consecutive_alert_count = 1
                state.current_level = 1
                return state.escalation_state, None

            if state.escalation_state == EscalationState.ALERT:
                state.consecutive_alert_count += 1
                # Check if we've been in Alert long enough to escalate
                if state.alert_started_at:
                    elapsed = (now - state.alert_started_at).total_seconds() / 60.0
                    if elapsed >= ESCALATION_MINUTES:
                        state.escalation_state = EscalationState.CRITICAL
                        state.current_level = 2
                        reason = "persisted_30min"
                        logger.warning(
                            "Alert ESCALATED to Critical for %s: "
                            "persisted %.0f min (threshold=%d min)",
                            location, elapsed, ESCALATION_MINUTES,
                        )
                        return state.escalation_state, reason
                return state.escalation_state, None

            # Already CRITICAL via escalation — maintain
            if state.escalation_state == EscalationState.CRITICAL:
                state.consecutive_alert_count += 1
                return state.escalation_state, "sustained_critical"

        # risk_level == 0 → Safe
        if risk_level == 0:
            state.consecutive_alert_count = 0

            if state.escalation_state in (
                EscalationState.ALERT,
                EscalationState.CRITICAL,
            ):
                # Start de-escalation timer
                if state.consecutive_safe_since is None:
                    state.consecutive_safe_since = now
                    state.escalation_state = EscalationState.WATCH
                    state.current_level = 0
                    return state.escalation_state, "de-escalating"

            if state.escalation_state == EscalationState.WATCH:
                if state.consecutive_safe_since:
                    safe_minutes = (
                        now - state.consecutive_safe_since
                    ).total_seconds() / 60.0
                    if safe_minutes >= DEESCALATION_MINUTES:
                        state.escalation_state = EscalationState.RESOLVED
                        state.current_level = 0
                        state.alert_started_at = None
                        state.consecutive_safe_since = None
                        reason = "de-escalated"
                        logger.info(
                            "Alert RESOLVED for %s after %.0f min of safe conditions",
                            location, safe_minutes,
                        )
                        return state.escalation_state, reason
                return state.escalation_state, "watching"

            # Already NONE or RESOLVED — stay Safe
            state.escalation_state = EscalationState.NONE
            state.current_level = 0
            return state.escalation_state, None

        return state.escalation_state, reason

    def _is_in_cooldown(self, location: str, now: datetime) -> bool:
        """Check if location is within Critical alert cooldown window."""
        state = self._get_or_create_state(location)
        if state.last_critical_sent_at is None:
            return False
        elapsed = (now - state.last_critical_sent_at).total_seconds()
        return elapsed < ALERT_COOLDOWN_SECONDS

    def _mark_critical_sent(self, location: str, now: datetime) -> None:
        """Record that a Critical alert was dispatched for cooldown tracking."""
        state = self._get_or_create_state(location)
        state.last_critical_sent_at = now


# ---------------------------------------------------------------------------
# Module-level convenience functions
# ---------------------------------------------------------------------------

def get_smart_evaluator() -> SmartAlertEvaluator:
    """Get the singleton SmartAlertEvaluator instance."""
    return SmartAlertEvaluator.get_instance()


def evaluate_smart_alert(
    risk_classification: Dict[str, Any],
    weather_data: Optional[Dict[str, Any]] = None,
    data_quality: Optional[float] = None,
    location: str = "Parañaque City",
) -> SmartAlertDecision:
    """
    Convenience wrapper: evaluate a prediction through the smart alert pipeline.

    Args:
        risk_classification: Output from ``classify_risk_level()``.
        weather_data: Current weather observations dict.
        data_quality: Data quality score 0-1.
        location: Location name.

    Returns:
        SmartAlertDecision with final risk level and enriched metadata.
    """
    evaluator = get_smart_evaluator()
    return evaluator.evaluate(
        risk_classification=risk_classification,
        weather_data=weather_data,
        data_quality=data_quality,
        location=location,
    )
