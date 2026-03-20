"""
Python-based PostgreSQL backup (no pg_dump required).

Uses psycopg2 COPY protocol to export all tables as SQL-compatible dump.
Intended as a fallback when pg_dump CLI is not installed.

Usage:
    python scripts/backup_database_py.py                  # Auto from APP_ENV
    python scripts/backup_database_py.py --env development # Explicit env
"""

import argparse
import gzip
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def get_database_url(env: str) -> str:
    """Load DATABASE_URL from the appropriate .env file."""
    env_file_map = {
        "development": ".env.development",
        "staging": ".env.staging",
        "production": ".env.production",
    }
    env_file = backend_path / env_file_map.get(env, ".env")
    if not env_file.exists():
        raise FileNotFoundError(f"Env file not found: {env_file}")

    db_url = None
    with open(env_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("DATABASE_URL="):
                db_url = line.split("=", 1)[1].strip()
                break
    if not db_url:
        raise RuntimeError(f"DATABASE_URL not found in {env_file}")
    return db_url


def backup_with_psycopg2(database_url: str, output_dir: Path) -> Path:
    """Export all tables using psycopg2 COPY TO STDOUT."""
    import psycopg2

    parsed = urlparse(database_url)
    # Strip query params for raw connection
    conn_params = {
        "host": parsed.hostname,
        "port": parsed.port or 5432,
        "user": parsed.username or "postgres",
        "password": parsed.password or "",
        "dbname": parsed.path.lstrip("/"),
        "sslmode": "require",
    }

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = output_dir / f"floodingnaque_backup_{timestamp}.sql"

    logger.info(f"Connecting to {conn_params['host']}:{conn_params['port']}/{conn_params['dbname']}")
    conn = psycopg2.connect(**conn_params)
    conn.set_session(readonly=True)
    cur = conn.cursor()

    # Get all user tables in public schema
    cur.execute("""
        SELECT tablename FROM pg_tables
        WHERE schemaname = 'public'
        ORDER BY tablename
    """)
    all_tables = [row[0] for row in cur.fetchall()]

    # Identify partitioned parent tables
    cur.execute("""
        SELECT relname FROM pg_class
        WHERE relkind = 'p' AND relnamespace = 'public'::regnamespace
    """)
    partitioned_parents = {row[0] for row in cur.fetchall()}

    # Identify partition children (inheriting from a parent)
    cur.execute("""
        SELECT c.relname
        FROM pg_inherits i
        JOIN pg_class c ON i.inhrelid = c.oid
        WHERE c.relnamespace = 'public'::regnamespace
    """)
    partition_children = {row[0] for row in cur.fetchall()}

    # Export parent tables (data aggregated from partitions via SELECT *) and
    # non-partition tables. Skip partition children to avoid duplicates.
    tables = [t for t in all_tables if t not in partition_children]
    logger.info(f"Found {len(all_tables)} tables total, {len(tables)} to export "
                f"({len(partition_children)} partition children skipped)")
    logger.info(f"Tables: {', '.join(tables)}")

    with open(backup_file, "w", encoding="utf-8") as f:
        f.write(f"-- Floodingnaque Database Backup\n")
        f.write(f"-- Date: {datetime.now().isoformat()}\n")
        f.write(f"-- Source: {conn_params['host']}\n")
        f.write(f"-- Tables: {len(tables)}\n\n")

        for table in tables:
            logger.info(f"  Exporting: {table}")

            # Get CREATE TABLE DDL
            cur.execute(f"""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %s
                ORDER BY ordinal_position
            """, (table,))
            columns = cur.fetchall()

            f.write(f"\n-- Table: {table} ({len(columns)} columns)\n")
            f.write(f"-- Columns: {', '.join(c[0] for c in columns)}\n")

            # Get row count
            cur.execute(f'SELECT COUNT(*) FROM "{table}"')  # noqa: S608
            count = cur.fetchone()[0]
            f.write(f"-- Rows: {count}\n")

            if count == 0:
                f.write(f"-- (empty table, skipping data)\n")
                continue

            # Use COPY TO STDOUT via copy_expert (psycopg2)
            # Partitioned parent tables need SELECT variant
            f.write(f"\n-- COPY data for {table}\n")
            f.write(f"COPY \"{table}\" FROM stdin WITH (FORMAT csv, HEADER true, NULL 'NULL');\n")

            import io
            buf = io.BytesIO()
            # Use COPY (SELECT ...) variant which works for both regular and partitioned tables
            copy_sql = f'COPY (SELECT * FROM "{table}") TO STDOUT WITH (FORMAT csv, HEADER true, NULL \'NULL\')'
            cur.copy_expert(copy_sql, buf)
            buf.seek(0)
            f.write(buf.read().decode("utf-8"))

            f.write("\\.\n")

    cur.close()
    conn.close()

    # Compress
    compressed = backup_file.with_suffix(".sql.gz")
    with open(backup_file, "rb") as f_in:
        with gzip.open(compressed, "wb") as f_out:
            while chunk := f_in.read(65536):
                f_out.write(chunk)
    backup_file.unlink()

    size_mb = compressed.stat().st_size / (1024 * 1024)
    logger.info(f"Backup complete: {compressed} ({size_mb:.2f} MB)")
    return compressed


def main():
    parser = argparse.ArgumentParser(description="Python-based PostgreSQL backup")
    parser.add_argument("--env", default=os.getenv("APP_ENV", "development"),
                        choices=["development", "staging", "production"],
                        help="Environment to backup (default: APP_ENV or development)")
    parser.add_argument("--output", default=None, help="Output directory")
    args = parser.parse_args()

    output_dir = Path(args.output) if args.output else backend_path / "backups"
    output_dir.mkdir(parents=True, exist_ok=True)

    db_url = get_database_url(args.env)
    logger.info(f"Backing up {args.env} database")

    backup_path = backup_with_psycopg2(db_url, output_dir)
    print(f"\nBackup saved to: {backup_path}")


if __name__ == "__main__":
    main()
