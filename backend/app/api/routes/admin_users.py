"""
Admin User Management Routes.

Provides admin-only CRUD endpoints for managing user accounts,
roles, and access control. All routes require admin authentication.
"""

import logging
import secrets as _secrets
import string as _string
from functools import wraps

from app.api.middleware.auth import require_auth
from app.core.security import hash_password
from app.models.db import User, get_db_session
from app.utils.api_constants import (
    HTTP_BAD_REQUEST,
    HTTP_CONFLICT,
    HTTP_CREATED,
    HTTP_FORBIDDEN,
    HTTP_NOT_FOUND,
    HTTP_OK,
)
from app.utils.api_responses import api_error
from flask import Blueprint, g, jsonify, request

logger = logging.getLogger(__name__)

admin_users_bp = Blueprint("admin_users", __name__)

VALID_ROLES = {"user", "admin", "operator"}


def _generate_temp_password() -> str:
    """Generate a secure 16-char temporary password meeting all complexity rules."""
    alphabet = _string.ascii_letters + _string.digits + "!@#$%^&*"
    while True:
        temp_password = "".join(_secrets.choice(alphabet) for _ in range(16))
        if (
            any(c.isupper() for c in temp_password)
            and any(c.islower() for c in temp_password)
            and any(c.isdigit() for c in temp_password)
            and any(c in "!@#$%^&*" for c in temp_password)
        ):
            return temp_password


def require_admin(f):
    """Decorator that requires admin role after authentication."""

    @wraps(f)
    @require_auth
    def decorated(*args, **kwargs):
        if getattr(g, "current_user_role", None) != "admin":
            return api_error("Admin access required", HTTP_FORBIDDEN, code="ADMIN_REQUIRED")
        return f(*args, **kwargs)

    return decorated


@admin_users_bp.route("/", methods=["GET"])
@require_admin
def list_users():
    """
    List all users with optional filtering and pagination.

    Query Parameters:
        page (int): Page number (default 1)
        per_page (int): Items per page (default 20, max 100)
        role (str): Filter by role (user/admin/operator)
        status (str): Filter by status (active/suspended/deleted)
        search (str): Search by email or name
        sort_by (str): Sort field (created_at/email/role/last_login_at)
        order (str): Sort order (asc/desc)

    Returns:
        200: Paginated user list
    """
    try:
        with get_db_session() as session:
            page = max(1, request.args.get("page", 1, type=int))
            per_page = min(100, max(1, request.args.get("per_page", 20, type=int)))
            role_filter = request.args.get("role")
            status_filter = request.args.get("status")
            search = request.args.get("search", "").strip()
            sort_by = request.args.get("sort_by", "created_at")
            order = request.args.get("order", "desc")

            query = session.query(User).filter(User.is_deleted == False)  # noqa: E712

            # Role filter
            if role_filter and role_filter in VALID_ROLES:
                query = query.filter(User.role == role_filter)

            # Status filter
            if status_filter == "active":
                query = query.filter(User.is_active == True)  # noqa: E712
            elif status_filter == "suspended":
                query = query.filter(User.is_active == False)  # noqa: E712

            # Search
            if search:
                search_pattern = f"%{search}%"
                query = query.filter((User.email.ilike(search_pattern)) | (User.full_name.ilike(search_pattern)))

            # Sort
            sort_column = getattr(User, sort_by, User.created_at)
            if order == "asc":
                query = query.order_by(sort_column.asc())
            else:
                query = query.order_by(sort_column.desc())

            # Paginate
            total = query.count()
            users = query.offset((page - 1) * per_page).limit(per_page).all()

            return (
                jsonify(
                    {
                        "success": True,
                        "data": [u.to_dict(include_sensitive=True) for u in users],
                        "pagination": {
                            "page": page,
                            "per_page": per_page,
                            "total": total,
                            "total_pages": (total + per_page - 1) // per_page,
                        },
                    }
                ),
                HTTP_OK,
            )
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        return api_error(f"Failed to list users: {str(e)}", 500)


@admin_users_bp.route("/", methods=["POST"])
@require_admin
def create_user():
    """
    Create a new user account (admin-initiated).

    Request Body:
        { "email": str, "name": str (optional), "role": "user"|"operator"|"admin" }

    Returns:
        201: Created user with temporary password
    """
    try:
        data = request.get_json(silent=True) or {}
        email = (data.get("email") or "").strip().lower()
        full_name = (data.get("name") or "").strip()
        role = (data.get("role") or "user").strip()

        if not email:
            return api_error("Email is required", HTTP_BAD_REQUEST)
        if role not in VALID_ROLES:
            return api_error(f"Invalid role. Must be one of: {', '.join(VALID_ROLES)}", HTTP_BAD_REQUEST)

        with get_db_session() as session:
            existing = session.query(User).filter(User.email == email).first()
            if existing:
                return api_error("A user with this email already exists", HTTP_CONFLICT)

            temp_password = _generate_temp_password()
            user = User(
                email=email,
                full_name=full_name or None,
                role=role,
                password_hash=hash_password(temp_password),
                is_active=True,
                is_verified=True,
            )
            session.add(user)
            session.flush()

            logger.info(f"Admin {g.current_user_email} created user {email} with role {role}")

            return (
                jsonify(
                    {
                        "success": True,
                        "data": user.to_dict(include_sensitive=True),
                        "temporary_password": temp_password,
                        "message": f"User {email} created successfully",
                    }
                ),
                HTTP_CREATED,
            )
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        return api_error(f"Failed to create user: {str(e)}", 500)


@admin_users_bp.route("/<int:user_id>", methods=["GET"])
@require_admin
def get_user(user_id: int):
    """Get a single user by ID."""
    try:
        with get_db_session() as session:
            user = session.query(User).filter(User.id == user_id, User.is_deleted == False).first()  # noqa: E712
            if not user:
                return api_error("User not found", HTTP_NOT_FOUND)
            return jsonify({"success": True, "data": user.to_dict(include_sensitive=True)}), HTTP_OK
    except Exception as e:
        logger.error(f"Error fetching user {user_id}: {e}")
        return api_error(f"Failed to fetch user: {str(e)}", 500)


@admin_users_bp.route("/<int:user_id>/role", methods=["PATCH"])
@require_admin
def update_user_role(user_id: int):
    """
    Update a user's role.

    Request Body:
        { "role": "user" | "operator" | "admin" }
    """
    try:
        with get_db_session() as session:
            data = request.get_json(silent=True) or {}
            new_role = data.get("role")
            if not new_role or new_role not in VALID_ROLES:
                return api_error(f"Invalid role. Must be one of: {', '.join(VALID_ROLES)}", HTTP_BAD_REQUEST)

            user = session.query(User).filter(User.id == user_id, User.is_deleted == False).first()  # noqa: E712
            if not user:
                return api_error("User not found", HTTP_NOT_FOUND)

            # Prevent self-demotion
            if user_id == g.current_user_id and new_role != "admin":
                return api_error("Cannot change your own admin role", HTTP_BAD_REQUEST)

            old_role = user.role
            user.role = new_role

            logger.info(f"Admin {g.current_user_email} changed user {user.email} role: {old_role} -> {new_role}")
            return (
                jsonify(
                    {
                        "success": True,
                        "message": f"Role updated to {new_role}",
                        "data": user.to_dict(),
                    }
                ),
                HTTP_OK,
            )
    except Exception as e:
        logger.error(f"Error updating user role: {e}")
        return api_error(f"Failed to update role: {str(e)}", 500)


@admin_users_bp.route("/<int:user_id>/status", methods=["PATCH"])
@require_admin
def toggle_user_status(user_id: int):
    """Toggle user active/suspended status."""
    try:
        with get_db_session() as session:
            user = session.query(User).filter(User.id == user_id, User.is_deleted == False).first()  # noqa: E712
            if not user:
                return api_error("User not found", HTTP_NOT_FOUND)

            # Prevent self-suspension
            if user_id == g.current_user_id:
                return api_error("Cannot suspend your own account", HTTP_BAD_REQUEST)

            user.is_active = not user.is_active

            status = "activated" if user.is_active else "suspended"
            logger.info(f"Admin {g.current_user_email} {status} user {user.email}")
            return (
                jsonify(
                    {
                        "success": True,
                        "message": f"User {status}",
                        "data": user.to_dict(),
                    }
                ),
                HTTP_OK,
            )
    except Exception as e:
        logger.error(f"Error toggling user status: {e}")
        return api_error(f"Failed to toggle status: {str(e)}", 500)


@admin_users_bp.route("/<int:user_id>/reset-password", methods=["POST"])
@require_admin
def admin_reset_password(user_id: int):
    """Trigger a password reset for the user (admin-initiated)."""
    try:
        with get_db_session() as session:
            user = session.query(User).filter(User.id == user_id, User.is_deleted == False).first()  # noqa: E712
            if not user:
                return api_error("NotFound", "User not found", HTTP_NOT_FOUND)

            temp_password = _generate_temp_password()
            user.password_hash = hash_password(temp_password)
            logger.info(f"Admin {g.current_user_email} reset password for {user.email}")

            return (
                jsonify(
                    {
                        "success": True,
                        "message": f"Password reset for {user.email}",
                        "temporary_password": temp_password,
                    }
                ),
                HTTP_OK,
            )
    except Exception as e:
        logger.error(f"Error resetting password for user {user_id}: {e}")
        return api_error("ResetPasswordFailed", f"Failed to reset password: {str(e)}", 500)


@admin_users_bp.route("/<int:user_id>", methods=["DELETE"])
@require_admin
def delete_user(user_id: int):
    """Soft-delete a user account."""
    try:
        with get_db_session() as session:
            user = session.query(User).filter(User.id == user_id, User.is_deleted == False).first()  # noqa: E712
            if not user:
                return api_error("User not found", HTTP_NOT_FOUND)

            # Prevent self-deletion
            if user_id == g.current_user_id:
                return api_error("Cannot delete your own account", HTTP_BAD_REQUEST)

            user.soft_delete()

            logger.info(f"Admin {g.current_user_email} deleted user {user.email}")
            return (
                jsonify(
                    {
                        "success": True,
                        "message": f"User {user.email} deleted",
                    }
                ),
                HTTP_OK,
            )
    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {e}")
        return api_error(f"Failed to delete user: {str(e)}", 500)
