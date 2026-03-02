"""
Shared database module for Floodingnaque microservices.

Provides SQLAlchemy engine and session management shared across services.
Each service connects to the same PostgreSQL database but operates on
its own set of tables.
"""

import logging
import os
import threading
from contextlib import contextmanager
from typing import Optional

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker
from sqlalchemy.pool import QueuePool, StaticPool

from .config import get_secret

logger = logging.getLogger(__name__)

# Shared declarative base for all services
Base = declarative_base()

# Lazy engine singleton
_engine: Optional[Engine] = None
_engine_lock = threading.Lock()


def _resolve_db_url() -> str:
    """Resolve database URL from secrets/environment."""
    url = get_secret("DATABASE_URL")
    if url:
        return url

    app_env = os.getenv("APP_ENV", "development").lower()
    if app_env in ("production", "prod", "staging", "stage"):
        raise ValueError(f"DATABASE_URL must be set for {app_env}")

    logger.warning("DATABASE_URL not set — using SQLite for development")
    return "sqlite:///data/service.db"


def get_engine() -> Engine:
    """Get or create the SQLAlchemy engine (thread-safe singleton)."""
    global _engine
    if _engine is not None:
        return _engine

    with _engine_lock:
        if _engine is not None:
            return _engine

        db_url = _resolve_db_url()
        is_sqlite = db_url.startswith("sqlite")

        if is_sqlite:
            engine = create_engine(
                db_url,
                poolclass=StaticPool,
                connect_args={"check_same_thread": False},
                echo=os.getenv("SQL_ECHO", "false").lower() == "true",
            )
        else:
            pool_size = int(os.getenv("DB_POOL_SIZE", "5"))
            max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "10"))
            engine = create_engine(
                db_url,
                poolclass=QueuePool,
                pool_size=pool_size,
                max_overflow=max_overflow,
                pool_timeout=30,
                pool_recycle=1800,
                pool_pre_ping=True,
                echo=os.getenv("SQL_ECHO", "false").lower() == "true",
            )

        _engine = engine
        logger.info("Database engine created: %s", "SQLite" if is_sqlite else "PostgreSQL")
        return _engine


def get_session_factory():
    """Get a scoped session factory."""
    engine = get_engine()
    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    return scoped_session(session_factory)


@contextmanager
def get_db_session():
    """Context manager for database sessions with automatic cleanup."""
    Session = get_session_factory()
    session = Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db():
    """Initialize database tables."""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized")


def dispose_engine():
    """Dispose engine connections (for graceful shutdown)."""
    global _engine
    if _engine:
        _engine.dispose()
        _engine = None
        logger.info("Database engine disposed")
