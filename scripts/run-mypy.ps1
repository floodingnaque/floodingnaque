#!/usr/bin/env pwsh
# Pre-commit wrapper for mypy - runs from the backend/ directory
# using the project's virtual environment.

$ErrorActionPreference = "Stop"

# Resolve venv Python (support both venv/ and .venv/)
$root = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $root "venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    $venvPython = Join-Path $root ".venv\Scripts\python.exe"
}
if (-not (Test-Path $venvPython)) {
    Write-Error "Could not find venv Python at $root\venv or $root\.venv"
    exit 1
}

Push-Location (Join-Path $root "backend")
try {
    & $venvPython -m mypy --ignore-missing-imports --no-error-summary --config-file mypy.ini app
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
