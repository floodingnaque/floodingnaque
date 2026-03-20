"""
Basic Model Evaluation Script
=============================

.. deprecated:: 1.0.0
    This script is deprecated. Use the unified CLI instead:

    python -m scripts evaluate                    # Basic evaluation
    python -m scripts evaluate --save-plots       # With plots

    Or use the UnifiedEvaluator class:

    from scripts.evaluate_unified import UnifiedEvaluator
    evaluator = UnifiedEvaluator()
    results = evaluator.evaluate()

Evaluate the trained model and generate metrics.
"""

import warnings

warnings.warn(
    "evaluate_model.py is deprecated. Use 'python -m scripts evaluate' or UnifiedEvaluator instead.",
    DeprecationWarning,
    stacklevel=2,
)

import os
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

# Resolve paths relative to backend directory
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
MODELS_DIR = BACKEND_DIR / "models"
DATA_DIR = BACKEND_DIR / "data"


def evaluate_model(model_path=None, data_path=None):
    """Evaluate the trained model and generate metrics."""

    # Use default paths relative to backend directory
    if model_path is None:
        model_path = MODELS_DIR / "flood_rf_model.joblib"
    else:
        model_path = Path(model_path)

    if data_path is None:
        # Use real processed data from v2 preprocessing pipeline
        data_path = DATA_DIR / "processed" / "cumulative_v2_up_to_2025.csv"
    else:
        data_path = Path(data_path)

    # Load model and data with proper error handling
    if not model_path.exists():
        raise FileNotFoundError(f"Model file not found: {model_path}")

    if not data_path.exists():
        raise FileNotFoundError(f"Data file not found: {data_path}")

    try:
        model = joblib.load(model_path)
    except Exception as e:
        raise IOError(f"Failed to load model from {model_path}: {e}") from e

    try:
        data = pd.read_csv(data_path)
    except pd.errors.EmptyDataError:
        raise ValueError(f"Data file is empty: {data_path}")
    except pd.errors.ParserError as e:
        raise ValueError(f"Failed to parse CSV file {data_path}: {e}") from e
    except Exception as e:
        raise IOError(f"Failed to read data from {data_path}: {e}") from e

    if "flood" not in data.columns:
        raise ValueError(f"Data file missing required 'flood' column: {data_path}")

    X = data.drop("flood", axis=1)
    y = data["flood"]

    # Predict
    y_pred = model.predict(X)

    # Accuracy
    accuracy = accuracy_score(y, y_pred)
    print(f"Accuracy: {accuracy}")  # OK: has curly braces

    # Confusion Matrix - with error handling for file operations
    try:
        cm = confusion_matrix(y, y_pred)
        plt.figure(figsize=(8, 6))
        sns.heatmap(cm, annot=True, fmt="d", cmap="Blues")
        plt.title("Confusion Matrix")
        plt.ylabel("Actual")
        plt.xlabel("Predicted")
        confusion_matrix_path = MODELS_DIR / "confusion_matrix.png"
        plt.savefig(confusion_matrix_path, dpi=300, bbox_inches="tight")
        plt.close()
    except PermissionError as e:
        print(f"Warning: Could not save confusion matrix (permission denied): {e}")
    except OSError as e:
        print(f"Warning: Could not save confusion matrix: {e}")
    except Exception as e:
        print(f"Warning: Error generating confusion matrix: {e}")
        plt.close()

    # Feature Importance - with error handling for file operations
    if hasattr(model, "feature_importances_"):
        try:
            plt.figure(figsize=(10, 6))
            feature_importances = pd.Series(model.feature_importances_, index=X.columns)
            feature_importances.nlargest(10).plot(kind="barh")
            plt.title("Top 10 Feature Importances")
            plt.xlabel("Importance")
            plt.tight_layout()
            feature_importance_path = MODELS_DIR / "feature_importance.png"
            plt.savefig(feature_importance_path, dpi=300, bbox_inches="tight")
            plt.close()
        except PermissionError as e:
            print(f"Warning: Could not save feature importance plot (permission denied): {e}")
        except OSError as e:
            print(f"Warning: Could not save feature importance plot: {e}")
        except Exception as e:
            print(f"Warning: Error generating feature importance plot: {e}")
            plt.close()

    print("Evaluation complete.")
    return accuracy


if __name__ == "__main__":
    evaluate_model()
