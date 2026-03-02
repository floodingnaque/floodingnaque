"""Routes package for Floodingnaque API.

Contains modular route definitions:
- health: /status, /health, / (root)
- health_k8s: /health/live, /health/ready (Kubernetes probes)
- ingest: /api/v1/ingest
- predict: /api/v1/predict
- data: /api/v1/data, /api/v1/data/meteostat/*
- models: /api/v1/models
- batch: /api/v1/batch/predict
- export: /api/v1/export/weather, /api/v1/export/predictions
- webhooks: /api/v1/webhooks/register, /api/v1/webhooks/list
- celery: /api/v1/tasks/*
- rate_limits: /api/v1/rate-limits/status, /api/v1/rate-limits/tiers
- tides: /api/v1/tides/current, /api/v1/tides/extremes, /api/v1/tides/prediction
- graphql: /api/v1/graphql/*
- security_txt: /.well-known/security.txt, /security.txt
- csp_report: /csp-report
- performance: /api/v1/performance/*
- users: /api/v1/auth/register, /api/v1/auth/login, /api/v1/auth/logout, /api/v1/auth/refresh, /api/v1/auth/me
- alerts: /api/v1/alerts, /api/v1/alerts/history, /api/v1/alerts/recent, /api/v1/alerts/stats
- dashboard: /api/v1/dashboard/summary, /api/v1/dashboard/statistics, /api/v1/dashboard/activity
- predictions: /api/v1/predictions, /api/v1/predictions/stats, /api/v1/predictions/recent
- sse: /api/v1/sse/alerts (Server-Sent Events for real-time flood alerts)
- upload: /api/v1/upload (File upload endpoints)
- config: /api/v1/config/* (Configuration management and hot-reload)
"""

from app.api.routes.aggregation import aggregation_bp
from app.api.routes.alerts import alerts_bp
from app.api.routes.batch import batch_bp
from app.api.routes.celery import celery_bp
from app.api.routes.config import config_bp
from app.api.routes.csp_report import csp_report_bp
from app.api.routes.dashboard import dashboard_bp
from app.api.routes.data import data_bp
from app.api.routes.export import export_bp
from app.api.routes.graphql import graphql_bp
from app.api.routes.health import health_bp
from app.api.routes.health_k8s import health_k8s_bp
from app.api.routes.ingest import ingest_bp
from app.api.routes.models import models_bp
from app.api.routes.performance import performance_bp
from app.api.routes.predict import predict_bp
from app.api.routes.predictions import predictions_bp
from app.api.routes.rate_limits import rate_limits_bp
from app.api.routes.security_txt import security_txt_bp
from app.api.routes.sse import sse_bp
from app.api.routes.tides import tides_bp
from app.api.routes.upload import upload_bp
from app.api.routes.users import users_bp
from app.api.routes.webhooks import webhooks_bp

__all__ = [
    # Core routes
    "aggregation_bp",
    "health_bp",
    "health_k8s_bp",
    "ingest_bp",
    "predict_bp",
    "data_bp",
    "models_bp",
    # Extended routes
    "batch_bp",
    "config_bp",
    "export_bp",
    "webhooks_bp",
    "celery_bp",
    "rate_limits_bp",
    "tides_bp",
    "graphql_bp",
    "security_txt_bp",
    "csp_report_bp",
    "performance_bp",
    "users_bp",
    "alerts_bp",
    "dashboard_bp",
    "predictions_bp",
    "sse_bp",
    "upload_bp",
]
