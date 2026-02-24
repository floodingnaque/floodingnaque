"""
Database Optimization Module for Floodingnaque

Provides:
- Read replica routing for dashboard queries
- Connection pool optimization
- Time-series partitioning helpers
- Database health monitoring

Usage:
    from app.utils.db_optimization import get_read_engine, get_write_engine, DatabaseRouter
"""

import logging
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable, Dict, Optional

from app.utils.secrets import get_secret

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.pool import NullPool, QueuePool

logger = logging.getLogger(__name__)


# =====================================================
# Configuration
# =====================================================


class DatabaseConfig:
    """Database configuration management."""

    def __init__(self):
        # Primary (write) database
        self.primary_url = get_secret("DATABASE_URL", default="")

        # Read replica (defaults to primary if not set)
        self.replica_url = os.getenv("DATABASE_REPLICA_URL", self.primary_url)

        # PgBouncer configuration
        self.pgbouncer_url = os.getenv("PGBOUNCER_URL", "")
        self.use_pgbouncer = os.getenv("USE_PGBOUNCER", "false").lower() == "true"

        # Pool settings
        self.pool_size = int(os.getenv("DB_POOL_SIZE", "20"))
        self.max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "10"))
        self.pool_recycle = int(os.getenv("DB_POOL_RECYCLE", "1800"))
        self.pool_timeout = int(os.getenv("DB_POOL_TIMEOUT", "30"))
        self.pool_pre_ping = os.getenv("DB_POOL_PRE_PING", "true").lower() == "true"

        # Read replica settings
        self.read_replica_enabled = os.getenv("READ_REPLICA_ENABLED", "false").lower() == "true"
        self.read_replica_lag_threshold_ms = int(os.getenv("READ_REPLICA_LAG_THRESHOLD_MS", "100"))

        # SSL settings
        self.ssl_mode = os.getenv("DB_SSL_MODE", "require")
        self.ssl_ca_cert = os.getenv("DB_SSL_CA_CERT", "")


config = DatabaseConfig()


# =====================================================
# PostgreSQL Driver Selection
# =====================================================


def _get_pg_driver() -> str:
    """Determine the best PostgreSQL driver for the current platform."""
    import sys

    if sys.platform == "win32":
        return "pg8000"
    try:
        import psycopg2

        return "psycopg2"
    except ImportError:
        return "pg8000"


def _prepare_database_url(url: str) -> str:
    """Prepare database URL with the appropriate driver."""
    if not url or url.startswith("sqlite"):
        return url

    pg_driver = _get_pg_driver()

    if url.startswith("postgres://"):
        url = url.replace("postgres://", f"postgresql+{pg_driver}://", 1)
    elif url.startswith("postgresql://") and "+" not in url.split("://")[0]:
        url = url.replace("postgresql://", f"postgresql+{pg_driver}://", 1)

    return url


# =====================================================
# Engine Factory
# =====================================================

_engines: Dict[str, Engine] = {}


def _create_engine_with_pooling(
    url: str,
    pool_size: int = 20,
    max_overflow: int = 10,
    pool_recycle: int = 1800,
    pool_timeout: int = 30,
    pool_pre_ping: bool = True,
    is_replica: bool = False,
    use_null_pool: bool = False,
) -> Engine:
    """Create SQLAlchemy engine with optimized pooling settings."""

    prepared_url = _prepare_database_url(url)

    if prepared_url.startswith("sqlite"):
        from sqlalchemy.pool import StaticPool

        return create_engine(
            prepared_url,
            echo=False,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            pool_pre_ping=True,
        )

    # Build connect args for SSL
    connect_args = {}
    pg_driver = _get_pg_driver()

    if pg_driver == "pg8000" and config.ssl_mode in ("require", "verify-ca", "verify-full"):
        import ssl

        ssl_context = ssl.create_default_context()

        if config.ssl_mode == "require":
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
        else:
            ssl_context.verify_mode = ssl.CERT_REQUIRED
            ssl_context.check_hostname = config.ssl_mode == "verify-full"
            if config.ssl_ca_cert and os.path.isfile(config.ssl_ca_cert):
                ssl_context.load_verify_locations(config.ssl_ca_cert)

        connect_args["ssl_context"] = ssl_context

    # Pool class selection
    poolclass = NullPool if use_null_pool else QueuePool

    engine = create_engine(
        prepared_url,
        echo=False,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_recycle=pool_recycle,
        pool_timeout=pool_timeout,
        pool_pre_ping=pool_pre_ping,
        poolclass=poolclass,
        pool_use_lifo=True,
        pool_reset_on_return="rollback",
        connect_args=connect_args if connect_args else {},
    )

    role = "replica" if is_replica else "primary"
    logger.info(
        f"Database engine ({role}) created: pool_size={pool_size}, " f"overflow={max_overflow}, recycle={pool_recycle}s"
    )

    return engine


def get_write_engine() -> Engine:
    """Get the primary (write) database engine."""
    if "write" not in _engines:
        url = config.pgbouncer_url if config.use_pgbouncer else config.primary_url

        # When using PgBouncer, use NullPool (PgBouncer handles pooling)
        use_null_pool = config.use_pgbouncer

        _engines["write"] = _create_engine_with_pooling(
            url=url,
            pool_size=config.pool_size,
            max_overflow=config.max_overflow,
            pool_recycle=config.pool_recycle,
            pool_timeout=config.pool_timeout,
            pool_pre_ping=config.pool_pre_ping,
            is_replica=False,
            use_null_pool=use_null_pool,
        )

    return _engines["write"]


def get_read_engine() -> Engine:
    """Get the read replica engine (or primary if replica not configured)."""
    if "read" not in _engines:
        if config.read_replica_enabled and config.replica_url:
            url = config.replica_url
            is_replica = True
        else:
            # Fallback to primary
            url = config.pgbouncer_url if config.use_pgbouncer else config.primary_url
            is_replica = False

        use_null_pool = config.use_pgbouncer

        _engines["read"] = _create_engine_with_pooling(
            url=url,
            pool_size=config.pool_size,
            max_overflow=config.max_overflow,
            pool_recycle=config.pool_recycle,
            pool_timeout=config.pool_timeout,
            pool_pre_ping=config.pool_pre_ping,
            is_replica=is_replica,
            use_null_pool=use_null_pool,
        )

    return _engines["read"]


# =====================================================
# Database Router
# =====================================================


class DatabaseRouter:
    """
    Routes database queries to primary or replica based on operation type.

    Usage:
        router = DatabaseRouter()

        # For write operations
        with router.write_session() as session:
            session.add(new_record)
            session.commit()

        # For read-only dashboard queries
        with router.read_session() as session:
            results = session.query(WeatherData).all()
    """

    def __init__(self):
        self._write_session_factory = None
        self._read_session_factory = None
        self._replica_lag_ms = 0
        self._last_lag_check = None

    @property
    def write_session_factory(self):
        """Lazy-load write session factory."""
        if self._write_session_factory is None:
            engine = get_write_engine()
            self._write_session_factory = scoped_session(sessionmaker(bind=engine, expire_on_commit=False))
        return self._write_session_factory

    @property
    def read_session_factory(self):
        """Lazy-load read session factory."""
        if self._read_session_factory is None:
            engine = get_read_engine()
            self._read_session_factory = scoped_session(sessionmaker(bind=engine, expire_on_commit=False))
        return self._read_session_factory

    @contextmanager
    def write_session(self):
        """Context manager for write operations on primary database."""
        session = self.write_session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @contextmanager
    def read_session(self):
        """Context manager for read-only operations (uses replica if available)."""
        # Check replica lag before using replica
        if config.read_replica_enabled and self._check_replica_lag():
            session = self.read_session_factory()
        else:
            # Fallback to write engine if replica is lagging
            session = self.write_session_factory()

        try:
            yield session
        finally:
            session.close()

    def _check_replica_lag(self) -> bool:
        """
        Check if replica lag is within acceptable threshold.
        Returns True if replica is safe to use.
        """
        now = datetime.now(timezone.utc)

        # Cache lag check for 10 seconds
        if self._last_lag_check and (now - self._last_lag_check).seconds < 10:
            return self._replica_lag_ms < config.read_replica_lag_threshold_ms

        try:
            engine = get_read_engine()
            with engine.connect() as conn:
                # PostgreSQL-specific lag check
                result = conn.execute(
                    text(
                        """
                    SELECT CASE
                        WHEN pg_is_in_recovery() THEN
                            EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp())) * 1000
                        ELSE 0
                    END as lag_ms
                """
                    )
                )
                row = result.fetchone()
                self._replica_lag_ms = row[0] if row and row[0] else 0
                self._last_lag_check = now

                if self._replica_lag_ms > config.read_replica_lag_threshold_ms:
                    logger.warning(
                        f"Replica lag ({self._replica_lag_ms}ms) exceeds threshold "
                        f"({config.read_replica_lag_threshold_ms}ms), using primary"
                    )
                    return False

                return True

        except Exception as e:
            logger.warning(f"Failed to check replica lag: {e}")
            return False


# Global router instance
_router: Optional[DatabaseRouter] = None


def get_router() -> DatabaseRouter:
    """Get or create the global database router."""
    global _router
    if _router is None:
        _router = DatabaseRouter()
    return _router


# =====================================================
# Decorator for Read Replica Routing
# =====================================================


def use_read_replica(func: Callable) -> Callable:
    """
    Decorator to route a function's database queries to read replica.

    Usage:
        @use_read_replica
        def get_dashboard_stats():
            # This will use read replica
            return db.query(WeatherData).count()
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        router = get_router()
        with router.read_session() as session:
            # Inject session into kwargs if not provided
            if "session" not in kwargs:
                kwargs["session"] = session
            return func(*args, **kwargs)

    return wrapper


def use_primary(func: Callable) -> Callable:
    """
    Decorator to ensure a function uses the primary database.

    Usage:
        @use_primary
        def create_prediction(data):
            # This will always use primary
            db.add(Prediction(**data))
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        router = get_router()
        with router.write_session() as session:
            if "session" not in kwargs:
                kwargs["session"] = session
            return func(*args, **kwargs)

    return wrapper


# =====================================================
# Health Monitoring
# =====================================================


def get_pool_health() -> Dict[str, Any]:
    """Get connection pool health status for all engines."""
    health = {}

    for name, engine in _engines.items():
        if hasattr(engine, "pool"):
            pool = engine.pool

            if hasattr(pool, "size"):
                total_capacity = pool.size() + pool.overflow()
                active = pool.checkedout()
                utilization = (active / max(total_capacity, 1)) * 100

                health[name] = {
                    "pool_size": pool.size(),
                    "checked_out": active,
                    "overflow": pool.overflow(),
                    "checked_in": pool.checkedin(),
                    "utilization_percent": round(utilization, 2),
                    "status": "critical" if utilization >= 90 else "warning" if utilization >= 75 else "healthy",
                }
            else:
                health[name] = {"status": "null_pool", "message": "Using NullPool (PgBouncer)"}
        else:
            health[name] = {"status": "unknown"}

    return health


def check_replica_status() -> Dict[str, Any]:
    """Check read replica status and replication lag."""
    if not config.read_replica_enabled:
        return {"enabled": False, "message": "Read replica not configured"}

    router = get_router()
    is_healthy = router._check_replica_lag()

    return {
        "enabled": True,
        "healthy": is_healthy,
        "lag_ms": router._replica_lag_ms,
        "threshold_ms": config.read_replica_lag_threshold_ms,
        "status": "healthy" if is_healthy else "lagging",
    }


# =====================================================
# Time-Series Partitioning Helpers
# =====================================================


def get_partition_name(table_name: str, timestamp: datetime) -> str:
    """Generate partition name based on timestamp (monthly partitions)."""
    return f"{table_name}_{timestamp.year}_{timestamp.month:02d}"


def create_partition_sql(table_name: str, year: int, month: int, partition_column: str = "created_at") -> str:
    """
    Generate SQL to create a monthly partition.

    Usage:
        sql = create_partition_sql('weather_data', 2025, 1)
        engine.execute(sql)
    """
    partition_name = f"{table_name}_{year}_{month:02d}"

    # Calculate partition range
    start_date = f"{year}-{month:02d}-01"
    if month == 12:
        end_date = f"{year + 1}-01-01"
    else:
        end_date = f"{year}-{month + 1:02d}-01"

    return f"""
        CREATE TABLE IF NOT EXISTS {partition_name}
        PARTITION OF {table_name}
        FOR VALUES FROM ('{start_date}') TO ('{end_date}');

        -- Create indexes on partition
        CREATE INDEX IF NOT EXISTS idx_{partition_name}_{partition_column}
        ON {partition_name} ({partition_column});
    """


def get_partitions_for_range(table_name: str, start_date: datetime, end_date: datetime) -> list:
    """Get list of partition names for a date range."""
    partitions = []
    current = start_date.replace(day=1)

    while current <= end_date:
        partitions.append(get_partition_name(table_name, current))

        # Move to next month
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)

    return partitions


# =====================================================
# Cleanup
# =====================================================


def dispose_all_engines():
    """Dispose all database engines (for graceful shutdown)."""
    for name, engine in _engines.items():
        logger.info(f"Disposing database engine: {name}")
        engine.dispose()
    _engines.clear()


# Initialize logging
logger.info(
    f"Database optimization module loaded: "
    f"use_pgbouncer={config.use_pgbouncer}, "
    f"read_replica={config.read_replica_enabled}"
)
