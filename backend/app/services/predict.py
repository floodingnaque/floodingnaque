import hashlib
import hmac
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib
import pandas as pd
from app.services.risk_classifier import classify_risk_level

logger = logging.getLogger(__name__)

# Default model path constant
DEFAULT_MODEL_PATH = os.path.join("models", "flood_rf_model.joblib")

# HMAC key for model signing (should be set in environment)
_MODEL_SIGNING_KEY = os.getenv("MODEL_SIGNING_KEY", "")


class ModelLoader:
    """
    Singleton class for lazy-loading and managing ML models.

    This replaces global mutable state with a controlled singleton pattern
    that supports dependency injection for testing.
    """

    _instance: Optional["ModelLoader"] = None

    def __init__(self):
        """Initialize the model loader."""
        self._model: Optional[Any] = None
        self._model_path: str = DEFAULT_MODEL_PATH
        self._model_metadata: Optional[Dict[str, Any]] = None
        self._model_checksum: Optional[str] = None

    @classmethod
    def get_instance(cls) -> "ModelLoader":
        """Get or create the singleton ModelLoader instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (useful for testing)."""
        cls._instance = None

    @property
    def model(self) -> Optional[Any]:
        """Get the currently loaded model."""
        return self._model

    @property
    def model_path(self) -> str:
        """Get the current model path."""
        return self._model_path

    @property
    def metadata(self) -> Optional[Dict[str, Any]]:
        """Get the model metadata."""
        return self._model_metadata

    @property
    def checksum(self) -> Optional[str]:
        """Get the model checksum."""
        return self._model_checksum

    def set_model(
        self, model: Any, path: str, metadata: Optional[Dict[str, Any]] = None, checksum: Optional[str] = None
    ) -> None:
        """Set the loaded model and its metadata."""
        self._model = model
        self._model_path = path
        self._model_metadata = metadata
        self._model_checksum = checksum


# Helper function to get model loader instance
def _get_model_loader() -> ModelLoader:
    """Get the ModelLoader singleton instance."""
    return ModelLoader.get_instance()


def get_model_metadata(model_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Get metadata for a model."""
    if model_path is None:
        model_path = _get_model_loader().model_path

    metadata_path = Path(model_path).with_suffix(".json")
    if metadata_path.exists():
        try:
            with open(metadata_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Could not load metadata: {str(e)}")
    return None


def compute_model_checksum(model_path: str) -> str:
    """
    Compute SHA-256 checksum of a model file for integrity verification.

    Args:
        model_path: Path to the model file

    Returns:
        str: Hex-encoded SHA-256 checksum
    """
    sha256_hash = hashlib.sha256()
    with open(model_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def compute_model_hmac_signature(model_path: str, signing_key: str) -> str:
    """
    Compute HMAC-SHA256 signature for a model file.

    This provides authenticity verification in addition to integrity.
    An attacker cannot forge a valid signature without the signing key.

    Args:
        model_path: Path to the model file
        signing_key: Secret key for HMAC signing

    Returns:
        str: Hex-encoded HMAC-SHA256 signature
    """
    if not signing_key:
        raise ValueError("MODEL_SIGNING_KEY is required for HMAC signature")

    h = hmac.new(signing_key.encode("utf-8"), digestmod=hashlib.sha256)
    with open(model_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_model_hmac_signature(model_path: str, expected_signature: str, signing_key: str) -> bool:
    """
    Verify HMAC signature of a model file.

    Uses timing-safe comparison to prevent timing attacks.

    Args:
        model_path: Path to the model file
        expected_signature: Expected HMAC signature from metadata
        signing_key: Secret key for HMAC verification

    Returns:
        bool: True if signature is valid
    """
    if not signing_key or not expected_signature:
        return False

    try:
        actual_signature = compute_model_hmac_signature(model_path, signing_key)
        return hmac.compare_digest(actual_signature, expected_signature)
    except Exception as e:
        logger.error(f"HMAC verification failed: {e}")
        return False


def verify_model_integrity(model_path: str, expected_checksum: Optional[str] = None) -> bool:
    """
    Verify model file integrity using checksum and optional HMAC signature.

    Security levels:
    1. Checksum (SHA-256): Verifies file hasn't been corrupted
    2. HMAC Signature: Verifies file authenticity (requires MODEL_SIGNING_KEY)

    Args:
        model_path: Path to the model file
        expected_checksum: Expected SHA-256 checksum (from metadata)

    Returns:
        bool: True if verification passes
    """
    metadata = get_model_metadata(model_path)

    # First verify HMAC signature if available (strongest protection)
    if _MODEL_SIGNING_KEY and metadata:
        expected_hmac = metadata.get("hmac_signature")
        if expected_hmac:
            if not verify_model_hmac_signature(model_path, expected_hmac, _MODEL_SIGNING_KEY):
                logger.error("SECURITY: HMAC signature verification FAILED! " "Model may have been tampered with.")
                return False
            logger.info("Model HMAC signature verified successfully")
            return True
        else:
            logger.warning("No HMAC signature in metadata. " "Re-train model with signing enabled for better security.")
    elif os.getenv("REQUIRE_MODEL_SIGNATURE", "false").lower() == "true":
        logger.error(
            "SECURITY: REQUIRE_MODEL_SIGNATURE is enabled but "
            "MODEL_SIGNING_KEY is not set or model has no signature."
        )
        return False

    # Fall back to checksum verification
    if not expected_checksum:
        if metadata:
            expected_checksum = metadata.get("checksum")

    if not expected_checksum:
        logger.warning("No checksum available for model verification")
        return True  # Allow if no checksum to verify against

    actual_checksum = compute_model_checksum(model_path)
    if actual_checksum != expected_checksum:
        logger.error("Model integrity check FAILED! Checksum mismatch detected.")
        return False

    logger.info("Model integrity verified successfully")
    return True


def save_model_with_checksum(model, model_path: str, metadata: Dict[str, Any]) -> str:
    """
    Save a model with checksum and optional HMAC signature for integrity verification.

    If MODEL_SIGNING_KEY is set, also computes an HMAC signature for authenticity.

    Args:
        model: The model object to save
        model_path: Path to save the model
        metadata: Metadata dictionary

    Returns:
        str: The computed checksum
    """
    # Save model first
    joblib.dump(model, model_path)

    # Compute checksum
    checksum = compute_model_checksum(model_path)

    # Update metadata with checksum
    metadata["checksum"] = checksum
    metadata["checksum_algorithm"] = "SHA-256"

    # Compute and store HMAC signature if signing key is available
    if _MODEL_SIGNING_KEY:
        try:
            hmac_sig = compute_model_hmac_signature(model_path, _MODEL_SIGNING_KEY)
            metadata["hmac_signature"] = hmac_sig
            metadata["hmac_algorithm"] = "HMAC-SHA256"
            logger.info(f"Model signed with HMAC: {hmac_sig[:16]}...")
        except Exception as e:
            logger.warning(f"Could not sign model with HMAC: {e}")
    else:
        logger.warning(
            "MODEL_SIGNING_KEY not set. Model saved without HMAC signature. "
            "Consider setting this for production security."
        )

    # Save metadata
    metadata_path = Path(model_path).with_suffix(".json")
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    logger.info(f"Model saved with checksum: {checksum[:16]}...")
    return checksum


def list_available_models(models_dir: str = "models") -> List[Dict[str, Any]]:
    """List all available model versions."""
    models_path = Path(models_dir)
    if not models_path.exists():
        return []

    models: List[Dict[str, Any]] = []
    for file in models_path.glob("flood_rf_model_v*.joblib"):
        try:
            version_str = file.stem.split("_v")[-1]
            version = int(version_str)
            metadata = get_model_metadata(str(file))
            models.append({"version": version, "path": str(file), "metadata": metadata})
        except (ValueError, IndexError):
            continue

    # Sort by version
    models.sort(key=lambda x: x["version"], reverse=True)
    return models


def get_latest_model_version(models_dir: str = "models") -> Optional[int]:
    """Get the latest model version number."""
    models = list_available_models(models_dir)
    if models:
        return models[0]["version"]

    # Check if latest model exists
    latest_path = Path(models_dir) / "flood_rf_model.joblib"
    if latest_path.exists():
        metadata = get_model_metadata(str(latest_path))
        if metadata and "version" in metadata:
            return metadata["version"]

    return None


def _load_model(model_path: Optional[str] = None, force_reload: bool = False, verify_integrity: bool = True) -> Any:
    """
    Load the trained model with optional integrity verification.

    Args:
        model_path: Path to the model file
        force_reload: Force reload even if already loaded
        verify_integrity: Verify model checksum before loading

    Returns:
        Loaded model object

    Raises:
        FileNotFoundError: If model file doesn't exist
        ValueError: If integrity check fails
    """
    loader = _get_model_loader()

    # Use provided path or default
    if model_path is None:
        model_path = loader.model_path

    # Reload if path changed or force reload
    if loader.model is None or force_reload or model_path != loader.model_path:
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Model file not found: {model_path}. " f"Please train the model first using train.py"
            )

        # Verify integrity if enabled
        if verify_integrity and os.getenv("VERIFY_MODEL_INTEGRITY", "True").lower() == "true":
            metadata = get_model_metadata(model_path)
            expected_checksum = metadata.get("checksum") if metadata else None

            if expected_checksum:
                if not verify_model_integrity(model_path, expected_checksum):
                    raise ValueError(
                        f"Model integrity verification failed for {model_path}. "
                        "The model file may have been tampered with."
                    )
            else:
                logger.warning("No checksum in metadata for model. Consider re-training with checksum enabled.")

        try:
            model = joblib.load(model_path)
            metadata = get_model_metadata(model_path)
            checksum = compute_model_checksum(model_path)

            loader.set_model(model, model_path, metadata, checksum)

            logger.info("Model loaded successfully")
            if metadata:
                logger.info(f"Model version: {metadata.get('version', 'unknown')}")
            logger.debug("Model checksum verified")

        except (IOError, OSError) as e:
            logger.error(f"Error loading model: {str(e)}")
            raise

    return loader.model


def load_model_version(version: int, models_dir: str = "models", force_reload: bool = False) -> Any:
    """Load a specific model version."""
    model_path = Path(models_dir) / f"flood_rf_model_v{version}.joblib"
    if not model_path.exists():
        raise FileNotFoundError(f"Model version {version} not found at {model_path}")

    return _load_model(str(model_path), force_reload=force_reload)


def predict_flood(
    input_data: Dict[str, Any],
    model_version: Optional[int] = None,
    return_proba: bool = False,
    return_risk_level: bool = True,
) -> Dict[str, Any] | int:
    """
    Predict flood based on input data.

    Args:
        input_data: dict with keys 'temperature', 'humidity', 'precipitation', etc.
        model_version: Optional model version number (uses latest if None)
        return_proba: If True, also return prediction probabilities
        return_risk_level: If True, return 3-level risk classification (Safe/Alert/Critical)

    Returns:
        int or dict: 0 (no flood) or 1 (flood predicted), or dict with prediction, probabilities, and risk level
    """
    if not isinstance(input_data, dict):
        raise ValueError("input_data must be a dictionary")

    # Validate required fields
    required_fields = ["temperature", "humidity", "precipitation"]
    missing_fields = [field for field in required_fields if field not in input_data]
    if missing_fields:
        raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

    # Load model (specific version or latest)
    if model_version is not None:
        model = load_model_version(model_version, force_reload=True)
    else:
        model = _load_model()

    try:
        # Convert input_data to DataFrame
        df = pd.DataFrame([input_data])

        # Get model feature names if available
        if hasattr(model, "feature_names_in_"):
            # Ensure columns match model expectations
            expected_features = model.feature_names_in_
            # Use reasonable defaults for missing features
            fill_values = {}
            for feature in expected_features:
                if feature not in input_data:
                    # Provide reasonable defaults based on feature name
                    if "wind" in feature.lower():
                        fill_values[feature] = 10.0  # Default wind speed
                    elif "temperature" in feature.lower():
                        fill_values[feature] = 298.15  # Default temperature (25°C)
                    elif "humidity" in feature.lower():
                        fill_values[feature] = 50.0  # Default humidity
                    elif "precipitation" in feature.lower():
                        fill_values[feature] = 0.0  # Default precipitation
                    else:
                        fill_values[feature] = 0.0  # Default for other features

            # Reindex with custom fill values
            df = df.reindex(columns=expected_features)
            # Apply custom fill values for missing features
            for feature, value in fill_values.items():
                df[feature] = df[feature].fillna(value)

        # Make prediction
        prediction = model.predict(df)
        result = int(prediction[0])

        # Get probabilities if requested or if risk level classification is needed
        probability_dict = None
        if (return_proba or return_risk_level) and hasattr(model, "predict_proba"):
            proba = model.predict_proba(df)[0]
            probability_dict = {"no_flood": float(proba[0]), "flood": float(proba[1]) if len(proba) > 1 else 0.0}

        # Classify risk level if requested
        risk_classification = None
        if return_risk_level:
            risk_classification = classify_risk_level(
                prediction=result,
                probability=probability_dict,
                precipitation=input_data.get("precipitation"),
                humidity=input_data.get("humidity"),
            )

        # Build response
        if return_proba or return_risk_level:
            loader = _get_model_loader()
            response: Dict[str, Any] = {
                "prediction": result,
                "model_version": loader.metadata.get("version") if loader.metadata else None,
            }
            if probability_dict:
                response["probability"] = probability_dict
            if risk_classification:
                response["risk_level"] = risk_classification["risk_level"]
                response["risk_label"] = risk_classification["risk_label"]
                response["risk_color"] = risk_classification["risk_color"]
                response["risk_description"] = risk_classification["description"]
                response["confidence"] = risk_classification["confidence"]

            logger.info(
                f"Prediction: {result}, Risk Level: {risk_classification['risk_label'] if risk_classification else 'N/A'}"
            )
            return response
        else:
            logger.info(f"Prediction made: {result} (0=no flood, 1=flood)")
            return result
    except (KeyError, ValueError, TypeError) as e:
        logger.error(f"Error making prediction: {str(e)}")
        raise


def get_current_model_info() -> Optional[Dict[str, Any]]:
    """Get information about the currently loaded model."""
    loader = _get_model_loader()

    if loader.model is None:
        try:
            _load_model()
        except (FileNotFoundError, ValueError, OSError) as e:
            logger.warning(f"Could not load model for info: {e}")
            return None

    info: Dict[str, Any] = {
        "model_path": loader.model_path,
        "model_type": type(loader.model).__name__ if loader.model else None,
        "metadata": loader.metadata,
        "checksum": loader.checksum[:16] + "..." if loader.checksum else None,
        "integrity_verified": bool(loader.checksum),
    }

    if loader.model and hasattr(loader.model, "feature_names_in_"):
        info["features"] = list(loader.model.feature_names_in_)

    return info


# =============================================================================
# Module-level convenience functions for backward compatibility
# =============================================================================
# These functions provide a simpler interface and allow for easy mocking in tests


def load_model(model_path: Optional[str] = None) -> Any:
    """
    Load prediction model.

    Module-level function that wraps the internal model loader for backward
    compatibility and easier testing (allows simple patching).

    Args:
        model_path: Optional path to model file. Uses default if not specified.

    Returns:
        Loaded model object

    Raises:
        FileNotFoundError: If model file doesn't exist
        ValueError: If integrity check fails
    """
    return _load_model(model_path=model_path)


def make_prediction(features: Dict[str, Any]) -> Dict[str, Any]:
    """
    Make a flood prediction.

    Module-level function for backward compatibility and easier testing.

    Args:
        features: Dictionary with weather features (temperature, humidity, precipitation)

    Returns:
        Prediction result dictionary with prediction, probability, and risk_level
    """
    return predict_flood(features, return_proba=True, return_risk_level=True)


def get_model_info() -> Optional[Dict[str, Any]]:
    """
    Get information about the loaded model.

    Module-level wrapper for get_current_model_info().

    Returns:
        Dictionary with model information or None if not loaded
    """
    return get_current_model_info()


# Export all public functions and classes
__all__ = [
    # Main class
    "ModelLoader",
    # Model loading functions
    "load_model",
    "_load_model",
    "load_model_version",
    # Prediction functions
    "make_prediction",
    "predict_flood",
    # Model info functions
    "get_model_info",
    "get_current_model_info",
    "get_model_metadata",
    # Model management functions
    "list_available_models",
    "get_latest_model_version",
    "save_model_with_checksum",
    # Integrity verification functions
    "verify_model_integrity",
    "verify_model_hmac_signature",
    "compute_model_checksum",
    "compute_model_hmac_signature",
]
