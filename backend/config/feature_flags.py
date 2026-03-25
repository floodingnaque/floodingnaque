"""
Floodingnaque Feature Flags System
==================================

Centralized feature flag management for controlling application behavior
without code deployments.

Features:
- Type-safe flag definitions with defaults
- Environment-specific overrides
- Percentage-based rollouts
- Flag groups for batch enabling/disabling
- Change tracking and audit logging

Usage:
    from config.feature_flags import flags, is_enabled

    # Check if a feature is enabled
    if is_enabled("mlflow_tracking"):
        mlflow.start_run()

    # Get flag with context (for percentage rollouts)
    if flags.is_enabled("new_algorithm", context={"user_id": user.id}):
        use_new_algorithm()

    # Get all flags status
    status = flags.get_all_flags()
"""

import hashlib
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Union

import yaml

logger = logging.getLogger(__name__)


class FlagType(str, Enum):
    """Types of feature flags."""

    BOOLEAN = "boolean"  # Simple on/off
    PERCENTAGE = "percentage"  # Gradual rollout (0-100)
    STRING = "string"  # String value selection
    INTEGER = "integer"  # Numeric threshold


@dataclass
class FeatureFlag:
    """Definition of a feature flag."""

    name: str
    description: str
    flag_type: FlagType = FlagType.BOOLEAN
    default_value: Any = False
    enabled: bool = False
    percentage: int = 0  # For percentage rollouts (0-100)
    allowed_values: List[Any] = field(default_factory=list)  # For string type
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Lifecycle tracking
    created_at: Optional[str] = None
    modified_at: Optional[str] = None
    owner: Optional[str] = None
    jira_ticket: Optional[str] = None  # For tracking feature development

    def is_enabled(self, context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Check if flag is enabled, considering percentage rollouts.

        Args:
            context: Optional context for percentage-based decisions
                     (e.g., {"user_id": 123} for consistent user experience)
        """
        if self.flag_type == FlagType.BOOLEAN:
            return self.enabled

        elif self.flag_type == FlagType.PERCENTAGE:
            if self.percentage >= 100:
                return True
            if self.percentage <= 0:
                return False

            # Use context for consistent hashing (same user always gets same result)
            if context:
                hash_input = f"{self.name}:{sorted(context.items())}"
                hash_value = int(hashlib.md5(hash_input.encode(), usedforsecurity=False).hexdigest(), 16)
                return (hash_value % 100) < self.percentage

            # No context - use random-ish behavior based on current time
            return False  # Default to off for safety without context

        return self.enabled

    def get_value(self) -> Any:
        """Get the current value of the flag."""
        if self.flag_type == FlagType.BOOLEAN:
            return self.enabled
        elif self.flag_type == FlagType.PERCENTAGE:
            return self.percentage
        return self.default_value


# =============================================================================
# Predefined Feature Flags
# =============================================================================

FEATURE_FLAGS: Dict[str, FeatureFlag] = {
    # ---------------------------------------------------------------------------
    # ML/Training Features
    # ---------------------------------------------------------------------------
    "mlflow_tracking": FeatureFlag(
        name="mlflow_tracking",
        description="Enable MLflow experiment tracking and model registry",
        flag_type=FlagType.BOOLEAN,
        default_value=True,
        enabled=True,
        owner="ml-team",
    ),
    "optuna_optimization": FeatureFlag(
        name="optuna_optimization",
        description="Enable Optuna hyperparameter optimization",
        flag_type=FlagType.BOOLEAN,
        default_value=True,
        enabled=True,
        owner="ml-team",
    ),
    "model_calibration": FeatureFlag(
        name="model_calibration",
        description="Enable probability calibration for models",
        flag_type=FlagType.BOOLEAN,
        default_value=True,
        enabled=True,
        owner="ml-team",
    ),
    "drift_detection": FeatureFlag(
        name="drift_detection",
        description="Enable data drift detection and alerts",
        flag_type=FlagType.BOOLEAN,
        default_value=True,
        enabled=True,
        owner="ml-team",
    ),
    "temporal_validation": FeatureFlag(
        name="temporal_validation",
        description="Enable temporal walk-forward cross-validation",
        flag_type=FlagType.BOOLEAN,
        default_value=True,
        enabled=True,
        owner="ml-team",
    ),
    "ensemble_stacking": FeatureFlag(
        name="ensemble_stacking",
        description="Enable stacking ensemble models",
        flag_type=FlagType.BOOLEAN,
        default_value=True,
        enabled=True,
        owner="ml-team",
    ),
    # ---------------------------------------------------------------------------
    # Data Pipeline Features
    # ---------------------------------------------------------------------------
    "data_validation": FeatureFlag(
        name="data_validation",
        description="Enable data quality validation on ingestion",
        flag_type=FlagType.BOOLEAN,
        default_value=True,
        enabled=True,
        owner="data-team",
    ),
    "meteostat_integration": FeatureFlag(
        name="meteostat_integration",
        description="Enable Meteostat historical weather data fetching",
        flag_type=FlagType.BOOLEAN,
        default_value=True,
        enabled=True,
        owner="data-team",
    ),
    "earth_engine_integration": FeatureFlag(
        name="earth_engine_integration",
        description="Enable Google Earth Engine satellite data",
        flag_type=FlagType.BOOLEAN,
        default_value=False,
        enabled=False,
        owner="data-team",
    ),
    "worldtides_integration": FeatureFlag(
        name="worldtides_integration",
        description="Enable WorldTides API for tidal data",
        flag_type=FlagType.BOOLEAN,
        default_value=False,
        enabled=False,
        owner="data-team",
    ),
    # ---------------------------------------------------------------------------
    # API Features
    # ---------------------------------------------------------------------------
    "api_rate_limiting": FeatureFlag(
        name="api_rate_limiting",
        description="Enable API rate limiting",
        flag_type=FlagType.BOOLEAN,
        default_value=True,
        enabled=True,
        owner="platform-team",
    ),
    "api_caching": FeatureFlag(
        name="api_caching",
        description="Enable response caching for API endpoints",
        flag_type=FlagType.BOOLEAN,
        default_value=True,
        enabled=True,
        owner="platform-team",
    ),
    "api_auth_bypass": FeatureFlag(
        name="api_auth_bypass",
        description="Allow auth bypass in development (NEVER enable in production!)",
        flag_type=FlagType.BOOLEAN,
        default_value=False,
        enabled=False,
        owner="security-team",
        metadata={"security_critical": True},
    ),
    # ---------------------------------------------------------------------------
    # Alerting Features
    # ---------------------------------------------------------------------------
    "email_alerts": FeatureFlag(
        name="email_alerts",
        description="Enable email alert notifications",
        flag_type=FlagType.BOOLEAN,
        default_value=True,
        enabled=True,
        owner="platform-team",
    ),
    "sms_alerts": FeatureFlag(
        name="sms_alerts",
        description="Enable SMS alert notifications",
        flag_type=FlagType.BOOLEAN,
        default_value=True,
        enabled=True,
        owner="platform-team",
    ),
    "slack_notifications": FeatureFlag(
        name="slack_notifications",
        description="Enable Slack notifications for alerts",
        flag_type=FlagType.BOOLEAN,
        default_value=False,
        enabled=False,
        owner="platform-team",
    ),
    # ---------------------------------------------------------------------------
    # Monitoring Features
    # ---------------------------------------------------------------------------
    "prometheus_metrics": FeatureFlag(
        name="prometheus_metrics",
        description="Enable Prometheus metrics endpoint",
        flag_type=FlagType.BOOLEAN,
        default_value=True,
        enabled=True,
        owner="platform-team",
    ),
    "detailed_logging": FeatureFlag(
        name="detailed_logging",
        description="Enable verbose debug logging",
        flag_type=FlagType.BOOLEAN,
        default_value=False,
        enabled=False,
        owner="platform-team",
    ),
    "performance_profiling": FeatureFlag(
        name="performance_profiling",
        description="Enable performance profiling for requests",
        flag_type=FlagType.BOOLEAN,
        default_value=False,
        enabled=False,
        owner="platform-team",
    ),
    # ---------------------------------------------------------------------------
    # Experimental Features
    # ---------------------------------------------------------------------------
    "new_prediction_algorithm": FeatureFlag(
        name="new_prediction_algorithm",
        description="Use new experimental prediction algorithm",
        flag_type=FlagType.PERCENTAGE,
        default_value=0,
        percentage=0,
        owner="ml-team",
        metadata={"experimental": True},
    ),
    "v2_api": FeatureFlag(
        name="v2_api",
        description="Enable V2 API endpoints",
        flag_type=FlagType.PERCENTAGE,
        default_value=0,
        percentage=0,
        owner="platform-team",
        metadata={"experimental": True},
    ),
}

# Flag groups for batch operations
FLAG_GROUPS = {
    "ml_features": [
        "mlflow_tracking",
        "optuna_optimization",
        "model_calibration",
        "drift_detection",
        "temporal_validation",
        "ensemble_stacking",
    ],
    "data_features": [
        "data_validation",
        "meteostat_integration",
        "earth_engine_integration",
        "worldtides_integration",
    ],
    "api_features": [
        "api_rate_limiting",
        "api_caching",
        "api_auth_bypass",
    ],
    "alerting_features": [
        "email_alerts",
        "sms_alerts",
        "slack_notifications",
    ],
    "monitoring_features": [
        "prometheus_metrics",
        "detailed_logging",
        "performance_profiling",
    ],
    "experimental_features": [
        "new_prediction_algorithm",
        "v2_api",
    ],
}


class FeatureFlagsManager:
    """
    Centralized feature flags manager.

    Loads flags from:
    1. Default definitions (FEATURE_FLAGS)
    2. Environment-specific YAML file
    3. Environment variables (FLOODINGNAQUE_FLAG_*)
    """

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize feature flags manager.

        Args:
            config_dir: Directory containing feature_flags.yaml
        """
        self.config_dir = config_dir or Path(__file__).parent
        self._flags: Dict[str, FeatureFlag] = {}
        self._change_callbacks: List[Callable[[str, bool], None]] = []
        self._access_log: List[Dict[str, Any]] = []

        # Load flags
        self._load_flags()

    def _load_flags(self) -> None:
        """Load flags from all sources."""
        # 1. Start with defaults
        self._flags = {k: FeatureFlag(**{**v.__dict__}) for k, v in FEATURE_FLAGS.items()}

        # 2. Load from YAML file
        self._load_yaml_flags()

        # 3. Apply environment variable overrides
        self._apply_env_overrides()

        logger.info(f"Loaded {len(self._flags)} feature flags")

    def _load_yaml_flags(self) -> None:
        """Load flags from YAML configuration file.

        Loads the base feature_flags.yaml first, then deep-merges
        environment-specific overrides from feature_flags.{APP_ENV}.yaml
        (e.g. feature_flags.production.yaml).
        """
        # 1. Load base feature_flags.yaml
        flags_file = self.config_dir / "feature_flags.yaml"
        self._apply_yaml_file(flags_file)

        # 2. Load environment-specific overrides
        app_env = os.getenv("APP_ENV", "development")
        env_flags_file = self.config_dir / f"feature_flags.{app_env}.yaml"
        if env_flags_file.exists():
            self._apply_yaml_file(env_flags_file)
            logger.info(f"Applied environment feature flags from {env_flags_file.name}")
        else:
            logger.debug(f"No environment-specific flags file: {env_flags_file.name}")

    def _apply_yaml_file(self, flags_file: Path) -> None:
        """Apply flags from a single YAML file."""

        if not flags_file.exists():
            logger.debug(f"Feature flags file not found: {flags_file}")
            return

        try:
            with open(flags_file, "r") as f:
                data = yaml.safe_load(f) or {}

            flags_data = data.get("flags", {})
            for name, settings in flags_data.items():
                if name in self._flags:
                    # Update existing flag
                    flag = self._flags[name]
                    if "enabled" in settings:
                        flag.enabled = settings["enabled"]
                    if "percentage" in settings:
                        flag.percentage = settings["percentage"]
                    if "metadata" in settings:
                        flag.metadata.update(settings["metadata"])
                else:
                    # Create new flag from YAML
                    flag_type = FlagType(settings.get("type", "boolean"))
                    self._flags[name] = FeatureFlag(
                        name=name,
                        description=settings.get("description", ""),
                        flag_type=flag_type,
                        enabled=settings.get("enabled", False),
                        percentage=settings.get("percentage", 0),
                        default_value=settings.get("default_value", False),
                        owner=settings.get("owner"),
                        metadata=settings.get("metadata", {}),
                    )

            logger.debug(f"Loaded flags from {flags_file.name}")

        except yaml.YAMLError as e:
            logger.error(f"Failed to parse feature flags file: {e}")

    def _apply_env_overrides(self) -> None:
        """Apply environment variable overrides (FLOODINGNAQUE_FLAG_*)."""
        prefix = "FLOODINGNAQUE_FLAG_"

        for key, value in os.environ.items():
            if key.startswith(prefix):
                flag_name = key[len(prefix) :].lower()

                if flag_name in self._flags:
                    flag = self._flags[flag_name]

                    if flag.flag_type == FlagType.BOOLEAN:
                        flag.enabled = value.lower() in ("true", "1", "yes", "on")
                    elif flag.flag_type == FlagType.PERCENTAGE:
                        try:
                            flag.percentage = int(value)
                        except ValueError:
                            logger.warning(f"Invalid percentage value for {flag_name}: {value}")

                    logger.debug(f"Flag {flag_name} overridden via environment: {value}")

    def is_enabled(self, flag_name: str, context: Optional[Dict[str, Any]] = None, default: bool = False) -> bool:
        """
        Check if a feature flag is enabled.

        Args:
            flag_name: Name of the flag
            context: Optional context for percentage-based rollouts
            default: Default value if flag not found

        Returns:
            bool: Whether the feature is enabled
        """
        # Track access
        self._access_log.append(
            {
                "flag": flag_name,
                "timestamp": datetime.now().isoformat(),
                "context": context,
            }
        )

        if flag_name not in self._flags:
            logger.debug(f"Unknown flag '{flag_name}', returning default: {default}")
            return default

        return self._flags[flag_name].is_enabled(context)

    def get_flag(self, flag_name: str) -> Optional[FeatureFlag]:
        """Get a flag definition by name."""
        return self._flags.get(flag_name)

    def get_value(self, flag_name: str, default: Any = None) -> Any:
        """Get the current value of a flag."""
        flag = self._flags.get(flag_name)
        return flag.get_value() if flag else default

    def set_flag(self, flag_name: str, enabled: Optional[bool] = None, percentage: Optional[int] = None) -> None:
        """
        Dynamically update a flag (runtime only, not persisted).

        Args:
            flag_name: Name of the flag
            enabled: New enabled state (for boolean flags)
            percentage: New percentage (for percentage flags)
        """
        if flag_name not in self._flags:
            logger.warning(f"Cannot set unknown flag: {flag_name}")
            return

        flag = self._flags[flag_name]
        old_value = flag.is_enabled()

        if enabled is not None:
            flag.enabled = enabled
        if percentage is not None:
            flag.percentage = percentage

        flag.modified_at = datetime.now().isoformat()

        new_value = flag.is_enabled()

        # Notify callbacks if value changed
        if old_value != new_value:
            for callback in self._change_callbacks:
                try:
                    callback(flag_name, new_value)
                except Exception as e:
                    logger.error(f"Error in flag change callback: {e}")

        logger.info(f"Flag {flag_name} updated: {old_value} -> {new_value}")

    def get_all_flags(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all flags."""
        return {
            name: {
                "enabled": flag.is_enabled(),
                "type": flag.flag_type.value,
                "description": flag.description,
                "percentage": flag.percentage if flag.flag_type == FlagType.PERCENTAGE else None,
                "owner": flag.owner,
            }
            for name, flag in self._flags.items()
        }

    def get_group_flags(self, group_name: str) -> Dict[str, bool]:
        """Get status of all flags in a group."""
        if group_name not in FLAG_GROUPS:
            return {}

        return {name: self.is_enabled(name) for name in FLAG_GROUPS[group_name]}

    def enable_group(self, group_name: str) -> None:
        """Enable all flags in a group."""
        if group_name not in FLAG_GROUPS:
            logger.warning(f"Unknown flag group: {group_name}")
            return

        for flag_name in FLAG_GROUPS[group_name]:
            self.set_flag(flag_name, enabled=True)

    def disable_group(self, group_name: str) -> None:
        """Disable all flags in a group."""
        if group_name not in FLAG_GROUPS:
            logger.warning(f"Unknown flag group: {group_name}")
            return

        for flag_name in FLAG_GROUPS[group_name]:
            self.set_flag(flag_name, enabled=False)

    def register_change_callback(self, callback: Callable[[str, bool], None]) -> None:
        """Register callback for flag changes."""
        self._change_callbacks.append(callback)

    def reload(self) -> None:
        """Reload flags from all sources."""
        logger.info("Reloading feature flags...")
        self._load_flags()

    def get_access_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent flag access log (for debugging)."""
        return self._access_log[-limit:]


# Global feature flags instance
_flags_manager: Optional[FeatureFlagsManager] = None


def get_flags_manager() -> FeatureFlagsManager:
    """Get the global feature flags manager."""
    global _flags_manager
    if _flags_manager is None:
        _flags_manager = FeatureFlagsManager()
    return _flags_manager


def is_enabled(flag_name: str, context: Optional[Dict[str, Any]] = None, default: bool = False) -> bool:
    """
    Convenience function to check if a feature is enabled.

    Args:
        flag_name: Name of the feature flag
        context: Optional context for percentage rollouts
        default: Default value if flag not found

    Returns:
        bool: Whether the feature is enabled
    """
    return get_flags_manager().is_enabled(flag_name, context, default)


# Aliases for convenience
flags = get_flags_manager
