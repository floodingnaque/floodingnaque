"""
ML Stack Version Validation for Floodingnaque.

Ensures runtime ML library versions match training environment versions
to prevent model loading failures and prediction inconsistencies.

Usage:
    from app.utils.ml_version_check import validate_ml_versions, get_ml_version_report

    # At startup
    warnings = validate_ml_versions()
    if warnings:
        for warning in warnings:
            logger.warning(warning)

    # For diagnostics
    report = get_ml_version_report()
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from packaging import version as pkg_version

logger = logging.getLogger(__name__)

# =============================================================================
# PINNED ML STACK VERSIONS
# =============================================================================
# These versions MUST match requirements.txt
# Update these when upgrading the ML stack (requires model retraining)
PINNED_VERSIONS: Dict[str, str] = {
    "numpy": "2.1.3",
    "pandas": "2.2.3",
    "scikit-learn": "1.8.0",
    "joblib": "1.4.2",
    "scipy": "1.14.1",
}

# Version compatibility modes
VERSION_CHECK_STRICT = "strict"  # Exact match required
VERSION_CHECK_MINOR = "minor"  # Major.minor must match (e.g., 1.5.x)
VERSION_CHECK_MAJOR = "major"  # Major version must match (e.g., 1.x.x)

# Per-package compatibility mode
PACKAGE_COMPATIBILITY_MODE: Dict[str, str] = {
    "numpy": VERSION_CHECK_MINOR,  # Array format stability
    "pandas": VERSION_CHECK_MINOR,  # DataFrame structure
    "scikit-learn": VERSION_CHECK_STRICT,  # Model pickle format
    "joblib": VERSION_CHECK_STRICT,  # Serialization format
    "scipy": VERSION_CHECK_MINOR,  # Used by sklearn
}


@dataclass
class VersionCheckResult:
    """Result of a version check for a single package."""

    package: str
    expected: str
    actual: Optional[str]
    status: str  # "ok", "mismatch", "missing"
    message: str
    severity: str  # "info", "warning", "error"


def get_installed_version(package_name: str) -> Optional[str]:
    """
    Get the installed version of a package.

    Args:
        package_name: Name of the package (e.g., 'numpy', 'scikit-learn')

    Returns:
        Version string or None if not installed
    """
    try:
        # Handle package name variations
        import_name = package_name.replace("-", "_")

        # Special cases for import names
        import_map = {
            "scikit_learn": "sklearn",
            "scikit-learn": "sklearn",
        }
        import_name = import_map.get(package_name, import_name)

        module = __import__(import_name)
        return getattr(module, "__version__", None)
    except ImportError:
        return None


def check_version_compatibility(expected: str, actual: str, mode: str = VERSION_CHECK_STRICT) -> Tuple[bool, str]:
    """
    Check if actual version is compatible with expected version.

    Args:
        expected: Expected version string
        actual: Actual installed version string
        mode: Compatibility mode (strict, minor, major)

    Returns:
        Tuple of (is_compatible, reason_message)
    """
    try:
        exp_ver = pkg_version.parse(expected)
        act_ver = pkg_version.parse(actual)

        if mode == VERSION_CHECK_STRICT:
            if exp_ver == act_ver:
                return True, f"Exact match: {actual}"
            return False, f"Expected {expected}, got {actual} (strict mode)"

        elif mode == VERSION_CHECK_MINOR:
            if exp_ver.major == act_ver.major and exp_ver.minor == act_ver.minor:
                return True, f"Minor version match: {actual}"
            return False, f"Expected {expected}, got {actual} (minor version mismatch)"

        elif mode == VERSION_CHECK_MAJOR:
            if exp_ver.major == act_ver.major:
                return True, f"Major version match: {actual}"
            return False, f"Expected {expected}, got {actual} (major version mismatch)"

        else:
            return False, f"Unknown compatibility mode: {mode}"

    except Exception as e:
        return False, f"Version parse error: {e}"


def validate_ml_versions(strict: bool = False, raise_on_error: bool = False) -> List[VersionCheckResult]:
    """
    Validate all ML stack versions against pinned requirements.

    Args:
        strict: If True, use strict mode for all packages
        raise_on_error: If True, raise RuntimeError on critical mismatches

    Returns:
        List of VersionCheckResult objects

    Raises:
        RuntimeError: If raise_on_error is True and critical version mismatch found
    """
    results: List[VersionCheckResult] = []
    critical_errors: List[str] = []

    for package, expected_version in PINNED_VERSIONS.items():
        actual_version = get_installed_version(package)

        if actual_version is None:
            result = VersionCheckResult(
                package=package,
                expected=expected_version,
                actual=None,
                status="missing",
                message=f"Package {package} is not installed",
                severity="error",
            )
            critical_errors.append(result.message)
        else:
            mode = VERSION_CHECK_STRICT if strict else PACKAGE_COMPATIBILITY_MODE.get(package, VERSION_CHECK_STRICT)
            is_compatible, message = check_version_compatibility(expected_version, actual_version, mode)

            if is_compatible:
                result = VersionCheckResult(
                    package=package,
                    expected=expected_version,
                    actual=actual_version,
                    status="ok",
                    message=message,
                    severity="info",
                )
            else:
                # Determine severity based on package criticality
                if package in ("scikit-learn", "joblib"):
                    severity = "error"
                    critical_errors.append(
                        f"CRITICAL: {package} version mismatch - {message}. " f"Model loading may fail!"
                    )
                else:
                    severity = "warning"

                result = VersionCheckResult(
                    package=package,
                    expected=expected_version,
                    actual=actual_version,
                    status="mismatch",
                    message=message,
                    severity=severity,
                )

        results.append(result)

    if raise_on_error and critical_errors:
        raise RuntimeError("ML stack version validation failed:\n" + "\n".join(critical_errors))

    return results


def get_ml_version_report() -> Dict:
    """
    Generate a detailed ML version report for diagnostics.

    Returns:
        Dictionary with version information and compatibility status
    """
    results = validate_ml_versions()

    return {
        "pinned_versions": PINNED_VERSIONS.copy(),
        "installed_versions": {r.package: r.actual for r in results},
        "compatibility_status": {
            r.package: {"status": r.status, "message": r.message, "severity": r.severity} for r in results
        },
        "all_compatible": all(r.status == "ok" for r in results),
        "critical_issues": [r.message for r in results if r.severity == "error"],
        "warnings": [r.message for r in results if r.severity == "warning"],
    }


def log_ml_version_status(log_level: int = logging.INFO) -> None:
    """
    Log ML stack version status at startup.

    Args:
        log_level: Logging level for the report
    """
    results = validate_ml_versions()

    logger.log(log_level, "=" * 60)
    logger.log(log_level, "ML Stack Version Validation")
    logger.log(log_level, "=" * 60)

    for result in results:
        if result.severity == "error":
            logger.error(f"  {result.package}: {result.message}")
        elif result.severity == "warning":
            logger.warning(f"  {result.package}: {result.message}")
        else:
            logger.log(log_level, f"  {result.package}: {result.message}")

    all_ok = all(r.status == "ok" for r in results)
    if all_ok:
        logger.log(log_level, "All ML dependencies validated successfully")
    else:
        warnings = [r for r in results if r.severity == "warning"]
        errors = [r for r in results if r.severity == "error"]
        if errors:
            logger.error(f"ML validation: {len(errors)} critical issues, {len(warnings)} warnings")
        elif warnings:
            logger.warning(f"ML validation: {len(warnings)} warnings")

    logger.log(log_level, "=" * 60)


def check_model_training_versions(model_metadata: Dict) -> List[str]:
    """
    Compare current ML stack versions against model training versions.

    Args:
        model_metadata: Model metadata dict containing 'training_versions'

    Returns:
        List of warning messages for version mismatches
    """
    warnings = []
    training_versions = model_metadata.get("training_versions", {})

    if not training_versions:
        warnings.append("Model metadata does not contain training versions. " "Cannot verify ML stack compatibility.")
        return warnings

    for package, trained_version in training_versions.items():
        current_version = get_installed_version(package)

        if current_version is None:
            warnings.append(f"Package {package} (trained with {trained_version}) is not installed")
            continue

        mode = PACKAGE_COMPATIBILITY_MODE.get(package, VERSION_CHECK_STRICT)
        is_compatible, message = check_version_compatibility(trained_version, current_version, mode)

        if not is_compatible:
            warnings.append(
                f"Model trained with {package}=={trained_version}, "
                f"but runtime has {package}=={current_version}. "
                f"This may cause loading or prediction issues."
            )

    return warnings


# Convenience function for health checks
def is_ml_stack_healthy() -> Tuple[bool, Optional[str]]:
    """
    Quick health check for ML stack versions.

    Returns:
        Tuple of (is_healthy, error_message_or_none)
    """
    try:
        results = validate_ml_versions()
        critical = [r for r in results if r.severity == "error"]

        if critical:
            return False, f"{len(critical)} critical ML stack version issues"
        return True, None
    except Exception as e:
        return False, f"ML version check failed: {e}"
