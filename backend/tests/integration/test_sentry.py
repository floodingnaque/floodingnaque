"""
Quick test script to verify Sentry integration.

Run this to test Sentry without starting the full Flask app.
"""

import os
import sys

from app.core.config import load_env
from app.utils.sentry import (
    add_breadcrumb,
    capture_exception,
    capture_message,
    init_sentry,
    is_sentry_enabled,
    set_tag,
    set_user_context,
)


def test_sentry_disabled():
    """Test Sentry when DSN is not configured."""
    print("=" * 60)
    print("TEST 1: Sentry without DSN (should be disabled)")
    print("=" * 60)

    # Ensure DSN is not set
    if "SENTRY_DSN" in os.environ:
        del os.environ["SENTRY_DSN"]

    result = init_sentry()
    enabled = is_sentry_enabled()

    print(f"✓ init_sentry() returned: {result}")
    print(f"✓ is_sentry_enabled(): {enabled}")
    print("✓ Expected: False (DSN not configured)")

    if not result and not enabled:
        print("✅ PASS: Sentry correctly disabled when DSN not set\n")
        return True
    else:
        print("❌ FAIL: Sentry should be disabled\n")
        return False


def test_sentry_enabled():
    """Test Sentry with a mock DSN."""
    print("=" * 60)
    print("TEST 2: Sentry with DSN (should initialize)")
    print("=" * 60)

    # Set a test DSN (won't actually send data without valid DSN)
    os.environ["SENTRY_DSN"] = "https://test@test.ingest.sentry.io/123456"
    os.environ["SENTRY_ENVIRONMENT"] = "test"

    result = init_sentry()
    enabled = is_sentry_enabled()

    print(f"✓ init_sentry() returned: {result}")
    print(f"✓ is_sentry_enabled(): {enabled}")
    print("✓ Expected: True (DSN configured)")

    if result and enabled:
        print("✅ PASS: Sentry correctly initialized with DSN")

        # Test capture_message
        print("\nTesting capture_message...")
        event_id = capture_message("Test message from Floodingnaque", level="info")
        print(f"✓ Event ID: {event_id}")
        print("✅ PASS: Message captured (would be sent to Sentry)\n")
        return True
    else:
        print("❌ FAIL: Sentry should be enabled\n")
        return False


def test_sentry_functions():
    """Test Sentry utility functions."""
    print("=" * 60)
    print("TEST 3: Sentry utility functions")
    print("=" * 60)

    try:
        # Test breadcrumb
        add_breadcrumb(message="Test breadcrumb", category="test", level="info")
        print("✓ add_breadcrumb() - OK")

        # Test tags
        set_tag("test_tag", "test_value")
        print("✓ set_tag() - OK")

        # Test user context
        set_user_context(user_id="test_user", email="test@example.com")
        print("✓ set_user_context() - OK")

        # Test exception capture
        try:
            raise ValueError("Test exception")
        except Exception as e:
            event_id = capture_exception(e, context={"tags": {"test": "true"}, "extra": {"info": "test data"}})
            print(f"✓ capture_exception() - Event ID: {event_id}")

        print("✅ PASS: All utility functions working\n")
        return True

    except Exception as e:
        print(f"❌ FAIL: {e}\n")
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("SENTRY INTEGRATION TEST SUITE")
    print("=" * 60 + "\n")

    # Load environment
    load_env()

    # Run tests
    results = []
    results.append(test_sentry_disabled())
    results.append(test_sentry_enabled())
    results.append(test_sentry_functions())

    # Summary
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("✅ ALL TESTS PASSED")
        print("\nSentry integration is working correctly!")
        print("\nTo enable Sentry in production:")
        print("1. Sign up at https://sentry.io")
        print("2. Create a Flask project")
        print("3. Add your DSN to .env:")
        print("   SENTRY_DSN=https://your-key@your-org.ingest.sentry.io/your-project")
        print("4. Restart the application")
    else:
        print("❌ SOME TESTS FAILED")
        print("Check the output above for details")

    print("=" * 60 + "\n")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
