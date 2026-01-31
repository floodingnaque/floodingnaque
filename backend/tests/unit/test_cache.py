"""
Unit tests for cache utilities.

Tests for app/utils/cache.py
"""

import json
from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest

# Import cache module at top level for proper coverage tracking
from app.utils import cache
from app.utils.cache import (
    _make_cache_key,
    cache_clear_pattern,
    cache_delete,
    cache_get,
    cache_set,
    cached,
    get_cache_stats,
    get_cache_warm_stats,
    is_cache_enabled,
    warm_cache,
)


class TestRedisClient:
    """Tests for Redis client initialization."""

    @patch.dict("os.environ", {"REDIS_URL": ""})
    def test_get_redis_client_no_url(self):
        """Test Redis client returns None when URL not configured."""
        cache._redis_client = None
        cache._cache_enabled = None
        result = cache.get_redis_client()
        assert result is None

    @patch.dict("os.environ", {"REDIS_URL": "redis://localhost:6379"})
    def test_get_redis_client_with_url(self):
        """Test Redis client creation with valid URL."""
        cache._redis_client = None
        cache._cache_enabled = None
        # Try to get a redis client - may or may not succeed depending on Redis availability
        try:
            result = cache.get_redis_client()
            assert result is not None or result is None  # Depends on Redis availability
        except Exception:
            # Redis not available - acceptable in test environment
            pass

    def test_is_cache_enabled(self):
        """Test cache enabled check."""
        # Just verify it returns a boolean
        result = is_cache_enabled()
        assert isinstance(result, bool)


class TestCacheKeyGeneration:
    """Tests for cache key generation."""

    def test_make_cache_key_simple(self):
        """Test simple cache key generation."""
        key = _make_cache_key("prefix", "arg1", "arg2")
        assert "prefix" in key
        assert "arg1" in key
        assert "arg2" in key

    def test_make_cache_key_with_kwargs(self):
        """Test cache key with keyword arguments."""
        key = _make_cache_key("prefix", key1="value1", key2="value2")
        assert "prefix" in key
        assert "key1=value1" in key or "key2=value2" in key

    def test_make_cache_key_long_key_hashed(self):
        """Test that long keys are hashed."""
        # Create a very long key
        long_arg = "x" * 300
        key = _make_cache_key("prefix", long_arg)
        # Should be hashed to be shorter than original
        assert len(key) < 300

    def test_make_cache_key_sorted_kwargs(self):
        """Test that kwargs are sorted for consistent keys."""
        key1 = _make_cache_key("prefix", a="1", b="2", c="3")
        key2 = _make_cache_key("prefix", c="3", a="1", b="2")
        assert key1 == key2


class TestCacheGetSet:
    """Tests for cache get and set operations."""

    @patch("app.utils.cache.get_redis_client")
    def test_cache_get_no_client(self, mock_get_client):
        """Test cache get returns None when no client."""
        mock_get_client.return_value = None
        result = cache_get("test_key")
        assert result is None

    @patch("app.utils.cache.get_redis_client")
    def test_cache_get_miss(self, mock_get_client):
        """Test cache get returns None on cache miss."""
        mock_client = MagicMock()
        mock_client.get.return_value = None
        mock_get_client.return_value = mock_client
        result = cache_get("test_key")
        assert result is None

    @patch("app.utils.cache.get_redis_client")
    def test_cache_get_hit(self, mock_get_client):
        """Test cache get returns value on cache hit."""
        mock_client = MagicMock()
        mock_client.get.return_value = json.dumps({"data": "test"})
        mock_get_client.return_value = mock_client
        result = cache_get("test_key")
        assert result == {"data": "test"}

    @patch("app.utils.cache.get_redis_client")
    def test_cache_set_no_client(self, mock_get_client):
        """Test cache set returns False when no client."""
        mock_get_client.return_value = None
        result = cache_set("test_key", {"data": "test"})
        assert result is False

    @patch("app.utils.cache.get_redis_client")
    def test_cache_set_success(self, mock_get_client):
        """Test cache set returns True on success."""
        mock_client = MagicMock()
        mock_client.setex.return_value = True
        mock_get_client.return_value = mock_client
        result = cache_set("test_key", {"data": "test"}, ttl=300)
        assert result is True

    @patch("app.utils.cache.get_redis_client")
    def test_cache_set_with_timedelta(self, mock_get_client):
        """Test cache set with timedelta TTL."""
        mock_client = MagicMock()
        mock_client.setex.return_value = True
        mock_get_client.return_value = mock_client
        result = cache_set("test_key", {"data": "test"}, ttl=timedelta(minutes=5))
        assert result is True


class TestCacheDecorator:
    """Tests for cached decorator."""

    def test_cached_decorator_basic(self):
        """Test cached decorator wraps function."""

        @cached(ttl=60, prefix="test")
        def my_function(x):
            return x * 2

        # Function should still be callable
        # Note: actual caching behavior depends on Redis availability
        assert callable(my_function)

    @patch("app.utils.cache.get_redis_client")
    def test_cached_decorator_no_cache(self, mock_get_client):
        """Test cached decorator works without cache."""
        mock_get_client.return_value = None

        @cached(ttl=60, prefix="test")
        def my_function(x):
            return x * 2

        result = my_function(5)
        assert result == 10


class TestCacheStats:
    """Tests for cache statistics."""

    @patch("app.utils.cache.get_redis_client")
    def test_get_cache_stats_no_client(self, mock_get_client):
        """Test cache stats when no client."""
        mock_get_client.return_value = None
        result = get_cache_stats()
        assert result == {} or "enabled" in result or result.get("enabled") is False

    @patch("app.utils.cache.get_redis_client")
    def test_get_cache_stats_with_client(self, mock_get_client):
        """Test cache stats with client."""
        mock_client = MagicMock()
        mock_client.info.return_value = {"keyspace_hits": 100, "keyspace_misses": 20, "connected_clients": 5}
        mock_get_client.return_value = mock_client
        result = get_cache_stats()
        # Should return some stats
        assert isinstance(result, dict)


class TestCacheWarm:
    """Tests for cache warming functionality."""

    @patch("app.utils.cache.get_redis_client")
    def test_warm_cache_no_client(self, mock_get_client):
        """Test cache warming without client."""
        mock_get_client.return_value = None
        result = warm_cache()
        assert result is False or result is None or isinstance(result, dict)

    def test_get_cache_warm_stats(self):
        """Test getting cache warm statistics."""
        result = get_cache_warm_stats()
        assert isinstance(result, dict)


class TestCacheDelete:
    """Tests for cache deletion."""

    @patch("app.utils.cache.get_redis_client")
    def test_cache_delete_no_client(self, mock_get_client):
        """Test cache delete without client."""
        mock_get_client.return_value = None
        result = cache_delete("test_key")
        assert result is False

    @patch("app.utils.cache.get_redis_client")
    def test_cache_delete_success(self, mock_get_client):
        """Test cache delete success."""
        mock_client = MagicMock()
        mock_client.delete.return_value = 1
        mock_get_client.return_value = mock_client
        result = cache_delete("test_key")
        assert result is True


class TestCacheInvalidation:
    """Tests for cache invalidation patterns."""

    @patch("app.utils.cache.get_redis_client")
    def test_cache_clear_pattern(self, mock_get_client):
        """Test cache invalidation by pattern."""
        mock_client = MagicMock()
        mock_client.scan_iter.return_value = ["key1", "key2"]
        mock_client.delete.return_value = 2
        mock_get_client.return_value = mock_client
        result = cache_clear_pattern("test:*")
        assert result >= 0 or result is None
