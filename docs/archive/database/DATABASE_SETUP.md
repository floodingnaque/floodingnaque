# Database Setup Guide

## Overview
The application uses SQLite as the default database, configured through SQLAlchemy ORM.

## Database Configuration

### Default Setup (SQLite)
The database is configured to use SQLite by default:
- **Database file**: `floodingnaque.db` (located in the `backend/` directory)
- **Connection string**: `sqlite:///floodingnaque.db`

### Using a Different Database
To use PostgreSQL, MySQL, or another database, set the `DATABASE_URL` environment variable in a `.env` file:

```env
# For PostgreSQL
DATABASE_URL=postgresql://user:password@localhost/dbname

# For MySQL
DATABASE_URL=mysql://user:password@localhost/dbname

# For SQLite (default)
DATABASE_URL=sqlite:///floodingnaque.db
```

## Database Schema

### Table: `weather_data`
Stores weather data ingested from external APIs.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key (auto-increment) |
| temperature | FLOAT | Temperature in Kelvin (from OpenWeatherMap) |
| humidity | FLOAT | Humidity percentage |
| precipitation | FLOAT | Precipitation amount |
| timestamp | DATETIME | When the data was recorded |

## Initialization

The database is automatically initialized when you run the Flask application (`main.py`). The `init_db()` function creates all necessary tables if they don't exist.

To manually initialize the database:
```bash
python -c "from app.models.db import init_db; init_db()"
```

## Verifying Setup

To verify the database setup, run:
```bash
python scripts/inspect_db.py
```

This will show:
- All tables in the database
- Column information for each table
- Record counts

## Usage

The database is accessed through SQLAlchemy sessions. The `app/models/db.py` module provides:
- `WeatherData` model class for ORM operations
- `get_db_session()` context manager for database operations
- `init_db()` function to create tables

Example usage:
```python
from app.models.db import WeatherData, get_db_session
from datetime import datetime

# Create a new record
with get_db_session() as session:
    weather = WeatherData(
        temperature=298.15,
        humidity=65.0,
        precipitation=0.0,
        timestamp=datetime.now()
    )
    session.add(weather)
    # Session auto-commits on context exit

# Query records
with get_db_session() as session:
    records = session.query(WeatherData).all()
```

## Notes

- The database file (`floodingnaque.db`) is created automatically in the `backend/data/` directory
- Sessions are managed via context manager for proper cleanup
- For production, consider using PostgreSQL or MySQL instead of SQLite
