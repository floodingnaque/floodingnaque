"""
Alert Notification Service — Flask Application Factory.
"""

import logging
import os

from flask import Flask
from flask_cors import CORS

logger = logging.getLogger(__name__)

SERVICE_NAME = "alert-notification"
SERVICE_VERSION = "1.0.0"


def create_app(config_override: dict = None) -> Flask:
    """Create and configure the Alert Notification Flask application."""
    from shared.config import load_env
    from shared.errors import register_error_handlers
    from shared.health import create_health_blueprint
    from shared.tracing import setup_tracing_middleware

    load_env()

    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-alert-secret")
    app.config["JSON_SORT_KEYS"] = False

    if config_override:
        app.config.update(config_override)

    CORS(app, origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","))
    setup_tracing_middleware(app, SERVICE_NAME)
    register_error_handlers(app)

    # Health checks
    health_bp = create_health_blueprint(SERVICE_NAME, SERVICE_VERSION)
    app.register_blueprint(health_bp)

    def check_redis():
        try:
            import redis
            client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
            return client.ping()
        except Exception:
            return False

    health_bp.register_dependency_check("redis", check_redis)

    # Routes
    from app.routes.alerts import alerts_bp
    from app.routes.sse import sse_bp
    from app.routes.webhooks import webhooks_bp
    from app.routes.notifications import notifications_bp

    app.register_blueprint(alerts_bp, url_prefix="/api/v1/alerts")
    app.register_blueprint(sse_bp, url_prefix="/api/v1/sse")
    app.register_blueprint(webhooks_bp, url_prefix="/api/v1/webhooks")
    app.register_blueprint(notifications_bp, url_prefix="/api/v1/notifications")

    # Subscribe to prediction events
    with app.app_context():
        _register_service()
        _subscribe_to_events(app)

    logger.info("%s v%s initialized", SERVICE_NAME, SERVICE_VERSION)
    return app


def _register_service():
    """Register with service registry."""
    try:
        from shared.discovery import ServiceRegistry
        registry = ServiceRegistry.get_instance()
        port = int(os.getenv("PORT", 5003))
        registry.register(
            service_name="alert-notification",
            host=os.getenv("HOSTNAME", "alert-notification"),
            port=port,
            metadata={"version": SERVICE_VERSION, "health_url": "/health"},
        )
        registry.start_heartbeat_loop("alert-notification")
    except Exception as e:
        logger.warning("Service registration failed: %s", e)


def _subscribe_to_events(app):
    """Subscribe to prediction events to auto-generate alerts."""
    try:
        from shared.messaging import EventBus
        from app.services.alert_manager import AlertManager

        bus = EventBus()

        def on_prediction_completed(event_data):
            """Auto-create alert when prediction indicates high risk."""
            with app.app_context():
                try:
                    prediction = event_data.get("data", {}).get("prediction", {})
                    risk_level = prediction.get("risk_level", "low")

                    if risk_level in ("high", "critical"):
                        manager = AlertManager.get_instance()
                        alert = manager.create_alert_from_prediction(prediction)
                        logger.info("Alert created from prediction: %s", alert.get("id"))

                        # Publish alert event
                        bus.publish("alert.triggered", alert)
                except Exception as e:
                    logger.error("Auto-alert creation failed: %s", e)

        bus.subscribe("prediction.completed", on_prediction_completed)
        bus.start_listening()
        logger.info("Subscribed to prediction.completed events")
    except Exception as e:
        logger.warning("Event subscription failed: %s", e)
