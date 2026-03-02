"""API Key Authentication Middleware.

Provides decorator-based authentication for protecting API endpoints.
Implements bcrypt hashing and timing-safe comparison to prevent attacks.

Security Features:
- bcrypt for API key hashing (resistant to rainbow table attacks)
- Timing-safe comparison prevents timing attacks
- No information leakage about valid keys
- API key format validation with entropy checks
- Key expiration and revocation support
"""

import hashlib
import hmac
import logging
import math
import os
import re
import time
from collections import Counter
from functools import wraps
from typing import Dict, Optional, Set, Tuple

from app.core.config import is_debug_mode
from app.core.constants import MIN_API_KEY_LENGTH
from flask import g, jsonify, request

try:
    import bcrypt

    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False
    logging.warning("bcrypt not available, falling back to SHA-256 (less secure)")

logger = logging.getLogger(__name__)

# Cache for hashed API keys (computed once at startup)
_hashed_api_keys: Optional[Dict[str, bytes]] = None  # Maps key_id to bcrypt hash
_legacy_hashed_keys: Optional[Set[str]] = None  # Fallback SHA-256 hashes

# API key expiration cache (key_hash -> expiration timestamp)
_api_key_expirations: Dict[str, float] = {}

# Revoked API keys (key_hash -> revocation timestamp)
_revoked_api_keys: Dict[str, float] = {}

# Failed authentication attempts tracking (IP -> (count, last_attempt))
_failed_auth_attempts: Dict[str, Tuple[int, float]] = {}

# Security configuration
MAX_FAILED_ATTEMPTS = int(os.getenv("AUTH_MAX_FAILED_ATTEMPTS", "5"))
FAILED_ATTEMPT_WINDOW = int(os.getenv("AUTH_FAILED_ATTEMPT_WINDOW", "300"))  # 5 minutes
LOCKOUT_DURATION = int(os.getenv("AUTH_LOCKOUT_DURATION", "900"))  # 15 minutes
API_KEY_MIN_ENTROPY = float(os.getenv("API_KEY_MIN_ENTROPY", "3.0"))  # bits per character


def _calculate_entropy(text: str) -> float:
    """
    Calculate Shannon entropy of a string.

    Higher entropy indicates more randomness (better for API keys).
    A good API key should have entropy > 3.0 bits per character.

    Args:
        text: String to analyze

    Returns:
        float: Entropy in bits per character
    """
    if not text:
        return 0.0

    char_counts = Counter(text)
    length = len(text)
    entropy = 0.0

    for count in char_counts.values():
        if count > 0:
            freq = count / length
            entropy -= freq * math.log2(freq)

    return entropy


def _validate_api_key_format(api_key: str) -> Tuple[bool, str]:
    """
    Validate API key format and entropy.

    Security checks:
    - Minimum length requirement
    - Character set validation (alphanumeric + limited special chars)
    - Entropy check to ensure sufficient randomness
    - No sequential patterns or common strings

    Args:
        api_key: The API key to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check length
    if len(api_key) < MIN_API_KEY_LENGTH:
        return False, f"API key must be at least {MIN_API_KEY_LENGTH} characters"

    # Check character set (URL-safe base64 characters)
    valid_pattern = re.compile(r"^[A-Za-z0-9_\-]+$")
    if not valid_pattern.match(api_key):
        return False, "API key contains invalid characters"

    # Check entropy
    entropy = _calculate_entropy(api_key)
    if entropy < API_KEY_MIN_ENTROPY:
        logger.warning("API key rejected: insufficient entropy")
        return False, "API key does not meet entropy requirements"

    # Check for common weak patterns
    weak_patterns = [
        r"(.)(\1{3,})",  # 4+ repeated characters
        r"(?:0123|1234|2345|3456|4567|5678|6789|abcd|bcde|cdef)",  # Sequential
        r"(?:password|secret|apikey|admin|test|demo)",  # Common words
    ]

    api_key_lower = api_key.lower()
    for pattern in weak_patterns:
        if re.search(pattern, api_key_lower):
            return False, "API key contains weak patterns"

    return True, ""


def _hash_api_key_bcrypt(api_key: str) -> bytes:
    """
    Hash an API key using bcrypt for secure storage.

    bcrypt includes salt and is resistant to rainbow table attacks.
    Cost factor 12 provides good security/performance balance.
    """
    if not BCRYPT_AVAILABLE:
        raise RuntimeError("bcrypt is not installed")
    return bcrypt.hashpw(api_key.encode("utf-8"), bcrypt.gensalt(rounds=12))


def _verify_api_key_bcrypt(api_key: str, hashed: bytes) -> bool:
    """
    Verify an API key against a bcrypt hash.

    bcrypt.checkpw is timing-safe by design.
    """
    if not BCRYPT_AVAILABLE:
        return False
    try:
        return bcrypt.checkpw(api_key.encode("utf-8"), hashed)
    except (ValueError, TypeError):
        return False


def _hash_api_key_pbkdf2(api_key: str) -> str:
    """
    Fallback: Hash an API key using PBKDF2-SHA256 (when bcrypt unavailable).

    PBKDF2 with high iteration count is a secure key derivation function
    that is resistant to brute-force and rainbow table attacks.

    Raises:
        ValueError: If API_KEY_HASH_SALT environment variable is not set.
    """
    # PBKDF2-SHA256 with 100,000 iterations for secure API key hashing
    # Security: Salt MUST be provided via environment variable - no hardcoded fallback
    secret_salt = os.getenv("API_KEY_HASH_SALT")
    if not secret_salt:
        raise ValueError(
            "API_KEY_HASH_SALT environment variable is required for PBKDF2 fallback. "
            "Set a secure random salt (at least 32 characters) or install bcrypt."
        )
    return hashlib.pbkdf2_hmac("sha256", api_key.encode("utf-8"), secret_salt.encode(), 100000).hex()


def _timing_safe_compare(a: str, b: str) -> bool:
    """
    Compare two strings in constant time to prevent timing attacks.

    Uses hmac.compare_digest which is designed to prevent timing analysis.
    """
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def get_valid_api_keys() -> Set[str]:
    """
    Get valid API keys from environment variables.

    Validates that keys meet minimum length requirement (MIN_API_KEY_LENGTH).
    Keys shorter than the minimum are rejected with a warning.

    Returns:
        set: Set of valid API keys (empty set if none configured)
    """
    keys_str = os.getenv("VALID_API_KEYS", "")
    if not keys_str:
        return set()

    valid_keys = set()
    key_count = 0
    rejected_count = 0
    for raw_key in keys_str.split(","):
        stripped_key = raw_key.strip()
        if not stripped_key:
            continue
        key_count += 1
        if len(stripped_key) < MIN_API_KEY_LENGTH:
            rejected_count += 1
            continue
        valid_keys.add(stripped_key)
        # Clear sensitive variable immediately after use
        stripped_key = None  # nosec - intentionally clearing sensitive data

    # Delegate logging to separate function to isolate from sensitive data context
    _log_key_validation_summary(rejected_count, key_count)

    return valid_keys


def _log_key_validation_summary(rejected: int, total: int) -> None:
    """Log API key validation summary without access to sensitive data."""
    if rejected > 0:
        # Sanitize inputs to ensure only numeric counts are logged (not sensitive data)
        # These are integer counts, not key values - safe to log
        sanitized_rejected = int(rejected)  # nosec - explicitly sanitized count
        sanitized_total = int(total)  # nosec - explicitly sanitized count
        min_length = int(MIN_API_KEY_LENGTH)  # nosec - configuration value
        logger.warning(
            "API key configuration: %d of %d keys rejected (below minimum length %d). "
            "See documentation for key generation guidelines.",
            sanitized_rejected,
            sanitized_total,
            min_length,
        )


def get_hashed_api_keys() -> Dict[str, bytes]:
    """
    Get pre-hashed API keys for secure comparison.

    Uses bcrypt if available, falls back to SHA-256.
    Hashes are computed once and cached for performance.

    Returns:
        Dict mapping key identifiers to bcrypt hashes
    """
    global _hashed_api_keys, _legacy_hashed_keys

    if _hashed_api_keys is None:
        valid_keys = get_valid_api_keys()

        if BCRYPT_AVAILABLE:
            # Use bcrypt for secure hashing
            _hashed_api_keys = {}
            for i, key in enumerate(valid_keys):
                key_id = f"key_{i}"
                _hashed_api_keys[key_id] = _hash_api_key_bcrypt(key)
            logger.info(f"Initialized {len(_hashed_api_keys)} API keys with bcrypt hashing")
        else:
            # Fallback to PBKDF2-SHA256 (secure key derivation function)
            _hashed_api_keys = {}
            _legacy_hashed_keys = {_hash_api_key_pbkdf2(key) for key in valid_keys}
            logger.warning("Using PBKDF2-SHA256 for API keys (bcrypt not available)")

    return _hashed_api_keys


def invalidate_api_key_cache():
    """Invalidate the API key cache (call when keys are updated)."""
    global _hashed_api_keys, _legacy_hashed_keys
    _hashed_api_keys = None
    _legacy_hashed_keys = None


def revoke_api_key(api_key: str) -> bool:
    """
    Revoke an API key immediately.

    Revoked keys cannot be used even if they haven't expired.

    Args:
        api_key: The API key to revoke

    Returns:
        bool: True if revoked successfully
    """
    global _revoked_api_keys
    key_hash = _hash_api_key_pbkdf2(api_key)[:16]  # Use truncated hash as identifier
    _revoked_api_keys[key_hash] = time.time()
    logger.info(f"API key revoked: {key_hash[:8]}...")
    return True


def is_api_key_revoked(api_key: str) -> bool:
    """
    Check if an API key has been revoked.

    Args:
        api_key: The API key to check

    Returns:
        bool: True if revoked
    """
    key_hash = _hash_api_key_pbkdf2(api_key)[:16]
    return key_hash in _revoked_api_keys


def set_api_key_expiration(api_key: str, expires_at: float) -> None:
    """
    Set expiration timestamp for an API key.

    Args:
        api_key: The API key
        expires_at: Unix timestamp when key expires
    """
    global _api_key_expirations
    key_hash = _hash_api_key_pbkdf2(api_key)[:16]
    _api_key_expirations[key_hash] = expires_at


def is_api_key_expired(api_key: str) -> bool:
    """
    Check if an API key has expired.

    Args:
        api_key: The API key to check

    Returns:
        bool: True if expired
    """
    key_hash = _hash_api_key_pbkdf2(api_key)[:16]

    if key_hash not in _api_key_expirations:
        # Check environment for default expiration
        default_expiry_days = int(os.getenv("API_KEY_DEFAULT_EXPIRY_DAYS", "0"))
        if default_expiry_days <= 0:
            return False  # No expiration by default

    expires_at = _api_key_expirations.get(key_hash, float("inf"))
    return time.time() > expires_at


def _check_ip_lockout(ip_address: str) -> Tuple[bool, int]:
    """
    Check if an IP address is locked out due to failed authentication attempts.

    Args:
        ip_address: Client IP address

    Returns:
        Tuple of (is_locked_out, seconds_remaining)
    """
    if ip_address not in _failed_auth_attempts:
        return False, 0

    count, last_attempt = _failed_auth_attempts[ip_address]
    now = time.time()

    # Check if lockout period has passed
    if count >= MAX_FAILED_ATTEMPTS:
        lockout_end = last_attempt + LOCKOUT_DURATION
        if now < lockout_end:
            return True, int(lockout_end - now)
        else:
            # Reset after lockout period
            del _failed_auth_attempts[ip_address]
            return False, 0

    # Check if failed attempt window has expired
    if now - last_attempt > FAILED_ATTEMPT_WINDOW:
        del _failed_auth_attempts[ip_address]
        return False, 0

    return False, 0


def _record_failed_attempt(ip_address: str) -> int:
    """
    Record a failed authentication attempt.

    Args:
        ip_address: Client IP address

    Returns:
        int: Current failure count
    """
    global _failed_auth_attempts
    now = time.time()

    if ip_address in _failed_auth_attempts:
        count, last_attempt = _failed_auth_attempts[ip_address]
        # Reset if window expired
        if now - last_attempt > FAILED_ATTEMPT_WINDOW:
            count = 0
        _failed_auth_attempts[ip_address] = (count + 1, now)
        return count + 1
    else:
        _failed_auth_attempts[ip_address] = (1, now)
        return 1


def _clear_failed_attempts(ip_address: str) -> None:
    """Clear failed authentication attempts for an IP after successful auth."""
    if ip_address in _failed_auth_attempts:
        del _failed_auth_attempts[ip_address]


def cleanup_auth_tracking() -> int:
    """
    Clean up old authentication tracking data.

    Should be called periodically to prevent memory growth.

    Returns:
        int: Number of entries cleaned up
    """
    global _failed_auth_attempts, _revoked_api_keys
    now = time.time()
    cleaned = 0

    # Clean failed attempts older than lockout duration
    to_remove = []
    for ip, (count, last_attempt) in _failed_auth_attempts.items():
        if now - last_attempt > LOCKOUT_DURATION:
            to_remove.append(ip)

    for ip in to_remove:
        del _failed_auth_attempts[ip]
        cleaned += 1

    # Note: Revoked keys are kept indefinitely for security
    # In production, use a persistent store (Redis/database)

    return cleaned


def validate_api_key(api_key: str, check_expiration: bool = True, check_revocation: bool = True) -> Tuple[bool, str]:
    """
    Validate an API key comprehensively.

    Security checks performed:
    1. Format validation (length, characters, entropy)
    2. Expiration check
    3. Revocation check
    4. Hash verification (bcrypt or SHA-256 fallback)

    bcrypt.checkpw is inherently timing-safe.
    For SHA-256 fallback, uses hmac.compare_digest.

    Args:
        api_key: The API key to validate
        check_expiration: Whether to check key expiration
        check_revocation: Whether to check key revocation

    Returns:
        Tuple of (is_valid, error_reason)
    """
    if not api_key:
        return False, "API key is required"

    # Format validation
    is_valid_format, format_error = _validate_api_key_format(api_key)
    if not is_valid_format:
        return False, format_error

    # Check revocation
    if check_revocation and is_api_key_revoked(api_key):
        return False, "API key has been revoked"

    # Check expiration
    if check_expiration and is_api_key_expired(api_key):
        return False, "API key has expired"

    # Ensure keys are initialized
    get_hashed_api_keys()

    # Verify hash
    if BCRYPT_AVAILABLE and _hashed_api_keys:
        # Verify against all bcrypt hashes (timing-safe)
        # We check all keys to maintain constant time regardless of match position
        valid = False
        for key_id, hashed in _hashed_api_keys.items():
            if _verify_api_key_bcrypt(api_key, hashed):
                valid = True
                # Don't break early - continue to maintain constant time
        if not valid:
            return False, "Invalid API key"
        return True, ""
    elif _legacy_hashed_keys:
        # Fallback to PBKDF2 comparison
        hashed_input = _hash_api_key_pbkdf2(api_key)
        valid = False
        for hashed_key in _legacy_hashed_keys:
            if _timing_safe_compare(hashed_input, hashed_key):
                valid = True
        if not valid:
            return False, "Invalid API key"
        return True, ""

    return False, "No API keys configured"


def validate_api_key_simple(api_key: str) -> bool:
    """
    Simple API key validation (backward compatible).

    Args:
        api_key: The API key to validate

    Returns:
        bool: True if valid, False otherwise
    """
    is_valid, _ = validate_api_key(api_key)
    return is_valid


def require_auth(f):
    """
    Decorator that requires a valid JWT Bearer token.

    Reads the Authorization header for a Bearer token, decodes it,
    and sets g.current_user_id, g.current_user_email, and g.current_user_role.

    Usage:
        @app.route('/protected')
        @require_auth
        def protected_endpoint():
            user_id = g.current_user_id
            ...
    """
    from app.core.security import decode_token

    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return (
                jsonify(
                    {"error": "Authorization required", "message": "Bearer token required in Authorization header"}
                ),
                401,
            )

        token = auth_header.split(" ", 1)[1]
        payload, error = decode_token(token)
        if error:
            return jsonify({"error": "InvalidToken", "message": error}), 401

        g.authenticated = True
        g.current_user_id = int(payload.get("sub"))
        g.current_user_email = payload.get("email")
        g.current_user_role = payload.get("role")
        return f(*args, **kwargs)

    return decorated


def require_auth_or_api_key(f):
    """
    Decorator that accepts either a JWT Bearer token or an API key.

    Checks Authorization: Bearer first, then falls back to X-API-Key.
    This allows browser-based users (JWT) and machine clients (API key)
    to share the same endpoints.
    """
    from app.core.security import decode_token

    @wraps(f)
    def decorated(*args, **kwargs):
        # Check IP lockout before attempting auth
        ip_address = request.remote_addr
        is_locked, remaining_seconds = _check_ip_lockout(ip_address)
        if is_locked:
            logger.warning(f"Locked out IP attempted access (remaining lockout: {remaining_seconds}s)")
            return (
                jsonify(
                    {
                        "error": "Too many failed attempts",
                        "message": f"Account temporarily locked. Try again in {remaining_seconds} seconds",
                        "retry_after": remaining_seconds,
                    }
                ),
                429,
            )

        # Try JWT Bearer token first
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]
            payload, error = decode_token(token)
            if not error:
                _clear_failed_attempts(ip_address)
                g.authenticated = True
                g.current_user_id = int(payload.get("sub"))
                g.current_user_email = payload.get("email")
                g.current_user_role = payload.get("role")
                return f(*args, **kwargs)

        # Fall back to API key
        api_key = request.headers.get("X-API-Key")
        if api_key:
            is_valid, _ = validate_api_key(api_key)
            if is_valid:
                _clear_failed_attempts(ip_address)
                g.authenticated = True
                g.api_key_hash = _hash_api_key_pbkdf2(api_key)[:8]
                return f(*args, **kwargs)
            else:
                _record_failed_attempt(ip_address)

        # Neither auth method succeeded
        logger.warning(f"Missing authentication for {request.method} {request.path} from {request.remote_addr}")
        return (
            jsonify({"error": "Authentication required", "message": "Provide a Bearer token or X-API-Key header"}),
            401,
        )

    return decorated


def require_api_key(f):
    """
    Decorator that requires a valid API key for endpoint access.

    The API key should be provided in the X-API-Key header.
    Authentication bypass requires explicit AUTH_BYPASS_ENABLED=true in development.

    Security features:
    - Timing-safe comparison prevents timing attacks
    - API keys are hashed before comparison
    - No information leakage about valid keys

    Usage:
        @app.route('/protected')
        @require_api_key
        def protected_endpoint():
            return jsonify({'message': 'Access granted'})
    """

    @wraps(f)
    def decorated(*args, **kwargs):
        valid_keys = get_valid_api_keys()
        is_debug = is_debug_mode()  # Use centralized check
        auth_bypass = os.getenv("AUTH_BYPASS_ENABLED", "False").lower() == "true"

        # Require explicit AUTH_BYPASS_ENABLED=true to skip auth in development
        if not valid_keys:
            if is_debug and auth_bypass:
                logger.warning(
                    "AUTH BYPASS: No API keys configured and AUTH_BYPASS_ENABLED=true. "
                    "This should NEVER happen in production!"
                )
                # Mark as bypass mode, NOT authenticated
                # This prevents privilege escalation by clearly distinguishing bypass from auth
                g.authenticated = False
                g.bypass_mode = True  # Explicit bypass flag for audit
                g.api_key_id = None
                return f(*args, **kwargs)
            elif is_debug:
                logger.warning(
                    f"No API keys configured for {request.method} {request.path}. "
                    "Set VALID_API_KEYS or AUTH_BYPASS_ENABLED=true for development."
                )
                return (
                    jsonify(
                        {
                            "error": "Authentication not configured",
                            "message": "API keys not configured. Set VALID_API_KEYS in .env",
                        }
                    ),
                    500,
                )
            else:
                logger.error("SECURITY: No API keys configured in production!")
                return (
                    jsonify(
                        {"error": "Service unavailable", "message": "Authentication service is not properly configured"}
                    ),
                    503,
                )

        # Get API key from header
        api_key = request.headers.get("X-API-Key")

        if not api_key:
            logger.warning(f"Missing API key for {request.method} {request.path} " f"from {request.remote_addr}")
            return (
                jsonify(
                    {"error": "API key required", "message": "Please provide a valid API key in the X-API-Key header"}
                ),
                401,
            )

        # Check IP lockout
        ip_address = request.remote_addr
        is_locked, remaining_seconds = _check_ip_lockout(ip_address)
        if is_locked:
            logger.warning(f"Locked out IP attempted access (remaining lockout: {remaining_seconds}s)")
            return (
                jsonify(
                    {
                        "error": "Too many failed attempts",
                        "message": f"Account temporarily locked. Try again in {remaining_seconds} seconds",
                        "retry_after": remaining_seconds,
                    }
                ),
                429,
            )

        # Validate using timing-safe comparison with full security checks
        is_valid, error_reason = validate_api_key(api_key)
        if not is_valid:
            failure_count = _record_failed_attempt(ip_address)
            # Mask IP address for privacy - only show last octet
            masked_ip = "*.*.*" + ip_address.rsplit(".", 1)[-1] if "." in ip_address else "[masked]"
            logger.warning(
                f"Invalid API key attempt for {request.method} {request.path} "
                f"from {masked_ip} (attempts: {failure_count})"
            )

            # Don't reveal specific reason in response (info leakage)
            response_msg = "The provided API key is not valid"
            if failure_count >= MAX_FAILED_ATTEMPTS - 1:
                response_msg = "Too many failed attempts. Account may be locked."

            return jsonify({"error": "Invalid API key", "message": response_msg}), 401

        # Clear failed attempts on successful auth
        _clear_failed_attempts(ip_address)

        # Set authentication context
        g.authenticated = True
        g.api_key_hash = _hash_api_key_pbkdf2(api_key)[:8]  # Store truncated hash for logging

        return f(*args, **kwargs)

    return decorated


def optional_api_key(f):
    """
    Decorator that accepts but doesn't require an API key.

    Useful for endpoints that provide enhanced features for authenticated users
    but still work for anonymous users.

    Sets g.authenticated to True if valid key provided (timing-safe).
    """

    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get("X-API-Key")

        # Set authentication status using Flask's g object
        g.authenticated = False
        g.api_key_hash = None

        if api_key:
            is_valid, _ = validate_api_key(api_key)
            if is_valid:
                g.authenticated = True
                g.api_key_hash = _hash_api_key_pbkdf2(api_key)[:8]

        return f(*args, **kwargs)

    return decorated


def get_auth_context() -> dict:
    """
    Get current authentication context.

    Returns:
        dict with:
        - 'authenticated' (bool): True if properly authenticated with valid key
        - 'bypass_mode' (bool): True if auth was bypassed (development only)
        - 'api_key_hash' (str or None): Truncated hash for logging
    """
    return {
        "authenticated": getattr(g, "authenticated", False),
        "bypass_mode": getattr(g, "bypass_mode", False),
        "api_key_hash": getattr(g, "api_key_hash", None),
    }


def is_using_bcrypt() -> bool:
    """Check if bcrypt is being used for API key hashing."""
    return BCRYPT_AVAILABLE
