# Progressive Training System (v1-v6) - Quick Start Guide

## Overview

The progressive training system generates six model versions with incremental feature additions and data improvements, perfect for demonstrating model evolution in your thesis.

## Version Progression

| Version | Name | Data Source | Features | Description |
|---------|------|-------------|----------|-------------|
| **v1** | Baseline_2022 | 2022 only | 5 core features | Temperature, humidity, precipitation, month, monsoon season |
| **v2** | Extended_2023 | 2022-2023 | 8 features | v1 + basic interactions (temp_humidity, humidity_precip, saturation_risk) |
| **v3** | Extended_2024 | 2022-2024 | 10 features | v2 + all interactions (temp_precip, monsoon_precip) |
| **v4** | Full_Official_2025 | 2022-2025 | 13 features | v3 + rolling features (precip_3day_sum, precip_7day_sum, rain_streak) |
| **v5** | PAGASA_Merged | Official + PAGASA | 13 features | v4 + PAGASA weather data + precip_14day_sum |
| **v6** | Ultimate_Combined | All sources + APIs | 14 features | v5 + external APIs (tide_height from WorldTides, GEE, Meteostat) |

## Quick Start

### 1. Train All Versions (v1-v6)

```powershell
cd backend
.\models\run_training_pipeline.ps1 -Progressive6
```

**Expected Duration**: 30-60 minutes (depending on data size)

### 2. Quick Mode (For Testing)

```powershell
.\models\run_training_pipeline.ps1 -Progressive6 -Quick
```

**Expected Duration**: 10-20 minutes (reduced estimators)

### 3. Train Specific Version Only

```powershell
# Train only v5
.\models\run_training_pipeline.ps1 -Progressive6 -Version 5

# Train only v6
.\models\run_training_pipeline.ps1 -Progressive6 -Version 6
```

### 4. With Custom Cross-Validation

```powershell
.\models\run_training_pipeline.ps1 -Progressive6 -CVFolds 10
```

## Expected Output

### Model Files (in `backend/models/`)

```
flood_model_v1.joblib          # Trained model v1
flood_model_v1.json            # Metadata for v1
feature_names_v1.json          # Feature list for v1

flood_model_v2.joblib
flood_model_v2.json
feature_names_v2.json

... (v3, v4, v5, v6)
```

### Reports (in `backend/reports/`)

```
progressive_v6_report_YYYYMMDD_HHMMSS.json    # Comprehensive metrics
progressive_v6_report_latest.json             # Latest report (no timestamp)
metrics_evolution_v6.png                      # Performance progression chart
feature_count_vs_performance.png              # Features vs F1 score
```

## Comparing Models

After training, compare all versions:

```powershell
cd backend
python scripts\compare_progressive_models.py
```

**Output**:
- `progressive_comparison.csv` - Metrics table
- `progressive_comparison.md` - Human-readable report
- `progressive_comparison.json` - Machine-readable report
- `metrics_comparison.png` - Side-by-side metrics
- `features_vs_performance.png` - Feature count analysis
- `dataset_size_vs_performance.png` - Data size impact

## Understanding the Results

### 1. Check Training Summary

After training completes, you'll see:

```
PROGRESSIVE TRAINING COMPLETE
======================================================================

Version Summary:
  v1: Baseline_2022
    Features: 5, Records: 1,234
    F1: 0.8234, F2: 0.8156, Accuracy: 0.8345

  v2: Extended_2023
    Features: 8, Records: 2,456
    F1: 0.8567, F2: 0.8489, Accuracy: 0.8678

  ... (v3-v6)

Overall Improvement (v1 → v6):
  Accuracy: +0.0523
  F1 Score: +0.0678
  F2 Score: +0.0712
  ROC-AUC:  +0.0589

Feature Growth: 5 → 14 (+9)
Data Growth: 1,234 → 8,901 records (+7,667)
```

### 2. Review Progression Report

Open `backend/reports/progressive_v6_report_latest.json`:

```json
{
  "generated_at": "2026-02-03T23:45:00",
  "versions": [
    {
      "version": 1,
      "name": "Baseline_2022",
      "metrics": {
        "accuracy": 0.8345,
        "f1_score": 0.8234,
        "f2_score": 0.8156,
        "roc_auc": 0.8567
      },
      ...
    }
  ],
  "progression_summary": {
    "improvements": {
      "accuracy": 0.0523,
      "f1_score": 0.0678,
      ...
    }
  }
}
```

### 3. View Visualizations

Open the generated charts:
- `metrics_evolution_v6.png` - Shows clear upward trend
- `feature_count_vs_performance.png` - Demonstrates feature impact

## Troubleshooting

### Issue: "Data file not found"

**Solution**: Some versions require specific data files. The script will try fallback files automatically.

For v6 (external APIs), you may need to run data ingestion first:

```powershell
.\models\run_training_pipeline.ps1 -Ingest -IngestMeteostat -IngestDays 30
```

### Issue: "Version parameter can only be used with -Progressive6"

**Solution**: Make sure to include `-Progressive6` flag when using `-Version`:

```powershell
# ✗ Wrong
.\models\run_training_pipeline.ps1 -Version 5

# ✓ Correct
.\models\run_training_pipeline.ps1 -Progressive6 -Version 5
```

### Issue: Training takes too long

**Solution**: Use Quick mode for testing:

```powershell
.\models\run_training_pipeline.ps1 -Progressive6 -Quick
```

This reduces n_estimators from 200 to 100.

## For Your Thesis

### Demonstrating Model Evolution

1. **Train all versions**: `.\models\run_training_pipeline.ps1 -Progressive6`
2. **Generate comparison**: `python scripts\compare_progressive_models.py`
3. **Use visualizations**: Include `metrics_evolution_v6.png` in your thesis
4. **Show progression table**: Use data from `progressive_comparison.md`

### Key Points to Highlight

- **Incremental Improvement**: Each version shows measurable gains
- **Feature Engineering Impact**: v2-v4 show how engineered features improve performance
- **Data Quality Matters**: v5-v6 demonstrate value of additional data sources
- **Balanced Approach**: F2 score prioritizes recall (catching floods is critical)

## Next Steps

1. ✅ Train all versions: `.\models\run_training_pipeline.ps1 -Progressive6`
2. ✅ Review results in `backend/reports/progressive_v6_report_latest.json`
3. ✅ Compare models: `python scripts\compare_progressive_models.py`
4. ✅ Include visualizations in thesis presentation

## Questions?

- Check model metadata: `backend/models/flood_model_v*.json`
- Review training logs in console output
- Examine feature lists: `backend/models/feature_names_v*.json`
