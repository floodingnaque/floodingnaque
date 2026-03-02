"""
User Service - Core user management logic.

Handles user CRUD, authentication, password hashing,
and JWT token lifecycle.
"""

import hashlib
import logging
import os
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from shared.auth import create_access_token, create_refresh_token, verify_token

logger = logging.getLogger(__name__)

try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False
    logger.warning("bcrypt not available - using SHA-256 fallback")


class UserService:
    """
    User management service.

    In the microservices architecture, this is the single source
    of truth for all user-related operations. Other services
    verify tokens locally but defer user data lookups here.
    """

    def __init__(self):
        # In-memory store for development; replace with DB in production
        self._users: Dict[int, Dict] = {}
        self._next_id = 1
        self._lock = threading.Lock()

    def register(self, email: str, password: str, full_name: str = None,
                 phone_number: str = None) -> Dict[str, Any]:
        """
        Register a new user.

        Args:
            email: User email (must be unique)
            password: Plain-text password (hashed before storage)
            full_name: Optional full name
            phone_number: Optional phone number

        Returns:
            Registration result with user data and tokens

        Raises:
            ValueError: If email already exists
        """
        # Check for existing email
        for user in self._users.values():
            if user["email"] == email:
                raise ValueError("Email already registered")

        # Validate password strength
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters")

        with self._lock:
            user_id = self._next_id
            self._next_id += 1

        password_hash = self._hash_password(password)

        user = {
            "id": user_id,
            "email": email,
            "password_hash": password_hash,
            "full_name": full_name,
            "phone_number": phone_number,
            "role": "user",
            "is_active": True,
            "is_verified": False,
            "created_at": datetime.now(timezone.utc).isoformat() + "Z",
            "last_login_at": None,
        }

        self._users[user_id] = user

        # Generate tokens
        access_token = create_access_token(user_id, email, "user")
        refresh_token = create_refresh_token(user_id)

        logger.info("User registered: %s (id=%d)", email, user_id)

        return {
            "user": self._sanitize_user(user),
            "access_token": access_token,
            "refresh_token": refresh_token,
        }

    def login(self, email: str, password: str, ip_address: str = None) -> Optional[Dict]:
        """
        Authenticate user and return tokens.

        Returns None if credentials are invalid.
        """
        user = self._find_by_email(email)
        if not user:
            return None

        if not user.get("is_active", True):
            return None

        if not self._verify_password(password, user["password_hash"]):
            return None

        # Update last login
        user["last_login_at"] = datetime.now(timezone.utc).isoformat() + "Z"
        if ip_address:
            user["last_login_ip"] = ip_address

        access_token = create_access_token(user["id"], user["email"], user["role"])
        refresh_token = create_refresh_token(user["id"])

        logger.info("User logged in: %s", email)

        return {
            "user": self._sanitize_user(user),
            "access_token": access_token,
            "refresh_token": refresh_token,
        }

    def logout(self, token: str):
        """Invalidate a token (in production, add to blacklist)."""
        logger.info("User token invalidated")

    def refresh_access_token(self, refresh_token: str) -> Optional[Dict]:
        """Issue new access token using a valid refresh token."""
        is_valid, payload = verify_token(refresh_token)
        if not is_valid or payload.get("type") != "refresh":
            return None

        user_id = int(payload["sub"])
        user = self._users.get(user_id)
        if not user:
            return None

        new_access = create_access_token(user["id"], user["email"], user["role"])
        return {"access_token": new_access}

    def get_user(self, user_id: int) -> Optional[Dict]:
        """Get user by ID."""
        user = self._users.get(user_id)
        return self._sanitize_user(user) if user else None

    def update_user(self, user_id: int, data: Dict) -> Dict:
        """Update user profile fields."""
        user = self._users.get(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        allowed = {"full_name", "phone_number", "role"}
        for key, value in data.items():
            if key in allowed:
                user[key] = value

        user["updated_at"] = datetime.now(timezone.utc).isoformat() + "Z"
        return self._sanitize_user(user)

    def delete_user(self, user_id: int):
        """Soft-delete a user."""
        user = self._users.get(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        user["is_active"] = False
        user["is_deleted"] = True
        user["deleted_at"] = datetime.now(timezone.utc).isoformat() + "Z"

    def set_active(self, user_id: int, active: bool):
        """Activate or deactivate a user."""
        user = self._users.get(user_id)
        if user:
            user["is_active"] = active

    def change_password(self, user_id: int, current_password: str, new_password: str):
        """Change user password."""
        user = self._users.get(user_id)
        if not user:
            raise ValueError("User not found")

        if not self._verify_password(current_password, user["password_hash"]):
            raise ValueError("Current password is incorrect")

        if len(new_password) < 8:
            raise ValueError("New password must be at least 8 characters")

        user["password_hash"] = self._hash_password(new_password)
        logger.info("Password changed for user %d", user_id)

    def list_users(self, page: int = 1, per_page: int = 20, role: str = None) -> Dict:
        """List users with pagination."""
        users = list(self._users.values())
        if role:
            users = [u for u in users if u.get("role") == role]

        users = [u for u in users if not u.get("is_deleted")]
        start = (page - 1) * per_page
        end = start + per_page

        return {
            "users": [self._sanitize_user(u) for u in users[start:end]],
            "total": len(users),
            "page": page,
            "per_page": per_page,
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get user statistics."""
        users = [u for u in self._users.values() if not u.get("is_deleted")]
        return {
            "total_users": len(users),
            "active_users": sum(1 for u in users if u.get("is_active")),
            "by_role": {
                "user": sum(1 for u in users if u.get("role") == "user"),
                "admin": sum(1 for u in users if u.get("role") == "admin"),
                "operator": sum(1 for u in users if u.get("role") == "operator"),
            },
        }

    def _find_by_email(self, email: str) -> Optional[Dict]:
        """Find user by email."""
        for user in self._users.values():
            if user["email"] == email and not user.get("is_deleted"):
                return user
        return None

    def _hash_password(self, password: str) -> str:
        """Hash a password using bcrypt (or SHA-256 fallback)."""
        if BCRYPT_AVAILABLE:
            return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        return hashlib.sha256(password.encode()).hexdigest()

    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against stored hash."""
        if BCRYPT_AVAILABLE:
            try:
                return bcrypt.checkpw(password.encode(), password_hash.encode())
            except Exception:
                pass
        return hashlib.sha256(password.encode()).hexdigest() == password_hash

    def _sanitize_user(self, user: Dict) -> Dict:
        """Remove sensitive fields from user dict."""
        return {
            "id": user["id"],
            "email": user["email"],
            "full_name": user.get("full_name"),
            "name": user.get("full_name") or "",
            "role": user.get("role", "user"),
            "is_active": user.get("is_active", True),
            "is_verified": user.get("is_verified", False),
            "created_at": user.get("created_at"),
            "last_login_at": user.get("last_login_at"),
        }
