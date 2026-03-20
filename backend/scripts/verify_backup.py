"""
Backup Verification Script for Floodingnaque.

Validates that database backups are restorable and contain expected data.
Designed to run in CI or as a periodic health check.

Usage:
    python scripts/verify_backup.py                          # Verify latest backup
    python scripts/verify_backup.py --backup-dir ./backups   # Custom backup directory
    python scripts/verify_backup.py --max-age-hours 24       # Fail if no backup within 24h
    python scripts/verify_backup.py --verbose                # Verbose logging

Exit codes:
    0 - All checks passed
    1 - Verification failed
    2 - No backups found
"""

import argparse
import gzip
import logging
import os
import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

logger = logging.getLogger(__name__)


def find_latest_backup(backup_dir: Path) -> Path | None:
    """Find the most recently modified backup file in the directory."""
    candidates = []
    for ext in ("*.sql", "*.sql.gz", "*.db", "*.db.gz", "*.backup.*", "*.dump", "*.dump.gz"):
        candidates.extend(backup_dir.glob(ext))

    if not candidates:
        return None

    return max(candidates, key=lambda p: p.stat().st_mtime)


def check_backup_age(backup_path: Path, max_age_hours: int) -> bool:
    """Return True if the backup is within the acceptable age window."""
    mtime = datetime.fromtimestamp(backup_path.stat().st_mtime, tz=timezone.utc)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    age_hours = (datetime.now(timezone.utc) - mtime).total_seconds() / 3600

    if mtime < cutoff:
        logger.error(
            "Backup too old: %s (%.1f hours, max %d)",
            backup_path.name,
            age_hours,
            max_age_hours,
        )
        return False

    logger.info("Backup age OK: %s (%.1f hours)", backup_path.name, age_hours)
    return True


def check_backup_size(backup_path: Path, min_bytes: int = 1024) -> bool:
    """Return True if the backup file is at least min_bytes."""
    size = backup_path.stat().st_size
    if size < min_bytes:
        logger.error("Backup too small: %s (%d bytes, min %d)", backup_path.name, size, min_bytes)
        return False

    size_mb = size / (1024 * 1024)
    logger.info("Backup size OK: %s (%.2f MB)", backup_path.name, size_mb)
    return True


def check_gzip_integrity(backup_path: Path) -> bool:
    """Verify that a .gz file can be fully decompressed."""
    if not backup_path.suffix == ".gz":
        return True

    try:
        with gzip.open(backup_path, "rb") as f:
            while f.read(65536):
                pass
        logger.info("Gzip integrity OK: %s", backup_path.name)
        return True
    except (gzip.BadGzipFile, OSError) as exc:
        logger.error("Gzip integrity FAILED: %s (%s)", backup_path.name, exc)
        return False


def check_sqlite_restorable(backup_path: Path) -> bool:
    """Try loading the backup into a temporary SQLite database."""
    if backup_path.suffix == ".gz":
        src_suffix = backup_path.stem.rsplit(".", 1)[-1]
    else:
        src_suffix = backup_path.suffix.lstrip(".")

    if src_suffix not in ("db", "sqlite", "sqlite3"):
        logger.info("Skipping SQLite restore check (not a .db file): %s", backup_path.name)
        return True

    tmpdir = None
    try:
        tmpdir = tempfile.mkdtemp(prefix="fnq_verify_")
        restore_path = Path(tmpdir) / "restore.db"

        if backup_path.suffix == ".gz":
            with gzip.open(backup_path, "rb") as f_in, open(restore_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        else:
            shutil.copy2(backup_path, restore_path)

        conn = sqlite3.connect(str(restore_path))
        try:
            result = conn.execute("PRAGMA integrity_check").fetchone()
            if result and result[0] == "ok":
                tables = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()
                logger.info(
                    "SQLite restore OK: %s (integrity=ok, %d tables)",
                    backup_path.name,
                    tables[0] if tables else 0,
                )
                return True
            else:
                logger.error("SQLite integrity check failed: %s (%s)", backup_path.name, result)
                return False
        finally:
            conn.close()
    except Exception as exc:
        logger.error("SQLite restore FAILED: %s (%s)", backup_path.name, exc)
        return False
    finally:
        if tmpdir:
            shutil.rmtree(tmpdir, ignore_errors=True)


def check_sql_dump_parseable(backup_path: Path) -> bool:
    """Basic check that a .sql dump contains expected SQL statements."""
    if backup_path.suffix == ".gz":
        src_suffix = backup_path.stem.rsplit(".", 1)[-1]
    else:
        src_suffix = backup_path.suffix.lstrip(".")

    if src_suffix != "sql":
        return True

    try:
        if backup_path.suffix == ".gz":
            opener = gzip.open(backup_path, "rt", encoding="utf-8", errors="replace")
        else:
            opener = open(backup_path, "r", encoding="utf-8", errors="replace")

        with opener as f:
            head = f.read(8192)

        markers = ("CREATE", "INSERT", "TABLE", "BEGIN")
        found = any(m in head.upper() for m in markers)

        if found:
            logger.info("SQL dump parseable: %s (contains SQL statements)", backup_path.name)
        else:
            logger.error("SQL dump appears empty or invalid: %s", backup_path.name)

        return found
    except Exception as exc:
        logger.error("SQL dump check FAILED: %s (%s)", backup_path.name, exc)
        return False


def verify_backup(
    backup_dir: Path,
    max_age_hours: int = 25,
    min_size_bytes: int = 1024,
) -> bool:
    """Run all verification checks on the latest backup. Returns True if all pass."""
    logger.info("=" * 60)
    logger.info("Backup verification started")
    logger.info("Backup directory: %s", backup_dir)
    logger.info("=" * 60)

    if not backup_dir.exists():
        logger.error("Backup directory does not exist: %s", backup_dir)
        return False

    latest = find_latest_backup(backup_dir)
    if latest is None:
        logger.error("No backup files found in %s", backup_dir)
        return False

    logger.info("Latest backup: %s", latest.name)

    checks = [
        ("Age", check_backup_age(latest, max_age_hours)),
        ("Size", check_backup_size(latest, min_size_bytes)),
        ("Gzip integrity", check_gzip_integrity(latest)),
        ("SQLite restore", check_sqlite_restorable(latest)),
        ("SQL parse", check_sql_dump_parseable(latest)),
    ]

    logger.info("-" * 40)
    all_passed = True
    for name, passed in checks:
        status = "PASS" if passed else "FAIL"
        logger.info("  %-20s %s", name, status)
        if not passed:
            all_passed = False

    logger.info("-" * 40)
    logger.info("Result: %s", "ALL CHECKS PASSED" if all_passed else "VERIFICATION FAILED")
    return all_passed


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify database backups")
    parser.add_argument(
        "--backup-dir",
        type=Path,
        default=Path(os.environ.get("FLOODINGNAQUE_BACKUP_DIR", str(backend_path / "backups"))),
        help="Directory containing backups",
    )
    parser.add_argument("--max-age-hours", type=int, default=25, help="Maximum backup age in hours (default: 25)")
    parser.add_argument("--min-size", type=int, default=1024, help="Minimum backup size in bytes (default: 1024)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    passed = verify_backup(
        backup_dir=args.backup_dir,
        max_age_hours=args.max_age_hours,
        min_size_bytes=args.min_size,
    )

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
