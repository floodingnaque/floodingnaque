"""Backward-compatible shim — canonical location is app.utils.observability.metrics."""

import warnings as _warnings

_warnings.warn(
    "Importing from app.utils.metrics is deprecated. "
    "Use app.utils.observability.metrics instead.",
    DeprecationWarning,
    stacklevel=2,
)

from app.utils.observability.metrics import *  # noqa: F401, F403, E402
from app.utils.observability.metrics import __all__  # noqa: F401, E402
