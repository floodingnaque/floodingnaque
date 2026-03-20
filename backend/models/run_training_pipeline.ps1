<#
run_training_pipeline.ps1

PURPOSE:
  Orchestrates Floodingnaque ML training workflows including data ingestion.

FEATURES IMPLEMENTED:
  - Data ingestion from multiple sources (Meteostat, WorldTides, Google Earth Engine)
  - Multiple training modes (Quick, Full, PAGASA, Ultimate)
  - Strict argument validation
  - Dry-run mode (no execution, plan only)
  - CI-friendly JSON logs (machine-readable)

SUPPORTED MODES:
  DATA INGESTION:
    -Ingest           Run data ingestion only
    -IngestGoogle     Fetch from Google Earth Engine
    -IngestMeteostat  Fetch from Meteostat (free, no API key)
    -IngestTides      Fetch from WorldTides API
    -IngestDays <int> Days of historical data (default: 30)

  TRAINING:
    -Quick
    -Full (default when no mode specified)
    -PAGASA
    -Ultimate / -Progressive

PLATFORM:
  PowerShell 7+ (Windows)

CROSS-PLATFORM NOTE:
  This script relies on PowerShell background jobs and Windows path semantics.
  For Linux/macOS, use a Python or Bash orchestrator.

EXIT CODES:
  0 = Success
  1 = Critical failure
  2 = Completed with warnings
#>

[CmdletBinding()]
param(
    [switch]$Help,

    # Data Ingestion Options
    [switch]$Ingest,
    [switch]$IngestGoogle,
    [switch]$IngestMeteostat,
    [switch]$IngestTides,
    [int]$IngestDays = 30,
    [string]$IngestFile,
    [string]$IngestDir,

    # Training Mode Options
    [switch]$Quick,
    [switch]$Full,
    [switch]$PAGASA,
    [switch]$Ultimate,
    [switch]$Progressive,
    [switch]$Progressive6,
    [int]$Version,

    [switch]$LatestOnly,
    [switch]$SkipMultiLevel,
    [switch]$SkipValidation,
    [switch]$SkipIngestion,

    [switch]$DryRun,
    [switch]$JsonLogs,

    [int]$CVFolds = 10,
    [int]$Seed = 42,

    [string]$DataDir = "data",
    [string]$ModelDir = "models",
    [string]$ReportDir = "reports",
    [string]$ScriptsDir = "scripts",
    [string]$LogFile
)

# =========================
# POWERSHELL VERSION GUARD
# =========================
if ($PSVersionTable.PSVersion.Major -lt 7) {
    Write-Host "PowerShell 7+ required"
    exit 1
}

# =========================
# HELP
# =========================
if ($Help) {
    @"
Floodingnaque ML Pipeline
=========================

USAGE:
  ./run_training_pipeline.ps1 [MODE] [OPTIONS]

DATA INGESTION:
  -Ingest            Run data ingestion only (no training)
  -IngestGoogle      Fetch from Google Earth Engine
  -IngestMeteostat   Fetch from Meteostat (free, no API key)
  -IngestTides       Fetch from WorldTides API
  -IngestDays <int>  Days of historical data (default: 30)
  -IngestFile <path> Ingest a specific CSV file
  -IngestDir <path>  Ingest all CSV files from directory

TRAINING MODES (mutually exclusive):
  -Quick             Fast training with default dataset
  -Full              Full progressive training (default)
  -PAGASA            PAGASA-specific training
  -Ultimate          Ultimate training with all features
  -Progressive       Progressive training (same as Ultimate)
  -Progressive6      Progressive training v1-v6 (thesis demonstration)

OPTIONS:
  -DryRun            Show execution plan only
  -JsonLogs          Emit structured JSON logs (CI-friendly)
  -SkipIngestion     Skip data ingestion step in training modes
  -SkipValidation    Skip model validation step
  -CVFolds <int>     Cross-validation folds (default: 10)
  -Seed <int>        Random seed (default: 42)
  -Version <int>     Train specific version only (1-6, use with -Progressive6)

EXAMPLES:
  # Ingest data only
  ./run_training_pipeline.ps1 -Ingest -IngestMeteostat -IngestDays 30

  # Ingest from multiple sources
  ./run_training_pipeline.ps1 -Ingest -IngestMeteostat -IngestTides -IngestDays 7

  # Full training pipeline (includes ingestion)
  ./run_training_pipeline.ps1 -Full -IngestMeteostat -IngestDays 30

  # Quick training without ingestion
  ./run_training_pipeline.ps1 -Quick -SkipIngestion

  # Progressive v1-v6 training (all versions)
  ./run_training_pipeline.ps1 -Progressive6

  # Progressive v1-v6 quick mode
  ./run_training_pipeline.ps1 -Progressive6 -Quick

  # Train only v5
  ./run_training_pipeline.ps1 -Progressive6 -Version 5

  # Dry run to see what would happen
  ./run_training_pipeline.ps1 -Full -DryRun
"@
    return
}

# =========================
# STRICT ARGUMENT VALIDATION
# =========================

# Check if this is ingest-only mode
$IngestOnly = $Ingest -and -not $Quick -and -not $Full -and -not $PAGASA -and -not $Ultimate -and -not $Progressive -and -not $Progressive6

# Check if any ingest source is specified
$HasIngestSource = $IngestGoogle -or $IngestMeteostat -or $IngestTides -or $IngestFile -or $IngestDir

# Training mode validation
$modes = @($Quick, $Full, $PAGASA, $Ultimate, $Progressive, $Progressive6) | Where-Object { $_ }
if ($modes.Count -gt 1) {
    Write-Error "Only one training mode may be specified"
    exit 1
}

# Default to Full mode if no mode specified and not ingest-only
if (-not $Quick -and -not $Full -and -not $PAGASA -and -not $Ultimate -and -not $Progressive -and -not $Progressive6 -and -not $IngestOnly) {
    if (-not $Ingest) {
        $Full = $true
    }
}

if ($PAGASA -and ($Ultimate -or $Progressive)) {
    Write-Error "PAGASA cannot be combined with Ultimate/Progressive"
    exit 1
}

# Version parameter validation
if ($Version -and -not $Progressive6) {
    Write-Error "Version parameter can only be used with -Progressive6 mode"
    exit 1
}

if ($Version -and ($Version -lt 1 -or $Version -gt 6)) {
    Write-Error "Version must be between 1 and 6"
    exit 1
}

if ($PAGASA -and ($Ultimate -or $Progressive)) {
    Write-Error "PAGASA cannot be combined with Ultimate/Progressive"
    exit 1
}

if ($CVFolds -lt 2 -or $CVFolds -gt 20) {
    Write-Error "CVFolds must be between 2 and 20"
    exit 1
}

if ($Seed -lt 0) {
    Write-Error "Seed must be non-negative"
    exit 1
}

if ($IngestDays -lt 1 -or $IngestDays -gt 365) {
    Write-Error "IngestDays must be between 1 and 365"
    exit 1
}

# If ingest-only mode, require at least one source
if ($IngestOnly -and -not $HasIngestSource) {
    Write-Error "Ingest mode requires at least one source: -IngestGoogle, -IngestMeteostat, -IngestTides, -IngestFile, or -IngestDir"
    exit 1
}

# =========================
# LOGGING
# =========================
$PipelineStart = Get-Date
$Warnings = @()

function Emit-Log {
    param(
        [string]$Level,
        [string]$Message
    )

    $entry = @{
        timestamp = (Get-Date).ToString("s")
        level     = $Level
        message   = $Message
    }

    if ($JsonLogs) {
        $entry | ConvertTo-Json -Compress | Write-Host
    }
    else {
        Write-Host "[$($entry.timestamp)][$Level] $Message"
    }

    if ($LogFile) {
        $entry | ConvertTo-Json -Compress | Add-Content -Path $LogFile
    }
}

# =========================
# PROGRESS INDICATOR
# =========================
function Progress-Tick {
    Write-Host -NoNewline "."
    Start-Sleep -Seconds 10
}

# =========================
# EXECUTION WRAPPER
# =========================
function Run-Step {
    param(
        [string]$Name,
        [scriptblock]$Action,
        [switch]$Critical
    )

    Emit-Log "INFO" "START: $Name"

    if ($DryRun) {
        Emit-Log "INFO" "DRY-RUN: skipped execution"
        return
    }

    try {
        $job = Start-Job $Action
        while ($job.State -eq "Running") {
            Progress-Tick
        }
        Receive-Job $job | Out-Null
        Remove-Job $job

        Emit-Log "INFO" "END: $Name"
    }
    catch {
        if ($Critical) {
            Emit-Log "ERROR" "FAILED: $Name :: $_"
            exit 1
        }
        else {
            Emit-Log "WARN" "WARN: $Name :: $_"
            $Warnings += "$Name :: $_"
        }
    }
}

# =========================
# ENVIRONMENT CHECKS
# =========================
Run-Step "Python availability" {
    python --version | Out-Null
} -Critical

Run-Step "Python version >= 3.10" {
    $code = @"
import sys
assert sys.version_info >= (3,10)
"@
    $code | python -
} -Critical

Run-Step "Dependencies check" {
    $code = @"
import pandas, numpy, sklearn, joblib
"@
    $code | python -
} -Critical

# =========================
# DIRECTORY SETUP
# =========================
# Since script is in backend/models/, go up one level to backend/
$BackendDir = Split-Path -Parent $PSScriptRoot
$ScriptsPath = Join-Path $BackendDir "scripts"  # Use backend/scripts/ not backend/models/scripts/
$DataPath = Join-Path $BackendDir $DataDir
$ModelPath = Join-Path $BackendDir $ModelDir
$ReportPath = Join-Path $BackendDir $ReportDir

if (-not $DryRun) {
    New-Item -ItemType Directory -Force -Path $DataPath, $ModelPath, $ReportPath | Out-Null
}

# =========================
# GOOGLE CREDENTIALS SETUP
# =========================
$CredentialsFile = Join-Path $BackendDir "astral-archive-482008-g2-b4f2279053c0.json"
if (Test-Path $CredentialsFile) {
    $env:GOOGLE_APPLICATION_CREDENTIALS = $CredentialsFile
    Emit-Log "INFO" "Google credentials file found"
}
elseif ($IngestGoogle) {
    Emit-Log "WARN" "Google credentials file not found (Earth Engine may not work)"
}

# Set Google Cloud environment variables
$env:GOOGLE_CLOUD_PROJECT = "astral-archive-482008-g2"
$env:EARTHENGINE_PROJECT = "astral-archive-482008-g2"
$env:GOOGLE_SERVICE_ACCOUNT_EMAIL = "floodingnaque@astral-archive-482008-g2.iam.gserviceaccount.com"

# =========================
# PIPELINE EXECUTION
# =========================
Emit-Log "INFO" "PIPELINE START"
if ($IngestOnly) {
    Emit-Log "INFO" "MODE: INGEST-ONLY"
}
else {
    Emit-Log "INFO" "MODE: $(if($Progressive6){'PROGRESSIVE_V6'}elseif($PAGASA){'PAGASA'}elseif($Ultimate -or $Progressive){'ULTIMATE'}elseif($Quick){'QUICK'}else{'FULL'})"
    if ($Progressive6 -and $Version) {
        Emit-Log "INFO" "Training only version: v$Version"
    }
}
Emit-Log "INFO" "Seed=$Seed CVFolds=$CVFolds DryRun=$DryRun"

# =========================
# DATA INGESTION STEP
# =========================
if ($HasIngestSource -and -not $SkipIngestion) {
    Emit-Log "INFO" "=== DATA INGESTION ==="

    # Build ingestion arguments
    $IngestArgs = @()

    if ($IngestFile) {
        $IngestArgs += "--file"
        $IngestArgs += $IngestFile
    }
    elseif ($IngestDir) {
        $IngestArgs += "--dir"
        $IngestArgs += $IngestDir
    }
    else {
        if ($IngestGoogle) {
            $IngestArgs += "--fetch-google"
        }
        if ($IngestMeteostat) {
            $IngestArgs += "--fetch-meteostat"
        }
        if ($IngestTides) {
            $IngestArgs += "--fetch-tides"
        }
        $IngestArgs += "--days"
        $IngestArgs += $IngestDays
    }

    $IngestScript = Join-Path $ScriptsPath "ingest_training_data.py"

    $sources = @()
    if ($IngestGoogle) { $sources += "Google" }
    if ($IngestMeteostat) { $sources += "Meteostat" }
    if ($IngestTides) { $sources += "WorldTides" }
    if ($IngestFile) { $sources += "File: $IngestFile" }
    if ($IngestDir) { $sources += "Dir: $IngestDir" }

    Run-Step "Data ingestion ($($sources -join ', '))" {
        param($script, $args)
        & python $script @args
    }.GetNewClosure() -Critical

    # Actually run it (Run-Step uses jobs which don't work well with params)
    if (-not $DryRun) {
        Emit-Log "INFO" "Running: python $IngestScript $($IngestArgs -join ' ')"
        & python $IngestScript @IngestArgs
        if ($LASTEXITCODE -ne 0) {
            Emit-Log "ERROR" "Data ingestion failed with exit code: $LASTEXITCODE"
            exit 1
        }
        Emit-Log "INFO" "Data ingestion completed"
    }
}

# Exit if ingest-only mode
if ($IngestOnly) {
    Emit-Log "INFO" "Ingest-only mode completed"
    $TotalMinutes = [math]::Round(((Get-Date) - $PipelineStart).TotalMinutes, 2)
    Emit-Log "INFO" "PIPELINE COMPLETE in $TotalMinutes minutes"
    exit 0
}

# =========================
# TRAINING EXECUTION
# =========================
Emit-Log "INFO" "=== MODEL TRAINING ==="

if ($PAGASA) {
    Run-Step "PAGASA preprocess" {
        python (Join-Path $using:ScriptsPath "preprocess_pagasa_data.py") --create-training
    } -Critical

    Run-Step "PAGASA train" {
        python (Join-Path $using:ScriptsPath "train_pagasa.py")
    } -Critical
}
elseif ($Ultimate -or $Progressive) {
    Run-Step "Dataset preparation" {
        python (Join-Path $using:ScriptsPath "preprocess_pagasa_data.py") --create-training
        python (Join-Path $using:ScriptsPath "preprocess_official_flood_records.py")
    }

    Run-Step "Ultimate training" {
        python (Join-Path $using:ScriptsPath "train_ultimate.py") --cv-folds $using:CVFolds --progressive
    } -Critical
}
elseif ($Progressive6) {
    # Build arguments for progressive v6 training
    $ProgressiveArgs = @()
    $ProgressiveArgs += "--cv-folds"
    $ProgressiveArgs += $CVFolds

    if ($Quick) {
        $ProgressiveArgs += "--quick"
    }

    if ($Version) {
        $ProgressiveArgs += "--version"
        $ProgressiveArgs += $Version
    }

    $ProgressiveScript = Join-Path $ScriptsPath "train_progressive_v6.py"

    if (-not $DryRun) {
        Emit-Log "INFO" "Running: python $ProgressiveScript $($ProgressiveArgs -join ' ')"
        & python $ProgressiveScript @ProgressiveArgs
        if ($LASTEXITCODE -ne 0) {
            Emit-Log "ERROR" "Progressive v6 training failed with exit code: $LASTEXITCODE"
            exit 1
        }
        Emit-Log "INFO" "Progressive v6 training completed"
    }
    else {
        Emit-Log "INFO" "DRY-RUN: Would run progressive v6 training"
    }
}
elseif ($Quick) {
    Run-Step "Quick training" {
        python (Join-Path $using:ScriptsPath "train.py") --data "data/processed/cumulative_up_to_2025.csv"
    } -Critical
}
else {
    Run-Step "Full progressive training" {
        python (Join-Path $using:ScriptsPath "progressive_train.py") --grid-search --cv-folds $using:CVFolds
    } -Critical
}

if (-not $SkipValidation) {
    Run-Step "Validation" {
        $validationOutput = Join-Path $using:ReportPath "validation.json"
        python (Join-Path $using:ScriptsPath "validate_model.py") --json | Out-File $validationOutput
    }
}

Run-Step "Evaluation" {
    python (Join-Path $using:ScriptsPath "evaluate_model.py")
}

# =========================
# SUMMARY
# =========================
$TotalMinutes = [math]::Round(((Get-Date) - $PipelineStart).TotalMinutes, 2)

$summary = @{
    success          = ($Warnings.Count -eq 0)
    warnings         = $Warnings
    duration_minutes = $TotalMinutes
    dry_run          = $DryRun
    ingest_only      = $IngestOnly
    completed_at     = (Get-Date).ToString("s")
}

$summaryFile = Join-Path $ReportPath "pipeline_summary.json"
$summary | ConvertTo-Json -Depth 3 | Out-File $summaryFile

Emit-Log "INFO" "PIPELINE COMPLETE in $TotalMinutes minutes"

if ($Warnings.Count -gt 0) {
    exit 2
}

exit 0
