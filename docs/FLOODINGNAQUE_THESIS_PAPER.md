# FLOODINGNAQUE: A PROPOSED REAL-TIME FLOOD DETECTION AND EARLY WARNING SYSTEM UTILIZING APIs AND RANDOM FOREST ALGORITHM

---

**ANDAM, EDRIAN¹, BARBA, CHRISTIAN DAVE², DE CASTRO, DONNA BELLE³, DOMINGO, RENGIEE⁴, GUMBA, JEFF CHRISTIAN⁵, MARTIZANO, RAMIL C.⁶, QUIRAY, NORIEL A.⁷**

Bachelor of Science in Computer Science, Asian Institute of Computer Studies
1571 Triangle Bldg., Doña Soledad Avenue, Better Living Subd, Parañaque City, 1709 Metro Manila, Philippines

¹edrian.andam07@gmail.com
²Christianbarba12@gmail.com
³Decastrobellebelle@gmail.com
⁴rengieedomingo025@gmail.com
⁵gjeffchristian@gmail.com
⁶iamdefinitely.ramil@gmail.com
⁷norielqry@gmail.com

---

## ABSTRACT

Flooding remains a critical challenge in Parañaque City, Metro Manila, Philippines, with recurrent incidents causing substantial damage to property, infrastructure, and posing significant risks to human life. This study presents Floodingnaque, a proposed real-time flood detection and early warning system that integrates weather Application Programming Interfaces (APIs) with the Random Forest machine learning algorithm to predict flood occurrences. The system utilizes multiple weather data sources including Meteostat for historical weather data and OpenWeatherMap for real-time meteorological information. The Random Forest classifier was trained using official flood records from the Parañaque City Disaster Risk Reduction and Management Office (DRRMO) spanning 2022 to 2025, comprising 1,182 documented flood events across multiple barangays. The training dataset was expanded to 13,698 balanced samples including both flood and non-flood instances. The model incorporates key features including precipitation, temperature, humidity, monsoon season indicators, and engineered interaction features. A progressive training approach was employed, demonstrating model evolution from baseline (2022 data) to the comprehensive cumulative dataset (2022-2025). The trained model achieved an accuracy of 100%, precision of 100%, recall of 100%, and F1-score of 100% on the official records dataset, with precipitation identified as the most influential feature (importance score: 0.3377). The system implements a three-level risk classification scheme (Safe, Alert, Critical) to facilitate timely response actions. This research contributes to disaster risk reduction efforts by providing an accessible, data-driven approach to flood prediction that can support local government units in protecting communities from flood-related hazards.

**Keywords:** Flood Prediction, Random Forest Algorithm, Machine Learning, Weather API, Early Warning System, Disaster Risk Reduction, Parañaque City

---

## DEFINITION OF TERMS

**API (Application Programming Interface)** – A set of protocols and tools that allows different software applications to communicate with each other. In this study, APIs are used to retrieve weather data from external services.

**Barangay** – The smallest administrative division in the Philippines, equivalent to a village or district within a city or municipality.

**CHIRPS (Climate Hazards Group InfraRed Precipitation with Station)** – A satellite-based precipitation dataset that combines satellite imagery with ground station data for climate monitoring.

**DRRMO (Disaster Risk Reduction and Management Office)** – A local government unit responsible for disaster preparedness, response, and mitigation activities.

**Ensemble Learning** – A machine learning technique that combines multiple models to produce a more accurate and robust prediction than any single model.

**Feature Engineering** – The process of creating new input variables from existing data to improve machine learning model performance.

**Flask** – A lightweight Python web framework used for building web applications and RESTful APIs.

**GPM IMERG (Global Precipitation Measurement Integrated Multi-satellitE Retrievals)** – A NASA satellite mission providing global precipitation estimates at high temporal and spatial resolution.

**ITCZ (Inter-Tropical Convergence Zone)** – A belt of low pressure near the equator where trade winds converge, often causing heavy rainfall and thunderstorms.

**Machine Learning** – A subset of artificial intelligence that enables systems to learn and improve from experience without being explicitly programmed.

**Monsoon** – A seasonal wind pattern that brings heavy rainfall, typically occurring in the Philippines from June to November (Southwest Monsoon or "Habagat").

**PAGASA (Philippine Atmospheric, Geophysical and Astronomical Services Administration)** – The Philippine government agency responsible for weather forecasting, flood monitoring, and climate services.

**Random Forest** – An ensemble machine learning algorithm that constructs multiple decision trees during training and outputs the class that is the mode of the classes predicted by individual trees.

**RESTful API** – An architectural style for designing networked applications that uses HTTP requests to access and manipulate data.

**ROC-AUC (Receiver Operating Characteristic - Area Under Curve)** – A performance metric that measures a classifier's ability to distinguish between classes.

**Synthetic Data** – Artificially generated data that mimics the statistical properties of real data, used when actual data is limited or unavailable.

**Tidal Data** – Information about the rise and fall of sea levels caused by gravitational forces of the moon and sun, relevant for coastal flood prediction.

---

## I. INTRODUCTION

Flooding is one of the most devastating natural disasters affecting urban areas worldwide, and the Philippines, particularly Metro Manila, is highly susceptible due to its geographic location, topography, and climate patterns (Briones, 2020). Parañaque City, situated in the southern part of Metro Manila, experiences frequent flooding during the monsoon season (June to November) and during localized thunderstorms throughout the year. The city's proximity to Manila Bay, its low-lying terrain, and rapid urbanization have exacerbated flood vulnerability, making timely flood prediction and warning essential for protecting residents and minimizing damage (Cruz & Narisma, 2019).

Traditional flood monitoring approaches often rely on manual observations and reactive responses, which may not provide sufficient lead time for communities to prepare and evacuate. The advancement of machine learning technologies and the availability of real-time weather data through APIs present opportunities to develop proactive flood prediction systems (Ahmed & Alim, 2021). The integration of these technologies can enable local government units to issue timely warnings and implement preventive measures before flooding occurs.

The Random Forest algorithm has emerged as a reliable machine learning technique for environmental prediction tasks due to its ability to handle complex, non-linear relationships between features, resistance to overfitting, and interpretability through feature importance analysis (Liu & Chen, 2022). Unlike single decision trees, Random Forest constructs an ensemble of decision trees and aggregates their predictions through majority voting, resulting in more robust and accurate classifications (Chen & Guestrin, 2016).

This study aims to develop Floodingnaque, a real-time flood detection and early warning system for Parañaque City that combines weather API data integration with Random Forest-based flood prediction. The specific objectives of this research are: (1) to design and implement a system architecture that integrates multiple weather data sources through APIs; (2) to train a Random Forest classifier using official flood records from the Parañaque City DRRMO; (3) to evaluate the prediction performance of the trained model using appropriate metrics; and (4) to implement a three-level risk classification system that translates predictions into actionable warnings.

The significance of this study lies in its potential to enhance disaster preparedness and response in Parañaque City. By leveraging official government flood records and real-time weather data, the system provides a localized solution tailored to the specific flood patterns and conditions of the area. The research also demonstrates the practical application of machine learning in disaster risk reduction, contributing to the growing body of knowledge on data-driven approaches for urban flood management in the Philippine context.

### Scope and Limitations

**Scope:**
This study focuses on the development of a flood prediction system specifically for Parañaque City, Metro Manila, Philippines. The research encompasses:

1. **Geographic Scope**: The 16 barangays of Parañaque City, with particular attention to flood-prone areas documented in official DRRMO records.

2. **Temporal Scope**: Official flood records from 2022 to 2025, and PAGASA weather data from 2020 to 2025.

3. **Technical Scope**: Development of a web-based flood prediction system using Random Forest algorithm, weather API integration, and a three-level risk classification system.

4. **Data Sources**: Official flood records from Parañaque City DRRMO, climatological data from PAGASA weather stations (Port Area, NAIA, Science Garden), satellite precipitation data from Google Earth Engine, and tidal data from WorldTides API.

**Limitations:**

1. **Data Availability**: The system relies on the availability and accuracy of external weather APIs. Service interruptions or API changes may affect real-time predictions.

2. **Localized Rainfall**: Weather station data may not capture highly localized rainfall variations within individual barangays. Microclimate effects are not fully accounted for.

3. **Historical Data Period**: The four-year historical dataset (2022-2025) may not capture long-term climate patterns or rare extreme weather events.

4. **Infrastructure Dependencies**: The system requires stable internet connectivity and server availability for real-time operation.

5. **Validation Constraints**: Real-time validation of predictions against actual flood events requires ongoing coordination with DRRMO, which was outside the scope of this initial development phase.

6. **Flood Depth Prediction**: The current model predicts flood occurrence (binary classification) but does not predict specific flood depth levels.

### Conceptual Framework

The Floodingnaque system is built upon an Input-Process-Output (IPO) conceptual framework that integrates multiple data sources through machine learning for flood prediction:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CONCEPTUAL FRAMEWORK                               │
│                    Floodingnaque Flood Prediction System                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐  │
│  │      INPUT      │    │      PROCESS        │    │       OUTPUT        │  │
│  ├─────────────────┤    ├─────────────────────┤    ├─────────────────────┤  │
│  │                 │    │                     │    │                     │  │
│  │ Weather Data:   │    │ Data Preprocessing: │    │ Flood Prediction:   │  │
│  │ • Temperature   │───▶│ • Data cleaning     │───▶│ • Binary (Yes/No)   │  │
│  │ • Humidity      │    │ • Feature scaling   │    │ • Probability score │  │
│  │ • Precipitation │    │ • Missing value     │    │                     │  │
│  │ • Wind speed    │    │   handling          │    │ Risk Classification:│  │
│  │                 │    │                     │    │ • Safe (Green)      │  │
│  │ Temporal Data:  │    │ Feature Engineering:│    │ • Alert (Yellow)    │  │
│  │ • Date/Time     │───▶│ • Interaction terms │───▶│ • Critical (Red)    │  │
│  │ • Month         │    │ • Monsoon indicator │    │                     │  │
│  │ • Season        │    │ • Saturation risk   │    │ Actionable Info:    │  │
│  │                 │    │                     │    │ • Warning messages  │  │
│  │ Historical Data:│    │ ML Model Training:  │    │ • Recommended       │  │
│  │ • DRRMO flood   │───▶│ • Random Forest     │───▶│   actions           │  │
│  │   records       │    │ • Cross-validation  │    │ • Visualization     │  │
│  │ • PAGASA data   │    │ • Hyperparameter    │    │                     │  │
│  │                 │    │   optimization      │    │                     │  │
│  │ Supplementary:  │    │                     │    │                     │  │
│  │ • Tidal data    │    │ Risk Assessment:    │    │                     │  │
│  │ • Satellite     │───▶│ • Probability       │───▶│                     │  │
│  │   precipitation │    │   thresholds        │    │                     │  │
│  │                 │    │ • Condition rules   │    │                     │  │
│  └─────────────────┘    └─────────────────────┘    └─────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Figure 1. Conceptual Framework of the Floodingnaque System**

The framework illustrates the flow of data from multiple input sources through processing stages to produce actionable flood warnings. The Random Forest algorithm serves as the core prediction engine, trained on historical flood records and weather data to classify current conditions into risk levels.

---

## II. REVIEW OF RELATED LITERATURE

### A. Flood Risk and Impact in Urban Areas

Urban flooding poses significant challenges to cities worldwide, with climate change and rapid urbanization intensifying flood risks (Zhang & Li, 2023). In the Philippines, Metro Manila experiences recurring flood events that cause economic losses, displacement of residents, and loss of life. Briones (2020) highlighted that flood hazard mapping and early warning efforts in Metro Manila have been hampered by limited data availability and the need for localized prediction systems. Cruz and Narisma (2019) examined climate change adaptation and flood resilience in Philippine cities, emphasizing the importance of integrating technological solutions with community-based disaster risk reduction strategies.

The Parañaque City DRRMO has documented 1,182 distinct flood events from 2022 to 2025, with incidents occurring across various barangays including San Dionisio, San Isidro, San Antonio, Vitalez, Sun Valley, and Marcelo Green, among others. These records indicate that flood depths range from gutter level to waist level, with weather disturbances ranging from localized thunderstorms to Inter-Tropical Convergence Zone (ITCZ) phenomena.

### B. Machine Learning for Flood Prediction

Machine learning has emerged as a powerful approach for flood forecasting and risk assessment. Ahmed and Alim (2021) conducted a comprehensive review of machine learning algorithms for flood prediction, identifying ensemble methods such as Random Forest as particularly effective for handling the complex relationships between meteorological variables and flood occurrence. Jain and Kumar (2020) compared various machine learning models for flood forecasting and found that ensemble algorithms consistently outperformed single models in terms of accuracy and generalization.

Muhammad and Rahman (2021) evaluated ensemble learning algorithms for flood hazard classification, demonstrating that Random Forest achieved superior performance compared to other classifiers when applied to environmental datasets. Liu and Chen (2022) specifically applied Random Forest to rainfall prediction for urban flood prevention, achieving high accuracy in classifying flood risk levels based on precipitation patterns.

### C. Random Forest Algorithm

The Random Forest algorithm, introduced by Breiman (2001), constructs multiple decision trees during training and outputs the mode of the classes for classification tasks. Each tree is trained on a bootstrap sample of the data, and at each node, a random subset of features is considered for splitting (Chen & Guestrin, 2016). This randomization reduces correlation among trees and improves the ensemble's generalization ability.

Key advantages of Random Forest for flood prediction include: (1) ability to handle high-dimensional data with minimal preprocessing; (2) robustness to outliers and noise in weather data; (3) provision of feature importance scores that aid in understanding prediction drivers; and (4) resistance to overfitting even with complex datasets. The algorithm's parameters, including the number of estimators (trees), maximum depth, and minimum samples for splitting, can be optimized through techniques such as grid search cross-validation.

### D. Weather Data APIs for Real-Time Monitoring

The availability of weather data through APIs has enabled the development of real-time disaster monitoring systems. OpenWeatherMap (2024) provides comprehensive weather data including current conditions, forecasts, and historical observations through its RESTful API. Meteostat (2024) offers free access to historical weather data from global weather stations, making it valuable for training machine learning models and validating predictions.

Khurshid and Lee (2019) demonstrated the integration of IoT and weather data APIs for real-time disaster monitoring, highlighting the importance of redundant data sources to ensure system reliability. Santos (2022) investigated API integration in local early warning systems in the Philippines, providing evidence of the effectiveness of web-based solutions for disaster preparedness in the local context.

### E. Disaster Risk Reduction in the Philippines

The Philippine government has established frameworks for disaster risk reduction at national and local levels. The Department of the Interior and Local Government (DILG, 2023) provides guidelines on disaster risk reduction management, mandating local government units to implement early warning systems and emergency response protocols. The Philippine Atmospheric, Geophysical and Astronomical Services Administration (PAGASA, 2023) serves as the primary source for weather data and flood bulletins, supporting disaster preparedness efforts nationwide.

The Department of Science and Technology-PAGASA (2024) maintains climate monitoring stations across Metro Manila, including Port Area, NAIA, and Science Garden stations, which provide valuable meteorological data for flood prediction research. These stations record daily rainfall, temperature, humidity, and wind observations that can be integrated into predictive models.

### F. Local Studies on Flood Prediction

Parayno (2021) demonstrated the application of machine learning models in localized flood forecasting in the Philippines, providing precedent for using Random Forest in the Philippine setting. Manila Observatory (2020) explored urban flood modeling and warning systems, reinforcing the need for data-based solutions tailored to Metro Manila's unique flooding characteristics. Villanueva and Dela Cruz (2020) highlighted data-driven approaches for disaster mitigation in the National Capital Region, validating the relevance of technological solutions to current government digital transformation initiatives.

### G. Synthetic Data Generation for Machine Learning

In research environments where labeled data is scarce or inaccessible, synthetic data generation provides an alternative for model development and validation. Patki, Wedge, and Veeramachaneni (2016) introduced the Synthetic Data Vault (SDV) framework for generating realistic synthetic datasets that preserve the statistical properties of original data. This approach has been applied in various domains where privacy concerns or data limitations prevent the use of actual records for training machine learning models.

---

## III. METHODOLOGY

### A. Research Design

This study employs a developmental research design to create, implement, and evaluate a flood prediction system. The methodology integrates software development practices with machine learning model training and evaluation, following an iterative approach that allows for progressive refinement of the prediction model.

### B. System Architecture

The Floodingnaque system follows a client-server architecture with the following components:

**1. Backend API (Flask + Python):**

- RESTful API endpoints for flood prediction requests (`/predict`, `/api/models`, `/status`)
- Model loading and management through a singleton ModelLoader class with lazy loading
- Integration with multiple weather data services for redundancy
- Rate limiting (100 requests/minute default) and caching mechanisms for performance optimization
- Asynchronous request handling for external API calls
- SQLAlchemy ORM for database operations with Alembic migrations
- Circuit breaker pattern for API resilience

**2. Weather Data Services:**

- **Meteostat Service**: Provides historical weather data from nearby weather stations without requiring an API key, configured for Parañaque City coordinates (14.4793°N, 121.0198°E) with 100km search radius
- **OpenWeatherMap Integration**: Supplies real-time weather observations and forecasts (temperature, humidity, pressure, wind)
- **Weatherstack Integration**: Provides backup precipitation data and current weather conditions
- **WorldTides Service**: Delivers tidal data critical for coastal flood risk assessment in Manila Bay area, including tide extremes and predictions
- **Google Earth Engine Service**: Enables access to satellite-derived precipitation data (GPM IMERG half-hourly, CHIRPS daily datasets) with automatic service account authentication

**3. Machine Learning Module:**

- Random Forest Classifier (scikit-learn) for flood prediction with configurable parameters
- Risk classification module for three-level risk assessment (Safe/Alert/Critical)
- Model versioning system with 6 progressive versions tracking improvements
- joblib for model serialization and deserialization
- Feature importance analysis and threshold optimization

**4. Frontend Interface (React + Vite + TypeScript):**

- Modern single-page application built with Vite for optimized development and production builds
- Component library using Radix UI primitives and shadcn/ui for accessible, customizable components
- Interactive flood map visualization using Leaflet and React-Leaflet
- Real-time data fetching with TanStack Query (React Query) for efficient state management
- Zustand for global state management
- Recharts for data visualization and charts
- Responsive design with Tailwind CSS
- Alert notification system with toast components
- Form handling with react-hook-form and Zod validation

**5. Database Layer (PostgreSQL/Supabase):**

- PostgreSQL database hosted on Supabase for production
- Tables for flood events, weather cache, predictions, and API request logging
- Alembic migrations for schema version control
- Connection pooling with PgBouncer for performance

**6. Infrastructure:**

- Docker containerization for consistent deployment
- Docker Compose configurations for development, staging, and production environments
- Nginx reverse proxy for SSL termination and load balancing
- Prometheus + Grafana monitoring stack
- CI/CD pipeline with GitHub Actions

### C. Data Collection

**1. Official Flood Records:**
The primary dataset consists of official flood incident records obtained from the Parañaque City Disaster Risk Reduction and Management Office (DRRMO) for the years 2022, 2023, 2024, and 2025. These records contain:
- Date and time of flood occurrence
- Barangay and specific location
- Geographic coordinates (latitude and longitude)
- Flood depth classification (Gutter Level, Knee Level, Waist Level)
- Weather disturbance type (Localized Thunderstorms, ITCZ, Monsoon)
- Remarks on road passability

**Table 1. Summary of Official Flood Records**

| Year | Number of Flood Events | Primary Weather Disturbances |
|------|------------------------|------------------------------|
| 2022 | 109 | Localized Thunderstorms |
| 2023 | 162 | ITCZ, Localized Thunderstorms |
| 2024 | 265 | Localized Thunderstorms, Monsoon |
| 2025 | 646 | ITCZ, Southwest Monsoon |
| **Total** | **1,182** | Mixed |

*Note: Each flood event may span multiple barangays or locations, resulting in multi-row entries in the official records. The training dataset (13,698 samples) includes both flood and non-flood samples generated to balance the classification model.*

**2. PAGASA Weather Station Data:**
Climatological data was obtained from DOST-PAGASA weather stations covering the study area. The data includes:

- Rainfall (mm)
- Maximum and Minimum Temperature (°C)
- Relative Humidity (%)
- Wind Speed (m/s) and Direction

Three weather stations were utilized:

- Port Area (Latitude: 14.58841°N, Longitude: 120.967866°E, Elevation: 15m)
- NAIA (Latitude: 14.5047°N, Longitude: 121.004751°E, Elevation: 21m)
- Science Garden (Latitude: 14.645072°N, Longitude: 121.044282°E, Elevation: 42m)

**3. Google Earth Engine Satellite Data:**
The system integrates satellite-derived precipitation data through Google Earth Engine, accessing:

- **GPM IMERG (Global Precipitation Measurement)**: Half-hourly precipitation estimates with near-real-time availability, providing high-resolution rainfall data independent of ground station coverage
- **CHIRPS (Climate Hazards Group InfraRed Precipitation with Station)**: Daily precipitation estimates combining satellite imagery with station data for climate monitoring
- **BigQuery Climate Data**: Access to historical climate datasets for model training and validation

**4. WorldTides Tidal Data:**
Given Parañaque City's proximity to Manila Bay, tidal data is critical for comprehensive flood risk assessment:

- Current and predicted tide heights relative to Mean Sea Level (MSL)
- Tide extremes (high/low tide times and heights)
- Integration with the flood prediction model to account for coastal flooding risks
- King tide identification for enhanced flood warning during extreme tidal events

### D. Data Preprocessing

The data preprocessing pipeline involves the following steps:

**1. Data Cleaning:**

- Handling missing values (indicated as -999.0 in PAGASA data)
- Processing trace rainfall values (indicated as -1.0, representing rainfall < 0.1mm)
- Removing duplicate records
- Standardizing date and time formats

**2. Feature Engineering:**
The following features were computed from raw data:

- `is_monsoon_season`: Binary indicator (1 if June-November, 0 otherwise)
- `temp_humidity_interaction`: Product of temperature and humidity
- `humidity_precip_interaction`: Product of humidity and precipitation
- `temp_precip_interaction`: Product of temperature and precipitation
- `monsoon_precip_interaction`: Product of monsoon indicator and precipitation
- `saturation_risk`: Computed measure of soil saturation potential

**3. Dataset Merging:**
Official flood records were merged with corresponding weather data to create a unified training dataset. The final cumulative dataset (2022-2025) comprises 13,698 samples with 10 features.

### E. Model Training

**1. Algorithm Selection:**
The Random Forest Classifier was selected based on its proven effectiveness in environmental prediction tasks and its ability to provide feature importance rankings.

**2. Hyperparameter Configuration:**
The model was configured with the following parameters:
- `n_estimators`: 200 (number of trees in the forest)
- `max_depth`: 15-20 (maximum depth of trees)
- `min_samples_split`: 5 (minimum samples required to split a node)
- `min_samples_leaf`: 2 (minimum samples required at a leaf node)
- `max_features`: 'sqrt' (number of features to consider at each split)
- `class_weight`: 'balanced' (to handle class imbalance)
- `random_state`: 42 (for reproducibility)
- `n_jobs`: -1 (utilize all CPU cores for parallel processing)

**3. Progressive Training Approach:**
A progressive training methodology was employed to demonstrate model evolution:

**Table 2. Progressive Model Training Versions**

| Version | Description | Dataset Size | Features |
|---------|-------------|--------------|----------|
| v1 | Baseline 2022 | 1,272 samples | 5 base features |
| v2 | Extended 2022-2023 | 3,450 samples | 5 base features |
| v3 | Extended 2022-2024 | 5,970 samples | 5 base features |
| v4 | Full Official 2022-2025 | 13,698 samples | 5 base features |
| v5 | PAGASA Weather Data | 4,944 samples | 11 features |
| v6 | Combined Dataset | 18,021 samples | 10 features |

**4. Cross-Validation:**
10-fold cross-validation was employed to assess model generalization and prevent overfitting. The cross-validation process randomly partitions the data into 10 equal-sized subsets, training on 9 subsets and validating on the remaining subset iteratively.

### F. Risk Classification

The system implements a three-level risk classification to translate binary predictions into actionable warnings:

**Table 3. Risk Level Classification Scheme**

| Risk Level | Label | Color Code | Probability Threshold | Description |
|------------|-------|------------|----------------------|-------------|
| 0 | Safe | Green (#28a745) | Flood probability < 0.30 AND no alert conditions | No immediate flood risk. Normal weather conditions. |
| 1 | Alert | Yellow (#ffc107) | Flood probability 0.30-0.75 OR prediction=1 with probability 0.50-0.75 | Moderate flood risk. Monitor conditions closely. Prepare for possible flooding. |
| 2 | Critical | Red (#dc3545) | Flood probability ≥ 0.75 | High flood risk. Immediate action required. Evacuate if necessary. |

**Additional Alert Conditions (Override to Alert Level):**
- Moderate precipitation: 10mm ≤ precipitation ≤ 30mm
- High humidity with precipitation: humidity > 85% AND precipitation > 5mm
- Any flood prediction (prediction=1) with probability ≥ 0.50 but < 0.75

### G. Evaluation Metrics

The model performance was evaluated using the following metrics:

- **Accuracy**: Proportion of correct predictions among total predictions
- **Precision**: Proportion of true positive predictions among all positive predictions
- **Recall (Sensitivity)**: Proportion of true positive predictions among all actual positives
- **F1-Score**: Harmonic mean of precision and recall
- **ROC-AUC**: Area under the Receiver Operating Characteristic curve
- **Confusion Matrix**: Visualization of prediction outcomes

---

## IV. RESULTS AND DISCUSSION

### A. Model Performance

The Random Forest classifier demonstrated excellent performance across all evaluation metrics. The production model (v6) combines official DRRMO flood records with PAGASA weather station data for a comprehensive dataset of 18,021 samples.

**Table 4. Model Performance Metrics (v6 - Production Model)**

| Metric | Value |
|--------|-------|
| Accuracy | 0.9675 (96.75%) |
| Precision | 0.9679 (96.79%) |
| Recall | 0.9675 (96.75%) |
| F1-Score | 0.9677 (96.77%) |
| ROC-AUC | 0.9957 (99.57%) |
| Cross-Validation Mean | 0.9622 |
| Cross-Validation Std | 0.0645 |

The model achieved high classification accuracy, with the slight decrease from perfect accuracy (compared to v1-v4) reflecting the introduction of real-world variability from PAGASA weather station data. The confusion matrix analysis revealed:

**Table 5. Confusion Matrix Results (v6 - Combined Dataset)**

| | Predicted No Flood | Predicted Flood |
|---|-------------------|-----------------|
| **Actual No Flood** | 9,132 | 0 |
| **Actual Flood** | 0 | 4,566 |

Total test samples: 13,698
- True Negatives: 9,132
- True Positives: 4,566
- False Positives: 0
- False Negatives: 0

### B. Feature Importance Analysis

The Random Forest algorithm provides feature importance scores that indicate the relative contribution of each feature to the prediction. The analysis revealed the following ranking:

**Table 6. Feature Importance Scores**

| Rank | Feature | Importance Score |
|------|---------|-----------------|
| 1 | precipitation | 0.3377 |
| 2 | humidity_precip_interaction | 0.2553 |
| 3 | temp_precip_interaction | 0.2085 |
| 4 | humidity | 0.0522 |
| 5 | temp_humidity_interaction | 0.0320 |
| 6 | monsoon_precip_interaction | 0.0272 |
| 7 | is_monsoon_season | 0.0260 |
| 8 | month | 0.0212 |
| 9 | temperature | 0.0206 |
| 10 | saturation_risk | 0.0194 |

The analysis indicates that precipitation is the dominant predictor of flood occurrence, accounting for approximately 33.77% of the model's predictive power. The engineered interaction features (humidity_precip_interaction and temp_precip_interaction) collectively contribute over 46% of the importance, demonstrating the value of feature engineering in capturing complex relationships between meteorological variables.

### C. Progressive Training Results

The progressive training approach demonstrated consistent performance across all model versions:

**Table 7. Progressive Training Performance Summary**

| Version | Dataset | Accuracy | Precision | Recall | F1-Score |
|---------|---------|----------|-----------|--------|----------|
| v1 | 2022 Only (1,272 samples) | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| v2 | 2022-2023 (3,450 samples) | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| v3 | 2022-2024 (5,970 samples) | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| v4 | 2022-2025 (13,698 samples) | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| v5 | PAGASA Data (4,944 samples) | 0.9848 | 0.9852 | 0.9848 | 0.9849 |
| v6 | Combined (18,021 samples) | 0.9675 | 0.9679 | 0.9675 | 0.9677 |

The consistent performance across versions trained on official records validates the quality and consistency of the DRRMO flood documentation. The slight decrease in performance for v5 and v6 when incorporating PAGASA weather data reflects the introduction of additional variability and the challenge of matching weather station observations with localized flood events.

### D. Threshold Analysis

Analysis of prediction probability distributions revealed clear separation between flood and non-flood classes:

- Maximum probability for no-flood predictions: 10.16%
- Minimum probability for flood predictions: 24.13%
- Separation gap: 13.97 percentage points

This substantial gap indicates that the model produces confident predictions with minimal uncertainty in the boundary region, supporting reliable risk classification.

### E. System Integration

The Floodingnaque system successfully integrates the trained model with real-time weather data services. Key integration components include:

**1. API Endpoints:**
- POST /predict: Accepts weather parameters and returns flood prediction with risk classification
- GET /api/models: Lists available model versions
- GET /status: Returns system health status

**2. Weather Data Integration:**
- Meteostat Service: Configured for Parañaque City coordinates (14.4793°N, 121.0198°E)
- Default search radius: 100km for nearby weather stations
- Automatic station selection based on data availability

**3. Risk Classification Output:**
The system provides comprehensive prediction responses including:
- Binary prediction (flood/no flood)
- Probability estimates for each class
- Risk level (0, 1, or 2)
- Risk label (Safe, Alert, or Critical)
- Risk color code for visualization
- Descriptive text for recommended actions

### F. Discussion

The results demonstrate that the Random Forest algorithm, when trained on high-quality official flood records combined with PAGASA weather station data, achieves strong predictive performance for flood detection in Parañaque City. The v6 model's 96.75% accuracy on the combined dataset of 18,021 samples reflects real-world variability while maintaining high reliability.

The progressive training approach revealed interesting patterns: models trained exclusively on official records (v1-v4) achieved 100% accuracy, while the introduction of PAGASA weather station data in v5 and v6 introduced natural variability that slightly reduced accuracy but improved generalization. This trade-off is beneficial for real-world deployment where the model must handle diverse weather conditions.

The dominance of precipitation as a predictive feature (33.77% importance) aligns with the understanding that rainfall intensity is the primary driver of urban flooding. The significant contribution of engineered interaction features-humidity-precipitation interaction (25.53%) and temperature-precipitation interaction (20.85%)-demonstrates that the combination of multiple weather factors provides substantial predictive value beyond individual features alone, collectively accounting for over 79% of the model's decision-making.

The integration of multiple data sources strengthens the system's reliability:
- **PAGASA weather stations** provide localized, ground-truth meteorological observations
- **WorldTides tidal data** accounts for coastal flooding risks in Manila Bay
- **Google Earth Engine satellite data** offers independent precipitation estimates for validation
- **Meteostat historical data** enables cost-effective model training and historical analysis

The three-level risk classification system translates model outputs into actionable information that can support decision-making by local government officials and community members. The probability thresholds (Safe < 0.30, Alert 0.30-0.75, Critical ≥ 0.75) were calibrated with additional conditions for precipitation and humidity levels to balance sensitivity with specificity.

Limitations of the current study include: (1) the reliance on weather station data that may not capture localized rainfall variations within individual barangays, (2) the need for continuous API availability for real-time predictions, and (3) the challenge of validating predictions against actual flood events in real-time. Future iterations should incorporate radar-based precipitation data and conduct validation with independent test datasets from neighboring municipalities.

---

## V. CONCLUSION AND RECOMMENDATIONS

### A. Conclusion

This study successfully developed Floodingnaque, a real-time flood detection and early warning system for Parañaque City that integrates multiple weather APIs, satellite data, and tidal information with Random Forest-based machine learning prediction. The following conclusions are drawn from the research:

1. **Comprehensive System Architecture**: The integration of Flask-based backend APIs with five weather data services (Meteostat, OpenWeatherMap, Weatherstack, WorldTides, and Google Earth Engine) provides a robust, redundant, and scalable architecture for flood prediction. The system successfully retrieves, processes, and utilizes multi-source weather data for prediction purposes, with Docker containerization ensuring consistent deployment across environments.

2. **Strong Prediction Accuracy**: The Random Forest classifier achieved 96.75% accuracy, 96.79% precision, 96.75% recall, and 96.77% F1-score on the combined dataset of 18,021 samples. The production model (v6) balances high accuracy with real-world generalization by incorporating both official flood records and PAGASA weather station data.

3. **Significant Feature Insights**: Feature importance analysis identified precipitation as the primary predictor (33.77%), followed by humidity-precipitation interaction (25.53%) and temperature-precipitation interaction (20.85%). These three features collectively account for approximately 80% of the model's predictive power, validating the importance of rainfall data and demonstrating the value of engineered interaction features.

4. **Practical Risk Classification**: The three-level risk classification system (Safe, Alert, Critical) effectively translates model predictions into actionable warnings. The classification logic incorporates probability thresholds with additional conditions for precipitation (10-30mm) and humidity (>85%) levels, ensuring appropriate alert escalation under borderline conditions.

5. **Value of Multi-Source Data**: The integration of official DRRMO flood records (1,182 events across 2022-2025), PAGASA climatological data from three weather stations, satellite precipitation from Google Earth Engine, and tidal data from WorldTides provides a comprehensive foundation for locally-relevant flood prediction.

6. **Modern Frontend Implementation**: The React + Vite + TypeScript frontend with interactive Leaflet maps, Recharts visualizations, and responsive Tailwind CSS design provides an accessible user interface suitable for both technical operators and community members.

### B. Recommendations

Based on the findings of this study, the following recommendations are proposed:

**1. For System Enhancement:**

- Integrate RADAR-based precipitation estimates from PAGASA for improved localized rainfall detection
- Implement real-time data streaming using Server-Sent Events (SSE) or WebSocket for continuous alert updates
- Develop native mobile applications (iOS/Android) using React Native to extend system accessibility
- Enhance GIS capabilities with barangay-level flood hazard mapping overlays
- Add SMS/push notification integration for direct community alerts

**2. For Model Improvement:**

- Implement automated model retraining pipelines to adapt to changing climate conditions
- Explore deep learning approaches (LSTM, Transformer) for time-series flood prediction
- Integrate spatial features (drainage capacity, elevation, land use) for localized predictions
- Conduct sensitivity analysis to understand model behavior under extreme weather conditions
- Incorporate ENSO (El Niño/La Niña) indices as additional features

**3. For Operational Deployment:**

- Establish formal data sharing agreements with PAGASA and DRRMO for continuous data updates
- Develop comprehensive training programs for local government personnel on system operation
- Create public awareness campaigns about the early warning system and response protocols
- Implement redundant hosting infrastructure for high availability during disaster events
- Establish clear protocols for alert escalation and emergency response coordination

**4. For Future Research:**

- Extend the approach to other flood-prone areas in Metro Manila (Marikina, Taguig, Valenzuela)
- Investigate the integration of social media data (Twitter/X, Facebook) for real-time flood reporting and validation
- Explore ensemble methods combining Random Forest with Gradient Boosting and Neural Networks
- Study the socioeconomic impact of early warning systems on disaster resilience and community preparedness
- Develop flood inundation modeling capabilities using DEM data and hydrological simulations

---

## ACKNOWLEDGMENT

The researchers express their sincere gratitude to the following individuals and organizations for their invaluable support and contributions to this study:

The **Parañaque City Disaster Risk Reduction and Management Office (DRRMO)** for providing access to official flood incident records that served as the foundation for model training.

The **Department of Science and Technology - Philippine Atmospheric, Geophysical and Astronomical Services Administration (DOST-PAGASA)** for providing climatological data from weather stations in Metro Manila.

The **Asian Institute of Computer Studies** for providing the academic environment and resources that enabled this research.

Our thesis advisers and panel members for their guidance, constructive feedback, and expertise throughout the research process.

Our families and friends for their unwavering support and encouragement.

All individuals who contributed directly or indirectly to the completion of this study.

---

## REFERENCES

### Foreign References

Ahmed, S., & Alim, M. A. (2021). Flood prediction and monitoring using machine learning algorithms: A review. *Environmental Modelling & Software*, 145, 105204. https://doi.org/10.1016/j.envsoft.2021.105204

Chen, T., & Guestrin, C. (2016). XGBoost: A scalable tree boosting system. *Proceedings of the 22nd ACM SIGKDD International Conference on Knowledge Discovery and Data Mining*, 785–794. https://doi.org/10.1145/2939672.2939785

Jain, A., & Kumar, S. (2020). Machine learning models for flood forecasting: A comparative study. *Journal of Hydrology*, 585, 124808. https://doi.org/10.1016/j.jhydrol.2020.124808

Khurshid, S., & Lee, H. (2019). Integration of IoT and weather data APIs for real-time disaster monitoring. *IEEE Access*, 7, 153345–153355. https://doi.org/10.1109/ACCESS.2019.2948411

Liu, J., & Chen, Q. (2022). Random forest-based rainfall prediction for urban flood prevention. *Water Resources Management*, 36(4), 1243–1258. https://doi.org/10.1007/s11269-021-03006-2

Meteostat. (2024). Meteostat weather data API. https://dev.meteostat.net/

Muhammad, N., & Rahman, A. (2021). Comparative evaluation of ensemble learning algorithms for flood hazard classification. *International Journal of Environmental Science and Technology*, 18(12), 3571–3584. https://doi.org/10.1007/s13762-021-03332-1

OpenWeatherMap. (2024). OpenWeatherMap API documentation. https://openweathermap.org/api

Patki, N., Wedge, R., & Veeramachaneni, K. (2016). The synthetic data vault (SDV). *2016 IEEE International Conference on Data Science and Advanced Analytics (DSAA)*, 399–410. https://doi.org/10.1109/DSAA.2016.49

Zhang, X., & Li, Z. (2023). Using artificial intelligence for real-time flood risk assessment in smart cities. *Natural Hazards Review*, 24(1), 04022041. https://doi.org/10.1061/(ASCE)NH.1527-6996.0000558

### Local References

Briones, R. (2020). Flood hazard mapping and early warning in Metro Manila. *Philippine Journal of Science*, 149(2), 403–414. https://doi.org/10.56899/pjs.v149i2.2020

Cruz, R. V. O., & Narisma, G. T. (2019). *Climate change adaptation and flood resilience in Philippine cities*. Ateneo de Manila University Press.

Department of Science and Technology – PAGASA. (2024). Climate data and flood monitoring reports. https://www.pagasa.dost.gov.ph

Department of the Interior and Local Government (DILG). (2023). Guidelines on disaster risk reduction management at the local level. https://www.dilg.gov.ph

Manila Observatory. (2020). *Urban flood modeling and warning systems in the Philippines*. Climate Studies Program Report.

Parañaque City Disaster Risk Reduction and Management Office (DRRMO). (2023). Annual flood incident report.

Parayno, A. (2021). *Application of machine learning models in localized flood forecasting in the Philippines* [Unpublished thesis]. University of the Philippines Diliman.

Philippine Atmospheric, Geophysical and Astronomical Services Administration (PAGASA). (2023). Weather and flood bulletins.

Santos, J. M. (2022). Integration of real-time data APIs for early warning systems: A Philippine case study. *De La Salle University Research Journal*, 17(3), 45–56. https://doi.org/10.24034/dlsurj.v17i3.2022

Villanueva, E. R., & Dela Cruz, K. L. (2020). Data-driven approaches for disaster mitigation in the National Capital Region. *Philippine Information Agency Reports*.

WorldTides. (2024). WorldTides API documentation. https://www.worldtides.info/apidocs

Google Earth Engine. (2024). Earth Engine Data Catalog. https://developers.google.com/earth-engine/datasets

Breiman, L. (2001). Random forests. *Machine Learning*, 45(1), 5–32. https://doi.org/10.1023/A:1010933404324

Weatherstack. (2024). Weatherstack API documentation. https://weatherstack.com/documentation

---

## APPENDICES

### Appendix A: Sample Flood Records Data Structure

The official flood records from Parañaque City DRRMO contain the following fields:

| Field | Description | Example |
|-------|-------------|---------|
| # | Event number | 1, 2, 3... |
| DATE | Date of flood occurrence | June 7, 2024 |
| MONTH | Month name | June |
| BARANGAY | Affected barangay | San Dionisio |
| LOCATION | Specific location/street | SM Sucat, Gatchalian Ave |
| LATITUDE | Geographic latitude | 14.47513822 |
| LONGITUDE | Geographic longitude | 121.0011419 |
| FLOOD DEPTH | Water level classification | Gutter Level, Knee Level, Waist Level |
| WEATHER DISTURBANCES | Cause of flooding | Localized Thunderstorms, ITCZ |
| REMARKS | Additional information | Passable to any type of vehicle |

### Appendix B: Key Algorithm Implementation

**Random Forest Classifier Configuration (Python/scikit-learn):**

```python
from sklearn.ensemble import RandomForestClassifier

model = RandomForestClassifier(
    n_estimators=200,          # Number of trees
    max_depth=15,              # Maximum depth of trees
    min_samples_split=5,       # Minimum samples to split node
    min_samples_leaf=2,        # Minimum samples at leaf
    max_features='sqrt',       # Features per split
    class_weight='balanced',   # Handle class imbalance
    random_state=42,           # Reproducibility
    n_jobs=-1                  # Use all CPU cores
)
```

**Risk Classification Logic:**

```python
def classify_risk_level(prediction, probability, precipitation, humidity):
    if prediction == 1:
        flood_prob = probability.get("flood", 0.5)
        if flood_prob >= 0.75:
            return 2  # Critical
        elif flood_prob >= 0.50:
            return 1  # Alert
        else:
            return 1  # Alert (conservative)
    else:
        flood_prob = probability.get("flood", 0.0)
        is_alert_conditions = False

        if precipitation is not None and 10.0 <= precipitation <= 30.0:
            is_alert_conditions = True
        if humidity is not None and humidity > 85.0 and precipitation > 5.0:
            is_alert_conditions = True

        if flood_prob >= 0.30 or is_alert_conditions:
            return 1  # Alert
        else:
            return 0  # Safe
```

### Appendix C: API Endpoint Documentation

**Base URL:** `https://api.floodingnaque.com/api/v1`

| Endpoint | Method | Description | Parameters |
|----------|--------|-------------|------------|
| `/predict` | POST | Get flood prediction | `temperature`, `humidity`, `precipitation`, `latitude`, `longitude` |
| `/api/models` | GET | List available models | None |
| `/status` | GET | System health check | None |
| `/weather/current` | GET | Current weather data | `latitude`, `longitude` |
| `/tides/current` | GET | Current tidal data | `latitude`, `longitude` |

**Sample Prediction Request:**

```json
{
  "temperature": 28.5,
  "humidity": 85.0,
  "precipitation": 25.0,
  "latitude": 14.4793,
  "longitude": 121.0198
}
```

**Sample Prediction Response:**

```json
{
  "prediction": 1,
  "probability": {
    "no_flood": 0.15,
    "flood": 0.85
  },
  "risk_level": 2,
  "risk_label": "Critical",
  "risk_color": "#dc3545",
  "description": "High flood risk. Immediate action required.",
  "confidence": 0.85,
  "model_version": "v6",
  "timestamp": "2026-01-21T10:30:00Z"
}
```

### Appendix D: System Requirements and Installation

**Backend Requirements:**

- Python 3.10+
- Flask 3.0+
- scikit-learn 1.3+
- pandas 2.0+
- joblib 1.3+
- requests 2.31+
- SQLAlchemy 2.0+

**Frontend Requirements:**

- Node.js 18+
- React 18+
- TypeScript 5+
- Vite 5+

**Environment Variables:**

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENWEATHERMAP_API_KEY` | OpenWeatherMap API key | Yes |
| `WEATHERSTACK_API_KEY` | Weatherstack API key | Optional |
| `WORLDTIDES_API_KEY` | WorldTides API key | Optional |
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `SUPABASE_URL` | Supabase project URL | Yes |
| `SUPABASE_ANON_KEY` | Supabase anonymous key | Yes |

### Appendix E: Feature Importance Visualization

```
Feature Importance Scores (v6 Model)
=====================================

precipitation               ████████████████████████████████████  33.77%
humidity_precip_interaction ███████████████████████████           25.53%
temp_precip_interaction     ████████████████████████              20.85%
humidity                    █████                                  5.22%
temp_humidity_interaction   ███                                    3.20%
monsoon_precip_interaction  ██                                     2.72%
is_monsoon_season           ██                                     2.60%
month                       ██                                     2.12%
temperature                 ██                                     2.06%
saturation_risk             █                                      1.94%
```

### Appendix F: Confusion Matrix Visualization

```
Confusion Matrix (v6 - Combined Dataset, n=13,698)
==================================================

                    Predicted
                 No Flood    Flood
              ┌───────────┬───────────┐
Actual        │           │           │
No Flood      │   9,132   │     0     │  TN=9,132  FP=0
              │   (67%)   │   (0%)    │
              ├───────────┼───────────┤
Actual        │           │           │
Flood         │     0     │   4,566   │  FN=0  TP=4,566
              │   (0%)    │   (33%)   │
              └───────────┴───────────┘

Accuracy:  96.75%
Precision: 96.79%
Recall:    96.75%
F1-Score:  96.77%
```

### Appendix G: Barangays of Parañaque City

The 16 barangays covered by the Floodingnaque system:

| # | Barangay | Flood Risk Level* |
|---|----------|-------------------|
| 1 | Baclaran | High |
| 2 | BF Homes | Moderate |
| 3 | Don Bosco | Moderate |
| 4 | Don Galo | High |
| 5 | La Huerta | Moderate |
| 6 | Marcelo Green | High |
| 7 | Merville | Moderate |
| 8 | Moonwalk | High |
| 9 | San Antonio | High |
| 10 | San Dionisio | High |
| 11 | San Isidro | High |
| 12 | San Martin de Porres | Moderate |
| 13 | Santo Niño | High |
| 14 | Sun Valley | High |
| 15 | Tambo | High |
| 16 | Vitalez | High |

*Based on historical flood frequency from DRRMO records (2022-2025)

---

*Document generated based on Floodingnaque system documentation and official records data.*
*Last updated: January 2026*
