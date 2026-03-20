"""Backward-compatible shim - canonical location is app.utils.resilience.cache."""

import warnings as _warnings

_warnings.warn(
    "Importing from app.utils.cache is deprecated. " "Use app.utils.resilience.cache instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Private names are skipped by `import *` - re-export them explicitly so
# existing tests / call-sites that reference them keep working.
from app.utils.resilience.cache import *  # noqa: F401, F403, E402
from app.utils.resilience.cache import (  # noqa: F401, E402
    _cache_enabled,
    _make_cache_key,
    _redis_client,
)
