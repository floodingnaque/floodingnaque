"""
Configuration Management API Routes.

Provides REST API endpoints for:
- Configuration reload (without restart)
- Configuration status and validation
- Environment information
- Schema export
"""

import logging
import os
from functools import wraps

from flask import Blueprint, g, jsonify, request

logger = logging.getLogger(__name__)

config_bp = Blueprint("config", __name__)


def require_admin_access(f):
    """Decorator to require admin access for configuration management."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check for admin API key or internal token
        api_key = request.headers.get("X-API-Key")
        internal_token = request.headers.get("X-Internal-Token")
        expected_internal = os.getenv("INTERNAL_API_TOKEN")

        # Admin API keys (comma-separated list)
        admin_keys = os.getenv("ADMIN_API_KEYS", "").split(",")
        admin_keys = [k.strip() for k in admin_keys if k.strip()]

        is_admin = False

        if api_key and api_key in admin_keys:
            is_admin = True
        elif internal_token and expected_internal and internal_token == expected_internal:
            is_admin = True
        elif getattr(g, "user_role", None) == "admin":
            is_admin = True

        if not is_admin:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": {
                            "code": "ADMIN_REQUIRED",
                            "message": "Admin access required for configuration management",
                        },
                    }
                ),
                403,
            )

        return f(*args, **kwargs)

    return decorated_function


@config_bp.route("/status", methods=["GET"])
def get_config_status():
    """
    Get current configuration status.

    Returns:
        200: Configuration status including environment, validation state, etc.
    ---
    tags:
      - Configuration
    responses:
      200:
        description: Configuration status
    """
    try:
        # Import from backend config module (not app.core.config)
        import sys
        from pathlib import Path

        # Add backend to path if needed
        backend_path = Path(__file__).parent.parent.parent.parent.parent
        if str(backend_path) not in sys.path:
            sys.path.insert(0, str(backend_path))

        from config import get_config, get_environment

        config = get_config()

        return jsonify(
            {
                "success": True,
                "data": {
                    "environment": get_environment(),
                    "is_validated": config.is_validated,
                    "config_sections": list(config._config.keys()),
                    "reload_supported": True,
                    "sighup_supported": os.name != "nt",  # Unix only
                },
            }
        )
    except ImportError as e:
        logger.warning(f"Config module not available: {e}")
        return jsonify(
            {
                "success": True,
                "data": {
                    "environment": os.environ.get("FLOODINGNAQUE_ENV", "development"),
                    "is_validated": False,
                    "config_sections": [],
                    "reload_supported": False,
                    "note": "Training config module not available",
                },
            }
        )
    except Exception as e:
        logger.error(f"Failed to get config status: {e}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": {"code": "CONFIG_ERROR", "message": "Failed to retrieve configuration status"},
                }
            ),
            500,
        )


@config_bp.route("/reload", methods=["POST"])
@require_admin_access
def reload_configuration():
    """
    Reload configuration from disk.

    This endpoint triggers a hot-reload of all configuration files
    without requiring a server restart.

    Reloads:
    - Training configuration (training_config.yaml + environment overrides)
    - Feature flags (feature_flags.yaml)
    - Secrets (secrets.yaml)

    Returns:
        200: Configuration reloaded successfully
        500: Reload failed
    ---
    tags:
      - Configuration
    security:
      - ApiKeyAuth: []
    responses:
      200:
        description: Configuration reloaded
      403:
        description: Admin access required
      500:
        description: Reload failed
    """
    try:
        import sys
        from pathlib import Path

        # Add backend to path if needed
        backend_path = Path(__file__).parent.parent.parent.parent.parent
        if str(backend_path) not in sys.path:
            sys.path.insert(0, str(backend_path))

        results = {
            "training_config": False,
            "feature_flags": False,
            "secrets": False,
        }
        errors = []

        # Reload training configuration
        try:
            from config import get_config  # noqa: E402

            config = get_config()
            config.reload()
            results["training_config"] = True
            logger.info("Training configuration reloaded via API")
        except Exception as e:
            errors.append("Training config: reload failed")
            logger.error(f"Failed to reload training config: {e}")

        # Reload feature flags
        try:
            from config.feature_flags import get_flags_manager  # noqa: E402

            flags = get_flags_manager()
            flags.reload()
            results["feature_flags"] = True
            logger.info("Feature flags reloaded via API")
        except ImportError:
            logger.debug("Feature flags module not available")
        except Exception as e:
            errors.append("Feature flags: reload failed")
            logger.error(f"Failed to reload feature flags: {e}")

        # Reload secrets
        try:
            from config.secrets import get_secrets_manager

            secrets = get_secrets_manager()
            secrets.reload()
            results["secrets"] = True
            logger.info("Secrets reloaded via API")
        except ImportError:
            logger.debug("Secrets module not available")
        except Exception as e:
            errors.append("Secrets: reload failed")
            logger.error(f"Failed to reload secrets: {e}")

        success = all(results.values()) or (results["training_config"] and not errors)

        return jsonify(
            {
                "success": success,
                "data": {
                    "reloaded": results,
                    "errors": errors if errors else None,
                    "message": "Configuration reloaded successfully" if success else "Partial reload with errors",
                },
            }
        ), (
            200 if success else 207
        )  # 207 Multi-Status for partial success

    except Exception as e:
        logger.error(f"Configuration reload failed: {e}", exc_info=True)
        return (
            jsonify(
                {
                    "success": False,
                    "error": {
                        "code": "RELOAD_FAILED",
                        "message": "Configuration reload failed. Check server logs for details.",
                    },
                }
            ),
            500,
        )


@config_bp.route("/validate", methods=["POST"])
@require_admin_access
def validate_configuration():
    """
    Validate configuration files without reloading.

    Useful for testing configuration changes before applying them.

    Returns:
        200: Validation results
    ---
    tags:
      - Configuration
    security:
      - ApiKeyAuth: []
    responses:
      200:
        description: Validation results
      403:
        description: Admin access required
    """
    try:
        from pathlib import Path

        import yaml

        config_dir = Path(__file__).parent.parent.parent.parent / "config"
        results = {}
        errors = []

        # Validate training_config.yaml
        training_config_path = config_dir / "training_config.yaml"
        if training_config_path.exists():
            try:
                with open(training_config_path) as f:
                    config_dict = yaml.safe_load(f)

                # Try schema validation
                try:
                    from config.schema import validate_config

                    validated = validate_config(config_dict)
                    results["training_config"] = {
                        "valid": True,
                        "sections": list(config_dict.keys()),
                        "schema_validated": True,
                    }
                except ImportError:
                    results["training_config"] = {
                        "valid": True,
                        "sections": list(config_dict.keys()),
                        "schema_validated": False,
                        "note": "Schema validation unavailable (pydantic not installed)",
                    }
                except Exception as e:
                    results["training_config"] = {"valid": False, "error": "Schema validation failed"}
                    errors.append("Training config schema: validation failed")
                    logger.error(f"Training config schema validation error: {e}")

            except yaml.YAMLError as e:
                results["training_config"] = {"valid": False, "error": "YAML parse error"}
                errors.append("Training config YAML: parse error")
                logger.error(f"Training config YAML parse error: {e}")
        else:
            results["training_config"] = {"valid": False, "error": "File not found"}

        # Validate feature_flags.yaml
        flags_path = config_dir / "feature_flags.yaml"
        if flags_path.exists():
            try:
                with open(flags_path) as f:
                    flags_dict = yaml.safe_load(f)
                results["feature_flags"] = {"valid": True, "flags_count": len(flags_dict.get("flags", {}))}
            except yaml.YAMLError as e:
                results["feature_flags"] = {"valid": False, "error": "YAML parse error"}
                errors.append("Feature flags YAML: parse error")
                logger.error(f"Feature flags YAML parse error: {e}")
        else:
            results["feature_flags"] = {"valid": True, "note": "File not found (using defaults)"}

        # Validate secrets.yaml (check syntax only, don't expose values)
        secrets_path = config_dir / "secrets.yaml"
        if secrets_path.exists():
            try:
                with open(secrets_path) as f:
                    secrets_dict = yaml.safe_load(f)
                results["secrets"] = {
                    "valid": True,
                    "secrets_count": len(secrets_dict.get("secrets", {})),
                    "has_metadata": "metadata" in secrets_dict,
                }
            except yaml.YAMLError as e:
                results["secrets"] = {"valid": False, "error": "YAML parse error"}
                errors.append("Secrets YAML: parse error")
                logger.error(f"Secrets YAML parse error: {e}")
        else:
            results["secrets"] = {"valid": True, "note": "File not found (using environment variables)"}

        return jsonify(
            {
                "success": len(errors) == 0,
                "data": {
                    "validation_results": results,
                    "errors": errors if errors else None,
                    "all_valid": len(errors) == 0,
                },
            }
        )

    except Exception as e:
        logger.error(f"Configuration validation failed: {e}", exc_info=True)
        return (
            jsonify(
                {
                    "success": False,
                    "error": {
                        "code": "VALIDATION_FAILED",
                        "message": "Configuration validation failed. Check server logs for details.",
                    },
                }
            ),
            500,
        )


@config_bp.route("/schema", methods=["GET"])
def get_config_schema():
    """
    Get JSON Schema for configuration validation.

    Useful for IDE autocomplete and external validation tools.

    Returns:
        200: JSON Schema
    ---
    tags:
      - Configuration
    responses:
      200:
        description: JSON Schema for configuration
    """
    try:
        from config.schema import ConfigSchema

        schema = ConfigSchema.model_json_schema()
        return jsonify(
            {"success": True, "data": {"schema": schema, "$schema": "http://json-schema.org/draft-07/schema#"}}
        )
    except ImportError:
        return (
            jsonify(
                {
                    "success": False,
                    "error": {
                        "code": "SCHEMA_UNAVAILABLE",
                        "message": "Schema validation not available (pydantic not installed)",
                    },
                }
            ),
            501,
        )
    except Exception as e:
        logger.error(f"Failed to get config schema: {e}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": {"code": "SCHEMA_ERROR", "message": "Failed to retrieve configuration schema"},
                }
            ),
            500,
        )


@config_bp.route("/environment", methods=["GET"])
def get_environment_info():
    """
    Get environment configuration information.

    Returns information about supported environment variables
    and current environment settings (values are not exposed).

    Returns:
        200: Environment information
    ---
    tags:
      - Configuration
    responses:
      200:
        description: Environment information
    """
    # Document all supported environment variables
    env_vars = {
        "FLOODINGNAQUE_ENV": {
            "description": "Environment name (development/staging/production)",
            "default": "development",
            "is_set": "FLOODINGNAQUE_ENV" in os.environ,
        },
        "FLOODINGNAQUE_MLFLOW_URI": {
            "description": "MLflow tracking server URI",
            "default": "mlruns",
            "is_set": "FLOODINGNAQUE_MLFLOW_URI" in os.environ,
        },
        "FLOODINGNAQUE_ENABLE_MLFLOW": {
            "description": "Enable/disable MLflow tracking",
            "default": "true",
            "is_set": "FLOODINGNAQUE_ENABLE_MLFLOW" in os.environ,
        },
        "FLOODINGNAQUE_MODELS_DIR": {
            "description": "Models directory path",
            "default": "models",
            "is_set": "FLOODINGNAQUE_MODELS_DIR" in os.environ,
        },
        "FLOODINGNAQUE_DATA_DIR": {
            "description": "Raw data directory path",
            "default": "data",
            "is_set": "FLOODINGNAQUE_DATA_DIR" in os.environ,
        },
        "FLOODINGNAQUE_PROCESSED_DIR": {
            "description": "Processed data directory path",
            "default": "data/processed",
            "is_set": "FLOODINGNAQUE_PROCESSED_DIR" in os.environ,
        },
        "FLOODINGNAQUE_LOG_LEVEL": {
            "description": "Logging level (DEBUG/INFO/WARNING/ERROR)",
            "default": "INFO",
            "is_set": "FLOODINGNAQUE_LOG_LEVEL" in os.environ,
        },
        "FLOODINGNAQUE_LOG_DIR": {
            "description": "Log directory path",
            "default": "logs",
            "is_set": "FLOODINGNAQUE_LOG_DIR" in os.environ,
        },
        "FLOODINGNAQUE_RANDOM_STATE": {
            "description": "Random seed for reproducibility",
            "default": "42",
            "is_set": "FLOODINGNAQUE_RANDOM_STATE" in os.environ,
        },
        "FLOODINGNAQUE_CV_FOLDS": {
            "description": "Number of cross-validation folds",
            "default": "10",
            "is_set": "FLOODINGNAQUE_CV_FOLDS" in os.environ,
        },
        "FLOODINGNAQUE_BACKUP_DIR": {
            "description": "Backup directory path",
            "default": "backups",
            "is_set": "FLOODINGNAQUE_BACKUP_DIR" in os.environ,
        },
        "FLOODINGNAQUE_MAX_BACKUPS": {
            "description": "Maximum number of backups to retain",
            "default": "5",
            "is_set": "FLOODINGNAQUE_MAX_BACKUPS" in os.environ,
        },
        "FLOODINGNAQUE_MAX_RETRIES": {
            "description": "Maximum API retry attempts",
            "default": "3",
            "is_set": "FLOODINGNAQUE_MAX_RETRIES" in os.environ,
        },
        "FLOODINGNAQUE_RETRY_DELAY": {
            "description": "Delay between API retries (seconds)",
            "default": "1",
            "is_set": "FLOODINGNAQUE_RETRY_DELAY" in os.environ,
        },
        "FLOODINGNAQUE_VALIDATE_CONFIG": {
            "description": "Enable/disable config schema validation",
            "default": "true",
            "is_set": "FLOODINGNAQUE_VALIDATE_CONFIG" in os.environ,
        },
        "FLOODINGNAQUE_STRICT_VALIDATION": {
            "description": "Fail on validation errors (vs warning)",
            "default": "false",
            "is_set": "FLOODINGNAQUE_STRICT_VALIDATION" in os.environ,
        },
    }

    # Feature flag environment variables
    flag_env_vars = {k: v for k, v in os.environ.items() if k.startswith("FLOODINGNAQUE_FLAG_")}

    return jsonify(
        {
            "success": True,
            "data": {
                "supported_variables": env_vars,
                "feature_flag_overrides": list(flag_env_vars.keys()),
                "total_supported": len(env_vars),
                "total_set": sum(1 for v in env_vars.values() if v["is_set"]),
            },
        }
    )
