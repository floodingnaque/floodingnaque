"""
Content Security Policy (CSP) Violation Reporting Endpoint.

Receives CSP violation reports from browsers and logs them for security monitoring.
This allows you to monitor and analyze CSP violations without using external services.

CSP reports are sent by browsers when a resource violates the Content-Security-Policy.
"""

import json
import logging
from datetime import datetime, timezone

from app.api.middleware import limiter
from flask import Blueprint, Response, jsonify, request

# Create a dedicated logger for CSP reports
csp_logger = logging.getLogger("csp_violations")
csp_logger.setLevel(logging.WARNING)

# Also log to main logger for visibility
logger = logging.getLogger(__name__)

csp_report_bp = Blueprint("csp_report", __name__)


@csp_report_bp.route("/csp-report", methods=["POST", "OPTIONS"])
@limiter.limit("100 per minute")  # Prevent abuse
def csp_report():
    """
    Receive and log CSP violation reports.

    Browsers send reports in the following format:
    {
        "csp-report": {
            "document-uri": "https://example.com/page",
            "referrer": "",
            "violated-directive": "script-src",
            "effective-directive": "script-src",
            "original-policy": "...",
            "disposition": "enforce",
            "blocked-uri": "https://evil.com/script.js",
            "line-number": 10,
            "column-number": 5,
            "source-file": "https://example.com/page",
            "status-code": 200,
            "script-sample": ""
        }
    }

    Returns:
        204 No Content on success (browsers expect this)
    """
    # Handle CORS preflight
    if request.method == "OPTIONS":
        return Response(
            status=204,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST",
                "Access-Control-Allow-Headers": "Content-Type",
            },
        )

    try:
        # CSP reports come as application/csp-report or application/json
        content_type = request.content_type or ""

        if "application/csp-report" in content_type or "application/json" in content_type:
            report_data = request.get_json(force=True, silent=True)
        else:
            # Try to parse as JSON anyway
            report_data = request.get_json(force=True, silent=True)

        if not report_data:
            logger.debug("Received empty CSP report")
            return Response(status=204)

        # Extract the CSP report (can be nested under 'csp-report' key)
        csp_report_data = report_data.get("csp-report", report_data)

        # Create structured log entry
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": "csp_violation",
            "client_ip": request.headers.get("X-Forwarded-For", request.remote_addr),
            "user_agent": request.headers.get("User-Agent", "unknown"),
            "report": {
                "document_uri": csp_report_data.get("document-uri", "unknown"),
                "referrer": csp_report_data.get("referrer", ""),
                "violated_directive": csp_report_data.get("violated-directive", "unknown"),
                "effective_directive": csp_report_data.get("effective-directive", "unknown"),
                "blocked_uri": csp_report_data.get("blocked-uri", "unknown"),
                "disposition": csp_report_data.get("disposition", "unknown"),
                "status_code": csp_report_data.get("status-code", 0),
                "source_file": csp_report_data.get("source-file", ""),
                "line_number": csp_report_data.get("line-number", 0),
                "column_number": csp_report_data.get("column-number", 0),
                "script_sample": csp_report_data.get("script-sample", "")[:200],  # Limit sample size
            },
        }

        # Log the violation
        csp_logger.warning(
            f"CSP Violation: {log_entry['report']['violated_directive']} - "
            f"Blocked: {log_entry['report']['blocked_uri']} - "
            f"On: {log_entry['report']['document_uri']}"
        )

        # Also log full details for debugging (at debug level)
        logger.debug(f"Full CSP report: {json.dumps(log_entry)}")

        # Check for common false positives and filter them
        blocked_uri = log_entry["report"]["blocked_uri"]
        if _is_known_false_positive(blocked_uri):
            logger.debug(f"Filtered known false positive: {blocked_uri}")
            return Response(status=204)

        # Log to file or send to monitoring system
        _store_csp_report(log_entry)

        # Return 204 No Content (browsers expect this)
        return Response(status=204)

    except Exception as e:
        logger.error(f"Error processing CSP report: {e}")
        # Still return 204 to not break browser behavior
        return Response(status=204)


@csp_report_bp.route("/csp-report/report-to", methods=["POST", "OPTIONS"])
@limiter.limit("100 per minute")
def csp_report_to():
    """
    Handle Report-To API reports (newer reporting standard).

    The Report-To API sends reports in a different format:
    [
        {
            "type": "csp-violation",
            "age": 10,
            "url": "https://example.com/page",
            "user_agent": "...",
            "body": {
                "documentURL": "https://example.com/page",
                "disposition": "enforce",
                "effectiveDirective": "script-src",
                ...
            }
        }
    ]
    """
    if request.method == "OPTIONS":
        return Response(
            status=204,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST",
                "Access-Control-Allow-Headers": "Content-Type",
            },
        )

    try:
        reports = request.get_json(force=True, silent=True) or []

        if not isinstance(reports, list):
            reports = [reports]

        for report in reports:
            report_type = report.get("type", "unknown")

            if report_type == "csp-violation":
                body = report.get("body", {})

                log_entry = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "type": "csp_violation_report_to",
                    "age_ms": report.get("age", 0),
                    "url": report.get("url", "unknown"),
                    "report": {
                        "document_url": body.get("documentURL", "unknown"),
                        "disposition": body.get("disposition", "unknown"),
                        "effective_directive": body.get("effectiveDirective", "unknown"),
                        "blocked_url": body.get("blockedURL", "unknown"),
                        "source_file": body.get("sourceFile", ""),
                        "line_number": body.get("lineNumber", 0),
                        "column_number": body.get("columnNumber", 0),
                    },
                }

                csp_logger.warning(
                    f"CSP Violation (Report-To): {log_entry['report']['effective_directive']} - "
                    f"Blocked: {log_entry['report']['blocked_url']}"
                )

                _store_csp_report(log_entry)

        return Response(status=204)

    except Exception as e:
        logger.error(f"Error processing Report-To: {e}")
        return Response(status=204)


def _is_known_false_positive(blocked_uri: str) -> bool:
    """
    Check if a blocked URI is a known false positive.

    Browser extensions and certain legitimate scripts can trigger
    CSP violations that are not security concerns.
    """
    false_positive_patterns = [
        "chrome-extension://",
        "moz-extension://",
        "safari-extension://",
        "ms-browser-extension://",
        "about:",
        "data:application/x-font",  # Font loading quirks
        "blob:",  # Often legitimate
    ]

    for pattern in false_positive_patterns:
        if blocked_uri.startswith(pattern):
            return True

    return False


def _store_csp_report(log_entry: dict):
    """
    Store CSP report for later analysis.

    Options:
    1. Log to file (current implementation)
    2. Store in database
    3. Send to monitoring service (Sentry, Datadog, etc.)
    4. Send alert for critical violations
    """
    import os

    # Option 1: Log to dedicated file
    log_file = os.getenv("CSP_REPORT_LOG_FILE", "logs/csp_violations.log")

    try:
        # Ensure logs directory exists
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")

    except Exception as e:
        logger.error(f"Failed to write CSP report to file: {e}")

    # Option 2: Send to Sentry (if configured)
    sentry_dsn = os.getenv("SENTRY_DSN")
    if sentry_dsn:
        try:
            import sentry_sdk

            sentry_sdk.capture_message(
                f"CSP Violation: {log_entry['report'].get('violated_directive', 'unknown')}",
                level="warning",
                extras=log_entry,
            )
        except Exception as sentry_err:  # nosec B110
            logger.debug("Failed to forward CSP violation to Sentry: %s", sentry_err)

    # Option 3: Check for critical violations and alert
    critical_directives = ["script-src", "object-src", "base-uri"]
    violated = log_entry["report"].get("violated_directive", "")

    if any(directive in violated for directive in critical_directives):
        logger.warning(f"CRITICAL CSP VIOLATION: {violated} - " f"This may indicate an XSS attempt or misconfiguration")


# Summary endpoint for monitoring
@csp_report_bp.route("/csp-report/summary", methods=["GET"])
@limiter.limit("10 per minute")
def csp_report_summary():
    """
    Get a summary of recent CSP violations.

    Protected endpoint - should be accessed with authentication in production.
    """
    import os
    from collections import Counter

    log_file = os.getenv("CSP_REPORT_LOG_FILE", "logs/csp_violations.log")

    if not os.path.exists(log_file):
        return jsonify({"success": True, "message": "No CSP violations recorded", "violations": [], "summary": {}})

    try:
        violations = []
        directive_counts = Counter()
        blocked_uri_counts = Counter()

        with open(log_file, "r") as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    violations.append(entry)

                    report = entry.get("report", {})
                    directive = report.get("violated_directive") or report.get("effective_directive", "unknown")
                    blocked = report.get("blocked_uri") or report.get("blocked_url", "unknown")

                    directive_counts[directive] += 1
                    blocked_uri_counts[blocked] += 1
                except json.JSONDecodeError:
                    continue

        # Return last 100 violations and summary
        return jsonify(
            {
                "success": True,
                "total_violations": len(violations),
                "recent_violations": violations[-100:],
                "summary": {
                    "by_directive": dict(directive_counts.most_common(10)),
                    "by_blocked_uri": dict(blocked_uri_counts.most_common(10)),
                },
            }
        )

    except Exception as e:
        logger.error(f"Error reading CSP report summary: {e}")
        return jsonify({"success": False, "error": "Failed to read CSP reports"}), 500
