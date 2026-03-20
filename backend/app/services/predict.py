import datetime
import hashlib
import hmac
import json
import logging
import os
import pickle  # nosec B403 - used only for joblib model loading, not arbitrary deserialization
import tempfile
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib
import numpy as np
import pandas as pd
from app.services.risk_classifier import classify_risk_level
from app.services.smart_alert_evaluator import evaluate_smart_alert
from app.services.xai_engine import generate_explanation
from app.utils.secrets import get_secret

logger = logging.getLogger(__name__)

# Resolve model paths relative to the backend directory, not CWD
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_MODELS_DIR = str(_BACKEND_DIR / "models")
DEFAULT_MODEL_PATH = str(_BACKEND_DIR / "models" / "flood_rf_model.joblib")

# HMAC key for model signing - resolved lazily so that secrets
# loaded at startup time (after import) are picked up correctly.
_MODEL_SIGNING_KEY: str | None = None


def _get_model_signing_key() -> str:
    """Return the MODEL_SIGNING_KEY, reading from secrets on first call."""
    global _MODEL_SIGNING_KEY
    if _MODEL_SIGNING_KEY is None:
        _MODEL_SIGNING_KEY = get_secret("MODEL_SIGNING_KEY", default="")
    return _MODEL_SIGNING_KEY


class ModelLoader:
    """
    Singleton class for lazy-loading and managing ML models.

    This replaces global mutable state with a controlled singleton pattern
    that supports dependency injection for testing.

    Thread-safety: Uses a lock to prevent duplicate instantiation under
    concurrent Gunicorn workers / threads.
    """

    _instance: Optional["ModelLoader"] = None
    _lock: threading.Lock = threading.Lock()

    def __init__(self):
        """Initialize the model loader."""
        self._model: Optional[Any] = None
        self._model_path: str = DEFAULT_MODEL_PATH
        self._model_metadata: Optional[Dict[str, Any]] = None
        self._model_checksum: Optional[str] = None

    @classmethod
    def get_instance(cls) -> "ModelLoader":
        """Get or create the singleton ModelLoader instance (thread-safe)."""
        if cls._instance is None:
            with cls._lock:
                # Double-checked locking
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (useful for testing)."""
        with cls._lock:
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

    Uses a `.sha256` sidecar cache keyed on file mtime to avoid re-hashing
    unchanged model files.

    Args:
        model_path: Path to the model file

    Returns:
        str: Hex-encoded SHA-256 checksum
    """
    sidecar = Path(model_path).with_suffix(".sha256")
    try:
        current_mtime = os.path.getmtime(model_path)
        if sidecar.exists():
            cached = sidecar.read_text().strip().split(":", 1)
            if len(cached) == 2:
                cached_mtime, cached_hash = cached
                if float(cached_mtime) == current_mtime:
                    return cached_hash
    except (OSError, ValueError):
        pass  # Fall through to full computation

    sha256_hash = hashlib.sha256()
    with open(model_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    digest = sha256_hash.hexdigest()

    # Persist to sidecar for next load
    try:
        current_mtime = os.path.getmtime(model_path)
        sidecar.write_text(f"{current_mtime}:{digest}")
    except OSError:
        pass

    return digest


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
    signing_key = _get_model_signing_key()
    if signing_key and metadata:
        expected_hmac = metadata.get("hmac_signature")
        if expected_hmac:
            if not verify_model_hmac_signature(model_path, expected_hmac, signing_key):
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
    # Write to a temp file in the same directory, then atomically rename
    # to prevent readers from seeing a partially-written model file.
    model_dir = os.path.dirname(os.path.abspath(model_path))
    fd, tmp_path = tempfile.mkstemp(suffix=".joblib.tmp", dir=model_dir)
    try:
        os.close(fd)
        joblib.dump(model, tmp_path)

        # Compute checksum on the completed temp file
        checksum = compute_model_checksum(tmp_path)

        # Atomic rename (same filesystem, so this is atomic on POSIX;
        # on Windows os.replace is the closest equivalent).
        os.replace(tmp_path, model_path)
    except BaseException:
        # Clean up the temp file on any error
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise

    # Update metadata with checksum
    metadata["checksum"] = checksum
    metadata["checksum_algorithm"] = "SHA-256"

    # Compute and store HMAC signature if signing key is available
    signing_key = _get_model_signing_key()
    if signing_key:
        try:
            hmac_sig = compute_model_hmac_signature(model_path, signing_key)
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

    # Save metadata atomically (temp file + rename)
    metadata_path = Path(model_path).with_suffix(".json")
    fd_meta, tmp_meta_path = tempfile.mkstemp(suffix=".json.tmp", dir=model_dir)
    try:
        with os.fdopen(fd_meta, "w") as f:
            json.dump(metadata, f, indent=2)
        os.replace(tmp_meta_path, str(metadata_path))
    except BaseException:
        if os.path.exists(tmp_meta_path):
            os.unlink(tmp_meta_path)
        raise

    logger.info(f"Model saved with checksum: {checksum[:16]}...")
    return checksum


def list_available_models(models_dir: str = DEFAULT_MODELS_DIR) -> List[Dict[str, Any]]:
    """List all available model versions."""
    models_path = Path(models_dir)
    if not models_path.exists():
        return []

    models: List[Dict[str, Any]] = []
    for file in models_path.glob("flood_model_v*.joblib"):
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


def get_latest_model_version(models_dir: str = DEFAULT_MODELS_DIR) -> Optional[int]:
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


def _validate_loaded_model(model: Any, metadata: Optional[Dict], model_path: str) -> None:
    """
    Post-load smoke test for a model.

    Verifies:
    - Model has predict/predict_proba methods
    - Feature names in metadata match model (if available)
    - A dummy prediction completes in < 100ms
    """
    import time

    import numpy as np

    # Check model has prediction capabilities
    has_predict = hasattr(model, "predict")
    has_proba = hasattr(model, "predict_proba")
    if not has_predict and not has_proba:
        raise ValueError(f"Model at {model_path} has no predict or predict_proba method")

    # Check feature names if metadata provides them
    expected_features = None
    if metadata:
        expected_features = metadata.get("feature_names") or metadata.get("features")
    if expected_features and hasattr(model, "feature_names_in_"):
        model_features = list(model.feature_names_in_)
        if set(model_features) != set(expected_features):
            missing = set(expected_features) - set(model_features)
            extra = set(model_features) - set(expected_features)
            logger.warning(
                "Feature mismatch in model %s: missing=%s, extra=%s",
                model_path,
                missing or "none",
                extra or "none",
            )

    # Smoke-test prediction latency with dummy input
    try:
        n_features = len(expected_features) if expected_features else 13
        dummy = np.zeros((1, n_features))
        start = time.perf_counter()
        if has_proba:
            model.predict_proba(dummy)
        else:
            model.predict(dummy)
        elapsed_ms = (time.perf_counter() - start) * 1000

        if elapsed_ms > 100:
            logger.warning("Model smoke-test prediction took %.1fms (threshold: 100ms)", elapsed_ms)
        else:
            logger.debug("Model smoke-test passed in %.1fms", elapsed_ms)
    except Exception as exc:
        # Non-fatal: model may expect specific feature names in DataFrame
        logger.debug("Model smoke-test skipped (expected): %s", exc)


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

            # Post-load validation: verify model can produce predictions
            _validate_loaded_model(model, metadata, model_path)

            loader.set_model(model, model_path, metadata, checksum)

            logger.info("Model loaded successfully")
            if metadata:
                logger.info(f"Model version: {metadata.get('version', 'unknown')}")
            logger.debug("Model checksum verified")

        except (pickle.UnpicklingError, EOFError, ModuleNotFoundError) as e:
            logger.error(
                f"Model file is corrupt or incompatible: {str(e)}. "
                "Re-train the model or obtain a compatible .joblib file."
            )
            raise ValueError(f"Corrupt or incompatible model file '{model_path}': {e}") from e
        except (IOError, OSError) as e:
            logger.error(f"Error loading model: {str(e)}")
            raise

    return loader.model


def load_model_version(version: int, models_dir: str = DEFAULT_MODELS_DIR, force_reload: bool = False) -> Any:
    """Load a specific model version."""
    model_path = Path(models_dir) / f"flood_model_v{version}.joblib"
    if not model_path.exists():
        raise FileNotFoundError(f"Model version {version} not found at {model_path}")

    return _load_model(str(model_path), force_reload=force_reload)


def _compute_rolling_features() -> Dict[str, Any]:
    """
    Compute rolling weather features from stored WeatherData records.

    Queries the database for recent weather observations and computes:
    - precip_3day_sum: total precipitation over last 3 days
    - precip_7day_sum: total precipitation over last 7 days
    - rain_streak: consecutive days with precipitation > 0.1mm (most recent)

    Returns:
        Dict with computed rolling features and metadata about data availability.
        Keys: precip_3day_sum, precip_7day_sum, rain_streak, tide_height,
              _rolling_source ("database" or "unavailable"),
              _days_available (int).
    """
    result: Dict[str, Any] = {
        "_rolling_source": "unavailable",
        "_days_available": 0,
    }

    try:
        from app.models.db import get_db_session
        from app.models.weather import WeatherData
        from sqlalchemy import func

        now = datetime.datetime.now(datetime.timezone.utc)
        seven_days_ago = now - datetime.timedelta(days=7)

        with get_db_session() as session:
            # Get daily precipitation sums for last 7 days, grouped by date
            daily_records = (
                session.query(
                    func.date(WeatherData.timestamp).label("day"),
                    func.sum(WeatherData.precipitation).label("daily_precip"),
                    func.max(WeatherData.precipitation).label("max_precip"),
                )
                .filter(
                    WeatherData.is_deleted.is_(False),
                    WeatherData.timestamp >= seven_days_ago,
                )
                .group_by(func.date(WeatherData.timestamp))
                .order_by(func.date(WeatherData.timestamp).desc())
                .all()
            )

            if not daily_records:
                logger.warning("No weather records found in last 7 days for rolling features")
                return result

            result["_days_available"] = len(daily_records)
            result["_rolling_source"] = "database"

            # Compute precip_7day_sum from all available days
            precip_values = [float(r.daily_precip or 0.0) for r in daily_records]
            result["precip_7day_sum"] = sum(precip_values)

            # Compute precip_3day_sum from most recent 3 days
            result["precip_3day_sum"] = sum(precip_values[:3])

            # Compute rain_streak: consecutive days with max_precip > 0.1mm
            # starting from most recent day going backwards
            streak = 0
            for r in daily_records:
                if (r.max_precip or 0.0) > 0.1:
                    streak += 1
                else:
                    break
            result["rain_streak"] = streak

            # Get most recent tide_height if available
            latest_tide = (
                session.query(WeatherData.tide_height)
                .filter(
                    WeatherData.is_deleted.is_(False),
                    WeatherData.tide_height.isnot(None),
                    WeatherData.timestamp >= seven_days_ago,
                )
                .order_by(WeatherData.timestamp.desc())
                .first()
            )
            if latest_tide and latest_tide.tide_height is not None:
                result["tide_height"] = float(latest_tide.tide_height)

    except Exception as e:
        logger.warning("Could not compute rolling features from database: %s", e)

    return result


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

    # --- Ensemble model feature flag ---
    # When enabled, delegate to EnsemblePredictor for the classification step.
    # All post-processing (risk level, smart alerts, XAI) still runs below.
    _use_ensemble = os.getenv("FLOODINGNAQUE_FLAG_ENSEMBLE_MODEL", "false").lower() == "true"
    _ensemble_prediction: Dict[str, Any] | None = None
    if _use_ensemble and model_version is None:
        try:
            from app.ml.ensemble_model import EnsemblePredictor

            ep = EnsemblePredictor.get_instance()
            if ep.is_enabled():
                from app.services.data_aggregation_service import DataBundle

                # Build a minimal feature vector from input_data
                bundle = DataBundle(
                    temperature=input_data.get("temperature", 0.0),
                    humidity=input_data.get("humidity", 0.0),
                    precipitation=input_data.get("precipitation", 0.0),
                )
                _ensemble_prediction = ep.predict(bundle.to_feature_vector())
                if "error" not in _ensemble_prediction:
                    logger.info("Ensemble prediction used: %s", _ensemble_prediction)
        except Exception as exc:
            logger.warning("Ensemble prediction failed, falling back to default: %s", exc)

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
        # Track any features filled with defaults
        fill_values = {}

        # Compute derived features from raw weather inputs before filling defaults.
        # These interaction features match the preprocessing pipeline used during
        # training (preprocess_pagasa_data.py / preprocess_official_flood_records.py).
        temp = input_data.get("temperature")  # Kelvin
        humidity = input_data.get("humidity")
        precip = input_data.get("precipitation", 0.0)

        now = datetime.datetime.now()
        month = now.month
        # Philippine monsoon season: June–November
        is_monsoon = 1 if 6 <= month <= 11 else 0

        derived_features = {}
        if temp is not None and humidity is not None:
            derived_features["temp_humidity_interaction"] = temp * humidity / 100
        if temp is not None and precip is not None:
            derived_features["temp_precip_interaction"] = temp * np.log1p(precip)
        if humidity is not None and precip is not None:
            derived_features["humidity_precip_interaction"] = humidity * precip / 100
            derived_features["saturation_risk"] = int(humidity > 85 and precip > 20)
        derived_features["is_monsoon_season"] = is_monsoon
        derived_features["month"] = month
        if precip is not None:
            derived_features["monsoon_precip_interaction"] = is_monsoon * precip

        # Compute rolling features from weather history in database.
        # These features (precip_3day_sum, precip_7day_sum, rain_streak, tide_height)
        # are trained with real historical data — defaulting to 0.0 degrades accuracy.
        rolling = _compute_rolling_features()
        rolling_source = rolling.pop("_rolling_source", "unavailable")
        days_available = rolling.pop("_days_available", 0)

        # Only inject rolling values NOT already provided in input_data
        for key, val in rolling.items():
            if key not in input_data:
                derived_features[key] = val

        # Merge raw input + derived features into a single lookup dict
        all_features = {**input_data, **derived_features}

        # Build feature array directly as NumPy (skip DataFrame overhead for single predictions)
        if hasattr(model, "feature_names_in_"):
            expected_features = list(model.feature_names_in_)
            feature_values = []
            for feature in expected_features:
                val = all_features.get(feature)
                if val is None or (isinstance(val, float) and np.isnan(val)):
                    # Provide reasonable defaults based on feature name
                    if "wind" in feature.lower():
                        default = 10.0
                    elif "temperature" in feature.lower():
                        default = 298.15
                    elif "humidity" in feature.lower():
                        default = 50.0
                    elif "precipitation" in feature.lower() or "precip" in feature.lower():
                        default = 0.0
                    elif "tide" in feature.lower():
                        default = 0.0
                    elif feature in ("rain_streak",):
                        default = 0
                    else:
                        default = 0.0
                    fill_values[feature] = default
                    feature_values.append(default)
                else:
                    feature_values.append(val)

            # Use a named DataFrame so scikit-learn receives the feature names
            # it was trained with. Passing a plain NumPy array triggers:
            #   UserWarning: X does not have valid feature names, but
            #   RandomForestClassifier was fitted with feature names
            X = pd.DataFrame([feature_values], columns=expected_features)

            # Warn caller about imputed features
            if fill_values:
                logger.warning(
                    "predict_flood: %d feature(s) missing from input, filled with defaults: %s",
                    len(fill_values),
                    ", ".join(f"{k}={v}" for k, v in fill_values.items()),
                )
        else:
            # Fallback: model has no feature_names_in_, use DataFrame for safety
            # All v1-v6 models have feature_names_in_; this path is only for
            # manually-loaded or third-party models. DataFrame adds ~5-10ms overhead.
            logger.warning(
                "predict_flood: model lacks feature_names_in_, falling back to DataFrame. "
                "Retrain model with scikit-learn >= 1.0 to enable fast NumPy path."
            )
            df = pd.DataFrame([all_features])
            X = df

        # Make prediction
        prediction = model.predict(X)
        result = int(prediction[0])

        # Get probabilities if requested or if risk level classification is needed
        probability_dict = None
        if (return_proba or return_risk_level) and hasattr(model, "predict_proba"):
            proba = model.predict_proba(X)[0]
            probability_dict = {"no_flood": float(proba[0]), "flood": float(proba[1]) if len(proba) > 1 else 0.0}

        # Classify risk level if requested
        risk_classification = None
        if return_risk_level:
            risk_classification = classify_risk_level(
                prediction=result,
                probability=probability_dict,
                precipitation=input_data.get("precipitation"),
                humidity=input_data.get("humidity"),
                precipitation_3h=input_data.get("precipitation_3h"),
                tide_risk_factor=input_data.get("tide_risk_factor"),
            )

        # Run smart alert evaluation pipeline
        smart_decision = None
        if risk_classification:
            try:
                smart_decision = evaluate_smart_alert(
                    risk_classification=risk_classification,
                    weather_data=input_data,
                    data_quality=input_data.get("data_quality"),
                    location=input_data.get("location", "Parañaque City"),
                )
                # Override risk classification with smart decision
                risk_classification["risk_level"] = smart_decision.risk_level
                risk_classification["risk_label"] = smart_decision.risk_label
                risk_classification["confidence"] = smart_decision.confidence
                # Keep risk_color in sync with the overridden label
                from app.services.risk_classifier import RISK_LEVEL_COLORS

                risk_classification["risk_color"] = RISK_LEVEL_COLORS.get(
                    smart_decision.risk_label, risk_classification["risk_color"]
                )
            except Exception as smart_exc:
                logger.warning("Smart alert evaluation failed, using base classification: %s", smart_exc)

        # Build response
        if return_proba or return_risk_level:
            loader = _get_model_loader()
            response: Dict[str, Any] = {
                "prediction": result,
                "model_version": loader.metadata.get("version") if loader.metadata else None,
            }
            if probability_dict:
                response["probability"] = probability_dict
            if fill_values:
                response["imputed_defaults"] = fill_values

            # Feature completeness tracking — indicates data quality of this prediction
            if hasattr(model, "feature_names_in_"):
                total_features = len(model.feature_names_in_)
                defaulted_count = len(fill_values)
                features_with_real_data = total_features - defaulted_count
                confidence_impact = "high" if defaulted_count > 2 else "low" if defaulted_count > 0 else "none"
                response["feature_completeness"] = {
                    "features_available": features_with_real_data,
                    "features_total": total_features,
                    "features_defaulted": list(fill_values.keys()),
                    "confidence_impact": confidence_impact,
                    "rolling_data_source": rolling_source,
                    "rolling_days_available": days_available,
                }
                if defaulted_count > 2:
                    logger.warning(
                        "Prediction made with %d/%d features defaulted (%s) — confidence may be reduced",
                        defaulted_count,
                        total_features,
                        ", ".join(fill_values.keys()),
                    )

            if risk_classification:
                response["risk_level"] = risk_classification["risk_level"]
                response["risk_label"] = risk_classification["risk_label"]
                response["risk_color"] = risk_classification["risk_color"]
                response["risk_description"] = risk_classification["description"]
                response["confidence"] = risk_classification["confidence"]

            # Attach smart alert metadata
            if smart_decision:
                response["smart_alert"] = {
                    "rainfall_3h": smart_decision.rainfall_3h,
                    "confidence_score": smart_decision.confidence,
                    "was_suppressed": smart_decision.was_suppressed,
                    "escalation_state": smart_decision.escalation_state,
                    "escalation_reason": smart_decision.escalation_reason,
                    "contributing_factors": smart_decision.contributing_factors,
                    "original_risk_level": smart_decision.original_risk_level,
                }

            # ── Explainable AI (XAI) ──────────────────────────────────
            try:
                explanation = generate_explanation(
                    model=model,
                    input_data=input_data,
                    risk_label=risk_classification["risk_label"] if risk_classification else "Unknown",
                    confidence=risk_classification["confidence"] if risk_classification else 0.5,
                )
                response["explanation"] = explanation
            except Exception as xai_exc:
                logger.warning("XAI explanation generation failed: %s", xai_exc)
                response["explanation"] = None

            # Surface model feature names for frontend
            if hasattr(model, "feature_names_in_"):
                response["features_used"] = list(model.feature_names_in_)

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
