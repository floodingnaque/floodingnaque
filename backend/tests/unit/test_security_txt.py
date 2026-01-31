"""
Unit tests for security.txt routes.

Tests for app/api/routes/security_txt.py
"""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from app.api.routes.security_txt import get_security_txt_content


class TestSecurityTxtContent:
    """Tests for security.txt content generation."""

    def test_get_security_txt_content_default(self):
        """Test default security.txt content generation."""
        content = get_security_txt_content()

        assert "Contact:" in content
        assert "mailto:" in content
        assert "Policy:" in content
        assert "Expires:" in content

    @patch.dict(
        "os.environ",
        {
            "SECURITY_CONTACT_EMAIL": "security@test.com",
            "SECURITY_POLICY_URL": "https://test.com/policy",
        },
    )
    def test_get_security_txt_content_custom(self):
        """Test security.txt content with custom environment variables."""
        content = get_security_txt_content()

        assert "security@test.com" in content
        assert "https://test.com/policy" in content

    def test_security_txt_content_format(self):
        """Test security.txt follows RFC 9116 format."""
        content = get_security_txt_content()

        # RFC 9116 required fields
        assert "Contact:" in content
        assert "Expires:" in content

        # Comments should start with #
        lines = content.split("\n")
        for line in lines:
            if line.strip() and not any(
                line.startswith(field)
                for field in [
                    "Contact:",
                    "Expires:",
                    "Policy:",
                    "Acknowledgments:",
                    "Encryption:",
                    "Canonical:",
                    "Preferred-Languages:",
                    "Hiring:",
                ]
            ):
                # Line should be a comment or empty
                assert line.strip().startswith("#") or line.strip() == ""


class TestSecurityTxtEndpoint:
    """Tests for /.well-known/security.txt endpoint."""

    def test_security_txt_endpoint(self, client):
        """Test security.txt endpoint returns content."""
        response = client.get("/.well-known/security.txt")

        assert response.status_code == 200
        assert response.content_type == "text/plain; charset=utf-8"

    def test_security_txt_content_type(self, client):
        """Test security.txt returns correct content type."""
        response = client.get("/.well-known/security.txt")

        assert "text/plain" in response.content_type

    def test_security_txt_cache_headers(self, client):
        """Test security.txt has appropriate cache headers."""
        response = client.get("/.well-known/security.txt")

        assert response.status_code == 200
        # Should have cache control headers
        cache_control = response.headers.get("Cache-Control", "")
        assert "max-age" in cache_control or cache_control == ""

    def test_security_txt_security_headers(self, client):
        """Test security.txt has security headers."""
        response = client.get("/.well-known/security.txt")

        # Should have X-Content-Type-Options
        assert response.headers.get("X-Content-Type-Options") == "nosniff"


class TestSecurityTxtRootEndpoint:
    """Tests for /security.txt endpoint (root level)."""

    def test_security_txt_root_endpoint(self, client):
        """Test security.txt at root level."""
        response = client.get("/security.txt")

        assert response.status_code == 200
        assert "text/plain" in response.content_type

    def test_security_txt_root_same_content(self, client):
        """Test root and well-known endpoints return same content structure."""
        well_known_response = client.get("/.well-known/security.txt")
        root_response = client.get("/security.txt")

        assert well_known_response.status_code == 200
        assert root_response.status_code == 200

        # Compare content excluding the Expires line (which has a dynamic timestamp)
        # The Expires line can differ by a second between requests
        well_known_lines = [
            line for line in well_known_response.data.decode().split("\n") if not line.startswith("Expires:")
        ]
        root_lines = [line for line in root_response.data.decode().split("\n") if not line.startswith("Expires:")]
        assert well_known_lines == root_lines


class TestSecurityTxtExpiration:
    """Tests for security.txt expiration handling."""

    @patch.dict(
        "os.environ",
        {
            "SECURITY_TXT_EXPIRES": "2027-01-01T00:00:00Z",
        },
    )
    def test_custom_expiration_date(self):
        """Test custom expiration date is used."""
        content = get_security_txt_content()

        assert "2027-01-01" in content

    def test_default_expiration_is_future(self):
        """Test default expiration is at least 1 year in future."""
        content = get_security_txt_content()

        # Extract expiration date
        for line in content.split("\n"):
            if line.startswith("Expires:"):
                expires_str = line.replace("Expires:", "").strip()
                expires_date = datetime.fromisoformat(expires_str.replace("Z", "+00:00"))
                now = datetime.now(expires_date.tzinfo)
                # Should be at least 300 days in the future
                assert expires_date > now + timedelta(days=300)
                break


class TestSecurityTxtPreferredLanguages:
    """Tests for preferred languages in security.txt."""

    def test_preferred_languages_present(self):
        """Test preferred languages are included."""
        content = get_security_txt_content()

        assert "Preferred-Languages:" in content
        assert "en" in content  # English should be included


class TestSecurityTxtCanonical:
    """Tests for canonical URL in security.txt."""

    def test_canonical_url_present(self):
        """Test canonical URL is included."""
        content = get_security_txt_content()

        assert "Canonical:" in content

    @patch.dict(
        "os.environ",
        {
            "SECURITY_CANONICAL_URL": "https://custom.api.com/.well-known/security.txt",
        },
    )
    def test_custom_canonical_url(self):
        """Test custom canonical URL is used."""
        content = get_security_txt_content()

        assert "https://custom.api.com/.well-known/security.txt" in content
