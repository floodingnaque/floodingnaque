"""
Secret management utilities for Docker Secrets support.

This module provides utilities for reading secrets from files using the
Docker Secrets _FILE suffix pattern. This is the recommended approach for
production deployments as it avoids exposing secrets in environment variables.

Usage:
    # Instead of directly using os.getenv():
    from app.utils.secrets import get_secret

    # This will check SECRET_KEY_FILE first, then fall back to SECRET_KEY
    secret_key = get_secret("SECRET_KEY")

    # With a default value:
    api_key = get_secret("API_KEY", default="development-key")

The _FILE Pattern:
    When running with Docker Secrets, sensitive values are mounted as files
    at /run/secrets/<secret_name>. By convention, the application checks for
    an environment variable with _FILE suffix first:

    1. If SECRET_KEY_FILE=/run/secrets/secret_key exists and is readable,
       the content of that file is returned (stripped of whitespace)
    2. Otherwise, the value of SECRET_KEY environment variable is returned
    3. If neither exists, the default value is returned

Security Benefits:
    - Secrets are never exposed in process listings or logs
    - Secrets are not visible via docker inspect
    - Secrets remain in memory-only tmpfs filesystems
    - Secrets can be rotated without rebuilding containers
"""

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Default Docker secrets path
DOCKER_SECRETS_PATH = Path("/run/secrets")


def read_secret_file(file_path: str) -> Optional[str]:
    """
    Safely read a secret from a file.

    Args:
        file_path: Path to the secret file

    Returns:
        The file contents stripped of leading/trailing whitespace,
        or None if the file doesn't exist or can't be read
    """
    try:
        path = Path(file_path)
        if path.exists() and path.is_file():
            # Read the secret and strip whitespace (including trailing newlines)
            secret = path.read_text(encoding="utf-8").strip()
            if secret:
                return secret
            logger.warning(f"Secret file {file_path} is empty")
            return None
    except PermissionError:
        logger.error(f"Permission denied reading secret file: {file_path}")
    except OSError as e:
        logger.error(f"Error reading secret file {file_path}: {e}")
    return None


def get_secret(
    name: str,
    default: Optional[str] = None,
    required: bool = False,
    secret_path: Path = DOCKER_SECRETS_PATH,
) -> Optional[str]:
    """
    Get a secret value using the _FILE suffix pattern.

    This function implements the Docker Secrets _FILE convention:
    1. First checks for {name}_FILE environment variable
    2. If found and file is readable, returns file contents
    3. Otherwise, returns the value of {name} environment variable
    4. If neither exists, returns the default value

    Args:
        name: Base name of the secret (e.g., "SECRET_KEY")
        default: Default value if secret is not found
        required: If True, raises ValueError when secret is not found
        secret_path: Base path for Docker secrets (default: /run/secrets)

    Returns:
        The secret value, or the default if not found

    Raises:
        ValueError: If required=True and the secret is not found

    Examples:
        >>> get_secret("DATABASE_URL")
        'postgresql://user:pass@host/db'

        >>> get_secret("API_KEY", default="dev-key")
        'dev-key'

        >>> get_secret("REQUIRED_SECRET", required=True)
        ValueError: Required secret REQUIRED_SECRET not found
    """
    # Check for _FILE suffix environment variable first
    file_env_var = f"{name}_FILE"
    file_path = os.getenv(file_env_var)

    if file_path:
        secret = read_secret_file(file_path)
        if secret:
            logger.debug(f"Loaded secret {name} from file")
            return secret
        logger.warning(f"{file_env_var} is set but file could not be read")

    # Check for Docker secret at default path (by convention, lowercase filename)
    default_secret_path = secret_path / name.lower()
    if default_secret_path.exists():
        secret = read_secret_file(str(default_secret_path))
        if secret:
            logger.debug(f"Loaded secret {name} from {default_secret_path}")
            return secret

    # Fall back to regular environment variable
    env_value = os.getenv(name)
    if env_value:
        return env_value

    # Use default or raise if required
    if required and default is None:
        raise ValueError(
            f"Required secret {name} not found. "
            f"Set {name} environment variable, {file_env_var} pointing to a secret file, "
            f"or mount a Docker secret at {default_secret_path}"
        )

    return default


def get_secret_or_env(
    secret_name: str,
    env_name: Optional[str] = None,
    default: Optional[str] = None,
    required: bool = False,
) -> Optional[str]:
    """
    Get a secret with a different environment variable name.

    Useful when the Docker secret name differs from the environment variable name.

    Args:
        secret_name: Name of the Docker secret file
        env_name: Environment variable name (defaults to secret_name.upper())
        default: Default value if not found
        required: If True, raises ValueError when not found

    Returns:
        The secret value

    Examples:
        >>> get_secret_or_env("db_password", env_name="PGBOUNCER_DB_PASSWORD")
    """
    env_name = env_name or secret_name.upper()

    # Check _FILE suffix first
    file_path = os.getenv(f"{env_name}_FILE")
    if file_path:
        secret = read_secret_file(file_path)
        if secret:
            return secret

    # Check for secret file at default path
    secret_path = DOCKER_SECRETS_PATH / secret_name
    if secret_path.exists():
        secret = read_secret_file(str(secret_path))
        if secret:
            return secret

    # Fall back to environment variable
    env_value = os.getenv(env_name)
    if env_value:
        return env_value

    if required and default is None:
        raise ValueError(f"Required secret {secret_name} (env: {env_name}) not found")

    return default


def mask_secret(value: str, visible_chars: int = 4) -> str:
    """
    Mask a secret value for safe logging.

    Args:
        value: The secret value to mask
        visible_chars: Number of characters to show at the end

    Returns:
        Masked string like "****abcd"

    Examples:
        >>> mask_secret("my-secret-api-key")
        '****-key'
    """
    if not value or len(value) <= visible_chars:
        return "****"
    return "*" * (len(value) - visible_chars) + value[-visible_chars:]


def validate_secrets(secret_names: list[str]) -> dict[str, bool]:
    """
    Validate that required secrets are available.

    Args:
        secret_names: List of secret names to validate

    Returns:
        Dictionary mapping secret names to availability status

    Examples:
        >>> validate_secrets(["SECRET_KEY", "DATABASE_URL"])
        {'SECRET_KEY': True, 'DATABASE_URL': True}
    """
    results = {}
    for name in secret_names:
        try:
            value = get_secret(name)
            results[name] = value is not None and len(value) > 0
        except Exception:
            results[name] = False
    return results


# List of secrets that should use the _FILE pattern in production
PRODUCTION_SECRETS = [
    "SECRET_KEY",
    "JWT_SECRET_KEY",
    "DATABASE_URL",
    "REDIS_URL",
    "CACHE_REDIS_URL",
    "CELERY_BROKER_URL",
    "CELERY_RESULT_BACKEND",
    "OWM_API_KEY",
    "WEATHERSTACK_API_KEY",
    "MODEL_SIGNING_KEY",
    "PGBOUNCER_DB_PASSWORD",
    "PGBOUNCER_ADMIN_PASSWORD",
    "PGBOUNCER_STATS_PASSWORD",
]
