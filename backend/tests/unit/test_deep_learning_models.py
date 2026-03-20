"""
Tests for Deep Learning Models - LSTM, Transformer, dataset, training.

Tests that require PyTorch are skipped when torch is not installed.
"""

from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pytest

# Conditional torch import
try:
    import torch

    _torch_available = True
except ImportError:
    _torch_available = False

needs_torch = pytest.mark.skipif(not _torch_available, reason="PyTorch not installed")


# ═════════════════════════════════════════════════════════════════════════════
# DeepLearningConfig
# ═════════════════════════════════════════════════════════════════════════════


class TestDeepLearningConfig:
    """These tests do NOT require PyTorch - config is plain Python."""

    def test_config_defaults(self):
        from app.services.deep_learning_models import DeepLearningConfig

        config = DeepLearningConfig()
        assert config.sequence_length == 14
        assert config.hidden_dim == 128
        assert config.num_layers == 2
        assert config.model_type == "lstm"
        assert config.batch_size == 64
        assert config.learning_rate == 1e-3
        assert config.dropout == 0.3

    def test_config_custom(self):
        from app.services.deep_learning_models import DeepLearningConfig

        config = DeepLearningConfig(
            model_type="transformer",
            hidden_dim=256,
            num_heads=8,
            epochs=50,
        )
        assert config.model_type == "transformer"
        assert config.hidden_dim == 256
        assert config.num_heads == 8
        assert config.epochs == 50


# ═════════════════════════════════════════════════════════════════════════════
# FloodSequenceDataset (via from_dataframe factory)
# ═════════════════════════════════════════════════════════════════════════════


@needs_torch
class TestFloodSequenceDataset:
    """Tests for sliding-window dataset creation via from_dataframe."""

    def _make_df(self, n=100, n_features=5):
        dates = pd.date_range("2020-01-01", periods=n, freq="D")
        df = pd.DataFrame(
            np.random.randn(n, n_features).astype(np.float32),
            columns=[f"feat_{i}" for i in range(n_features)],
        )
        df["date"] = dates
        df["flood"] = np.random.randint(0, 2, n).astype(np.float32)
        return df

    def test_dataset_length(self):
        from app.services.deep_learning_models import FloodSequenceDataset

        n_samples, n_features, seq_len = 100, 5, 14
        df = self._make_df(n=n_samples, n_features=n_features)
        feature_cols = [f"feat_{i}" for i in range(n_features)]
        ds = FloodSequenceDataset.from_dataframe(df, feature_cols, target_col="flood", sequence_length=seq_len)
        assert len(ds) == n_samples - seq_len

    def test_dataset_shapes(self):
        from app.services.deep_learning_models import FloodSequenceDataset

        n_samples, n_features, seq_len = 50, 8, 7
        df = self._make_df(n=n_samples, n_features=n_features)
        feature_cols = [f"feat_{i}" for i in range(n_features)]
        ds = FloodSequenceDataset.from_dataframe(df, feature_cols, target_col="flood", sequence_length=seq_len)
        x_seq, y_val = ds[0]
        assert x_seq.shape == (seq_len, n_features)
        assert y_val.shape == ()

    def test_raw_constructor(self):
        """Test direct constructor with pre-windowed data."""
        from app.services.deep_learning_models import FloodSequenceDataset

        sequences = np.random.randn(10, 7, 5).astype(np.float32)
        targets = np.random.randint(0, 2, 10).astype(np.float32)
        ds = FloodSequenceDataset(sequences, targets)
        assert len(ds) == 10
        x_seq, y_val = ds[0]
        assert x_seq.shape == (7, 5)


# ═════════════════════════════════════════════════════════════════════════════
# Model Architecture
# ═════════════════════════════════════════════════════════════════════════════


@needs_torch
class TestFloodLSTM:
    """Tests for LSTM model forward pass."""

    def test_output_shape(self):
        from app.services.deep_learning_models import DeepLearningConfig, FloodLSTM

        config = DeepLearningConfig(model_type="lstm", input_dim=10, hidden_dim=64, num_layers=2)
        model = FloodLSTM(config)
        batch = torch.randn(4, 14, 10)  # (batch, seq, features)
        out = model(batch)
        assert out.shape == (4, 1)

    def test_deterministic_eval(self):
        from app.services.deep_learning_models import DeepLearningConfig, FloodLSTM

        config = DeepLearningConfig(model_type="lstm", input_dim=5, hidden_dim=32, num_layers=1, dropout=0.0)
        model = FloodLSTM(config)
        model.eval()
        batch = torch.randn(2, 7, 5)
        with torch.no_grad():
            out1 = model(batch)
            out2 = model(batch)
        torch.testing.assert_close(out1, out2)


@needs_torch
class TestFloodTransformer:
    """Tests for Transformer model forward pass."""

    def test_output_shape(self):
        from app.services.deep_learning_models import DeepLearningConfig, FloodTransformer

        config = DeepLearningConfig(model_type="transformer", input_dim=10, hidden_dim=64, num_heads=4, num_layers=2)
        model = FloodTransformer(config)
        batch = torch.randn(4, 14, 10)
        out = model(batch)
        assert out.shape == (4, 1)

    def test_different_sequence_lengths(self):
        from app.services.deep_learning_models import DeepLearningConfig, FloodTransformer

        config = DeepLearningConfig(model_type="transformer", input_dim=8, hidden_dim=32, num_heads=4, num_layers=1)
        model = FloodTransformer(config)
        model.eval()
        for seq_len in [7, 14, 30]:
            batch = torch.randn(2, seq_len, 8)
            with torch.no_grad():
                out = model(batch)
            assert out.shape == (2, 1)


# ═════════════════════════════════════════════════════════════════════════════
# Training Smoke Test (via convenience function)
# ═════════════════════════════════════════════════════════════════════════════


@needs_torch
class TestDeepLearningTraining:
    """Smoke test: small dataset, 2 epochs, using train_deep_learning_model."""

    def _make_data(self, n=100, n_features=5):
        dates = pd.date_range("2020-01-01", periods=n, freq="D")
        df = pd.DataFrame(
            np.random.randn(n, n_features),
            columns=[f"feat_{i}" for i in range(n_features)],
        )
        df["date"] = dates
        df["flood"] = np.random.randint(0, 2, n)
        return df

    def test_train_lstm_via_convenience(self):
        from app.services.deep_learning_models import train_deep_learning_model

        df = self._make_data(n=60, n_features=4)
        feature_cols = [c for c in df.columns if c.startswith("feat_")]
        result = train_deep_learning_model(
            df,
            feature_cols=feature_cols,
            target_col="flood",
            model_type="lstm",
            sequence_length=7,
            epochs=2,
            hidden_dim=16,
            num_layers=1,
            batch_size=8,
        )
        assert "model_path" in result
        assert "metrics" in result
        assert result["model_type"] == "lstm"

    def test_train_transformer_via_convenience(self):
        from app.services.deep_learning_models import train_deep_learning_model

        df = self._make_data(n=60, n_features=4)
        feature_cols = [c for c in df.columns if c.startswith("feat_")]
        result = train_deep_learning_model(
            df,
            feature_cols=feature_cols,
            target_col="flood",
            model_type="transformer",
            sequence_length=7,
            epochs=2,
            hidden_dim=16,
            num_heads=2,
            num_layers=1,
            batch_size=8,
        )
        assert "model_path" in result
        assert result["metrics"] is not None

    def test_trainer_with_dataset(self):
        """Test DeepLearningTrainer.train() with a properly built dataset."""
        from app.services.deep_learning_models import (
            DeepLearningConfig,
            DeepLearningTrainer,
            FloodSequenceDataset,
        )

        df = self._make_data(n=60, n_features=4)
        feature_cols = [c for c in df.columns if c.startswith("feat_")]
        config = DeepLearningConfig(
            model_type="lstm",
            input_dim=len(feature_cols),
            hidden_dim=16,
            num_layers=1,
            epochs=2,
            sequence_length=7,
            batch_size=8,
        )
        dataset = FloodSequenceDataset.from_dataframe(df, feature_cols, target_col="flood", sequence_length=7)
        trainer = DeepLearningTrainer(config)
        metrics = trainer.train(dataset)
        assert "loss" in metrics
        assert "epochs_trained" in metrics
