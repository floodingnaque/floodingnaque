"""
Floodingnaque Configuration Schema Validation
=============================================

Pydantic models for validating YAML configuration structure on load.
Provides type safety, validation, and documentation for all config options.

Usage:
    from config.schema import validate_config, ConfigSchema

    # Validate loaded config dictionary
    validated_config = validate_config(config_dict)

    # Access validated values with type hints
    print(validated_config.general.log_level)
"""

from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator


class LogLevel(str, Enum):
    """Valid logging levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogFormat(str, Enum):
    """Valid log output formats."""

    JSON = "json"
    TEXT = "text"
    ECS = "ecs"  # Elastic Common Schema


class ImbalanceStrategy(str, Enum):
    """Imbalance handling strategies."""

    CLASS_WEIGHT = "class_weight"
    SMOTENC = "smotenc"
    HYBRID = "hybrid"


class CalibrationMethod(str, Enum):
    """Model calibration methods."""

    ISOTONIC = "isotonic"
    SIGMOID = "sigmoid"


class OptunaSampler(str, Enum):
    """Optuna sampler types."""

    TPE = "TPE"
    RANDOM = "Random"
    GRID = "Grid"
    CMAES = "CMA-ES"


class OptunaPruner(str, Enum):
    """Optuna pruner types."""

    MEDIAN = "MedianPruner"
    PERCENTILE = "PercentilePruner"
    SUCCESSIVE_HALVING = "SuccessiveHalvingPruner"
    HYPERBAND = "HyperbandPruner"
    NONE = "NopPruner"


# =============================================================================
# Sub-Models for Configuration Sections
# =============================================================================


class GeneralConfig(BaseModel):
    """General application settings."""

    project_name: str = Field(default="floodingnaque", description="Project name")
    random_state: int = Field(default=42, ge=0, description="Random seed for reproducibility")
    log_level: LogLevel = Field(default=LogLevel.INFO, description="Logging level")
    enable_mlflow: bool = Field(default=True, description="Enable MLflow tracking")
    enable_data_validation: bool = Field(default=True, description="Enable data validation")


class DataConfig(BaseModel):
    """Data loading and preprocessing settings."""

    processed_dir: str = Field(default="data/processed", description="Processed data directory")
    raw_dir: str = Field(default="data", description="Raw data directory")
    test_size: float = Field(default=0.2, ge=0.0, le=1.0, description="Test set ratio")
    validation_size: float = Field(default=0.1, ge=0.0, le=1.0, description="Validation set ratio")
    stratify: bool = Field(default=True, description="Use stratified sampling")
    min_samples: int = Field(default=100, ge=1, description="Minimum samples required")
    max_missing_ratio: float = Field(default=0.1, ge=0.0, le=1.0, description="Maximum allowed missing ratio")

    core_features: List[str] = Field(default_factory=list, description="Core feature columns")
    interaction_features: List[str] = Field(default_factory=list, description="Interaction feature columns")
    rolling_features: List[str] = Field(default_factory=list, description="Rolling window feature columns")
    categorical_features: List[str] = Field(default_factory=list, description="Categorical feature columns")

    @field_validator("test_size", "validation_size")
    @classmethod
    def validate_split_size(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"Split size must be between 0 and 1, got {v}")
        return v


class OptunaConfig(BaseModel):
    """Optuna hyperparameter optimization settings."""

    enabled: bool = Field(default=True, description="Enable Optuna optimization")
    n_trials: int = Field(default=50, ge=1, description="Number of optimization trials")
    timeout_minutes: int = Field(default=30, ge=1, description="Timeout in minutes")
    sampler: OptunaSampler = Field(default=OptunaSampler.TPE, description="Sampling algorithm")
    pruner: OptunaPruner = Field(default=OptunaPruner.MEDIAN, description="Pruning algorithm")
    search_space: Dict[str, Any] = Field(default_factory=dict, description="Hyperparameter search space")


class GridSearchConfig(BaseModel):
    """Grid search fallback settings."""

    enabled: bool = Field(default=False, description="Enable grid search")
    n_iter: int = Field(default=50, ge=1, description="Number of iterations for RandomizedSearchCV")
    cv_folds: int = Field(default=10, ge=2, description="Cross-validation folds")
    scoring: str = Field(default="f1_weighted", description="Scoring metric")
    param_grid: Dict[str, List[Any]] = Field(default_factory=dict, description="Parameter grid")


class CalibrationConfig(BaseModel):
    """Model probability calibration settings."""

    enabled: bool = Field(default=True, description="Enable model calibration")
    method: CalibrationMethod = Field(default=CalibrationMethod.ISOTONIC, description="Calibration method")
    cv_folds: int = Field(default=5, ge=2, description="Cross-validation folds for calibration")


class ModelConfig(BaseModel):
    """Model training and configuration."""

    type: str = Field(default="RandomForestClassifier", description="Model type/class name")
    default_params: Dict[str, Any] = Field(default_factory=dict, description="Default model parameters")
    optuna: OptunaConfig = Field(default_factory=OptunaConfig, description="Optuna settings")
    grid_search: GridSearchConfig = Field(default_factory=GridSearchConfig, description="Grid search settings")
    calibration: CalibrationConfig = Field(default_factory=CalibrationConfig, description="Calibration settings")


class SmotencConfig(BaseModel):
    """SMOTENC imbalance handling settings."""

    enabled: bool = Field(default=False, description="Enable SMOTENC")
    k_neighbors: int = Field(default=5, ge=1, description="Number of neighbors")
    sampling_strategy: str = Field(default="auto", description="Sampling strategy")


class ImbalanceConfig(BaseModel):
    """Imbalance handling configuration."""

    strategy: ImbalanceStrategy = Field(default=ImbalanceStrategy.CLASS_WEIGHT, description="Imbalance strategy")
    smotenc: SmotencConfig = Field(default_factory=SmotencConfig, description="SMOTENC settings")


class RiskFloodProbabilityConfig(BaseModel):
    """Flood probability thresholds for risk classification.

    Calibrated from v6 model on 1,660 flood / 3,889 non-flood records.
    """

    critical: float = Field(default=0.75, ge=0.0, le=1.0)
    alert: float = Field(default=0.40, ge=0.0, le=1.0)
    safe_max: float = Field(default=0.10, ge=0.0, le=1.0)


class RiskPrecipitationConfig(BaseModel):
    """Precipitation thresholds aligned with PAGASA Rainfall Warning System."""

    alert_min: float = Field(default=7.5, ge=0.0)
    alert_max: float = Field(default=30.0, ge=0.0)
    humidity_threshold: float = Field(default=82.0, ge=0.0, le=100.0)
    humidity_precip_min: float = Field(default=5.0, ge=0.0)


class RiskRainfall3hConfig(BaseModel):
    """3-hour rainfall accumulation thresholds (PAGASA-aligned)."""

    critical: float = Field(default=65.0, ge=0.0)
    alert: float = Field(default=30.0, ge=0.0)


class RiskTideConfig(BaseModel):
    """Tide risk thresholds."""

    alert_factor: float = Field(default=0.8, ge=0.0, le=1.0)
    critical_combined_factor: float = Field(default=0.7, ge=0.0, le=1.0)
    critical_combined_flood_prob: float = Field(default=0.40, ge=0.0, le=1.0)


class RiskClassificationConfig(BaseModel):
    """Risk classification thresholds — consumed by risk_classifier.py."""

    flood_probability: RiskFloodProbabilityConfig = Field(default_factory=RiskFloodProbabilityConfig)
    precipitation: RiskPrecipitationConfig = Field(default_factory=RiskPrecipitationConfig)
    rainfall_3h: RiskRainfall3hConfig = Field(default_factory=RiskRainfall3hConfig)
    tide: RiskTideConfig = Field(default_factory=RiskTideConfig)


class AlertThresholds(BaseModel):
    """Metric alert thresholds."""

    min_f2_score: float = Field(default=0.80, ge=0.0, le=1.0)
    min_recall: float = Field(default=0.85, ge=0.0, le=1.0)
    max_brier_score: float = Field(default=0.25, ge=0.0, le=1.0)


class MetricsConfig(BaseModel):
    """Metrics tracking configuration."""

    primary: Literal["f1", "f2", "recall", "roc_auc", "accuracy"] = Field(
        default="f2", description="Primary metric for optimization"
    )
    track: List[str] = Field(
        default_factory=lambda: ["accuracy", "precision", "recall", "f1_score", "f2_score", "roc_auc", "brier_score"],
        description="Metrics to track",
    )
    alerts: AlertThresholds = Field(default_factory=AlertThresholds, description="Alert thresholds")


class TemporalCVConfig(BaseModel):
    """Temporal cross-validation settings."""

    enabled: bool = Field(default=True, description="Enable temporal validation")
    n_splits: int = Field(default=5, ge=2, description="Number of temporal splits")
    gap: int = Field(default=0, ge=0, description="Gap between train and test")


class CrossValidationConfig(BaseModel):
    """Cross-validation configuration."""

    folds: int = Field(default=10, ge=2, description="Number of CV folds")
    shuffle: bool = Field(default=True, description="Shuffle before splitting")
    temporal: TemporalCVConfig = Field(default_factory=TemporalCVConfig, description="Temporal CV settings")


class MLflowTagsConfig(BaseModel):
    """MLflow experiment tags."""

    project: str = Field(default="floodingnaque")
    team: str = Field(default="ml-engineering")
    domain: str = Field(default="flood-prediction")
    pipeline: str = Field(default="progressive")


class MLflowConfig(BaseModel):
    """MLflow tracking configuration."""

    tracking_uri: str = Field(default="mlruns", description="MLflow tracking URI")
    experiment_name: str = Field(default="floodingnaque_progressive_training", description="Experiment name")
    auto_log: bool = Field(default=True, description="Enable automatic logging")
    log_models: bool = Field(default=True, description="Log models as artifacts")
    tags: MLflowTagsConfig = Field(default_factory=MLflowTagsConfig, description="Experiment tags")


class PromotionCriteria(BaseModel):
    """Model promotion criteria for a stage."""

    min_f2_score: float = Field(default=0.85, ge=0.0, le=1.0)
    min_f1_score: float = Field(default=0.80, ge=0.0, le=1.0)
    min_roc_auc: float = Field(default=0.85, ge=0.0, le=1.0)
    max_cv_std: float = Field(default=0.05, ge=0.0, le=1.0)


class RetentionConfig(BaseModel):
    """Model artifact retention settings."""

    max_versions_per_stage: int = Field(default=5, ge=1)
    archive_old_models: bool = Field(default=True)


class RegistryConfig(BaseModel):
    """Model registry configuration."""

    models_dir: str = Field(default="models", description="Models directory path")
    stages: List[str] = Field(
        default_factory=lambda: ["development", "staging", "production"], description="Available stages"
    )
    promotion_criteria: Dict[str, PromotionCriteria] = Field(
        default_factory=dict, description="Promotion criteria per stage"
    )
    retention: RetentionConfig = Field(default_factory=RetentionConfig, description="Retention settings")


class PSIConfig(BaseModel):
    """Population Stability Index thresholds."""

    warning_threshold: float = Field(default=0.1, ge=0.0)
    alert_threshold: float = Field(default=0.2, ge=0.0)


class DriftConfig(BaseModel):
    """Drift detection configuration."""

    enabled: bool = Field(default=True, description="Enable drift detection")
    psi: PSIConfig = Field(default_factory=PSIConfig, description="PSI thresholds")
    monitored_features: List[str] = Field(default_factory=list, description="Features to monitor")
    retrain_on: List[str] = Field(
        default_factory=lambda: ["psi_alert", "performance_degradation", "scheduled"], description="Retraining triggers"
    )


class FeatureRange(BaseModel):
    """Feature value range for validation."""

    min: Optional[float] = None
    max: Optional[float] = None
    values: Optional[List[Any]] = None  # For categorical features


class TargetValidation(BaseModel):
    """Target column validation."""

    column: str = Field(default="flood", description="Target column name")
    values: List[int] = Field(default_factory=lambda: [0, 1], description="Valid target values")


class ValidationConfig(BaseModel):
    """Data validation configuration."""

    feature_ranges: Dict[str, FeatureRange] = Field(default_factory=dict, description="Feature value ranges")
    target: TargetValidation = Field(default_factory=TargetValidation, description="Target validation")


class StationConfig(BaseModel):
    """Weather station configuration."""

    name: str = Field(..., description="Station name")
    lat: float = Field(..., ge=-90, le=90, description="Latitude")
    lon: float = Field(..., ge=-180, le=180, description="Longitude")
    elevation_m: float = Field(..., ge=0, description="Elevation in meters")
    notes: Optional[str] = Field(default=None, description="Station notes")


class StackingConfig(BaseModel):
    """Stacking ensemble configuration."""

    enabled: bool = Field(default=True)
    cv_folds: int = Field(default=5, ge=2)
    stack_method: Literal["predict_proba", "predict"] = Field(default="predict_proba")
    passthrough: bool = Field(default=False)


class MetaLearnerConfig(BaseModel):
    """Meta-learner configuration for stacking."""

    type: str = Field(default="LogisticRegression")
    max_iter: int = Field(default=1000, ge=1)
    class_weight: Optional[str] = Field(default="balanced")


class EnsembleConfig(BaseModel):
    """Ensemble model configuration."""

    stacking: StackingConfig = Field(default_factory=StackingConfig)
    meta_learner: MetaLearnerConfig = Field(default_factory=MetaLearnerConfig)
    base_phases: List[int] = Field(default_factory=lambda: [4, 5, 6])
    include_station_models: bool = Field(default=True)


class PhaseConfig(BaseModel):
    """Training phase configuration."""

    name: str = Field(..., description="Phase name")
    description: str = Field(..., description="Phase description")
    data_file: Optional[str] = Field(default=None, description="Data file path")
    data_files: Optional[List[str]] = Field(default=None, description="Multiple data file paths")
    data_type: str = Field(..., description="Data type identifier")
    features: Optional[List[str]] = Field(default=None, description="Feature columns")
    model_type: Optional[str] = Field(default=None, description="Model type override")
    stations: Optional[List[str]] = Field(default=None, description="Station names for station-specific models")
    base_phases: Optional[List[int]] = Field(default=None, description="Base phases for ensemble")
    station_phase: Optional[int] = Field(default=None, description="Station phase for ensemble")
    calibrate: Optional[bool] = Field(default=None, description="Enable calibration for this phase")


class FileLoggingConfig(BaseModel):
    """File logging configuration."""

    enabled: bool = Field(default=True)
    path: str = Field(default="logs/training.log")
    max_bytes: int = Field(default=10485760, ge=1024)  # 10MB default
    backup_count: int = Field(default=5, ge=0)


class ConsoleLoggingConfig(BaseModel):
    """Console logging configuration."""

    enabled: bool = Field(default=True)
    colorize: bool = Field(default=True)


class LoggingConfig(BaseModel):
    """Logging configuration."""

    format: LogFormat = Field(default=LogFormat.JSON)
    level: LogLevel = Field(default=LogLevel.INFO)
    file: FileLoggingConfig = Field(default_factory=FileLoggingConfig)
    console: ConsoleLoggingConfig = Field(default_factory=ConsoleLoggingConfig)


class ResourcesConfig(BaseModel):
    """Resource management configuration."""

    max_memory_gb: int = Field(default=8, ge=1)
    max_workers: int = Field(default=-1, description="-1 for auto (n_cpus - 1)")
    use_gpu: bool = Field(default=False)
    gpu_device: int = Field(default=0, ge=0)


class MonitoringConfig(BaseModel):
    """Training monitoring configuration."""

    max_training_minutes: int = Field(default=60, ge=1)
    warn_training_minutes: int = Field(default=30, ge=1)
    alert_on_degradation: bool = Field(default=True)
    degradation_threshold: float = Field(default=0.05, ge=0.0, le=1.0)


# =============================================================================
# Root Configuration Schema
# =============================================================================


class ConfigSchema(BaseModel):
    """
    Root configuration schema for Floodingnaque training pipeline.

    Validates all YAML configuration on load and provides type-safe access
    to configuration values.
    """

    general: GeneralConfig = Field(default_factory=GeneralConfig)
    data: DataConfig = Field(default_factory=DataConfig)
    model: ModelConfig = Field(default_factory=ModelConfig)
    imbalance: ImbalanceConfig = Field(default_factory=ImbalanceConfig)
    metrics: MetricsConfig = Field(default_factory=MetricsConfig)
    cross_validation: CrossValidationConfig = Field(default_factory=CrossValidationConfig)
    ensemble: EnsembleConfig = Field(default_factory=EnsembleConfig)
    stations: List[StationConfig] = Field(default_factory=list)
    mlflow: MLflowConfig = Field(default_factory=MLflowConfig)
    registry: RegistryConfig = Field(default_factory=RegistryConfig)
    drift: DriftConfig = Field(default_factory=DriftConfig)
    validation: ValidationConfig = Field(default_factory=ValidationConfig)
    phases: Dict[str, PhaseConfig] = Field(default_factory=dict)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    resources: ResourcesConfig = Field(default_factory=ResourcesConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    risk_classification: RiskClassificationConfig = Field(default_factory=RiskClassificationConfig)

    model_config = {"extra": "allow"}  # Allow extra fields for flexibility

    @model_validator(mode="after")
    def validate_cross_references(self) -> "ConfigSchema":
        """Validate cross-references between configuration sections."""
        # Validate ensemble base_phases reference valid phases
        if self.ensemble.base_phases:
            valid_phases = set(int(k.replace("phase_", "")) for k in self.phases.keys() if k.startswith("phase_"))
            for phase_num in self.ensemble.base_phases:
                if phase_num not in valid_phases and valid_phases:
                    pass  # Allow flexible phase references for future additions

        # Validate promotion criteria stages exist in registry stages
        for stage in self.registry.promotion_criteria.keys():
            if stage not in self.registry.stages:
                raise ValueError(f"Promotion criteria defined for unknown stage: {stage}")

        return self


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""

    def __init__(self, message: str, errors: Optional[List[Dict[str, Any]]] = None):
        super().__init__(message)
        self.errors = errors or []


def validate_config(config_dict: Dict[str, Any]) -> ConfigSchema:
    """
    Validate a configuration dictionary against the schema.

    Args:
        config_dict: Raw configuration dictionary loaded from YAML

    Returns:
        ConfigSchema: Validated configuration object

    Raises:
        ConfigValidationError: If validation fails
    """
    try:
        return ConfigSchema.model_validate(config_dict)
    except Exception as e:
        errors: List[Dict[str, Any]] = []
        if hasattr(e, "errors"):
            error_method = e.errors  # type: ignore[union-attr]
            if callable(error_method):
                errors = error_method()  # type: ignore[assignment]
        raise ConfigValidationError(f"Configuration validation failed: {e}", errors=errors) from e


def get_schema_json() -> str:
    """
    Get JSON Schema for the configuration.

    Useful for IDE autocomplete and external validation tools.

    Returns:
        str: JSON Schema as string
    """
    import json

    return json.dumps(ConfigSchema.model_json_schema(), indent=2)


def export_schema_to_file(output_path: Union[str, Path]) -> None:
    """
    Export JSON Schema to a file.

    Args:
        output_path: Path to write the schema file
    """
    output_path = Path(output_path)
    output_path.write_text(get_schema_json())
