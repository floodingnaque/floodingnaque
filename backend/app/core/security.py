"""Security Utilities.

Provides security-related utilities for the Floodingnaque API.
Includes JWT token management for user authentication.
"""

import hashlib
import hmac
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

from app.utils.secrets import get_secret

try:
    import jwt

    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    logging.warning("PyJWT not installed. Install with: pip install PyJWT")

try:
    import bcrypt

    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False
    logging.warning("bcrypt not installed. Install with: pip install bcrypt")

logger = logging.getLogger(__name__)


def generate_secret_key(length: int = 32) -> str:
    """
    Generate a cryptographically secure secret key.

    Args:
        length: Length of the key in bytes (default: 32)

    Returns:
        str: Hex-encoded secret key
    """
    return secrets.token_hex(length)


def generate_api_key() -> str:
    """
    Generate a new API key.

    Returns:
        str: A unique API key
    """
    return f"floodingnaque_{secrets.token_urlsafe(32)}"


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key for secure storage using bcrypt.

    bcrypt is a password hashing function designed to be computationally
    expensive and resistant to rainbow table attacks.

    Args:
        api_key: The API key to hash

    Returns:
        str: bcrypt hash of the API key (or PBKDF2 fallback)
    """
    if BCRYPT_AVAILABLE:
        # bcrypt includes salt and is resistant to rainbow table attacks
        return bcrypt.hashpw(api_key.encode(), bcrypt.gensalt(rounds=12)).decode()  # type: ignore[possibly-undefined]
    else:
        # Fallback to PBKDF2-SHA256 with high iteration count
        # Security: Salt MUST be provided via environment variable
        secret_salt = os.getenv("API_KEY_HASH_SALT")
        if not secret_salt:
            raise ValueError(
                "API_KEY_HASH_SALT environment variable is required for PBKDF2 fallback. "
                "Set a secure random salt (at least 32 characters) or install bcrypt."
            )
        return hashlib.pbkdf2_hmac("sha256", api_key.encode(), secret_salt.encode(), 100000).hex()


def verify_api_key(api_key: str, hashed_key: str) -> bool:
    """
    Verify an API key against its hash.

    Args:
        api_key: The API key to verify
        hashed_key: The stored hash to compare against

    Returns:
        bool: True if the API key matches the hash
    """
    if BCRYPT_AVAILABLE:
        try:
            return bcrypt.checkpw(api_key.encode(), hashed_key.encode())  # type: ignore[possibly-undefined]
        except (ValueError, TypeError):
            return False
    else:
        # Fallback verification using PBKDF2
        # Security: Salt MUST be provided via environment variable
        secret_salt = os.getenv("API_KEY_HASH_SALT")
        if not secret_salt:
            raise ValueError(
                "API_KEY_HASH_SALT environment variable is required for PBKDF2 fallback. "
                "Set a secure random salt (at least 32 characters) or install bcrypt."
            )
        computed_hash = hashlib.pbkdf2_hmac("sha256", api_key.encode(), secret_salt.encode(), 100000).hex()
        return hmac.compare_digest(computed_hash, hashed_key)


def is_secure_password(password: str, min_length: int = 12) -> tuple:
    """
    Check if a password meets security requirements.

    Args:
        password: The password to check
        min_length: Minimum required length (default: 12)

    Returns:
        tuple: (is_valid: bool, errors: list)
    """
    errors = []

    if len(password) < min_length:
        errors.append(f"Password must be at least {min_length} characters long")

    if not any(c.isupper() for c in password):
        errors.append("Password must contain at least one uppercase letter")

    if not any(c.islower() for c in password):
        errors.append("Password must contain at least one lowercase letter")

    if not any(c.isdigit() for c in password):
        errors.append("Password must contain at least one digit")

    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        errors.append("Password must contain at least one special character")

    return (len(errors) == 0, errors)


def sanitize_input(value: str, max_length: int = 1000) -> str:
    """
    Sanitize user input to prevent injection attacks.

    Args:
        value: The input string to sanitize
        max_length: Maximum allowed length

    Returns:
        str: Sanitized string
    """
    if not value:
        return ""

    # Truncate to max length
    value = value[:max_length]

    # Remove null bytes
    value = value.replace("\x00", "")

    # Basic HTML escape (for display purposes)
    value = value.replace("&", "&amp;")
    value = value.replace("<", "&lt;")
    value = value.replace(">", "&gt;")
    value = value.replace('"', "&quot;")
    value = value.replace("'", "&#x27;")

    return value


def get_secure_headers() -> dict:
    """
    Get a dictionary of recommended security headers.

    Returns:
        dict: Security headers for HTTP responses
    """
    return {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    }


def validate_origin(origin: str, allowed_origins: list) -> bool:
    """
    Validate if an origin is in the allowed list.

    Args:
        origin: The origin to validate
        allowed_origins: List of allowed origins

    Returns:
        bool: True if origin is allowed
    """
    if not origin or not allowed_origins:
        return False

    # Normalize origin
    origin = origin.rstrip("/")

    for allowed in allowed_origins:
        allowed = allowed.rstrip("/")
        if origin == allowed:
            return True
        # Support wildcard subdomains
        if allowed.startswith("*."):
            domain = allowed[2:]
            if origin.endswith(domain) or origin.endswith("." + domain):
                return True

    return False


class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded."""


class SecurityViolation(Exception):
    """Exception raised for security violations."""


# =============================================================================
# JWT Token Management
# =============================================================================

# JWT Configuration
JWT_SECRET_KEY = get_secret("JWT_SECRET_KEY") or get_secret("SECRET_KEY", default="dev-secret-key-change-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_ACCESS_TOKEN_EXPIRES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES_MINUTES", "15"))  # 15 minutes
JWT_REFRESH_TOKEN_EXPIRES = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRES_DAYS", "7"))  # 7 days


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        str: Bcrypt hashed password
    """
    if not BCRYPT_AVAILABLE:
        raise RuntimeError("bcrypt is required for password hashing. Install with: pip install bcrypt")
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")  # type: ignore[possibly-undefined]


def verify_password(password: str, password_hash: str) -> bool:
    """
    Verify a password against its hash.

    Args:
        password: Plain text password
        password_hash: Bcrypt hash to compare against

    Returns:
        bool: True if password matches
    """
    if not BCRYPT_AVAILABLE:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))  # type: ignore[possibly-undefined]
    except (ValueError, TypeError):
        return False


def create_access_token(user_id: int, email: str, role: str = "user", expires_minutes: Optional[int] = None) -> str:
    """
    Create a JWT access token.

    Args:
        user_id: User's database ID
        email: User's email
        role: User's role (user/admin/operator)
        expires_minutes: Custom expiration in minutes

    Returns:
        str: Encoded JWT token
    """
    if not JWT_AVAILABLE:
        raise RuntimeError("PyJWT is required. Install with: pip install PyJWT")

    if expires_minutes is None:
        expires_minutes = JWT_ACCESS_TOKEN_EXPIRES

    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=expires_minutes)

    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "type": "access",
        "iat": now,
        "exp": expire,
        "jti": secrets.token_hex(16),  # Unique token ID for revocation
    }

    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)  # type: ignore[possibly-undefined]


def create_refresh_token(user_id: int, expires_days: Optional[int] = None) -> Tuple[str, str]:
    """
    Create a JWT refresh token.

    Args:
        user_id: User's database ID
        expires_days: Custom expiration in days

    Returns:
        Tuple[str, str]: (encoded token, token hash for storage)
    """
    if not JWT_AVAILABLE:
        raise RuntimeError("PyJWT is required. Install with: pip install PyJWT")

    if expires_days is None:
        expires_days = JWT_REFRESH_TOKEN_EXPIRES

    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=expires_days)
    token_id = secrets.token_hex(32)

    payload = {"sub": str(user_id), "type": "refresh", "iat": now, "exp": expire, "jti": token_id}

    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)  # type: ignore[possibly-undefined]
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    return token, token_hash


def decode_token(token: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Decode and validate a JWT token.

    Args:
        token: The JWT token to decode

    Returns:
        Tuple[payload, error]: (decoded payload, None) on success, (None, error_message) on failure
    """
    if not JWT_AVAILABLE:
        return None, "JWT support not available"

    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])  # type: ignore[possibly-undefined]
        return payload, None
    except jwt.ExpiredSignatureError:  # type: ignore[possibly-undefined]
        return None, "Token has expired"
    except jwt.InvalidTokenError as e:  # type: ignore[possibly-undefined]
        # Log detailed invalid token error server-side, but return a generic message to the client
        logger.warning("Invalid JWT token: %s", str(e))
        return None, "Invalid token"


def create_password_reset_token() -> Tuple[str, datetime]:
    """
    Create a password reset token.

    Returns:
        Tuple[str, datetime]: (token, expiration_time)
    """
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(hours=1)  # 1 hour expiry
    return token, expires


def verify_password_reset_token(stored_token: str, provided_token: str, expires_at: datetime) -> bool:
    """
    Verify a password reset token.

    Args:
        stored_token: Token stored in database
        provided_token: Token provided by user
        expires_at: Token expiration time

    Returns:
        bool: True if token is valid and not expired
    """
    if not stored_token or not provided_token:
        return False

    if datetime.now(timezone.utc) > expires_at:
        return False

    return hmac.compare_digest(stored_token, provided_token)


def is_jwt_available() -> bool:
    """Check if JWT support is available."""
    return JWT_AVAILABLE


def is_bcrypt_available() -> bool:
    """Check if bcrypt is available."""
    return BCRYPT_AVAILABLE
