# Floodingnaque Data Schema Documentation

This document describes the expected columns and data types for all dataset types used in the Floodingnaque flood prediction system.

## Table of Contents
- [Raw Data Files](#raw-data-files)
  - [PAGASA Weather Station Data](#pagasa-weather-station-data)
  - [Official Flood Records](#official-flood-records)
- [Processed Data Files](#processed-data-files)
  - [Cumulative Training Dataset](#cumulative-training-dataset)
  - [Fetched Meteostat Data](#fetched-meteostat-data)
  - [PAGASA Merged Dataset](#pagasa-merged-dataset)
  - [Processed Flood Records](#processed-flood-records)
- [Data Quality Notes](#data-quality-notes)

---

## Raw Data Files

### PAGASA Weather Station Data

**Files:**
- `Floodingnaque_CADS-S0126006_NAIA Daily Data.csv`
- `Floodingnaque_CADS-S0126006_Port Area Daily Data.csv`
- `Floodingnaque_CADS-S0126006_Science Garden Daily Data.csv`

**Source:** Philippine Atmospheric, Geophysical and Astronomical Services Administration (PAGASA)

| Column | Type | Unit | Description |
|--------|------|------|-------------|
| `YEAR` | int | - | Year of observation (2020-2025) |
| `MONTH` | int | - | Month (1-12) |
| `DAY` | int | - | Day of month (1-31) |
| `RAINFALL` | float | mm | Daily total precipitation. `-1` indicates trace rainfall |
| `TMAX` | float | °C | Maximum temperature |
| `TMIN` | float | °C | Minimum temperature |
| `RH` | float | % | Relative humidity (0-100) |
| `WIND_SPEED` | float | m/s | Average wind speed |
| `WIND_DIRECTION` | float | ° | Wind direction in degrees (0-360) |

**Station Locations:**
| Station | Latitude | Longitude | Elevation (m) |
|---------|----------|-----------|---------------|
| NAIA | 14.5086 | 121.0194 | 21 |
| Port Area | 14.5833 | 120.9667 | 15 |
| Science Garden | 14.6500 | 121.0500 | 46 |

---

### Official Flood Records

**Files:**
- `Floodingnaque_Paranaque_Official_Flood_Records_2022.csv`
- `Floodingnaque_Paranaque_Official_Flood_Records_2023.csv`
- `Floodingnaque_Paranaque_Official_Flood_Records_2024.csv`
- `Floodingnaque_Paranaque_Official_Flood_Records_2025.csv`

**Source:** City of Parañaque Disaster Risk Reduction and Management Office (CDRRMO)

> ⚠️ **Note:** These files have irregular header formats. Rows 1-4 typically contain metadata and multi-row headers. Use `skiprows` or preprocessing when loading.
>
> **Recommended:** Use the cleaned versions in `data/cleaned/` instead:
> - `cleaned/Floodingnaque_Flood_Records_2022_cleaned.csv`
> - `cleaned/Floodingnaque_Flood_Records_2023_cleaned.csv`
> - `cleaned/Floodingnaque_Flood_Records_2024_cleaned.csv`
> - `cleaned/Floodingnaque_Flood_Records_2025_cleaned.csv`
> - `cleaned/Floodingnaque_Flood_Records_All_cleaned.csv` (combined)
>
> Generate cleaned files with: `python scripts/clean_raw_flood_records.py`

**Cleaned Files Schema:**

| Column | Type | Description |
|--------|------|-------------|
| `record_num` | int | Record sequence number |
| `date` | string | Date in YYYY-MM-DD format |
| `month` | int | Month (1-12) |
| `day` | int | Day of month |
| `year` | int | Year (2022-2025) |
| `barangay` | string | Barangay (village) name |
| `location` | string | Specific location/street |
| `latitude` | float | GPS latitude (WGS84) |
| `longitude` | float | GPS longitude (WGS84) |
| `flood_depth` | string | Standardized depth (gutter/ankle/knee/waist/chest) |
| `weather_disturbance` | string | Weather cause description |
| `remarks` | string | Additional notes |
| `time_reported` | float | Hour flood was reported (if available) |
| `time_subsided` | float | Hour flood subsided (if available) |

**Raw Files Expected Columns (after normalization):**

| Column | Type | Unit | Description |
|--------|------|------|-------------|
| `#` or `record_num` | int | - | Record sequence number |
| `DATE` | string | - | Date of flood event (various formats) |
| `MONTH` | string | - | Month name |
| `BARANGAY` | string | - | Barangay (village) name |
| `LOCATION` | string | - | Specific location/street |
| `LATITUDE` | float | ° | GPS latitude (WGS84) |
| `LONGITUDE` | float | ° | GPS longitude (WGS84) |
| `FLOOD_DEPTH` | string | - | Flood depth description (Gutter/Knee/Waist/Chest level) |
| `WEATHER_DISTURBANCES` | string | - | Weather cause (Typhoon, ITCZ, Monsoon, etc.) |
| `REMARKS` | string | - | Additional notes (subsided time, etc.) |

**Flood Depth Mapping:**
| Text | Depth (cm) | Severity |
|------|------------|----------|
| Gutter Level | 8 | 0 (Minor) |
| Ankle Level | 15 | 0 (Minor) |
| Knee Level | 48 | 1 (Moderate) |
| Waist Level | 100 | 2 (Severe) |
| Chest Level | 130 | 3 (Critical) |

---

## Processed Data Files

### Cumulative Training Dataset

**Files:**
- `processed/cumulative_v2_up_to_2022.csv`
- `processed/cumulative_v2_up_to_2023.csv`
- `processed/cumulative_v2_up_to_2024.csv`
- `processed/cumulative_v2_up_to_2025.csv`

**Description:** Main training dataset combining flood records with weather data and engineered features.

#### Core Columns

| Column | Type | Unit | Description |
|--------|------|------|-------------|
| `record_num` | float | - | Original record number |
| `year` | float | - | Year of event |
| `date` | string | YYYY-MM-DD | Event date |
| `month` | float | - | Month (1-12) |
| `day` | float | - | Day of month |
| `month_name` | string | - | Month name (JANUARY, etc.) |
| `latitude` | float | ° | Location latitude |
| `longitude` | float | ° | Location longitude |

#### Weather Columns

| Column | Type | Unit | Description |
|--------|------|------|-------------|
| `precipitation` | float | mm | Daily precipitation |
| `temperature` | float | °C | Average temperature |
| `humidity` | float | % | Relative humidity |
| `wind_speed` | float | m/s | Wind speed |
| `wind_direction` | float | ° | Wind direction |
| `temp_max` | float | °C | Maximum temperature |
| `temp_min` | float | °C | Minimum temperature |
| `temp_range` | float | °C | Temperature range (max - min) |

#### Weather Disturbance Flags

| Column | Type | Description |
|--------|------|-------------|
| `weather_disturbance` | string | Raw weather description |
| `is_typhoon` | int | 1 if typhoon-related |
| `is_itcz` | int | 1 if ITCZ-related |
| `is_sw_monsoon` | int | 1 if SW monsoon (Habagat) |
| `is_ne_monsoon` | int | 1 if NE monsoon (Amihan) |
| `is_easterlies` | int | 1 if Easterlies |
| `is_thunderstorm` | int | 1 if thunderstorm |
| `is_lpa` | int | 1 if Low Pressure Area |

#### Target Variables

| Column | Type | Description |
|--------|------|-------------|
| `flood` | int | Binary target (0=no flood, 1=flood) |
| `flood_depth_cm` | int | Flood depth in centimeters |
| `flood_severity` | int | Severity level (0-3) |
| `flood_depth_text` | string | Original depth description |

#### Engineered Features

| Column | Type | Description |
|--------|------|-------------|
| `precip_3day_sum` | float | 3-day rolling sum of precipitation |
| `precip_7day_sum` | float | 7-day rolling sum of precipitation |
| `precip_3day_avg` | float | 3-day rolling average precipitation |
| `precip_7day_avg` | float | 7-day rolling average precipitation |
| `precip_max_3day` | float | 3-day rolling max precipitation |
| `precip_max_7day` | float | 7-day rolling max precipitation |
| `precip_lag1` | float | Precipitation 1 day ago |
| `precip_lag2` | float | Precipitation 2 days ago |
| `rain_streak` | float | Consecutive rain days |
| `humidity_3day_avg` | float | 3-day rolling average humidity |
| `humidity_lag1` | float | Humidity 1 day ago |
| `temp_humidity_interaction` | float | Temperature × Humidity / 100 |
| `humidity_precip_interaction` | float | Humidity × Precipitation / 10 |
| `temp_precip_interaction` | float | Temperature × Precipitation / 10 |
| `monsoon_precip_interaction` | float | Monsoon flag × Precipitation |
| `saturation_risk` | int | High humidity + high precip flag |
| `heat_index` | float | Computed heat index |
| `is_monsoon_season` | float | 1 if June-November |

#### Spatial Features

| Column | Type | Description |
|--------|------|-------------|
| `nearest_station` | string | Nearest weather station ID |
| `distance_to_nearest_km` | float | Distance to nearest station |
| `station_key` | string | Station identifier |
| `station_lat` | float | Station latitude |
| `station_lon` | float | Station longitude |
| `elevation` | float | Station elevation (m) |

#### Location Features

| Column | Type | Description |
|--------|------|-------------|
| `barangay` | string | Original barangay name |
| `barangay_clean` | string | Normalized barangay name |
| `barangay_encoded` | int | Label-encoded barangay |
| `location` | string | Specific location details |
| `remarks` | string | Additional notes |

#### Time Features

| Column | Type | Description |
|--------|------|-------------|
| `time_reported` | float | Hour flood was reported |
| `time_subsided` | float | Hour flood subsided |
| `flood_duration_hours` | float | Duration in hours |

---

### Fetched Meteostat Data

**File:** `processed/fetched_meteostat.csv`

**Description:** Weather data fetched from Meteostat API for real-time predictions.

| Column | Type | Unit | Description |
|--------|------|------|-------------|
| `temperature` | float | K | Temperature in Kelvin |
| `precipitation` | float | mm | Daily precipitation |
| `date` | string | YYYY-MM-DD | Observation date |
| `humidity` | float | % | Relative humidity |
| `flood` | int | - | Flood occurrence (for labeled data) |

> **Note:** Historical humidity values may show 70 (default) if hourly data was unavailable. Updated service now fetches actual humidity from hourly observations.

---

### PAGASA Merged Dataset

**File:** `processed/pagasa_all_stations_merged.csv`

**Description:** Merged and enriched data from all three PAGASA stations with engineered features.

| Column | Type | Unit | Description |
|--------|------|------|-------------|
| `year` | int | - | Year |
| `month` | int | - | Month (1-12) |
| `day` | int | - | Day |
| `date` | string | YYYY-MM-DD | Full date |
| `station` | string | - | Station name (naia/port_area/science_garden) |
| `precipitation` | float | mm | Rainfall |
| `temp_max` | float | °C | Maximum temperature |
| `temp_min` | float | °C | Minimum temperature |
| `temperature` | float | °C | Average temperature |
| `temperature_kelvin` | float | K | Temperature in Kelvin |
| `humidity` | float | % | Relative humidity |
| `wind_speed` | float | m/s | Wind speed |
| `wind_direction` | float | ° | Wind direction |
| `latitude` | float | ° | Station latitude |
| `longitude` | float | ° | Station longitude |
| `elevation` | int | m | Station elevation |
| `season` | string | - | Season (wet/dry) |
| `is_monsoon_season` | int | - | Monsoon flag |
| ... | ... | ... | (Plus all engineered features as in cumulative) |
| `flood` | int | - | Flood occurrence |
| `flood_probability` | float | - | Predicted flood probability |
| `confirmed_flood_month` | int | - | Month had confirmed flood |

---

### Processed Flood Records

**Files:**
- `processed/processed_flood_records_v2_2022.csv`
- `processed/processed_flood_records_v2_2023.csv`
- `processed/processed_flood_records_v2_2024.csv`
- `processed/processed_flood_records_v2_2025.csv`

**Description:** Cleaned and normalized flood records with weather data joined.

Contains similar columns to cumulative dataset but for individual years.

---

## Data Quality Notes

### Known Issues

1. **Humidity in fetched_meteostat.csv**: Historical values may show constant 70% (default) because Meteostat's Daily API doesn't include humidity. Fixed by using Hourly API aggregation.

2. **Raw flood records format**: CSV files have irregular multi-row headers (rows 1-4 are metadata). Use preprocessing scripts to normalize.

3. **Missing values**: Weather data may have NaN values for certain days. Use fillna or interpolation strategies.

4. **Coordinate precision**: Some GPS coordinates may have slight variations for the same location.

### Validation

Run `python scripts/validate_checksums.py` to verify data integrity against `data/checksums.json`.

### Data Pipeline

```
Raw PAGASA Data ─────────────┐
                             ├──► Preprocessing ──► Merged PAGASA Dataset
Raw Flood Records ───────────┤                            │
                             │                            ▼
Meteostat API ───────────────┴──────────────────► Cumulative Training Dataset
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| v2 | 2026-01 | Added cumulative datasets, feature engineering, multi-station support |
| v1 | 2025-12 | Initial schema with basic weather and flood data |
