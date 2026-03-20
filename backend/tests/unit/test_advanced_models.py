"""
Tests for Advanced ML Models - XGBoost, LightGBM, Ensemble, and Comparison.

Tests cover:
- XGBoost creation, training, and prediction
- LightGBM creation, training, and prediction
- Ensemble (VotingClassifier) creation and prediction
- Model comparison head-to-head
- Graceful fallback when XGBoost / LightGBM are not installed
- Config dataclasses
"""

import json

import numpy as np
import pandas as pd
import pytest
from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split

# ═════════════════════════════════════════════════════════════════════════════
# Helper
# ═════════════════════════════════════════════════════════════════════════════


def _try_import(module: str) -> bool:
    """Check if a module can be imported."""
    try:
        __import__(module)
        return True
    except ImportError:
        return False


# ═════════════════════════════════════════════════════════════════════════════
# Fixtures
# ═════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def flood_dataset():
    """Create a synthetic binary classification dataset mimicking flood data."""
    X, y = make_classification(
        n_samples=400,
        n_features=10,
        n_informative=6,
        n_redundant=2,
        n_classes=2,
        weights=[0.7, 0.3],  # imbalanced like real flood data
        random_state=42,
    )
    feature_names = [
        "temperature",
        "humidity",
        "precipitation",
        "is_monsoon_season",
        "month",
        "temp_humidity_interaction",
        "humidity_precip_interaction",
        "temp_precip_interaction",
        "monsoon_precip_interaction",
        "saturation_risk",
    ]
    X_df = pd.DataFrame(X, columns=feature_names)
    y_series = pd.Series(y, name="flood")
    return X_df, y_series


@pytest.fixture
def train_test_data(flood_dataset):
    """Split flood dataset into train/test."""
    X, y = flood_dataset
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )
    return X_train, X_test, y_train, y_test


# ═════════════════════════════════════════════════════════════════════════════
# XGBoost Tests
# ═════════════════════════════════════════════════════════════════════════════


class TestXGBoost:
    """Tests for the XGBoost classifier wrapper."""

    def test_xgboost_available(self):
        """XGBoost should be importable."""
        from app.services.advanced_models import _XGBOOST_AVAILABLE

        # We only test that the check exists; actual availability depends on env
        assert isinstance(_XGBOOST_AVAILABLE, bool)

    @pytest.mark.skipif(not _try_import("xgboost"), reason="XGBoost not installed")
    def test_create_xgboost_model(self, train_test_data):
        from app.services.advanced_models import XGBoostConfig, create_xgboost_model

        X_train, X_test, y_train, y_test = train_test_data
        model = create_xgboost_model(y_train=y_train)
        assert model is not None

        # Train and predict
        model.fit(X_train, y_train)
        preds = model.predict(X_test)
        assert len(preds) == len(X_test)
        assert set(np.unique(preds)).issubset({0, 1})

    @pytest.mark.skipif(not _try_import("xgboost"), reason="XGBoost not installed")
    def test_xgboost_scale_pos_weight(self, train_test_data):
        """scale_pos_weight should be auto-computed from label distribution."""
        from app.services.advanced_models import create_xgboost_model

        _, _, y_train, _ = train_test_data
        model = create_xgboost_model(y_train=y_train)
        # Should be > 1 for imbalanced data
        assert model.get_params()["scale_pos_weight"] > 1.0

    @pytest.mark.skipif(not _try_import("xgboost"), reason="XGBoost not installed")
    def test_xgboost_config(self):
        from app.services.advanced_models import XGBoostConfig

        config = XGBoostConfig(n_estimators=100, max_depth=4, learning_rate=0.1)
        params = config.to_xgb_params()
        assert params["n_estimators"] == 100
        assert params["max_depth"] == 4
        assert params["learning_rate"] == 0.1

    @pytest.mark.skipif(not _try_import("xgboost"), reason="XGBoost not installed")
    def test_xgboost_predict_proba(self, train_test_data):
        from app.services.advanced_models import create_xgboost_model

        X_train, X_test, y_train, _ = train_test_data
        model = create_xgboost_model(y_train=y_train)
        model.fit(X_train, y_train)
        proba = model.predict_proba(X_test)
        assert proba.shape == (len(X_test), 2)
        assert np.allclose(proba.sum(axis=1), 1.0)


# ═════════════════════════════════════════════════════════════════════════════
# LightGBM Tests
# ═════════════════════════════════════════════════════════════════════════════


class TestLightGBM:
    """Tests for the LightGBM classifier wrapper."""

    def test_lightgbm_available(self):
        from app.services.advanced_models import _LIGHTGBM_AVAILABLE

        assert isinstance(_LIGHTGBM_AVAILABLE, bool)

    @pytest.mark.skipif(not _try_import("lightgbm"), reason="LightGBM not installed")
    def test_create_lightgbm_model(self, train_test_data):
        from app.services.advanced_models import create_lightgbm_model

        X_train, X_test, y_train, y_test = train_test_data
        model = create_lightgbm_model()
        assert model is not None

        model.fit(X_train, y_train)
        preds = model.predict(X_test)
        assert len(preds) == len(X_test)
        assert set(np.unique(preds)).issubset({0, 1})

    @pytest.mark.skipif(not _try_import("lightgbm"), reason="LightGBM not installed")
    def test_lightgbm_config(self):
        from app.services.advanced_models import LightGBMConfig

        config = LightGBMConfig(n_estimators=100, num_leaves=31, learning_rate=0.1)
        params = config.to_lgbm_params()
        assert params["n_estimators"] == 100
        assert params["num_leaves"] == 31
        assert params["is_unbalance"] is True

    @pytest.mark.skipif(not _try_import("lightgbm"), reason="LightGBM not installed")
    def test_lightgbm_predict_proba(self, train_test_data):
        from app.services.advanced_models import create_lightgbm_model

        X_train, X_test, y_train, _ = train_test_data
        model = create_lightgbm_model()
        model.fit(X_train, y_train)
        proba = model.predict_proba(X_test)
        assert proba.shape == (len(X_test), 2)
        assert np.allclose(proba.sum(axis=1), 1.0)


# ═════════════════════════════════════════════════════════════════════════════
# Ensemble Tests
# ═════════════════════════════════════════════════════════════════════════════


class TestEnsemble:
    """Tests for the Ensemble Voting Classifier."""

    @pytest.mark.skipif(
        not (_try_import("xgboost") and _try_import("lightgbm")),
        reason="XGBoost and LightGBM required for ensemble",
    )
    def test_create_ensemble(self, train_test_data):
        from app.services.advanced_models import create_ensemble_model

        _, _, y_train, _ = train_test_data
        model = create_ensemble_model(y_train=y_train)
        assert model is not None
        assert len(model.estimators) >= 2

    @pytest.mark.skipif(
        not (_try_import("xgboost") and _try_import("lightgbm")),
        reason="XGBoost and LightGBM required",
    )
    def test_ensemble_train_predict(self, train_test_data):
        from app.services.advanced_models import create_ensemble_model

        X_train, X_test, y_train, _ = train_test_data
        model = create_ensemble_model(y_train=y_train)
        model.fit(X_train, y_train)
        preds = model.predict(X_test)
        assert len(preds) == len(X_test)

    @pytest.mark.skipif(
        not (_try_import("xgboost") and _try_import("lightgbm")),
        reason="XGBoost and LightGBM required",
    )
    def test_ensemble_soft_voting_proba(self, train_test_data):
        from app.services.advanced_models import create_ensemble_model

        X_train, X_test, y_train, _ = train_test_data
        model = create_ensemble_model(y_train=y_train)
        model.fit(X_train, y_train)
        proba = model.predict_proba(X_test)
        assert proba.shape == (len(X_test), 2)

    def test_ensemble_config(self):
        from app.services.advanced_models import EnsembleConfig

        config = EnsembleConfig(
            voting="soft",
            weights=[2, 1, 1],
            include_rf=True,
            include_xgboost=True,
            include_lightgbm=True,
        )
        assert config.voting == "soft"
        assert config.weights == [2, 1, 1]

    def test_ensemble_requires_two_estimators(self):
        """Ensemble should fail if fewer than 2 estimators are available."""
        from app.services.advanced_models import EnsembleConfig, create_ensemble_model

        config = EnsembleConfig(
            include_rf=True,
            include_xgboost=False,
            include_lightgbm=False,
            include_gradient_boosting=False,
        )
        with pytest.raises(ValueError, match="at least 2"):
            create_ensemble_model(ensemble_config=config)


# ═════════════════════════════════════════════════════════════════════════════
# Model Comparison Tests
# ═════════════════════════════════════════════════════════════════════════════


class TestModelComparison:
    """Tests for the compare_models() function."""

    @pytest.mark.skipif(
        not (_try_import("xgboost") and _try_import("lightgbm")),
        reason="All frameworks needed for comparison",
    )
    def test_compare_models(self, train_test_data, tmp_path):
        from app.services.advanced_models import compare_models

        X_train, X_test, y_train, y_test = train_test_data
        result = compare_models(
            X_train=X_train,
            y_train=y_train,
            X_test=X_test,
            y_test=y_test,
            cv_folds=3,
            output_dir=str(tmp_path),
        )

        assert "results" in result
        assert "best_model" in result
        assert "comparison_table" in result
        assert len(result["results"]) >= 3  # RF + XGB + LGBM + ensemble

    @pytest.mark.skipif(
        not (_try_import("xgboost") and _try_import("lightgbm")),
        reason="All frameworks needed",
    )
    def test_comparison_metrics(self, train_test_data, tmp_path):
        from app.services.advanced_models import compare_models

        X_train, X_test, y_train, y_test = train_test_data
        result = compare_models(
            X_train=X_train,
            y_train=y_train,
            X_test=X_test,
            y_test=y_test,
            cv_folds=3,
            output_dir=str(tmp_path),
        )

        for r in result["results"]:
            metrics = r["metrics"]
            assert 0 <= metrics["accuracy"] <= 1
            assert 0 <= metrics["f1_score"] <= 1
            assert 0 <= metrics["roc_auc"] <= 1
            assert r["training_time_seconds"] >= 0

    def test_compare_rf_only(self, train_test_data, tmp_path):
        """Comparison with only RF should still work."""
        from app.services.advanced_models import compare_models

        X_train, X_test, y_train, y_test = train_test_data
        result = compare_models(
            X_train=X_train,
            y_train=y_train,
            X_test=X_test,
            y_test=y_test,
            include_xgboost=False,
            include_lightgbm=False,
            include_ensemble=False,
            cv_folds=3,
            output_dir=str(tmp_path),
        )

        assert len(result["results"]) == 1
        assert result["best_model"] == "RandomForest"


# ═════════════════════════════════════════════════════════════════════════════
# Availability Helpers
# ═════════════════════════════════════════════════════════════════════════════


class TestAvailability:
    """Tests for get_available_algorithms()."""

    def test_get_available_algorithms(self):
        from app.services.advanced_models import get_available_algorithms

        algos = get_available_algorithms()
        assert "random_forest" in algos
        assert "xgboost" in algos
        assert "lightgbm" in algos
        assert "ensemble" in algos
        assert algos["random_forest"] is True  # always available
