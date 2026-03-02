"""
Shared configuration module for Floodingnaque microservices.

Provides environment-aware configuration loading that each service
inherits and extends with service-specific settings.
"""

import logging
import os
import secrets
from dataclasses import dataclass, field
from typing import List, Optional

from dotenv import load_dotenv

logger = logging.getLogger(__name__)


def load_env():
    """Load environment variables from .env file."""
    env = os.getenv("APP_ENV", "development")
    env_file = f".env.{env}"
    if os.path.exists(env_file):
        load_dotenv(env_file)
    elif os.path.exists(".env"):
        load_dotenv(".env")


def get_secret(key: str, default: str = "") -> str:
    """
    Get secret from environment or Docker Secrets _FILE pattern.

    Docker Secrets mount files at /run/secrets/<name>. This function
    checks for <KEY>_FILE env var first, then falls back to <KEY>.
    """
    file_key = f"{key}_FILE"
    file_path = os.getenv(file_key)
    if file_path and os.path.isfile(file_path):
        try:
            with open(file_path, "r") as f:
                return f.read().strip()
        except OSError:
            pass
    return os.getenv(key, default)


@dataclass
class BaseServiceConfig:
    """Base configuration shared by all microservices."""

    # Service identity
    SERVICE_NAME: str = "unknown-service"
    SERVICE_VERSION: str = "1.0.0"
    SERVICE_PORT: int = 5000

    # Environment
    APP_ENV: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # Database
    DATABASE_URL: str = ""
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security
    SECRET_KEY: str = ""
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRES: int = 3600  # 1 hour
    JWT_REFRESH_TOKEN_EXPIRES: int = 2592000  # 30 days

    # Service discovery
    SERVICE_REGISTRY_URL: str = ""
    API_GATEWAY_URL: str = ""

    # Inter-service communication
    WEATHER_SERVICE_URL: str = "http://weather-collector:5001"
    ML_PREDICTION_SERVICE_URL: str = "http://ml-prediction:5002"
    ALERT_SERVICE_URL: str = "http://alert-notification:5003"
    USER_SERVICE_URL: str = "http://user-management:5004"
    DASHBOARD_SERVICE_URL: str = "http://dashboard-api:5005"

    # Rate limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_DEFAULT: str = "100/hour"

    # CORS
    CORS_ORIGINS: List[str] = field(default_factory=lambda: ["http://localhost:5173"])

    def __post_init__(self):
        """Load from environment variables after init."""
        self.APP_ENV = os.getenv("APP_ENV", self.APP_ENV)
        self.DEBUG = os.getenv("FLASK_DEBUG", str(self.DEBUG)).lower() == "true"
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", self.LOG_LEVEL)

        self.DATABASE_URL = get_secret("DATABASE_URL") or self.DATABASE_URL
        self.REDIS_URL = os.getenv("REDIS_URL", self.REDIS_URL)

        self.SECRET_KEY = get_secret("SECRET_KEY") or secrets.token_hex(32)
        self.JWT_SECRET_KEY = get_secret("JWT_SECRET_KEY") or self.SECRET_KEY

        # Service URLs from environment
        self.WEATHER_SERVICE_URL = os.getenv("WEATHER_SERVICE_URL", self.WEATHER_SERVICE_URL)
        self.ML_PREDICTION_SERVICE_URL = os.getenv("ML_PREDICTION_SERVICE_URL", self.ML_PREDICTION_SERVICE_URL)
        self.ALERT_SERVICE_URL = os.getenv("ALERT_SERVICE_URL", self.ALERT_SERVICE_URL)
        self.USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", self.USER_SERVICE_URL)
        self.DASHBOARD_SERVICE_URL = os.getenv("DASHBOARD_SERVICE_URL", self.DASHBOARD_SERVICE_URL)

        cors = os.getenv("CORS_ORIGINS", "")
        if cors:
            self.CORS_ORIGINS = [o.strip() for o in cors.split(",")]

    @property
    def is_production(self) -> bool:
        return self.APP_ENV in ("production", "prod", "staging", "stage")

    def validate(self) -> List[str]:
        """Validate configuration, return list of warnings."""
        warnings = []
        if self.is_production:
            if not self.DATABASE_URL:
                warnings.append("DATABASE_URL not set for production")
            if self.SECRET_KEY == "" or len(self.SECRET_KEY) < 32:
                warnings.append("SECRET_KEY is weak or not set")
        return warnings
