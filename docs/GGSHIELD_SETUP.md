# GitGuardian ggshield Setup Guide

This guide covers the installation and configuration of ggshield for secret detection in the Floodingnaque project.

## Overview

**ggshield** is GitGuardian's CLI tool that scans your code for secrets (API keys, passwords, tokens, etc.) before they get committed to version control.

We use ggshield via **pipx** (isolated global installation) rather than in the project's virtual environment to avoid dependency conflicts.

---

## Installation

### Prerequisites

- Python 3.8+ installed
- pip available in your terminal

### Step 1: Install pipx

pipx installs Python applications in isolated environments, preventing dependency conflicts.

```powershell
# Install pipx
pip install pipx

# Ensure pipx binaries are in your PATH
pipx ensurepath
```

> **Note**: After running `ensurepath`, restart your terminal or run the following to update PATH in the current session:
> ```powershell
> $env:PATH = "$env:USERPROFILE\.local\bin;$env:PATH"
> ```

### Step 2: Install ggshield via pipx

```powershell
pipx install ggshield
```

### Step 3: Verify Installation

```powershell
ggshield --version
# Expected output: ggshield, version 1.46.0 (or later)
```

---

## Authentication (Optional but Recommended)

ggshield works in two modes:

1. **Unauthenticated**: Basic local scanning with limited features
2. **Authenticated**: Full GitGuardian platform integration with dashboard, policies, and historical tracking

### Option A: Interactive Login

```powershell
ggshield auth login
```

This opens a browser for GitGuardian authentication.

### Option B: API Key (CI/CD)

1. Get your API key from [GitGuardian Dashboard](https://dashboard.gitguardian.com/api/personal-access-tokens)
2. Set the environment variable:

```powershell
# PowerShell (current session)
$env:GITGUARDIAN_API_KEY = "your-api-key-here"  # pragma: allowlist secret

# PowerShell (permanent - user level)
[Environment]::SetEnvironmentVariable("GITGUARDIAN_API_KEY", "your-api-key-here", "User")  # pragma: allowlist secret
```

For CI/CD, add `GITGUARDIAN_API_KEY` as a secret in your pipeline configuration.

### Verify Authentication

```powershell
ggshield auth status
```

---

## Pre-commit Integration

ggshield is configured to run automatically on every commit via pre-commit hooks.

### Configuration

The hook is defined in `.pre-commit-config.yaml`:

```yaml
# GitGuardian secret scanning
# Requires: pipx install ggshield (installed globally via pipx)
# Configure: ggshield auth login (or set GITGUARDIAN_API_KEY env var)
- repo: local
  hooks:
    - id: ggshield
      name: ggshield secret scan
      entry: ggshield secret scan pre-commit
      language: system
      stages: [pre-commit]
      pass_filenames: true
```

### Install Pre-commit Hooks

```powershell
cd floodingnaque
pre-commit install
```

### Test the Hook

```powershell
# Run ggshield on all files
pre-commit run ggshield --all-files

# Run all pre-commit hooks
pre-commit run --all-files
```

---

## Manual Scanning

### Scan Current Directory

```powershell
ggshield secret scan path .
```

### Scan Specific Files

```powershell
ggshield secret scan path backend/app/core/config.py
```

### Scan Git History

```powershell
# Scan last 10 commits
ggshield secret scan repo . --commits-limit 10

# Scan entire history (can be slow)
ggshield secret scan repo .
```

### Scan a Specific Commit

```powershell
ggshield secret scan commit HEAD
```

---

## Handling Detected Secrets

### If ggshield Finds a Secret

1. **DO NOT COMMIT** - The pre-commit hook will block the commit
2. **Remove the secret** from your code
3. **Use environment variables** instead:
   ```python
   # Bad
   API_KEY = "sk-1234567890abcdef"  # pragma: allowlist secret

   # Good
   import os
   API_KEY = os.environ.get("API_KEY")
   ```
4. **If already committed**: Consider the secret compromised and rotate it immediately

### Ignoring False Positives

If ggshield flags something that isn't actually a secret:

#### Option 1: Inline Ignore

Add a comment to ignore a specific line:

```python
password = "not-a-real-secret"  # ggshield:ignore  # pragma: allowlist secret
```

#### Option 2: Create a .gitguardian.yaml Config

Create `.gitguardian.yaml` in the project root:

```yaml
# .gitguardian.yaml
secret:
  ignored-paths:
    - "**/test_*.py"
    - "**/*_test.py"
    - "**/fixtures/**"

  ignored-matches:
    - name: "Test API key"
      match: "test-api-key-.*"
```

#### Option 3: Add to GitGuardian Dashboard

If authenticated, you can mark false positives in the GitGuardian dashboard for team-wide ignoring.

---

## CI/CD Integration

### GitHub Actions

Add to `.github/workflows/security.yml`:

```yaml
name: Security Scan

on: [push, pull_request]

jobs:
  ggshield:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Required for scanning commits

      - name: GitGuardian Scan
        uses: GitGuardian/ggshield-action@v1
        env:
          GITGUARDIAN_API_KEY: ${{ secrets.GITGUARDIAN_API_KEY }}
```

### GitLab CI

Add to `.gitlab-ci.yml`:

```yaml
ggshield:
  image: gitguardian/ggshield:latest
  stage: test
  script:
    - ggshield secret scan ci
  variables:
    GITGUARDIAN_API_KEY: $GITGUARDIAN_API_KEY
```

---

## Troubleshooting

### "ggshield is not recognized"

The pipx bin directory is not in your PATH.

```powershell
# Add to current session
$env:PATH = "$env:USERPROFILE\.local\bin;$env:PATH"

# Or reinstall with ensurepath
pipx ensurepath
# Then restart terminal
```

### Pre-commit Hook Fails with Virtualenv Error

This happens when using `repo: https://github.com/gitguardian/ggshield` on Windows with spaces in the user path. Solution: Use the local system hook instead (already configured).

### "No API key found"

Either authenticate or set the environment variable:

```powershell
ggshield auth login
# or
$env:GITGUARDIAN_API_KEY = "your-key"  # pragma: allowlist secret
```

### Scanning is Slow

For large repositories:

```powershell
# Limit commit history depth
ggshield secret scan repo . --commits-limit 50

# Scan only staged files (pre-commit does this automatically)
ggshield secret scan pre-commit
```

---

## Best Practices

1. **Never commit secrets** - Use environment variables or secret managers
2. **Use `.env` files** - But add them to `.gitignore`
3. **Rotate exposed secrets immediately** - Even if caught before push
4. **Enable branch protection** - Require ggshield to pass before merging
5. **Regular full scans** - Periodically scan entire history for old secrets

---

## Related Documentation

- [GitGuardian ggshield Documentation](https://docs.gitguardian.com/ggshield-docs/getting-started)
- [Pre-commit Framework](https://pre-commit.com/)
- [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)

---

## Quick Reference

| Command | Description |
|---------|-------------|
| `pipx install ggshield` | Install ggshield globally |
| `ggshield auth login` | Authenticate with GitGuardian |
| `ggshield auth status` | Check authentication status |
| `ggshield secret scan path .` | Scan current directory |
| `ggshield secret scan pre-commit` | Scan staged files |
| `ggshield secret scan repo .` | Scan git history |
| `pre-commit run ggshield --all-files` | Run via pre-commit |
