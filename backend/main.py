#!/usr/bin/env python3
"""
Floodingnaque Backend - Main Entry Point
A commercial-grade flood prediction API for Parañaque City.
"""

import atexit
import logging
import os
import signal
import sys

from app.api.app import create_app
from app.core.config import is_debug_mode

# Module logger
logger = logging.getLogger(__name__)

# Global flag for shutdown
_shutdown_in_progress = False


def cleanup_connections():
    """
    Clean up all connections and resources during shutdown.
    This ensures graceful termination of database connections,
    scheduler jobs, and other resources.
    """
    global _shutdown_in_progress

    if _shutdown_in_progress:
        return

    _shutdown_in_progress = True
    logger.info("Starting graceful shutdown...")

    try:
        # Stop the scheduler if running
        from app.services import scheduler as scheduler_module

        if hasattr(scheduler_module, "scheduler") and hasattr(scheduler_module.scheduler, "running"):
            if scheduler_module.scheduler.running:
                scheduler_module.scheduler.shutdown(wait=False)
                logger.info("Scheduler shutdown complete")
    except Exception as e:
        logger.warning(f"Error stopping scheduler: {e}")  # OK: has curly braces

    try:
        # Dispose database engine connections
        from app.models.db import engine

        if engine:
            engine.dispose()
            logger.info("Database connections closed")
    except Exception as e:
        logger.warning(f"Error closing database connections: {e}")  # OK: has curly braces

    try:
        # Close Redis connections if available
        from app.utils.cache import get_redis_client

        redis_client = get_redis_client()
        if redis_client:
            redis_client.close()
            logger.info("Redis connection closed")
    except Exception as e:
        logger.warning(f"Error closing Redis connection: {e}")  # OK: has curly braces

    logger.info("Graceful shutdown complete")


def signal_handler(signum, frame):
    """
    Handle SIGTERM and SIGINT for graceful shutdown.

    Args:
        signum: Signal number
        frame: Current stack frame
    """
    signal_name = signal.Signals(signum).name
    logger.info(f"Received {signal_name} signal, initiating graceful shutdown...")  # OK: has curly braces
    cleanup_connections()
    sys.exit(0)


# Register signal handlers
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

# Register cleanup on normal exit
atexit.register(cleanup_connections)

# Create app instance for Gunicorn
# This ensures the app is properly initialized when imported by Gunicorn
application = create_app()

if __name__ == "__main__":
    # Get configuration from environment
    port = int(os.getenv("PORT", 5000))
    host = os.getenv("HOST", "0.0.0.0")  # nosec B104
    debug = is_debug_mode()  # Use centralized check

    # Only print once (not on reloader subprocess)
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        print(f"Starting Floodingnaque API on {host}:{port} (debug={debug})")  # OK: has curly braces

    try:
        application.run(host=host, port=port, debug=debug)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    finally:
        cleanup_connections()
