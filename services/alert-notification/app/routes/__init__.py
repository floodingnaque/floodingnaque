"""Routes package for Alert Notification Service."""

from app.routes.alerts import alerts_bp
from app.routes.notifications import notifications_bp
from app.routes.sse import sse_bp
from app.routes.webhooks import webhooks_bp

__all__ = ["alerts_bp", "sse_bp", "webhooks_bp", "notifications_bp"]
