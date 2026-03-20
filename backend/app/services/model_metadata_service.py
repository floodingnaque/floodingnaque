"""
Model Metadata Service - DB persistence for model training metadata.

Provides a service layer between training pipelines and the ``model_registry``
database table, supporting:

- Registering new model versions after training
- Promoting / retiring versions
- Querying version history and lineage
- Tracking retraining triggers and parent versions

Author: Floodingnaque Team
Date: 2026-03-02
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _next_version(session) -> int:
    """Get the next available integer version number."""
    from app.models.model_registry import ModelRegistry

    max_ver = session.query(ModelRegistry.version).order_by(ModelRegistry.version.desc()).first()
    return (max_ver[0] + 1) if max_ver else 1


def register_model(
    *,
    file_path: str,
    algorithm: str = "RandomForest",
    metrics: Optional[Dict[str, float]] = None,
    training_mode: Optional[str] = None,
    training_duration_seconds: Optional[float] = None,
    dataset_size: Optional[int] = None,
    dataset_path: Optional[str] = None,
    parameters: Optional[Dict[str, Any]] = None,
    feature_names: Optional[List[str]] = None,
    feature_importance: Optional[Dict[str, float]] = None,
    ensemble_members: Optional[List[str]] = None,
    comparison_report: Optional[Dict[str, Any]] = None,
    retrain_trigger: Optional[str] = None,
    parent_version: Optional[int] = None,
    training_data_hash: Optional[str] = None,
    semantic_version: Optional[str] = None,
    notes: Optional[str] = None,
    created_by: str = "system",
    auto_promote: bool = False,
) -> Dict[str, Any]:
    """
    Register a newly trained model in the database.

    Parameters
    ----------
    file_path : str
        Path to the saved model file (.joblib or .pt).
    algorithm : str
        Algorithm name (RandomForest, XGBClassifier, LGBMClassifier,
        VotingClassifier, FloodLSTM, FloodTransformer, etc.).
    metrics : dict
        Performance metrics (accuracy, precision, recall, f1_score, etc.).
    training_mode : str
        Training mode (basic, production, xgboost, lightgbm, ensemble, comparison).
    training_duration_seconds : float
        How long the training took.
    dataset_size : int
        Number of training records.
    parameters : dict
        Model hyperparameters.
    feature_names : list of str
        Feature columns used.
    feature_importance : dict
        Feature importance scores.
    ensemble_members : list of str
        Sub-model names if ensemble.
    comparison_report : dict
        Comparison report if comparison mode.
    retrain_trigger : str
        What triggered training (manual, scheduled, drift, new_data).
    parent_version : int
        Version this was retrained from.
    training_data_hash : str
        SHA-256 hash of training data.
    semantic_version : str
        Semantic version string (e.g., "2.1.0").
    notes : str
        Free-text notes.
    created_by : str
        User or system identifier.
    auto_promote : bool
        If True, immediately promote this version (deactivate others).

    Returns
    -------
    dict with version, id, and registration details.
    """
    from app.models.db import get_db_session
    from app.models.model_registry import ModelRegistry

    metrics = metrics or {}

    # Compute model file checksum
    model_checksum = None
    try:
        p = Path(file_path)
        if p.exists():
            model_checksum = hashlib.sha256(p.read_bytes()).hexdigest()
    except Exception as e:
        logger.warning(f"Could not compute model checksum: {e}")

    try:
        with get_db_session() as session:
            version = _next_version(session)

            record = ModelRegistry(
                version=version,
                semantic_version=semantic_version,
                file_path=file_path,
                algorithm=algorithm,
                accuracy=metrics.get("accuracy"),
                precision_score=metrics.get("precision"),
                recall_score=metrics.get("recall"),
                f1_score=metrics.get("f1_score"),
                f2_score=metrics.get("f2_score"),
                roc_auc=metrics.get("roc_auc"),
                cv_mean=metrics.get("cv_mean"),
                cv_std=metrics.get("cv_std"),
                training_date=datetime.now(timezone.utc),
                training_duration_seconds=training_duration_seconds,
                training_mode=training_mode,
                dataset_size=dataset_size,
                dataset_path=dataset_path,
                parameters=json.dumps(parameters) if parameters else None,
                feature_names=json.dumps(feature_names) if feature_names else None,
                feature_importance=json.dumps(feature_importance) if feature_importance else None,
                ensemble_members=json.dumps(ensemble_members) if ensemble_members else None,
                comparison_report=json.dumps(comparison_report) if comparison_report else None,
                retrain_trigger=retrain_trigger,
                parent_version=parent_version,
                training_data_hash=training_data_hash,
                model_checksum=model_checksum,
                notes=notes,
                created_by=created_by,
                is_active=False,
            )

            session.add(record)

            if auto_promote:
                # Deactivate all others
                session.query(ModelRegistry).filter(
                    ModelRegistry.version != version,
                    ModelRegistry.is_active.is_(True),
                ).update(
                    {
                        "is_active": False,
                        "retired_at": datetime.now(timezone.utc),
                    },
                    synchronize_session="fetch",
                )
                record.is_active = True
                record.promoted_at = datetime.now(timezone.utc)

            session.commit()

            result = record.to_dict()
            logger.info(
                f"Model v{version} registered: algorithm={algorithm}, "
                f"f1={metrics.get('f1_score', 'N/A')}, active={record.is_active}"
            )
            return result

    except Exception as e:
        logger.error(f"Failed to register model: {e}", exc_info=True)
        # Return a minimal result so training pipeline doesn't fail
        return {
            "version": None,
            "error": str(e),
            "file_path": file_path,
            "algorithm": algorithm,
        }


def promote_version(version: int, promoted_by: str = "system") -> Dict[str, Any]:
    """
    Promote a model version to active, retiring the current active version.

    Parameters
    ----------
    version : int
        Version number to promote.
    promoted_by : str
        Who/what initiated the promotion.

    Returns
    -------
    dict with promotion details.
    """
    from app.models.db import get_db_session
    from app.models.model_registry import ModelRegistry

    try:
        with get_db_session() as session:
            record = session.query(ModelRegistry).filter_by(version=version).first()
            if not record:
                return {"success": False, "error": f"Version {version} not found"}

            # Retire current active models
            now = datetime.now(timezone.utc)
            retired = (
                session.query(ModelRegistry)
                .filter(
                    ModelRegistry.is_active.is_(True),
                    ModelRegistry.version != version,
                )
                .update(
                    {"is_active": False, "retired_at": now},
                    synchronize_session="fetch",
                )
            )

            record.is_active = True
            record.promoted_at = now
            record.notes = (record.notes or "") + f"\nPromoted by {promoted_by} at {now.isoformat()}"
            session.commit()

            logger.info(f"Model v{version} promoted (retired {retired} previous version(s))")
            return {
                "success": True,
                "version": version,
                "retired_count": retired,
                "promoted_at": now.isoformat(),
            }

    except Exception as e:
        logger.error(f"Failed to promote version {version}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


def retire_version(version: int) -> Dict[str, Any]:
    """Retire (deactivate) a specific model version."""
    from app.models.db import get_db_session
    from app.models.model_registry import ModelRegistry

    try:
        with get_db_session() as session:
            record = session.query(ModelRegistry).filter_by(version=version).first()
            if not record:
                return {"success": False, "error": f"Version {version} not found"}

            record.is_active = False
            record.retired_at = datetime.now(timezone.utc)
            session.commit()

            return {"success": True, "version": version, "retired_at": record.retired_at.isoformat()}

    except Exception as e:
        logger.error(f"Failed to retire version {version}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


def get_active_version() -> Optional[Dict[str, Any]]:
    """Get the currently active model version."""
    from app.models.db import get_db_session
    from app.models.model_registry import ModelRegistry

    try:
        with get_db_session() as session:
            record = session.query(ModelRegistry).filter_by(is_active=True).first()
            return record.to_dict() if record else None
    except Exception as e:
        logger.error(f"Failed to get active version: {e}", exc_info=True)
        return None


def get_version(version: int) -> Optional[Dict[str, Any]]:
    """Get a specific model version by number."""
    from app.models.db import get_db_session
    from app.models.model_registry import ModelRegistry

    try:
        with get_db_session() as session:
            record = session.query(ModelRegistry).filter_by(version=version).first()
            return record.to_dict() if record else None
    except Exception as e:
        logger.error(f"Failed to get version {version}: {e}", exc_info=True)
        return None


def list_versions(
    limit: int = 50,
    algorithm: Optional[str] = None,
    active_only: bool = False,
) -> List[Dict[str, Any]]:
    """
    List model versions with optional filters.

    Parameters
    ----------
    limit : int
        Maximum number of versions to return.
    algorithm : str, optional
        Filter by algorithm name.
    active_only : bool
        If True, only return active versions.

    Returns
    -------
    list of version dicts, ordered by version descending.
    """
    from app.models.db import get_db_session
    from app.models.model_registry import ModelRegistry

    try:
        with get_db_session() as session:
            query = session.query(ModelRegistry)
            if algorithm:
                query = query.filter(ModelRegistry.algorithm == algorithm)
            if active_only:
                query = query.filter(ModelRegistry.is_active.is_(True))
            records = query.order_by(ModelRegistry.version.desc()).limit(limit).all()
            return [r.to_dict() for r in records]
    except Exception as e:
        logger.error(f"Failed to list versions: {e}", exc_info=True)
        return []


def get_version_lineage(version: int) -> List[Dict[str, Any]]:
    """
    Trace the retraining lineage of a model version.

    Follows ``parent_version`` links to build the full lineage chain.

    Returns
    -------
    list of version dicts from oldest ancestor to the given version.
    """
    from app.models.db import get_db_session
    from app.models.model_registry import ModelRegistry

    lineage: List[Dict[str, Any]] = []
    try:
        with get_db_session() as session:
            current = version
            visited = set()
            while current and current not in visited:
                visited.add(current)
                record = session.query(ModelRegistry).filter_by(version=current).first()
                if not record:
                    break
                lineage.append(record.to_dict())
                current = record.parent_version

        lineage.reverse()  # oldest first
        return lineage
    except Exception as e:
        logger.error(f"Failed to trace lineage for v{version}: {e}", exc_info=True)
        return []


def get_algorithm_summary() -> Dict[str, Any]:
    """
    Get a summary of model versions grouped by algorithm.

    Returns counts, best F1, and active version per algorithm.
    """
    from app.models.db import get_db_session
    from app.models.model_registry import ModelRegistry
    from sqlalchemy import func

    try:
        with get_db_session() as session:
            rows = (
                session.query(
                    ModelRegistry.algorithm,
                    func.count(ModelRegistry.id).label("count"),
                    func.max(ModelRegistry.f1_score).label("best_f1"),
                    func.max(ModelRegistry.version).label("latest_version"),
                )
                .group_by(ModelRegistry.algorithm)
                .all()
            )

            summary = {}
            for algo, count, best_f1, latest in rows:
                active = session.query(ModelRegistry.version).filter_by(algorithm=algo, is_active=True).first()
                summary[algo] = {
                    "count": count,
                    "best_f1": float(best_f1) if best_f1 else None,
                    "latest_version": latest,
                    "active_version": active[0] if active else None,
                }

            return summary
    except Exception as e:
        logger.error(f"Failed to get algorithm summary: {e}", exc_info=True)
        return {}
