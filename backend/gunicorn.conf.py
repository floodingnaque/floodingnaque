"""Gunicorn configuration file.

Reads environment variables with sensible defaults. Used by:
    gunicorn -c gunicorn.conf.py main:application

Env vars set in compose.production.yaml / .env.* files.
"""

import multiprocessing
import os

# ── Server socket ────────────────────────────────────────────────────────
bind = f"{os.getenv('HOST', '0.0.0.0')}:{os.getenv('PORT', '5000')}"

# ── Worker processes ─────────────────────────────────────────────────────
workers = int(os.getenv("GUNICORN_WORKERS", min(multiprocessing.cpu_count() * 2 + 1, 9)))
threads = int(os.getenv("GUNICORN_THREADS", "2"))
worker_class = os.getenv("GUNICORN_WORKER_CLASS", "sync")
timeout = int(os.getenv("GUNICORN_TIMEOUT", "120"))

# ── Worker recycling (prevents gradual memory leaks) ─────────────────────
max_requests = int(os.getenv("GUNICORN_MAX_REQUESTS", "5000"))
max_requests_jitter = int(os.getenv("GUNICORN_MAX_REQUESTS_JITTER", "200"))

# ── Logging ──────────────────────────────────────────────────────────────
accesslog = "-"
errorlog = "-"
capture_output = True
enable_stdio_inheritance = True

# ── Performance ──────────────────────────────────────────────────────────
preload_app = True
