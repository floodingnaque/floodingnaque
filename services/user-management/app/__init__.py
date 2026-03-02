"""
User Management Service - Flask Application Factory.
"""

import logging
import os

from flask import Flask
from flask_cors import CORS

logger = logging.getLogger(__name__)

SERVICE_NAME = "user-management"
SERVICE_VERSION = "1.0.0"


def create_app(config_override: dict = None) -> Flask:
    """Create and configure the User Management Flask application."""
    from shared.config import load_env
    from shared.errors import register_error_handlers
    from shared.health import create_health_blueprint
    from shared.tracing import setup_tracing_middleware

    load_env()

    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-user-secret")
    app.config["JSON_SORT_KEYS"] = False

    if config_override:
        app.config.update(config_override)

    CORS(app, origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","))
    setup_tracing_middleware(app, SERVICE_NAME)
    register_error_handlers(app)

    # Health checks
    health_bp = create_health_blueprint(SERVICE_NAME, SERVICE_VERSION)
    app.register_blueprint(health_bp)

    def check_db():
        try:
            from shared.database import get_engine
            from sqlalchemy import text
            with get_engine().connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    health_bp.register_dependency_check("database", check_db)

    # Routes
    from app.routes.auth import auth_bp
    from app.routes.users import users_bp
    from app.routes.admin import admin_bp

    app.register_blueprint(auth_bp, url_prefix="/api/v1/auth")
    app.register_blueprint(users_bp, url_prefix="/api/v1/users")
    app.register_blueprint(admin_bp, url_prefix="/api/v1/admin/users")

    # Initialize database tables
    with app.app_context():
        try:
            from shared.database import init_db
            init_db()
        except Exception as e:
            logger.warning("DB init skipped: %s", e)
        _register_service()

    logger.info("%s v%s initialized", SERVICE_NAME, SERVICE_VERSION)
    return app


def _register_service():
    try:
        from shared.discovery import ServiceRegistry
        registry = ServiceRegistry.get_instance()
        port = int(os.getenv("PORT", 5004))
        registry.register(
            service_name="user-management",
            host=os.getenv("HOSTNAME", "user-management"),
            port=port,
            metadata={"version": SERVICE_VERSION, "health_url": "/health"},
        )
        registry.start_heartbeat_loop("user-management")
    except Exception as e:
        logger.warning("Service registration failed: %s", e)
