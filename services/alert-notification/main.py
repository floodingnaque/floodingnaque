#!/usr/bin/env python3
"""
Alert Notification Service - Main Entry Point

Responsible for:
- Creating and managing flood alerts based on predictions
- Sending notifications via SMS, email, Slack, and web push
- Server-Sent Events (SSE) for real-time dashboard alerts
- Alert history, statistics, and deduplication
- Webhook dispatch for third-party integrations

Port: 5003
"""

import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import create_app

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    app = create_app()
    port = int(os.getenv("PORT", 5003))
    host = os.getenv("HOST", "0.0.0.0")

    logger.info("Alert Notification Service starting on %s:%s", host, port)

    if os.name == "nt":
        from waitress import serve
        serve(app, host=host, port=port)
    else:
        app.run(host=host, port=port, debug=os.getenv("FLASK_DEBUG", "false").lower() == "true")


if __name__ == "__main__":
    main()
