"""
Admin user management routes.

Endpoints for admin-level user operations:
  POST /api/v1/admin/users/<id>/activate    — Activate user
  POST /api/v1/admin/users/<id>/deactivate  — Deactivate user
  POST /api/v1/admin/users/<id>/role        — Change user role
  GET  /api/v1/admin/users/stats            — User statistics
"""

import logging

from flask import Blueprint, jsonify, request

from shared.auth import require_role

logger = logging.getLogger(__name__)

admin_bp = Blueprint("admin_users", __name__)


@admin_bp.route("/<int:user_id>/activate", methods=["POST"])
@require_role("admin")
def activate_user(user_id):
    """Activate a user account."""
    try:
        from app.services.user_service import UserService
        service = UserService()
        service.set_active(user_id, True)
        return jsonify({"success": True, "message": f"User {user_id} activated"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@admin_bp.route("/<int:user_id>/deactivate", methods=["POST"])
@require_role("admin")
def deactivate_user(user_id):
    """Deactivate a user account."""
    try:
        from app.services.user_service import UserService
        service = UserService()
        service.set_active(user_id, False)
        return jsonify({"success": True, "message": f"User {user_id} deactivated"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@admin_bp.route("/<int:user_id>/role", methods=["POST"])
@require_role("admin")
def change_role(user_id):
    """Change a user's role."""
    data = request.get_json()
    role = data.get("role") if data else None
    if role not in ("user", "admin", "operator"):
        return jsonify({"success": False, "error": "Valid role required (user/admin/operator)"}), 400

    try:
        from app.services.user_service import UserService
        service = UserService()
        service.update_user(user_id, {"role": role})
        return jsonify({"success": True, "message": f"User {user_id} role changed to {role}"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@admin_bp.route("/stats", methods=["GET"])
@require_role("admin")
def user_stats():
    """Get user registration and activity statistics."""
    try:
        from app.services.user_service import UserService
        service = UserService()
        stats = service.get_stats()
        return jsonify({"success": True, "stats": stats})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
