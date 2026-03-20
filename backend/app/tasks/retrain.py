"""
Celery task for ensemble model retraining.

Triggered manually via the admin API or on a schedule.  Loads the
latest training data, validates it, trains a new ensemble, and
saves the artifact to the model registry.
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


def retrain_ensemble(
    data_path: str,
    version: str = "v1",
    cv_folds: int = 10,
    grid_search: bool = False,
) -> Dict[str, Any]:
    """
    Retrain the ensemble model on the given dataset.

    This function is designed to be called from a Celery task or
    directly from the admin API.  It loads the CSV, validates it,
    trains the ensemble, and returns the artifact metadata.

    Args:
        data_path: Path to the training CSV file.
        version: Version label for the new model.
        cv_folds: Number of cross-validation folds.
        grid_search: Whether to run hyperparameter search.

    Returns:
        Dict with artifact metadata or error information.
    """
    import pandas as pd
    from app.ml.dataset_validator import DatasetValidator
    from app.ml.ensemble_model import FEATURE_NAMES, EnsembleTrainer

    # Validate dataset
    validator = DatasetValidator()
    validation = validator.validate_file(data_path)
    if not validation.is_valid:
        logger.error("Dataset validation failed: %s", validation.errors)
        return {"status": "error", "errors": validation.errors}

    # Load data
    df = pd.read_csv(data_path)

    # Ensure feature columns exist
    available_features = [f for f in FEATURE_NAMES if f in df.columns]
    if len(available_features) < 5:
        return {
            "status": "error",
            "errors": [f"Only {len(available_features)} of {len(FEATURE_NAMES)} features available"],
        }

    X = df[available_features]
    y = df["flood_occurred"]

    # Train
    trainer = EnsembleTrainer(cv_folds=cv_folds)
    artifact = trainer.train(X, y, version=version, grid_search=grid_search)

    logger.info("Retrain complete: %s", artifact.version)

    return {
        "status": "success",
        "artifact": artifact.to_dict(),
    }
