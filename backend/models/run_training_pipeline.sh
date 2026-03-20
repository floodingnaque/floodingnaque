#!/usr/bin/env bash
#
# run_training_pipeline.sh
#
# PURPOSE:
#   Orchestrates Floodingnaque ML training workflows including data ingestion.
#   Cross-platform Bash equivalent of run_training_pipeline.ps1 for Linux/macOS.
#
# FEATURES IMPLEMENTED:
#   - Data ingestion from multiple sources (Meteostat, WorldTides, Google Earth Engine)
#   - Multiple training modes (Quick, Full, PAGASA, Ultimate)
#   - Strict argument validation
#   - Dry-run mode (no execution, plan only)
#   - CI-friendly JSON logs (machine-readable)
#
# SUPPORTED MODES:
#   DATA INGESTION:
#     --ingest              Run data ingestion only
#     --ingest-google       Fetch from Google Earth Engine
#     --ingest-meteostat    Fetch from Meteostat (free, no API key)
#     --ingest-tides        Fetch from WorldTides API
#     --ingest-days <int>   Days of historical data (default: 30)
#
#   TRAINING:
#     --quick               Fast training with default dataset
#     --full                Full progressive training (default)
#     --pagasa              PAGASA-specific training
#     --ultimate            Ultimate training with all features
#     --progressive         Progressive training (same as Ultimate)
#
# PLATFORM:
#   Bash 4+ (Linux/macOS)
#
# EXIT CODES:
#   0 = Success
#   1 = Critical failure
#   2 = Completed with warnings
#

set -euo pipefail

# =========================
# COLORS AND FORMATTING
# =========================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# =========================
# DEFAULT VALUES
# =========================
INGEST_ONLY=false
INGEST_GOOGLE=false
INGEST_METEOSTAT=false
INGEST_TIDES=false
INGEST_DAYS=30
INGEST_FILE=""
INGEST_DIR=""

MODE_QUICK=false
MODE_FULL=false
MODE_PAGASA=false
MODE_ULTIMATE=false
MODE_PROGRESSIVE=false

SKIP_INGESTION=false
SKIP_VALIDATION=false
DRY_RUN=false
JSON_LOGS=false

CV_FOLDS=10
SEED=42

DATA_DIR="data"
MODEL_DIR="models"
REPORT_DIR="reports"
SCRIPTS_DIR="scripts"
LOG_FILE=""

WARNINGS=()

# =========================
# HELP
# =========================
show_help() {
    cat << 'EOF'
Floodingnaque ML Pipeline (Bash)
================================

USAGE:
  ./run_training_pipeline.sh [MODE] [OPTIONS]

DATA INGESTION:
  --ingest              Run data ingestion only (no training)
  --ingest-google       Fetch from Google Earth Engine
  --ingest-meteostat    Fetch from Meteostat (free, no API key)
  --ingest-tides        Fetch from WorldTides API
  --ingest-days <int>   Days of historical data (default: 30)
  --ingest-file <path>  Ingest a specific CSV file
  --ingest-dir <path>   Ingest all CSV files from directory

TRAINING MODES (mutually exclusive):
  --quick               Fast training with default dataset
  --full                Full progressive training (default)
  --pagasa              PAGASA-specific training
  --ultimate            Ultimate training with all features
  --progressive         Progressive training (same as Ultimate)

OPTIONS:
  --dry-run             Show execution plan only
  --json-logs           Emit structured JSON logs (CI-friendly)
  --skip-ingestion      Skip data ingestion step in training modes
  --skip-validation     Skip model validation step
  --cv-folds <int>      Cross-validation folds (default: 10)
  --seed <int>          Random seed (default: 42)
  --log-file <path>     Write logs to file

EXAMPLES:
  # Ingest data only
  ./run_training_pipeline.sh --ingest --ingest-meteostat --ingest-days 30

  # Ingest from multiple sources
  ./run_training_pipeline.sh --ingest --ingest-meteostat --ingest-tides --ingest-days 7

  # Full training pipeline (includes ingestion)
  ./run_training_pipeline.sh --full --ingest-meteostat --ingest-days 30

  # Quick training without ingestion
  ./run_training_pipeline.sh --quick --skip-ingestion

  # Dry run to see what would happen
  ./run_training_pipeline.sh --full --dry-run

EOF
}

# =========================
# LOGGING
# =========================
PIPELINE_START=$(date +%s)

emit_log() {
    local level="$1"
    local message="$2"
    local timestamp
    timestamp=$(date -Iseconds)

    if [[ "$JSON_LOGS" == true ]]; then
        printf '{"timestamp":"%s","level":"%s","message":"%s"}\n' \
            "$timestamp" "$level" "$message"
    else
        echo "[$timestamp][$level] $message"
    fi

    if [[ -n "$LOG_FILE" ]]; then
        printf '{"timestamp":"%s","level":"%s","message":"%s"}\n' \
            "$timestamp" "$level" "$message" >> "$LOG_FILE"
    fi
}

# =========================
# PROGRESS INDICATOR
# =========================
progress_tick() {
    if [[ "$JSON_LOGS" != true ]]; then
        printf "."
    fi
    sleep 1
}

# =========================
# EXECUTION WRAPPER
# =========================
run_step() {
    local name="$1"
    local command="$2"
    local critical="${3:-false}"

    emit_log "INFO" "START: $name"

    if [[ "$DRY_RUN" == true ]]; then
        emit_log "INFO" "DRY-RUN: skipped execution"
        emit_log "INFO" "  Would run: $command"
        return 0
    fi

    # Run in background and show progress
    local temp_output
    temp_output=$(mktemp)

    eval "$command" > "$temp_output" 2>&1 &
    local pid=$!

    while kill -0 "$pid" 2>/dev/null; do
        progress_tick
    done

    wait "$pid"
    local exit_code=$?

    if [[ "$JSON_LOGS" != true ]]; then
        echo ""  # New line after progress dots
    fi

    if [[ $exit_code -ne 0 ]]; then
        if [[ "$critical" == true ]]; then
            emit_log "ERROR" "FAILED: $name"
            cat "$temp_output"
            rm -f "$temp_output"
            exit 1
        else
            emit_log "WARN" "WARN: $name (exit code: $exit_code)"
            WARNINGS+=("$name :: exit code $exit_code")
        fi
    else
        emit_log "INFO" "END: $name"
    fi

    rm -f "$temp_output"
}

# =========================
# PARSE ARGUMENTS
# =========================
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            --ingest)
                INGEST_ONLY=true
                shift
                ;;
            --ingest-google)
                INGEST_GOOGLE=true
                shift
                ;;
            --ingest-meteostat)
                INGEST_METEOSTAT=true
                shift
                ;;
            --ingest-tides)
                INGEST_TIDES=true
                shift
                ;;
            --ingest-days)
                INGEST_DAYS="$2"
                shift 2
                ;;
            --ingest-file)
                INGEST_FILE="$2"
                shift 2
                ;;
            --ingest-dir)
                INGEST_DIR="$2"
                shift 2
                ;;
            --quick)
                MODE_QUICK=true
                shift
                ;;
            --full)
                MODE_FULL=true
                shift
                ;;
            --pagasa)
                MODE_PAGASA=true
                shift
                ;;
            --ultimate)
                MODE_ULTIMATE=true
                shift
                ;;
            --progressive)
                MODE_PROGRESSIVE=true
                shift
                ;;
            --skip-ingestion)
                SKIP_INGESTION=true
                shift
                ;;
            --skip-validation)
                SKIP_VALIDATION=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --json-logs)
                JSON_LOGS=true
                shift
                ;;
            --cv-folds)
                CV_FOLDS="$2"
                shift 2
                ;;
            --seed)
                SEED="$2"
                shift 2
                ;;
            --log-file)
                LOG_FILE="$2"
                shift 2
                ;;
            *)
                echo "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# =========================
# VALIDATION
# =========================
validate_args() {
    # Check if ingest-only mode
    if [[ "$INGEST_ONLY" == true ]] && \
       [[ "$MODE_QUICK" == false ]] && \
       [[ "$MODE_FULL" == false ]] && \
       [[ "$MODE_PAGASA" == false ]] && \
       [[ "$MODE_ULTIMATE" == false ]] && \
       [[ "$MODE_PROGRESSIVE" == false ]]; then
        INGEST_ONLY=true
    else
        INGEST_ONLY=false
    fi

    # Check for ingest source
    local has_ingest_source=false
    if [[ "$INGEST_GOOGLE" == true ]] || \
       [[ "$INGEST_METEOSTAT" == true ]] || \
       [[ "$INGEST_TIDES" == true ]] || \
       [[ -n "$INGEST_FILE" ]] || \
       [[ -n "$INGEST_DIR" ]]; then
        has_ingest_source=true
    fi

    # Count training modes
    local mode_count=0
    [[ "$MODE_QUICK" == true ]] && ((mode_count++))
    [[ "$MODE_FULL" == true ]] && ((mode_count++))
    [[ "$MODE_PAGASA" == true ]] && ((mode_count++))
    [[ "$MODE_ULTIMATE" == true ]] && ((mode_count++))
    [[ "$MODE_PROGRESSIVE" == true ]] && ((mode_count++))

    if [[ $mode_count -gt 1 ]]; then
        echo -e "${RED}Error: Only one training mode may be specified${NC}"
        exit 1
    fi

    # Default to Full mode
    if [[ $mode_count -eq 0 ]] && [[ "$INGEST_ONLY" == false ]]; then
        MODE_FULL=true
    fi

    # Validate PAGASA + Ultimate combo
    if [[ "$MODE_PAGASA" == true ]] && \
       ([[ "$MODE_ULTIMATE" == true ]] || [[ "$MODE_PROGRESSIVE" == true ]]); then
        echo -e "${RED}Error: PAGASA cannot be combined with Ultimate/Progressive${NC}"
        exit 1
    fi

    # Validate CV folds
    if [[ $CV_FOLDS -lt 2 ]] || [[ $CV_FOLDS -gt 20 ]]; then
        echo -e "${RED}Error: CV_FOLDS must be between 2 and 20${NC}"
        exit 1
    fi

    # Validate seed
    if [[ $SEED -lt 0 ]]; then
        echo -e "${RED}Error: Seed must be non-negative${NC}"
        exit 1
    fi

    # Validate ingest days
    if [[ $INGEST_DAYS -lt 1 ]] || [[ $INGEST_DAYS -gt 365 ]]; then
        echo -e "${RED}Error: IngestDays must be between 1 and 365${NC}"
        exit 1
    fi

    # If ingest-only, require source
    if [[ "$INGEST_ONLY" == true ]] && [[ "$has_ingest_source" == false ]]; then
        echo -e "${RED}Error: Ingest mode requires at least one source${NC}"
        echo "Use: --ingest-google, --ingest-meteostat, --ingest-tides, --ingest-file, or --ingest-dir"
        exit 1
    fi
}

# =========================
# ENVIRONMENT CHECKS
# =========================
check_environment() {
    run_step "Python availability" "python3 --version" true

    run_step "Python version >= 3.10" "python3 -c 'import sys; assert sys.version_info >= (3,10), \"Python 3.10+ required\"'" true

    run_step "Dependencies check" "python3 -c 'import pandas, numpy, sklearn, joblib'" true
}

# =========================
# DIRECTORY SETUP
# =========================
setup_directories() {
    # Determine script directory
    local script_dir
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

    # Backend directory (parent of models/)
    BACKEND_DIR="$(dirname "$script_dir")"

    SCRIPTS_PATH="$BACKEND_DIR/scripts"
    DATA_PATH="$BACKEND_DIR/$DATA_DIR"
    MODEL_PATH="$BACKEND_DIR/$MODEL_DIR"
    REPORT_PATH="$BACKEND_DIR/$REPORT_DIR"

    if [[ "$DRY_RUN" == false ]]; then
        mkdir -p "$DATA_PATH" "$MODEL_PATH" "$REPORT_PATH"
    fi

    # Google credentials
    local creds_file="$BACKEND_DIR/astral-archive-482008-g2-b4f2279053c0.json"
    if [[ -f "$creds_file" ]]; then
        export GOOGLE_APPLICATION_CREDENTIALS="$creds_file"
        emit_log "INFO" "Google credentials file found"
    elif [[ "$INGEST_GOOGLE" == true ]]; then
        emit_log "WARN" "Google credentials file not found (Earth Engine may not work)"
    fi

    # Set Google Cloud environment variables
    export GOOGLE_CLOUD_PROJECT="astral-archive-482008-g2"
    export EARTHENGINE_PROJECT="astral-archive-482008-g2"
    export GOOGLE_SERVICE_ACCOUNT_EMAIL="floodingnaque@astral-archive-482008-g2.iam.gserviceaccount.com"
}

# =========================
# DATA INGESTION
# =========================
run_ingestion() {
    local has_ingest_source=false
    if [[ "$INGEST_GOOGLE" == true ]] || \
       [[ "$INGEST_METEOSTAT" == true ]] || \
       [[ "$INGEST_TIDES" == true ]] || \
       [[ -n "$INGEST_FILE" ]] || \
       [[ -n "$INGEST_DIR" ]]; then
        has_ingest_source=true
    fi

    if [[ "$has_ingest_source" == false ]] || [[ "$SKIP_INGESTION" == true ]]; then
        return 0
    fi

    emit_log "INFO" "=== DATA INGESTION ==="

    # Build ingestion arguments
    local ingest_args=()

    if [[ -n "$INGEST_FILE" ]]; then
        ingest_args+=("--file" "$INGEST_FILE")
    elif [[ -n "$INGEST_DIR" ]]; then
        ingest_args+=("--dir" "$INGEST_DIR")
    else
        [[ "$INGEST_GOOGLE" == true ]] && ingest_args+=("--fetch-google")
        [[ "$INGEST_METEOSTAT" == true ]] && ingest_args+=("--fetch-meteostat")
        [[ "$INGEST_TIDES" == true ]] && ingest_args+=("--fetch-tides")
        ingest_args+=("--days" "$INGEST_DAYS")
    fi

    local ingest_script="$SCRIPTS_PATH/ingest_training_data.py"

    # Build source description
    local sources=()
    [[ "$INGEST_GOOGLE" == true ]] && sources+=("Google")
    [[ "$INGEST_METEOSTAT" == true ]] && sources+=("Meteostat")
    [[ "$INGEST_TIDES" == true ]] && sources+=("WorldTides")
    [[ -n "$INGEST_FILE" ]] && sources+=("File: $INGEST_FILE")
    [[ -n "$INGEST_DIR" ]] && sources+=("Dir: $INGEST_DIR")

    local sources_str
    sources_str=$(IFS=', '; echo "${sources[*]}")

    emit_log "INFO" "Running: python3 $ingest_script ${ingest_args[*]}"

    if [[ "$DRY_RUN" == false ]]; then
        if ! python3 "$ingest_script" "${ingest_args[@]}"; then
            emit_log "ERROR" "Data ingestion failed"
            exit 1
        fi
        emit_log "INFO" "Data ingestion completed"
    else
        emit_log "INFO" "DRY-RUN: Would run data ingestion ($sources_str)"
    fi
}

# =========================
# TRAINING
# =========================
run_training() {
    emit_log "INFO" "=== MODEL TRAINING ==="

    if [[ "$MODE_PAGASA" == true ]]; then
        run_step "PAGASA preprocess" \
            "python3 '$SCRIPTS_PATH/preprocess_pagasa_data.py' --create-training" \
            true

        run_step "PAGASA train" \
            "python3 '$SCRIPTS_PATH/train_pagasa.py'" \
            true
    elif [[ "$MODE_ULTIMATE" == true ]] || [[ "$MODE_PROGRESSIVE" == true ]]; then
        run_step "Dataset preparation" \
            "python3 '$SCRIPTS_PATH/preprocess_pagasa_data.py' --create-training && \
             python3 '$SCRIPTS_PATH/preprocess_official_flood_records.py'"

        run_step "Ultimate training" \
            "python3 '$SCRIPTS_PATH/train_ultimate.py' --cv-folds $CV_FOLDS --progressive" \
            true
    elif [[ "$MODE_QUICK" == true ]]; then
        run_step "Quick training" \
            "python3 '$SCRIPTS_PATH/train.py' --data 'data/processed/cumulative_up_to_2025.csv'" \
            true
    else
        # Full mode (default)
        run_step "Full progressive training" \
            "python3 '$SCRIPTS_PATH/progressive_train.py' --grid-search --cv-folds $CV_FOLDS" \
            true
    fi

    # Validation
    if [[ "$SKIP_VALIDATION" == false ]]; then
        run_step "Validation" \
            "python3 '$SCRIPTS_PATH/validate_model.py' --json > '$REPORT_PATH/validation.json'"
    fi

    # Evaluation
    run_step "Evaluation" \
        "python3 '$SCRIPTS_PATH/evaluate_model.py'"
}

# =========================
# SUMMARY
# =========================
write_summary() {
    local end_time
    end_time=$(date +%s)
    local duration=$((end_time - PIPELINE_START))
    local duration_minutes
    duration_minutes=$(echo "scale=2; $duration / 60" | bc)

    local success="true"
    [[ ${#WARNINGS[@]} -gt 0 ]] && success="false"

    local summary_file="$REPORT_PATH/pipeline_summary.json"

    # Determine mode string
    local mode_str="FULL"
    [[ "$MODE_QUICK" == true ]] && mode_str="QUICK"
    [[ "$MODE_PAGASA" == true ]] && mode_str="PAGASA"
    [[ "$MODE_ULTIMATE" == true ]] && mode_str="ULTIMATE"
    [[ "$MODE_PROGRESSIVE" == true ]] && mode_str="PROGRESSIVE"
    [[ "$INGEST_ONLY" == true ]] && mode_str="INGEST-ONLY"

    cat > "$summary_file" << EOF
{
    "success": $success,
    "mode": "$mode_str",
    "warnings": [$(printf '"%s",' "${WARNINGS[@]}" | sed 's/,$//')]
    "duration_minutes": $duration_minutes,
    "dry_run": $DRY_RUN,
    "ingest_only": $INGEST_ONLY,
    "cv_folds": $CV_FOLDS,
    "seed": $SEED,
    "platform": "$(uname -s)",
    "completed_at": "$(date -Iseconds)"
}
EOF

    emit_log "INFO" "PIPELINE COMPLETE in $duration_minutes minutes"
}

# =========================
# MAIN
# =========================
main() {
    parse_args "$@"
    validate_args

    emit_log "INFO" "PIPELINE START"

    if [[ "$INGEST_ONLY" == true ]]; then
        emit_log "INFO" "MODE: INGEST-ONLY"
    elif [[ "$MODE_QUICK" == true ]]; then
        emit_log "INFO" "MODE: QUICK"
    elif [[ "$MODE_PAGASA" == true ]]; then
        emit_log "INFO" "MODE: PAGASA"
    elif [[ "$MODE_ULTIMATE" == true ]] || [[ "$MODE_PROGRESSIVE" == true ]]; then
        emit_log "INFO" "MODE: ULTIMATE"
    else
        emit_log "INFO" "MODE: FULL"
    fi

    emit_log "INFO" "Seed=$SEED CVFolds=$CV_FOLDS DryRun=$DRY_RUN"

    check_environment
    setup_directories

    # Data ingestion
    run_ingestion

    # Exit if ingest-only
    if [[ "$INGEST_ONLY" == true ]]; then
        emit_log "INFO" "Ingest-only mode completed"
        write_summary
        exit 0
    fi

    # Training
    run_training

    # Summary
    write_summary

    # Exit code based on warnings
    if [[ ${#WARNINGS[@]} -gt 0 ]]; then
        exit 2
    fi

    exit 0
}

main "$@"
