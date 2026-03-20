"""
Deep Learning Architectures for Time-Series Flood Prediction.

Implements LSTM and Transformer models that capture temporal dependencies
beyond the rolling-window features used by the existing Random Forest
pipeline.  These models process sequences of daily weather observations
to predict flood probability for the next time step.

Architectures
-------------
1. **FloodLSTM**: Bidirectional LSTM with attention - captures long-range
   temporal dependencies in precipitation and humidity sequences.
2. **FloodTransformer**: Lightweight Transformer encoder - uses multi-head
   self-attention to weigh the importance of each day in the look-back
   window for the flood prediction task.

Both models produce:
- Binary flood classification (0/1)
- Calibrated probability estimate

Dependencies
------------
- PyTorch ≥ 2.0 (``pip install torch``)
- scikit-learn (for evaluation metrics - already in requirements)

Usage
-----
::

    from app.services.deep_learning_models import (
        FloodLSTM,
        FloodTransformer,
        FloodSequenceDataset,
        DeepLearningTrainer,
    )

    # Create dataset from DataFrame
    dataset = FloodSequenceDataset.from_dataframe(df, features, target="flood")

    # Train LSTM
    trainer = DeepLearningTrainer(model_type="lstm", input_dim=len(features))
    metrics = trainer.train(dataset)
    trainer.save("models/flood_lstm.pt")

Author: Floodingnaque Team
Date: 2026-03-02
"""

from __future__ import annotations

import json
import logging
import math
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ── Lazy PyTorch import ─────────────────────────────────────────────────────
_torch_available = False
try:
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader, Dataset, random_split

    _torch_available = True
except ImportError:
    logger.info("PyTorch not installed. Deep learning models unavailable. " "Install with: pip install torch")

# Paths
MODELS_DIR = Path(__file__).resolve().parent.parent.parent / "models"


def _check_torch():
    """Raise if PyTorch is not available."""
    if not _torch_available:
        raise ImportError("PyTorch is required for deep learning models. " "Install with: pip install torch")


# ═════════════════════════════════════════════════════════════════════════════
# Configuration
# ═════════════════════════════════════════════════════════════════════════════


@dataclass
class DeepLearningConfig:
    """Configuration for deep learning model training."""

    # Architecture
    model_type: str = "lstm"  # "lstm" or "transformer"
    input_dim: int = 10  # Number of input features
    hidden_dim: int = 128  # Hidden layer size
    num_layers: int = 2  # Depth of LSTM / Transformer encoder
    num_heads: int = 4  # Transformer attention heads
    dropout: float = 0.3  # Regularisation dropout rate
    bidirectional: bool = True  # Bidirectional LSTM

    # Sequence settings
    sequence_length: int = 14  # Look-back window (days)
    prediction_horizon: int = 1  # Predict 1 day ahead

    # Training
    batch_size: int = 64
    learning_rate: float = 1e-3
    weight_decay: float = 1e-4  # L2 regularisation
    epochs: int = 100
    patience: int = 15  # Early stopping patience
    min_delta: float = 1e-4  # Minimum improvement for early stopping
    class_weight: Optional[float] = None  # Positive class weight (auto if None)

    # Misc
    random_state: int = 42
    device: str = "auto"  # "cpu", "cuda", or "auto"
    save_best_only: bool = True

    def get_device(self) -> "torch.device":
        """Resolve the compute device."""
        _check_torch()
        if self.device == "auto":
            return torch.device("cuda" if torch.cuda.is_available() else "cpu")
        return torch.device(self.device)


# ═════════════════════════════════════════════════════════════════════════════
# Dataset
# ═════════════════════════════════════════════════════════════════════════════


class FloodSequenceDataset:
    """
    Time-series dataset that creates sliding-window sequences for flood prediction.

    Each sample is (X_seq, y) where:
    - X_seq has shape (sequence_length, n_features) - the look-back window
    - y is the binary flood label for the day *after* the window
    """

    def __init__(
        self,
        sequences: np.ndarray,
        targets: np.ndarray,
    ):
        _check_torch()
        self.sequences = torch.FloatTensor(sequences)
        self.targets = torch.FloatTensor(targets)

    def __len__(self):
        return len(self.targets)

    def __getitem__(self, idx):
        return self.sequences[idx], self.targets[idx]

    @classmethod
    def from_dataframe(
        cls,
        df: pd.DataFrame,
        feature_cols: List[str],
        target_col: str = "flood",
        sequence_length: int = 14,
        date_col: str = "date",
        group_col: Optional[str] = None,
    ) -> "FloodSequenceDataset":
        """
        Create a sequence dataset from a pandas DataFrame.

        Parameters
        ----------
        df : pd.DataFrame
            Training data sorted by date.
        feature_cols : list of str
            Feature column names.
        target_col : str
            Binary target column.
        sequence_length : int
            Number of past days per sample.
        date_col : str
            Date column for sorting.
        group_col : str, optional
            If provided, sequences don't cross group boundaries
            (e.g., station_id or barangay).

        Returns
        -------
        FloodSequenceDataset
        """
        _check_torch()
        df = df.copy()
        if date_col in df.columns:
            df = df.sort_values(date_col)

        available = [c for c in feature_cols if c in df.columns]
        if not available:
            raise ValueError("No feature columns found in DataFrame")

        all_sequences: List[np.ndarray] = []
        all_targets: List[float] = []

        groups = [None] if group_col is None or group_col not in df.columns else df[group_col].unique()

        for grp in groups:
            sub = df if grp is None else df[df[group_col] == grp]
            X = sub[available].values.astype(np.float32)
            y = sub[target_col].values.astype(np.float32)

            # Normalise features (per-group z-score)
            means = np.nanmean(X, axis=0)
            stds = np.nanstd(X, axis=0)
            stds[stds == 0] = 1.0
            X = (X - means) / stds

            # Replace NaNs after normalisation
            X = np.nan_to_num(X, nan=0.0)

            for i in range(sequence_length, len(X)):
                seq = X[i - sequence_length : i]
                target = y[i]
                all_sequences.append(seq)
                all_targets.append(target)

        sequences = np.array(all_sequences, dtype=np.float32)
        targets = np.array(all_targets, dtype=np.float32)

        logger.info(
            f"Created sequence dataset: {len(targets)} samples, "
            f"seq_len={sequence_length}, features={len(available)}, "
            f"flood_rate={targets.mean():.3f}"
        )
        return cls(sequences, targets)


# ═════════════════════════════════════════════════════════════════════════════
# LSTM Model
# ═════════════════════════════════════════════════════════════════════════════

if _torch_available:

    class TemporalAttention(nn.Module):
        """
        Additive attention over LSTM hidden states.

        Learns which time steps in the sequence are most important
        for the flood prediction, producing a weighted context vector.
        """

        def __init__(self, hidden_dim: int):
            super().__init__()
            self.attention = nn.Sequential(
                nn.Linear(hidden_dim, hidden_dim // 2),
                nn.Tanh(),
                nn.Linear(hidden_dim // 2, 1),
            )

        def forward(self, lstm_output: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
            """
            Parameters
            ----------
            lstm_output : (batch, seq_len, hidden_dim)

            Returns
            -------
            context : (batch, hidden_dim)
            weights : (batch, seq_len)
            """
            scores = self.attention(lstm_output).squeeze(-1)  # (B, T)
            weights = torch.softmax(scores, dim=-1)  # (B, T)
            context = torch.bmm(weights.unsqueeze(1), lstm_output).squeeze(1)  # (B, H)
            return context, weights

    class FloodLSTM(nn.Module):
        """
        Bidirectional LSTM with temporal attention for flood prediction.

        Architecture
        ------------
        Input → BiLSTM(num_layers) → Temporal Attention → FC → Sigmoid

        The attention mechanism allows the model to focus on the most
        flood-relevant days in the look-back window (e.g., the 2-3 days
        of heaviest rainfall).
        """

        def __init__(self, config: DeepLearningConfig):
            super().__init__()
            self.config = config

            # Input projection
            self.input_proj = nn.Sequential(
                nn.Linear(config.input_dim, config.hidden_dim),
                nn.LayerNorm(config.hidden_dim),
                nn.ReLU(),
                nn.Dropout(config.dropout * 0.5),
            )

            # Bidirectional LSTM
            self.lstm = nn.LSTM(
                input_size=config.hidden_dim,
                hidden_size=config.hidden_dim,
                num_layers=config.num_layers,
                batch_first=True,
                bidirectional=config.bidirectional,
                dropout=config.dropout if config.num_layers > 1 else 0,
            )

            lstm_out_dim = config.hidden_dim * (2 if config.bidirectional else 1)

            # Temporal attention
            self.attention = TemporalAttention(lstm_out_dim)

            # Classification head
            self.classifier = nn.Sequential(
                nn.Linear(lstm_out_dim, config.hidden_dim),
                nn.ReLU(),
                nn.Dropout(config.dropout),
                nn.Linear(config.hidden_dim, config.hidden_dim // 2),
                nn.ReLU(),
                nn.Dropout(config.dropout * 0.5),
                nn.Linear(config.hidden_dim // 2, 1),
            )

        def forward(
            self, x: torch.Tensor, return_attention: bool = False
        ) -> Union[torch.Tensor, Tuple[torch.Tensor, torch.Tensor]]:
            """
            Forward pass.

            Parameters
            ----------
            x : (batch, seq_len, input_dim)
            return_attention : bool
                If True, also return attention weights.

            Returns
            -------
            logits : (batch, 1)
            attn_weights : (batch, seq_len) - only if return_attention=True
            """
            # Project input features
            x = self.input_proj(x)

            # LSTM encoding
            lstm_out, _ = self.lstm(x)

            # Attention pooling
            context, attn_weights = self.attention(lstm_out)

            # Classify
            logits = self.classifier(context)

            if return_attention:
                return logits, attn_weights
            return logits

    # ═════════════════════════════════════════════════════════════════════════
    # Transformer Model
    # ═════════════════════════════════════════════════════════════════════════

    class PositionalEncoding(nn.Module):
        """Sinusoidal positional encoding for Transformer."""

        def __init__(self, d_model: int, max_len: int = 500, dropout: float = 0.1):
            super().__init__()
            self.dropout = nn.Dropout(dropout)

            pe = torch.zeros(max_len, d_model)
            position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
            div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
            pe[:, 0::2] = torch.sin(position * div_term)
            pe[:, 1::2] = torch.cos(position * div_term[: d_model // 2])
            pe = pe.unsqueeze(0)  # (1, max_len, d_model)
            self.register_buffer("pe", pe)

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            x = x + self.pe[:, : x.size(1), :]
            return self.dropout(x)

    class FloodTransformer(nn.Module):
        """
        Transformer encoder for time-series flood prediction.

        Architecture
        ------------
        Input → Linear projection → Positional Encoding →
        TransformerEncoder(N layers) → Global Average Pool → FC → Sigmoid

        Advantages over LSTM:
        - Parallelisable (faster training)
        - Direct attention across all time steps (no vanishing gradient)
        - Self-attention weights are directly interpretable
        """

        def __init__(self, config: DeepLearningConfig):
            super().__init__()
            self.config = config

            d_model = config.hidden_dim
            # Ensure d_model is divisible by num_heads
            if d_model % config.num_heads != 0:
                d_model = config.num_heads * (config.hidden_dim // config.num_heads + 1)

            # Input projection
            self.input_proj = nn.Sequential(
                nn.Linear(config.input_dim, d_model),
                nn.LayerNorm(d_model),
            )

            # Positional encoding (generous max_len to handle variable-length inputs)
            self.pos_encoder = PositionalEncoding(d_model, max_len=500, dropout=config.dropout)

            # Transformer encoder
            encoder_layer = nn.TransformerEncoderLayer(
                d_model=d_model,
                nhead=config.num_heads,
                dim_feedforward=d_model * 4,
                dropout=config.dropout,
                activation="gelu",
                batch_first=True,
                norm_first=True,  # Pre-norm for better training stability
            )
            self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=config.num_layers)

            # CLS token for aggregation
            self.cls_token = nn.Parameter(torch.randn(1, 1, d_model))

            # Classification head
            self.classifier = nn.Sequential(
                nn.LayerNorm(d_model),
                nn.Linear(d_model, d_model // 2),
                nn.GELU(),
                nn.Dropout(config.dropout),
                nn.Linear(d_model // 2, 1),
            )

            self._d_model = d_model

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            """
            Forward pass.

            Parameters
            ----------
            x : (batch, seq_len, input_dim)

            Returns
            -------
            logits : (batch, 1)
            """
            batch_size = x.size(0)

            # Project input
            x = self.input_proj(x)

            # Prepend CLS token
            cls = self.cls_token.expand(batch_size, -1, -1)
            x = torch.cat([cls, x], dim=1)  # (B, 1+T, D)

            # Positional encoding
            x = self.pos_encoder(x)

            # Transformer encoding
            x = self.transformer(x)

            # Use CLS token output for classification
            cls_out = x[:, 0, :]
            logits = self.classifier(cls_out)
            return logits


# ═════════════════════════════════════════════════════════════════════════════
# Trainer
# ═════════════════════════════════════════════════════════════════════════════


class DeepLearningTrainer:
    """
    Training loop for FloodLSTM / FloodTransformer.

    Handles:
    - Train/validation splitting
    - Class-weight balancing for imbalanced flood data
    - Early stopping with patience
    - Learning rate scheduling (cosine annealing)
    - Model checkpointing
    - Metric computation (accuracy, precision, recall, F1, ROC-AUC)
    """

    def __init__(self, config: Optional[DeepLearningConfig] = None):
        _check_torch()
        self.config = config or DeepLearningConfig()
        self.device = self.config.get_device()
        self.model: Optional[nn.Module] = None
        self.training_history: List[Dict[str, float]] = []
        self.best_metrics: Dict[str, float] = {}

        logger.info(f"DeepLearningTrainer using device: {self.device}")

    def _build_model(self) -> nn.Module:
        """Instantiate the model based on config."""
        if self.config.model_type == "lstm":
            model = FloodLSTM(self.config)
        elif self.config.model_type == "transformer":
            model = FloodTransformer(self.config)
        else:
            raise ValueError(f"Unknown model_type: {self.config.model_type}")

        model = model.to(self.device)
        n_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        logger.info(f"Built {self.config.model_type.upper()} model: " f"{n_params:,} trainable parameters")
        return model

    def train(
        self,
        dataset: FloodSequenceDataset,
        val_ratio: float = 0.2,
    ) -> Dict[str, Any]:
        """
        Train the model on the given dataset.

        Parameters
        ----------
        dataset : FloodSequenceDataset
            Full dataset (will be split into train/val).
        val_ratio : float
            Fraction of data for validation.

        Returns
        -------
        dict with final metrics, training history, and model path.
        """
        _check_torch()
        torch.manual_seed(self.config.random_state)
        np.random.seed(self.config.random_state)

        # ── Build model ─────────────────────────────────────────────────────
        self.model = self._build_model()

        # ── Split dataset ───────────────────────────────────────────────────
        val_size = int(len(dataset) * val_ratio)
        train_size = len(dataset) - val_size
        train_ds, val_ds = random_split(
            dataset,
            [train_size, val_size],
            generator=torch.Generator().manual_seed(self.config.random_state),
        )

        train_loader = DataLoader(train_ds, batch_size=self.config.batch_size, shuffle=True, drop_last=True)
        val_loader = DataLoader(val_ds, batch_size=self.config.batch_size, shuffle=False)

        # ── Class weight ────────────────────────────────────────────────────
        pos_weight = self.config.class_weight
        if pos_weight is None:
            # Auto-compute from dataset
            all_targets = dataset.targets.numpy()
            n_pos = all_targets.sum()
            n_neg = len(all_targets) - n_pos
            pos_weight = n_neg / max(n_pos, 1)
            logger.info(f"Auto class weight: {pos_weight:.2f}")

        criterion = nn.BCEWithLogitsLoss(pos_weight=torch.tensor([pos_weight], device=self.device))

        # ── Optimiser & scheduler ───────────────────────────────────────────
        optimizer = torch.optim.AdamW(
            self.model.parameters(),
            lr=self.config.learning_rate,
            weight_decay=self.config.weight_decay,
        )
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=self.config.epochs, eta_min=1e-6)

        # ── Training loop ───────────────────────────────────────────────────
        best_val_loss = float("inf")
        patience_counter = 0
        best_state = None

        for epoch in range(1, self.config.epochs + 1):
            # Train
            self.model.train()
            train_loss = 0.0
            train_batches = 0
            for X_batch, y_batch in train_loader:
                X_batch = X_batch.to(self.device)
                y_batch = y_batch.to(self.device).unsqueeze(1)

                optimizer.zero_grad()
                logits = self.model(X_batch)
                loss = criterion(logits, y_batch)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
                optimizer.step()

                train_loss += loss.item()
                train_batches += 1

            scheduler.step()
            avg_train_loss = train_loss / max(train_batches, 1)

            # Validate
            val_metrics = self._evaluate(val_loader, criterion)
            val_loss = val_metrics["loss"]

            self.training_history.append(
                {
                    "epoch": epoch,
                    "train_loss": avg_train_loss,
                    "val_loss": val_loss,
                    "val_accuracy": val_metrics.get("accuracy", 0),
                    "val_f1": val_metrics.get("f1_score", 0),
                    "lr": scheduler.get_last_lr()[0],
                }
            )

            # Log every 10 epochs
            if epoch % 10 == 0 or epoch == 1:
                logger.info(
                    f"Epoch {epoch}/{self.config.epochs} - "
                    f"train_loss={avg_train_loss:.4f}, "
                    f"val_loss={val_loss:.4f}, "
                    f"val_f1={val_metrics.get('f1_score', 0):.4f}"
                )

            # Early stopping
            if val_loss < best_val_loss - self.config.min_delta:
                best_val_loss = val_loss
                patience_counter = 0
                best_state = {k: v.cpu().clone() for k, v in self.model.state_dict().items()}
                self.best_metrics = val_metrics
            else:
                patience_counter += 1
                if patience_counter >= self.config.patience:
                    logger.info(f"Early stopping at epoch {epoch}")
                    break

        # ── Restore best model ──────────────────────────────────────────────
        if best_state is not None:
            self.model.load_state_dict(best_state)
            logger.info(f"Restored best model (val_loss={best_val_loss:.4f})")

        self.best_metrics["epochs_trained"] = epoch
        return self.best_metrics

    def _evaluate(
        self,
        loader: "DataLoader",
        criterion: "nn.Module",
    ) -> Dict[str, float]:
        """Run evaluation on a DataLoader, return metrics."""
        from sklearn.metrics import (
            accuracy_score,
            f1_score,
            precision_score,
            recall_score,
            roc_auc_score,
        )

        self.model.eval()
        total_loss = 0.0
        all_preds: List[int] = []
        all_targets: List[int] = []
        all_probs: List[float] = []

        with torch.no_grad():
            for X_batch, y_batch in loader:
                X_batch = X_batch.to(self.device)
                y_batch = y_batch.to(self.device).unsqueeze(1)

                logits = self.model(X_batch)
                loss = criterion(logits, y_batch)
                total_loss += loss.item()

                probs = torch.sigmoid(logits).cpu().numpy().flatten()
                preds = (probs >= 0.5).astype(int)
                targets = y_batch.cpu().numpy().flatten().astype(int)

                all_preds.extend(preds)
                all_targets.extend(targets)
                all_probs.extend(probs)

        n_batches = max(len(loader), 1)
        metrics: Dict[str, float] = {"loss": total_loss / n_batches}

        if len(set(all_targets)) > 1:
            metrics["accuracy"] = accuracy_score(all_targets, all_preds)
            metrics["precision"] = precision_score(all_targets, all_preds, zero_division=0)
            metrics["recall"] = recall_score(all_targets, all_preds, zero_division=0)
            metrics["f1_score"] = f1_score(all_targets, all_preds, zero_division=0)
            try:
                metrics["roc_auc"] = roc_auc_score(all_targets, all_probs)
            except ValueError:
                metrics["roc_auc"] = 0.0
        else:
            metrics.update({"accuracy": 0.0, "precision": 0.0, "recall": 0.0, "f1_score": 0.0, "roc_auc": 0.0})

        return metrics

    def predict(self, sequences: np.ndarray, return_proba: bool = True) -> Dict[str, Any]:
        """
        Make predictions on new sequences.

        Parameters
        ----------
        sequences : np.ndarray of shape (n_samples, seq_len, n_features)
        return_proba : bool

        Returns
        -------
        dict with predictions, probabilities.
        """
        _check_torch()
        if self.model is None:
            raise RuntimeError("Model not trained. Call train() first.")

        self.model.eval()
        X = torch.FloatTensor(sequences).to(self.device)

        with torch.no_grad():
            logits = self.model(X)
            probs = torch.sigmoid(logits).cpu().numpy().flatten()
            preds = (probs >= 0.5).astype(int)

        result: Dict[str, Any] = {"predictions": preds.tolist()}
        if return_proba:
            result["probabilities"] = probs.tolist()
        return result

    def save(self, path: Optional[str] = None) -> str:
        """Save model, config, and training history."""
        _check_torch()
        if self.model is None:
            raise RuntimeError("No model to save")

        if path is None:
            MODELS_DIR.mkdir(parents=True, exist_ok=True)
            path = str(MODELS_DIR / f"flood_{self.config.model_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pt")

        checkpoint = {
            "model_state_dict": self.model.state_dict(),
            "config": {
                "model_type": self.config.model_type,
                "input_dim": self.config.input_dim,
                "hidden_dim": self.config.hidden_dim,
                "num_layers": self.config.num_layers,
                "num_heads": self.config.num_heads,
                "dropout": self.config.dropout,
                "bidirectional": self.config.bidirectional,
                "sequence_length": self.config.sequence_length,
            },
            "metrics": self.best_metrics,
            "training_history": self.training_history,
            "saved_at": datetime.now().isoformat(),
        }

        torch.save(checkpoint, path)

        # Also save metadata as JSON sidecar
        meta_path = Path(path).with_suffix(".json")
        with open(meta_path, "w") as f:
            json.dump(
                {
                    "model_type": self.config.model_type,
                    "input_dim": self.config.input_dim,
                    "hidden_dim": self.config.hidden_dim,
                    "sequence_length": self.config.sequence_length,
                    "metrics": {k: float(v) for k, v in self.best_metrics.items()},
                    "epochs_trained": self.best_metrics.get("epochs_trained", 0),
                    "saved_at": datetime.now().isoformat(),
                },
                f,
                indent=2,
            )

        logger.info(f"Model saved to {path}")
        return path

    @classmethod
    def load(cls, path: str) -> "DeepLearningTrainer":
        """Load a saved model checkpoint."""
        _check_torch()
        checkpoint = torch.load(path, map_location="cpu", weights_only=False)

        cfg_dict = checkpoint["config"]
        config = DeepLearningConfig(
            model_type=cfg_dict["model_type"],
            input_dim=cfg_dict["input_dim"],
            hidden_dim=cfg_dict["hidden_dim"],
            num_layers=cfg_dict["num_layers"],
            num_heads=cfg_dict.get("num_heads", 4),
            dropout=cfg_dict.get("dropout", 0.3),
            bidirectional=cfg_dict.get("bidirectional", True),
            sequence_length=cfg_dict.get("sequence_length", 14),
        )

        trainer = cls(config=config)
        trainer.model = trainer._build_model()
        trainer.model.load_state_dict(checkpoint["model_state_dict"])
        trainer.best_metrics = checkpoint.get("metrics", {})
        trainer.training_history = checkpoint.get("training_history", [])

        logger.info(f"Loaded {config.model_type.upper()} model from {path}")
        return trainer


# ═════════════════════════════════════════════════════════════════════════════
# Integration with UnifiedTrainer
# ═════════════════════════════════════════════════════════════════════════════


def train_deep_learning_model(
    df: pd.DataFrame,
    feature_cols: List[str],
    target_col: str = "flood",
    model_type: str = "lstm",
    sequence_length: int = 14,
    epochs: int = 100,
    output_dir: Optional[str] = None,
    **kwargs,
) -> Dict[str, Any]:
    """
    Convenience function to train a deep learning model from a DataFrame.

    This integrates with the existing training pipeline:
    - Takes the same DataFrame format as Random Forest training
    - Returns comparable metrics dictionary
    - Saves model in the standard models directory

    Parameters
    ----------
    df : pd.DataFrame
        Training data with feature columns and target.
    feature_cols : list of str
        Feature column names.
    target_col : str
        Binary target column.
    model_type : str
        "lstm" or "transformer".
    sequence_length : int
        Look-back window in days.
    epochs : int
        Maximum training epochs.
    output_dir : str, optional
        Override model output directory.

    Returns
    -------
    dict with model_path, metrics, features, model_type.
    """
    _check_torch()

    available = [c for c in feature_cols if c in df.columns]
    logger.info(f"Training {model_type.upper()} with {len(available)} features")

    config = DeepLearningConfig(
        model_type=model_type,
        input_dim=len(available),
        sequence_length=sequence_length,
        epochs=epochs,
        **{k: v for k, v in kwargs.items() if hasattr(DeepLearningConfig, k)},
    )

    # Create dataset
    dataset = FloodSequenceDataset.from_dataframe(df, available, target_col=target_col, sequence_length=sequence_length)

    # Train
    trainer = DeepLearningTrainer(config=config)
    metrics = trainer.train(dataset)

    # Save
    out_dir = Path(output_dir) if output_dir else MODELS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    model_path = str(out_dir / f"flood_{model_type}_model.pt")
    trainer.save(model_path)

    return {
        "model_path": model_path,
        "model_type": model_type,
        "metrics": {k: round(float(v), 4) for k, v in metrics.items()},
        "features": available,
        "sequence_length": sequence_length,
        "architecture": {
            "hidden_dim": config.hidden_dim,
            "num_layers": config.num_layers,
            "num_heads": config.num_heads if model_type == "transformer" else None,
            "bidirectional": config.bidirectional if model_type == "lstm" else None,
        },
    }
