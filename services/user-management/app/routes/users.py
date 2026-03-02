"""
User profile routes.

Endpoints:
  GET    /api/v1/users/          - List users (admin only)
  GET    /api/v1/users/<id>      - Get user profile
  PUT    /api/v1/users/<id>      - Update user profile
  DELETE /api/v1/users/<id>      - Soft-delete user
"""

import logging

from flask import Blueprint, jsonify, request

from shared.auth import require_auth, require_role

logger = logging.getLogger(__name__)

users_bp = Blueprint("users", __name__)


@users_bp.route("/", methods=["GET"])
@require_role("admin")
def list_users():
    """List all users (admin only)."""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    role = request.args.get("role")

    try:
        from app.services.user_service import UserService
        service = UserService()
        result = service.list_users(page=page, per_page=per_page, role=role)
        return jsonify({"success": True, **result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@users_bp.route("/<int:user_id>", methods=["GET"])
@require_auth
def get_user(user_id):
    """Get user profile by ID."""
    from flask import g

    # Users can only view their own profile; admins can view any
    if g.current_user["id"] != user_id and g.current_user["role"] != "admin":
        return jsonify({"success": False, "error": "Access denied"}), 403

    try:
        from app.services.user_service import UserService
        service = UserService()
        user = service.get_user(user_id)
        if not user:
            return jsonify({"success": False, "error": "User not found"}), 404
        return jsonify({"success": True, "user": user})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@users_bp.route("/<int:user_id>", methods=["PUT"])
@require_auth
def update_user(user_id):
    """Update user profile."""
    from flask import g

    if g.current_user["id"] != user_id and g.current_user["role"] != "admin":
        return jsonify({"success": False, "error": "Access denied"}), 403

    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "Request body required"}), 400

    # Non-admins cannot change their own role
    if g.current_user["role"] != "admin" and "role" in data:
        del data["role"]

    try:
        from app.services.user_service import UserService
        service = UserService()
        user = service.update_user(user_id, data)
        return jsonify({"success": True, "user": user})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@users_bp.route("/<int:user_id>", methods=["DELETE"])
@require_auth
def delete_user(user_id):
    """Soft-delete a user account."""
    from flask import g

    if g.current_user["id"] != user_id and g.current_user["role"] != "admin":
        return jsonify({"success": False, "error": "Access denied"}), 403

    try:
        from app.services.user_service import UserService
        service = UserService()
        service.delete_user(user_id)
        return jsonify({"success": True, "message": "User deleted"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
