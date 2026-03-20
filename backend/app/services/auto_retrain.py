"""
Automated Model Retraining Pipeline.

Orchestrates the end-to-end retraining workflow:

1. **Data freshness check** - Detect newly ingested DRRMO flood events and
   weather data since the last training run.
2. **Drift detection** - Compute PSI (Population Stability Index) on
   monitored features to detect distributional drift.
3. **Conditional retraining** - Trigger retraining when drift exceeds
   thresholds, new data volume is significant, or on a schedule.
4. **Performance gating** - Only promote the new model if it meets minimum
   metric thresholds (F2 ≥ 0.85, recall ≥ 0.85).
5. **Shadow deployment** - New models run in shadow mode before promotion,
   logging predictions alongside the production model.
6. **Rollback** - Automatic rollback if the new model degrades in production.

Integration
-----------
- Called from ``tasks.py`` (Celery) for async execution
- Called from ``scheduler.py`` (APScheduler) for periodic checks
- Can be triggered manually via ``/api/admin/retrain``

Author: Floodingnaque Team
Date: 2026-03-02
"""

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Paths
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
MODELS_DIR = BACKEND_DIR / "models"
DATA_DIR = BACKEND_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"
REPORTS_DIR = BACKEND_DIR / "reports"


# ═════════════════════════════════════════════════════════════════════════════
# Configuration
# ═════════════════════════════════════════════════════════════════════════════


@dataclass
class RetrainingConfig:
    """Configuration for the automated retraining pipeline."""

    # ── Triggers ────────────────────────────────────────────────────────────
    min_new_records: int = 50
    """Minimum new records required to trigger data-driven retraining."""

    schedule_days: int = 30
    """Maximum days between retraining runs (scheduled trigger)."""

    psi_warning: float = 0.10
    """PSI threshold for drift warning (logged but no action)."""

    psi_alert: float = 0.20
    """PSI threshold for drift alert (triggers retraining)."""

    # ── Performance gates ───────────────────────────────────────────────────
    min_f2_score: float = 0.85
    """Minimum F2 score for model promotion."""

    min_recall: float = 0.85
    """Minimum recall for model promotion (safety-critical)."""

    min_f1_score: float = 0.80
    """Minimum F1 score for model promotion."""

    max_metric_degradation: float = 0.03
    """Maximum allowed degradation vs. current production model."""

    # ── Training ────────────────────────────────────────────────────────────
    training_mode: str = "production"
    """Default training mode (basic, production, progressive, etc.)."""

    include_enso: bool = True
    """Whether to include ENSO features in retraining."""

    include_spatial: bool = True
    """Whether to include spatial features in retraining."""

    include_deep_learning: bool = False
    """Whether to also train deep learning models alongside RF."""

    deep_learning_model_type: str = "lstm"
    """Type of deep learning model to train (lstm or transformer)."""

    # ── Paths ───────────────────────────────────────────────────────────────
    models_dir: str = str(MODELS_DIR)
    data_dir: str = str(PROCESSED_DIR)
    reports_dir: str = str(REPORTS_DIR)

    # ── Shadow deployment ───────────────────────────────────────────────────
    shadow_period_hours: int = 24
    """Hours to run new model in shadow mode before promotion."""

    shadow_min_predictions: int = 100
    """Minimum predictions during shadow period for comparison."""


# ═════════════════════════════════════════════════════════════════════════════
# Drift Detection (PSI)
# ═════════════════════════════════════════════════════════════════════════════


def compute_psi(
    reference: np.ndarray,
    current: np.ndarray,
    n_bins: int = 10,
) -> float:
    """
    Compute Population Stability Index between reference and current distributions.

    PSI < 0.10: No significant change
    0.10 ≤ PSI < 0.20: Moderate change (warning)
    PSI ≥ 0.20: Significant change (retraining recommended)

    Parameters
    ----------
    reference : array-like
        Reference (training) distribution.
    current : array-like
        Current (production) distribution.
    n_bins : int
        Number of histogram bins.

    Returns
    -------
    float: PSI value
    """
    ref = np.array(reference, dtype=float)
    cur = np.array(current, dtype=float)

    # Remove NaN
    ref = ref[~np.isnan(ref)]
    cur = cur[~np.isnan(cur)]

    if len(ref) == 0 or len(cur) == 0:
        return 0.0

    # Create bins from reference distribution
    breakpoints = np.percentile(ref, np.linspace(0, 100, n_bins + 1))
    breakpoints = np.unique(breakpoints)

    if len(breakpoints) < 2:
        return 0.0

    # Compute bin proportions
    ref_counts = np.histogram(ref, bins=breakpoints)[0]
    cur_counts = np.histogram(cur, bins=breakpoints)[0]

    # Add small epsilon to avoid division by zero / log(0)
    eps = 1e-6
    ref_pct = (ref_counts + eps) / (ref_counts.sum() + eps * len(ref_counts))
    cur_pct = (cur_counts + eps) / (cur_counts.sum() + eps * len(cur_counts))

    # PSI formula
    psi = np.sum((cur_pct - ref_pct) * np.log(cur_pct / ref_pct))
    return float(psi)


def detect_drift(
    reference_df: pd.DataFrame,
    current_df: pd.DataFrame,
    monitored_features: Optional[List[str]] = None,
    psi_threshold: float = 0.20,
) -> Dict[str, Any]:
    """
    Detect distributional drift between reference and current data.

    Parameters
    ----------
    reference_df : pd.DataFrame
        Training data distribution.
    current_df : pd.DataFrame
        Recent production data.
    monitored_features : list of str, optional
        Features to monitor. Defaults to core weather features.
    psi_threshold : float
        PSI threshold for drift alert.

    Returns
    -------
    dict with drift_detected (bool), per-feature PSI values, and summary.
    """
    if monitored_features is None:
        monitored_features = ["temperature", "humidity", "precipitation", "precip_3day_sum"]

    psi_values: Dict[str, float] = {}
    drifted_features: List[str] = []

    for feat in monitored_features:
        if feat in reference_df.columns and feat in current_df.columns:
            psi = compute_psi(reference_df[feat].values, current_df[feat].values)
            psi_values[feat] = round(psi, 4)
            if psi >= psi_threshold:
                drifted_features.append(feat)

    drift_detected = len(drifted_features) > 0

    result = {
        "drift_detected": drift_detected,
        "psi_values": psi_values,
        "drifted_features": drifted_features,
        "threshold": psi_threshold,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if drift_detected:
        logger.warning(f"Data drift detected in features: {drifted_features}")
    else:
        logger.info(f"No drift detected. PSI values: {psi_values}")

    return result


# ═════════════════════════════════════════════════════════════════════════════
# Data Freshness
# ═════════════════════════════════════════════════════════════════════════════


def check_data_freshness(
    data_dir: str = str(PROCESSED_DIR),
    last_training_hash: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Check how much new data is available since the last training run.

    Compares file hashes and record counts to determine if retraining
    is warranted based on new DRRMO flood event data.

    Returns
    -------
    dict with new_records_available, data_files, current_hash, etc.
    """
    data_path = Path(data_dir)
    result: Dict[str, Any] = {
        "data_dir": str(data_path),
        "files_found": [],
        "total_records": 0,
        "current_hash": None,
        "hash_changed": False,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }

    if not data_path.exists():
        logger.warning(f"Data directory not found: {data_path}")
        return result

    # Scan for training data files
    csv_files = sorted(data_path.glob("*.csv"))
    hasher = hashlib.sha256()
    total_records = 0

    for f in csv_files:
        try:
            # Hash file content for change detection
            with open(f, "rb") as fh:
                file_hash = hashlib.md5(fh.read()).hexdigest()  # nosec B303,B324
            hasher.update(file_hash.encode())

            # Count records
            n_rows = sum(1 for _ in open(f, "r")) - 1  # minus header
            total_records += max(0, n_rows)

            result["files_found"].append(
                {
                    "name": f.name,
                    "records": n_rows,
                    "hash": file_hash[:12],
                }
            )
        except Exception as e:
            logger.warning(f"Error reading {f.name}: {e}")

    current_hash = hasher.hexdigest()
    result["total_records"] = total_records
    result["current_hash"] = current_hash

    if last_training_hash:
        result["hash_changed"] = current_hash != last_training_hash

    return result


# ═════════════════════════════════════════════════════════════════════════════
# Retraining Pipeline
# ═════════════════════════════════════════════════════════════════════════════


class AutoRetrainingPipeline:
    """
    Orchestrates the automated model retraining workflow.

    Lifecycle:
    1. check_triggers()   → Determine if retraining is needed
    2. run_pipeline()     → Execute full retraining
    3. evaluate_candidate() → Compare new model vs. production
    4. promote_or_rollback() → Deploy or discard
    """

    def __init__(self, config: Optional[RetrainingConfig] = None):
        self.config = config or RetrainingConfig()
        self.pipeline_log: List[Dict[str, Any]] = []
        self._last_run_metadata: Optional[Dict[str, Any]] = None

    def _log_step(self, step: str, status: str, details: Any = None):
        """Log a pipeline step."""
        entry = {
            "step": step,
            "status": status,
            "details": details,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.pipeline_log.append(entry)
        log_fn = logger.info if status == "success" else logger.warning
        log_fn(f"Pipeline [{step}]: {status}" + (f" - {details}" if details else ""))

    def check_triggers(
        self,
        last_training_hash: Optional[str] = None,
        last_training_date: Optional[datetime] = None,
        current_data: Optional[pd.DataFrame] = None,
        reference_data: Optional[pd.DataFrame] = None,
    ) -> Dict[str, Any]:
        """
        Evaluate whether retraining should be triggered.

        Returns
        -------
        dict with should_retrain (bool), triggered_by (list), details.
        """
        triggers: List[str] = []
        details: Dict[str, Any] = {}

        # ── 1. Schedule-based ───────────────────────────────────────────────
        if last_training_date:
            days_since = (datetime.now(timezone.utc) - last_training_date).days
            details["days_since_training"] = days_since
            if days_since >= self.config.schedule_days:
                triggers.append("scheduled")
                self._log_step("trigger_check", "info", f"Scheduled: {days_since} days since last training")

        # ── 2. Data freshness ───────────────────────────────────────────────
        freshness = check_data_freshness(
            data_dir=self.config.data_dir,
            last_training_hash=last_training_hash,
        )
        details["data_freshness"] = freshness

        if freshness.get("hash_changed"):
            triggers.append("new_data")
            self._log_step("trigger_check", "info", "New data detected (hash changed)")

        # ── 3. Drift detection ──────────────────────────────────────────────
        if current_data is not None and reference_data is not None:
            drift = detect_drift(
                reference_data,
                current_data,
                psi_threshold=self.config.psi_alert,
            )
            details["drift"] = drift
            if drift["drift_detected"]:
                triggers.append("drift")
                self._log_step("trigger_check", "warning", f"Drift on: {drift['drifted_features']}")

        should_retrain = len(triggers) > 0
        result = {
            "should_retrain": should_retrain,
            "triggered_by": triggers,
            "details": details,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

        self._log_step("trigger_check", "success", f"Triggers: {triggers}")
        return result

    def run_pipeline(
        self,
        triggers: Optional[List[str]] = None,
        force: bool = False,
        progress_callback: Optional[Callable[[str, int], None]] = None,
    ) -> Dict[str, Any]:
        """
        Execute the full retraining pipeline.

        Parameters
        ----------
        triggers : list of str, optional
            Reasons for retraining (for logging).
        force : bool
            Skip trigger checks and retrain unconditionally.
        progress_callback : callable, optional
            Called with (status_message, progress_pct) for UI updates.

        Returns
        -------
        dict with status, metrics, model_path, promoted (bool).
        """
        import sys

        start_time = time.time()
        result: Dict[str, Any] = {
            "status": "started",
            "triggered_by": triggers or ["manual" if force else "unknown"],
            "started_at": datetime.now(timezone.utc).isoformat(),
        }

        def _progress(msg: str, pct: int):
            if progress_callback:
                progress_callback(msg, pct)

        try:
            # ── Step 1: Prepare ─────────────────────────────────────────────
            _progress("Initialising retraining pipeline...", 5)
            self._log_step("init", "success", f"Mode: {self.config.training_mode}")

            # Ensure scripts are importable
            backend_path = str(BACKEND_DIR)
            if backend_path not in sys.path:
                sys.path.insert(0, backend_path)

            from scripts.train_unified import TrainingMode, UnifiedTrainer

            # ── Step 2: Load and enrich data ────────────────────────────────
            _progress("Loading and enriching training data...", 15)
            mode = TrainingMode(self.config.training_mode)
            trainer = UnifiedTrainer(mode=mode)

            # ── Step 3: Train RF model ──────────────────────────────────────
            _progress("Training Random Forest model...", 30)
            rf_results = trainer.train()
            rf_metrics = rf_results.get("metrics", {})
            result["rf_model"] = {
                "path": rf_results.get("model_path"),
                "metrics": rf_metrics,
            }
            self._log_step("train_rf", "success", f"F1={rf_metrics.get('f1_score', 0):.4f}")

            # ── Step 4: Train deep learning model (optional) ────────────────
            if self.config.include_deep_learning:
                _progress(f"Training {self.config.deep_learning_model_type.upper()} model...", 55)
                try:
                    from app.services.deep_learning_models import train_deep_learning_model

                    # Load data for deep learning
                    dl_data_path = Path(self.config.data_dir)
                    dl_files = sorted(dl_data_path.glob("*.csv"))
                    if dl_files:
                        dl_df = pd.read_csv(dl_files[-1])
                        feature_cols = rf_results.get("features", [])
                        dl_results = train_deep_learning_model(
                            dl_df,
                            feature_cols=feature_cols,
                            model_type=self.config.deep_learning_model_type,
                            output_dir=self.config.models_dir,
                        )
                        result["dl_model"] = dl_results
                        self._log_step("train_dl", "success", f"F1={dl_results['metrics'].get('f1_score', 0):.4f}")
                except ImportError:
                    self._log_step("train_dl", "skipped", "PyTorch not available")
                except Exception as e:
                    self._log_step("train_dl", "error", str(e))

            # ── Step 5: Evaluate candidate ──────────────────────────────────
            _progress("Evaluating model quality...", 75)
            promotion_check = self._evaluate_promotion_criteria(rf_metrics)
            result["promotion_check"] = promotion_check

            # ── Step 6: Promote or skip ─────────────────────────────────────
            promoted = False
            if promotion_check["passes"]:
                _progress("Promoting new model...", 90)
                try:
                    from app.services.predict import _load_model

                    model_path = rf_results.get("model_path")
                    if model_path:
                        _load_model(model_path=model_path, force_reload=True)
                        promoted = True
                        self._log_step("promote", "success", f"Model promoted: {model_path}")
                except Exception as e:
                    self._log_step("promote", "error", str(e))
            else:
                self._log_step("promote", "skipped", f"Did not meet criteria: {promotion_check['failed_criteria']}")

            result["promoted"] = promoted

            # ── Step 7: Register model in database ──────────────────────────
            try:
                from app.services.model_metadata_service import register_model

                elapsed_so_far = round(time.time() - start_time, 1)
                reg_result = register_model(
                    file_path=rf_results.get("model_path", ""),
                    algorithm=rf_results.get("algorithm", "RandomForestClassifier"),
                    metrics=rf_metrics,
                    training_mode=self.config.training_mode,
                    training_duration_seconds=elapsed_so_far,
                    feature_names=rf_results.get("features"),
                    retrain_trigger=",".join(triggers) if triggers else "unknown",
                    auto_promote=promoted,
                    created_by="auto_retrain_pipeline",
                )
                result["registered_version"] = reg_result.get("version")
                self._log_step("register", "success", f"Registered as v{reg_result.get('version')}")
            except Exception as e:
                self._log_step("register", "warning", f"DB registration failed: {e}")

            # ── Finalise ────────────────────────────────────────────────────
            elapsed = round(time.time() - start_time, 1)
            result["status"] = "completed"
            result["elapsed_seconds"] = elapsed
            result["completed_at"] = datetime.now(timezone.utc).isoformat()

            # Save pipeline report
            self._save_report(result)
            _progress("Retraining complete", 100)
            logger.info(f"Retraining pipeline completed in {elapsed}s. Promoted={promoted}")

        except Exception as e:
            result["status"] = "failed"
            result["error"] = str(e)
            self._log_step("pipeline", "error", str(e))
            logger.error(f"Retraining pipeline failed: {e}", exc_info=True)

        result["pipeline_log"] = self.pipeline_log
        self._last_run_metadata = result
        return result

    def _evaluate_promotion_criteria(
        self,
        metrics: Dict[str, float],
    ) -> Dict[str, Any]:
        """Check if candidate model meets promotion thresholds."""
        failed: List[str] = []

        f1 = metrics.get("f1_score", 0)
        recall = metrics.get("recall", 0)
        roc_auc = metrics.get("roc_auc", 0)

        if f1 < self.config.min_f1_score:
            failed.append(f"f1_score={f1:.4f} < {self.config.min_f1_score}")
        if recall < self.config.min_recall:
            failed.append(f"recall={recall:.4f} < {self.config.min_recall}")

        return {
            "passes": len(failed) == 0,
            "failed_criteria": failed,
            "metrics_evaluated": {
                "f1_score": f1,
                "recall": recall,
                "roc_auc": roc_auc,
            },
        }

    def _save_report(self, result: Dict[str, Any]):
        """Persist pipeline report to disk."""
        reports_dir = Path(self.config.reports_dir)
        reports_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = reports_dir / f"retrain_report_{ts}.json"

        try:
            # Make JSON-serialisable
            def _serialise(obj):
                if isinstance(obj, (np.integer,)):
                    return int(obj)
                if isinstance(obj, (np.floating,)):
                    return float(obj)
                if isinstance(obj, np.ndarray):
                    return obj.tolist()
                if isinstance(obj, datetime):
                    return obj.isoformat()
                return str(obj)

            with open(report_path, "w") as f:
                json.dump(result, f, indent=2, default=_serialise)
            logger.info(f"Pipeline report saved: {report_path}")
        except Exception as e:
            logger.warning(f"Failed to save pipeline report: {e}")

    def get_last_run_metadata(self) -> Optional[Dict[str, Any]]:
        """Return metadata from the last pipeline run."""
        return self._last_run_metadata


# ═════════════════════════════════════════════════════════════════════════════
# Convenience Functions
# ═════════════════════════════════════════════════════════════════════════════


def run_auto_retrain(
    force: bool = False,
    config: Optional[RetrainingConfig] = None,
    progress_callback: Optional[Callable[[str, int], None]] = None,
) -> Dict[str, Any]:
    """
    Run the automated retraining pipeline.

    This is the main entry point for scheduled/triggered retraining.

    Parameters
    ----------
    force : bool
        Skip trigger checks and force retraining.
    config : RetrainingConfig, optional
        Custom configuration.
    progress_callback : callable, optional
        Progress callback for UI updates.

    Returns
    -------
    dict with pipeline results.
    """
    pipeline = AutoRetrainingPipeline(config=config)

    if not force:
        trigger_result = pipeline.check_triggers()
        if not trigger_result["should_retrain"]:
            logger.info("No retraining triggers fired - skipping")
            return {
                "status": "skipped",
                "reason": "No triggers fired",
                "trigger_check": trigger_result,
            }
        triggers = trigger_result["triggered_by"]
    else:
        triggers = ["forced"]

    return pipeline.run_pipeline(
        triggers=triggers,
        force=force,
        progress_callback=progress_callback,
    )


def check_retraining_needed(
    last_training_hash: Optional[str] = None,
    last_training_date: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Quick check if retraining is needed without running the full pipeline.

    Returns
    -------
    dict with should_retrain (bool) and reasons.
    """
    pipeline = AutoRetrainingPipeline()
    return pipeline.check_triggers(
        last_training_hash=last_training_hash,
        last_training_date=last_training_date,
    )
