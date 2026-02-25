"""Backward-compatible shim — canonical location is app.utils.resilience.cache."""

import warnings as _warnings

_warnings.warn(
    "Importing from app.utils.cache is deprecated. " "Use app.utils.resilience.cache instead.",
    DeprecationWarning,
    stacklevel=2,
)

from app.utils.resilience.cache import *  # noqa: F401, F403, E402
