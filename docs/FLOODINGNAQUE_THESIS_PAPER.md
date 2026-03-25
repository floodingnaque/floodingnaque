FLOODINGNAQUE: A REAL-TIME FLOOD DETECTION AND EARLY WARNING
SYSTEM UTILIZING API AND RANDOM FOREST ALGORITHM
Andam, Edrian1, Barba, Christian Dave2, De Castro, Donna Belle3, Domingo, Rengiee4,
Gumba, Jeff Christian5, Martizano, Ramil C.6, Quiray, Noriel A.7
Bachelor of Science in Computer Science, Asian Institute of Computer Studies
1571 Triangle Bldg., Doña Soledad Avenue, Better Living Subd, Parañaque City, 1709 Metro Manila, Philippines
1edrian.andam07@gmail.com
2Christianbarba12@gmail.com
3Decastrobellebelle@gmail.com
4rengieedomingo025@gmail.com
5gjeffchristian@gmail.com
6iamdefinitely.ramil@gmail.com
7norielqry@gmail.com

Abstract
Purpose – This study aims to design, develop, and evaluate Floodingnaque, a real-time flood detection and early warning system for Parañaque City, Metro Manila, Philippines. The system integrates weather Application Programming Interfaces (APIs) with the Random Forest machine learning algorithm to predict flood occurrence and classify risk levels.
Method – This study used a developmental research design that combines software engineering practices with machine learning model development and evaluation. The system was developed using a Flask-based backend and a React frontend. The Random Forest classifier was trained on official flood records from the Parañaque City Disaster Risk Reduction and Management Office (DRRMO) from 2022 to 2025, which included 295 documented flood incidents. The study integrated multiple weather APIs, including Meteostat, OpenWeatherMap, Weatherstack, WorldTides, and Google Earth Engine, to obtain real-time and historical meteorological data. A progressive training approach was applied across six model versions, expanding the dataset to 6,570 records using data from DRRMO, PAGASA weather stations, and external API sources.
Results – The final production model (v6) achieved an accuracy of 97.35%, precision of 97.51%, recall of 97.35%, and an F1-score of 97.38% using the combined dataset of 6,570 records. It also obtained a Receiver Operating Characteristic Area Under the Curve (ROC-AUC) of 99.21%. Feature importance analysis showed that three-day cumulative precipitation was the most influential predictor (30.24%), followed by rain streak duration (18.52%) and the interaction between humidity and precipitation (15.97%). The system effectively implements a three-level risk classification scheme (Safe, Alert, Critical) calibrated using real DRRMO flood probability distributions.
Discussion – The results indicate that antecedent rainfall, which refers to accumulated rainfall over previous days, is more effective in predicting urban flooding than single-time measurements. This finding supports hydrological principles related to soil saturation. The use of multiple weather data sources improved system reliability. In addition, the three-level risk classification converts probabilistic outputs into actionable warnings that align with the PAGASA Rainfall Warning System.
Conclusion – Floodingnaque demonstrates that a Random Forest-based system integrated with weather APIs can achieve high predictive accuracy for localized urban flood detection. The system offers a data-driven, accessible, and scalable approach to disaster risk reduction in Parañaque City. It also supports local government units in improving flood preparedness and response.
Recommendations – Future studies should integrate radar-based precipitation data from PAGASA, explore deep learning models such as Long Short-Term Memory (LSTM) networks, and develop native mobile applications to increase accessibility. Researchers should also consider incorporating Internet of Things (IoT) sensor networks for real-time ground validation and establishing formal data-sharing agreements with DRRMO and PAGASA to support continuous model improvement.
Social Implication – The system promotes community resilience in flood-prone barangays of Parañaque City by providing timely and evidence-based flood warnings. These warnings support early evacuation and efficient resource allocation. The web-based interface improves access to early warning information for both residents and local government officials, contributing to national disaster risk reduction efforts.
Keywords: Disaster Risk Reduction, Early Warning System, Flood Prediction, Machine Learning, Parañaque City, Random Forest Algorithm, Weather API
I. INTRODUCTION
Flooding is one of the most destructive natural hazards affecting urban communities worldwide. Its impacts continue to increase due to climate change and rapid urban expansion. The Philippines consistently ranks among the most disaster-prone countries because of its geographic exposure to typhoons, monsoons, and seasonal heavy rainfall. Metro Manila, the country’s capital region, experiences frequent flooding that causes property damage, disrupts infrastructure, and threatens human life. Within this region, Parañaque City, located in the southern part of Metro Manila along Manila Bay, is highly vulnerable. Its low-lying coastal terrain, proximity to tidal waterways, and high level of urbanization increase flood risk during the Southwest Monsoon season from June to November and during localized convective thunderstorms throughout the year.
The effects of recurring flooding in Parañaque City extend beyond immediate physical damage. Bankoff (2003) examined the historical, environmental, and social factors contributing to flood vulnerability in Metropolitan Manila and found that rapid urbanization, inadequate drainage systems, and geographic exposure have made the region highly susceptible to flooding. Rivera and Vega (2025) further explain that recurrent flash floods in the Philippines require a shift from reactive disaster response to proactive resilience-building strategies. Besarra et al. (2025) measured the economic impact of flood events on housing in the Philippines under climate change projections, emphasizing the need for effective early warning systems at the local level. Bagtasa (2022) showed that rainfall from tropical cyclones in the Philippines varies significantly across time and location, highlighting the importance of localized precipitation monitoring for accurate flood prediction in cities such as Parañaque.
Traditional flood monitoring methods rely mainly on manual observation and post-event reporting, which limit timely response. Garcia et al. (2015) demonstrated the feasibility of automated real-time flood monitoring in Metro Manila. Similarly, Te et al. (2024) validated the use of Internet of Things (IoT) pressure sensors with LoRaWAN connectivity for localized flood detection, providing a strong technological foundation for this study. The increasing availability of weather data through Application Programming Interfaces (APIs), combined with advances in machine learning, creates an opportunity to develop proactive and automated flood prediction systems tailored to flood-prone urban areas in the Philippines.
This study introduces Floodingnaque, a real-time flood detection and early warning system for Parañaque City. The system integrates multiple weather APIs with a Random Forest machine learning classifier. It uses official flood incident records from the Parañaque City Disaster Risk Reduction and Management Office (DRRMO), climatological data from PAGASA weather stations, satellite-based precipitation data from Google Earth Engine, and tidal data from the WorldTides API. These data sources support the development of a reliable and locally calibrated flood prediction system.
Statement of the Problem
Despite the frequent occurrence of flooding in Parañaque City, there is no automated flood prediction and early warning system at the barangay level that provides timely and actionable risk information. Current monitoring practices rely on manual observation, informal reporting, and general national bulletins from PAGASA, which lack the spatial detail needed to differentiate flood risk within the city.
This study addresses the following questions:

1. How can a machine learning model trained on official local flood records and multi-source weather data accurately predict flood occurrence in Parañaque City?
2. What system architecture can effectively integrate multiple real-time weather APIs with a flood prediction model for operational use?
3. How accurately can the Random Forest classifier categorize flood risk into three actionable levels (Safe, Alert, Critical) using meteorological features?
4. Which meteorological features contribute most to accurate flood prediction in the context of Parañaque City?
   Objectives of the Study
   The main objective of this study is to design, develop, and evaluate Floodingnaque, a web-based real-time flood detection and early warning system for Parañaque City. Specifically, the study aims to:
5. Design and implement a system architecture that integrates multiple weather data sources through APIs, including Meteostat, OpenWeatherMap, Weatherstack, WorldTides, and Google Earth Engine.
6. Train and evaluate a Random Forest classifier using official flood records from the Parañaque City DRRMO from 2022 to 2025, along with supplementary data from PAGASA weather stations.
7. Evaluate the model’s performance using accuracy, precision, recall, F1-score, ROC-AUC, and cross-validation metrics.
8. Develop a three-level risk classification system (Safe, Alert, Critical) that converts probabilistic predictions into clear and actionable warnings for the community.
9. Create an accessible and interactive web-based interface that presents real-time risk information through maps, alerts, and dashboard features.
   Significance of the Study
   Community and Residents of Parañaque City. The system provides residents in flood-prone barangays with timely, accessible, and localized flood risk information. This supports early preparedness actions such as evacuation, property protection, and monitoring of high-risk areas.
   Local Government Units (LGUs) and DRRMO. The Parañaque City Disaster Risk Reduction and Management Office can use the system as a data-driven decision-support tool. It translates meteorological data into risk levels, which helps improve the planning and deployment of emergency response resources.
   Researchers and the Academic Community. This study contributes to research on machine learning applications in disaster risk reduction in the Philippines. It offers a clear methodology for developing localized flood prediction systems using open-source tools and official government data.
   Future Researchers. The Floodingnaque system and its documented process provide a framework that future studies can adapt for other flood-prone areas in Metro Manila and across the Philippines.
   Scope and Delimitation
   This study focuses on the design, development, and evaluation of a flood prediction system for Parañaque City, Metro Manila, Philippines, covering all 16 barangays. It uses official DRRMO flood records from 2022 to 2025, PAGASA climatological data from 2020 to 2025, and additional data from satellite and tidal sources.
   The system predicts flood occurrence and classifies risk into three levels but does not estimate flood depth. Real-time validation using live flood events is not included in this phase of the study. This aspect is recommended for future research through pilot testing and field deployment.
   II. LITERATURE REVIEW
   A. Flood Risk and Urban Vulnerability in the Philippines
   Flooding in the Philippines remains a persistent and growing national concern. This issue results from the combined effects of geographic exposure, seasonal monsoons, typhoon activity, and increasing urban population density. Araza and Alosnos (2025) improved Earth Observation-based methods for mapping flood and drought impacts on agricultural production in the Philippines. Their study highlights that the effects of flooding extend beyond infrastructure damage and include broader socioeconomic consequences.
   Onsay et al. (2025) used a combination of machine learning, econometric methods, and hermeneutic analysis to forecast flood risks during Typhoon Kristine (TS Trami) in the Bicol region. Their findings show that machine learning approaches can combine community experiences with quantitative disaster data in the Philippine context.
   Understanding community behavior is also essential in assessing flood vulnerability. Pascual et al. (2024) identified key factors that influence residents’ preparedness for flash floods in the Philippines. These factors include perceived severity, social influence, and access to information. Similarly, de Veluz et al. (2025) applied protection motivation theory and the theory of planned behavior to show that source credibility and social influence strongly affect preparedness intentions in Quezon Province. Besarra et al. (2025) further emphasized the economic impact of flooding by estimating increased housing damage costs due to climate change. Their findings highlight the need for effective early warning systems at the local government level.
   Rivera and Vega (2025) provided a comprehensive review of flash flood causes, impacts, and mitigation strategies in the Philippines. They emphasized the importance of shifting from reactive responses to proactive and technology-based risk reduction approaches. Bagtasa (2022) demonstrated that rainfall from tropical cyclones varies significantly across regions, which supports the need for localized precipitation monitoring instead of relying on national averages. Bankoff (2003) explained that Metro Manila’s flood vulnerability is shaped by historical, social, and environmental factors. These include inadequate infrastructure, informal settlements, and geographic exposure, which together increase flood risk.
   B. Machine Learning for Flood Prediction and Susceptibility Mapping
   Machine learning has become a widely used approach for flood prediction and susceptibility assessment. It often performs better than traditional hydrological models in terms of predictive accuracy and efficiency. Mosavi et al. (2018) reviewed various machine learning models for flood prediction and found that ensemble classifiers are especially effective in modeling complex and nonlinear relationships between weather variables and flood occurrence.
   Wang et al. (2015) provided one of the early applications of the Random Forest algorithm for flood hazard assessment. Their study demonstrated its ability to rank feature importance and established a methodological foundation for later research. Bui et al. (2019) confirmed the effectiveness of tree-based ensemble methods, including Random Forest, for flash flood susceptibility modeling in areas with limited data. This finding is particularly relevant to the Parañaque City context.
   Bennett et al. (2018) showed that antecedent precipitation, or rainfall accumulated over previous days, is a key factor in determining flood volume. This finding supports the use of rolling precipitation features in the Floodingnaque model. Nguyen et al. (2025) addressed uncertainty in flood predictions by applying machine learning with Monte Carlo analysis. Their work provides guidance for interpreting prediction confidence in operational flood warning systems.
   Tavakoli et al. (2026) introduced a particle swarm optimization (PSO)-based machine learning framework with SHAP-based clustering for flood susceptibility assessment. Their study highlights the importance of explainability tools in helping non-technical users understand model outputs. Mishra and Albano (2026) developed a Python-based application for flood depth estimation using machine learning, reinforcing the suitability of Python frameworks such as Flask and scikit-learn used in this study. Magoulick (2026) presented a digital twin framework for multi-hazard coastal flood prediction with adaptive learning, showing the potential of integrating real-time data with continuously updated models.
   C. Random Forest and Advanced Ensemble Methods
   The Random Forest algorithm, introduced by Breiman (2001), builds multiple decision trees and combines their outputs through majority voting. This process improves classification accuracy and reduces the risk of overfitting compared to single decision tree models. Its ability to handle high-dimensional data and provide feature importance analysis makes it suitable for meteorological prediction tasks.
   Li et al. (2026) applied Random Forest in a cloud-based alert monitoring and analysis system. Their findings confirm its effectiveness for real-time alert classification, which aligns with the risk classification function of Floodingnaque. Yoganand et al. (2026) combined SHAP-based explainability with transfer learning for flood prediction, showing that model interpretability can be improved through feature attribution techniques.
   Yao et al. (2026) proposed a deep learning framework using Bayesian optimization and BiLSTM-U-Net architecture for urban flood prediction. This work suggests potential directions for future system enhancements. Ke et al. (2025) integrated machine learning with GeoDetector for regional flood susceptibility mapping and demonstrated that ensemble models maintain strong performance across different spatial scales.
   Lee et al. (2026) applied interpretable machine learning techniques to urban flood mapping, emphasizing their importance for policy and planning decisions. Huang et al. (2026) used long-term flood data from the Indo-China Peninsula to train machine learning models, highlighting the value of historical datasets. This supports the use of official DRRMO records in the present study.
   D. Weather APIs, IoT, and Real-Time Data Integration
   The increasing availability of meteorological data through RESTful APIs and IoT sensor networks has enabled the development of real-time environmental monitoring systems. Meng et al. (2018) examined the requirements of developers for API documentation, which informed the design of well-structured and accessible system endpoints in Floodingnaque.
   Garcia et al. (2015) demonstrated the feasibility of real-time urban flood monitoring in Metro Manila, providing a strong local reference for this study. Te et al. (2024) developed an IoT-based flood monitoring system using pressure sensors and LoRaWAN connectivity. Their findings show that distributed sensor networks can effectively support localized flood detection in urban Philippine settings.
   Krishnachaithanya et al. (2025) used Google Earth Engine as a scalable platform for machine learning-based flood risk mapping in large cities. Their study validates the use of satellite datasets such as GPM IMERG and CHIRPS for precipitation estimation. Similarly, Li et al. (2025) combined remote sensing data with explainable machine learning for flood risk assessment in China. Their work supports the integration of satellite-derived data with machine learning models for urban flood management.
   E. Flood Susceptibility Mapping and Regional Case Studies
   Regional studies across Asia provide useful comparisons for flood prediction systems. Askari et al. (2025) applied an entropy-based machine learning framework for flood risk mapping in Pakistan. Their results show that well-calibrated models can produce reliable predictions even with limited local data.
   Vojtek et al. (2026) examined the transferability of machine learning and deep learning models for flood prediction across different river systems in Slovakia. Their findings indicate that model performance depends heavily on the quality and representativeness of training data. This insight supports the progressive training approach used in the Floodingnaque system.

III. METHODOLOGY
A. Research Design
This study uses a developmental research design to design, implement, and evaluate a flood prediction system. The methodology combines software development practices with machine learning model development and evaluation. An iterative approach guides the process, allowing continuous refinement of the prediction model. The development progresses through six training phases, with each phase expanding the dataset and feature set to improve model performance.
B. System Architecture
The Floodingnaque system follows a client-server architecture composed of six main layers: backend API, weather data services, machine learning module, frontend interface, database layer, and infrastructure.
The backend API is developed using Flask 3.0 with Python. It provides RESTful endpoints for flood prediction (/api/v1/predict/), model management (/api/models), and system health monitoring (/status). The weather data services layer integrates five providers to ensure data reliability and system resilience. These include Meteostat for historical data, OpenWeatherMap for real-time observations, Weatherstack for precipitation data, WorldTides for tidal information in Manila Bay, and Google Earth Engine for satellite-based precipitation datasets such as GPM IMERG V06 and CHIRPS.
The frontend is a React 19 single-page application built using Vite 7, TypeScript, and Tailwind CSS 4. It uses TanStack Query and Zustand for state management, Leaflet for interactive flood maps, and recharts for data visualization. The database layer uses PostgreSQL hosted on Supabase, with SQLAlchemy as the Object Relational Mapper (ORM) and Alembic for migration management. Docker containerization ensures consistent deployment across development, staging, and production environments.
Table 1. System Architecture Layers // Generate figure

C. Data Collection
Data for this study were collected from four main sources: official flood records, PAGASA weather station data, satellite-derived precipitation, and tidal observations.
The primary dataset consists of official flood incident records from the Parañaque City Disaster Risk Reduction and Management Office (DRRMO) covering the years 2022 to 2025. These records include the date and time of each flood event, affected barangays and locations, geographic coordinates, flood depth classification (Gutter Level, Knee Level, Waist Level), type of weather disturbance (Localized Thunderstorms, ITCZ, Monsoon), and road passability remarks.
Table 2. Summary of Official DRRMO Flood Records (2022–2025) // Generate figure

Climatological data were obtained from DOST-PAGASA weather stations from 2020 to 2025. Three stations were used: Port Area (14.5884°N, 120.9679°E, elevation 15 m), NAIA (14.5047°N, 121.0048°E, elevation 21 m), and Science Garden (14.6451°N, 121.0443°E, elevation 42 m). The dataset includes daily rainfall, temperature, relative humidity, and wind speed.
Satellite-derived precipitation data were obtained from GPM IMERG V06 half-hourly estimates and CHIRPS daily datasets through Google Earth Engine. Tidal data were collected from the WorldTides API using Manila Bay coordinates (14.4793°N, 120.9822°E), which provide current and forecasted tide levels relative to Mean Sea Level.
D. Data Preprocessing
The data preprocessing pipeline consists of three stages: data cleaning, feature engineering, and dataset merging.
During data cleaning, missing values, represented as −999.0 in PAGASA datasets, are handled through imputation or removal. Trace rainfall values (−1.0), which indicate precipitation below 0.1 mm, are retained due to their meteorological relevance. Duplicate entries are removed, and date and time formats are standardized across all datasets.
In the feature engineering stage, several variables are derived to improve model performance. These include: (1) is_monsoon_season, a binary indicator for the months of June to November; (2) temp_humidity_interaction, representing the combined effect of temperature and humidity; (3) humidity_precip_interaction, capturing the relationship between humidity and precipitation; (4) monsoon_precip_interaction; (5) saturation_risk; (6) precip_3day_sum, which represents cumulative rainfall over three days; (7) precip_7day_sum, which represents cumulative rainfall over seven days; (8) rain_streak, defined as the number of consecutive rainy days; and (9) tide_height, obtained from the WorldTides API.
The final dataset for the production model (v6) contains 6,570 records and 13 features.
E. Model Training and Progressive Methodology
The Random Forest classifier is configured with 200 decision trees, a maximum depth of 15, a minimum of 5 samples required to split a node, and a minimum of 2 samples per leaf. It uses square root feature selection and balanced subsampling to address class imbalance. A fixed random state of 42 ensures reproducibility, and parallel processing utilizes all available CPU cores.
A progressive training approach is applied across six model versions to demonstrate continuous improvement. Each version incorporates additional data and features to enhance predictive performance.
Table 3. Progressive Model Training Versions // Generate figure
Model performance is evaluated using five-fold stratified cross-validation to ensure generalization and reduce overfitting. Hyperparameter tuning is performed using grid search cross-validation and Optuna-based Bayesian optimization.
F. Risk Classification Scheme
The system uses a three-level risk classification scheme that converts model probability outputs into actionable warnings: Safe, Alert, and Critical. Threshold values are calibrated using real DRRMO flood probability distributions, where the mean probability for flood events is 0.9445 and the 90th percentile of non-flood events is 0.0544. These thresholds are aligned with the PAGASA Rainfall Warning System to ensure consistency with existing national warning standards.
Table 4. Three-Level Risk Classification Scheme // Generate figure
G. Evaluation Metrics
Model performance is evaluated using six metrics. Accuracy measures the proportion of correct predictions. Precision indicates the proportion of correctly identified positive cases among all predicted positives. Recall, also known as sensitivity, measures the proportion of actual positive cases correctly identified by the model.
The F1-score represents the balance between precision and recall. The Receiver Operating Characteristic Area Under the Curve (ROC-AUC) evaluates the model’s ability to distinguish between classes. Finally, the confusion matrix provides a detailed breakdown of true positives, true negatives, false positives, and false negatives.
IV. RESULTS AND DISCUSSIONS
A. Model Performance
The Random Forest classifier demonstrates strong predictive performance across all evaluation metrics. The production model (v6), trained on a combined dataset of 6,570 records, was tested using a 20% holdout set. After removing records with missing values during preprocessing, the effective dataset yielded 6,235 usable records, of which 20% (1,247) were reserved for testing.
Table 5. Production Model Performance Metrics (v6) // Generate figure

Table 6. Confusion Matrix Results (v6) // Generate figure

The confusion matrix shows only one false negative, which means the model failed to identify one actual flood event. It also produced 23 false positives out of 1,247 test samples. This pattern of errors indicates a conservative model design. The model prioritizes detecting flood events, even if it increases false alarms, which is appropriate for early warning systems focused on protecting lives and property.
B. Feature Importance Analysis
Feature importance scores from the Random Forest model show how each meteorological variable contributes to prediction accuracy.
Table 7. Feature Importance Scores (v6 Production Model) // Generate figure
Three-day cumulative precipitation is the most influential predictor of flood occurrence, accounting for 30.24% of the model’s importance score. This finding supports the hydrological principle that accumulated rainfall affects soil saturation and runoff. Bennett et al. (2018) confirmed that antecedent precipitation plays a key role in determining flood volume.
The rain streak feature contributes 18.52%, capturing the effect of consecutive rainy days on soil saturation. Combined, rolling precipitation features account for more than 55% of the total importance, which is much higher than instantaneous precipitation at 6.65%. This result validates the feature engineering approach used in the study.
The humidity–precipitation interaction feature contributes 15.97%, showing that the combination of atmospheric moisture and rainfall intensity improves prediction accuracy more than either factor alone. This finding is consistent with studies by Askari et al. (2025) and Li et al. (2025) in similar flood risk contexts.
Notably, the tide_height feature contributed negligibly (0.00%), likely due to the coarse temporal resolution of tidal observations relative to the fine-grained flood events and the dominant influence of precipitation-based features. Future work could explore higher-frequency tidal data to better capture coastal flooding dynamics.
C. Progressive Training Results
The progressive training approach illustrates how the model improves as the dataset becomes larger and more diverse.
Table 8. Progressive Training Performance Summary // Generate figure
Versions v1, v2, and v4 achieved perfect test accuracy. However, this result reflects the limited size and uniform nature of the DRRMO-only datasets rather than true predictive capability. Cross-validation scores ranging from 0.972 to 0.995 provide more realistic estimates of performance for these versions.
Version v3 showed a significant drop in accuracy to 61.70%, which resulted from a distribution shift caused by the inclusion of 2024 data. This issue was resolved in version v4 after adding rolling precipitation features.
The inclusion of PAGASA weather station data in v5 and external API data in v6 introduced more variability into the dataset. As a result, test accuracy decreased slightly to 97.35%, but the model’s ability to generalize improved. This trade-off aligns with the findings of Vojtek et al. (2026), who emphasized that exposure to diverse data improves real-world performance.The v6 model exhibits a cross-validation standard deviation of ±9.91%, which is higher than preceding versions. This variance reflects the temporal heterogeneity introduced by merging DRRMO records with multi-year PAGASA observations and satellite-derived data. Individual fold performance ranged from approximately 80% to near-perfect accuracy, indicating that certain temporal partitions (e.g., folds dominated by 2024 monsoon events) are inherently more difficult to classify. Despite this variability, the overall CV mean of 90.60% and the high test-set accuracy of 97.35% confirm that the model generalizes well to unseen data.D. Threshold Analysis
Analysis of probability outputs from the v6 model shows clear separation between flood and non-flood classes.
The mean predicted probability for non-flood cases is 3.50%, while flood cases have a mean probability of 94.45%. The 90th percentile of non-flood predictions is 5.44%, and the 10th percentile of flood predictions is 83.71%. This creates a separation gap of approximately 78.3 percentage points.
This wide gap confirms that the selected thresholds for risk classification are appropriate. Predictions below 0.10 are classified as Safe, while predictions at or above 0.75 are classified as Critical. Only a small number of cases fall within the uncertain range between these thresholds.
E. System Integration
The Floodingnaque system successfully integrates the trained model with real-time weather data services through a Flask-based RESTful API architecture.
The main prediction endpoint (POST /api/v1/predict/) accepts temperature in Kelvin, relative humidity in percentage, and precipitation in millimeters. It also allows optional inputs such as wind speed and atmospheric pressure. The system applies compound rate limiting (60 requests per hour with a 10-request-per-minute burst cap; authenticated users receive doubled limits), validates request size, and requires API key authentication for security. Additional endpoints include GET /api/v1/alerts/ for paginated alert retrieval (120/hr), GET /api/v1/dashboard/summary for aggregated statistics (120/hr), and POST /api/v1/admin/models/retrain for administrator-triggered retraining (5/hr).
Each prediction response includes the binary classification result, flood probability, risk level (Safe, Alert, Critical), color-coded output for visualization, model version, and a request identifier for tracking.
To ensure system reliability, the weather data layer uses a multi-level fallback mechanism. It includes circuit breaker patterns with a failure threshold of five attempts and a 60-second recovery period. The system also uses exponential backoff for retry attempts, which helps maintain service availability during temporary API failures.
F. Discussion
The findings show that the Random Forest model achieves strong predictive performance when trained on official DRRMO flood records combined with PAGASA weather station data and additional external sources.
The dominance of antecedent rainfall features in the model aligns with established hydrological principles, as supported by Bennett et al. (2018). This result confirms the effectiveness of using time-based rainfall features in flood prediction. The low importance of the monsoon season indicator (0.71%) suggests that the model relies more on actual weather conditions than on seasonal assumptions. This is beneficial for real-time applications.
The integration of multiple data sources reflects the multi-sensor approach discussed by Te et al. (2024) and the use of satellite data highlighted by Krishnachaithanya et al. (2025). The three-level risk classification system, aligned with PAGASA standards, ensures that predictions are easy to understand and apply in real-world decision-making.
The system’s web-based interface, built using React, Leaflet, and Recharts, enhances usability for both technical users and community members by presenting clear visualizations and real-time updates.
However, the study has several limitations. First, the reliance on weather stations outside Parañaque City, such as Port Area, NAIA, and Science Garden, may not fully capture local rainfall patterns within specific barangays. Second, the system depends on continuous API availability, which may affect performance during service interruptions, despite the use of fallback mechanisms.
Finally, real-time validation using actual flood events has not yet been conducted. Future research should focus on pilot testing and collaboration with the Parañaque City DRRMO to evaluate the system under real-world conditions.
V. CONCLUSIONS AND RECOMMENDATIONS
Conclusion
This study successfully developed Floodingnaque, a real-time flood detection and early warning system for Parañaque City. The system integrates multiple weather APIs, satellite data, and tidal information with a Random Forest-based machine learning model. Five main conclusions are drawn from the study.
First, the multi-source system architecture, which integrates Meteostat, OpenWeatherMap, Weatherstack, WorldTides, and Google Earth Engine, provides a reliable and scalable platform for flood prediction. The use of fallback mechanisms and circuit breaker patterns improves system resilience during API service interruptions.
Second, the Random Forest classifier achieved strong predictive performance, with 97.35% accuracy, 97.51% precision, 97.35% recall, and a 97.38% F1-score on the combined dataset of 6,570 records. The model also achieved a Receiver Operating Characteristic Area Under the Curve (ROC-AUC) of 99.21%, indicating excellent classification capability for operational use.
Third, feature importance analysis identified three-day cumulative precipitation (30.24%), rain streak duration (18.52%), and humidity–precipitation interaction (15.97%) as the most significant predictors. Together, these features account for approximately 65% of the model’s predictive contribution, confirming the effectiveness of the temporal feature engineering strategy.
Fourth, the three-level risk classification system (Safe, Alert, Critical), calibrated using real DRRMO probability distributions and aligned with PAGASA Rainfall Warning System thresholds, effectively converts probabilistic outputs into clear and actionable warnings for communities.
Fifth, the progressive training approach demonstrates that increasing dataset size and diversity, from 209 DRRMO records in version v1 to 6,570 combined records in version v6, improves model generalizability. This finding highlights the importance of incorporating real-world variability in flood prediction models.
Recommendation
Based on the findings of this study, the following recommendations are proposed for system improvement, deployment, and future research:

1. Future system development should incorporate PAGASA radar-based precipitation data to improve localized rainfall detection within individual barangays. This will address the limitation of relying on weather stations located outside Parañaque City.
2. Automated model retraining pipelines should be implemented to continuously update the model using newly recorded flood events. This approach will allow the system to adapt to changing climate patterns and maintain prediction accuracy.
3. Future studies should explore deep learning models, such as Long Short-Term Memory (LSTM) networks and Transformer-based architectures, to improve time-series flood prediction and capture long-term rainfall patterns.
4. Native mobile applications for iOS and Android should be developed using frameworks such as React Native. This will expand accessibility and enable real-time push notifications for residents in flood-prone areas.
5. Formal data-sharing agreements with PAGASA and the Parañaque City DRRMO should be established to support continuous data updates and allow real-time validation of model predictions against actual flood events.
6. The methodology should be applied to other flood-prone cities in Metro Manila, such as Marikina, Taguig, and Valenzuela. This will help evaluate the transferability of the model and support the development of a wider flood early warning network.
   Social Implications
   Floodingnaque has significant implications for disaster risk reduction in Parañaque City and across the Philippines. By providing timely and evidence-based flood risk information through a web-based platform, the system enables residents and local government officials to make informed decisions about preparedness and evacuation.
   This directly addresses the gaps in preparedness identified by Pascual et al. (2024) and de Veluz et al. (2025), who emphasized that access to reliable and timely information influences community response to flood risks. The system’s three-level risk classification, aligned with PAGASA standards, simplifies complex probability outputs and makes them easier for non-technical users to understand.
   However, several considerations must be addressed during implementation. These include the risk of over-reliance on automated systems, potential inequalities in digital access, and the need for community training to ensure proper interpretation of warnings.
   Acknowledgement
   The researchers express their sincere gratitude to the Parañaque City Disaster Risk Reduction and Management Office (DRRMO) for providing official flood incident records from 2022 to 2025, which served as the foundation for model development and validation.
   The researchers also acknowledge the Department of Science and Technology – Philippine Atmospheric, Geophysical and Astronomical Services Administration (DOST-PAGASA) for providing climatological data from the Port Area, NAIA, and Science Garden weather stations.
   The Asian Institute of Computer Studies is recognized for providing the academic environment and resources necessary for this study. The researchers also thank their thesis advisers and panel members for their guidance, valuable feedback, and support throughout the research process.
   DECLARATIONS
   AI-Assisted Editing
   AI tools were used exclusively for editing and refining the original content for readability and grammatical accuracy. AI was not used to generate new content, alter original ideas, or fabricate data or citations.
   Conflict of Interest
   The authors declare no conflicts of interest.
   Informed Consent
   All data from the Parañaque City DRRMO and DOST-PAGASA were obtained through official channels with proper authorization. No personal or individual participant data were collected.
   Ethics Approval
   This study follows local and international ethical standards and was approved by the AICS Research Ethics Committee.

REFERENCES
LOCAL REFERENCES
Araza, A., & Alosnos, E. (2025). Advancing Earth Observation-based methods for rapid mapping and estimation of flood and drought impacts on rice production in the Philippines. International Journal of Disaster Risk Reduction, 105979. https://doi.org/10.1016/j.ijdrr.2025.105979
Bagtasa, G. (2022). Variability of tropical cyclone rainfall volume in the Philippines. International Journal of Climatology, 42(11), 6007–6017. https://doi.org/10.1002/joc.7573
Bankoff, G. (2003). Constructing vulnerability: The historical, natural and social generation of flooding in metropolitan Manila. Disasters, 27(3), 224–238. https://doi.org/10.1111/1467-7717.00230
Besarra, I., Opdyke, A., Mendoza, J. E., Delmendo, P. A., Santiago, J., Evangelista, D. J., & Lagmay, A. M. F. A. (2025). The cost of flooding on housing under climate change in the Philippines: Examining projected damage at the local scale. Journal of Environmental Management, 380, 124966. https://doi.org/10.1016/j.jenvman.2025.124966
de Veluz, M. R. D., Ong, A. K. S., Redi, A. A. N. P., Maaliw, R. R., Lagrazon, P. G., & Monetiro, C. N. (2025). Expanding integrated protection motivation theory and theory of planned behavior: The role of source of influence in flood and typhoon risk preparedness intentions in Quezon province, Philippines. Climate Risk Management, 48, 100706. https://doi.org/10.1016/j.crm.2025.100706
Garcia, F. C. C., Retamar, A. E., & Javier, J. C. (2015). A real-time urban flood monitoring system for Metro Manila. In TENCON 2015 – 2015 IEEE Region 10 Conference (pp. 1–5). IEEE. https://doi.org/10.1109/TENCON.2015.7372990
Onsay, E. A., Bulao, R. J. G., & Rabajante, J. F. (2025). Bagyong Kristine (TS Trami) in Bicol, Philippines: Flood risk forecasting, disaster risk preparedness predictions and lived experiences through machine learning (ML), econometrics, and hermeneutic analysis. Natural Hazards Research. https://doi.org/10.1016/j.nhres.2025.02.004
Pascual, L. A. C. A., Ong, A. K. S., Briggs, C. M., Diaz, J. F. T., & German, J. D. (2024). Factors affecting the intention to prepare for flash floods in the Philippines. International Journal of Disaster Risk Reduction, 112, 104794. https://doi.org/10.1016/j.ijdrr.2024.104794
Rivera, A. T., & Vega, J. B. G. D. (2025). From vulnerability to resilience: Addressing the causes, impacts, and solutions for recurrent flash floods in the Philippines. Tropical Cyclone Research and Review. https://doi.org/10.1016/j.tcrr.2025.08.005
Te, M. C. L., Bautista, J. A. T., Dimacali, S. M. E. V., Lood, A. V. M., Pangan, M. G. M., & Chua, A. Y. (2024). A smart IoT urban flood monitoring system using a high-performance pressure sensor with LoRaWAN. HighTech and Innovation Journal, 5(4), 918–936. https://doi.org/10.28991/HIJ-2024-05-04-04
REGIONAL REFERENCES
Askari, K., Zheng, W., Shi, S., Chu, J., & Wang, F. (2025). A novel entropy-based machine learning framework for flood risk mapping in Pakistan. Journal of Hydrology: Regional Studies, 62, 102911. https://doi.org/10.1016/j.ejrh.2025.102911
Bui, D. T., Tsangaratos, P., Ngo, P. T. T., Pham, T. D., & Pham, B. T. (2019). Flash flood susceptibility modeling using an optimized fuzzy rule based feature selection technique and tree based ensemble methods. Science of the Total Environment, 668, 1038–1054. https://doi.org/10.1016/j.scitotenv.2019.02.422
Huang, G., Ng, A. H. M., Zhou, Q., Zhu, Q., Du, Z., & Ge, L. (2026). Flood susceptibility prediction in the Indo-China Peninsula using 21 years of inundation occurrence data and machine learning. Journal of Hydrology, 135176. https://doi.org/10.1016/j.jhydrol.2026.135176
Ke, X., Wang, N., Li, T., Liu, Z., Li, Z., Zuo, G., & Chen, Y. (2025). From prediction to regionalization: Enhancing flash flood susceptibility mapping using machine learning and GeoDetector. Geoscience Frontiers, 102213. https://doi.org/10.1016/j.gsf.2025.102213
Krishnachaithanya, N., Sivakumar, P. B., & Deepika, T. (2025). Probabilistic flood risk mapping for Indian megacities using a scalable machine learning framework in Google Earth Engine. Results in Engineering, 107872. https://doi.org/10.1016/j.rineng.2025.107872
Lee, S. J., Cho, Y., Yang, R. Y., & Quan, S. J. (2026). From pixels to policy: Multi-scale flood susceptibility mapping using interpretable machine learning for urban resilience. Land Use Policy, 164, 107950. https://doi.org/10.1016/j.landusepol.2026.107950
Li, B., Guo, M., Jia, Y., Zeng, T., & Liu, X. (2026). Design of cloud platform alert monitoring and automatic analysis system based on random forest algorithm. Array, 100694. https://doi.org/10.1016/j.array.2026.100694
Li, S., Tang, Y., Zhao, Y., Ning, X., Zhang, Y., Lv, S., & Liu, C. (2025). Assessing future flood risk using remote sensing and explainable machine learning: A case study in the Beijing-Tianjin-Hebei region. Remote Sensing Applications: Society and Environment, 101742. https://doi.org/10.1016/j.rsase.2025.101742
Yao, X., Yang, L., Tan, J., Xie, Z., Gan, C., Wen, P., & Zhao, S. (2026). Bayesian-optimized BiLSTM-U-Net framework for urban flood prediction with spatio-temporal feature integration. Journal of Hydrology, 669, 135175. https://doi.org/10.1016/j.jhydrol.2026.135175
Yoganand, V., Rani, B. S., & Kattukota, N. (2026). A SHAP-integrated ILeNet transfer learning model for flood prediction in Telangana. Remote Sensing Applications: Society and Environment, 101943. https://doi.org/10.1016/j.rsase.2026.101943

INTERNATIONAL REFERENCES
Bennett, B., Leonard, M., Deng, Y., & Westra, S. (2018). An empirical investigation into the effect of antecedent precipitation on flood volume. Journal of Hydrology, 567, 435–445. https://doi.org/10.1016/j.jhydrol.2018.10.025
Breiman, L. (2001). Random forests. Machine Learning, 45(1), 5–32. https://doi.org/10.1023/A:1010933404324
Magoulick, P. (2026). Operational digital twin for multi-hazard coastal flood prediction with adaptive learning: Real-time performance in the Chesapeake Bay. Environmental Modelling & Software, 198, 106891. https://doi.org/10.1016/j.envsoft.2026.106891
Meng, M., Steinhardt, S., & Schubert, A. (2018). Application programming interface documentation: What do software developers want? Journal of Technical Writing and Communication, 48(3), 295–330. https://doi.org/10.1177/0047281617721853
Mishra, M., & Albano, R. (2026). FLOOD-DEPTH-ML: Machine learning-driven Python application for estimation of urban flood depths through submerged vehicles detection. Results in Engineering, 109495. https://doi.org/10.1016/j.rineng.2026.109495
Mosavi, A., Ozturk, P., & Chau, K. W. (2018). Flood prediction using machine learning models: Literature review. Water, 10(11), 1536. https://doi.org/10.3390/w10111536
Nguyen, M., Wilson, M. D., Lane, E. M., Brasington, J., & Pearson, R. A. (2025). Estimating uncertainty in flood model outputs using machine learning informed by Monte Carlo analysis. Journal of Hydrology, 133928. https://doi.org/10.1016/j.jhydrol.2025.133928
Tavakoli, M., Parizi, E., Kanani-Sadat, Y., Nikraftar, Z., & Delooei, A. H. (2026). An integrated framework for flood susceptibility assessment in rural areas using PSO-optimized machine learning and SHAP-based intelligent clustering. Environmental Impact Assessment Review, 120, 108414. https://doi.org/10.1016/j.eiar.2026.108414
Vojtek, M., Držík, D., Kapusta, J., & Vojteková, J. (2026). Transferability of machine/deep learning-based prediction of fluvial flood extent to distinct river sections in Slovakia based on benchmark flood maps and high-resolution spatial data. Journal of Hydrology: Regional Studies, 65, 103339. https://doi.org/10.1016/j.ejrh.2026.103339
Wang, Z., Lai, C., Chen, X., Yang, B., Zhao, S., & Bai, X. (2015). Flood hazard risk assessment model based on random forest. Journal of Hydrology, 527, 1130–1141. https://doi.org/10.1016/j.jhydrol.2015.06.008

 
VI. APPENDICES
Appendix A. Sample DRRMO Flood Record Data Structure
The official flood records from Parañaque City DRRMO contain the following standardized fields used as the primary training data source for the floodingnaque model.
Table A1. DRRMO Flood Record Field Definitions // Generate figure
Appendix B. Random Forest Model Configuration
The following Python code excerpt presents the core Random Forest classifier configuration used in the Floodingnaque production model (v6).
from sklearn.ensemble import RandomForestClassifier
model = RandomForestClassifier(
n_estimators=200, # Number of decision trees
max_depth=15, # Maximum tree depth
min_samples_split=5, # Minimum samples to split a node
min_samples_leaf=2, # Minimum samples at a leaf node
max_features='sqrt', # Features considered per split
class_weight='balanced_subsample', # Handle class imbalance
random_state=42, # Reproducibility
n_jobs=-1 # Utilize all CPU cores
)

Appendix C. Risk Classification Logic
def classify_risk_level(prediction, probability, precipitation, humidity):
if prediction == 1:
flood_prob = probability.get('flood', 0.5)
if flood_prob >= 0.75:
return 2 # Critical
elif flood_prob >= 0.50:
return 1 # Alert
else:
return 1 # Alert (conservative fallback)
else:
is_alert = False
if precipitation is not None and 7.5 <= precipitation <= 30.0:
is_alert = True # PAGASA Yellow/Orange warning range
if humidity is not None and humidity > 82.0 and precipitation > 5.0:
is_alert = True
if probability.get('flood', 0.0) >= 0.10 or is_alert:
return 1 # Alert
else:
return 0 # Safe

Appendix D. API Endpoint Reference
The Floodingnaque RESTful API exposes the following primary endpoints for flood prediction, data retrieval, and system monitoring.
Table D1. Primary API Endpoints // Generate figure
Appendix E. Barangay Flood Risk Classification
Table E1. Flood Risk Classification for 16 Barangays of Parañaque City // Generate figure
\*Based on historical flood frequency from DRRMO records (2022–2025). High: ≥4 documented flood events per year on average; Moderate: <4 documented flood events per year on average.
