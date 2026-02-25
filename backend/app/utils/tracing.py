"""Backward-compatible shim — canonical location is app.utils.observability.tracing."""

import warnings as _warnings

_warnings.warn(
    "Importing from app.utils.tracing is deprecated. " "Use app.utils.observability.tracing instead.",
    DeprecationWarning,
    stacklevel=2,
)

from app.utils.observability.tracing import *  # noqa: F401, F403, E402
from app.utils.observability.tracing import __all__  # noqa: F401, E402
