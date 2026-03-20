# Data Provenance & Source Documentation

> Complete traceability of every data source used in the Floodingnaque flood prediction system for Parañaque City. All model training uses **real observed data** — no synthetic generation.

---

## Primary Data Sources

### 1. DRRMO Flood Records (2022–2025)

| Attribute          | Value                                                                         |
| ------------------ | ----------------------------------------------------------------------------- |
| **Agency**         | Parañaque City Disaster Risk Reduction and Management Office (DRRMO)          |
| **Access**         | Official request to Parañaque City LGU                                        |
| **Format**         | CSV (manually digitised from incident reports)                                |
| **Date Range**     | January 2022 – March 2025                                                     |
| **Records**        | 605 records (310 non-flood / 295 flood events)                                |
| **Fields**         | Date, barangay, location, flood depth (cm), weather disturbance, remarks      |
| **Quality**        | Manual transcription — some barangay fields unresolved (135/295 flood events) |
| **Processed File** | `backend/data/processed/cumulative_v2_up_to_2025.csv`                         |

### 2. PAGASA Weather Station Data

| Attribute          | Value                                                                                 |
| ------------------ | ------------------------------------------------------------------------------------- |
| **Agency**         | Philippine Atmospheric, Geophysical and Astronomical Services Administration (PAGASA) |
| **Stations**       | Science Garden, Port Area, NAIA (3 stations near Parañaque)                           |
| **Access**         | PAGASA Climate Data Division                                                          |
| **Format**         | CSV (daily observations)                                                              |
| **Date Range**     | 2022–2025                                                                             |
| **Records**        | 4,944 records (3,579 non-flood / 1,365 flood via IDW-matched DRRMO events)            |
| **Fields**         | Temperature, humidity, precipitation, wind speed, cloud cover                         |
| **Quality**        | Excellent — calibrated ground-station instruments                                     |
| **Processed File** | `backend/data/processed/pagasa_training_dataset.csv`                                  |

### 3. External API Data (v6 augmentation)

| Source                           | Records | Fields                          | Quality Notes                                                                                                          |
| -------------------------------- | ------- | ------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| **Google Earth Engine (CHIRPS)** | ~500    | Satellite-derived precipitation | Satellite estimates — not direct measurement. Good spatial coverage but lower temporal precision than ground stations. |
| **Meteostat**                    | ~500    | Temperature, humidity, wind     | Some stations report constant humidity (data quality flag). Estimated values marked accordingly.                       |
| **WorldTides**                   | ~21     | Tide height, tide phase         | Astronomical tide predictions — high accuracy for Manila Bay.                                                          |

**Combined v6 dataset**: 6,570 records across all sources.

---

## Non-Flood Data Methodology

Non-flood records are **not synthetic**. They are real weather observations from days when no flooding was reported:

1. **DRRMO-based**: Days in the DRRMO dataset explicitly recorded as non-flood (clear weather, no incidents)
2. **PAGASA-based**: Stratified sampling from PAGASA weather archives on confirmed dry days (no DRRMO flood incident within ±1 day and precipitation < 5mm)
3. **Balance ratio**: Approximately 70:30 non-flood:flood (natural class distribution preserved where possible)

---

## Spatial Data Sources

| Data                    | Source                                 | Resolution          | Notes                                                           |
| ----------------------- | -------------------------------------- | ------------------- | --------------------------------------------------------------- |
| **Elevation**           | SRTM 30m DEM (NASA, 2000)              | ~30m, ±16m vertical | Barangay centroid approximations                                |
| **Waterways**           | NAMRIA topographic maps + OSM          | —                   | Parañaque River, Wawa River, La Huerta Creek                    |
| **Land Use**            | Parañaque City CLUP                    | Barangay-level      | Commercial/residential/mixed classification                     |
| **Runoff Coefficients** | ASCE Manual of Practice No. 77         | —                   | Standard urban values                                           |
| **Flood History**       | DRRMO 2022–2025 records                | Per-barangay        | 295 identifiable events (135 with unresolved barangay excluded) |
| **Barangay Boundaries** | PSA / NAMRIA administrative boundaries | —                   | 16 barangays                                                    |
| **Rainfall Warnings**   | PAGASA Rainfall Warning System         | —                   | Yellow 7.5–15mm/hr, Orange 15–30mm/hr, Red >30mm/hr             |

---

## Model Version Data Lineage

| Version | Training Data    | Records | Features | Accuracy | F1    | ROC-AUC | CV Mean ± Std |
| ------- | ---------------- | ------- | -------- | -------- | ----- | ------- | ------------- |
| v1      | DRRMO 2022 only  | 209     | 5        | 1.000    | 1.000 | 1.000   | 0.990 ± 0.019 |
| v2      | DRRMO 2022–2023  | 217     | 8        | 1.000    | 1.000 | 1.000   | 0.972 ± 0.017 |
| v3      | DRRMO 2022–2024  | 593     | 10       | 0.617    | 0.548 | 0.837   | 0.917 ± 0.098 |
| v4      | DRRMO 2022–2025  | 605     | 13       | 1.000    | 1.000 | 1.000   | 0.995 ± 0.007 |
| v5      | + PAGASA weather | 5,549   | 12       | 0.969    | 0.970 | 0.990   | 0.948 ± 0.074 |
| v6      | + External APIs  | 6,570   | 13       | 0.974    | 0.974 | 0.992   | 0.906 ± 0.099 |

**Key observations:**

- v1–v2, v4: Perfect accuracy reflects overfitting on small, homogeneous DRRMO-only datasets (<605 records). Not indicative of generalisation.
- v3: Accuracy drop to 61.7% coincides with 2024 data introducing distribution shift.
- v5: First realistic evaluation — PAGASA weather data adds variability from 3 ground stations. 96.9% accuracy with CV mean 0.948 ± 0.074.
- v6: Best model — marginal improvement to 97.4% accuracy. Higher CV std (0.099) likely due to external API data heterogeneity.

---

## Risk Classification Thresholds

Thresholds calibrated from 5,549 real records (DRRMO + PAGASA). See `reports/threshold_calibration_report.json`.

| Parameter                  | Value   | Source                                          |
| -------------------------- | ------- | ----------------------------------------------- |
| flood_probability.critical | 0.75    | v6 model: flood event p10 = 0.84                |
| flood_probability.alert    | 0.40    | v6 model: probability gap between distributions |
| flood_probability.safe_max | 0.10    | v6 model: non-flood event p90 = 0.05            |
| precipitation.alert_min    | 7.5 mm  | PAGASA Yellow Warning lower bound               |
| precipitation.alert_max    | 30.0 mm | PAGASA Red Warning threshold                    |
| humidity_threshold         | 82.0%   | Flood-day humidity median = 81.9%               |
| rainfall_3h.critical       | 65.0 mm | PAGASA-aligned 3h accumulation                  |
| rainfall_3h.alert          | 30.0 mm | PAGASA Orange Warning alignment                 |

---

## Limitations

1. **Barangay attribution**: 135 of 295 DRRMO flood events have unresolved barangay names due to data entry inconsistencies.
2. **Temporal coverage**: Only 3+ years of data (2022–2025). Longer records would improve climate variability coverage.
3. **Spatial resolution**: SRTM elevation (30m) is coarse for urban flood modelling. LiDAR data would improve accuracy significantly.
4. **Rolling features**: At inference time, rolling weather features (7-day precipitation, 3-day humidity) may default to 0 if historical weather data is unavailable via API.
5. **Meteostat quality**: Some Meteostat records report constant humidity values, indicating estimated rather than measured data.
6. **CHIRPS**: Satellite-derived precipitation estimates have lower accuracy than ground stations, particularly for localised convective rainfall events.
