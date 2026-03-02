"""
Tests for Model Metadata Service - DB persistence of model training metadata.

Uses an in-memory SQLite database to avoid requiring a running PostgreSQL server.
"""

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


# ═════════════════════════════════════════════════════════════════════════════
# Fixtures
# ═════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def db_session():
    """Create an in-memory SQLite test database with model_registry table."""
    from app.models.db import Base
    from app.models.model_registry import ModelRegistry  # noqa: F401 - ensures table registered

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def mock_db_session(db_session):
    """Patch get_db_session to use our test session."""
    from contextlib import contextmanager

    @contextmanager
    def _get_db_session():
        yield db_session

    # The service uses lazy imports: `from app.models.db import get_db_session`
    # inside each function.  We need to patch the source module.
    with patch("app.models.db.get_db_session", _get_db_session):
        yield db_session


# ═════════════════════════════════════════════════════════════════════════════
# Registration Tests
# ═════════════════════════════════════════════════════════════════════════════

class TestRegisterModel:
    """Tests for register_model()."""

    def test_register_basic_model(self, mock_db_session):
        from app.services.model_metadata_service import register_model

        result = register_model(
            file_path="/models/flood_rf_model.joblib",
            algorithm="RandomForestClassifier",
            metrics={"accuracy": 0.95, "f1_score": 0.93, "recall": 0.92, "roc_auc": 0.97},
            training_mode="basic",
            created_by="test",
        )

        assert result["version"] == 1
        assert result["algorithm"] == "RandomForestClassifier"
        assert result["metrics"]["f1_score"] == 0.93

    def test_register_xgboost_model(self, mock_db_session):
        from app.services.model_metadata_service import register_model

        result = register_model(
            file_path="/models/flood_xgb_model.joblib",
            algorithm="XGBClassifier",
            metrics={"accuracy": 0.96, "f1_score": 0.94, "roc_auc": 0.98},
            training_mode="xgboost",
            created_by="test",
        )

        assert result["version"] == 1
        assert result["algorithm"] == "XGBClassifier"
        assert result["training_mode"] == "xgboost"

    def test_register_ensemble_model(self, mock_db_session):
        from app.services.model_metadata_service import register_model

        result = register_model(
            file_path="/models/flood_ensemble_model.joblib",
            algorithm="VotingClassifier",
            metrics={"f1_score": 0.95},
            ensemble_members=["rf", "xgb", "lgbm"],
            training_mode="ensemble",
        )

        assert result["version"] == 1
        assert result["ensemble_members"] == ["rf", "xgb", "lgbm"]

    def test_auto_increment_version(self, mock_db_session):
        from app.services.model_metadata_service import register_model

        r1 = register_model(file_path="/models/v1.joblib", algorithm="RF")
        r2 = register_model(file_path="/models/v2.joblib", algorithm="XGB")
        r3 = register_model(file_path="/models/v3.joblib", algorithm="LGBM")

        assert r1["version"] == 1
        assert r2["version"] == 2
        assert r3["version"] == 3

    def test_auto_promote(self, mock_db_session):
        from app.services.model_metadata_service import register_model

        r1 = register_model(file_path="/models/v1.joblib", auto_promote=True)
        assert r1["is_active"] is True

        r2 = register_model(file_path="/models/v2.joblib", auto_promote=True)
        assert r2["is_active"] is True

        # v1 should be retired
        from app.models.model_registry import ModelRegistry
        v1 = mock_db_session.query(ModelRegistry).filter_by(version=1).first()
        assert v1.is_active is False

    def test_register_with_feature_names(self, mock_db_session):
        from app.services.model_metadata_service import register_model

        features = ["temperature", "humidity", "precipitation"]
        result = register_model(
            file_path="/models/v1.joblib",
            feature_names=features,
        )

        assert result["feature_names"] == features

    def test_register_with_retrain_trigger(self, mock_db_session):
        from app.services.model_metadata_service import register_model

        result = register_model(
            file_path="/models/v1.joblib",
            retrain_trigger="drift",
            parent_version=None,
        )

        assert result["retrain_trigger"] == "drift"


# ═════════════════════════════════════════════════════════════════════════════
# Promotion / Retirement Tests
# ═════════════════════════════════════════════════════════════════════════════

class TestPromoteRetire:
    """Tests for promote_version() and retire_version()."""

    def test_promote_version(self, mock_db_session):
        from app.services.model_metadata_service import (
            promote_version,
            register_model,
        )

        register_model(file_path="/v1.joblib")
        register_model(file_path="/v2.joblib")

        result = promote_version(2, promoted_by="admin")
        assert result["success"] is True
        assert result["version"] == 2

    def test_promote_nonexistent_version(self, mock_db_session):
        from app.services.model_metadata_service import promote_version

        result = promote_version(999)
        assert result["success"] is False

    def test_retire_version(self, mock_db_session):
        from app.services.model_metadata_service import (
            register_model,
            retire_version,
        )

        register_model(file_path="/v1.joblib", auto_promote=True)
        result = retire_version(1)
        assert result["success"] is True


# ═════════════════════════════════════════════════════════════════════════════
# Query Tests
# ═════════════════════════════════════════════════════════════════════════════

class TestQueryVersions:
    """Tests for version querying functions."""

    def test_list_versions(self, mock_db_session):
        from app.services.model_metadata_service import (
            list_versions,
            register_model,
        )

        register_model(file_path="/v1.joblib", algorithm="RF")
        register_model(file_path="/v2.joblib", algorithm="XGB")
        register_model(file_path="/v3.joblib", algorithm="LGBM")

        versions = list_versions()
        assert len(versions) == 3
        # Should be ordered descending
        assert versions[0]["version"] == 3

    def test_list_versions_filter_algorithm(self, mock_db_session):
        from app.services.model_metadata_service import (
            list_versions,
            register_model,
        )

        register_model(file_path="/v1.joblib", algorithm="RF")
        register_model(file_path="/v2.joblib", algorithm="XGB")

        versions = list_versions(algorithm="XGB")
        assert len(versions) == 1
        assert versions[0]["algorithm"] == "XGB"

    def test_get_active_version(self, mock_db_session):
        from app.services.model_metadata_service import (
            get_active_version,
            register_model,
        )

        register_model(file_path="/v1.joblib", auto_promote=True)
        active = get_active_version()
        assert active is not None
        assert active["version"] == 1
        assert active["is_active"] is True

    def test_get_active_version_none(self, mock_db_session):
        from app.services.model_metadata_service import get_active_version

        active = get_active_version()
        assert active is None

    def test_get_version(self, mock_db_session):
        from app.services.model_metadata_service import (
            get_version,
            register_model,
        )

        register_model(file_path="/v1.joblib", algorithm="RF")
        v = get_version(1)
        assert v is not None
        assert v["algorithm"] == "RF"

    def test_get_version_lineage(self, mock_db_session):
        from app.services.model_metadata_service import (
            get_version_lineage,
            register_model,
        )

        register_model(file_path="/v1.joblib", algorithm="RF")
        register_model(file_path="/v2.joblib", algorithm="XGB", parent_version=1)
        register_model(file_path="/v3.joblib", algorithm="LGBM", parent_version=2)

        lineage = get_version_lineage(3)
        assert len(lineage) == 3
        assert lineage[0]["version"] == 1  # oldest ancestor first
        assert lineage[2]["version"] == 3

    def test_get_algorithm_summary(self, mock_db_session):
        from app.services.model_metadata_service import (
            get_algorithm_summary,
            register_model,
        )

        register_model(file_path="/v1.joblib", algorithm="RF", metrics={"f1_score": 0.9})
        register_model(file_path="/v2.joblib", algorithm="RF", metrics={"f1_score": 0.92})
        register_model(file_path="/v3.joblib", algorithm="XGB", metrics={"f1_score": 0.94})

        summary = get_algorithm_summary()
        assert "RF" in summary
        assert "XGB" in summary
        assert summary["RF"]["count"] == 2
        assert summary["RF"]["best_f1"] == 0.92
        assert summary["XGB"]["count"] == 1


# ═════════════════════════════════════════════════════════════════════════════
# ModelRegistry ORM Tests
# ═════════════════════════════════════════════════════════════════════════════

class TestModelRegistryORM:
    """Tests for the ModelRegistry ORM model itself."""

    def test_to_dict(self, db_session):
        from app.models.model_registry import ModelRegistry

        record = ModelRegistry(
            version=1,
            file_path="/models/test.joblib",
            algorithm="RandomForestClassifier",
            accuracy=0.95,
            f1_score=0.93,
            is_active=True,
        )
        db_session.add(record)
        db_session.commit()

        d = record.to_dict()
        assert d["version"] == 1
        assert d["algorithm"] == "RandomForestClassifier"
        assert d["metrics"]["accuracy"] == 0.95
        assert d["is_active"] is True

    def test_repr(self, db_session):
        from app.models.model_registry import ModelRegistry

        record = ModelRegistry(
            version=42,
            file_path="/test.joblib",
            algorithm="XGBClassifier",
            f1_score=0.95,
            is_active=False,
        )
        assert "42" in repr(record)
        assert "XGBClassifier" in repr(record)
