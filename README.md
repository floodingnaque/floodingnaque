# Floodingnaque - Flood Prediction System for Parañaque City

Random Forest-Based Flood Detection and Alert System

[![Python](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/github/license/floodingnaque/floodingnaque)](LICENSE)
[![Last Updated](https://img.shields.io/github/last-commit/floodingnaque/floodingnaque)](#)

## Table of Contents

- [Overview](#overview)
- [Official Flood Records Training](#official-flood-records-training-2022-2025)
- [Latest Enhancements](#latest-enhancements)
- [Frequently Asked Questions](#frequently-asked-questions)
- [Recommended Workflows](#recommended-workflows)
- [System Architecture](#system-architecture)
- [Random Forest Model](#random-forest-model-features)
- [Command Reference](#command-reference)
- [Documentation](#documentation)
- [Thesis Defense Materials](#thesis-defense-materials)
- [Installation](#installation)
- [Expected Performance](#expected-performance)
- [Key Features](#key-features)
- [License](#license)

## Overview

This project implements a **Random Forest machine learning model** to predict flood risks in Parañaque City with a **3-level risk classification system** (Safe/Alert/Critical). The system is designed for academic research and production deployment.

## Official Flood Records Training (2022-2025)

Train models with **1,182 official flood events** from the Parañaque City Disaster Risk Reduction and Management Office (DRRMO), expanded to **13,698 balanced training samples**.

| Feature         | Description                                               |
| --------------- | --------------------------------------------------------- |
| Data Source     | Official government records from DRRMO                    |
| Coverage        | 4 years of historical records (2022-2025)                 |
| Training Method | Progressive training showing model evolution              |
| Preprocessing   | Comprehensive handling of diverse CSV formats             |
| Output          | Publication-ready visualizations for thesis presentations |

This enhancement provides significantly stronger thesis support compared to projects using synthetic data.

### Quick Start References

| Guide                                                                                  | Description                        |
| -------------------------------------------------------------------------------------- | ---------------------------------- |
| [QUICKSTART.md](QUICKSTART.md)                                                         | Quick start guide                  |
| [backend/docs/CENTRALIZED_DOCUMENTATION.md](backend/docs/CENTRALIZED_DOCUMENTATION.md) | Complete centralized documentation |

---

## Latest Enhancements

### New Features for Thesis Defense

| Feature                         | Description                                                                           |
| ------------------------------- | ------------------------------------------------------------------------------------- |
| Official Flood Records Training | 1,182 official flood events from Parañaque City (2022-2025) with progressive training |
| Enhanced Training Script        | Hyperparameter tuning with GridSearchCV                                               |
| Thesis Report Generator         | Publication-ready visualizations (300 DPI)                                            |
| Dataset Merger Tool             | Combine multiple CSV files easily                                                     |
| Model Comparison                | Compare performance across versions                                                   |
| Automatic Versioning            | Track all model improvements                                                          |
| Comprehensive Documentation     | Complete guides and references                                                        |

### Model Evolution Visualization

Track model improvement over time with:

| Visualization                 | Purpose                                      |
| ----------------------------- | -------------------------------------------- |
| Metrics Evolution Charts      | View accuracy, precision, recall improvement |
| Parameters Evolution          | Track hyperparameter changes                 |
| Feature Importance Comparison | Understand prediction drivers                |

## Frequently Asked Questions

### Can I add new CSV files for training?

Yes. Use the following commands:

```powershell
cd backend
python scripts/train.py --data data/your_new_file.csv
```

To merge multiple files:

```powershell
python scripts/merge_datasets.py --input "data/*.csv"
python scripts/train.py --data data/merged_dataset.csv
```

### How does model versioning work?

**With Official Records (Progressive Training):**

| Version  | Training Data        | Record Count                         |
| -------- | -------------------- | ------------------------------------ |
| Model v1 | 2022 data only       | ~100 records                         |
| Model v2 | 2022 + 2023 data     | ~270 records                         |
| Model v3 | 2022 + 2023 + 2024   | ~1,100 records                       |
| Model v4 | All data (2022-2025) | 1,182 events → 13,698 samples (Best) |

**With Custom Data:**

Each training session creates:

- Model file (.joblib)
- Metadata (.json) with training date, dataset, parameters, metrics, and feature importance

## Recommended Workflows

### Option A: Train with Official Flood Records (Recommended)

Use real flood data from Parañaque City (2022-2025):

```powershell
cd backend

# Step 1: Preprocess official records
python scripts/preprocess_official_flood_records.py

# Step 2: Progressive training (shows model evolution)
python scripts/progressive_train.py --grid-search --cv-folds 10

# Step 3: Generate thesis materials
python scripts/generate_thesis_report.py
python scripts/compare_models.py

# Step 4: Validate
python scripts/validate_model.py
```

**Output:**

- 4 models trained on real data (v1, v2, v3, v4)
- 1,182 official flood events from DRRMO records (2022-2025)
- 13,698 balanced training samples (flood + non-flood)
- Model evolution showing improvement over time
- Publication-ready charts and reports

### Option B: Custom Training Pipeline

Use your own CSV files:

```powershell
cd backend

# Step 1: Merge all datasets
python scripts/merge_datasets.py --input "data/*.csv"

# Step 2: Train optimal model (with hyperparameter tuning)
python scripts/train.py --data data/merged_dataset.csv --grid-search --cv-folds 10

# Step 3: Generate thesis presentation materials
python scripts/generate_thesis_report.py

# Step 4: Compare model versions
python scripts/compare_models.py

# Step 5: Validate
python scripts/validate_model.py
```

**Generated Reports (Publication Quality):**

| Report                    | Description                       |
| ------------------------- | --------------------------------- |
| Feature importance chart  | Shows prediction drivers          |
| Confusion matrix          | Prediction accuracy visualization |
| ROC curve                 | Model performance curve           |
| Precision-Recall curve    | Classification threshold analysis |
| Metrics comparison        | Cross-version comparison          |
| Learning curves           | Overfitting analysis              |
| Version comparison charts | Side-by-side model performance    |

## System Architecture

```
Official Flood Records (2022-2025)
            |
            v
      Preprocessing
            |
            +---> Progressive Training ---> Random Forest Models (v1, v2, v3, v4)
            |
Custom CSV Files ---> Data Merger ---> Training Script
                                              |
                                              v
                                       Model Versions
                                              |
                                              v
                                         Flask API
                                              |
                                              v
                                 3-Level Risk Classification
                                   (Safe / Alert / Critical)
                                              |
                                              v
                                       Alert Delivery
                                       (SMS / Email)
                                              |
                                              v
                                   React Frontend (Vite)
                              Landing Page (/) | Dashboard (/dashboard)
```

## Random Forest Model Features

### Why Random Forest?

| Advantage          | Description                             |
| ------------------ | --------------------------------------- |
| Ensemble Learning  | Multiple decision trees voting together |
| Robust             | Less prone to overfitting               |
| Feature Importance | Shows which weather factors matter most |
| No Scaling Needed  | Works with raw weather data             |
| Interpretable      | Easy to explain to stakeholders         |
| Industry Standard  | Widely used in production systems       |

### Model Capabilities

| Capability                  | Description                              |
| --------------------------- | ---------------------------------------- |
| Hyperparameter Tuning       | Automatic optimization with GridSearchCV |
| Cross-Validation            | Robust k-fold validation                 |
| Multi-Dataset Training      | Merge multiple CSV files                 |
| Automatic Versioning        | Track improvements over time             |
| Comprehensive Metrics       | Accuracy, Precision, Recall, F1, ROC-AUC |
| Feature Importance Analysis | Understand model decisions               |

## Command Reference

### Training Commands

```powershell
# Basic training
python scripts/train.py

# With new dataset
python scripts/train.py --data data/my_data.csv

# With hyperparameter tuning (Recommended)
python scripts/train.py --grid-search --cv-folds 10

# Merge multiple datasets during training
python scripts/train.py --data "data/*.csv" --merge-datasets

# Progressive training with official records (Recommended for thesis)
python scripts/progressive_train.py --grid-search --cv-folds 10

# Year-specific training
python scripts/progressive_train.py --year-specific
```

### Analysis Commands

```powershell
# Generate thesis report
python scripts/generate_thesis_report.py

# Compare model versions
python scripts/compare_models.py

# Merge datasets
python scripts/merge_datasets.py

# Preprocess official flood records
python scripts/preprocess_official_flood_records.py
```

### API Commands

```powershell
# Start server
python main.py

# Test prediction
curl -X POST http://localhost:5000/predict -H "Content-Type: application/json" -d "{\"temperature\": 25.0, \"humidity\": 80.0, \"precipitation\": 15.0}"

# List models
curl http://localhost:5000/api/models
```

## Documentation

### Quick References

| Document                                                                               | Description                                               |
| -------------------------------------------------------------------------------------- | --------------------------------------------------------- |
| [backend/docs/CENTRALIZED_DOCUMENTATION.md](backend/docs/CENTRALIZED_DOCUMENTATION.md) | Complete documentation (thesis guide, commands, training) |

### Detailed Guides

| Document                                                                               | Description                                                           |
| -------------------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| [backend/docs/CENTRALIZED_DOCUMENTATION.md](backend/docs/CENTRALIZED_DOCUMENTATION.md) | Full documentation (records guide, system overview, model management) |

### Infrastructure & DevOps

| Document                                                 | Description                      |
| -------------------------------------------------------- | -------------------------------- |
| [docs/DOCKER_GUIDE.md](docs/DOCKER_GUIDE.md)             | Complete Docker deployment guide |
| [docs/TLS_SETUP.md](docs/TLS_SETUP.md)                   | TLS/SSL configuration with Nginx |
| [docs/GIT_WORKFLOW_GUIDE.md](docs/GIT_WORKFLOW_GUIDE.md) | Git branching strategy           |

## Thesis Defense Materials

### Key Talking Points

**About Random Forest:**

- Ensemble of 200 decision trees
- Each tree votes on prediction
- Majority decision wins
- Feature importance shows which factors matter most

**About the System:**

- Automatic model versioning
- Easy dataset integration
- Hyperparameter optimization
- 3-level risk classification (Safe/Alert/Critical)
- Real-time predictions via API
- Progressive training with 1,182 official flood events
- Model evolution demonstrating improvement over time

### Generated Presentation Materials

All materials are automatically generated in the `reports/` directory:

| Material                | Description                  |
| ----------------------- | ---------------------------- |
| Feature importance      | Which weather factors matter |
| Confusion matrix        | Prediction accuracy          |
| ROC curve               | Model performance            |
| Learning curves         | Overfitting analysis         |
| Metrics evolution       | Improvement over time        |
| Parameters evolution    | Hyperparameter changes       |
| Model comparison charts | Side-by-side performance     |

## Installation

### Requirements

- Python 3.8 or higher
- pip package manager

### Setup

```powershell
# Clone repository
git clone https://github.com/floodingnaque/floodingnaque.git
cd floodingnaque/backend

# Install dependencies
pip install -r requirements.txt

# Train model
python scripts/train.py

# Start API
python main.py
```

## Expected Performance

### Performance Metrics (with Grid Search Optimization)

| Metric    | Expected Minimum | Notes                                    |
| --------- | ---------------- | ---------------------------------------- |
| Accuracy  | 95%+             | Held-out test set (20% stratified split) |
| Precision | 95%+             | Weighted average across classes          |
| Recall    | 95%+             | Weighted average across classes          |
| F1 Score  | 95%+             | Weighted average across classes          |
| ROC-AUC   | 0.98+            | Area under ROC curve                     |

> **Important - Accuracy Disclaimer:** The thesis reports 100% accuracy on
> the official DRRMO historical records dataset (N ≈ 200). This result is
> expected when a Random Forest classifier operates on a small, clean,
> well-separated dataset and does **not** imply equivalent performance on
> unseen or noisy real-world data. Always refer to the stratified
> cross-validation scores in the training output for a more robust
> generalisation estimate.

### Feature Importance (Example)

| Feature       | Importance |
| ------------- | ---------- |
| Precipitation | 45%        |
| Humidity      | 30%        |
| Temperature   | 20%        |
| Wind Speed    | 5%         |

## Key Features

### Data Management

| Feature                        | Description                         |
| ------------------------------ | ----------------------------------- |
| CSV Integration                | Easy import of custom datasets      |
| Multi-dataset Merging          | Combine multiple CSV files          |
| Duplicate Removal              | Automatic deduplication             |
| Column Validation              | Schema validation                   |
| Official Records Preprocessing | Support for 2022-2025 flood records |

### Model Training

| Feature                  | Description                   |
| ------------------------ | ----------------------------- |
| Random Forest Classifier | Ensemble learning algorithm   |
| Hyperparameter Tuning    | GridSearchCV optimization     |
| Cross-validation         | K-fold validation             |
| Automatic Versioning     | Version tracking              |
| Progressive Training     | Model evolution visualization |
| Year-specific Training   | Train on specific date ranges |

### Evaluation

| Feature                     | Description                    |
| --------------------------- | ------------------------------ |
| Comprehensive Metrics       | Full performance analysis      |
| Publication-quality Charts  | 300 DPI visualizations         |
| Feature Importance Analysis | Prediction driver analysis     |
| Model Comparison Tools      | Cross-version comparison       |
| Metrics Evolution           | Performance tracking over time |

### Deployment

| Feature                     | Description                                                |
| --------------------------- | ---------------------------------------------------------- |
| Flask REST API              | RESTful web service                                        |
| React Frontend              | Vite + TypeScript + Tailwind CSS + shadcn/ui               |
| Public Landing Page         | 9-section pitch page with live status for all 16 barangays |
| 3-level Risk Classification | Safe/Alert/Critical levels                                 |
| Real-time Predictions       | Low-latency inference                                      |
| Alert Delivery System       | SMS and email notifications                                |

## Support

For detailed instructions, see the documentation in `backend/docs/`.

## License

See the [LICENSE](LICENSE) file for details.
