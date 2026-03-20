"""Rate Limiting Tiers Configuration.

Defines rate limiting tiers based on API keys for different service levels.
Includes adaptive rate limiting and IP reputation scoring.
"""

import os
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

from app.utils.observability.logging import get_logger

logger = get_logger(__name__)


class RateLimitTier:
    """Rate limiting tier configuration."""

    def __init__(
        self,
        name: str,
        requests_per_minute: int,
        requests_per_hour: int,
        requests_per_day: int,
        burst_capacity: int = 10,
        priority: int = 0,
        degradation_factor: float = 0.5,
    ):
        self.name = name
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.requests_per_day = requests_per_day
        self.burst_capacity = burst_capacity
        self.priority = priority  # Higher priority = less likely to be rate limited under load
        self.degradation_factor = degradation_factor  # Factor to apply under system stress

    def get_limits(self) -> Dict[str, str]:
        """Get rate limit strings for Flask-Limiter."""
        return {
            "per_minute": f"{self.requests_per_minute}/minute",
            "per_hour": f"{self.requests_per_hour}/hour",
            "per_day": f"{self.requests_per_day}/day",
        }

    def get_degraded_limits(self) -> Dict[str, str]:
        """Get degraded rate limits for system stress conditions."""
        return {
            "per_minute": f"{int(self.requests_per_minute * self.degradation_factor)}/minute",
            "per_hour": f"{int(self.requests_per_hour * self.degradation_factor)}/hour",
            "per_day": f"{int(self.requests_per_day * self.degradation_factor)}/day",
        }


# Define rate limiting tiers
RATE_LIMIT_TIERS = {
    "free": RateLimitTier(
        name="Free Tier",
        requests_per_minute=5,
        requests_per_hour=100,
        requests_per_day=1000,
        burst_capacity=10,
        priority=0,
        degradation_factor=0.3,
    ),
    "basic": RateLimitTier(
        name="Basic Tier",
        requests_per_minute=20,
        requests_per_hour=500,
        requests_per_day=10000,
        burst_capacity=50,
        priority=1,
        degradation_factor=0.5,
    ),
    "pro": RateLimitTier(
        name="Pro Tier",
        requests_per_minute=100,
        requests_per_hour=2000,
        requests_per_day=50000,
        burst_capacity=200,
        priority=2,
        degradation_factor=0.7,
    ),
    "enterprise": RateLimitTier(
        name="Enterprise Tier",
        requests_per_minute=500,
        requests_per_hour=10000,
        requests_per_day=250000,
        burst_capacity=1000,
        priority=3,
        degradation_factor=0.9,
    ),
    "unlimited": RateLimitTier(
        name="Unlimited Tier",
        requests_per_minute=10000,
        requests_per_hour=100000,
        requests_per_day=1000000,
        burst_capacity=5000,
        priority=4,
        degradation_factor=1.0,  # No degradation for unlimited
    ),
}


# ============================================================================
# IP Reputation System
# ============================================================================


@dataclass
class IPReputationEntry:
    """Track reputation data for an IP address."""

    ip_address: str
    score: float = 100.0  # 0-100, higher is better
    request_count: int = 0
    error_count: int = 0
    rate_limit_hits: int = 0
    suspicious_activity_count: int = 0
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    blocked_until: Optional[float] = None

    def is_blocked(self) -> bool:
        """Check if IP is currently blocked."""
        if self.blocked_until is None:
            return False
        return time.time() < self.blocked_until

    def decay_score(self) -> None:
        """Apply time-based decay to restore reputation."""
        hours_since_last = (time.time() - self.last_seen) / 3600
        if hours_since_last > 1:
            # Restore 5 points per hour of inactivity, up to 100
            restoration = min(5.0 * hours_since_last, 100.0 - self.score)
            self.score = min(100.0, self.score + restoration)


class IPReputationManager:
    """Manage IP reputation for adaptive rate limiting."""

    # Score thresholds
    EXCELLENT_THRESHOLD = 90.0
    GOOD_THRESHOLD = 70.0
    FAIR_THRESHOLD = 50.0
    POOR_THRESHOLD = 30.0
    BLOCKED_THRESHOLD = 10.0

    # Penalty amounts
    ERROR_PENALTY = 2.0
    RATE_LIMIT_PENALTY = 5.0
    SUSPICIOUS_PENALTY = 15.0
    MALICIOUS_PENALTY = 50.0

    # Block durations (seconds)
    TEMP_BLOCK_DURATION = 300  # 5 minutes
    EXTENDED_BLOCK_DURATION = 3600  # 1 hour
    SEVERE_BLOCK_DURATION = 86400  # 24 hours

    def __init__(self):
        self._ip_data: Dict[str, IPReputationEntry] = {}
        self._whitelist: set = set()
        self._blacklist: set = set()
        self._load_lists()

    def _load_lists(self):
        """Load whitelist and blacklist from environment."""
        whitelist_str = os.getenv("IP_WHITELIST", "")
        blacklist_str = os.getenv("IP_BLACKLIST", "")

        if whitelist_str:
            self._whitelist = set(ip.strip() for ip in whitelist_str.split(","))
        if blacklist_str:
            self._blacklist = set(ip.strip() for ip in blacklist_str.split(","))

    def get_reputation(self, ip_address: str) -> IPReputationEntry:
        """Get or create reputation entry for an IP."""
        if ip_address not in self._ip_data:
            self._ip_data[ip_address] = IPReputationEntry(ip_address=ip_address)

        entry = self._ip_data[ip_address]
        entry.decay_score()  # Apply time-based restoration
        return entry

    def record_request(self, ip_address: str) -> None:
        """Record a successful request."""
        entry = self.get_reputation(ip_address)
        entry.request_count += 1
        entry.last_seen = time.time()

    def record_error(self, ip_address: str, severity: str = "low") -> None:
        """Record an error response for an IP."""
        entry = self.get_reputation(ip_address)
        entry.error_count += 1
        entry.last_seen = time.time()

        penalty = self.ERROR_PENALTY
        if severity == "high":
            penalty *= 3

        entry.score = max(0.0, entry.score - penalty)
        self._check_block_threshold(entry)

    def record_rate_limit_hit(self, ip_address: str) -> None:
        """Record a rate limit violation."""
        entry = self.get_reputation(ip_address)
        entry.rate_limit_hits += 1
        entry.last_seen = time.time()
        entry.score = max(0.0, entry.score - self.RATE_LIMIT_PENALTY)
        self._check_block_threshold(entry)

    def record_suspicious_activity(self, ip_address: str, reason: str = "") -> None:
        """Record suspicious activity (failed auth, injection attempts, etc.)."""
        entry = self.get_reputation(ip_address)
        entry.suspicious_activity_count += 1
        entry.last_seen = time.time()
        entry.score = max(0.0, entry.score - self.SUSPICIOUS_PENALTY)

        logger.warning(
            f"Suspicious activity from {ip_address}: {reason} "
            f"(score: {entry.score:.1f}, count: {entry.suspicious_activity_count})"
        )

        self._check_block_threshold(entry)

    def record_malicious_activity(self, ip_address: str, reason: str = "") -> None:
        """Record confirmed malicious activity."""
        entry = self.get_reputation(ip_address)
        entry.score = max(0.0, entry.score - self.MALICIOUS_PENALTY)
        entry.last_seen = time.time()

        logger.error(f"Malicious activity from {ip_address}: {reason} " f"(score: {entry.score:.1f})")

        # Immediate extended block for malicious activity
        entry.blocked_until = time.time() + self.EXTENDED_BLOCK_DURATION

    def _check_block_threshold(self, entry: IPReputationEntry) -> None:
        """Check if IP should be blocked based on score."""
        if entry.score <= self.BLOCKED_THRESHOLD:
            if entry.suspicious_activity_count >= 10:
                entry.blocked_until = time.time() + self.SEVERE_BLOCK_DURATION
            elif entry.suspicious_activity_count >= 5:
                entry.blocked_until = time.time() + self.EXTENDED_BLOCK_DURATION
            else:
                entry.blocked_until = time.time() + self.TEMP_BLOCK_DURATION

    def is_blocked(self, ip_address: str) -> Tuple[bool, Optional[int]]:
        """Check if an IP is blocked.

        Returns:
            Tuple of (is_blocked, seconds_remaining)
        """
        # Check blacklist first
        if ip_address in self._blacklist:
            return True, None  # Permanent block

        # Check whitelist
        if ip_address in self._whitelist:
            return False, None

        entry = self.get_reputation(ip_address)
        if entry.is_blocked():
            remaining = int(entry.blocked_until - time.time())
            return True, remaining

        return False, None

    def get_rate_limit_multiplier(self, ip_address: str) -> float:
        """Get rate limit multiplier based on reputation.

        Returns a multiplier to apply to rate limits:
        - > 1.0: IP gets more requests (good reputation)
        - 1.0: Normal limits
        - < 1.0: IP gets fewer requests (poor reputation)
        """
        if ip_address in self._whitelist:
            return 2.0  # Whitelisted IPs get double limits

        entry = self.get_reputation(ip_address)

        if entry.score >= self.EXCELLENT_THRESHOLD:
            return 1.5
        elif entry.score >= self.GOOD_THRESHOLD:
            return 1.2
        elif entry.score >= self.FAIR_THRESHOLD:
            return 1.0
        elif entry.score >= self.POOR_THRESHOLD:
            return 0.7
        else:
            return 0.3

    def cleanup_old_entries(self, max_age_hours: int = 24) -> int:
        """Remove old entries to prevent memory growth."""
        cutoff = time.time() - (max_age_hours * 3600)
        to_remove = [
            ip for ip, entry in self._ip_data.items() if entry.last_seen < cutoff and entry.score >= self.GOOD_THRESHOLD
        ]

        for ip in to_remove:
            del self._ip_data[ip]

        return len(to_remove)

    def get_stats(self) -> Dict:
        """Get reputation system statistics."""
        if not self._ip_data:
            return {
                "total_ips": 0,
                "blocked_ips": 0,
                "avg_score": 100.0,
                "whitelisted": len(self._whitelist),
                "blacklisted": len(self._blacklist),
            }

        blocked = sum(1 for entry in self._ip_data.values() if entry.is_blocked())
        avg_score = sum(e.score for e in self._ip_data.values()) / len(self._ip_data)

        return {
            "total_ips": len(self._ip_data),
            "blocked_ips": blocked,
            "avg_score": round(avg_score, 2),
            "whitelisted": len(self._whitelist),
            "blacklisted": len(self._blacklist),
        }


# Global reputation manager instance
_reputation_manager: Optional[IPReputationManager] = None


def get_reputation_manager() -> IPReputationManager:
    """Get the global IP reputation manager."""
    global _reputation_manager
    if _reputation_manager is None:
        _reputation_manager = IPReputationManager()
    return _reputation_manager


def get_api_key_tier(api_key_hash: str) -> str:
    """
    Get the rate limiting tier for an API key hash.

    In a real implementation, this would:
    1. Look up the API key in a database
    2. Return the associated tier based on subscription plan
    3. Cache the result for performance

    For now, we use environment variables to configure tiers.

    Args:
        api_key_hash: Hashed API key

    Returns:
        str: Tier name ('free', 'basic', 'pro', 'enterprise', 'unlimited')
    """
    # Check environment variable for API key tiers
    tier_config = os.getenv("API_KEY_TIERS", "")

    if tier_config:
        # Format: "key_hash1:tier1,key_hash2:tier2"
        try:
            for mapping in tier_config.split(","):
                key_hash, tier = mapping.strip().split(":")
                if key_hash == api_key_hash:
                    return tier.lower()
        except (ValueError, AttributeError):
            logger.warning(f"Invalid API_KEY_TIERS format: {tier_config}")

    # Default tier based on API key prefix (for demo purposes)
    if api_key_hash.startswith("a"):
        return "free"
    elif api_key_hash.startswith("b"):
        return "basic"
    elif api_key_hash.startswith("c"):
        return "pro"
    elif api_key_hash.startswith("d"):
        return "enterprise"
    else:
        return "free"  # Default to free tier


def get_tier_limits(tier_name: str) -> RateLimitTier:
    """
    Get rate limiting configuration for a tier.

    Args:
        tier_name: Name of the tier

    Returns:
        RateLimitTier: Tier configuration
    """
    tier = RATE_LIMIT_TIERS.get(tier_name.lower())
    if not tier:
        logger.warning("Unknown tier requested, defaulting to free tier")
        return RATE_LIMIT_TIERS["free"]

    return tier


def get_rate_limit_for_key(api_key_hash: str, limit_type: str = "per_minute", ip_address: Optional[str] = None) -> str:
    """
    Get rate limit string for a specific API key.

    Applies IP reputation multiplier if provided.

    Args:
        api_key_hash: Hashed API key
        limit_type: Type of limit ('per_minute', 'per_hour', 'per_day')
        ip_address: Optional IP for reputation-based adjustment

    Returns:
        str: Rate limit string for Flask-Limiter (e.g., "100/minute")
    """
    tier_name = get_api_key_tier(api_key_hash)
    tier = get_tier_limits(tier_name)
    limits = tier.get_limits()

    limit_str = limits.get(limit_type, "10/minute")

    # Apply IP reputation multiplier if available
    if ip_address:
        manager = get_reputation_manager()
        multiplier = manager.get_rate_limit_multiplier(ip_address)

        if multiplier != 1.0:
            # Parse and adjust the limit
            parts = limit_str.split("/")
            if len(parts) == 2:
                base_count = int(parts[0])
                adjusted_count = int(base_count * multiplier)
                limit_str = f"{adjusted_count}/{parts[1]}"

    return limit_str


def get_anonymous_limits(ip_address: Optional[str] = None) -> str:
    """
    Get rate limits for unauthenticated requests.

    Applies IP reputation adjustment if provided.

    Args:
        ip_address: Optional IP for reputation-based adjustment

    Returns:
        str: Rate limit string for anonymous users
    """
    base_limits = "2/minute;20/hour;100/day"

    if ip_address:
        manager = get_reputation_manager()
        multiplier = manager.get_rate_limit_multiplier(ip_address)

        if multiplier != 1.0:
            # Adjust each component
            parts = []
            for limit in base_limits.split(";"):
                count_unit = limit.split("/")
                if len(count_unit) == 2:
                    adjusted = int(int(count_unit[0]) * multiplier)
                    parts.append(f"{adjusted}/{count_unit[1]}")
            base_limits = ";".join(parts)

    return base_limits


def check_rate_limit_status(api_key_hash: Optional[str] = None) -> Dict:
    """
    Check current rate limiting status for an API key.

    Args:
        api_key_hash: Hashed API key (None for anonymous)

    Returns:
        dict: Rate limiting status information
    """
    if api_key_hash:
        tier_name = get_api_key_tier(api_key_hash)
        tier = get_tier_limits(tier_name)

        return {
            "authenticated": True,
            "tier": tier_name,
            "tier_name": tier.name,
            "limits": {
                "per_minute": tier.requests_per_minute,
                "per_hour": tier.requests_per_hour,
                "per_day": tier.requests_per_day,
                "burst_capacity": tier.burst_capacity,
            },
        }
    else:
        return {
            "authenticated": False,
            "tier": "anonymous",
            "tier_name": "Anonymous Users",
            "limits": {"per_minute": 2, "per_hour": 20, "per_day": 100, "burst_capacity": 5},
        }


# Environment-based configuration helpers
def load_api_key_tiers_from_env() -> Dict[str, str]:
    """
    Load API key to tier mappings from environment variables.

    Returns:
        dict: Mapping of API key hashes to tier names
    """
    mappings = {}
    tier_config = os.getenv("API_KEY_TIERS", "")

    if tier_config:
        try:
            for mapping in tier_config.split(","):
                key_hash, tier = mapping.strip().split(":")
                mappings[key_hash.strip()] = tier.strip().lower()
        except (ValueError, AttributeError):
            logger.warning(f"Invalid API_KEY_TIERS format: {tier_config}")

    return mappings


def validate_tier_configuration() -> bool:
    """
    Validate the rate limiting tier configuration.

    Returns:
        bool: True if configuration is valid
    """
    try:
        # Check if all required tiers exist
        required_tiers = ["free", "basic", "pro", "enterprise"]
        for tier in required_tiers:
            if tier not in RATE_LIMIT_TIERS:
                logger.error(f"Missing required tier: {tier}")
                return False

        # Validate tier configurations
        for tier_name, tier in RATE_LIMIT_TIERS.items():
            if tier.requests_per_minute <= 0 or tier.requests_per_hour <= 0 or tier.requests_per_day <= 0:
                logger.error(f"Invalid limits for tier {tier_name}")
                return False

        logger.info("Rate limiting tier configuration is valid")
        return True

    except Exception:
        logger.error("Error validating tier configuration")
        return False


# Initialize and validate configuration on import
if not validate_tier_configuration():
    logger.error("Rate limiting tier configuration validation failed")
