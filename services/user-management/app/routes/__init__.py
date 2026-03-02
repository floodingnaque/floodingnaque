"""Routes package for User Management Service."""

from app.routes.admin import admin_bp
from app.routes.auth import auth_bp
from app.routes.users import users_bp

__all__ = ["auth_bp", "users_bp", "admin_bp"]
