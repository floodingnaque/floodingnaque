# Floodingnaque API Test Suite

Comprehensive testing framework with 85%+ code coverage requirement.

## Quick Start

```bash
# Install dependencies
pip install -r ../requirements-dev.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test types
pytest -m unit              # Unit tests
pytest -m property          # Property-based tests
pytest -m contract          # Contract tests
pytest -m snapshot          # Snapshot tests
```

## Directory Structure

```
tests/
├── README.md                           # This file
├── conftest.py                         # Shared fixtures and configuration
├── strategies.py                       # Hypothesis strategies for property-based testing
│
├── unit/                               # Unit tests (fast, isolated)
│   ├── test_*.py                       # Standard unit tests
│   ├── test_property_based_validation.py    # Property tests for validation
│   └── test_property_based_prediction.py    # Property tests for predictions
│
├── integration/                        # Integration tests (require services)
│   └── test_*.py                       # End-to-end integration tests
│
├── contracts/                          # Contract tests (API compatibility)
│   ├── __init__.py
│   └── test_api_contracts.py          # API contract validation tests
│
├── snapshots/                          # Snapshot tests (regression detection)
│   ├── __init__.py
│   ├── test_model_snapshots.py        # ML model output snapshots
│   └── __snapshots__/                 # Snapshot data (auto-generated)
│
├── security/                           # Security tests
│   └── test_*.py                       # Security vulnerability tests
│
└── load/                               # Load/performance tests
    └── test_*.py                       # Load testing scenarios
```

## Test Categories

### Unit Tests (75% of suite)
**Location**: `tests/unit/`  
**Speed**: Fast (<5 seconds)  
**Purpose**: Test individual components in isolation

```bash
pytest -m unit
```

### Property-Based Tests
**Location**: `tests/unit/test_property_based_*.py`  
**Speed**: Medium (~10 seconds)  
**Purpose**: Automatically generate edge cases

```bash
pytest -m property
```

### Contract Tests
**Location**: `tests/contracts/`  
**Speed**: Fast (~3 seconds)  
**Purpose**: Ensure API backward compatibility

```bash
pytest -m contract
```

### Snapshot Tests
**Location**: `tests/snapshots/`  
**Speed**: Fast (~2 seconds)  
**Purpose**: Detect unintended output changes

```bash
pytest -m snapshot
```

### Integration Tests (15% of suite)
**Location**: `tests/integration/`  
**Speed**: Slow (~30 seconds)  
**Purpose**: Test end-to-end workflows

```bash
pytest -m integration
```

### Security Tests
**Location**: `tests/security/`  
**Speed**: Medium (~5 seconds)  
**Purpose**: Validate security measures

```bash
pytest -m security
```

## Key Files

### conftest.py
Shared fixtures for all tests:
- `app` - Flask application instance
- `client` - Test client
- `mock_model` - Mock ML model
- `valid_weather_data` - Sample weather data
- `valid_api_key` - Test API key

### strategies.py
Hypothesis strategies for generating test data:
- Weather data strategies
- Location/coordinate strategies
- Security testing strategies
- Model output strategies

## Common Commands

```bash
# Run tests by marker
pytest -m unit              # Unit tests only
pytest -m integration       # Integration tests only
pytest -m "not slow"        # Exclude slow tests
pytest -m "unit or property" # Multiple markers

# Run with coverage
pytest --cov=app --cov-report=html
pytest --cov=app --cov-report=term-missing

# Run in parallel (faster)
pytest -n auto

# Verbose output
pytest -v -s

# Stop on first failure
pytest -x

# Run only failed tests
pytest --lf

# Debug mode
pytest --pdb

# Update snapshots
pytest -m snapshot --snapshot-update
```

## Writing Tests

### Unit Test Example

```python
"""Tests for component X."""
import pytest
from app.module import function_to_test

class TestComponent:
    """Test suite for component."""

    def test_happy_path(self):
        """Test normal operation."""
        result = function_to_test(valid_input)
        assert result == expected_output

    def test_error_handling(self):
        """Test error conditions."""
        with pytest.raises(ExpectedError):
            function_to_test(invalid_input)
```

### Property-Based Test Example

```python
"""Property-based tests for component X."""
from hypothesis import given, settings
from tests.strategies import valid_temperature

class TestProperties:
    """Property-based test suite."""

    @given(temp=valid_temperature())
    @settings(max_examples=100, deadline=None)
    def test_temperature_invariant(self, temp):
        """Property: Temperature should always be valid."""
        result = validate_temperature(temp)
        assert -50 <= result <= 50
```

### Contract Test Example

```python
"""Contract tests for API endpoint."""
import pytest

class TestContracts:
    """API contract test suite."""

    @pytest.mark.contract
    def test_endpoint_response_schema(self, contract_client):
        """Contract: Endpoint returns expected schema."""
        response = contract_client.get('/api/endpoint')
        data = response.get_json()

        assert 'required_field' in data
        assert isinstance(data['required_field'], expected_type)
```

### Snapshot Test Example

```python
"""Snapshot tests for component outputs."""
from syrupy.assertion import SnapshotAssertion

class TestSnapshots:
    """Snapshot test suite."""

    @pytest.mark.snapshot
    def test_output_structure(self, snapshot: SnapshotAssertion):
        """Snapshot: Component output structure."""
        result = function_to_test(input_data)
        assert result == snapshot
```

## Test Markers

Add markers to categorize tests:

```python
@pytest.mark.unit           # Unit test
@pytest.mark.integration    # Integration test
@pytest.mark.property       # Property-based test
@pytest.mark.contract       # Contract test
@pytest.mark.snapshot       # Snapshot test
@pytest.mark.security       # Security test
@pytest.mark.slow          # Long-running test
@pytest.mark.model         # ML model test
```

## Coverage Requirements

- **Minimum**: 85% (enforced)
- **Target**: 90%+
- **Critical paths**: 100%

View coverage:
```bash
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

## CI/CD Integration

Tests run automatically on:
- Every commit
- Pull requests
- Pre-deployment

CI command:
```bash
pytest -m "not load" --cov=app --cov-fail-under=85 --cov-report=xml
```

## Troubleshooting

### Tests Failing?

```bash
# Run with verbose output
pytest -v -s

# Run specific test
pytest tests/unit/test_file.py::TestClass::test_method

# Debug with pdb
pytest --pdb tests/unit/test_file.py
```

### Coverage Not Met?

```bash
# Show missing lines
pytest --cov=app --cov-report=term-missing

# Focus on specific module
pytest --cov=app.services.predict --cov-report=term-missing
```

### Snapshot Tests Failing?

```bash
# View differences
pytest -m snapshot -vv

# Update if changes are intentional
pytest -m snapshot --snapshot-update
```

### Tests Too Slow?

```bash
# Run in parallel
pytest -n auto

# Skip slow tests
pytest -m "not slow"

# Profile tests
pytest --durations=10
```

## Best Practices

1. **One assertion per test** - Keep tests focused
2. **Use descriptive names** - Test names should explain what they test
3. **Use fixtures** - Share setup code with fixtures
4. **Mock external dependencies** - Tests should be isolated
5. **Test error paths** - Don't just test happy paths
6. **Keep tests fast** - Unit tests should run in milliseconds
7. **Document complex tests** - Add docstrings explaining the test

## Resources

- **Full Testing Guide**: `../docs/TESTING_GUIDE.md`
- **Quick Reference**: `../docs/TESTING_QUICK_REF.md`
- **Improvements Summary**: `../docs/TESTING_IMPROVEMENTS_SUMMARY.md`

## Getting Help

- Check documentation in `../docs/`
- Review example tests in `unit/` and `contracts/`
- Ask team members
- Create issue in repository

## Test Metrics

Current test suite:
- **Total Tests**: 150+
- **Unit Tests**: ~85
- **Property Tests**: ~20
- **Contract Tests**: ~15
- **Snapshot Tests**: ~12
- **Integration Tests**: ~10
- **Security Tests**: ~8
- **Coverage**: 85%+
- **Execution Time**: <30 seconds (parallel)

---

For detailed information, see [TESTING_GUIDE.md](../docs/TESTING_GUIDE.md)
