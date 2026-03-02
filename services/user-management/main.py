#!/usr/bin/env python3
"""
User Management Service - Main Entry Point

Responsible for:
- User registration, login, logout
- JWT token issuance and refresh
- Password management (reset, change)
- Role-based access control (RBAC)
- User profile management
- Admin user operations

Port: 5004
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
    port = int(os.getenv("PORT", 5004))
    host = os.getenv("HOST", "0.0.0.0")

    logger.info("User Management Service starting on %s:%s", host, port)

    if os.name == "nt":
        from waitress import serve
        serve(app, host=host, port=port)
    else:
        app.run(host=host, port=port, debug=os.getenv("FLASK_DEBUG", "false").lower() == "true")


if __name__ == "__main__":
    main()
