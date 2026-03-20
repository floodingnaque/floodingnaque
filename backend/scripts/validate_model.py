import json
import logging
import os
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Resolve paths relative to backend directory
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
MODELS_DIR = BACKEND_DIR / "models"
DATA_DIR = BACKEND_DIR / "data"


def load_model_metadata(model_path):
    """Load model metadata from JSON file."""
    metadata_path = model_path.with_suffix(".json")
    if metadata_path.exists():
        with open(metadata_path, "r") as f:
            return json.load(f)
    return None


def validate_model_integrity(model_path):
    """Validate that model file exists and can be loaded."""
    logger.info(f"Validating model integrity: {model_path}")

    if not model_path.exists():
        logger.error(f"Model file not found: {model_path}")
        return False, "Model file not found"

    try:
        model = joblib.load(model_path)
        logger.info("✓ Model loaded successfully")

        # Check model type
        if not hasattr(model, "predict"):
            logger.error("Model does not have predict method")
            return False, "Invalid model type"

        logger.info(f"✓ Model type: {type(model).__name__}")
        return True, model
    except Exception as e:
        logger.error(f"Error loading model: {str(e)}")
        return False, str(e)


def validate_model_features(model, expected_features=None):
    """Validate that model expects the correct features."""
    logger.info("Validating model features...")

    if hasattr(model, "feature_names_in_"):
        model_features = list(model.feature_names_in_)
        logger.info(f"Model expects features: {model_features}")

        # If expected_features provided, check compatibility
        if expected_features is not None:
            expected_set = set(expected_features)
            model_set = set(model_features)

            # Check if all expected features are present in model
            missing_in_model = expected_set - model_set
            if missing_in_model:
                logger.warning(f"Some expected features missing in model: {missing_in_model}")
                return False, f"Missing features: {missing_in_model}"

            # Check if model has extra features (this is OK, just warn)
            extra_in_model = model_set - expected_set
            if extra_in_model:
                logger.info(f"Model has additional features (OK): {extra_in_model}")

        logger.info(f"✓ Model features validated: {model_features}")
        return True, model_features
    else:
        logger.warning("Model does not store feature names - cannot validate")
        return True, None


def test_model_predictions(model, test_data):
    """Test model with sample predictions."""
    logger.info("Testing model predictions...")

    try:
        # Get model features to create proper test cases
        model_features = []
        if hasattr(model, "feature_names_in_"):
            model_features = list(model.feature_names_in_)

        # Create base test cases with common features
        base_test_cases = [
            {"temperature": 298.15, "humidity": 65.0, "precipitation": 0.0},  # Normal
            {"temperature": 298.15, "humidity": 90.0, "precipitation": 50.0},  # High flood risk
            {"temperature": 293.15, "humidity": 50.0, "precipitation": 5.0},  # Low flood risk
        ]

        # Add default values for any additional features the model expects
        test_cases = []
        for base_case in base_test_cases:
            test_case = base_case.copy()
            # Add default values for any missing features
            for feature in model_features:
                if feature not in test_case:
                    # Provide reasonable defaults for unknown features
                    if "wind" in feature.lower():
                        test_case[feature] = 10.0  # Default wind speed
                    else:
                        test_case[feature] = 0.0  # Default for other features
            test_cases.append(test_case)

        results = []
        for i, test_case in enumerate(test_cases):
            try:
                df = pd.DataFrame([test_case])

                # Reindex if model has feature names
                if hasattr(model, "feature_names_in_"):
                    df = df.reindex(columns=model.feature_names_in_, fill_value=0)

                prediction = model.predict(df)
                proba = model.predict_proba(df) if hasattr(model, "predict_proba") else None

                result = {
                    "test_case": i + 1,
                    "input": test_case,
                    "prediction": int(prediction[0]),
                    "probability": proba[0].tolist() if proba is not None else None,
                }
                results.append(result)
                logger.info(f"  Test {i+1}: {test_case} -> Prediction: {prediction[0]}")
            except Exception as e:
                logger.error(f"  Test {i+1} failed: {str(e)}")
                return False, str(e)

        logger.info("✓ All test predictions successful")
        return True, results
    except Exception as e:
        logger.error(f"Error testing predictions: {str(e)}")
        return False, str(e)


def evaluate_model_performance(model, data_file=None):
    """Evaluate model performance on test data."""
    if data_file is None:
        data_file = DATA_DIR / "processed" / "cumulative_v2_up_to_2025.csv"
    else:
        data_file = Path(data_file)

    logger.info(f"Evaluating model performance on {data_file}...")

    if not data_file.exists():
        logger.warning(f"Data file not found: {data_file}. Skipping performance evaluation.")
        return None

    try:
        data = pd.read_csv(data_file)

        # Check required columns
        required_cols = ["temperature", "humidity", "precipitation", "flood"]
        if not all(col in data.columns for col in required_cols):
            logger.warning("Data file missing required columns. Skipping performance evaluation.")
            return None

        X = data.drop("flood", axis=1)
        y = data["flood"]

        # Make predictions
        y_pred = model.predict(X)
        y_pred_proba = model.predict_proba(X) if hasattr(model, "predict_proba") else None

        # Calculate metrics
        metrics = {
            "accuracy": float(accuracy_score(y, y_pred)),
            "precision": float(precision_score(y, y_pred, average="weighted", zero_division=0)),
            "recall": float(recall_score(y, y_pred, average="weighted", zero_division=0)),
            "f1_score": float(f1_score(y, y_pred, average="weighted", zero_division=0)),
        }

        if y_pred_proba is not None and y_pred_proba.shape[1] > 1:
            try:
                metrics["roc_auc"] = float(roc_auc_score(y, y_pred_proba[:, 1]))
            except (ValueError, TypeError) as e:
                # ROC-AUC calculation failed (e.g., single class in y_true)
                logger.debug(f"Could not calculate ROC-AUC: {e}")

        logger.info("Performance Metrics:")
        logger.info(f"  Accuracy:  {metrics['accuracy']:.4f}")
        logger.info(f"  Precision: {metrics['precision']:.4f}")
        logger.info(f"  Recall:    {metrics['recall']:.4f}")
        logger.info(f"  F1 Score:  {metrics['f1_score']:.4f}")
        if "roc_auc" in metrics:
            logger.info(f"  ROC-AUC:   {metrics['roc_auc']:.4f}")

        return metrics
    except Exception as e:
        logger.error(f"Error evaluating performance: {str(e)}")
        return None


def validate_model(model_path=None, models_dir=None, data_file=None):
    """
    Comprehensive model validation.

    Args:
        model_path: Path to specific model file (defaults to latest)
        models_dir: Directory containing models
        data_file: Path to test data for performance evaluation

    Returns:
        dict: Validation results
    """
    # Use default paths relative to backend directory
    if models_dir is None:
        models_dir = MODELS_DIR
    else:
        models_dir = Path(models_dir)

    if data_file is None:
        data_file = DATA_DIR / "processed" / "cumulative_v2_up_to_2025.csv"
    else:
        data_file = Path(data_file)

    logger.info("=" * 60)
    logger.info("MODEL VALIDATION")
    logger.info("=" * 60)

    # Determine model path
    if model_path is None:
        model_path = Path(models_dir) / "flood_rf_model.joblib"
    else:
        model_path = Path(model_path)

    results = {"model_path": str(model_path), "valid": False, "checks": {}}

    # 1. Model Integrity Check
    logger.info("\n[1/4] Model Integrity Check")
    integrity_valid, integrity_result = validate_model_integrity(model_path)
    results["checks"]["integrity"] = {
        "valid": integrity_valid,
        "message": integrity_result if not integrity_valid else "Model loaded successfully",
    }

    if not integrity_valid:
        logger.error("✗ Model validation failed at integrity check")
        return results

    model = integrity_result

    # 2. Metadata Check
    logger.info("\n[2/4] Metadata Check")
    metadata = load_model_metadata(model_path)
    if metadata:
        logger.info("✓ Metadata file found")
        logger.info(f"  Version: {metadata.get('version', 'unknown')}")
        logger.info(f"  Created: {metadata.get('created_at', 'unknown')}")
        logger.info(f"  Accuracy: {metadata.get('metrics', {}).get('accuracy', 'unknown')}")
        results["checks"]["metadata"] = {"valid": True, "metadata": metadata}
    else:
        logger.warning("⚠ No metadata file found")
        results["checks"]["metadata"] = {"valid": False, "message": "Metadata file not found"}

    # 3. Feature Validation
    logger.info("\n[3/4] Feature Validation")
    # Get expected features from model metadata if available, otherwise use defaults
    expected_features = None
    if metadata and "training_data" in metadata:
        expected_features = metadata["training_data"].get("features")

    # If not in metadata, try to get from model itself
    if expected_features is None and hasattr(model, "feature_names_in_"):
        expected_features = list(model.feature_names_in_)

    # Fallback to common features
    if expected_features is None:
        expected_features = ["temperature", "humidity", "precipitation"]

    features_valid, feature_result = validate_model_features(model, expected_features)
    results["checks"]["features"] = {
        "valid": features_valid,
        "features": feature_result if features_valid else feature_result,
    }

    # 4. Prediction Test
    logger.info("\n[4/4] Prediction Test")
    predictions_valid, prediction_results = test_model_predictions(model, None)
    results["checks"]["predictions"] = {
        "valid": predictions_valid,
        "test_results": prediction_results if predictions_valid else prediction_results,
    }

    # 5. Performance Evaluation (optional)
    logger.info("\n[5/5] Performance Evaluation")
    performance_metrics = evaluate_model_performance(model, data_file)
    if performance_metrics:
        results["checks"]["performance"] = {"valid": True, "metrics": performance_metrics}
    else:
        results["checks"]["performance"] = {"valid": False, "message": "Performance evaluation skipped"}

    # Overall validation result
    # Features check is not critical if predictions work (model can handle missing features)
    critical_checks = ["integrity", "predictions"]
    all_critical_valid = all(results["checks"].get(check, {}).get("valid", False) for check in critical_checks)

    # Feature validation is a warning, not a blocker
    if not results["checks"].get("features", {}).get("valid", True):
        logger.warning("Feature validation warning (non-critical): Model may have different features than expected")

    results["valid"] = all_critical_valid

    logger.info("\n" + "=" * 60)
    if results["valid"]:
        logger.info("✓ MODEL VALIDATION PASSED")
    else:
        logger.error("✗ MODEL VALIDATION FAILED")
    logger.info("=" * 60)

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Validate flood prediction model")
    parser.add_argument("--model", type=str, help="Path to specific model file (defaults to latest)")
    parser.add_argument("--models-dir", type=str, default="models", help="Directory containing models")
    parser.add_argument(
        "--data", type=str, default="data/processed/cumulative_v2_up_to_2025.csv", help="Path to test data"
    )
    parser.add_argument("--json", action="store_true", help="Output results as JSON")

    args = parser.parse_args()

    results = validate_model(model_path=args.model, models_dir=args.models_dir, data_file=args.data)

    if args.json:
        print(json.dumps(results, indent=2))

    sys.exit(0 if results["valid"] else 1)
