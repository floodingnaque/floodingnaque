"""Backward-compatible shim — canonical location is app.utils.observability.sentry."""

import warnings as _warnings

_warnings.warn(
    "Importing from app.utils.sentry is deprecated. " "Use app.utils.observability.sentry instead.",
    DeprecationWarning,
    stacklevel=2,
)

from app.utils.observability.sentry import *  # noqa: F401, F403, E402
