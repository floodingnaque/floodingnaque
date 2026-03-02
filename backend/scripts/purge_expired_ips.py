"""
Purge expired login IP addresses (GDPR / Data Privacy Act).

Usage:
    python -m scripts.purge_expired_ips          # dry-run by default
    python -m scripts.purge_expired_ips --apply   # actually commit changes
"""

import argparse
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Purge login IPs past the retention window.")
    parser.add_argument("--apply", action="store_true", help="Commit changes (dry-run by default)")
    args = parser.parse_args()

    # Import after arg parse so --help works without a running DB
    from app.models.db import get_db_session
    from app.models.user import User

    with get_db_session() as session:
        count = User.purge_expired_ips(session)

        if count == 0:
            logger.info("No expired login IPs to purge.")
        elif args.apply:
            logger.info(f"Purged login IPs for {count} user(s).")
        else:
            session.rollback()
            logger.info(f"[DRY-RUN] Would purge login IPs for {count} user(s). Re-run with --apply to commit.")
            sys.exit(0)


if __name__ == "__main__":
    main()
