"""
Unit tests for Model Versioning & A/B Testing Service.

Tests cover:
- Semantic versioning parsing and comparison
- A/B test creation and management
- Traffic splitting strategies
- Performance monitoring
- Automated rollback logic
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from app.services.model_versioning import (
    ABTest,
    ABTestMetrics,
    ABTestStatus,
    ModelVariant,
    ModelVersionManager,
    PerformanceSnapshot,
    PerformanceThresholds,
    RollbackEvent,
    RollbackReason,
    SemanticVersion,
    TrafficSplitStrategy,
    VersionBumpType,
    ab_test_prediction,
    get_version_manager,
    parse_version,
)

# =============================================================================
# Semantic Version Tests
# =============================================================================


class TestSemanticVersion:
    """Tests for SemanticVersion class."""

    def test_default_version(self):
        """Test default version is 1.0.0."""
        version = SemanticVersion()
        assert version.major == 1
        assert version.minor == 0
        assert version.patch == 0
        assert str(version) == "1.0.0"

    def test_version_string_format(self):
        """Test version string formatting."""
        version = SemanticVersion(2, 3, 4)
        assert str(version) == "2.3.4"

    def test_version_with_prerelease(self):
        """Test version with prerelease tag."""
        version = SemanticVersion(1, 0, 0, prerelease="beta")
        assert str(version) == "1.0.0-beta"

    def test_version_with_build_metadata(self):
        """Test version with build metadata."""
        version = SemanticVersion(1, 0, 0, build_metadata="abc123")
        assert str(version) == "1.0.0+abc123"

    def test_version_with_prerelease_and_metadata(self):
        """Test version with both prerelease and metadata."""
        version = SemanticVersion(1, 0, 0, prerelease="rc1", build_metadata="build42")
        assert str(version) == "1.0.0-rc1+build42"

    def test_parse_simple_version(self):
        """Test parsing simple version string."""
        version = SemanticVersion.parse("2.3.4")
        assert version.major == 2
        assert version.minor == 3
        assert version.patch == 4

    def test_parse_version_with_prerelease(self):
        """Test parsing version with prerelease."""
        version = SemanticVersion.parse("1.2.3-alpha")
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3
        assert version.prerelease == "alpha"

    def test_parse_version_with_metadata(self):
        """Test parsing version with build metadata."""
        version = SemanticVersion.parse("1.2.3+build456")
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3
        assert version.build_metadata == "build456"

    def test_parse_incomplete_version(self):
        """Test parsing incomplete version string."""
        version = SemanticVersion.parse("1.2")
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 0

    def test_from_legacy_version(self):
        """Test converting legacy integer version."""
        version = SemanticVersion.from_legacy_version(5)
        assert version.major == 5
        assert version.minor == 0
        assert version.patch == 0

    def test_bump_major(self):
        """Test major version bump."""
        version = SemanticVersion(1, 2, 3)
        new_version = version.bump_major()
        assert new_version.major == 2
        assert new_version.minor == 0
        assert new_version.patch == 0

    def test_bump_minor(self):
        """Test minor version bump."""
        version = SemanticVersion(1, 2, 3)
        new_version = version.bump_minor()
        assert new_version.major == 1
        assert new_version.minor == 3
        assert new_version.patch == 0

    def test_bump_patch(self):
        """Test patch version bump."""
        version = SemanticVersion(1, 2, 3)
        new_version = version.bump_patch()
        assert new_version.major == 1
        assert new_version.minor == 2
        assert new_version.patch == 4

    def test_version_comparison_equal(self):
        """Test version equality."""
        v1 = SemanticVersion(1, 2, 3)
        v2 = SemanticVersion(1, 2, 3)
        assert v1 == v2

    def test_version_comparison_less_than(self):
        """Test version less than comparison."""
        v1 = SemanticVersion(1, 2, 3)
        v2 = SemanticVersion(1, 2, 4)
        v3 = SemanticVersion(1, 3, 0)
        v4 = SemanticVersion(2, 0, 0)

        assert v1 < v2
        assert v1 < v3
        assert v1 < v4

    def test_version_comparison_greater_than(self):
        """Test version greater than comparison."""
        v1 = SemanticVersion(2, 0, 0)
        v2 = SemanticVersion(1, 9, 9)
        assert v1 > v2

    def test_version_hash(self):
        """Test version hashing for use in sets/dicts."""
        v1 = SemanticVersion(1, 2, 3)
        v2 = SemanticVersion(1, 2, 3)

        # Same versions should have same hash
        assert hash(v1) == hash(v2)

        # Can be used in sets
        version_set = {v1, v2}
        assert len(version_set) == 1

    def test_to_dict(self):
        """Test version serialization to dictionary."""
        version = SemanticVersion(1, 2, 3, prerelease="beta")
        d = version.to_dict()

        assert d["major"] == 1
        assert d["minor"] == 2
        assert d["patch"] == 3
        assert d["prerelease"] == "beta"
        assert d["version_string"] == "1.2.3-beta"


# =============================================================================
# A/B Test Metrics Tests
# =============================================================================


class TestABTestMetrics:
    """Tests for ABTestMetrics class."""

    def test_default_metrics(self):
        """Test default metric values."""
        metrics = ABTestMetrics(variant_name="control")

        assert metrics.variant_name == "control"
        assert metrics.predictions_count == 0
        assert metrics.correct_predictions == 0
        assert metrics.total_latency_ms == 0.0
        assert metrics.errors_count == 0

    def test_accuracy_calculation(self):
        """Test accuracy calculation."""
        metrics = ABTestMetrics(variant_name="test")
        metrics.predictions_count = 100
        metrics.correct_predictions = 85

        assert metrics.accuracy == 0.85

    def test_accuracy_none_when_no_predictions(self):
        """Test accuracy is None when no predictions."""
        metrics = ABTestMetrics(variant_name="test")
        assert metrics.accuracy is None

    def test_accuracy_none_when_no_correct(self):
        """Test accuracy is None when no correct predictions recorded."""
        metrics = ABTestMetrics(variant_name="test")
        metrics.predictions_count = 100
        assert metrics.accuracy is None

    def test_average_latency(self):
        """Test average latency calculation."""
        metrics = ABTestMetrics(variant_name="test")
        metrics.predictions_count = 10
        metrics.total_latency_ms = 500.0

        assert metrics.average_latency_ms == 50.0

    def test_error_rate(self):
        """Test error rate calculation."""
        metrics = ABTestMetrics(variant_name="test")
        metrics.predictions_count = 90
        metrics.errors_count = 10

        assert metrics.error_rate == 0.1

    def test_average_confidence(self):
        """Test average confidence calculation."""
        metrics = ABTestMetrics(variant_name="test")
        metrics.confidence_scores = [0.8, 0.9, 0.7, 0.85, 0.95]

        assert metrics.average_confidence == pytest.approx(0.84)

    def test_to_dict(self):
        """Test metrics serialization."""
        metrics = ABTestMetrics(variant_name="test")
        metrics.predictions_count = 100
        metrics.correct_predictions = 80
        metrics.total_latency_ms = 1000.0

        d = metrics.to_dict()
        assert d["variant_name"] == "test"
        assert d["predictions_count"] == 100
        assert d["accuracy"] == 0.8
        assert d["average_latency_ms"] == 10.0


# =============================================================================
# A/B Test Tests
# =============================================================================


class TestABTest:
    """Tests for ABTest class."""

    @pytest.fixture
    def sample_variants(self):
        """Create sample variants for testing."""
        control = ModelVariant(
            name="control",
            version=SemanticVersion(1, 0, 0),
            model_path="models/flood_rf_model_v1.joblib",
            weight=0.5,
            is_control=True,
        )
        treatment = ModelVariant(
            name="treatment",
            version=SemanticVersion(2, 0, 0),
            model_path="models/flood_rf_model_v2.joblib",
            weight=0.5,
            is_control=False,
        )
        return [control, treatment]

    def test_ab_test_creation(self, sample_variants):
        """Test A/B test creation."""
        test = ABTest(
            test_id="test_123", name="Model Comparison", description="Testing v2 against v1", variants=sample_variants
        )

        assert test.test_id == "test_123"
        assert test.status == ABTestStatus.CREATED
        assert len(test.variants) == 2
        assert len(test.metrics) == 2

    def test_total_predictions(self, sample_variants):
        """Test total predictions calculation."""
        test = ABTest(test_id="test_123", name="Test", description="Test", variants=sample_variants)

        test.metrics["control"].predictions_count = 50
        test.metrics["treatment"].predictions_count = 50

        assert test.total_predictions == 100

    def test_is_complete(self, sample_variants):
        """Test completion check."""
        test = ABTest(
            test_id="test_123", name="Test", description="Test", variants=sample_variants, target_sample_size=100
        )

        assert not test.is_complete

        test.metrics["control"].predictions_count = 50
        test.metrics["treatment"].predictions_count = 50

        assert test.is_complete

    def test_select_variant_random(self, sample_variants):
        """Test random variant selection."""
        test = ABTest(
            test_id="test_123",
            name="Test",
            description="Test",
            variants=sample_variants,
            strategy=TrafficSplitStrategy.RANDOM,
        )

        # With many selections, both should be selected
        selected = [test.select_variant() for _ in range(100)]
        names = [v.name for v in selected]

        assert "control" in names
        assert "treatment" in names

    def test_select_variant_round_robin(self, sample_variants):
        """Test round robin variant selection."""
        test = ABTest(
            test_id="test_123",
            name="Test",
            description="Test",
            variants=sample_variants,
            strategy=TrafficSplitStrategy.ROUND_ROBIN,
        )

        v1 = test.select_variant()
        v2 = test.select_variant()
        v3 = test.select_variant()

        # Should alternate
        assert v1.name == "control"
        assert v2.name == "treatment"
        assert v3.name == "control"

    def test_select_variant_sticky(self, sample_variants):
        """Test sticky variant selection."""
        test = ABTest(
            test_id="test_123",
            name="Test",
            description="Test",
            variants=sample_variants,
            strategy=TrafficSplitStrategy.STICKY,
        )

        # Same user should always get same variant
        v1 = test.select_variant(user_id="user_123")
        v2 = test.select_variant(user_id="user_123")
        v3 = test.select_variant(user_id="user_123")

        assert v1.name == v2.name == v3.name

    def test_select_variant_canary(self, sample_variants):
        """Test canary variant selection."""
        test = ABTest(
            test_id="test_123",
            name="Test",
            description="Test",
            variants=sample_variants,
            strategy=TrafficSplitStrategy.CANARY,
        )
        test.canary_percentage = 10.0

        # Most should go to control
        selected = [test.select_variant() for _ in range(100)]
        control_count = sum(1 for v in selected if v.is_control)

        # With 10% canary, expect ~90% control
        assert control_count > 70  # Allow some variance

    def test_increment_canary(self, sample_variants):
        """Test canary percentage increment."""
        test = ABTest(
            test_id="test_123",
            name="Test",
            description="Test",
            variants=sample_variants,
            strategy=TrafficSplitStrategy.CANARY,
        )
        test.canary_percentage = 0.0
        test.canary_increment = 25.0

        assert not test.increment_canary()  # 25%
        assert test.canary_percentage == 25.0

        assert not test.increment_canary()  # 50%
        assert not test.increment_canary()  # 75%
        assert test.increment_canary()  # 100% - returns True
        assert test.canary_percentage == 100.0

    def test_to_dict(self, sample_variants):
        """Test A/B test serialization."""
        test = ABTest(test_id="test_123", name="Test", description="Test desc", variants=sample_variants)

        d = test.to_dict()
        assert d["test_id"] == "test_123"
        assert d["name"] == "Test"
        assert d["status"] == "created"
        assert len(d["variants"]) == 2


# =============================================================================
# Performance Thresholds Tests
# =============================================================================


class TestPerformanceThresholds:
    """Tests for PerformanceThresholds."""

    def test_default_thresholds(self):
        """Test default threshold values."""
        thresholds = PerformanceThresholds()

        assert thresholds.min_accuracy == 0.70
        assert thresholds.max_error_rate == 0.10
        assert thresholds.max_latency_ms == 500.0
        assert thresholds.min_confidence == 0.50
        assert thresholds.evaluation_window == 100
        assert thresholds.consecutive_failures == 3

    def test_custom_thresholds(self):
        """Test custom threshold values."""
        thresholds = PerformanceThresholds(min_accuracy=0.85, max_error_rate=0.05, max_latency_ms=200.0)

        assert thresholds.min_accuracy == 0.85
        assert thresholds.max_error_rate == 0.05
        assert thresholds.max_latency_ms == 200.0


# =============================================================================
# Rollback Event Tests
# =============================================================================


class TestRollbackEvent:
    """Tests for RollbackEvent."""

    def test_rollback_event_creation(self):
        """Test rollback event creation."""
        event = RollbackEvent(
            timestamp=datetime.now(timezone.utc),
            from_version=SemanticVersion(2, 0, 0),
            to_version=SemanticVersion(1, 0, 0),
            reason=RollbackReason.ACCURACY_DEGRADATION,
            details="Accuracy dropped to 60%",
        )

        assert str(event.from_version) == "2.0.0"
        assert str(event.to_version) == "1.0.0"
        assert event.reason == RollbackReason.ACCURACY_DEGRADATION
        assert event.automatic is True

    def test_rollback_event_to_dict(self):
        """Test rollback event serialization."""
        event = RollbackEvent(
            timestamp=datetime.now(timezone.utc),
            from_version=SemanticVersion(2, 0, 0),
            to_version=SemanticVersion(1, 0, 0),
            reason=RollbackReason.HIGH_ERROR_RATE,
            details="Error rate 15%",
            automatic=False,
        )

        d = event.to_dict()
        assert d["from_version"] == "2.0.0"
        assert d["to_version"] == "1.0.0"
        assert d["reason"] == "high_error_rate"
        assert d["automatic"] is False


# =============================================================================
# Model Version Manager Tests
# =============================================================================


class TestModelVersionManager:
    """Tests for ModelVersionManager singleton."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton before each test."""
        ModelVersionManager.reset_instance()
        yield
        ModelVersionManager.reset_instance()

    def test_singleton_pattern(self):
        """Test that manager is a singleton."""
        manager1 = ModelVersionManager.get_instance()
        manager2 = ModelVersionManager.get_instance()

        assert manager1 is manager2

    def test_reset_instance(self):
        """Test singleton reset."""
        manager1 = ModelVersionManager.get_instance()
        ModelVersionManager.reset_instance()
        manager2 = ModelVersionManager.get_instance()

        assert manager1 is not manager2

    def test_get_next_version_initial(self):
        """Test next version when no current version."""
        manager = ModelVersionManager.get_instance()
        manager._current_version = None

        next_ver = manager.get_next_version()
        assert next_ver == SemanticVersion(1, 0, 0)

    def test_get_next_version_bumps(self):
        """Test version bumps."""
        manager = ModelVersionManager.get_instance()
        manager._current_version = SemanticVersion(1, 2, 3)

        major = manager.get_next_version(VersionBumpType.MAJOR)
        minor = manager.get_next_version(VersionBumpType.MINOR)
        patch = manager.get_next_version(VersionBumpType.PATCH)

        assert str(major) == "2.0.0"
        assert str(minor) == "1.3.0"
        assert str(patch) == "1.2.4"

    def test_set_performance_thresholds(self):
        """Test updating performance thresholds."""
        manager = ModelVersionManager.get_instance()

        new_thresholds = PerformanceThresholds(min_accuracy=0.80, max_error_rate=0.05)
        manager.set_performance_thresholds(new_thresholds)

        assert manager._thresholds.min_accuracy == 0.80
        assert manager._thresholds.max_error_rate == 0.05

    def test_record_prediction_success(self):
        """Test recording successful prediction."""
        manager = ModelVersionManager.get_instance()

        manager.record_prediction(latency_ms=50.0, confidence=0.85, risk_level="low")

        metrics = manager._current_metrics
        assert metrics.predictions_count == 1
        assert metrics.total_latency_ms == 50.0
        assert 0.85 in metrics.confidence_scores
        assert metrics.risk_level_distribution["low"] == 1

    def test_record_prediction_error(self):
        """Test recording prediction error."""
        manager = ModelVersionManager.get_instance()

        manager.record_prediction(latency_ms=0, error=True)

        metrics = manager._current_metrics
        assert metrics.errors_count == 1
        assert manager._failure_count == 1

    def test_record_feedback(self):
        """Test recording prediction feedback."""
        manager = ModelVersionManager.get_instance()

        manager.record_feedback(was_correct=True)
        manager.record_feedback(was_correct=True)
        manager.record_feedback(was_correct=False)

        assert manager._current_metrics.correct_predictions == 2

    def test_rollback_callback(self):
        """Test rollback callback registration."""
        manager = ModelVersionManager.get_instance()

        callback_called = []

        def my_callback(event):
            callback_called.append(event)

        manager.register_rollback_callback(my_callback)

        assert my_callback in manager._rollback_callbacks

    def test_ab_test_creation(self):
        """Test creating A/B test."""
        manager = ModelVersionManager.get_instance()

        # Register mock versions
        manager._model_versions = {
            "models/v1.joblib": SemanticVersion(1, 0, 0),
            "models/v2.joblib": SemanticVersion(2, 0, 0),
        }

        test = manager.create_ab_test(
            test_id="test_1",
            name="Test",
            description="Testing",
            control_version=SemanticVersion(1, 0, 0),
            treatment_version=SemanticVersion(2, 0, 0),
        )

        assert test.test_id == "test_1"
        assert len(test.variants) == 2
        assert "test_1" in manager._active_tests

    def test_ab_test_duplicate_id(self):
        """Test creating A/B test with duplicate ID fails."""
        manager = ModelVersionManager.get_instance()

        manager._model_versions = {
            "models/v1.joblib": SemanticVersion(1, 0, 0),
            "models/v2.joblib": SemanticVersion(2, 0, 0),
        }

        manager.create_ab_test(
            test_id="test_1",
            name="Test",
            description="Testing",
            control_version=SemanticVersion(1, 0, 0),
            treatment_version=SemanticVersion(2, 0, 0),
        )

        with pytest.raises(ValueError, match="already exists"):
            manager.create_ab_test(
                test_id="test_1",
                name="Test2",
                description="Testing2",
                control_version=SemanticVersion(1, 0, 0),
                treatment_version=SemanticVersion(2, 0, 0),
            )

    def test_list_ab_tests(self):
        """Test listing A/B tests."""
        manager = ModelVersionManager.get_instance()

        manager._model_versions = {
            "models/v1.joblib": SemanticVersion(1, 0, 0),
            "models/v2.joblib": SemanticVersion(2, 0, 0),
        }

        manager.create_ab_test(
            test_id="test_1",
            name="Test1",
            description="Testing1",
            control_version=SemanticVersion(1, 0, 0),
            treatment_version=SemanticVersion(2, 0, 0),
        )

        tests = manager.list_ab_tests()
        assert len(tests) == 1
        assert tests[0]["test_id"] == "test_1"

    def test_list_ab_tests_by_status(self):
        """Test listing A/B tests filtered by status."""
        manager = ModelVersionManager.get_instance()

        manager._model_versions = {
            "models/v1.joblib": SemanticVersion(1, 0, 0),
            "models/v2.joblib": SemanticVersion(2, 0, 0),
        }

        manager.create_ab_test(
            test_id="test_1",
            name="Test1",
            description="Testing1",
            control_version=SemanticVersion(1, 0, 0),
            treatment_version=SemanticVersion(2, 0, 0),
        )

        # Only CREATED
        created = manager.list_ab_tests(status=ABTestStatus.CREATED)
        assert len(created) == 1

        # No RUNNING
        running = manager.list_ab_tests(status=ABTestStatus.RUNNING)
        assert len(running) == 0

    def test_get_performance_history(self):
        """Test getting performance history."""
        manager = ModelVersionManager.get_instance()

        # Add some history
        manager._performance_history.append(
            PerformanceSnapshot(
                timestamp=datetime.now(timezone.utc),
                version=SemanticVersion(1, 0, 0),
                accuracy=0.85,
                error_rate=0.05,
                average_latency_ms=50.0,
                average_confidence=0.9,
                predictions_count=100,
            )
        )

        history = manager.get_performance_history()
        assert len(history) == 1
        assert history[0]["accuracy"] == 0.85

    def test_get_rollback_history(self):
        """Test getting rollback history."""
        manager = ModelVersionManager.get_instance()

        manager._rollback_history.append(
            RollbackEvent(
                timestamp=datetime.now(timezone.utc),
                from_version=SemanticVersion(2, 0, 0),
                to_version=SemanticVersion(1, 0, 0),
                reason=RollbackReason.MANUAL,
                details="Test rollback",
            )
        )

        history = manager.get_rollback_history()
        assert len(history) == 1
        assert history[0]["reason"] == "manual"


# =============================================================================
# Convenience Function Tests
# =============================================================================


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton before each test."""
        ModelVersionManager.reset_instance()
        yield
        ModelVersionManager.reset_instance()

    def test_get_version_manager(self):
        """Test get_version_manager function."""
        manager = get_version_manager()
        assert isinstance(manager, ModelVersionManager)

    def test_parse_version(self):
        """Test parse_version function."""
        version = parse_version("1.2.3-beta+build456")
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3
        assert version.prerelease == "beta"
        assert version.build_metadata == "build456"


# =============================================================================
# Decorator Tests
# =============================================================================


class TestABTestPredictionDecorator:
    """Tests for ab_test_prediction decorator."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton before each test."""
        ModelVersionManager.reset_instance()
        yield
        ModelVersionManager.reset_instance()

    def test_decorator_without_active_test(self):
        """Test decorator when no test is running."""

        @ab_test_prediction("nonexistent_test")
        def predict(model, data):
            return {"prediction": 1}

        result = predict(MagicMock(), {"temp": 300})
        assert result["prediction"] == 1
        assert "_ab_test" not in result

    def test_decorator_adds_test_info(self):
        """Test decorator adds A/B test info to result."""
        manager = get_version_manager()

        # Setup test
        manager._model_versions = {
            "models/v1.joblib": SemanticVersion(1, 0, 0),
            "models/v2.joblib": SemanticVersion(2, 0, 0),
        }

        test = manager.create_ab_test(
            test_id="test_1",
            name="Test",
            description="Testing",
            control_version=SemanticVersion(1, 0, 0),
            treatment_version=SemanticVersion(2, 0, 0),
        )

        # Mock model loading
        manager._test_models = {"control": MagicMock(), "treatment": MagicMock()}
        test.status = ABTestStatus.RUNNING

        @ab_test_prediction("test_1")
        def predict(model, data):
            return {"prediction": 1, "confidence": 0.9}

        result = predict(MagicMock(), {"temp": 300})

        assert "_ab_test" in result
        assert result["_ab_test"]["test_id"] == "test_1"
        assert result["_ab_test"]["variant"] in ["control", "treatment"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
