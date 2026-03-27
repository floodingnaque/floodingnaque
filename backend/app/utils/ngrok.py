"""
Ngrok tunnel manager for local development.

Exposes the Flask dev server to the internet via Ngrok, useful for:
- Testing webhooks (Semaphore SMS callbacks, GitHub webhooks, etc.)
- Mobile device testing against the local API
- Sharing a dev preview with teammates

Enable by setting NGROK_ENABLED=True in your .env.development file.

Requires: pip install pyngrok (included in requirements-dev.txt)
"""

import logging
import os

logger = logging.getLogger(__name__)

_tunnel = None
_public_url: str | None = None


def start_ngrok(port: int) -> str | None:
    """
    Start an Ngrok tunnel to the given port.

    Reads configuration from environment variables:
        NGROK_AUTHTOKEN  - Your ngrok auth token (https://dashboard.ngrok.com)
        NGROK_DOMAIN     - Custom domain, e.g. my-app.ngrok-free.app (optional)
        NGROK_REGION     - Tunnel region: us, eu, ap, au, sa, jp, in (optional)

    Returns:
        The public HTTPS URL, or None if Ngrok failed to start.
    """
    global _tunnel, _public_url

    try:
        from pyngrok import conf, ngrok
    except ImportError:
        logger.error(
            "pyngrok is not installed. Run: pip install -r requirements-dev.txt"
        )
        return None

    authtoken = os.getenv("NGROK_AUTHTOKEN")
    if authtoken:
        conf.get_default().auth_token = authtoken

    region = os.getenv("NGROK_REGION")
    if region:
        conf.get_default().region = region

    try:
        kwargs: dict = {"addr": str(port), "proto": "http"}
        domain = os.getenv("NGROK_DOMAIN")
        if domain:
            kwargs["domain"] = domain

        _tunnel = ngrok.connect(**kwargs)
        _public_url = _tunnel.public_url

        # Always prefer HTTPS URL
        if _public_url and _public_url.startswith("http://"):
            _public_url = _public_url.replace("http://", "https://", 1)

        logger.info(f"Ngrok tunnel established: {_public_url}")
        return _public_url
    except Exception:
        logger.exception("Failed to start Ngrok tunnel")
        return None


def get_public_url() -> str | None:
    """Return the current Ngrok public URL, or None if not running."""
    return _public_url


def stop_ngrok() -> None:
    """Disconnect all Ngrok tunnels."""
    global _tunnel, _public_url
    try:
        from pyngrok import ngrok

        if _tunnel and _tunnel.public_url:
            ngrok.disconnect(_tunnel.public_url)
        ngrok.kill()
        logger.info("Ngrok tunnel closed")
    except Exception:
        logger.debug("Ngrok shutdown skipped (not running or already closed)")
    finally:
        _tunnel = None
        _public_url = None
