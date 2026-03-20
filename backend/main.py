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
import threading
from pathlib import Path

# Load .env BEFORE any app imports so module-level code (e.g. security.py)
# can read SECRET_KEY / JWT_SECRET_KEY from the environment.
from dotenv import load_dotenv

_base_dir = Path(__file__).resolve().parent
_app_env = os.getenv("APP_ENV", "development").lower()
_env_map = {
    "development": ".env.development",
    "dev": ".env.development",
    "staging": ".env.staging",
    "stage": ".env.staging",
    "production": ".env.production",
    "prod": ".env.production",
}
_env_file = _base_dir / _env_map.get(_app_env, ".env.development")
if _env_file.exists():
    load_dotenv(_env_file, override=False)
else:
    load_dotenv(_base_dir / ".env", override=False)

from app.api.app import create_app
from app.core.config import is_debug_mode

# Module logger
logger = logging.getLogger(__name__)

# Thread-safe flag for shutdown (prevents double cleanup race condition)
_shutdown_lock = threading.Lock()
_shutdown_in_progress = False


def cleanup_connections():
    """
    Clean up all connections and resources during shutdown.
    This ensures graceful termination of database connections,
    scheduler jobs, and other resources.

    Thread-safe: uses a lock to prevent double-cleanup when a signal
    handler and atexit (or finally block) race each other.
    """
    global _shutdown_in_progress

    with _shutdown_lock:
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
        from app.utils.resilience.cache import get_redis_client

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


# Register signal handlers (guard SIGHUP for Windows compatibility)
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)
if hasattr(signal, "SIGHUP"):
    signal.signal(signal.SIGHUP, signal_handler)

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
    except OSError as e:
        # WinError 10038: socket closed during shutdown — harmless on Windows CTRL+C
        if "WinError" in str(e) or getattr(e, "winerror", None):
            logger.debug(f"Ignoring Windows socket teardown error: {e}")
        else:
            raise
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    finally:
        cleanup_connections()
