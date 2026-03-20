#!/bin/bash
# =====================================================
# Floodingnaque - PostgreSQL Database Backup Script
# =====================================================
# This script creates backups of the Supabase PostgreSQL database
#
# Usage:
#   ./backup_database.sh                    # Full backup
#   ./backup_database.sh --tables-only      # Schema + data backup
#   ./backup_database.sh --schema-only      # Schema only
#
# Cron example (daily at 2 AM):
#   0 2 * * * /path/to/backup_database.sh >> /var/log/floodingnaque-backup.log 2>&1
# =====================================================

set -euo pipefail

# Configuration
BACKUP_DIR="${BACKUP_DIR:-/app/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="floodingnaque_backup_${TIMESTAMP}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# Check required environment variables
check_requirements() {
    if [ -z "${DATABASE_URL:-}" ]; then
        log_error "DATABASE_URL environment variable is not set"
        exit 1
    fi

    # Ensure backup directory exists
    mkdir -p "$BACKUP_DIR"

    # Check if pg_dump is available
    if ! command -v pg_dump &> /dev/null; then
        log_error "pg_dump is not installed. Please install PostgreSQL client tools."
        exit 1
    fi
}

# Parse DATABASE_URL into components
parse_database_url() {
    # Extract components from PostgreSQL URL
    # Format: postgresql://user:password@host:port/database

    # Remove postgresql:// prefix
    local url="${DATABASE_URL#postgresql://}"
    url="${url#postgres://}"

    # Extract user:password
    local userpass="${url%%@*}"
    DB_USER="${userpass%%:*}"
    DB_PASSWORD="${userpass#*:}"

    # Extract host:port/database
    local hostportdb="${url#*@}"
    local hostport="${hostportdb%%/*}"
    DB_NAME="${hostportdb#*/}"

    # Handle query parameters
    DB_NAME="${DB_NAME%%\?*}"

    DB_HOST="${hostport%%:*}"
    DB_PORT="${hostport#*:}"

    # Default port if not specified
    if [ "$DB_PORT" = "$DB_HOST" ]; then
        DB_PORT="5432"
    fi

    # For Supabase pooler, use port 6543
    if [[ "$DB_HOST" == *"pooler.supabase.com"* ]]; then
        log_info "Detected Supabase pooler connection"
    fi
}

# Create backup
create_backup() {
    local backup_type="${1:-full}"
    local backup_file="${BACKUP_DIR}/${BACKUP_NAME}"
    local pg_dump_opts=""

    case "$backup_type" in
        "schema-only")
            pg_dump_opts="--schema-only"
            backup_file="${backup_file}_schema.sql"
            ;;
        "tables-only")
            pg_dump_opts="--data-only"
            backup_file="${backup_file}_data.sql"
            ;;
        *)
            backup_file="${backup_file}_full.sql"
            ;;
    esac

    log_info "Starting $backup_type backup..."
    log_info "Backup file: $backup_file"

    # Set password for pg_dump
    export PGPASSWORD="$DB_PASSWORD"

    # Create backup
    if pg_dump \
        --host="$DB_HOST" \
        --port="$DB_PORT" \
        --username="$DB_USER" \
        --dbname="$DB_NAME" \
        --format=plain \
        --no-owner \
        --no-privileges \
        $pg_dump_opts \
        --file="$backup_file" 2>&1; then

        log_info "Backup created successfully"

        # Compress backup
        log_info "Compressing backup..."
        gzip -f "$backup_file"
        backup_file="${backup_file}.gz"

        # Get file size
        local size
        size=$(du -h "$backup_file" | cut -f1)
        log_info "Backup completed: $backup_file ($size)"

        # Create latest symlink
        ln -sf "$backup_file" "${BACKUP_DIR}/latest_${backup_type}.sql.gz"

        echo "$backup_file"
    else
        log_error "Backup failed!"
        exit 1
    fi

    unset PGPASSWORD
}

# Cleanup old backups
cleanup_old_backups() {
    log_info "Cleaning up backups older than $RETENTION_DAYS days..."

    local deleted_count
    deleted_count=$(find "$BACKUP_DIR" -name "floodingnaque_backup_*.sql.gz" -mtime "+${RETENTION_DAYS}" -delete -print | wc -l)

    if [ "$deleted_count" -gt 0 ]; then
        log_info "Deleted $deleted_count old backup(s)"
    else
        log_info "No old backups to delete"
    fi
}

# List existing backups
list_backups() {
    log_info "Existing backups in $BACKUP_DIR:"
    echo ""
    ls -lh "$BACKUP_DIR"/*.sql.gz 2>/dev/null || echo "No backups found"
    echo ""

    # Show disk usage
    local total_size
    total_size=$(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1)
    log_info "Total backup size: ${total_size:-0}"
}

# Restore from backup
restore_backup() {
    local backup_file="$1"

    if [ ! -f "$backup_file" ]; then
        log_error "Backup file not found: $backup_file"
        exit 1
    fi

    log_warn "WARNING: This will restore the database from backup!"
    log_warn "All current data will be overwritten!"
    read -r -p "Are you sure? (yes/no): " confirm

    if [ "$confirm" != "yes" ]; then
        log_info "Restore cancelled"
        exit 0
    fi

    export PGPASSWORD="$DB_PASSWORD"

    log_info "Restoring from: $backup_file"

    if [[ "$backup_file" == *.gz ]]; then
        gunzip -c "$backup_file" | psql \
            --host="$DB_HOST" \
            --port="$DB_PORT" \
            --username="$DB_USER" \
            --dbname="$DB_NAME"
    else
        psql \
            --host="$DB_HOST" \
            --port="$DB_PORT" \
            --username="$DB_USER" \
            --dbname="$DB_NAME" \
            --file="$backup_file"
    fi

    unset PGPASSWORD

    log_info "Restore completed"
}

# Verify backup integrity
verify_backup() {
    local backup_file="$1"

    if [ ! -f "$backup_file" ]; then
        log_error "Backup file not found: $backup_file"
        exit 1
    fi

    log_info "Verifying backup integrity: $backup_file"

    # Check if gzip file is valid
    if [[ "$backup_file" == *.gz ]]; then
        if gzip -t "$backup_file" 2>&1; then
            log_info "Gzip integrity: OK"
        else
            log_error "Gzip integrity: FAILED"
            exit 1
        fi

        # Check SQL content
        local line_count
        line_count=$(gunzip -c "$backup_file" | wc -l)
        log_info "SQL lines: $line_count"

        # Check for common SQL elements
        if gunzip -c "$backup_file" | grep -q "CREATE TABLE\|INSERT INTO"; then
            log_info "SQL content: OK (contains table definitions/data)"
        else
            log_warn "SQL content: May be incomplete (no CREATE TABLE or INSERT found)"
        fi
    fi

    log_info "Verification completed"
}

# Main script
main() {
    local action="${1:-backup}"

    check_requirements
    parse_database_url

    case "$action" in
        "backup"|"--full")
            create_backup "full"
            cleanup_old_backups
            ;;
        "--schema-only")
            create_backup "schema-only"
            ;;
        "--tables-only"|"--data-only")
            create_backup "tables-only"
            ;;
        "--list"|"list")
            list_backups
            ;;
        "--restore")
            if [ -z "${2:-}" ]; then
                log_error "Please specify backup file to restore"
                exit 1
            fi
            restore_backup "$2"
            ;;
        "--verify")
            if [ -z "${2:-}" ]; then
                backup_file="${BACKUP_DIR}/latest_full.sql.gz"
            else
                backup_file="$2"
            fi
            verify_backup "$backup_file"
            ;;
        "--cleanup")
            cleanup_old_backups
            ;;
        "--help"|"-h")
            echo "Floodingnaque Database Backup Script"
            echo ""
            echo "Usage: $0 [action] [options]"
            echo ""
            echo "Actions:"
            echo "  backup, --full      Create full database backup (default)"
            echo "  --schema-only       Backup schema only (no data)"
            echo "  --tables-only       Backup data only (no schema)"
            echo "  --list, list        List existing backups"
            echo "  --restore <file>    Restore from backup file"
            echo "  --verify [file]     Verify backup integrity"
            echo "  --cleanup           Remove old backups"
            echo "  --help, -h          Show this help"
            echo ""
            echo "Environment Variables:"
            echo "  DATABASE_URL        PostgreSQL connection string (required)"
            echo "  BACKUP_DIR          Backup directory (default: /app/backups)"
            echo "  RETENTION_DAYS      Days to keep backups (default: 30)"
            ;;
        *)
            log_error "Unknown action: $action"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
}

main "$@"
