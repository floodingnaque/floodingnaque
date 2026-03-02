#!/usr/bin/env python3
"""
Weather Data Collector Service - Main Entry Point

Responsible for:
- Collecting weather data from multiple external APIs (Meteostat, Google Weather,
  PAGASA, WorldTides, Manila Bay Tides)
- Scheduling periodic data collection jobs
- Storing raw and processed weather observations
- Publishing 'weather.data.collected' events for downstream services

Port: 5001
"""

import logging
import os
import sys

# Add parent directory to path for shared package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import create_app

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    app = create_app()
    port = int(os.getenv("PORT", 5001))
    host = os.getenv("HOST", "0.0.0.0")

    logger.info("Weather Data Collector Service starting on %s:%s", host, port)

    if os.name == "nt":
        # Windows - use waitress
        from waitress import serve
        serve(app, host=host, port=port)
    else:
        app.run(host=host, port=port, debug=os.getenv("FLASK_DEBUG", "false").lower() == "true")


if __name__ == "__main__":
    main()
