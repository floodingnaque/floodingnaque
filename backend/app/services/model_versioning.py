"""
Model Versioning & A/B Testing Service.

Provides:
- Semantic versioning for ML models (MAJOR.MINOR.PATCH)
- A/B testing capability for comparing model performance
- Automated model rollback on performance degradation
- Model promotion workflows
"""

import json
import logging
import random
import threading
import time
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import joblib
from app.services.predict import ModelLoader, compute_model_checksum, get_model_metadata, verify_model_integrity

logger = logging.getLogger(__name__)


# =============================================================================
# Semantic Versioning
# =============================================================================


@dataclass
class SemanticVersion:
    """
    Semantic version representation (MAJOR.MINOR.PATCH).

    - MAJOR: Breaking changes (incompatible feature changes, significant retraining)
    - MINOR: New capabilities, significant accuracy improvements
    - PATCH: Bug fixes, minor tuning, metadata updates
    """

    major: int = 1
    minor: int = 0
    patch: int = 0
    prerelease: Optional[str] = None  # e.g., 'alpha', 'beta', 'rc1'
    build_metadata: Optional[str] = None  # e.g., build number, commit hash

    def __str__(self) -> str:
        """Format as semantic version string."""
        version = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            version += f"-{self.prerelease}"
        if self.build_metadata:
            version += f"+{self.build_metadata}"
        return version

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SemanticVersion):
            return NotImplemented
        return (self.major, self.minor, self.patch) == (other.major, other.minor, other.patch)

    def __lt__(self, other: "SemanticVersion") -> bool:
        return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)

    def __le__(self, other: "SemanticVersion") -> bool:
        return (self.major, self.minor, self.patch) <= (other.major, other.minor, other.patch)

    def __gt__(self, other: "SemanticVersion") -> bool:
        return (self.major, self.minor, self.patch) > (other.major, other.minor, other.patch)

    def __ge__(self, other: "SemanticVersion") -> bool:
        return (self.major, self.minor, self.patch) >= (other.major, other.minor, other.patch)

    def __hash__(self) -> int:
        return hash((self.major, self.minor, self.patch))

    @classmethod
    def parse(cls, version_string: str) -> "SemanticVersion":
        """Parse a semantic version string."""
        # Handle build metadata
        build_metadata = None
        if "+" in version_string:
            version_string, build_metadata = version_string.split("+", 1)

        # Handle prerelease
        prerelease = None
        if "-" in version_string:
            version_string, prerelease = version_string.split("-", 1)

        # Parse major.minor.patch
        parts = version_string.split(".")
        if len(parts) < 3:
            parts.extend(["0"] * (3 - len(parts)))

        try:
            major = int(parts[0])
            minor = int(parts[1])
            patch = int(parts[2])
        except (ValueError, IndexError):
            major, minor, patch = 1, 0, 0

        return cls(major=major, minor=minor, patch=patch, prerelease=prerelease, build_metadata=build_metadata)

    @classmethod
    def from_legacy_version(cls, version_int: int) -> "SemanticVersion":
        """Convert legacy integer version to semantic version."""
        return cls(major=version_int, minor=0, patch=0)

    def bump_major(self) -> "SemanticVersion":
        """Increment major version (reset minor and patch)."""
        return SemanticVersion(major=self.major + 1, minor=0, patch=0)

    def bump_minor(self) -> "SemanticVersion":
        """Increment minor version (reset patch)."""
        return SemanticVersion(major=self.major, minor=self.minor + 1, patch=0)

    def bump_patch(self) -> "SemanticVersion":
        """Increment patch version."""
        return SemanticVersion(major=self.major, minor=self.minor, patch=self.patch + 1)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "major": self.major,
            "minor": self.minor,
            "patch": self.patch,
            "prerelease": self.prerelease,
            "build_metadata": self.build_metadata,
            "version_string": str(self),
        }


class VersionBumpType(Enum):
    """Types of version bumps."""

    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"


# =============================================================================
# A/B Testing
# =============================================================================


class TrafficSplitStrategy(Enum):
    """Strategy for splitting traffic between model variants."""

    RANDOM = "random"  # Random assignment based on weights
    ROUND_ROBIN = "round_robin"  # Sequential assignment
    STICKY = "sticky"  # Same user always gets same variant
    CANARY = "canary"  # Gradually increase new variant traffic


@dataclass
class ModelVariant:
    """A model variant in an A/B test."""

    name: str
    version: SemanticVersion
    model_path: str
    weight: float  # Traffic weight (0.0 - 1.0)
    is_control: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": str(self.version),
            "model_path": self.model_path,
            "weight": self.weight,
            "is_control": self.is_control,
            "metadata": self.metadata,
        }


@dataclass
class ABTestMetrics:
    """Metrics collected for an A/B test variant."""

    variant_name: str
    predictions_count: int = 0
    correct_predictions: int = 0
    total_latency_ms: float = 0.0
    errors_count: int = 0
    risk_level_distribution: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    confidence_scores: List[float] = field(default_factory=list)

    @property
    def accuracy(self) -> Optional[float]:
        """Calculate accuracy if feedback is available."""
        if self.predictions_count == 0:
            return None
        if self.correct_predictions == 0:
            return None
        return self.correct_predictions / self.predictions_count

    @property
    def average_latency_ms(self) -> float:
        """Calculate average prediction latency."""
        if self.predictions_count == 0:
            return 0.0
        return self.total_latency_ms / self.predictions_count

    @property
    def error_rate(self) -> float:
        """Calculate error rate."""
        total = self.predictions_count + self.errors_count
        if total == 0:
            return 0.0
        return self.errors_count / total

    @property
    def average_confidence(self) -> Optional[float]:
        """Calculate average confidence score."""
        if not self.confidence_scores:
            return None
        return sum(self.confidence_scores) / len(self.confidence_scores)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "variant_name": self.variant_name,
            "predictions_count": self.predictions_count,
            "correct_predictions": self.correct_predictions,
            "accuracy": self.accuracy,
            "average_latency_ms": self.average_latency_ms,
            "errors_count": self.errors_count,
            "error_rate": self.error_rate,
            "risk_level_distribution": dict(self.risk_level_distribution),
            "average_confidence": self.average_confidence,
        }


class ABTestStatus(Enum):
    """Status of an A/B test."""

    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class ABTest:
    """Configuration and state for an A/B test."""

    test_id: str
    name: str
    description: str
    variants: List[ModelVariant]
    strategy: TrafficSplitStrategy = TrafficSplitStrategy.RANDOM
    status: ABTestStatus = ABTestStatus.CREATED
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    target_sample_size: int = 1000
    metrics: Dict[str, ABTestMetrics] = field(default_factory=dict)
    user_assignments: Dict[str, str] = field(default_factory=dict)  # user_id -> variant_name
    round_robin_index: int = 0
    canary_percentage: float = 0.0  # For canary deployments
    canary_increment: float = 10.0  # Percentage increase per phase
    winner: Optional[str] = None
    statistical_significance: Optional[float] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self):
        # Initialize metrics for each variant
        for variant in self.variants:
            if variant.name not in self.metrics:
                self.metrics[variant.name] = ABTestMetrics(variant_name=variant.name)

    @property
    def total_predictions(self) -> int:
        """Get total predictions across all variants."""
        return sum(m.predictions_count for m in self.metrics.values())

    @property
    def is_complete(self) -> bool:
        """Check if test has reached target sample size."""
        return self.total_predictions >= self.target_sample_size

    def select_variant(self, user_id: Optional[str] = None) -> ModelVariant:
        """Select a variant based on the traffic split strategy."""
        if self.strategy == TrafficSplitStrategy.STICKY and user_id:
            # Return same variant for same user
            if user_id in self.user_assignments:
                variant_name = self.user_assignments[user_id]
                return next(v for v in self.variants if v.name == variant_name)

        if self.strategy == TrafficSplitStrategy.ROUND_ROBIN:
            variant = self.variants[self.round_robin_index % len(self.variants)]
            self.round_robin_index += 1
        elif self.strategy == TrafficSplitStrategy.CANARY:
            # Canary: control gets (100 - canary_percentage)%, treatment gets canary_percentage%
            treatment = next((v for v in self.variants if not v.is_control), self.variants[0])
            control = next((v for v in self.variants if v.is_control), self.variants[-1])
            variant = treatment if random.random() * 100 < self.canary_percentage else control  # nosec B311
        else:  # RANDOM
            # Weighted random selection
            weights = [v.weight for v in self.variants]
            variant = random.choices(self.variants, weights=weights, k=1)[0]  # nosec B311

        # Store assignment for sticky strategy
        if user_id:
            self.user_assignments[user_id] = variant.name

        return variant

    def increment_canary(self) -> bool:
        """Increment canary percentage. Returns True if reached 100%."""
        self.canary_percentage = min(100.0, self.canary_percentage + self.canary_increment)
        return self.canary_percentage >= 100.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_id": self.test_id,
            "name": self.name,
            "description": self.description,
            "variants": [v.to_dict() for v in self.variants],
            "strategy": self.strategy.value,
            "status": self.status.value,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "target_sample_size": self.target_sample_size,
            "total_predictions": self.total_predictions,
            "is_complete": self.is_complete,
            "metrics": {k: v.to_dict() for k, v in self.metrics.items()},
            "canary_percentage": self.canary_percentage,
            "winner": self.winner,
            "statistical_significance": self.statistical_significance,
            "created_at": self.created_at.isoformat(),
        }


# =============================================================================
# Performance Monitoring & Rollback
# =============================================================================


@dataclass
class PerformanceThresholds:
    """Thresholds for triggering automated rollback."""

    min_accuracy: float = 0.70
    max_error_rate: float = 0.10
    max_latency_ms: float = 500.0
    min_confidence: float = 0.50
    evaluation_window: int = 100  # Number of predictions to evaluate
    consecutive_failures: int = 3  # Failures before rollback


@dataclass
class PerformanceSnapshot:
    """Snapshot of model performance at a point in time."""

    timestamp: datetime
    version: SemanticVersion
    accuracy: Optional[float]
    error_rate: float
    average_latency_ms: float
    average_confidence: Optional[float]
    predictions_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "version": str(self.version),
            "accuracy": self.accuracy,
            "error_rate": self.error_rate,
            "average_latency_ms": self.average_latency_ms,
            "average_confidence": self.average_confidence,
            "predictions_count": self.predictions_count,
        }


class RollbackReason(Enum):
    """Reasons for automated rollback."""

    ACCURACY_DEGRADATION = "accuracy_degradation"
    HIGH_ERROR_RATE = "high_error_rate"
    HIGH_LATENCY = "high_latency"
    LOW_CONFIDENCE = "low_confidence"
    MANUAL = "manual"
    AB_TEST_FAILURE = "ab_test_failure"


@dataclass
class RollbackEvent:
    """Record of a rollback event."""

    timestamp: datetime
    from_version: SemanticVersion
    to_version: SemanticVersion
    reason: RollbackReason
    details: str
    automatic: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "from_version": str(self.from_version),
            "to_version": str(self.to_version),
            "reason": self.reason.value,
            "details": self.details,
            "automatic": self.automatic,
        }


# =============================================================================
# Model Version Manager (Enhanced Singleton)
# =============================================================================


class ModelVersionManager:
    """
    Enhanced model manager with semantic versioning, A/B testing, and auto-rollback.

    Thread-safe singleton that extends the basic ModelLoader with advanced features.
    """

    _instance: Optional["ModelVersionManager"] = None
    _lock = threading.Lock()

    def __init__(self):
        """Initialize the version manager."""
        self._models_dir = Path("models")
        self._loaded_models: Dict[str, Any] = {}  # version_string -> model
        self._model_versions: Dict[str, SemanticVersion] = {}  # path -> version
        self._current_version: Optional[SemanticVersion] = None
        self._previous_version: Optional[SemanticVersion] = None  # For rollback

        # A/B Testing
        self._active_tests: Dict[str, ABTest] = {}
        self._test_models: Dict[str, Any] = {}  # variant_name -> loaded model

        # Performance monitoring
        self._thresholds = PerformanceThresholds()
        self._performance_history: List[PerformanceSnapshot] = []
        self._current_metrics = ABTestMetrics(variant_name="production")
        self._rollback_history: List[RollbackEvent] = []
        self._failure_count = 0

        # Callbacks
        self._rollback_callbacks: List[Callable[[RollbackEvent], None]] = []

        # Load version registry
        self._load_version_registry()

        # Restore any persisted A/B tests from the database
        self._restore_tests_from_db()

    @classmethod
    def get_instance(cls) -> "ModelVersionManager":
        """Get or create the singleton instance (thread-safe)."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (for testing)."""
        with cls._lock:
            cls._instance = None

    # =========================================================================
    # A/B Test Persistence
    # =========================================================================

    def _persist_test(self, test: ABTest) -> None:
        """Save or update an A/B test record in the database."""
        try:
            from app.models.ab_test import ABTestRecord
            from app.models.db import get_db_session

            with get_db_session() as session:
                record = session.query(ABTestRecord).filter_by(test_id=test.test_id).first()

                data = {
                    "name": test.name,
                    "description": test.description,
                    "variants_json": [v.to_dict() for v in test.variants],
                    "strategy": test.strategy.value,
                    "target_sample_size": test.target_sample_size,
                    "status": test.status.value,
                    "start_time": test.start_time,
                    "end_time": test.end_time,
                    "metrics_json": {k: v.to_dict() for k, v in test.metrics.items()},
                    "user_assignments_json": test.user_assignments,
                    "round_robin_index": test.round_robin_index,
                    "canary_percentage": test.canary_percentage,
                    "canary_increment": test.canary_increment,
                    "winner": test.winner,
                    "statistical_significance": test.statistical_significance,
                }

                if record is None:
                    record = ABTestRecord(test_id=test.test_id, **data)
                    session.add(record)
                else:
                    for key, value in data.items():
                        setattr(record, key, value)

            logger.debug(f"Persisted A/B test {test.test_id} to database")
        except Exception as e:
            logger.warning(f"Failed to persist A/B test {test.test_id}: {e}")

    def _restore_tests_from_db(self) -> None:
        """Restore non-terminal A/B tests from the database on startup."""
        try:
            from app.models.ab_test import ABTestRecord
            from app.models.db import get_db_session

            with get_db_session() as session:
                records = (
                    session.query(ABTestRecord).filter(ABTestRecord.status.in_(["created", "running", "paused"])).all()
                )

                for rec in records:
                    try:
                        test = self._record_to_ab_test(rec)
                        self._active_tests[test.test_id] = test
                        logger.info(
                            f"Restored A/B test {test.test_id} "
                            f"({test.status.value}, {test.total_predictions} predictions)"
                        )
                    except Exception as e:
                        logger.warning(f"Could not restore A/B test {rec.test_id}: {e}")

            if self._active_tests:
                logger.info(f"Restored {len(self._active_tests)} A/B test(s) from database")
        except Exception as e:
            logger.warning(f"Could not restore A/B tests from database: {e}")

    @staticmethod
    def _record_to_ab_test(rec) -> ABTest:
        """Deserialise an ABTestRecord row into an in-memory ABTest."""
        from collections import defaultdict

        variants = []
        for vd in rec.variants_json or []:
            variants.append(
                ModelVariant(
                    name=vd["name"],
                    version=SemanticVersion.parse(vd["version"]),
                    model_path=vd["model_path"],
                    weight=vd["weight"],
                    is_control=vd.get("is_control", False),
                    metadata=vd.get("metadata", {}),
                )
            )

        metrics: Dict[str, ABTestMetrics] = {}
        for name, md in (rec.metrics_json or {}).items():
            m = ABTestMetrics(variant_name=name)
            m.predictions_count = md.get("predictions_count", 0)
            m.correct_predictions = md.get("correct_predictions", 0)
            m.total_latency_ms = md.get("average_latency_ms", 0) * md.get("predictions_count", 0)
            m.errors_count = md.get("errors_count", 0)
            m.risk_level_distribution = defaultdict(int, md.get("risk_level_distribution", {}))
            # confidence_scores list is not persisted (too large); only the
            # average survives a restart.
            m.confidence_scores = []
            metrics[name] = m

        test = ABTest(
            test_id=rec.test_id,
            name=rec.name,
            description=rec.description or "",
            variants=variants,
            strategy=TrafficSplitStrategy(rec.strategy),
            status=ABTestStatus(rec.status),
            start_time=rec.start_time,
            end_time=rec.end_time,
            target_sample_size=rec.target_sample_size,
            metrics=metrics,
            user_assignments=rec.user_assignments_json or {},
            round_robin_index=rec.round_robin_index or 0,
            canary_percentage=rec.canary_percentage or 0.0,
            canary_increment=rec.canary_increment or 10.0,
            winner=rec.winner,
            statistical_significance=rec.statistical_significance,
        )
        return test

    # =========================================================================
    # Version Management
    # =========================================================================

    def _load_version_registry(self) -> None:
        """Load version information from model metadata files."""
        if not self._models_dir.exists():
            return

        for model_file in self._models_dir.glob("flood_rf_model_v*.joblib"):
            metadata = get_model_metadata(str(model_file))
            if metadata:
                # Check for semantic version in metadata
                if "semantic_version" in metadata:
                    version = SemanticVersion.parse(metadata["semantic_version"])
                elif "version" in metadata:
                    version = SemanticVersion.from_legacy_version(metadata["version"])
                else:
                    continue

                self._model_versions[str(model_file)] = version

        # Load current version
        latest_path = self._models_dir / "flood_rf_model.joblib"
        if latest_path.exists():
            metadata = get_model_metadata(str(latest_path))
            if metadata:
                if "semantic_version" in metadata:
                    self._current_version = SemanticVersion.parse(metadata["semantic_version"])
                elif "version" in metadata:
                    self._current_version = SemanticVersion.from_legacy_version(metadata["version"])

    def get_current_version(self) -> Optional[SemanticVersion]:
        """Get the current active model version."""
        return self._current_version

    def list_versions(self) -> List[Dict[str, Any]]:
        """List all available model versions with metadata."""
        versions = []
        for path, version in self._model_versions.items():
            metadata = get_model_metadata(path)
            versions.append(
                {
                    "version": version.to_dict(),
                    "path": path,
                    "is_current": version == self._current_version,
                    "metadata": metadata,
                }
            )

        # Sort by version descending
        versions.sort(key=lambda x: SemanticVersion.parse(x["version"]["version_string"]), reverse=True)
        return versions

    def get_next_version(self, bump_type: VersionBumpType = VersionBumpType.MINOR) -> SemanticVersion:
        """Calculate the next version based on bump type."""
        if self._current_version is None:
            return SemanticVersion(1, 0, 0)

        if bump_type == VersionBumpType.MAJOR:
            return self._current_version.bump_major()
        elif bump_type == VersionBumpType.MINOR:
            return self._current_version.bump_minor()
        else:
            return self._current_version.bump_patch()

    def register_version(
        self, model_path: str, version: SemanticVersion, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Register a new model version."""
        if metadata is None:
            metadata = {}

        # Add semantic version to metadata
        metadata["semantic_version"] = str(version)
        metadata["version_info"] = version.to_dict()
        metadata["registered_at"] = datetime.now(timezone.utc).isoformat()

        # Save updated metadata
        metadata_path = Path(model_path).with_suffix(".json")
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        # Update registry
        self._model_versions[model_path] = version
        logger.info(f"Registered model version {version} at {model_path}")

    def promote_version(self, version: SemanticVersion, backup_current: bool = True) -> bool:
        """
        Promote a version to be the current active model.

        Args:
            version: Version to promote
            backup_current: Whether to backup the current version before promoting

        Returns:
            True if promotion was successful
        """
        # Find the model path for this version
        model_path = None
        for path, ver in self._model_versions.items():
            if ver == version:
                model_path = path
                break

        if model_path is None:
            logger.error(f"Version {version} not found in registry")
            return False

        # Verify integrity before promoting
        if not verify_model_integrity(model_path):
            logger.error(f"Integrity check failed for version {version}")
            return False

        # Backup current if requested
        if backup_current and self._current_version:
            self._previous_version = self._current_version

        # Load and set as current
        try:
            model = joblib.load(model_path)
            metadata = get_model_metadata(model_path)
            checksum = compute_model_checksum(model_path)

            # Update ModelLoader singleton
            loader = ModelLoader.get_instance()
            loader.set_model(model=model, path=model_path, metadata=metadata, checksum=checksum)

            self._current_version = version
            self._loaded_models[str(version)] = model

            logger.info(f"Promoted version {version} to production")
            return True

        except Exception as e:
            logger.error(f"Failed to promote version {version}: {e}")
            return False

    # =========================================================================
    # A/B Testing
    # =========================================================================

    def create_ab_test(
        self,
        test_id: str,
        name: str,
        description: str,
        control_version: SemanticVersion,
        treatment_version: SemanticVersion,
        traffic_split: float = 0.5,
        strategy: TrafficSplitStrategy = TrafficSplitStrategy.RANDOM,
        target_sample_size: int = 1000,
    ) -> ABTest:
        """
        Create a new A/B test between two model versions.

        Args:
            test_id: Unique identifier for the test
            name: Human-readable name
            description: Description of what's being tested
            control_version: The baseline/current version
            treatment_version: The new version being tested
            traffic_split: Percentage of traffic to treatment (0.0-1.0)
            strategy: Traffic split strategy
            target_sample_size: Number of predictions needed

        Returns:
            The created ABTest object
        """
        if test_id in self._active_tests:
            raise ValueError(f"Test {test_id} already exists")

        # Find model paths
        control_path = None
        treatment_path = None
        for path, ver in self._model_versions.items():
            if ver == control_version:
                control_path = path
            if ver == treatment_version:
                treatment_path = path

        if not control_path or not treatment_path:
            raise ValueError("One or both versions not found in registry")

        # Create variants
        control_variant = ModelVariant(
            name="control",
            version=control_version,
            model_path=control_path,
            weight=1.0 - traffic_split,
            is_control=True,
        )

        treatment_variant = ModelVariant(
            name="treatment",
            version=treatment_version,
            model_path=treatment_path,
            weight=traffic_split,
            is_control=False,
        )

        test = ABTest(
            test_id=test_id,
            name=name,
            description=description,
            variants=[control_variant, treatment_variant],
            strategy=strategy,
            target_sample_size=target_sample_size,
        )

        self._active_tests[test_id] = test
        self._persist_test(test)
        logger.info(f"Created A/B test '{name}' ({test_id})")
        return test

    def start_ab_test(self, test_id: str) -> bool:
        """Start an A/B test."""
        if test_id not in self._active_tests:
            logger.error(f"Test {test_id} not found")
            return False

        test = self._active_tests[test_id]

        # Load models for both variants
        for variant in test.variants:
            if variant.model_path not in self._loaded_models:
                try:
                    model = joblib.load(variant.model_path)
                    self._test_models[variant.name] = model
                except Exception as e:
                    logger.error(f"Failed to load model for variant {variant.name}: {e}")
                    return False

        test.status = ABTestStatus.RUNNING
        test.start_time = datetime.now(timezone.utc)

        if test.strategy == TrafficSplitStrategy.CANARY:
            test.canary_percentage = test.canary_increment  # Start at first increment

        self._persist_test(test)
        logger.info(f"Started A/B test {test_id}")
        return True

    def get_ab_test_variant(
        self, test_id: str, user_id: Optional[str] = None
    ) -> Tuple[Optional[Any], Optional[ModelVariant]]:
        """
        Get model and variant for an A/B test prediction.

        Args:
            test_id: The test identifier
            user_id: Optional user ID for sticky assignments

        Returns:
            Tuple of (model, variant) or (None, None) if test not found/running
        """
        if test_id not in self._active_tests:
            return None, None

        test = self._active_tests[test_id]
        if test.status != ABTestStatus.RUNNING:
            return None, None

        variant = test.select_variant(user_id)
        model = self._test_models.get(variant.name)

        return model, variant

    def record_ab_prediction(
        self,
        test_id: str,
        variant_name: str,
        latency_ms: float,
        confidence: Optional[float] = None,
        risk_level: Optional[str] = None,
        error: bool = False,
    ) -> None:
        """Record a prediction result for A/B test metrics."""
        if test_id not in self._active_tests:
            return

        test = self._active_tests[test_id]
        if variant_name not in test.metrics:
            return

        metrics = test.metrics[variant_name]

        if error:
            metrics.errors_count += 1
        else:
            metrics.predictions_count += 1
            metrics.total_latency_ms += latency_ms

            if confidence is not None:
                metrics.confidence_scores.append(confidence)

            if risk_level is not None:
                metrics.risk_level_distribution[risk_level] += 1

        # Periodically persist metrics (every 50 predictions)
        if test.total_predictions % 50 == 0:
            self._persist_test(test)

        # Check if test is complete
        if test.is_complete and test.status == ABTestStatus.RUNNING:
            self._evaluate_ab_test(test_id)

    def record_ab_feedback(self, test_id: str, variant_name: str, was_correct: bool) -> None:
        """Record feedback for accuracy calculation."""
        if test_id not in self._active_tests:
            return

        test = self._active_tests[test_id]
        if variant_name not in test.metrics:
            return

        if was_correct:
            test.metrics[variant_name].correct_predictions += 1

    def _evaluate_ab_test(self, test_id: str) -> Dict[str, Any]:
        """Evaluate A/B test results and determine winner."""
        test = self._active_tests[test_id]

        results = {"test_id": test_id, "variants": {}}

        best_variant = None
        best_score = -1.0

        for variant in test.variants:
            metrics = test.metrics[variant.name]

            # Calculate composite score
            # Weight: accuracy (40%), error_rate (30%), latency (20%), confidence (10%)
            score = 0.0

            if metrics.accuracy is not None:
                score += 0.4 * metrics.accuracy

            score += 0.3 * (1.0 - metrics.error_rate)

            # Normalize latency (assume max 1000ms is bad)
            latency_score = max(0, 1.0 - (metrics.average_latency_ms / 1000.0))
            score += 0.2 * latency_score

            if metrics.average_confidence is not None:
                score += 0.1 * metrics.average_confidence

            results["variants"][variant.name] = {"metrics": metrics.to_dict(), "score": score}

            if score > best_score:
                best_score = score
                best_variant = variant.name

        # Calculate statistical significance (simplified)
        # In production, use proper statistical tests (chi-squared, etc.)
        if len(test.variants) == 2:
            v1, v2 = test.variants
            m1, m2 = test.metrics[v1.name], test.metrics[v2.name]

            if m1.predictions_count > 30 and m2.predictions_count > 30:
                # Basic significance estimate
                diff = abs(results["variants"][v1.name]["score"] - results["variants"][v2.name]["score"])
                test.statistical_significance = min(0.99, diff * 2)  # Simplified

        test.winner = best_variant
        results["winner"] = best_variant
        results["statistical_significance"] = test.statistical_significance

        logger.info(f"A/B test {test_id} evaluated. Winner: {best_variant}")
        return results

    def conclude_ab_test(self, test_id: str, promote_winner: bool = False) -> Dict[str, Any]:
        """
        Conclude an A/B test and optionally promote the winner.

        Args:
            test_id: Test identifier
            promote_winner: Whether to automatically promote the winning variant

        Returns:
            Test results including winner and metrics
        """
        if test_id not in self._active_tests:
            raise ValueError(f"Test {test_id} not found")

        test = self._active_tests[test_id]

        # Evaluate if not already done
        results = self._evaluate_ab_test(test_id)

        test.status = ABTestStatus.COMPLETED
        test.end_time = datetime.now(timezone.utc)

        # Promote winner if requested
        if promote_winner and test.winner:
            winner_variant = next(v for v in test.variants if v.name == test.winner)
            if self.promote_version(winner_variant.version):
                results["promoted"] = True
                logger.info(f"Promoted winner {winner_variant.version} from test {test_id}")

        # Cleanup test models
        for variant in test.variants:
            if variant.name in self._test_models:
                del self._test_models[variant.name]

        self._persist_test(test)
        return results

    def get_ab_test(self, test_id: str) -> Optional[Dict[str, Any]]:
        """Get A/B test details."""
        if test_id not in self._active_tests:
            return None
        return self._active_tests[test_id].to_dict()

    def list_ab_tests(self, status: Optional[ABTestStatus] = None) -> List[Dict[str, Any]]:
        """List all A/B tests, optionally filtered by status."""
        tests = []
        for test in self._active_tests.values():
            if status is None or test.status == status:
                tests.append(test.to_dict())
        return tests

    # =========================================================================
    # Performance Monitoring & Auto-Rollback
    # =========================================================================

    def set_performance_thresholds(self, thresholds: PerformanceThresholds) -> None:
        """Update performance thresholds for auto-rollback."""
        self._thresholds = thresholds
        logger.info(f"Updated performance thresholds: {asdict(thresholds)}")

    def record_prediction(
        self,
        latency_ms: float,
        confidence: Optional[float] = None,
        risk_level: Optional[str] = None,
        error: bool = False,
    ) -> Optional[RollbackEvent]:
        """
        Record a prediction and check for performance degradation.

        Returns:
            RollbackEvent if a rollback was triggered, None otherwise
        """
        if error:
            self._current_metrics.errors_count += 1
            self._failure_count += 1
        else:
            self._current_metrics.predictions_count += 1
            self._current_metrics.total_latency_ms += latency_ms
            self._failure_count = 0  # Reset on success

            if confidence is not None:
                self._current_metrics.confidence_scores.append(confidence)

            if risk_level is not None:
                self._current_metrics.risk_level_distribution[risk_level] += 1

        # Check for rollback conditions
        return self._check_rollback_conditions()

    def record_feedback(self, was_correct: bool) -> None:
        """Record prediction feedback for accuracy tracking."""
        if was_correct:
            self._current_metrics.correct_predictions += 1

    def _check_rollback_conditions(self) -> Optional[RollbackEvent]:
        """Check if current performance warrants a rollback."""
        if self._previous_version is None:
            return None  # No version to rollback to

        metrics = self._current_metrics
        thresholds = self._thresholds

        # Only evaluate after enough predictions
        if metrics.predictions_count < thresholds.evaluation_window:
            return None

        rollback_reason = None
        details = ""

        # Check error rate
        if metrics.error_rate > thresholds.max_error_rate:
            rollback_reason = RollbackReason.HIGH_ERROR_RATE
            details = f"Error rate {metrics.error_rate:.2%} exceeds threshold {thresholds.max_error_rate:.2%}"

        # Check latency
        elif metrics.average_latency_ms > thresholds.max_latency_ms:
            rollback_reason = RollbackReason.HIGH_LATENCY
            details = f"Latency {metrics.average_latency_ms:.1f}ms exceeds threshold {thresholds.max_latency_ms:.1f}ms"

        # Check accuracy (if feedback available)
        elif metrics.accuracy is not None and metrics.accuracy < thresholds.min_accuracy:
            rollback_reason = RollbackReason.ACCURACY_DEGRADATION
            details = f"Accuracy {metrics.accuracy:.2%} below threshold {thresholds.min_accuracy:.2%}"

        # Check confidence
        elif metrics.average_confidence is not None and metrics.average_confidence < thresholds.min_confidence:
            rollback_reason = RollbackReason.LOW_CONFIDENCE
            details = f"Confidence {metrics.average_confidence:.2%} below threshold {thresholds.min_confidence:.2%}"

        # Check consecutive failures
        elif self._failure_count >= thresholds.consecutive_failures:
            rollback_reason = RollbackReason.HIGH_ERROR_RATE
            details = f"{self._failure_count} consecutive failures"

        if rollback_reason and self._current_version:
            return self._execute_rollback(rollback_reason, details)

        return None

    def _execute_rollback(self, reason: RollbackReason, details: str, automatic: bool = True) -> RollbackEvent:
        """Execute a model rollback."""
        if self._previous_version is None or self._current_version is None:
            raise ValueError("No previous version available for rollback")

        # Create rollback event
        event = RollbackEvent(
            timestamp=datetime.now(timezone.utc),
            from_version=self._current_version,
            to_version=self._previous_version,
            reason=reason,
            details=details,
            automatic=automatic,
        )

        # Take performance snapshot before rollback
        if self._current_version:
            snapshot = PerformanceSnapshot(
                timestamp=datetime.now(timezone.utc),
                version=self._current_version,
                accuracy=self._current_metrics.accuracy,
                error_rate=self._current_metrics.error_rate,
                average_latency_ms=self._current_metrics.average_latency_ms,
                average_confidence=self._current_metrics.average_confidence,
                predictions_count=self._current_metrics.predictions_count,
            )
            self._performance_history.append(snapshot)

        # Perform rollback
        success = self.promote_version(self._previous_version, backup_current=False)

        if success:
            self._rollback_history.append(event)
            self._reset_metrics()

            logger.warning(
                f"ROLLBACK EXECUTED: {event.from_version} -> {event.to_version}. "
                f"Reason: {reason.value}. Details: {details}"
            )

            # Notify callbacks
            for callback in self._rollback_callbacks:
                try:
                    callback(event)
                except Exception as e:
                    logger.error(f"Rollback callback error: {e}")
        else:
            logger.error(f"Rollback FAILED from {event.from_version} to {event.to_version}")

        return event

    def manual_rollback(self, to_version: SemanticVersion, details: str = "") -> RollbackEvent:
        """Manually trigger a rollback to a specific version."""
        if self._current_version is None:
            raise ValueError("No current version to rollback from")

        # Temporarily set previous version
        original_previous = self._previous_version
        self._previous_version = to_version

        try:
            event = self._execute_rollback(
                reason=RollbackReason.MANUAL, details=details or "Manual rollback requested", automatic=False
            )
            return event
        finally:
            # Restore previous version pointer
            self._previous_version = original_previous

    def _reset_metrics(self) -> None:
        """Reset current metrics after rollback or version change."""
        self._current_metrics = ABTestMetrics(variant_name="production")
        self._failure_count = 0

    def register_rollback_callback(self, callback: Callable[[RollbackEvent], None]) -> None:
        """Register a callback to be notified on rollback events."""
        self._rollback_callbacks.append(callback)

    def get_rollback_history(self) -> List[Dict[str, Any]]:
        """Get history of all rollback events."""
        return [event.to_dict() for event in self._rollback_history]

    def get_performance_history(self) -> List[Dict[str, Any]]:
        """Get performance snapshots history."""
        return [snapshot.to_dict() for snapshot in self._performance_history]

    def get_current_performance(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        return {
            "version": str(self._current_version) if self._current_version else None,
            "metrics": self._current_metrics.to_dict(),
            "thresholds": asdict(self._thresholds),
        }


# =============================================================================
# Convenience Functions
# =============================================================================


def get_version_manager() -> ModelVersionManager:
    """Get the ModelVersionManager singleton instance."""
    return ModelVersionManager.get_instance()


def parse_version(version_string: str) -> SemanticVersion:
    """Parse a version string into a SemanticVersion object."""
    return SemanticVersion.parse(version_string)


def create_ab_test(
    name: str, control_version: str, treatment_version: str, traffic_split: float = 0.5, target_sample_size: int = 1000
) -> ABTest:
    """
    Convenience function to create and start an A/B test.

    Args:
        name: Test name
        control_version: Control version string (e.g., "1.0.0")
        treatment_version: Treatment version string (e.g., "2.0.0")
        traffic_split: Traffic percentage for treatment (0.0-1.0)
        target_sample_size: Number of predictions needed

    Returns:
        The created ABTest object
    """
    import uuid

    manager = get_version_manager()
    test_id = str(uuid.uuid4())[:8]

    test = manager.create_ab_test(
        test_id=test_id,
        name=name,
        description=f"A/B test comparing {control_version} vs {treatment_version}",
        control_version=SemanticVersion.parse(control_version),
        treatment_version=SemanticVersion.parse(treatment_version),
        traffic_split=traffic_split,
        target_sample_size=target_sample_size,
    )

    return test


# =============================================================================
# Decorator for A/B Testing Predictions
# =============================================================================


def ab_test_prediction(test_id: str):
    """
    Decorator to route predictions through an A/B test.

    Usage:
        @ab_test_prediction('my_test_123')
        def make_prediction(model, input_data):
            return model.predict(input_data)
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            manager = get_version_manager()
            user_id = kwargs.pop("user_id", None)

            model, variant = manager.get_ab_test_variant(test_id, user_id)

            if model is None or variant is None:
                # Test not running, use normal flow
                return func(*args, **kwargs)

            # Track timing
            start_time = time.time()
            error = False
            result = None

            try:
                # Replace model in args if it's the first positional arg
                if args:
                    args = (model,) + args[1:]
                result = func(*args, **kwargs)
            except Exception as e:
                error = True
                raise
            finally:
                latency_ms = (time.time() - start_time) * 1000

                # Extract confidence from result if available
                confidence = None
                risk_level = None
                if isinstance(result, dict):
                    confidence = result.get("confidence")
                    risk_level = result.get("risk_level")

                manager.record_ab_prediction(
                    test_id=test_id,
                    variant_name=variant.name,
                    latency_ms=latency_ms,
                    confidence=confidence,
                    risk_level=risk_level,
                    error=error,
                )

            # Add variant info to result
            if isinstance(result, dict):
                result["_ab_test"] = {"test_id": test_id, "variant": variant.name, "version": str(variant.version)}

            return result

        return wrapper

    return decorator
