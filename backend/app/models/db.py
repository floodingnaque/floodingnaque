import logging
import os
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone

from app.utils.secrets import get_secret
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker
from sqlalchemy.pool import QueuePool, StaticPool

logger = logging.getLogger(__name__)

# Pool connection metrics
pool_metrics = {
    "checkouts": 0,
    "checkins": 0,
    "invalidated": 0,
    "last_checkout_time": None,
    "connection_errors": 0,
    "pool_exhausted_count": 0,
    "avg_checkout_time_ms": 0.0,
    "total_checkout_time_ms": 0.0,
}


# SQLAlchemy 1.4/2.0 compatible declarative base
Base = declarative_base()

# Enhanced database configuration with Supabase support
# Note: The actual DATABASE_URL is validated in app.core.config._get_database_url()
# Development allows SQLite fallback; Production/Staging require Supabase PostgreSQL
DB_URL = get_secret("DATABASE_URL")

if not DB_URL:
    # Only for initial module load before config is loaded - will be overridden
    app_env = os.getenv("APP_ENV", "development").lower()
    if app_env in ("production", "prod", "staging", "stage"):
        raise ValueError(
            f"DATABASE_URL must be set for {app_env}! " "Configure a Supabase PostgreSQL connection string."
        )
    DB_URL = "sqlite:///data/floodingnaque.db"
    logger.warning("DATABASE_URL not set - using SQLite for development only")


# Supabase-specific: Handle connection string format
# Auto-select the best PostgreSQL driver based on platform:
# - Linux/Docker: Use psycopg2 (faster C-based driver)
# - Windows: Use pg8000 (pure Python, no compilation needed)
def _get_pg_driver():
    """Determine the best PostgreSQL driver for the current platform."""
    if sys.platform == "win32":
        return "pg8000"
    # On Linux/Docker, prefer psycopg2 if available
    try:
        import psycopg2  # noqa: F401

        return "psycopg2"
    except ImportError:
        return "pg8000"


pg_driver = _get_pg_driver()
logger.info(f"Using PostgreSQL driver: {pg_driver}")

# Handle SSL mode for pg8000 (doesn't accept sslmode in URL like psycopg2)
# Extract sslmode from URL and configure via connect_args for pg8000
# Also support environment-based SSL configuration via DB_SSL_MODE and DB_SSL_CA_CERT
ssl_context = None

# Get SSL configuration from environment
db_ssl_mode = os.getenv("DB_SSL_MODE", "").lower()
db_ssl_ca_cert = os.getenv("DB_SSL_CA_CERT", "")

# Determine app environment for default SSL mode
app_env = os.getenv("APP_ENV", "development").lower()
if not db_ssl_mode:
    # Default: verify-full for production/staging, require for development
    if app_env in ("production", "prod", "staging", "stage"):
        db_ssl_mode = "verify-full"
    else:
        db_ssl_mode = "require"

if pg_driver == "pg8000":
    import ssl

    # Remove sslmode from URL for pg8000 if present
    if "sslmode=" in DB_URL:
        import re

        sslmode_match = re.search(r"[?&]sslmode=([^&]*)", DB_URL)
        if sslmode_match:
            url_sslmode = sslmode_match.group(1).lower()
            # Use URL sslmode if DB_SSL_MODE not explicitly set
            if not os.getenv("DB_SSL_MODE"):
                db_ssl_mode = url_sslmode
            # Remove sslmode parameter from URL
            DB_URL = re.sub(r"[?&]sslmode=[^&]*", "", DB_URL)
            # Clean up URL if we left a dangling ? or &
            DB_URL = DB_URL.replace("?&", "?").rstrip("?")

    if db_ssl_mode in ("require", "verify-ca", "verify-full"):
        ssl_context = ssl.create_default_context()

        if db_ssl_mode == "require":
            # Encrypted connection, no certificate verification
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            logger.info("SSL mode 'require': Encrypted connection without certificate verification")

        elif db_ssl_mode in ("verify-ca", "verify-full"):
            # Full certificate verification
            ssl_context.verify_mode = ssl.CERT_REQUIRED

            if db_ssl_mode == "verify-full":
                ssl_context.check_hostname = True
                logger.info("SSL mode 'verify-full': Full certificate and hostname verification")
            else:
                ssl_context.check_hostname = False
                logger.info("SSL mode 'verify-ca': Certificate verification without hostname check")

            # Load CA certificate
            if db_ssl_ca_cert:
                import os.path

                if os.path.isfile(db_ssl_ca_cert):
                    ssl_context.load_verify_locations(db_ssl_ca_cert)
                    logger.info(f"Loaded CA certificate from: {db_ssl_ca_cert}")
                else:
                    error_msg = (
                        f"CRITICAL: SSL certificate file not found: {db_ssl_ca_cert}. "
                        f"SSL mode '{db_ssl_mode}' requires a valid CA certificate. "
                        "Set DB_SSL_CA_CERT to the path of your CA certificate file."
                    )
                    logger.error(error_msg)
                    # Fail fast in production/staging
                    if app_env in ("production", "prod", "staging", "stage"):
                        raise ValueError(error_msg)
                    else:
                        # Fall back to require mode in development
                        logger.warning("Falling back to SSL mode 'require' for development")
                        ssl_context.check_hostname = False
                        ssl_context.verify_mode = ssl.CERT_NONE
                        db_ssl_mode = "require"
            else:
                error_msg = (
                    f"CRITICAL: DB_SSL_CA_CERT not set but SSL mode is '{db_ssl_mode}'. "
                    "Certificate verification modes require DB_SSL_CA_CERT to be set."
                )
                logger.error(error_msg)
                # Fail fast in production/staging
                if app_env in ("production", "prod", "staging", "stage"):
                    raise ValueError(error_msg)
                else:
                    # Fall back to require mode in development
                    logger.warning("Falling back to SSL mode 'require' for development")
                    ssl_context.check_hostname = False
                    ssl_context.verify_mode = ssl.CERT_NONE
                    db_ssl_mode = "require"

        logger.info(f"Configured SSL context for pg8000 (sslmode={db_ssl_mode})")

if DB_URL.startswith("postgres://"):
    DB_URL = DB_URL.replace("postgres://", f"postgresql+{pg_driver}://", 1)
elif DB_URL.startswith("postgresql://") and "+" not in DB_URL.split("://")[0]:
    DB_URL = DB_URL.replace("postgresql://", f"postgresql+{pg_driver}://", 1)

# Connection pool settings for better performance and reliability
# Get pool settings from environment (defaults match config.py)
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "20"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "10"))
DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "1800"))  # 30 minutes for better connection freshness
DB_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))
DB_POOL_PRE_PING = os.getenv("DB_POOL_PRE_PING", "True").lower() == "true"
DB_ECHO_POOL = os.getenv("DB_ECHO_POOL", "False").lower() == "true"

if DB_URL.startswith("sqlite"):
    # SQLite-specific settings
    engine = create_engine(
        DB_URL,
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # SQLite works best with StaticPool
        pool_pre_ping=True,  # Verify connections before using
    )
else:
    # PostgreSQL/Supabase settings
    # Use QueuePool for production with configurable settings
    is_supabase = "supabase" in DB_URL.lower()

    # Respect environment variables, but provide conservative defaults for Supabase free tier
    # Users can override these in .env for paid tiers
    if is_supabase and DB_POOL_SIZE == 20:  # Only use conservative defaults if user hasn't customized
        pool_size = 3  # Slightly higher for better concurrency
        max_overflow = 5  # Allow more overflow connections
        pool_recycle = 600  # 10 minutes for Supabase connections
        logger.info("Using optimized pool settings for Supabase (override with DB_POOL_SIZE in .env)")
    else:
        pool_size = DB_POOL_SIZE
        max_overflow = DB_MAX_OVERFLOW
        pool_recycle = DB_POOL_RECYCLE

    # Build engine with optimized connection pooling
    # Configure connect_args based on driver
    connect_args = {}
    if pg_driver == "pg8000" and ssl_context:
        connect_args["ssl_context"] = ssl_context

    engine = create_engine(
        DB_URL,
        echo=DB_ECHO_POOL,  # Log SQL statements when debugging
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_recycle=pool_recycle,
        pool_timeout=DB_POOL_TIMEOUT,
        pool_pre_ping=DB_POOL_PRE_PING,  # Health check before using connection
        poolclass=QueuePool,
        # Performance-oriented settings
        pool_use_lifo=True,  # LIFO reduces latency for connections
        pool_reset_on_return="rollback",  # Clean state on return
        connect_args=connect_args if connect_args else {},
    )

    logger.info(
        f"Database pool configured: size={pool_size}, overflow={max_overflow}, "
        f"recycle={pool_recycle}s, timeout={DB_POOL_TIMEOUT}s, pre_ping={DB_POOL_PRE_PING}"
    )

# Pool monitoring events for PostgreSQL/Supabase connections
if not DB_URL.startswith("sqlite"):

    @event.listens_for(engine, "checkout")
    def receive_checkout(dbapi_conn, connection_record, connection_proxy):
        """Track when a connection is checked out from the pool."""
        pool_metrics["checkouts"] += 1
        pool_metrics["last_checkout_time"] = time.time()
        connection_record.info["checkout_time"] = time.time()
        logger.debug(f"Connection checked out from pool (total: {pool_metrics['checkouts']})")

    @event.listens_for(engine, "checkin")
    def receive_checkin(dbapi_conn, connection_record):
        """Track when a connection is returned to the pool."""
        pool_metrics["checkins"] += 1
        checkout_time = connection_record.info.get("checkout_time")
        if checkout_time:
            duration_ms = (time.time() - checkout_time) * 1000
            pool_metrics["total_checkout_time_ms"] += duration_ms
            total_checkouts = pool_metrics["checkins"]
            if total_checkouts > 0:
                pool_metrics["avg_checkout_time_ms"] = pool_metrics["total_checkout_time_ms"] / total_checkouts
        logger.debug(f"Connection checked in to pool (total: {pool_metrics['checkins']})")

    @event.listens_for(engine, "invalidate")
    def receive_invalidate(dbapi_conn, connection_record, exception):
        """Track when a connection is invalidated."""
        pool_metrics["invalidated"] += 1
        if exception:
            pool_metrics["connection_errors"] += 1
            logger.warning(f"Connection invalidated due to: {exception}")
        else:
            logger.debug(f"Connection invalidated (total: {pool_metrics['invalidated']})")

    @event.listens_for(engine, "connect")
    def receive_connect(dbapi_conn, connection_record):
        """Log new database connections."""
        logger.info("New database connection established")

    @event.listens_for(engine, "close")
    def receive_close(dbapi_conn, connection_record):
        """Log when a connection is closed."""
        logger.debug("Database connection closed")

    @event.listens_for(engine, "detach")
    def receive_detach(dbapi_conn, connection_record):
        """Log when a connection is detached from pool."""
        logger.debug("Connection detached from pool")


def get_pool_status():
    """Get current connection pool status and metrics."""
    if DB_URL.startswith("sqlite"):
        return {"status": "sqlite_static_pool", "metrics": None}

    pool = engine.pool

    # Calculate pool utilization percentage
    total_capacity = pool.size() + pool.overflow()
    active_connections = pool.checkedout()
    utilization_percent = (active_connections / max(total_capacity, 1)) * 100 if total_capacity > 0 else 0

    # Determine pool health status
    if utilization_percent >= 90:
        health_status = "critical"
    elif utilization_percent >= 75:
        health_status = "warning"
    else:
        health_status = "healthy"

    return {
        "pool_size": pool.size(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "checked_in": pool.checkedin(),
        "utilization_percent": round(utilization_percent, 2),
        "health_status": health_status,
        "metrics": {
            **pool_metrics,
            "avg_checkout_time_ms": round(pool_metrics.get("avg_checkout_time_ms", 0), 2),
        },
        "config": {
            "pool_size": DB_POOL_SIZE,
            "max_overflow": DB_MAX_OVERFLOW,
            "pool_recycle_seconds": DB_POOL_RECYCLE,
            "pool_timeout": DB_POOL_TIMEOUT,
            "pre_ping_enabled": DB_POOL_PRE_PING,
        },
    }


Session = sessionmaker(bind=engine)
# Use scoped_session for thread-safe session management
db_session = scoped_session(Session)


# ---------------------------------------------------------------------------
# Import model classes so they are registered with Base.metadata.
# External code can import models from here for backward compatibility,
# but the canonical location is now the per-model module files.
# ---------------------------------------------------------------------------
from app.models.weather import WeatherData  # noqa: E402, F401
from app.models.prediction import Prediction  # noqa: E402, F401
from app.models.alert import AlertHistory  # noqa: E402, F401
from app.models.model_registry import ModelRegistry  # noqa: E402, F401
from app.models.cache import SatelliteWeatherCache, TideDataCache  # noqa: E402, F401
from app.models.api_request import APIRequest, EarthEngineRequest  # noqa: E402, F401
from app.models.user import User  # noqa: E402, F401
from app.models.webhook import Webhook  # noqa: E402, F401


def init_db():
    """Initialize database tables with enhanced error handling."""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized successfully")

        # Log table creation
        tables = Base.metadata.tables.keys()
        logger.info(f"Created tables: {', '.join(tables)}")

        # Initialize slow query logging
        try:
            from app.utils.query_optimizer import setup_slow_query_logging

            setup_slow_query_logging(engine)
            logger.info("Slow query logging initialized")
        except ImportError:
            logger.debug("Query optimizer not available - slow query logging disabled")
        except Exception as e:
            logger.warning(f"Failed to initialize slow query logging: {e}")

        return True
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise


@contextmanager
def get_db_session():
    """Context manager for database sessions."""
    session = db_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        db_session.remove()  # Remove session from registry for scoped_session
