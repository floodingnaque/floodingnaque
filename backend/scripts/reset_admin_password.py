#!/usr/bin/env python3
"""Reset or create the admin user account.

Usage:
    python -m scripts.reset_admin_password
    python -m scripts.reset_admin_password --email admin@floodingnaque.com --password "NewSecurePass123!"
"""

import argparse
import sys
from pathlib import Path

# Ensure backend root is on sys.path
backend_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_root))

from app.core.security import hash_password, is_secure_password  # noqa: E402
from app.models.db import get_db_session  # noqa: E402
from app.models.user import User  # noqa: E402

DEFAULT_EMAIL = "admin@floodingnaque.com"
DEFAULT_PASSWORD = "Admin_floodingnaque_2025!"


def main() -> None:
    parser = argparse.ArgumentParser(description="Reset or create the admin user.")
    parser.add_argument("--email", default=DEFAULT_EMAIL, help="Admin email address")
    parser.add_argument("--password", default=DEFAULT_PASSWORD, help="New password")
    args = parser.parse_args()

    # Validate password strength
    ok, errors = is_secure_password(args.password)
    if not ok:
        print("Password does not meet requirements:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    password_hash = hash_password(args.password)

    with get_db_session() as session:
        user = session.query(User).filter(User.email == args.email).first()

        if user:
            user.password_hash = password_hash
            user.failed_login_attempts = 0
            user.locked_until = None
            user.is_active = True
            user.is_deleted = False
            print(f"Password reset for existing user: {args.email}")
        else:
            user = User(
                email=args.email,
                password_hash=password_hash,
                full_name="Admin",
                role="admin",
                is_active=True,
                is_verified=True,
            )
            session.add(user)
            print(f"Created new admin user: {args.email}")

    print(f"Login with:  email={args.email}  password={args.password}")


if __name__ == "__main__":
    main()
