"""
Unit tests for the Smart Alert Evaluator.

Tests cover:
- 3-hour rolling rainfall accumulation tracking
- Composite confidence scoring
- False alarm reduction (confidence threshold)
- Alert escalation (Alert → Critical after 30 min persistence)
- Alert de-escalation (Safe for 15 min → Resolved)
- Cooldown / deduplication for Critical alerts
- Contributing factor detection
- Rainfall threshold overrides
"""

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.services.smart_alert_evaluator import (
    ALERT_COOLDOWN_SECONDS,
    CONFIDENCE_THRESHOLD,
    DEESCALATION_MINUTES,
    ESCALATION_MINUTES,
    RAINFALL_3H_ALERT_THRESHOLD,
    RAINFALL_3H_CRITICAL_THRESHOLD,
    EscalationState,
    SmartAlertDecision,
    SmartAlertEvaluator,
    evaluate_smart_alert,
    get_smart_evaluator,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset the singleton before each test."""
    SmartAlertEvaluator.reset_instance()
    yield
    SmartAlertEvaluator.reset_instance()


@pytest.fixture
def evaluator():
    return SmartAlertEvaluator.get_instance()


def _make_risk(level=0, label="Safe", confidence=0.8):
    """Helper to build a fake risk classification dict."""
    return {
        "risk_level": level,
        "risk_label": label,
        "confidence": confidence,
        "risk_color": "#28a745",
        "description": "Test",
        "binary_prediction": 1 if level >= 1 else 0,
        "probability": {"no_flood": 1 - confidence, "flood": confidence},
    }


# ---------------------------------------------------------------------------
# Test: Singleton
# ---------------------------------------------------------------------------

class TestSingleton:
    def test_get_instance_returns_same_object(self):
        a = SmartAlertEvaluator.get_instance()
        b = SmartAlertEvaluator.get_instance()
        assert a is b

    def test_reset_creates_new_instance(self):
        a = SmartAlertEvaluator.get_instance()
        SmartAlertEvaluator.reset_instance()
        b = SmartAlertEvaluator.get_instance()
        assert a is not b

    def test_convenience_function(self):
        assert isinstance(get_smart_evaluator(), SmartAlertEvaluator)


# ---------------------------------------------------------------------------
# Test: SmartAlertDecision
# ---------------------------------------------------------------------------

class TestSmartAlertDecision:
    def test_to_dict(self):
        d = SmartAlertDecision(
            risk_level=2,
            risk_label="Critical",
            confidence=0.85,
            rainfall_3h=62.5,
            was_suppressed=False,
            escalation_state="critical",
            escalation_reason="persisted_30min",
            contributing_factors=["Heavy rainfall"],
            original_risk_level=1,
        )
        result = d.to_dict()
        assert result["risk_level"] == 2
        assert result["rainfall_3h"] == 62.5
        assert result["contributing_factors"] == ["Heavy rainfall"]
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# Test: Composite Confidence Scoring
# ---------------------------------------------------------------------------

class TestCompositeConfidence:
    def test_with_data_quality(self, evaluator):
        # model=0.8, quality=0.6 → 0.8*0.7 + 0.6*0.3 = 0.56 + 0.18 = 0.74
        result = evaluator._compute_composite_confidence(0.8, 0.6)
        assert abs(result - 0.74) < 0.001

    def test_without_data_quality(self, evaluator):
        result = evaluator._compute_composite_confidence(0.8, None)
        assert result == 0.8

    def test_zero_data_quality(self, evaluator):
        # model=0.8, quality=0.0 → 0.56 + 0.0 = 0.56
        result = evaluator._compute_composite_confidence(0.8, 0.0)
        assert abs(result - 0.56) < 0.001


# ---------------------------------------------------------------------------
# Test: 3-Hour Rainfall Accumulation
# ---------------------------------------------------------------------------

class TestRainfallAccumulation:
    def test_uses_precipitation_3h_from_weather_data(self, evaluator):
        """Should prefer satellite-derived precipitation_3h when provided."""
        weather = {"precipitation_3h": 55.0}
        result = evaluator._compute_rainfall_3h(weather, "test_loc")
        assert result == 55.0

    def test_falls_back_to_db_query(self, evaluator):
        """When precipitation_3h is missing, query DB for last 3h."""
        weather = {"precipitation": 12.0}
        with patch("app.models.db.get_db_session") as mock_session:
            mock_ctx = MagicMock()
            mock_session.return_value.__enter__ = lambda s: mock_ctx
            mock_session.return_value.__exit__ = MagicMock(return_value=False)
            mock_ctx.query.return_value.filter.return_value.scalar.return_value = 42.0

            result = evaluator._compute_rainfall_3h(weather, "test_loc")
            assert result == 42.0

    def test_falls_back_to_current_precipitation_on_error(self, evaluator):
        """On DB error, falls back to current precipitation value."""
        weather = {"precipitation": 15.5}

        with patch(
            "app.models.db.get_db_session",
            side_effect=Exception("DB down"),
        ):
            result = evaluator._compute_rainfall_3h(weather, "test_loc")
            assert result == 15.5


# ---------------------------------------------------------------------------
# Test: Rainfall Threshold Overrides
# ---------------------------------------------------------------------------

class TestRainfallThresholds:
    def test_critical_threshold(self, evaluator):
        level, label, reason = evaluator._apply_rainfall_thresholds(
            risk_level=0, risk_label="Safe", rainfall_3h=85.0
        )
        assert level == 2
        assert label == "Critical"
        assert "Critical" in reason

    def test_alert_threshold(self, evaluator):
        level, label, reason = evaluator._apply_rainfall_thresholds(
            risk_level=0, risk_label="Safe", rainfall_3h=55.0
        )
        assert level == 1
        assert label == "Alert"
        assert "Alert" in reason

    def test_no_override_when_already_critical(self, evaluator):
        level, label, reason = evaluator._apply_rainfall_thresholds(
            risk_level=2, risk_label="Critical", rainfall_3h=55.0
        )
        assert level == 2  # unchanged
        assert reason is None

    def test_no_override_below_threshold(self, evaluator):
        level, label, reason = evaluator._apply_rainfall_thresholds(
            risk_level=0, risk_label="Safe", rainfall_3h=30.0
        )
        assert level == 0
        assert reason is None


# ---------------------------------------------------------------------------
# Test: Contributing Factors Detection
# ---------------------------------------------------------------------------

class TestContributingFactors:
    def test_heavy_rainfall(self, evaluator):
        factors = evaluator._detect_contributing_factors(
            {"precipitation": 35.0}, risk_level=2, rainfall_3h=0.0
        )
        assert any("Heavy rainfall" in f for f in factors)

    def test_moderate_rainfall(self, evaluator):
        factors = evaluator._detect_contributing_factors(
            {"precipitation": 15.0}, risk_level=1, rainfall_3h=0.0
        )
        assert any("Moderate rainfall" in f for f in factors)

    def test_high_humidity(self, evaluator):
        factors = evaluator._detect_contributing_factors(
            {"humidity": 92.0}, risk_level=1, rainfall_3h=0.0
        )
        assert any("humidity" in f.lower() for f in factors)

    def test_high_tide(self, evaluator):
        factors = evaluator._detect_contributing_factors(
            {"tide_height": 2.0}, risk_level=1, rainfall_3h=0.0
        )
        assert any("tide" in f.lower() for f in factors)

    def test_elevated_tide_risk(self, evaluator):
        factors = evaluator._detect_contributing_factors(
            {"tide_risk_factor": 0.75}, risk_level=1, rainfall_3h=0.0
        )
        assert any("tide risk" in f.lower() for f in factors)

    def test_strong_winds(self, evaluator):
        factors = evaluator._detect_contributing_factors(
            {"wind_speed": 25.0}, risk_level=1, rainfall_3h=0.0
        )
        assert any("wind" in f.lower() for f in factors)

    def test_high_accumulation(self, evaluator):
        factors = evaluator._detect_contributing_factors(
            {}, risk_level=1, rainfall_3h=55.0
        )
        assert any("3h accumulation" in f for f in factors)

    def test_no_factors_for_calm_conditions(self, evaluator):
        factors = evaluator._detect_contributing_factors(
            {"precipitation": 2.0, "humidity": 50.0, "wind_speed": 5.0},
            risk_level=0,
            rainfall_3h=10.0,
        )
        assert len(factors) == 0


# ---------------------------------------------------------------------------
# Test: False Alarm Reduction
# ---------------------------------------------------------------------------

class TestFalseAlarmReduction:
    @patch.object(SmartAlertEvaluator, "_compute_rainfall_3h", return_value=5.0)
    def test_suppress_low_confidence_alert(self, mock_rain, evaluator):
        """Alert with confidence below threshold should be suppressed."""
        risk = _make_risk(level=1, label="Alert", confidence=0.3)
        decision = evaluator.evaluate(
            risk_classification=risk,
            weather_data={"precipitation": 5.0},
            data_quality=0.3,  # composite = 0.3*0.7 + 0.3*0.3 = 0.30 < 0.45
        )
        assert decision.was_suppressed is True
        assert any("Suppressed" in f for f in decision.contributing_factors)

    @patch.object(SmartAlertEvaluator, "_compute_rainfall_3h", return_value=5.0)
    def test_allow_high_confidence_alert(self, mock_rain, evaluator):
        """Alert with confidence above threshold should NOT be suppressed."""
        risk = _make_risk(level=1, label="Alert", confidence=0.8)
        decision = evaluator.evaluate(
            risk_classification=risk,
            weather_data={"precipitation": 15.0},
            data_quality=0.9,  # composite = 0.8*0.7 + 0.9*0.3 = 0.83
        )
        assert decision.was_suppressed is False

    @patch.object(SmartAlertEvaluator, "_compute_rainfall_3h", return_value=5.0)
    def test_critical_never_suppressed_by_confidence(self, mock_rain, evaluator):
        """Critical alerts are NOT suppressed by confidence threshold."""
        risk = _make_risk(level=2, label="Critical", confidence=0.3)
        decision = evaluator.evaluate(
            risk_classification=risk,
            weather_data={},
            data_quality=0.2,
        )
        # Critical might be suppressed by cooldown but NOT by confidence
        assert not any("Suppressed" in f for f in decision.contributing_factors)


# ---------------------------------------------------------------------------
# Test: Escalation State Machine
# ---------------------------------------------------------------------------

class TestEscalation:
    def test_safe_stays_none(self, evaluator):
        state, reason = evaluator._update_escalation("loc", 0, datetime.now(timezone.utc))
        assert state == EscalationState.NONE

    def test_alert_starts_timer(self, evaluator):
        state, reason = evaluator._update_escalation("loc", 1, datetime.now(timezone.utc))
        assert state == EscalationState.ALERT
        assert reason is None

    def test_alert_escalates_after_threshold(self, evaluator):
        now = datetime.now(timezone.utc)
        # First evaluation: start Alert
        evaluator._update_escalation("loc", 1, now)
        # Second evaluation: 31 minutes later → should escalate
        later = now + timedelta(minutes=ESCALATION_MINUTES + 1)
        state, reason = evaluator._update_escalation("loc", 1, later)
        assert state == EscalationState.CRITICAL
        assert reason == "persisted_30min"

    def test_alert_does_not_escalate_before_threshold(self, evaluator):
        now = datetime.now(timezone.utc)
        evaluator._update_escalation("loc", 1, now)
        # 10 minutes later — should NOT escalate
        later = now + timedelta(minutes=10)
        state, reason = evaluator._update_escalation("loc", 1, later)
        assert state == EscalationState.ALERT
        assert reason is None

    def test_critical_direct(self, evaluator):
        state, reason = evaluator._update_escalation("loc", 2, datetime.now(timezone.utc))
        assert state == EscalationState.CRITICAL
        assert reason == "direct_critical"

    def test_deescalation_starts_watch(self, evaluator):
        now = datetime.now(timezone.utc)
        # Build up to Alert
        evaluator._update_escalation("loc", 1, now)
        # Then go Safe → should start WATCH
        safe_time = now + timedelta(minutes=5)
        state, reason = evaluator._update_escalation("loc", 0, safe_time)
        assert state == EscalationState.WATCH
        assert reason == "de-escalating"

    def test_deescalation_resolves_after_threshold(self, evaluator):
        now = datetime.now(timezone.utc)
        evaluator._update_escalation("loc", 1, now)
        # Go Safe
        safe_start = now + timedelta(minutes=5)
        evaluator._update_escalation("loc", 0, safe_start)
        # Wait 16 minutes of safe
        safe_end = safe_start + timedelta(minutes=DEESCALATION_MINUTES + 1)
        state, reason = evaluator._update_escalation("loc", 0, safe_end)
        assert state == EscalationState.RESOLVED
        assert reason == "de-escalated"

    def test_deescalation_resets_on_new_alert(self, evaluator):
        now = datetime.now(timezone.utc)
        evaluator._update_escalation("loc", 1, now)
        # Go Safe briefly
        evaluator._update_escalation("loc", 0, now + timedelta(minutes=2))
        # Back to Alert before de-escalation completes
        state, reason = evaluator._update_escalation("loc", 1, now + timedelta(minutes=3))
        assert state == EscalationState.ALERT


# ---------------------------------------------------------------------------
# Test: Cooldown
# ---------------------------------------------------------------------------

class TestCooldown:
    def test_no_cooldown_initially(self, evaluator):
        assert evaluator._is_in_cooldown("loc", datetime.now(timezone.utc)) is False

    def test_cooldown_after_critical(self, evaluator):
        now = datetime.now(timezone.utc)
        evaluator._mark_critical_sent("loc", now)
        # Immediately after — should be in cooldown
        assert evaluator._is_in_cooldown("loc", now + timedelta(seconds=10)) is True

    def test_cooldown_expires(self, evaluator):
        now = datetime.now(timezone.utc)
        evaluator._mark_critical_sent("loc", now)
        # After cooldown period — should NOT be in cooldown
        later = now + timedelta(seconds=ALERT_COOLDOWN_SECONDS + 1)
        assert evaluator._is_in_cooldown("loc", later) is False


# ---------------------------------------------------------------------------
# Test: Full Pipeline (evaluate)
# ---------------------------------------------------------------------------

class TestFullPipeline:
    @patch.object(SmartAlertEvaluator, "_compute_rainfall_3h", return_value=10.0)
    def test_safe_prediction_passes_through(self, mock_rain, evaluator):
        risk = _make_risk(level=0, label="Safe", confidence=0.9)
        decision = evaluator.evaluate(risk_classification=risk, weather_data={})
        assert decision.risk_level == 0
        assert decision.risk_label == "Safe"
        assert decision.was_suppressed is False

    @patch.object(SmartAlertEvaluator, "_compute_rainfall_3h", return_value=85.0)
    def test_rainfall_forces_critical(self, mock_rain, evaluator):
        """Safe prediction overridden to Critical by rainfall accumulation."""
        risk = _make_risk(level=0, label="Safe", confidence=0.9)
        decision = evaluator.evaluate(
            risk_classification=risk,
            weather_data={"precipitation": 40.0},
            data_quality=0.8,
        )
        assert decision.risk_level == 2
        assert decision.risk_label == "Critical"
        assert decision.original_risk_level == 0

    @patch.object(SmartAlertEvaluator, "_compute_rainfall_3h", return_value=5.0)
    def test_escalation_in_full_pipeline(self, mock_rain, evaluator):
        """Alert that persists for 30+ minutes auto-escalates to Critical."""
        now = datetime.now(timezone.utc)
        risk = _make_risk(level=1, label="Alert", confidence=0.8)

        # First evaluation
        with patch("app.services.smart_alert_evaluator.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            d1 = evaluator.evaluate(risk_classification=risk, weather_data={}, data_quality=0.8)
        assert d1.risk_level == 1

        # Manually set the alert_started_at to simulate time passing
        state = evaluator._get_or_create_state("Parañaque City")
        state.alert_started_at = now - timedelta(minutes=ESCALATION_MINUTES + 1)

        d2 = evaluator.evaluate(risk_classification=risk, weather_data={}, data_quality=0.8)
        assert d2.risk_level == 2
        assert d2.risk_label == "Critical"
        assert d2.escalation_state == "critical"
        assert d2.escalation_reason == "persisted_30min"
        assert any("Auto-escalated" in f for f in d2.contributing_factors)

    @patch.object(SmartAlertEvaluator, "_compute_rainfall_3h", return_value=5.0)
    def test_duplicate_critical_suppressed_by_cooldown(self, mock_rain, evaluator):
        """Second Critical alert within cooldown window is suppressed."""
        risk = _make_risk(level=2, label="Critical", confidence=0.9)

        d1 = evaluator.evaluate(risk_classification=risk, weather_data={}, data_quality=0.9)
        assert d1.was_suppressed is False

        d2 = evaluator.evaluate(risk_classification=risk, weather_data={}, data_quality=0.9)
        assert d2.was_suppressed is True
        assert any("Cooldown" in f for f in d2.contributing_factors)

    @patch.object(SmartAlertEvaluator, "_compute_rainfall_3h", return_value=5.0)
    def test_convenience_function(self, mock_rain):
        """Test the module-level evaluate_smart_alert function."""
        risk = _make_risk(level=0, label="Safe", confidence=0.9)
        decision = evaluate_smart_alert(risk_classification=risk)
        assert isinstance(decision, SmartAlertDecision)
        assert decision.risk_level == 0

    def test_get_location_state_returns_none_for_unknown(self, evaluator):
        result = evaluator.get_location_state("nonexistent")
        assert result is None

    @patch.object(SmartAlertEvaluator, "_compute_rainfall_3h", return_value=5.0)
    def test_get_location_state_after_evaluation(self, mock_rain, evaluator):
        risk = _make_risk(level=1, label="Alert", confidence=0.8)
        evaluator.evaluate(risk_classification=risk, weather_data={}, data_quality=0.8)
        state = evaluator.get_location_state("Parañaque City")
        assert state is not None
        assert state["current_level"] == 1
        assert state["escalation_state"] == "alert"


# ---------------------------------------------------------------------------
# Test: Enhanced Risk Classifier (precipitation_3h / tide_risk_factor)
# ---------------------------------------------------------------------------

class TestEnhancedRiskClassifier:
    def test_precipitation_3h_forces_critical(self):
        from app.services.risk_classifier import classify_risk_level

        result = classify_risk_level(
            prediction=0,
            probability={"no_flood": 0.9, "flood": 0.1},
            precipitation=5.0,
            humidity=50.0,
            precipitation_3h=85.0,
        )
        assert result["risk_level"] == 2

    def test_precipitation_3h_forces_alert(self):
        from app.services.risk_classifier import classify_risk_level

        result = classify_risk_level(
            prediction=0,
            probability={"no_flood": 0.9, "flood": 0.1},
            precipitation=5.0,
            humidity=50.0,
            precipitation_3h=55.0,
        )
        assert result["risk_level"] == 1

    def test_tide_risk_factor_elevates_to_alert(self):
        from app.services.risk_classifier import classify_risk_level

        result = classify_risk_level(
            prediction=0,
            probability={"no_flood": 0.85, "flood": 0.15},
            precipitation=5.0,
            humidity=50.0,
            tide_risk_factor=0.85,
        )
        assert result["risk_level"] == 1

    def test_tide_plus_flood_probability_critical(self):
        from app.services.risk_classifier import classify_risk_level

        result = classify_risk_level(
            prediction=0,
            probability={"no_flood": 0.55, "flood": 0.45},
            precipitation=5.0,
            humidity=50.0,
            tide_risk_factor=0.75,
        )
        assert result["risk_level"] == 2

    def test_no_override_for_low_values(self):
        from app.services.risk_classifier import classify_risk_level

        result = classify_risk_level(
            prediction=0,
            probability={"no_flood": 0.9, "flood": 0.1},
            precipitation=5.0,
            humidity=50.0,
            precipitation_3h=30.0,
            tide_risk_factor=0.3,
        )
        assert result["risk_level"] == 0


# ---------------------------------------------------------------------------
# Test: AlertHistory Model Fields
# ---------------------------------------------------------------------------

class TestAlertHistoryModel:
    def test_new_columns_exist(self):
        from app.models.alert import AlertHistory

        # Check that the new columns are defined
        assert hasattr(AlertHistory, "confidence_score")
        assert hasattr(AlertHistory, "rainfall_3h")
        assert hasattr(AlertHistory, "escalation_state")
        assert hasattr(AlertHistory, "escalation_reason")
        assert hasattr(AlertHistory, "suppressed")
        assert hasattr(AlertHistory, "contributing_factors")
