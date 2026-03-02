"""
Weather Data Collector Service — Flask Application Factory.
"""

import logging
import os

from flask import Flask
from flask_cors import CORS

logger = logging.getLogger(__name__)

SERVICE_NAME = "weather-collector"
SERVICE_VERSION = "1.0.0"


def create_app(config_override: dict = None) -> Flask:
    """Create and configure the Weather Collector Flask application."""
    from shared.config import load_env
    from shared.errors import register_error_handlers
    from shared.health import create_health_blueprint
    from shared.tracing import setup_tracing_middleware

    load_env()

    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-weather-secret")
    app.config["JSON_SORT_KEYS"] = False

    if config_override:
        app.config.update(config_override)

    # CORS
    CORS(app, origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","))

    # Distributed tracing
    setup_tracing_middleware(app, SERVICE_NAME)

    # Error handlers
    register_error_handlers(app)

    # Health checks
    health_bp = create_health_blueprint(SERVICE_NAME, SERVICE_VERSION)
    app.register_blueprint(health_bp)

    # Register health dependency checks
    def check_database():
        try:
            from shared.database import get_engine
            from sqlalchemy import text
            with get_engine().connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    health_bp.register_dependency_check("database", check_database)

    # Service routes
    from app.routes.weather import weather_bp
    from app.routes.ingest import ingest_bp
    from app.routes.tides import tides_bp
    from app.routes.data import data_bp

    app.register_blueprint(weather_bp, url_prefix="/api/v1/weather")
    app.register_blueprint(ingest_bp, url_prefix="/api/v1/ingest")
    app.register_blueprint(tides_bp, url_prefix="/api/v1/tides")
    app.register_blueprint(data_bp, url_prefix="/api/v1/data")

    # Register with service registry
    with app.app_context():
        _register_service()
        _start_scheduler(app)

    logger.info("%s v%s initialized", SERVICE_NAME, SERVICE_VERSION)
    return app


def _register_service():
    """Register this service with the service registry."""
    try:
        from shared.discovery import ServiceRegistry
        registry = ServiceRegistry.get_instance()
        port = int(os.getenv("PORT", 5001))
        registry.register(
            service_name="weather-collector",
            host=os.getenv("HOSTNAME", "weather-collector"),
            port=port,
            metadata={"version": SERVICE_VERSION, "health_url": "/health"},
        )
        registry.start_heartbeat_loop("weather-collector")
    except Exception as e:
        logger.warning("Service registration failed (non-fatal): %s", e)


def _start_scheduler(app):
    """Start background weather data collection scheduler."""
    scheduler_enabled = os.getenv("SCHEDULER_ENABLED", "true").lower() == "true"
    if not scheduler_enabled:
        logger.info("Scheduler disabled")
        return

    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        scheduler = BackgroundScheduler()

        # Collect weather data every 15 minutes
        scheduler.add_job(
            func=lambda: _collect_weather_data(app),
            trigger="interval",
            minutes=int(os.getenv("WEATHER_COLLECTION_INTERVAL_MIN", "15")),
            id="collect_weather",
            name="Collect weather data from external APIs",
        )

        # Collect tide data every hour
        scheduler.add_job(
            func=lambda: _collect_tide_data(app),
            trigger="interval",
            minutes=int(os.getenv("TIDE_COLLECTION_INTERVAL_MIN", "60")),
            id="collect_tides",
            name="Collect tide data",
        )

        scheduler.start()
        logger.info("Weather collection scheduler started")
    except Exception as e:
        logger.error("Failed to start scheduler: %s", e)


def _collect_weather_data(app):
    """Background job: collect weather data from all sources."""
    with app.app_context():
        try:
            from app.services.collector import WeatherCollector
            collector = WeatherCollector()
            result = collector.collect_all()
            logger.info("Weather data collected: %s records", result.get("total", 0))

            # Publish event for downstream services
            from shared.messaging import EventBus
            bus = EventBus()
            bus.publish("weather.data.collected", result)
        except Exception as e:
            logger.error("Weather collection failed: %s", e)


def _collect_tide_data(app):
    """Background job: collect tide data."""
    with app.app_context():
        try:
            from app.services.collector import WeatherCollector
            collector = WeatherCollector()
            result = collector.collect_tides()
            logger.info("Tide data collected: %s records", result.get("total", 0))

            from shared.messaging import EventBus
            bus = EventBus()
            bus.publish("weather.tides.collected", result)
        except Exception as e:
            logger.error("Tide collection failed: %s", e)
