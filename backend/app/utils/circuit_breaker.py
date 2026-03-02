"""Backward-compatible shim - canonical location is app.utils.resilience.circuit_breaker."""

import warnings as _warnings

_warnings.warn(
    "Importing from app.utils.circuit_breaker is deprecated. " "Use app.utils.resilience.circuit_breaker instead.",
    DeprecationWarning,
    stacklevel=2,
)

from app.utils.resilience.circuit_breaker import *  # noqa: F401, F403, E402
