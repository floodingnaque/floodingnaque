"""
Security.txt endpoint per RFC 9116.

Provides security contact information at /.well-known/security.txt
as recommended by https://securitytxt.org/

This allows security researchers to easily find contact information
when they discover vulnerabilities in the application.
"""

import os

from flask import Blueprint, Response

security_txt_bp = Blueprint("security_txt", __name__)

# Security.txt content - customize these values for your organization
SECURITY_TXT_CONTENT = """# Floodingnaque Security Information
# This file follows the security.txt standard (RFC 9116)
# https://securitytxt.org/

# Contact information for reporting security vulnerabilities
# Replace with your actual security contact email
Contact: mailto:{contact_email}

# Optional: Preferred language(s) for communication
Preferred-Languages: en, fil

# Link to security policy
Policy: {policy_url}

# Acknowledgments page for security researchers
Acknowledgments: {acknowledgments_url}

# Encryption key for secure communications (optional)
# Encryption: {{pgp_key_url}}

# Expiration date for this file (should be renewed annually)
Expires: {expires}

# Canonical URL for this file
Canonical: {canonical_url}

# Optional: Hiring page for security professionals
# Hiring: {{hiring_url}}
"""


def get_security_txt_content() -> str:
    """
    Generate security.txt content from environment variables.

    Environment variables:
    - SECURITY_CONTACT_EMAIL: Email for security reports
    - SECURITY_POLICY_URL: Link to security policy
    - SECURITY_ACKNOWLEDGMENTS_URL: Link to hall of fame
    - SECURITY_PGP_KEY_URL: Optional PGP key URL
    - SECURITY_TXT_EXPIRES: Expiration date (ISO 8601 format)
    - SECURITY_CANONICAL_URL: Canonical URL for this file
    """
    from datetime import datetime, timedelta, timezone

    # Default expiration is 1 year from now
    default_expires = (datetime.now(timezone.utc) + timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%SZ")

    contact_email = os.getenv("SECURITY_CONTACT_EMAIL", "security@floodingnaque.com")
    policy_url = os.getenv("SECURITY_POLICY_URL", "https://floodingnaque.com/security-policy")
    acknowledgments_url = os.getenv("SECURITY_ACKNOWLEDGMENTS_URL", "https://floodingnaque.com/security/thanks")
    expires = os.getenv("SECURITY_TXT_EXPIRES", default_expires)
    canonical_url = os.getenv("SECURITY_CANONICAL_URL", "https://api.floodingnaque.com/.well-known/security.txt")

    content = SECURITY_TXT_CONTENT.format(
        contact_email=contact_email,
        policy_url=policy_url,
        acknowledgments_url=acknowledgments_url,
        expires=expires,
        canonical_url=canonical_url,
    )

    return content


@security_txt_bp.route("/.well-known/security.txt", methods=["GET"])
def security_txt():
    """
    Serve security.txt file per RFC 9116.

    This endpoint provides security contact information for researchers
    who discover vulnerabilities in the application.
    """
    content = get_security_txt_content()
    return Response(
        content,
        mimetype="text/plain",
        headers={"Cache-Control": "public, max-age=86400", "X-Content-Type-Options": "nosniff"},  # Cache for 1 day
    )


@security_txt_bp.route("/security.txt", methods=["GET"])
def security_txt_root():
    """
    Also serve security.txt at root for compatibility.
    """
    content = get_security_txt_content()
    return Response(
        content,
        mimetype="text/plain",
        headers={"Cache-Control": "public, max-age=86400", "X-Content-Type-Options": "nosniff"},
    )
