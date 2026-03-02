# Floodingnaque Backend API

Version 2.0 - Production-Ready Enterprise Backend

A Flask-based REST API for flood prediction using machine learning and weather data ingestion.

## Table of Contents

- [Overview](#overview)
- [Version 2.0 Release Notes](#version-20-release-notes)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Reference](#api-reference)
- [Frontend Integration](#frontend-integration)
- [Project Structure](#project-structure)
- [Features](#features)
- [Documentation](#documentation)
- [License](#license)

## Overview

The Floodingnaque Backend API provides a comprehensive solution for flood risk prediction in Paranaque City. The system integrates machine learning models with real-time weather data to deliver accurate flood risk assessments through a RESTful interface.

## Version 2.0 Release Notes

### Database Enhancements

| Feature | Description |
|---------|-------------|
| Production Tables | 4 tables: weather_data, predictions, alert_history, model_registry |
| Performance Indexes | 10 indexes providing 80% faster query execution |
| Data Integrity | 15+ constraints ensuring data consistency |
| Audit Trail | Complete operation logging for all database transactions |

### Security Improvements

| Feature | Description |
|---------|-------------|
| Credential Management | All credentials secured via environment variables |
| Input Validation | 15+ validators for comprehensive request validation |
| Injection Protection | SQL injection and XSS attack prevention |
| Rate Limiting | Configurable request rate limiting support |

### Performance Optimizations

| Feature | Description |
|---------|-------------|
| Query Performance | 83% improvement in database query execution |
| Connection Pooling | 20 connections with 10 overflow capacity |
| Health Checks | Automatic connection health monitoring |
| Connection Recycling | 1-hour connection lifecycle management |

### Documentation Updates

| Feature | Description |
|---------|-------------|
| Coverage | 2,000+ lines of comprehensive technical guides |
| Migration System | Database migration documentation and tooling |
| Deployment | Production deployment guides included |
| Academic | Thesis-defense ready documentation |

For complete architectural details, refer to [BACKEND_ARCHITECTURE.md](docs/BACKEND_ARCHITECTURE.md).

## Prerequisites

- Python 3.13 or higher
- pip package manager
- OpenWeatherMap API key
- Weatherstack API key (optional)

## Installation

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 2: Train the Model

Required for first-time setup only:

```bash
python scripts/train.py
```

## Configuration

Create a `.env` file in the `backend/` directory with the following variables:

```env
DATABASE_URL=sqlite:///floodingnaque.db
OWM_API_KEY=your_openweathermap_api_key_here
METEOSTAT_API_KEY=your_weatherstack_api_key_here
PORT=5000
HOST=0.0.0.0
FLASK_DEBUG=False
```

### Core Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| DATABASE_URL | Database connection string | Yes | sqlite:///floodingnaque.db |
| OWM_API_KEY | OpenWeatherMap API key | Yes | - |
| WEATHERSTACK_API_KEY | Weatherstack API key | No | - |
| PORT | Server port number | Yes | 5000 |
| HOST | Server host address | Yes | 0.0.0.0 |
| FLASK_DEBUG | Enable debug mode | No | False |
| APP_ENV | Environment (development/staging/production) | No | development |

### Training Pipeline Environment Variables (FLOODINGNAQUE_*)

These environment variables control the ML training pipeline and override YAML configuration values:

| Variable | Description | Default |
|----------|-------------|---------|
| FLOODINGNAQUE_ENV | Environment name (development/staging/production) | development |
| FLOODINGNAQUE_MLFLOW_URI | MLflow tracking server URI | mlruns |
| FLOODINGNAQUE_ENABLE_MLFLOW | Enable/disable MLflow tracking (true/false) | true |
| FLOODINGNAQUE_MODELS_DIR | Models directory path | models |
| FLOODINGNAQUE_DATA_DIR | Raw data directory path | data |
| FLOODINGNAQUE_PROCESSED_DIR | Processed data directory path | data/processed |
| FLOODINGNAQUE_LOG_LEVEL | Logging level (DEBUG/INFO/WARNING/ERROR) | INFO |
| FLOODINGNAQUE_LOG_DIR | Log directory path | logs |
| FLOODINGNAQUE_RANDOM_STATE | Random seed for reproducibility | 42 |
| FLOODINGNAQUE_CV_FOLDS | Number of cross-validation folds | 10 |
| FLOODINGNAQUE_BACKUP_DIR | Backup directory path | backups |
| FLOODINGNAQUE_MAX_BACKUPS | Maximum number of backups to retain | 5 |
| FLOODINGNAQUE_MAX_RETRIES | Maximum API retry attempts | 3 |
| FLOODINGNAQUE_RETRY_DELAY | Delay between API retries (seconds) | 1 |
| FLOODINGNAQUE_VALIDATE_CONFIG | Enable/disable config schema validation | true |
| FLOODINGNAQUE_STRICT_VALIDATION | Fail on validation errors (vs warning only) | false |

### Feature Flag Environment Variables

Feature flags can be overridden via environment variables with the `FLOODINGNAQUE_FLAG_` prefix:

```env
# Examples
FLOODINGNAQUE_FLAG_MLFLOW_TRACKING=true
FLOODINGNAQUE_FLAG_DRIFT_DETECTION=false
FLOODINGNAQUE_FLAG_API_RATE_LIMITING=true
```

See `config/feature_flags.yaml` for all available flags.

### Configuration Files

The configuration system supports multiple file types in `backend/config/`:

| File | Description |
|------|-------------|
| `training_config.yaml` | Base training configuration |
| `development.yaml` | Development environment overrides |
| `staging.yaml` | Staging environment overrides |
| `production.yaml` | Production environment overrides |
| `feature_flags.yaml` | Feature flag configuration |
| `secrets.yaml` | Secrets (copy from secrets.yaml.template) |

### Configuration Hot-Reload

Configuration can be reloaded without restarting the server:

**Via API (requires admin access):**
```bash
curl -X POST http://localhost:5000/api/v1/config/reload \
  -H "X-API-Key: your-admin-key"
```

**Via SIGHUP signal (Unix only):**
```bash
kill -SIGHUP <pid>
```

## Usage

### Development Server

```bash
python main.py
```

### Production Server

**Linux, macOS, or Docker:**

```bash
gunicorn --bind 0.0.0.0:$PORT --workers 4 --threads 2 --timeout 120 main:app
```

**Windows:**

```bash
waitress-serve --host=0.0.0.0 --port=5000 --threads=4 main:app
```

## API Reference

### Base URL

```
http://localhost:5000
```

### Available Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Returns API information |
| GET | `/api/v1/status` | Returns basic health status |
| GET | `/api/v1/health` | Returns detailed health metrics |
| GET | `/api/v1/ingest` | Returns ingestion endpoint usage information |
| POST | `/api/v1/ingest` | Ingests weather data for specified coordinates |
| GET | `/api/v1/data` | Retrieves historical weather data |
| POST | `/api/v1/predict` | Returns flood risk prediction with 3-level classification |
| GET | `/api/docs` | Returns API documentation |
| GET | `/api/version` | Returns API version information |
| GET | `/api/models` | Returns list of available model versions |

### Request Examples

**Ingest Weather Data:**

```bash
curl -X POST http://localhost:5000/api/v1/ingest \
  -H "Content-Type: application/json" \
  -d '{"lat": 14.6, "lon": 120.98}'
```

**Retrieve Historical Data:**

```bash
curl http://localhost:5000/api/v1/data?limit=10
```

**Predict Flood Risk:**

```bash
curl -X POST http://localhost:5000/api/v1/predict \
  -H "Content-Type: application/json" \
  -d '{"temperature": 298.15, "humidity": 65.0, "precipitation": 5.0}'
```

## Frontend Integration

The API supports Cross-Origin Resource Sharing (CORS) for frontend integration. All endpoints return JSON responses with consistent error handling.

### Response Format

**Success Response:**

```json
{
  "data": {},
  "request_id": "uuid-string"
}
```

**Error Response:**

```json
{
  "error": "Error message",
  "request_id": "uuid-string"
}
```

## Project Structure

```
backend/
├── main.py                     # Application entry point
├── app/                        # Main application code
│   ├── __init__.py
│   ├── api/                    # API layer
│   │   ├── __init__.py
│   │   ├── app.py              # Flask application factory
│   │   ├── routes/             # API route blueprints
│   │   │   ├── __init__.py
│   │   │   ├── data.py         # Data retrieval endpoints
│   │   │   ├── health.py       # Health check endpoints
│   │   │   ├── ingest.py       # Weather data ingestion endpoints
│   │   │   ├── models.py       # Model management endpoints
│   │   │   └── predict.py      # Prediction endpoints
│   │   ├── middleware/         # Request middleware
│   │   │   ├── __init__.py
│   │   │   ├── auth.py         # Authentication middleware
│   │   │   ├── logging.py      # Request logging middleware
│   │   │   ├── rate_limit.py   # Rate limiting middleware
│   │   │   └── security.py     # Security headers middleware
│   │   └── schemas/            # Request/response validation
│   │       ├── __init__.py
│   │       ├── prediction.py   # Prediction schemas
│   │       └── weather.py      # Weather data schemas
│   ├── core/                   # Core functionality
│   │   ├── __init__.py
│   │   ├── config.py           # Configuration management
│   │   ├── constants.py        # Application constants
│   │   ├── exceptions.py       # Custom exceptions
│   │   └── security.py         # Security utilities
│   ├── services/               # Business logic layer
│   │   ├── __init__.py
│   │   ├── alerts.py           # Alert notification system
│   │   ├── evaluation.py       # Model evaluation utilities
│   │   ├── ingest.py           # Weather data ingestion
│   │   ├── predict.py          # Flood prediction service
│   │   ├── risk_classifier.py  # 3-level risk classification
│   │   └── scheduler.py        # Background scheduled tasks
│   ├── models/                 # Database models
│   │   ├── __init__.py
│   │   └── db.py               # SQLAlchemy models
│   └── utils/                  # Utilities
│       ├── __init__.py
│       ├── utils.py            # Helper functions
│       └── validation.py       # Input validation helpers
├── scripts/                    # Utility scripts
│   ├── __init__.py
│   ├── train.py                # Model training script
│   ├── progressive_train.py    # Progressive training (v1-v4)
│   ├── preprocess_official_flood_records.py
│   ├── generate_thesis_report.py
│   ├── compare_models.py       # Model version comparison
│   ├── merge_datasets.py       # Merge multiple CSV files
│   ├── validate_model.py       # Model validation
│   ├── evaluate_model.py       # Model evaluation
│   ├── migrate_db.py           # Database migrations
│   └── inspect_db.py           # Database inspection
├── tests/                      # Test suite
│   ├── __init__.py
│   ├── unit/                   # Unit tests
│   ├── integration/            # Integration tests
│   └── security/               # Security tests
├── docs/                       # Documentation
├── data/                       # Data files
├── models/                     # ML models (versioned)
├── requirements.txt            # Python dependencies
├── Procfile                    # Production deployment config
├── Dockerfile                  # Docker configuration
└── pytest.ini                  # Pytest configuration
```

## Features

| Category | Features |
|----------|----------|
| API | RESTful architecture with comprehensive endpoints |
| Machine Learning | Flood prediction using trained classification models |
| Data Ingestion | Weather data from OpenWeatherMap and Weatherstack |
| Data Retrieval | Historical data access with pagination support |
| Debugging | Request ID tracking for request tracing |
| Security | CORS support for cross-origin frontend requests |
| Error Handling | Consistent JSON error responses |
| Deployment | Production-ready configuration |
| Monitoring | Sentry error tracking and performance monitoring |

## Documentation

| Document | Description |
|----------|-------------|
| [**Interactive API Explorer**](http://localhost:5000/apidocs) | 🔗 Try API calls directly in your browser |
| [OpenAPI Spec (JSON)](http://localhost:5000/openapi.json) | Download OpenAPI 3.1 schema for code generation |
| [OpenAPI Spec (YAML)](http://localhost:5000/openapi.yaml) | Download OpenAPI 3.1 schema in YAML format |
| [GETTING_STARTED.md](docs/GETTING_STARTED.md) | Quick start guide |
| [BACKEND_ARCHITECTURE.md](docs/BACKEND_ARCHITECTURE.md) | Complete backend architecture |
| [DATABASE_GUIDE.md](docs/DATABASE_GUIDE.md) | Database reference guide |
| [MODEL_MANAGEMENT.md](docs/MODEL_MANAGEMENT.md) | Model versioning and management |
| [POWERSHELL_API_EXAMPLES.md](docs/POWERSHELL_API_EXAMPLES.md) | PowerShell API examples |
| [SENTRY_SETUP.md](docs/SENTRY_SETUP.md) | Sentry error tracking setup |

### API Explorer Features

The interactive API explorer at `/apidocs` provides:
- **Try It Out**: Execute API calls directly from the browser
- **Request Examples**: Pre-filled example payloads for each endpoint
- **Response Previews**: See expected response formats
- **Authentication**: Test with API keys and JWT tokens
- **Schema Validation**: Automatic request validation

## License

This project is licensed under the MIT License. See the LICENSE file for details.

