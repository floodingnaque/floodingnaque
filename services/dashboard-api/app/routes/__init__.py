"""Dashboard API Service - Route Registration."""

from flask import Flask


def register_blueprints(app: Flask) -> None:
    """Register all dashboard-api route blueprints."""
    from app.routes.dashboard import dashboard_bp
    from app.routes.predictions import predictions_bp
    from app.routes.aggregation import aggregation_bp
    from app.routes.export import export_bp
    from app.routes.performance import performance_bp
    from app.routes.gis import gis_bp

    prefix = "/api/v1/dashboard"

    app.register_blueprint(dashboard_bp, url_prefix=prefix)
    app.register_blueprint(predictions_bp, url_prefix=f"{prefix}/predictions")
    app.register_blueprint(aggregation_bp, url_prefix=f"{prefix}/aggregation")
    app.register_blueprint(export_bp, url_prefix=f"{prefix}/export")
    app.register_blueprint(performance_bp, url_prefix=f"{prefix}/performance")
    app.register_blueprint(gis_bp, url_prefix=f"{prefix}/gis")
