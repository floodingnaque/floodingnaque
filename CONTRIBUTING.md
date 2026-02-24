# Contributing to Floodingnaque

Thank you for your interest in contributing to Floodingnaque! This document outlines the process for contributing to the project.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Process](#development-process)
- [Code Style](#code-style)
- [Testing](#testing)
- [Documentation](#documentation)
- [Pull Request Process](#pull-request-process)
- [Reporting Issues](#reporting-issues)

## Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/<YOUR_USERNAME>/floodingnaque
   ```
3. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
4. Install dependencies:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

## Development Process

1. Create a new branch for your feature or bugfix:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. Make your changes
3. Write tests for your changes
4. Ensure all tests pass
5. Commit your changes with a clear, descriptive commit message
6. Push to your fork
7. Submit a pull request

## Code Style

We follow PEP 8 for Python code. Key points:

- Use 4 spaces for indentation
- Limit lines to 120 characters
- Use descriptive variable and function names
- Write docstrings for all public classes and functions
- Import statements should be at the top of the file, grouped logically

Run `flake8` to check for style issues:
```bash
flake8 .
```

## Testing

All contributions should include appropriate tests. We use pytest for testing.

Run tests with:
```bash
cd backend
python -m pytest tests/
```

## Documentation

- Update the README.md if you change functionality
- Document new APIs in the code with docstrings
- Update relevant documentation in the `docs/` directory

## Pull Request Process

1. Ensure your code passes all tests
2. Update documentation as needed
3. Write a clear, descriptive PR title
4. Include a detailed description of your changes
5. Reference any related issues
6. Request review from maintainers

## Reporting Issues

Please use the GitHub issue tracker to report bugs or suggest features. When reporting a bug, include:

- A clear description of the issue
- Steps to reproduce
- Expected vs actual behavior
- Screenshots if applicable
- Your environment details (OS, Python version, etc.)

Thank you for contributing!