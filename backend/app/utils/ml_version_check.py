"""Backward-compatible shim — canonical location is app.utils.ml.ml_version_check."""

import warnings as _warnings

_warnings.warn(
    "Importing from app.utils.ml_version_check is deprecated. "
    "Use app.utils.ml.ml_version_check instead.",
    DeprecationWarning,
    stacklevel=2,
)

from app.utils.ml.ml_version_check import *  # noqa: F401, F403, E402
from app.utils.ml.ml_version_check import __all__  # noqa: F401, E402
