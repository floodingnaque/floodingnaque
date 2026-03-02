"""Backward-compatible shim - canonical location is app.utils.observability.correlation."""

import warnings as _warnings

_warnings.warn(
    "Importing from app.utils.correlation is deprecated. " "Use app.utils.observability.correlation instead.",
    DeprecationWarning,
    stacklevel=2,
)

from app.utils.observability.correlation import *  # noqa: F401, F403, E402
