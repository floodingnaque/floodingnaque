"""
Shared database connection helpers.

Centralises PostgreSQL driver detection, SSL context creation, and URL
preparation so that both ``app.models.db`` and ``alembic/env.py`` use
the same logic.
"""

import logging
import os
import re
import ssl
import sys
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


def get_pg_driver() -> str:
    """Return the best PostgreSQL driver for the current platform.

    * **Windows** → ``pg8000`` (pure-Python, no compilation needed)
    * **Linux / Docker** → ``psycopg2`` when available, else ``pg8000``
    """
    if sys.platform == "win32":
        return "pg8000"
    try:
        import psycopg2  # noqa: F401

        return "psycopg2"
    except ImportError:
        return "pg8000"


def _build_ssl_context(
    db_ssl_mode: str,
    db_ssl_ca_cert: str,
    app_env: str,
) -> Optional[ssl.SSLContext]:
    """Create an ``ssl.SSLContext`` matching *db_ssl_mode*.

    Returns ``None`` when SSL is not required.
    """
    if db_ssl_mode not in ("require", "verify-ca", "verify-full"):
        return None

    ctx = ssl.create_default_context()

    if db_ssl_mode == "require":
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        logger.info("SSL mode 'require': encrypted connection without certificate verification")
        return ctx

    # verify-ca / verify-full
    ctx.verify_mode = ssl.CERT_REQUIRED
    ctx.check_hostname = db_ssl_mode == "verify-full"
    logger.info(
        "SSL mode '%s': %s",
        db_ssl_mode,
        (
            "full certificate and hostname verification"
            if db_ssl_mode == "verify-full"
            else "certificate verification without hostname check"
        ),
    )

    if db_ssl_ca_cert:
        if os.path.isfile(db_ssl_ca_cert):
            ctx.load_verify_locations(db_ssl_ca_cert)
            logger.info("Loaded CA certificate from: %s", db_ssl_ca_cert)
            return ctx

        error_msg = (
            f"CRITICAL: SSL certificate file not found: {db_ssl_ca_cert}. "
            f"SSL mode '{db_ssl_mode}' requires a valid CA certificate. "
            "Set DB_SSL_CA_CERT to the path of your CA certificate file."
        )
        logger.error(error_msg)
    else:
        error_msg = (
            f"CRITICAL: DB_SSL_CA_CERT not set but SSL mode is '{db_ssl_mode}'. "
            "Certificate verification modes require DB_SSL_CA_CERT to be set."
        )
        logger.error(error_msg)

    # Fail fast in production / staging
    if app_env in ("production", "prod", "staging", "stage"):
        raise ValueError(error_msg)

    # Fall back to 'require' in development
    logger.warning("Falling back to SSL mode 'require' for development")
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def prepare_db_url(url: str) -> Tuple[str, Dict[str, Any]]:
    """Normalise a database URL for the current platform.

    Handles:
    * PostgreSQL driver injection (``pg8000`` / ``psycopg2``).
    * SSL-mode extraction from the URL and ``ssl.SSLContext`` creation
      for ``pg8000`` (which cannot parse ``sslmode`` from the URL).

    Returns:
        ``(prepared_url, connect_args)`` ready for
        :func:`sqlalchemy.create_engine`.
    """
    if not url or url.startswith("sqlite"):
        return url, {}

    pg_driver = get_pg_driver()
    connect_args: Dict[str, Any] = {}

    # --- Resolve SSL mode ------------------------------------------------
    db_ssl_mode = os.getenv("DB_SSL_MODE", "").lower()
    db_ssl_ca_cert = os.getenv("DB_SSL_CA_CERT", "")
    app_env = os.getenv("APP_ENV", "development").lower()

    if not db_ssl_mode:
        if app_env in ("production", "prod", "staging", "stage"):
            db_ssl_mode = "verify-full"
        else:
            db_ssl_mode = "require"

    # --- pg8000 SSL handling ---------------------------------------------
    if pg_driver == "pg8000":
        if "sslmode=" in url:
            match = re.search(r"[?&]sslmode=([^&]*)", url)
            if match:
                if not os.getenv("DB_SSL_MODE"):
                    db_ssl_mode = match.group(1).lower()
                url = re.sub(r"[?&]sslmode=[^&]*", "", url)
                url = url.replace("?&", "?").rstrip("?")

        ssl_ctx = _build_ssl_context(db_ssl_mode, db_ssl_ca_cert, app_env)
        if ssl_ctx is not None:
            connect_args["ssl_context"] = ssl_ctx
            logger.info("Configured SSL context for pg8000 (sslmode=%s)", db_ssl_mode)

    # --- Driver prefix ---------------------------------------------------
    if url.startswith("postgres://"):
        url = url.replace("postgres://", f"postgresql+{pg_driver}://", 1)
    elif url.startswith("postgresql://") and "+" not in url.split("://")[0]:
        url = url.replace("postgresql://", f"postgresql+{pg_driver}://", 1)

    return url, connect_args
