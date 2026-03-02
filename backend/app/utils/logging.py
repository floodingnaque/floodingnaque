"""Backward-compatible shim - canonical location is app.utils.observability.logging."""

import warnings as _warnings

_warnings.warn(
    "Importing from app.utils.logging is deprecated. " "Use app.utils.observability.logging instead.",
    DeprecationWarning,
    stacklevel=2,
)

from app.utils.observability.logging import *  # noqa: F401, F403, E402
