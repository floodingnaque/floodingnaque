"""Configuration management for Floodingnaque API."""

import logging
import os
import secrets as python_secrets  # Renamed to avoid conflict with our secrets module
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import List, Optional

from app.utils.secrets import get_secret
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Base directory for the backend
BASE_DIR = Path(__file__).resolve().parent.parent.parent


def is_debug_mode() -> bool:
    """
    Check if application is running in debug mode.

    Centralized check for consistent debug mode detection across the app.
    Uses FLASK_DEBUG environment variable.

    Returns:
        bool: True if debug mode is enabled
    """
    return os.getenv("FLASK_DEBUG", "False").lower() == "true"


def _get_secret_key() -> str:
    """
    Get SECRET_KEY from environment or Docker secret with security validation.

    Supports Docker Secrets _FILE pattern:
    - First checks SECRET_KEY_FILE environment variable
    - Falls back to SECRET_KEY environment variable
    - In development, generates a temporary key with warning
    - In production (FLASK_DEBUG=False), fails if not explicitly set
    """
    # Use get_secret for Docker Secrets _FILE pattern support
    key = get_secret("SECRET_KEY")
    is_debug = os.getenv("FLASK_DEBUG", "False").lower() == "true"

    if not key or key in ("change-me-in-production", "change_this_to_a_random_secret_key_in_production"):
        if not is_debug:
            raise ValueError(
                "CRITICAL: SECRET_KEY must be set in production! "
                "Set SECRET_KEY_FILE=/run/secrets/secret_key or SECRET_KEY env var. "
                'Generate one with: python -c "import secrets; print(secrets.token_hex(32))"'
            )
        # Development mode - generate temporary key
        key = python_secrets.token_hex(32)
        logger.warning(
            "SECRET_KEY not configured - using temporary key. "
            "Set SECRET_KEY or SECRET_KEY_FILE in .env for persistent sessions."
        )
    return key


def _get_jwt_secret_key() -> str:
    """
    Get JWT_SECRET_KEY with security validation.

    Supports Docker Secrets _FILE pattern:
    - First checks JWT_SECRET_KEY_FILE environment variable
    - Falls back to JWT_SECRET_KEY environment variable
    """
    key = get_secret("JWT_SECRET_KEY")
    is_debug = os.getenv("FLASK_DEBUG", "False").lower() == "true"

    if not key or key in ("change_this_to_another_random_secret_key",):
        if not is_debug:
            raise ValueError(
                "CRITICAL: JWT_SECRET_KEY must be set in production! "
                "Set JWT_SECRET_KEY_FILE=/run/secrets/jwt_secret_key or JWT_SECRET_KEY env var. "
                'Generate one with: python -c "import secrets; print(secrets.token_hex(32))"'
            )
        key = python_secrets.token_hex(32)
        logger.warning("JWT_SECRET_KEY not configured - using temporary key.")
    return key


def _get_db_ssl_mode() -> str:
    """
    Get DB_SSL_MODE with environment-specific defaults.

    - Production/Staging: defaults to 'verify-full' (maximum security)
    - Development: defaults to 'require' (encrypted, no certificate needed)

    Returns:
        str: SSL mode (require, verify-ca, or verify-full)
    """
    ssl_mode = os.getenv("DB_SSL_MODE", "").lower()

    if ssl_mode in ("require", "verify-ca", "verify-full"):
        return ssl_mode

    # Environment-based defaults
    app_env = os.getenv("APP_ENV", "development").lower()

    if app_env in ("production", "prod", "staging", "stage"):
        return "verify-full"

    return "require"


def _get_database_url() -> str:
    """
    Get DATABASE_URL with environment-specific validation.

    Supports Docker Secrets _FILE pattern:
    - First checks DATABASE_URL_FILE environment variable
    - Falls back to DATABASE_URL environment variable

    - Production: Requires Supabase PostgreSQL with SSL (fails if not set or using SQLite)
    - Staging: Requires PostgreSQL with SSL (fails if using SQLite)
    - Development: Allows SQLite fallback with warning

    Returns:
        str: Database connection URL

    Raises:
        ValueError: If production/staging uses SQLite or DATABASE_URL not configured
    """
    # Use get_secret for Docker Secrets _FILE pattern support
    url = get_secret("DATABASE_URL", default="")
    is_debug = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    app_env = os.getenv("APP_ENV", "development").lower()

    # Production and staging require PostgreSQL/Supabase
    if app_env in ("production", "prod", "staging", "stage"):
        if not url:
            raise ValueError(
                f"CRITICAL: DATABASE_URL must be set for {app_env}! "
                "Configure a Supabase PostgreSQL connection string in your .env file. "
                "Format: postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres?sslmode=require"
            )
        if url.startswith("sqlite"):
            raise ValueError(
                f"CRITICAL: SQLite is not allowed in {app_env}! " "Configure a Supabase PostgreSQL connection string."
            )

        # Enforce SSL mode for production PostgreSQL connections
        if url.startswith("postgresql") and "sslmode=" not in url:
            logger.warning(
                "DATABASE_URL does not specify sslmode. " "Automatically adding sslmode=require for security."
            )
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}sslmode=require"

        return url

    # Development mode - allow SQLite fallback with warning
    if not url:
        fallback = "sqlite:///data/floodingnaque.db"
        logger.warning(
            "DATABASE_URL not configured - using SQLite fallback for development. "
            "Set DATABASE_URL to use Supabase PostgreSQL."
        )
        return fallback

    if url.startswith("sqlite") and not is_debug:
        logger.warning(
            "Using SQLite database. This is not recommended for production. "
            "Configure Supabase PostgreSQL for better reliability."
        )

    return url


def get_env_file() -> Path:
    """
    Determine which .env file to load based on APP_ENV.

    Priority:
    1. APP_ENV environment variable (development, staging, production)
    2. Falls back to .env if exists, otherwise .env.development

    Returns:
        Path to the appropriate .env file
    """
    app_env = os.getenv("APP_ENV", "").lower()

    env_file_map = {
        "development": ".env.development",
        "dev": ".env.development",
        "staging": ".env.staging",
        "stage": ".env.staging",
        "production": ".env.production",
        "prod": ".env.production",
    }

    # Get the appropriate env file name
    env_file_name = env_file_map.get(app_env)

    if env_file_name:
        env_file = BASE_DIR / env_file_name
        if env_file.exists():
            return env_file
        logger.warning(f"Environment file {env_file_name} not found, falling back...")

    # Default to .env.development for local development
    dev_env = BASE_DIR / ".env.development"
    if dev_env.exists():
        logger.info("Using .env.development as default")
        return dev_env

    # No env file found - will rely on system environment variables
    logger.warning("No .env file found. Using system environment variables only.")
    return dev_env  # Return path even if doesn't exist - load_dotenv handles gracefully


def load_env() -> None:
    """
    Load environment variables from the appropriate .env file.

    The file is selected based on APP_ENV environment variable:
    - development/dev -> .env.development
    - staging/stage -> .env.staging
    - production/prod -> .env.production
    - (unset) -> .env or .env.development

    In testing mode (TESTING=true), .env files are NOT loaded to allow
    test fixtures to fully control the environment.
    """
    # In testing mode, skip loading .env files entirely
    # This allows test fixtures to control all environment variables
    is_testing = os.getenv("TESTING", "false").lower() == "true"
    if is_testing:
        logger.debug("TESTING=true: Skipping .env file loading")
        return

    env_file = get_env_file()

    if env_file.exists():
        logger.info(f"Loading environment from: {env_file.name}")
        load_dotenv(env_file, override=False)
    else:
        logger.warning(f"Environment file not found: {env_file}")
        load_dotenv(override=False)  # Try to load from default .env


@dataclass
class Config:
    """
    Application configuration with validation.

    All values are loaded from environment variables with sensible defaults.
    """

    # Flask Settings - SECRET_KEY fails in production if not set
    SECRET_KEY: str = field(default_factory=_get_secret_key)
    JWT_SECRET_KEY: str = field(default_factory=_get_jwt_secret_key)
    DEBUG: bool = field(default_factory=lambda: os.getenv("FLASK_DEBUG", "False").lower() == "true")
    HOST: str = field(default_factory=lambda: os.getenv("HOST", "0.0.0.0"))  # nosec B104
    PORT: int = field(default_factory=lambda: int(os.getenv("PORT", "5000")))

    # Database - Supabase PostgreSQL is required (no SQLite fallback in production)
    DATABASE_URL: str = field(default_factory=lambda: _get_database_url())

    # Connection Pool Settings for Production
    # Adjust based on your database plan limits:
    # - Supabase Free: pool_size=3, max_overflow=5
    # - Supabase Pro: pool_size=20, max_overflow=10
    # - Self-hosted: pool_size=20-50 based on resources
    DB_POOL_SIZE: int = field(default_factory=lambda: int(os.getenv("DB_POOL_SIZE", "20")))
    DB_MAX_OVERFLOW: int = field(default_factory=lambda: int(os.getenv("DB_MAX_OVERFLOW", "10")))
    DB_POOL_RECYCLE: int = field(default_factory=lambda: int(os.getenv("DB_POOL_RECYCLE", "1800")))  # 30 min default
    DB_POOL_TIMEOUT: int = field(default_factory=lambda: int(os.getenv("DB_POOL_TIMEOUT", "30")))
    DB_POOL_PRE_PING: bool = field(default_factory=lambda: os.getenv("DB_POOL_PRE_PING", "True").lower() == "true")
    DB_ECHO_POOL: bool = field(default_factory=lambda: os.getenv("DB_ECHO_POOL", "False").lower() == "true")

    # Database SSL Configuration
    # - require: Encrypted connection, no certificate verification (development default)
    # - verify-ca: Encrypted + verify CA certificate
    # - verify-full: Encrypted + verify CA + hostname check (production recommended)
    DB_SSL_MODE: str = field(default_factory=lambda: _get_db_ssl_mode())
    DB_SSL_CA_CERT: str = field(default_factory=lambda: os.getenv("DB_SSL_CA_CERT", ""))

    # Security
    RATE_LIMIT_ENABLED: bool = field(default_factory=lambda: os.getenv("RATE_LIMIT_ENABLED", "True").lower() == "true")
    RATE_LIMIT_DEFAULT: int = field(default_factory=lambda: int(os.getenv("RATE_LIMIT_DEFAULT", "100")))
    ENABLE_HTTPS: bool = field(default_factory=lambda: os.getenv("ENABLE_HTTPS", "False").lower() == "true")

    # JWT Token Settings
    JWT_ACCESS_TOKEN_EXPIRES_MINUTES: int = field(
        default_factory=lambda: int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES_MINUTES", "30"))
    )
    JWT_REFRESH_TOKEN_EXPIRES_DAYS: int = field(
        default_factory=lambda: int(os.getenv("JWT_REFRESH_TOKEN_EXPIRES_DAYS", "7"))
    )
    JWT_TOKEN_LOCATION: List[str] = field(default_factory=lambda: os.getenv("JWT_TOKEN_LOCATION", "headers").split(","))
    JWT_ALGORITHM: str = field(default_factory=lambda: os.getenv("JWT_ALGORITHM", "HS256"))

    # Model Security (supports _FILE pattern for Docker Secrets)
    MODEL_SIGNING_KEY: str = field(default_factory=lambda: get_secret("MODEL_SIGNING_KEY", default=""))
    REQUIRE_MODEL_SIGNATURE: bool = field(
        default_factory=lambda: os.getenv("REQUIRE_MODEL_SIGNATURE", "false").lower() == "true"
    )
    VERIFY_MODEL_INTEGRITY: bool = field(
        default_factory=lambda: os.getenv("VERIFY_MODEL_INTEGRITY", "true").lower() == "true"
    )

    # CORS
    CORS_ORIGINS: str = field(default_factory=lambda: os.getenv("CORS_ORIGINS", "https://floodingnaque.vercel.app"))

    # External APIs (supports _FILE pattern for Docker Secrets)
    OWM_API_KEY: str = field(default_factory=lambda: get_secret("OWM_API_KEY", default=""))
    WEATHERSTACK_API_KEY: str = field(default_factory=lambda: get_secret("WEATHERSTACK_API_KEY", default=""))

    # Meteostat Configuration
    METEOSTAT_ENABLED: bool = field(default_factory=lambda: os.getenv("METEOSTAT_ENABLED", "True").lower() == "true")
    METEOSTAT_CACHE_MAX_AGE_DAYS: int = field(
        default_factory=lambda: int(os.getenv("METEOSTAT_CACHE_MAX_AGE_DAYS", "7"))
    )
    METEOSTAT_STATION_ID: str = field(default_factory=lambda: os.getenv("METEOSTAT_STATION_ID", ""))
    METEOSTAT_AS_FALLBACK: bool = field(
        default_factory=lambda: os.getenv("METEOSTAT_AS_FALLBACK", "True").lower() == "true"
    )

    # Model Configuration
    MODEL_DIR: str = field(default_factory=lambda: os.getenv("MODEL_DIR", "models"))
    MODEL_NAME: str = field(default_factory=lambda: os.getenv("MODEL_NAME", "flood_rf_model"))

    # Logging
    LOG_LEVEL: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    LOG_FORMAT: str = field(default_factory=lambda: os.getenv("LOG_FORMAT", "json"))
    LOG_SAMPLING_ENABLED: bool = field(
        default_factory=lambda: os.getenv("LOG_SAMPLING_ENABLED", "False").lower() == "true"
    )
    LOG_SAMPLING_RATE: float = field(
        default_factory=lambda: float(os.getenv("LOG_SAMPLING_RATE", "0.1"))
    )  # Sample 10% of logs
    LOG_SAMPLING_EXCLUDE_ERRORS: bool = field(
        default_factory=lambda: os.getenv("LOG_SAMPLING_EXCLUDE_ERRORS", "True").lower() == "true"
    )

    # Default Location (Parañaque City)
    DEFAULT_LATITUDE: float = field(default_factory=lambda: float(os.getenv("DEFAULT_LATITUDE", "14.4793")))
    DEFAULT_LONGITUDE: float = field(default_factory=lambda: float(os.getenv("DEFAULT_LONGITUDE", "121.0198")))

    def get_cors_origins_list(self) -> List[str]:
        """Get CORS origins as a list."""
        if not self.CORS_ORIGINS:
            return []
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    def get_jwt_access_token_expires(self) -> timedelta:
        """Get JWT access token expiration as timedelta."""
        return timedelta(minutes=self.JWT_ACCESS_TOKEN_EXPIRES_MINUTES)

    def get_jwt_refresh_token_expires(self) -> timedelta:
        """Get JWT refresh token expiration as timedelta."""
        return timedelta(days=self.JWT_REFRESH_TOKEN_EXPIRES_DAYS)

    @classmethod
    def validate(cls) -> List[str]:
        """
        Validate configuration and return list of warnings/errors.

        Returns:
            List of warning/error messages (empty if all valid)
        """
        warnings = []
        config = cls()

        # Check required API keys in production
        if not config.DEBUG:
            if not config.OWM_API_KEY or config.OWM_API_KEY == "your_openweathermap_api_key_here":
                warnings.append("OWM_API_KEY is not configured")

            if config.SECRET_KEY == "change-me-in-production":  # nosec B105
                warnings.append("SECRET_KEY should be changed in production")

            if not config.CORS_ORIGINS:
                warnings.append("CORS_ORIGINS should be configured in production")

            if not config.ENABLE_HTTPS:
                warnings.append("HTTPS should be enabled in production")

            # JWT security checks
            if config.JWT_ACCESS_TOKEN_EXPIRES_MINUTES > 60:
                warnings.append(
                    f"JWT_ACCESS_TOKEN_EXPIRES_MINUTES is {config.JWT_ACCESS_TOKEN_EXPIRES_MINUTES}. "
                    "Consider shorter expiration (15-30 minutes) for production."
                )

            # Model security checks
            if config.REQUIRE_MODEL_SIGNATURE and not config.MODEL_SIGNING_KEY:
                warnings.append("REQUIRE_MODEL_SIGNATURE is enabled but MODEL_SIGNING_KEY is not set")

        return warnings

    @classmethod
    def from_env(cls) -> "Config":
        """Create Config instance from environment variables."""
        load_env()
        return cls()


# Global config instance (lazy initialization)
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global config instance."""
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config
