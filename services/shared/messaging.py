"""
Inter-service communication module for Floodingnaque microservices.

Provides:
- Synchronous HTTP client with retry logic and circuit breaker
- Redis pub/sub for async event-driven messaging
- Service-to-service authentication via JWT
"""

import json
import logging
import os
import threading
import time
from enum import Enum
from typing import Any, Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .auth import create_service_token

logger = logging.getLogger(__name__)


# ── Circuit Breaker ────────────────────────────────────────────────────────

class CircuitState(Enum):
    CLOSED = "closed"       # Normal operation
    OPEN = "open"           # Failing - reject requests
    HALF_OPEN = "half_open" # Testing - allow one request


class CircuitBreaker:
    """
    Circuit breaker for inter-service calls.

    Prevents cascading failures by stopping requests to a failing service
    after a threshold of consecutive failures.
    """

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 30):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self._lock = threading.Lock()

    def can_execute(self) -> bool:
        """Check if a request is allowed."""
        with self._lock:
            if self.state == CircuitState.CLOSED:
                return True
            if self.state == CircuitState.OPEN:
                if time.time() - (self.last_failure_time or 0) > self.recovery_timeout:
                    self.state = CircuitState.HALF_OPEN
                    return True
                return False
            # HALF_OPEN - allow one request
            return True

    def record_success(self):
        """Record a successful call."""
        with self._lock:
            self.failure_count = 0
            self.state = CircuitState.CLOSED

    def record_failure(self):
        """Record a failed call."""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
                logger.warning("Circuit breaker OPEN after %d failures", self.failure_count)


# ── HTTP Service Client ───────────────────────────────────────────────────

class ServiceClient:
    """
    HTTP client for inter-service communication.

    Features:
    - Automatic retries with exponential backoff
    - Circuit breaker pattern
    - Service-to-service JWT authentication
    - Request tracing with correlation IDs
    """

    def __init__(self, base_url: str, service_name: str = "unknown", timeout: int = 10):
        self.base_url = base_url.rstrip("/")
        self.service_name = service_name
        self.timeout = timeout
        self.circuit_breaker = CircuitBreaker()

        # Create session with retry adapter
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "DELETE"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def _get_headers(self, extra_headers: Optional[Dict] = None) -> Dict[str, str]:
        """Build request headers with service auth token."""
        headers = {
            "Content-Type": "application/json",
            "X-Service-Name": self.service_name,
            "Authorization": f"Bearer {create_service_token(self.service_name)}",
        }
        if extra_headers:
            headers.update(extra_headers)
        return headers

    def request(self, method: str, path: str, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Make an authenticated HTTP request to another service.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: URL path (appended to base_url)
            **kwargs: Passed to requests.Session.request()

        Returns:
            Response JSON or None on failure
        """
        if not self.circuit_breaker.can_execute():
            logger.warning("Circuit breaker OPEN for %s - skipping request", self.base_url)
            return None

        url = f"{self.base_url}{path}"
        kwargs.setdefault("headers", self._get_headers(kwargs.pop("extra_headers", None)))
        kwargs.setdefault("timeout", self.timeout)

        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            self.circuit_breaker.record_success()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.circuit_breaker.record_failure()
            logger.error("Service call failed: %s %s - %s", method, url, e)
            return None

    def get(self, path: str, **kwargs):
        return self.request("GET", path, **kwargs)

    def post(self, path: str, data: Any = None, **kwargs):
        return self.request("POST", path, json=data, **kwargs)

    def put(self, path: str, data: Any = None, **kwargs):
        return self.request("PUT", path, json=data, **kwargs)

    def delete(self, path: str, **kwargs):
        return self.request("DELETE", path, **kwargs)


# ── Redis Pub/Sub Event Bus ───────────────────────────────────────────────

class EventBus:
    """
    Redis-based event bus for async inter-service messaging.

    Services publish domain events (e.g., 'weather.data.collected',
    'prediction.completed', 'alert.triggered') which other services
    subscribe to.
    """

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self._redis = None
        self._pubsub = None
        self._handlers: Dict[str, List[callable]] = {}
        self._listener_thread: Optional[threading.Thread] = None

    def _get_redis(self):
        """Lazy-init Redis connection."""
        if self._redis is None:
            try:
                import redis
                self._redis = redis.from_url(self.redis_url, decode_responses=True)
                self._redis.ping()
                logger.info("EventBus connected to Redis: %s", self.redis_url)
            except Exception as e:
                logger.warning("EventBus Redis unavailable: %s", e)
                self._redis = None
        return self._redis

    def publish(self, event_type: str, data: Dict[str, Any]):
        """
        Publish an event to the bus.

        Args:
            event_type: Event channel (e.g., 'weather.data.collected')
            data: Event payload
        """
        client = self._get_redis()
        if client is None:
            logger.debug("EventBus publish skipped (no Redis): %s", event_type)
            return

        message = json.dumps({
            "event": event_type,
            "data": data,
            "timestamp": time.time(),
            "source": os.getenv("SERVICE_NAME", "unknown"),
        })
        try:
            client.publish(event_type, message)
            logger.debug("Event published: %s", event_type)
        except Exception as e:
            logger.error("Event publish failed: %s - %s", event_type, e)

    def subscribe(self, event_type: str, handler: callable):
        """
        Subscribe to events of a given type.

        Args:
            event_type: Event channel to subscribe to
            handler: Callback function receiving event data dict
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def start_listening(self):
        """Start background thread to listen for subscribed events."""
        client = self._get_redis()
        if client is None or not self._handlers:
            return

        self._pubsub = client.pubsub()
        self._pubsub.subscribe(*self._handlers.keys())

        def _listen():
            for message in self._pubsub.listen():
                if message["type"] != "message":
                    continue
                channel = message["channel"]
                try:
                    data = json.loads(message["data"])
                    for handler in self._handlers.get(channel, []):
                        handler(data)
                except Exception as e:
                    logger.error("Event handler error [%s]: %s", channel, e)

        self._listener_thread = threading.Thread(target=_listen, daemon=True)
        self._listener_thread.start()
        logger.info("EventBus listening on: %s", list(self._handlers.keys()))

    def stop(self):
        """Stop listening and close connections."""
        if self._pubsub:
            self._pubsub.unsubscribe()
            self._pubsub.close()
        if self._redis:
            self._redis.close()


# ── Factory functions ─────────────────────────────────────────────────────

def create_weather_client() -> ServiceClient:
    """Create a client for the Weather Data Collector Service."""
    url = os.getenv("WEATHER_SERVICE_URL", "http://weather-collector:5001")
    return ServiceClient(url, service_name="weather-collector")


def create_prediction_client() -> ServiceClient:
    """Create a client for the ML Prediction Service."""
    url = os.getenv("ML_PREDICTION_SERVICE_URL", "http://ml-prediction:5002")
    return ServiceClient(url, service_name="ml-prediction")


def create_alert_client() -> ServiceClient:
    """Create a client for the Alert Notification Service."""
    url = os.getenv("ALERT_SERVICE_URL", "http://alert-notification:5003")
    return ServiceClient(url, service_name="alert-notification")


def create_user_client() -> ServiceClient:
    """Create a client for the User Management Service."""
    url = os.getenv("USER_SERVICE_URL", "http://user-management:5004")
    return ServiceClient(url, service_name="user-management")


def create_dashboard_client() -> ServiceClient:
    """Create a client for the Dashboard API Service."""
    url = os.getenv("DASHBOARD_SERVICE_URL", "http://dashboard-api:5005")
    return ServiceClient(url, service_name="dashboard-api")
