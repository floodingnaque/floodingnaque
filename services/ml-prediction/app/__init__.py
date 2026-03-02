"""
ML Prediction Service — Flask Application Factory.
"""

import logging
import os

from flask import Flask
from flask_cors import CORS

logger = logging.getLogger(__name__)

SERVICE_NAME = "ml-prediction"
SERVICE_VERSION = "1.0.0"


def create_app(config_override: dict = None) -> Flask:
    """Create and configure the ML Prediction Flask application."""
    from shared.config import load_env
    from shared.errors import register_error_handlers
    from shared.health import create_health_blueprint
    from shared.tracing import setup_tracing_middleware

    load_env()

    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-ml-secret")
    app.config["JSON_SORT_KEYS"] = False

    if config_override:
        app.config.update(config_override)

    CORS(app, origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","))
    setup_tracing_middleware(app, SERVICE_NAME)
    register_error_handlers(app)

    # Health checks
    health_bp = create_health_blueprint(SERVICE_NAME, SERVICE_VERSION)
    app.register_blueprint(health_bp)

    def check_model():
        try:
            from app.services.predictor import FloodPredictor
            predictor = FloodPredictor.get_instance()
            return predictor.is_model_loaded()
        except Exception:
            return False

    health_bp.register_dependency_check("ml_model", check_model)

    # Routes
    from app.routes.predict import predict_bp
    from app.routes.models import models_bp
    from app.routes.batch import batch_bp

    app.register_blueprint(predict_bp, url_prefix="/api/v1/predict")
    app.register_blueprint(models_bp, url_prefix="/api/v1/models")
    app.register_blueprint(batch_bp, url_prefix="/api/v1/batch")

    # Pre-load model on startup
    with app.app_context():
        _preload_model()
        _register_service()
        _subscribe_to_events()

    logger.info("%s v%s initialized", SERVICE_NAME, SERVICE_VERSION)
    return app


def _preload_model():
    """Pre-load the ML model on service startup."""
    try:
        from app.services.predictor import FloodPredictor
        predictor = FloodPredictor.get_instance()
        predictor.load_model()
        logger.info("ML model pre-loaded successfully")
    except Exception as e:
        logger.warning("Model pre-load failed (will load on first request): %s", e)


def _register_service():
    """Register with service registry."""
    try:
        from shared.discovery import ServiceRegistry
        registry = ServiceRegistry.get_instance()
        port = int(os.getenv("PORT", 5002))
        registry.register(
            service_name="ml-prediction",
            host=os.getenv("HOSTNAME", "ml-prediction"),
            port=port,
            metadata={"version": SERVICE_VERSION, "health_url": "/health"},
        )
        registry.start_heartbeat_loop("ml-prediction")
    except Exception as e:
        logger.warning("Service registration failed: %s", e)


def _subscribe_to_events():
    """Subscribe to weather data events for automatic predictions."""
    try:
        from shared.messaging import EventBus
        from app.services.predictor import FloodPredictor

        bus = EventBus()

        def on_weather_collected(event_data):
            """Auto-predict when new weather data arrives."""
            logger.info("Weather data event received — triggering prediction")
            try:
                predictor = FloodPredictor.get_instance()
                result = predictor.predict_from_latest()
                bus.publish("prediction.completed", result)
            except Exception as e:
                logger.error("Auto-prediction failed: %s", e)

        bus.subscribe("weather.data.collected", on_weather_collected)
        bus.start_listening()
        logger.info("Subscribed to weather.data.collected events")
    except Exception as e:
        logger.warning("Event subscription failed: %s", e)
