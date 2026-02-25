# Contributing to Floodingnaque

Thank you for your interest in contributing to Floodingnaque! This document outlines the process for contributing to the project.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Process](#development-process)
- [Pre-commit Hooks](#pre-commit-hooks)
- [Code Style](#code-style)
- [Testing](#testing)
- [Frontend Development](#frontend-development)
- [Documentation](#documentation)
- [Pull Request Process](#pull-request-process)
- [Reporting Issues](#reporting-issues)

## Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```powershell
   git clone https://github.com/<YOUR_USERNAME>/floodingnaque
   ```
3. Create a virtual environment:
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```
4. Install backend dependencies:
   ```powershell
   cd backend
   pip install -r requirements.txt -r requirements-dev.txt
   ```
5. Install frontend dependencies:
   ```powershell
   cd ..\frontend
   npm install
   ```
6. Install pre-commit hooks:
   ```powershell
   cd ..  # project root
   pip install pre-commit
   pre-commit install
   pre-commit install --hook-type commit-msg
   ```

## Development Process

1. Create a new branch for your feature or bugfix:
   ```powershell
   git checkout -b feature/your-feature-name
   ```
2. Make your changes
3. Write tests for your changes
4. Ensure all tests pass and pre-commit hooks are green
5. Commit your changes with a [Conventional Commit](https://www.conventionalcommits.org/) message:
   ```powershell
   git commit -m "feat: add rainfall threshold configuration"
   ```
6. Push to your fork
7. Submit a pull request

## Pre-commit Hooks

This project uses [pre-commit](https://pre-commit.com/) to enforce code quality on every commit. The following hooks run automatically:

| Hook | Scope | Purpose |
|------|-------|---------|
| **black** | Backend (`*.py`) | Code formatting (line-length 120) |
| **isort** | Backend (`*.py`) | Import sorting (black-compatible) |
| **flake8** | Backend (`*.py`) | Linting (max-complexity 15) |
| **mypy** | Backend (`app/**/*.py`) | Static type checking |
| **bandit** | Backend (`*.py`) | Security vulnerability scanning |
| **eslint** | Frontend (`src/**/*.{ts,tsx}`) | TypeScript/React linting |
| **tsc** | Frontend (`src/**/*.{ts,tsx}`) | TypeScript type checking |
| **check-yaml** | All YAML files | YAML syntax validation |
| **commitizen** | Commit messages | Conventional Commits enforcement |
| **ggshield** | Manual | Secret scanning (opt-in locally, automatic in CI) |

Run hooks manually against all files:
```powershell
pre-commit run --all-files
```

## Code Style

### Backend (Python)

We follow PEP 8 with the following project conventions:

- Use 4 spaces for indentation
- **Line length: 120 characters** (enforced by black/flake8)
- Use descriptive variable and function names
- Write docstrings for all public classes and functions
- Import statements should be at the top of the file, grouped logically
- **Type hints required** for all function signatures (enforced by mypy)

Check formatting:
```powershell
cd backend
black --check .
flake8 .
mypy app/
```

### Frontend (TypeScript/React)

- Follow the ESLint configuration in `eslint.config.js`
- Use functional components with hooks
- Theme with Tailwind CSS v4

Check linting:
```powershell
cd frontend
npm run lint
npx tsc -b --noEmit
```

## Testing

### Backend

All contributions should include appropriate tests. We use **pytest** for testing.

```powershell
cd backend

# Run all tests
python -m pytest tests/

# Run with coverage
python -m pytest tests/ --cov=app --cov-report=term-missing

# Run specific test file
python -m pytest tests/unit/test_prediction.py -v
```

### Frontend

We use **Vitest** for unit tests and **Playwright** for E2E tests.

```powershell
cd frontend

# Unit tests
npm run test

# E2E tests (requires backend running)
npx playwright test

# Type check
npx tsc -b --noEmit
```

## Frontend Development

```powershell
cd frontend
npm run dev       # Start dev server on http://localhost:3000
npm run build     # Production build to dist/
npm run preview   # Preview the production build locally
npm run lint      # Lint with ESLint
npm run test      # Run Vitest unit tests
```

Key directories:
- `src/components/` — Reusable UI components (shadcn/ui based)
- `src/pages/` — Route-level page components
- `src/stores/` — Zustand state management
- `src/services/` — API client and data fetching
- `src/lib/` — Shared utilities

## Documentation

- Update the README.md if you change functionality
- Document new APIs in the code with docstrings
- Update relevant documentation in the `docs/` directory

## Pull Request Process

1. Ensure your code passes all pre-commit hooks (`pre-commit run --all-files`)
2. Ensure all tests pass (backend and frontend)
3. Update documentation as needed
4. Write a clear, descriptive PR title using Conventional Commits format
5. Include a detailed description of your changes
6. Reference any related issues
7. Request review from maintainers

## Reporting Issues

Please use the GitHub issue tracker to report bugs or suggest features. When reporting a bug, include:

- A clear description of the issue
- Steps to reproduce
- Expected vs actual behavior
- Screenshots if applicable
- Your environment details (OS, Python version, Node.js version, etc.)

Thank you for contributing!