"""Database engine, session, and model registration.

Changes vs. the original module-level approach:

* **C1** — SSL / driver logic moved to :mod:`app.utils.db_connection`.
* **C2** — Engine is created lazily via :func:`get_engine` (no side-effects
  at import time).
* **C3** — ``pool_metrics`` is guarded by :data:`_metrics_lock`.
"""

import logging
import os
import threading
import time
from contextlib import contextmanager
from typing import Any, Dict

from app.utils.db_connection import get_pg_driver, prepare_db_url
from app.utils.secrets import get_secret
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker
from sqlalchemy.pool import QueuePool, StaticPool

logger = logging.getLogger(__name__)

# ── Thread-safe pool metrics (C3) ─────────────────────────────────────────
_metrics_lock = threading.Lock()
pool_metrics: Dict[str, Any] = {
    "checkouts": 0,
    "checkins": 0,
    "invalidated": 0,
    "last_checkout_time": None,
    "connection_errors": 0,
    "pool_exhausted_count": 0,
    "avg_checkout_time_ms": 0.0,
    "total_checkout_time_ms": 0.0,
}


def _update_metric(key: str, value: Any) -> None:
    """Atomically update a single metric."""
    with _metrics_lock:
        pool_metrics[key] = value


def _increment_metric(key: str, amount: float = 1) -> None:
    """Atomically increment a numeric metric."""
    with _metrics_lock:
        pool_metrics[key] = pool_metrics.get(key, 0) + amount


# ── Declarative base ──────────────────────────────────────────────────────
Base = declarative_base()

# ── Lazy engine singleton (C2) ────────────────────────────────────────────
_engine: Engine | None = None
_engine_lock = threading.Lock()

# Pool configuration read from environment (evaluated once)
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "20"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "10"))
DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "1800"))
DB_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))
DB_POOL_PRE_PING = os.getenv("DB_POOL_PRE_PING", "True").lower() == "true"
DB_ECHO_POOL = os.getenv("DB_ECHO_POOL", "False").lower() == "true"


def _resolve_db_url() -> str:
    """Return the database URL, raising in prod when unset."""
    url = get_secret("DATABASE_URL")
    if url:
        return url

    app_env = os.getenv("APP_ENV", "development").lower()
    if app_env in ("production", "prod", "staging", "stage"):
        raise ValueError(
            f"DATABASE_URL must be set for {app_env}! "
            "Configure a Supabase PostgreSQL connection string."
        )
    logger.warning("DATABASE_URL not set — using SQLite for development only")
    return "sqlite:///data/floodingnaque.db"


def _attach_pool_events(eng: Engine) -> None:
    """Register connection-pool monitoring events."""

    @event.listens_for(eng, "checkout")
    def receive_checkout(dbapi_conn: Any, connection_record: Any, connection_proxy: Any) -> None:
        _increment_metric("checkouts")
        with _metrics_lock:
            pool_metrics["last_checkout_time"] = time.time()
        connection_record.info["checkout_time"] = time.time()
        logger.debug("Connection checked out from pool (total: %s)", pool_metrics["checkouts"])

    @event.listens_for(eng, "checkin")
    def receive_checkin(dbapi_conn: Any, connection_record: Any) -> None:
        _increment_metric("checkins")
        checkout_time = connection_record.info.get("checkout_time")
        if checkout_time:
            duration_ms = (time.time() - checkout_time) * 1000
            with _metrics_lock:
                pool_metrics["total_checkout_time_ms"] += duration_ms
                total = pool_metrics["checkins"]
                if total > 0:
                    pool_metrics["avg_checkout_time_ms"] = pool_metrics["total_checkout_time_ms"] / total
        logger.debug("Connection checked in to pool (total: %s)", pool_metrics["checkins"])

    @event.listens_for(eng, "invalidate")
    def receive_invalidate(dbapi_conn: Any, connection_record: Any, exception: Any) -> None:
        _increment_metric("invalidated")
        if exception:
            _increment_metric("connection_errors")
            logger.warning("Connection invalidated due to: %s", exception)
        else:
            logger.debug("Connection invalidated (total: %s)", pool_metrics["invalidated"])

    @event.listens_for(eng, "connect")
    def receive_connect(dbapi_conn: Any, connection_record: Any) -> None:
        logger.info("New database connection established")

    @event.listens_for(eng, "close")
    def receive_close(dbapi_conn: Any, connection_record: Any) -> None:
        logger.debug("Database connection closed")

    @event.listens_for(eng, "detach")
    def receive_detach(dbapi_conn: Any, connection_record: Any) -> None:
        logger.debug("Connection detached from pool")


def get_engine() -> Engine:
    """Return the lazily-created SQLAlchemy engine (thread-safe singleton)."""
    global _engine
    if _engine is not None:
        return _engine

    with _engine_lock:
        # Double-checked locking
        if _engine is not None:
            return _engine

        raw_url = _resolve_db_url()
        db_url, connect_args = prepare_db_url(raw_url)

        pg_driver = get_pg_driver()
        logger.info("Using PostgreSQL driver: %s", pg_driver)

        if db_url.startswith("sqlite"):
            eng = create_engine(
                db_url,
                echo=False,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
                pool_pre_ping=True,
            )
        else:
            is_supabase = "supabase" in db_url.lower()
            if is_supabase and DB_POOL_SIZE == 20:
                pool_size, max_overflow, pool_recycle = 3, 5, 600
                logger.info("Using optimized pool settings for Supabase (override with DB_POOL_SIZE)")
            else:
                pool_size, max_overflow, pool_recycle = DB_POOL_SIZE, DB_MAX_OVERFLOW, DB_POOL_RECYCLE

            eng = create_engine(
                db_url,
                echo=DB_ECHO_POOL,
                pool_size=pool_size,
                max_overflow=max_overflow,
                pool_recycle=pool_recycle,
                pool_timeout=DB_POOL_TIMEOUT,
                pool_pre_ping=DB_POOL_PRE_PING,
                poolclass=QueuePool,
                pool_use_lifo=True,
                pool_reset_on_return="rollback",
                connect_args=connect_args if connect_args else {},
            )
            logger.info(
                "Database pool configured: size=%s, overflow=%s, "
                "recycle=%ss, timeout=%ss, pre_ping=%s",
                pool_size, max_overflow, pool_recycle, DB_POOL_TIMEOUT, DB_POOL_PRE_PING,
            )
            _attach_pool_events(eng)

        _engine = eng
        return _engine


# ── Backward-compatible ``engine`` accessor ───────────────────────────────
# Many modules do ``from app.models.db import engine``.  We keep that
# working by making ``engine`` a module-level attribute resolved lazily.

class _EngineProxy:
    """Thin descriptor so ``engine`` can be accessed at module level."""

    def __getattr__(self, name: str) -> Any:
        return getattr(get_engine(), name)

    def __bool__(self) -> bool:
        return _engine is not None

    # Allow ``engine.dispose()`` etc. to work transparently
    def dispose(self, **kw: Any) -> None:
        if _engine is not None:
            _engine.dispose(**kw)


engine = _EngineProxy()  # type: ignore[assignment]


def get_pool_status() -> Dict[str, Any]:
    """Return current connection pool status and metrics."""
    eng = get_engine()
    raw_url = _resolve_db_url()

    if raw_url.startswith("sqlite"):
        return {"status": "sqlite_static_pool", "metrics": None}

    pool = eng.pool

    total_capacity = pool.size() + pool.overflow()
    active = pool.checkedout()
    utilization = (active / max(total_capacity, 1)) * 100 if total_capacity > 0 else 0

    if utilization >= 90:
        health = "critical"
    elif utilization >= 75:
        health = "warning"
    else:
        health = "healthy"

    with _metrics_lock:
        snapshot = dict(pool_metrics)

    return {
        "pool_size": pool.size(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "checked_in": pool.checkedin(),
        "utilization_percent": round(utilization, 2),
        "health_status": health,
        "metrics": {
            **snapshot,
            "avg_checkout_time_ms": round(snapshot.get("avg_checkout_time_ms", 0), 2),
        },
        "config": {
            "pool_size": DB_POOL_SIZE,
            "max_overflow": DB_MAX_OVERFLOW,
            "pool_recycle_seconds": DB_POOL_RECYCLE,
            "pool_timeout": DB_POOL_TIMEOUT,
            "pre_ping_enabled": DB_POOL_PRE_PING,
        },
    }


# ── Session factory (also lazy) ──────────────────────────────────────────
_Session: scoped_session | None = None
_session_lock = threading.Lock()


def _get_scoped_session() -> scoped_session:
    """Return the lazily-created scoped session."""
    global _Session
    if _Session is not None:
        return _Session
    with _session_lock:
        if _Session is not None:
            return _Session
        _Session = scoped_session(sessionmaker(bind=get_engine()))
        return _Session


# Backward-compatible alias
db_session = property(lambda self: _get_scoped_session())  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Import model classes so they are registered with Base.metadata.
# ---------------------------------------------------------------------------
from app.models.weather import WeatherData  # noqa: E402, F401
from app.models.prediction import Prediction  # noqa: E402, F401
from app.models.alert import AlertHistory  # noqa: E402, F401
from app.models.model_registry import ModelRegistry  # noqa: E402, F401
from app.models.cache import SatelliteWeatherCache, TideDataCache  # noqa: E402, F401
from app.models.api_request import APIRequest, EarthEngineRequest  # noqa: E402, F401
from app.models.user import User  # noqa: E402, F401
from app.models.webhook import Webhook  # noqa: E402, F401


def init_db() -> bool:
    """Verify database connectivity and set up runtime hooks.

    Table creation is handled exclusively by Alembic migrations.
    This function validates the connection and initialises optional
    runtime helpers (e.g. slow-query logging).
    """
    try:
        engine = get_engine()

        # Verify connectivity — fail fast at startup
        from sqlalchemy import text

        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database engine initialised (tables managed by Alembic)")

        try:
            from app.utils.query_optimizer import setup_slow_query_logging

            setup_slow_query_logging(engine)
            logger.info("Slow query logging initialized")
        except ImportError:
            logger.debug("Query optimizer not available — slow query logging disabled")
        except Exception as e:
            logger.warning("Failed to initialize slow query logging: %s", e)

        return True
    except Exception as e:
        logger.error("Error initializing database: %s", e)
        raise


@contextmanager
def get_db_session():
    """Context manager for database sessions."""
    scoped = _get_scoped_session()
    session = scoped()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        scoped.remove()
