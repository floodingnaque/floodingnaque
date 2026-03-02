"""
Service discovery module for Floodingnaque microservices.

Provides a lightweight service registry that services register with
on startup, enabling dynamic endpoint resolution for inter-service
communication.
"""

import logging
import os
import threading
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ServiceRegistry:
    """
    In-memory service registry backed by Redis for distributed state.

    Each service registers itself on startup with its name, host, port,
    and health check URL. Other services query the registry to discover
    endpoints.

    In production, this can be replaced with Consul, etcd, or
    Kubernetes service discovery.
    """

    _instance: Optional["ServiceRegistry"] = None
    _lock = threading.Lock()

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self._redis = None
        self._local_cache: Dict[str, Dict[str, Any]] = {}
        self._ttl = int(os.getenv("SERVICE_REGISTRY_TTL", "60"))

    @classmethod
    def get_instance(cls) -> "ServiceRegistry":
        """Get or create singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _get_redis(self):
        if self._redis is None:
            try:
                import redis
                self._redis = redis.from_url(self.redis_url, decode_responses=True)
                self._redis.ping()
            except Exception:
                self._redis = None
        return self._redis

    def register(self, service_name: str, host: str, port: int, metadata: Optional[Dict] = None):
        """
        Register a service instance.

        Args:
            service_name: Unique service identifier
            host: Service hostname or IP
            port: Service port
            metadata: Optional metadata (version, health_url, etc.)
        """
        entry = {
            "host": host,
            "port": port,
            "url": f"http://{host}:{port}",
            "registered_at": time.time(),
            **(metadata or {}),
        }

        self._local_cache[service_name] = entry

        client = self._get_redis()
        if client:
            import json
            key = f"service:{service_name}"
            client.setex(key, self._ttl, json.dumps(entry))
            logger.info("Service registered: %s at %s:%s", service_name, host, port)

    def deregister(self, service_name: str):
        """Remove a service from the registry."""
        self._local_cache.pop(service_name, None)
        client = self._get_redis()
        if client:
            client.delete(f"service:{service_name}")

    def discover(self, service_name: str) -> Optional[Dict[str, Any]]:
        """
        Discover a service by name.

        Returns:
            Service entry dict with host, port, url, or None if not found.
        """
        # Try Redis first for distributed state
        client = self._get_redis()
        if client:
            import json
            data = client.get(f"service:{service_name}")
            if data:
                return json.loads(data)

        # Fall back to local cache
        return self._local_cache.get(service_name)

    def get_service_url(self, service_name: str) -> Optional[str]:
        """Get the base URL for a service."""
        entry = self.discover(service_name)
        return entry["url"] if entry else None

    def list_services(self) -> List[str]:
        """List all registered service names."""
        client = self._get_redis()
        if client:
            keys = client.keys("service:*")
            return [k.replace("service:", "") for k in keys]
        return list(self._local_cache.keys())

    def heartbeat(self, service_name: str):
        """Refresh a service registration TTL."""
        client = self._get_redis()
        if client:
            client.expire(f"service:{service_name}", self._ttl)

    def start_heartbeat_loop(self, service_name: str, interval: int = 30):
        """Start background heartbeat for a service."""
        def _heartbeat():
            while True:
                try:
                    self.heartbeat(service_name)
                except Exception as e:
                    logger.warning("Heartbeat failed for %s: %s", service_name, e)
                time.sleep(interval)

        thread = threading.Thread(target=_heartbeat, daemon=True)
        thread.start()
