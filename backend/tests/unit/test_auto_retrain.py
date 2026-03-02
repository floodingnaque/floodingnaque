"""
Tests for Automated Retraining Pipeline — drift detection, triggers, pipeline.
"""

import numpy as np
import pandas as pd
import pytest
from datetime import datetime, timezone, timedelta

from app.services.auto_retrain import (
    AutoRetrainingPipeline,
    RetrainingConfig,
    check_retraining_needed,
    compute_psi,
    detect_drift,
)


# ═════════════════════════════════════════════════════════════════════════════
# PSI (Population Stability Index)
# ═════════════════════════════════════════════════════════════════════════════

class TestComputePSI:
    """Tests for PSI drift metric computation."""

    def test_identical_distributions(self):
        ref = np.random.normal(0, 1, 1000)
        psi = compute_psi(ref, ref)
        assert psi < 0.01  # Nearly zero for identical data

    def test_shifted_distribution(self):
        ref = np.random.normal(0, 1, 1000)
        cur = np.random.normal(2, 1, 1000)  # Shifted mean
        psi = compute_psi(ref, cur)
        assert psi > 0.1  # Should detect significant drift

    def test_empty_arrays(self):
        assert compute_psi(np.array([]), np.array([1, 2, 3])) == 0.0
        assert compute_psi(np.array([1, 2, 3]), np.array([])) == 0.0

    def test_nan_handling(self):
        ref = np.array([1, 2, np.nan, 4, 5])
        cur = np.array([1, 2, 3, np.nan, 5])
        psi = compute_psi(ref, cur)
        assert isinstance(psi, float)

    def test_non_negative(self):
        ref = np.random.normal(0, 1, 500)
        cur = np.random.normal(0.5, 1.5, 500)
        assert compute_psi(ref, cur) >= 0


# ═════════════════════════════════════════════════════════════════════════════
# Drift Detection
# ═════════════════════════════════════════════════════════════════════════════

class TestDetectDrift:
    """Tests for multi-feature drift detection."""

    def test_no_drift(self):
        np.random.seed(42)
        ref = pd.DataFrame({
            "temperature": np.random.normal(30, 2, 500),
            "humidity": np.random.normal(70, 10, 500),
        })
        result = detect_drift(ref, ref)
        assert result["drift_detected"] is False

    def test_drift_detected(self):
        np.random.seed(42)
        ref = pd.DataFrame({
            "temperature": np.random.normal(30, 2, 500),
            "humidity": np.random.normal(70, 10, 500),
        })
        cur = pd.DataFrame({
            "temperature": np.random.normal(35, 3, 500),  # Shifted
            "humidity": np.random.normal(70, 10, 500),
        })
        result = detect_drift(ref, cur, monitored_features=["temperature", "humidity"])
        assert result["drift_detected"] is True
        assert "temperature" in result["drifted_features"]

    def test_psi_values_reported(self):
        ref = pd.DataFrame({"x": np.random.normal(0, 1, 200)})
        cur = pd.DataFrame({"x": np.random.normal(0, 1, 200)})
        result = detect_drift(ref, cur, monitored_features=["x"])
        assert "x" in result["psi_values"]


# ═════════════════════════════════════════════════════════════════════════════
# Trigger Checking
# ═════════════════════════════════════════════════════════════════════════════

class TestCheckTriggers:
    """Tests for retraining trigger evaluation."""

    def test_schedule_trigger(self):
        pipeline = AutoRetrainingPipeline()
        old_date = datetime.now(timezone.utc) - timedelta(days=60)
        result = pipeline.check_triggers(last_training_date=old_date)
        assert result["should_retrain"] is True
        assert "scheduled" in result["triggered_by"]

    def test_no_trigger_recent_training(self):
        pipeline = AutoRetrainingPipeline()
        recent = datetime.now(timezone.utc) - timedelta(days=5)
        result = pipeline.check_triggers(last_training_date=recent)
        # Without data changes or drift, should not trigger
        assert "scheduled" not in result.get("triggered_by", [])

    def test_drift_trigger(self):
        np.random.seed(42)
        ref = pd.DataFrame({
            "temperature": np.random.normal(30, 2, 500),
            "humidity": np.random.normal(70, 10, 500),
            "precipitation": np.random.normal(5, 3, 500),
        })
        cur = pd.DataFrame({
            "temperature": np.random.normal(38, 4, 500),  # Large shift
            "humidity": np.random.normal(90, 5, 500),     # Large shift
            "precipitation": np.random.normal(20, 8, 500),
        })
        pipeline = AutoRetrainingPipeline()
        result = pipeline.check_triggers(
            reference_data=ref, current_data=cur
        )
        assert result["should_retrain"] is True
        assert "drift" in result["triggered_by"]


# ═════════════════════════════════════════════════════════════════════════════
# Retraining Config
# ═════════════════════════════════════════════════════════════════════════════

class TestRetrainingConfig:
    """Tests for retraining configuration defaults."""

    def test_defaults(self):
        config = RetrainingConfig()
        assert config.min_new_records == 50
        assert config.schedule_days == 30
        assert config.min_f1_score == 0.80
        assert config.min_recall == 0.85
        assert config.training_mode == "production"

    def test_custom_config(self):
        config = RetrainingConfig(
            schedule_days=14,
            include_enso=True,
            include_deep_learning=True,
        )
        assert config.schedule_days == 14
        assert config.include_enso is True
        assert config.include_deep_learning is True


# ═════════════════════════════════════════════════════════════════════════════
# Promotion Criteria
# ═════════════════════════════════════════════════════════════════════════════

class TestPromotionCriteria:
    """Tests for model promotion gating."""

    def test_passes_good_metrics(self):
        pipeline = AutoRetrainingPipeline()
        metrics = {"f1_score": 0.92, "recall": 0.90, "roc_auc": 0.95}
        result = pipeline._evaluate_promotion_criteria(metrics)
        assert result["passes"] is True

    def test_fails_low_f1(self):
        pipeline = AutoRetrainingPipeline()
        metrics = {"f1_score": 0.60, "recall": 0.90, "roc_auc": 0.90}
        result = pipeline._evaluate_promotion_criteria(metrics)
        assert result["passes"] is False
        assert any("f1_score" in c for c in result["failed_criteria"])

    def test_fails_low_recall(self):
        pipeline = AutoRetrainingPipeline()
        metrics = {"f1_score": 0.90, "recall": 0.70, "roc_auc": 0.90}
        result = pipeline._evaluate_promotion_criteria(metrics)
        assert result["passes"] is False
        assert any("recall" in c for c in result["failed_criteria"])
