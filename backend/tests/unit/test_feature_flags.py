"""
Unit Tests for Feature Flags Service.

Tests the FeatureFlagService and all feature flag functionality including:
- Boolean flags (on/off)
- Percentage-based rollouts
- User segment targeting
- A/B testing with experiment groups
- Time-based activation
- Emergency kill switches
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

# Add backend to path
backend_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_path))


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset the singleton instance before each test."""
    import app.services.feature_flags as ff_module
    from app.services.feature_flags import FeatureFlagService

    FeatureFlagService._instance = None
    FeatureFlagService._initialized = False
    ff_module._feature_flag_service = None
    yield
    FeatureFlagService._instance = None
    FeatureFlagService._initialized = False
    ff_module._feature_flag_service = None


@pytest.fixture
def feature_service():
    """Get a fresh feature flag service instance."""
    from app.services.feature_flags import FeatureFlagService

    return FeatureFlagService()


# =============================================================================
# FeatureFlagType Enum Tests
# =============================================================================


class TestFeatureFlagType:
    """Tests for FeatureFlagType enum."""

    def test_all_flag_types_defined(self):
        """Test that all expected flag types are defined."""
        from app.services.feature_flags import FeatureFlagType

        assert FeatureFlagType.BOOLEAN.value == "boolean"
        assert FeatureFlagType.PERCENTAGE.value == "percentage"
        assert FeatureFlagType.SEGMENT.value == "segment"
        assert FeatureFlagType.EXPERIMENT.value == "experiment"
        assert FeatureFlagType.SCHEDULE.value == "schedule"

    def test_flag_type_count(self):
        """Test that we have expected number of flag types."""
        from app.services.feature_flags import FeatureFlagType

        assert len(FeatureFlagType) == 5


class TestExperimentGroup:
    """Tests for ExperimentGroup enum."""

    def test_all_groups_defined(self):
        """Test that all experiment groups are defined."""
        from app.services.feature_flags import ExperimentGroup

        assert ExperimentGroup.CONTROL.value == "control"
        assert ExperimentGroup.TREATMENT_A.value == "treatment_a"
        assert ExperimentGroup.TREATMENT_B.value == "treatment_b"


# =============================================================================
# FeatureFlag Dataclass Tests
# =============================================================================


class TestFeatureFlag:
    """Tests for FeatureFlag dataclass."""

    def test_create_basic_flag(self):
        """Test creating a basic feature flag."""
        from app.services.feature_flags import FeatureFlag, FeatureFlagType

        flag = FeatureFlag(
            name="test_flag",
            description="A test flag",
            flag_type=FeatureFlagType.BOOLEAN,
        )

        assert flag.name == "test_flag"
        assert flag.description == "A test flag"
        assert flag.flag_type == FeatureFlagType.BOOLEAN
        assert flag.enabled is True  # Default
        assert flag.rollout_percentage == 100  # Default

    def test_create_percentage_flag(self):
        """Test creating a percentage-based flag."""
        from app.services.feature_flags import FeatureFlag, FeatureFlagType

        flag = FeatureFlag(
            name="rollout_flag",
            description="Gradual rollout",
            flag_type=FeatureFlagType.PERCENTAGE,
            rollout_percentage=50,
        )

        assert flag.rollout_percentage == 50

    def test_create_segment_flag(self):
        """Test creating a segment-targeted flag."""
        from app.services.feature_flags import FeatureFlag, FeatureFlagType

        flag = FeatureFlag(
            name="segment_flag",
            description="Segment targeting",
            flag_type=FeatureFlagType.SEGMENT,
            allowed_segments=["beta", "admin"],
        )

        assert "beta" in flag.allowed_segments
        assert "admin" in flag.allowed_segments

    def test_create_experiment_flag(self):
        """Test creating an experiment flag."""
        from app.services.feature_flags import FeatureFlag, FeatureFlagType

        flag = FeatureFlag(
            name="experiment_flag",
            description="A/B test",
            flag_type=FeatureFlagType.EXPERIMENT,
            experiment_groups={"control": 50, "treatment": 50},
            experiment_config={
                "control": {"threshold": 0.5},
                "treatment": {"threshold": 0.3},
            },
        )

        assert flag.experiment_groups["control"] == 50
        assert flag.experiment_groups["treatment"] == 50
        assert flag.experiment_config["control"]["threshold"] == 0.5

    def test_create_scheduled_flag(self):
        """Test creating a time-scheduled flag."""
        from app.services.feature_flags import FeatureFlag, FeatureFlagType

        start = datetime.now(timezone.utc) - timedelta(hours=1)
        end = datetime.now(timezone.utc) + timedelta(hours=1)

        flag = FeatureFlag(
            name="scheduled_flag",
            description="Time-based flag",
            flag_type=FeatureFlagType.SCHEDULE,
            start_time=start,
            end_time=end,
        )

        assert flag.start_time == start
        assert flag.end_time == end

    def test_flag_to_dict(self):
        """Test converting flag to dictionary."""
        from app.services.feature_flags import FeatureFlag, FeatureFlagType

        flag = FeatureFlag(
            name="test",
            description="Test",
            flag_type=FeatureFlagType.BOOLEAN,
            tags=["test", "unit"],
        )

        data = flag.to_dict()

        assert data["name"] == "test"
        assert data["flag_type"] == "boolean"
        assert "test" in data["tags"]
        assert "created_at" in data

    def test_flag_force_value(self):
        """Test force value override."""
        from app.services.feature_flags import FeatureFlag, FeatureFlagType

        flag = FeatureFlag(
            name="override",
            description="Test",
            flag_type=FeatureFlagType.BOOLEAN,
            enabled=True,
            force_value=False,
        )

        assert flag.enabled is True
        assert flag.force_value is False


# =============================================================================
# FeatureFlagService Tests
# =============================================================================


class TestFeatureFlagServiceSingleton:
    """Tests for FeatureFlagService singleton pattern."""

    def test_singleton_returns_same_instance(self):
        """Test that singleton returns same instance."""
        from app.services.feature_flags import FeatureFlagService

        instance1 = FeatureFlagService()
        instance2 = FeatureFlagService()

        assert instance1 is instance2

    def test_get_feature_flag_service_returns_singleton(self):
        """Test convenience function returns singleton."""
        from app.services.feature_flags import (
            FeatureFlagService,
            get_feature_flag_service,
        )

        service = get_feature_flag_service()
        assert isinstance(service, FeatureFlagService)

        service2 = get_feature_flag_service()
        assert service is service2


class TestFeatureFlagServiceInitialization:
    """Tests for FeatureFlagService initialization."""

    def test_loads_default_flags(self, feature_service):
        """Test that default flags are loaded."""
        # Check some expected default flags
        assert feature_service.get_flag("model_v2_rollout") is not None
        assert feature_service.get_flag("bypass_openweathermap") is not None
        assert feature_service.get_flag("alert_threshold_experiment") is not None

    def test_default_flag_count(self, feature_service):
        """Test that expected number of default flags are loaded."""
        flags = feature_service.list_flags()
        assert len(flags) >= 10  # At least 10 default flags

    @patch.dict(os.environ, {"FEATURE_FLAG_MODEL_V2_ROLLOUT": "enabled"}, clear=False)
    def test_loads_from_environment_enabled(self):
        """Test loading enabled override from environment."""
        from app.services.feature_flags import FeatureFlagService

        FeatureFlagService._instance = None
        service = FeatureFlagService()

        flag = service.get_flag("model_v2_rollout")
        assert flag.force_value is True

    @patch.dict(os.environ, {"FEATURE_FLAG_MODEL_V2_ROLLOUT": "disabled"}, clear=False)
    def test_loads_from_environment_disabled(self):
        """Test loading disabled override from environment."""
        from app.services.feature_flags import FeatureFlagService

        FeatureFlagService._instance = None
        service = FeatureFlagService()

        flag = service.get_flag("model_v2_rollout")
        assert flag.force_value is False

    @patch.dict(os.environ, {"FEATURE_FLAG_MODEL_V2_ROLLOUT": "50"}, clear=False)
    def test_loads_from_environment_percentage(self):
        """Test loading percentage from environment."""
        from app.services.feature_flags import FeatureFlagService

        FeatureFlagService._instance = None
        service = FeatureFlagService()

        flag = service.get_flag("model_v2_rollout")
        assert flag.rollout_percentage == 50


class TestFeatureFlagServiceRegistration:
    """Tests for flag registration."""

    def test_register_new_flag(self, feature_service):
        """Test registering a new flag."""
        from app.services.feature_flags import FeatureFlag, FeatureFlagType

        flag = FeatureFlag(
            name="custom_flag",
            description="Custom test flag",
            flag_type=FeatureFlagType.BOOLEAN,
        )

        feature_service.register_flag(flag)

        retrieved = feature_service.get_flag("custom_flag")
        assert retrieved is not None
        assert retrieved.name == "custom_flag"

    def test_get_nonexistent_flag(self, feature_service):
        """Test getting a flag that doesn't exist."""
        flag = feature_service.get_flag("nonexistent_flag")
        assert flag is None


class TestFeatureFlagServiceListing:
    """Tests for listing flags."""

    def test_list_all_flags(self, feature_service):
        """Test listing all flags."""
        flags = feature_service.list_flags()
        assert len(flags) > 0

    def test_list_flags_by_tag(self, feature_service):
        """Test listing flags filtered by tag."""
        flags = feature_service.list_flags(tags=["emergency"])
        assert len(flags) > 0
        for flag in flags:
            assert "emergency" in flag.tags

    def test_list_flags_by_multiple_tags(self, feature_service):
        """Test listing flags filtered by multiple tags."""
        flags = feature_service.list_flags(tags=["model", "rollout"])
        assert len(flags) > 0

    def test_list_flags_no_matches(self, feature_service):
        """Test listing flags with no matching tags."""
        flags = feature_service.list_flags(tags=["nonexistent_tag_xyz"])
        assert len(flags) == 0


class TestFeatureFlagServiceIsEnabled:
    """Tests for is_enabled method."""

    def test_boolean_flag_enabled(self, feature_service):
        """Test checking enabled boolean flag."""
        from app.services.feature_flags import FeatureFlag, FeatureFlagType

        flag = FeatureFlag(
            name="test_enabled",
            description="Test",
            flag_type=FeatureFlagType.BOOLEAN,
            enabled=True,
        )
        feature_service.register_flag(flag)

        assert feature_service.is_enabled("test_enabled") is True

    def test_boolean_flag_disabled(self, feature_service):
        """Test checking disabled boolean flag."""
        from app.services.feature_flags import FeatureFlag, FeatureFlagType

        flag = FeatureFlag(
            name="test_disabled",
            description="Test",
            flag_type=FeatureFlagType.BOOLEAN,
            enabled=False,
        )
        feature_service.register_flag(flag)

        assert feature_service.is_enabled("test_disabled") is False

    def test_unknown_flag_returns_false(self, feature_service):
        """Test that unknown flag returns False."""
        assert feature_service.is_enabled("unknown_flag_xyz") is False

    def test_force_value_override(self, feature_service):
        """Test that force_value overrides enabled state."""
        from app.services.feature_flags import FeatureFlag, FeatureFlagType

        flag = FeatureFlag(
            name="force_test",
            description="Test",
            flag_type=FeatureFlagType.BOOLEAN,
            enabled=True,
            force_value=False,
        )
        feature_service.register_flag(flag)

        assert feature_service.is_enabled("force_test") is False

    def test_segment_flag_matching(self, feature_service):
        """Test segment flag with matching segment."""
        from app.services.feature_flags import FeatureFlag, FeatureFlagType

        flag = FeatureFlag(
            name="segment_test",
            description="Test",
            flag_type=FeatureFlagType.SEGMENT,
            allowed_segments=["beta", "admin"],
        )
        feature_service.register_flag(flag)

        assert feature_service.is_enabled("segment_test", segment="beta") is True
        assert feature_service.is_enabled("segment_test", segment="admin") is True
        assert feature_service.is_enabled("segment_test", segment="regular") is False
        assert feature_service.is_enabled("segment_test", segment=None) is False

    def test_percentage_flag_full_rollout(self, feature_service):
        """Test percentage flag at 100%."""
        from app.services.feature_flags import FeatureFlag, FeatureFlagType

        flag = FeatureFlag(
            name="full_rollout",
            description="Test",
            flag_type=FeatureFlagType.PERCENTAGE,
            rollout_percentage=100,
        )
        feature_service.register_flag(flag)

        assert feature_service.is_enabled("full_rollout", user_id="any_user") is True

    def test_percentage_flag_zero_rollout(self, feature_service):
        """Test percentage flag at 0%."""
        from app.services.feature_flags import FeatureFlag, FeatureFlagType

        flag = FeatureFlag(
            name="no_rollout",
            description="Test",
            flag_type=FeatureFlagType.PERCENTAGE,
            rollout_percentage=0,
        )
        feature_service.register_flag(flag)

        assert feature_service.is_enabled("no_rollout", user_id="any_user") is False

    def test_percentage_flag_sticky_for_user(self, feature_service):
        """Test percentage flag is sticky for same user."""
        from app.services.feature_flags import FeatureFlag, FeatureFlagType

        flag = FeatureFlag(
            name="sticky_test",
            description="Test",
            flag_type=FeatureFlagType.PERCENTAGE,
            rollout_percentage=50,
        )
        feature_service.register_flag(flag)

        # Same user should get same result
        result1 = feature_service.is_enabled("sticky_test", user_id="user_123")
        result2 = feature_service.is_enabled("sticky_test", user_id="user_123")
        result3 = feature_service.is_enabled("sticky_test", user_id="user_123")

        assert result1 == result2 == result3

    def test_scheduled_flag_before_start(self, feature_service):
        """Test scheduled flag before start time."""
        from app.services.feature_flags import FeatureFlag, FeatureFlagType

        start = datetime.now(timezone.utc) + timedelta(hours=1)

        flag = FeatureFlag(
            name="future_flag",
            description="Test",
            flag_type=FeatureFlagType.SCHEDULE,
            start_time=start,
        )
        feature_service.register_flag(flag)

        assert feature_service.is_enabled("future_flag") is False

    def test_scheduled_flag_after_end(self, feature_service):
        """Test scheduled flag after end time."""
        from app.services.feature_flags import FeatureFlag, FeatureFlagType

        end = datetime.now(timezone.utc) - timedelta(hours=1)

        flag = FeatureFlag(
            name="past_flag",
            description="Test",
            flag_type=FeatureFlagType.SCHEDULE,
            end_time=end,
        )
        feature_service.register_flag(flag)

        assert feature_service.is_enabled("past_flag") is False

    def test_scheduled_flag_within_window(self, feature_service):
        """Test scheduled flag within time window."""
        from app.services.feature_flags import FeatureFlag, FeatureFlagType

        start = datetime.now(timezone.utc) - timedelta(hours=1)
        end = datetime.now(timezone.utc) + timedelta(hours=1)

        flag = FeatureFlag(
            name="active_scheduled",
            description="Test",
            flag_type=FeatureFlagType.SCHEDULE,
            start_time=start,
            end_time=end,
        )
        feature_service.register_flag(flag)

        assert feature_service.is_enabled("active_scheduled") is True


class TestFeatureFlagServiceExperiments:
    """Tests for A/B testing functionality."""

    def test_get_experiment_group(self, feature_service):
        """Test getting experiment group for user."""
        group = feature_service.get_experiment_group("alert_threshold_experiment", "user_123")

        assert group in ["control", "treatment_a", "treatment_b"]

    def test_experiment_group_sticky(self, feature_service):
        """Test experiment group is sticky for user."""
        group1 = feature_service.get_experiment_group("alert_threshold_experiment", "user_456")
        group2 = feature_service.get_experiment_group("alert_threshold_experiment", "user_456")
        group3 = feature_service.get_experiment_group("alert_threshold_experiment", "user_456")

        assert group1 == group2 == group3

    def test_experiment_config(self, feature_service):
        """Test getting experiment config."""
        config = feature_service.get_experiment_config("alert_threshold_experiment", "user_789")

        assert config is not None
        assert "flood_risk_low" in config

    def test_nonexistent_experiment(self, feature_service):
        """Test getting group for non-experiment flag."""
        group = feature_service.get_experiment_group("model_v2_rollout", "user_123")
        assert group is None

    def test_disabled_experiment(self, feature_service):
        """Test disabled experiment returns None."""
        flag = feature_service.get_flag("alert_threshold_experiment")
        flag.enabled = False

        group = feature_service.get_experiment_group("alert_threshold_experiment", "user_123")
        assert group is None


class TestFeatureFlagServiceUpdate:
    """Tests for updating flags at runtime."""

    def test_update_enabled_state(self, feature_service):
        """Test updating flag enabled state."""
        result = feature_service.update_flag("model_v2_rollout", enabled=True)

        assert result is True
        flag = feature_service.get_flag("model_v2_rollout")
        assert flag.enabled is True

    def test_update_rollout_percentage(self, feature_service):
        """Test updating rollout percentage."""
        result = feature_service.update_flag("model_v2_rollout", rollout_percentage=75)

        assert result is True
        flag = feature_service.get_flag("model_v2_rollout")
        assert flag.rollout_percentage == 75

    def test_update_force_value(self, feature_service):
        """Test updating force value (emergency override)."""
        result = feature_service.update_flag("bypass_openweathermap", force_value=True)

        assert result is True
        assert feature_service.is_enabled("bypass_openweathermap") is True

    def test_update_unknown_flag(self, feature_service):
        """Test updating non-existent flag."""
        result = feature_service.update_flag("nonexistent_xyz", enabled=True)
        assert result is False

    def test_update_clamps_percentage(self, feature_service):
        """Test that percentage is clamped to 0-100."""
        feature_service.update_flag("model_v2_rollout", rollout_percentage=150)
        flag = feature_service.get_flag("model_v2_rollout")
        assert flag.rollout_percentage == 100

        feature_service.update_flag("model_v2_rollout", rollout_percentage=-50)
        flag = feature_service.get_flag("model_v2_rollout")
        assert flag.rollout_percentage == 0

    def test_set_emergency_bypass(self, feature_service):
        """Test setting emergency bypass."""
        result = feature_service.set_emergency_bypass("bypass_worldtides", True)

        assert result is True
        flag = feature_service.get_flag("bypass_worldtides")
        assert flag.force_value is True


class TestFeatureFlagServiceListeners:
    """Tests for listener functionality."""

    def test_register_listener(self, feature_service):
        """Test registering a listener."""
        callback_calls = []

        def callback(name, flag):
            callback_calls.append((name, flag))

        feature_service.register_listener("model_v2_rollout", callback)
        feature_service.update_flag("model_v2_rollout", enabled=True)

        assert len(callback_calls) == 1
        assert callback_calls[0][0] == "model_v2_rollout"

    def test_listener_error_handling(self, feature_service):
        """Test that listener errors don't crash service."""

        def bad_callback(name, flag):
            raise ValueError("Test error")

        feature_service.register_listener("model_v2_rollout", bad_callback)

        # Should not raise
        result = feature_service.update_flag("model_v2_rollout", enabled=True)
        assert result is True


class TestFeatureFlagServiceStats:
    """Tests for statistics tracking."""

    def test_stats_recorded(self, feature_service):
        """Test that evaluations are recorded."""
        feature_service.is_enabled("model_v2_rollout")
        feature_service.is_enabled("model_v2_rollout")
        feature_service.is_enabled("bypass_openweathermap")

        stats = feature_service.get_stats()

        assert "model_v2_rollout" in stats
        assert stats["model_v2_rollout"]["enabled"] + stats["model_v2_rollout"]["disabled"] == 2


# =============================================================================
# Convenience Function Tests
# =============================================================================


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_is_feature_enabled(self):
        """Test is_feature_enabled convenience function."""
        from app.services.feature_flags import is_feature_enabled

        # Should not raise
        result = is_feature_enabled("bypass_openweathermap")
        assert isinstance(result, bool)

    def test_get_alert_thresholds_default(self):
        """Test get_alert_thresholds returns defaults when not in experiment."""
        from app.services.feature_flags import get_alert_thresholds

        thresholds = get_alert_thresholds("test_user")

        assert "flood_risk_low" in thresholds
        assert "flood_risk_medium" in thresholds
        assert "flood_risk_high" in thresholds

    def test_should_use_model_v2_default(self):
        """Test should_use_model_v2 returns False by default."""
        from app.services.feature_flags import should_use_model_v2

        result = should_use_model_v2()
        assert result is False  # Default is 0% rollout

    def test_should_bypass_external_api_default(self):
        """Test should_bypass_external_api returns False by default."""
        from app.services.feature_flags import should_bypass_external_api

        assert should_bypass_external_api("openweathermap") is False
        assert should_bypass_external_api("worldtides") is False

    def test_should_bypass_when_global_bypass_enabled(self, feature_service):
        """Test bypass returns True when global bypass is enabled."""
        from app.services.feature_flags import should_bypass_external_api

        feature_service.set_emergency_bypass("bypass_all_external_apis", True)

        assert should_bypass_external_api("openweathermap") is True
        assert should_bypass_external_api("worldtides") is True

    def test_should_bypass_specific_api(self, feature_service):
        """Test bypass returns True when specific API bypass is enabled."""
        from app.services.feature_flags import should_bypass_external_api

        feature_service.set_emergency_bypass("bypass_worldtides", True)

        assert should_bypass_external_api("worldtides") is True
        assert should_bypass_external_api("openweathermap") is False


class TestFeatureFlagDecorator:
    """Tests for feature_flag decorator."""

    def test_decorator_enabled_flag(self, feature_service):
        """Test decorator executes function when flag is enabled."""
        from app.services.feature_flags import FeatureFlag, FeatureFlagType, feature_flag

        # Register enabled flag
        flag = FeatureFlag(
            name="decorator_test_enabled",
            description="Test",
            flag_type=FeatureFlagType.BOOLEAN,
            enabled=True,
        )
        feature_service.register_flag(flag)

        @feature_flag("decorator_test_enabled")
        def test_func():
            return "executed"

        result = test_func()
        assert result == "executed"

    def test_decorator_disabled_flag(self, feature_service):
        """Test decorator returns None when flag is disabled."""
        from app.services.feature_flags import FeatureFlag, FeatureFlagType, feature_flag

        # Register disabled flag
        flag = FeatureFlag(
            name="decorator_test_disabled",
            description="Test",
            flag_type=FeatureFlagType.BOOLEAN,
            enabled=False,
        )
        feature_service.register_flag(flag)

        @feature_flag("decorator_test_disabled")
        def test_func():
            return "executed"

        result = test_func()
        assert result is None

    def test_decorator_with_fallback(self, feature_service):
        """Test decorator uses fallback when flag is disabled."""
        from app.services.feature_flags import FeatureFlag, FeatureFlagType, feature_flag

        # Register disabled flag
        flag = FeatureFlag(
            name="decorator_test_fallback",
            description="Test",
            flag_type=FeatureFlagType.BOOLEAN,
            enabled=False,
        )
        feature_service.register_flag(flag)

        def fallback_func():
            return "fallback"

        @feature_flag("decorator_test_fallback", fallback=fallback_func)
        def test_func():
            return "executed"

        result = test_func()
        assert result == "fallback"


class TestHashPercentage:
    """Tests for consistent hashing."""

    def test_hash_is_deterministic(self, feature_service):
        """Test that hash produces same result for same input."""
        hash1 = feature_service._get_hash_percentage("flag", "user")
        hash2 = feature_service._get_hash_percentage("flag", "user")

        assert hash1 == hash2

    def test_hash_is_in_range(self, feature_service):
        """Test that hash is in range 0-99."""
        for i in range(100):
            hash_val = feature_service._get_hash_percentage("flag", f"user_{i}")
            assert 0 <= hash_val < 100

    def test_hash_distributes(self, feature_service):
        """Test that hash distributes users reasonably."""
        results = [feature_service._get_hash_percentage("flag", f"user_{i}") for i in range(1000)]

        # Should have some variance
        assert min(results) < 20
        assert max(results) > 80


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
