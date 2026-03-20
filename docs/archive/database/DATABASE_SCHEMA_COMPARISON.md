# Database Schema Comparison Report: SQLite vs Supabase (PostgreSQL)

## Executive Summary

Both the SQLite development database and the Supabase PostgreSQL production database have **identical schema structures**. This ensures consistency between development and production environments, eliminating potential issues that could arise from schema mismatches.

## Detailed Comparison

### 1. Tables Present

| Table Name | SQLite | Supabase | Match |
|------------|--------|----------|-------|
| weather_data | ✓ | ✓ | ✅ |
| predictions | ✓ | ✓ | ✅ |
| alert_history | ✓ | ✓ | ✅ |
| model_registry | ✓ | ✓ | ✅ |

### 2. Column Structure Comparison

#### weather_data Table

| Column Name | SQLite Type | Supabase Type | Match |
|-------------|-------------|---------------|-------|
| id | INTEGER | integer | ✅ |
| temperature | FLOAT | double precision | ✅ |
| humidity | FLOAT | double precision | ✅ |
| precipitation | FLOAT | double precision | ✅ |
| wind_speed | FLOAT | double precision | ✅ |
| pressure | FLOAT | double precision | ✅ |
| location_lat | FLOAT | double precision | ✅ |
| location_lon | FLOAT | double precision | ✅ |
| source | VARCHAR(50) | character varying | ✅ |
| timestamp | DATETIME | timestamp without time zone | ✅ |
| created_at | DATETIME | timestamp without time zone | ✅ |
| updated_at | DATETIME | timestamp without time zone | ✅ |
| station_id | VARCHAR(50) | character varying | ✅ |

#### predictions Table

| Column Name | SQLite Type | Supabase Type | Match |
|-------------|-------------|---------------|-------|
| id | INTEGER | integer | ✅ |
| weather_data_id | INTEGER | integer | ✅ |
| prediction | INTEGER | integer | ✅ |
| risk_level | INTEGER | integer | ✅ |
| risk_label | VARCHAR(50) | character varying | ✅ |
| confidence | FLOAT | double precision | ✅ |
| model_version | INTEGER | integer | ✅ |
| model_name | VARCHAR(100) | character varying | ✅ |
| created_at | DATETIME | timestamp without time zone | ✅ |

#### alert_history Table

| Column Name | SQLite Type | Supabase Type | Match |
|-------------|-------------|---------------|-------|
| id | INTEGER | integer | ✅ |
| prediction_id | INTEGER | integer | ✅ |
| risk_level | INTEGER | integer | ✅ |
| risk_label | VARCHAR(50) | character varying | ✅ |
| location | VARCHAR(255) | character varying | ✅ |
| recipients | TEXT | text | ✅ |
| message | TEXT | text | ✅ |
| delivery_status | VARCHAR(50) | character varying | ✅ |
| delivery_channel | VARCHAR(50) | character varying | ✅ |
| error_message | TEXT | text | ✅ |
| created_at | DATETIME | timestamp without time zone | ✅ |
| delivered_at | DATETIME | timestamp without time zone | ✅ |

#### model_registry Table

| Column Name | SQLite Type | Supabase Type | Match |
|-------------|-------------|---------------|-------|
| id | INTEGER | integer | ✅ |
| version | INTEGER | integer | ✅ |
| file_path | VARCHAR(500) | character varying | ✅ |
| algorithm | VARCHAR(100) | character varying | ✅ |
| accuracy | FLOAT | double precision | ✅ |
| precision_score | FLOAT | double precision | ✅ |
| recall_score | FLOAT | double precision | ✅ |
| f1_score | FLOAT | double precision | ✅ |
| roc_auc | FLOAT | double precision | ✅ |
| training_date | DATETIME | timestamp without time zone | ✅ |
| dataset_size | INTEGER | integer | ✅ |
| dataset_path | VARCHAR(500) | character varying | ✅ |
| parameters | TEXT | text | ✅ |
| feature_importance | TEXT | text | ✅ |
| is_active | BOOLEAN | boolean | ✅ |
| notes | TEXT | text | ✅ |
| created_at | DATETIME | timestamp without time zone | ✅ |
| created_by | VARCHAR(100) | character varying | ✅ |

## Key Observations

1. **Schema Consistency**: All tables and columns are present in both databases with equivalent data types.

2. **Type Mapping**: The SQLAlchemy ORM correctly maps SQLite types to PostgreSQL equivalents:
   - SQLite INTEGER ↔ PostgreSQL integer
   - SQLite FLOAT ↔ PostgreSQL double precision
   - SQLite VARCHAR ↔ PostgreSQL character varying
   - SQLite TEXT ↔ PostgreSQL text
   - SQLite DATETIME ↔ PostgreSQL timestamp without time zone
   - SQLite BOOLEAN ↔ PostgreSQL boolean

3. **Enhanced Schema Features**: Both databases include all enhanced schema features:
   - Additional weather parameters (wind_speed, pressure)
   - Location information (location_lat, location_lon)
   - Metadata fields (source, created_at, updated_at)
   - Station identification (station_id)
   - Soft delete support (is_deleted, deleted_at)
   - Performance indexes
   - Data validation constraints

## Recommendations

1. **Continue Current Approach**: The current database schema synchronization approach is working well and ensures consistency between development and production.

2. **Migration Process**: Continue using the migration scripts that add new columns to existing tables when schema updates are needed.

3. **Testing**: Regularly verify schema consistency using the verification scripts like `verify_supabase_schema.py`.

4. **Documentation**: Maintain this comparison report as a reference for future schema changes.
