"""
Dashboard API Service - Flask Application Factory

Aggregates data from weather-collector, ml-prediction,
alert-notification, and user-management services to serve
the frontend dashboard.
"""

import os
import logging
from flask import Flask
from flask_cors import CORS

logger = logging.getLogger(__name__)


def create_app(testing: bool = False) -> Flask:
    """Create and configure the Dashboard API Flask application."""
    app = Flask(__name__)

    # ---------- configuration ----------
    app.config["TESTING"] = testing
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-dashboard-secret")
    app.config["JWT_SECRET"] = os.getenv("JWT_SECRET", "dev-jwt-secret")

    # Service endpoints
    app.config["WEATHER_SERVICE_URL"] = os.getenv(
        "WEATHER_SERVICE_URL", "http://weather-collector:5001"
    )
    app.config["PREDICTION_SERVICE_URL"] = os.getenv(
        "PREDICTION_SERVICE_URL", "http://ml-prediction:5002"
    )
    app.config["ALERT_SERVICE_URL"] = os.getenv(
        "ALERT_SERVICE_URL", "http://alert-notification:5003"
    )
    app.config["USER_SERVICE_URL"] = os.getenv(
        "USER_SERVICE_URL", "http://user-management:5004"
    )

    # Redis
    app.config["REDIS_URL"] = os.getenv("REDIS_URL", "redis://redis:6379/0")
    app.config["CACHE_TTL"] = int(os.getenv("CACHE_TTL", "60"))

    # Database (read-only access for direct queries when needed)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL",
        "postgresql://floodingnaque:password@db:5432/floodingnaque",
    )

    # ---------- CORS ----------
    CORS(
        app,
        resources={r"/api/*": {"origins": os.getenv("CORS_ORIGINS", "*").split(",")}},
        supports_credentials=True,
    )

    # ---------- shared infrastructure ----------
    try:
        from shared.health import create_health_blueprint
        from shared.errors import register_error_handlers
        from shared.tracing import setup_tracing_middleware

        health_bp = create_health_blueprint("dashboard-api")
        app.register_blueprint(health_bp)
        register_error_handlers(app)
        setup_tracing_middleware(app, "dashboard-api")
    except ImportError:
        logger.warning("Shared package not available - running in standalone mode")

    # ---------- service blueprints ----------
    from app.routes import register_blueprints

    register_blueprints(app)

    # ---------- service clients ----------
    _init_service_clients(app)

    logger.info("Dashboard API Service initialised")
    return app


def _init_service_clients(app: Flask) -> None:
    """Lazily create inter-service HTTP clients and attach to app context."""
    try:
        from shared.messaging import (
            create_weather_client,
            create_prediction_client,
            create_alert_client,
            create_user_client,
        )

        app.weather_client = create_weather_client()
        app.prediction_client = create_prediction_client()
        app.alert_client = create_alert_client()
        app.user_client = create_user_client()
        logger.info("Inter-service clients initialised")
    except ImportError:
        logger.warning("Service clients unavailable - direct HTTP fallback")
        app.weather_client = None
        app.prediction_client = None
        app.alert_client = None
        app.user_client = None
