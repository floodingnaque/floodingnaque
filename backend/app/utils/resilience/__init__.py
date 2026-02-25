"""Resilience utilities: circuit breakers and caching."""

from app.utils.resilience.cache import (
    cache_delete,
    cache_get,
    cache_set,
    cached,
    get_cache_stats,
    is_cache_enabled,
)
from app.utils.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitOpenError,
    CircuitState,
    meteostat_breaker,
    openweathermap_breaker,
    retry_with_backoff,
    weatherstack_breaker,
)

__all__ = [
    # Cache
    "cache_delete",
    "cache_get",
    "cache_set",
    "cached",
    "get_cache_stats",
    "is_cache_enabled",
    # Circuit breaker
    "CircuitBreaker",
    "CircuitOpenError",
    "CircuitState",
    "meteostat_breaker",
    "openweathermap_breaker",
    "retry_with_backoff",
    "weatherstack_breaker",
]
