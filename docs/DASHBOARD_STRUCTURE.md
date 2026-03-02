# Floodingnaque Dashboard Structure Specification

## Overview

This document describes the complete three-tier dashboard architecture for
Floodingnaque, an AI-powered flood early warning system for Paranaque City.
Each tier is tailored to its audience: residents receive situational awareness,
LGU/DRRMO operators receive decision-support tools, and system administrators
receive full platform control.

The system uses a Random Forest classification model trained on historical
weather and hydrological data. All dashboards share a common layout shell with
role-aware sidebar navigation.

---

## 1. Resident Dashboard (`user` role)

**Route:** `/dashboard`
**Component:** `ResidentDashboard.tsx`
**Purpose:** Provide residents with clear, actionable flood risk information
for their barangay.

### 1.1 Sections

| Section | Description |
|---------|-------------|
| **Flood Status Hero** | Full-width card showing the current risk level (LOW / MODERATE / HIGH) with color-coded background, location name, confidence percentage, and timestamp. |
| **Barangay Risk Map** | Interactive Leaflet map (two-thirds width) with polygon overlays for all 16 barangays, color-coded by risk level, with popup evacuation details. |
| **Alert Feed** | Real-time SSE-powered alert list in the sidebar showing recent system alerts with timestamps. |
| **Tidal Risk Indicator** | Speedometer gauge displaying current tidal height against the danger threshold. |
| **Emergency Info Panel** | Evacuation centers, emergency contacts, and dynamic risk-level advisories that change messaging based on current flood risk. |
| **Public Report Download** | Widget offering monthly flood reports (PDF) and weekly data summaries (CSV) for public download. |
| **Trend Charts** | Two-column grid showing Rainfall Trend (area chart) and Alert Frequency (bar chart) using Recharts. |

### 1.2 Data Sources

- `/api/v1/predict/location` -- flood risk prediction
- `/api/v1/sse/alerts` -- real-time alert stream
- `/api/v1/tides/current` -- tidal data
- `/api/v1/export/weather`, `/api/v1/export/predictions` -- report downloads

---

## 2. LGU / DRRMO Dashboard (`operator` role)

**Route:** `/dashboard`
**Component:** `LGUDashboard.tsx`
**Purpose:** Operational command center for local government flood response
teams.

### 2.1 Sections

| Section | Description |
|---------|-------------|
| **KPI Row** | Four stat cards: Current Risk Level, Active Alerts, Predictions Today, Average Confidence Score. |
| **Flood Status Hero** | Same as Resident but with extended metadata visible to operators. |
| **Forecast Panel** | 24-hour rainfall forecast with per-barangay breakdown and time-series chart. |
| **Feature Importance Chart** | Horizontal bar chart ranking the ML model features most influential in the current prediction. |
| **Live Analytics** | Three-column grid: Rainfall Trend, Risk Distribution (pie chart), and Alert Frequency (bar chart). |
| **Decision Support Engine** | Risk-level-aware action recommendation checklist. HIGH risk: 5 actionable steps (Early Warning, Evacuation Center activation, Official notification, Rescue deployment, NDRRMC coordination). MODERATE: 3 precautionary actions. LOW: status confirmation. Includes progress tracking with a completion bar. |
| **Tidal Risk Indicator** | Speedometer gauge with danger threshold line. |
| **SMS Simulation Panel** | Form to compose and preview simulated SMS alerts to selected barangays. |
| **AI Model Health** | Model summary cards showing version, accuracy, F1 score, and feature count from the inference engine. |
| **Barangay Risk Map** | Full-width interactive map with risk overlays. |

### 2.2 Data Sources

- All Resident data sources, plus:
- `/api/v1/dashboard/stats` -- aggregated KPIs
- `/api/v1/predictions/stats` -- prediction history
- `/api/v1/alerts/simulate-sms` -- SMS simulation
- `/api/v1/health` -- model metadata and performance metrics

---

## 3. Admin Dashboard (`admin` role)

**Route:** `/admin` and sub-routes
**Purpose:** Full platform administration, user management, data operations,
and model lifecycle control.

### 3.1 Admin Panel (Overview)

**Route:** `/admin`
**Component:** `admin/page.tsx`

| Section | Description |
|---------|-------------|
| **System Overview** | Four stat cards: Total Predictions, Active Alerts, API Response Time (with SLA badge), Average Risk Level. |
| **Infrastructure Status** | Three cards for Database (connection status, latency, pool size), Server Health (status, scheduler, Sentry), and Services (ML model, Redis, cache, model version). |
| **Model Performance Metrics** | Grid of current model accuracy scores (accuracy, precision, recall, F1, MAE, etc.) from the health endpoint. |
| **System Information** | Python version, model type, feature count, last health check, SLA threshold, current admin identity. |

### 3.2 User Management

**Route:** `/admin/users`
**Component:** `admin/users/page.tsx`

Full CRUD interface for managing registered accounts.

| Feature | Description |
|---------|-------------|
| **Search** | Real-time search by name or email. |
| **Filters** | Role filter (Admin, Operator, Resident) and status filter (Active, Suspended). |
| **User Table** | Paginated table with columns: Name, Email, Role (color-coded badge), Status badge, Last Login, and Actions dropdown. |
| **Actions** | Per-user dropdown: Change Role (cycle between admin/operator/user), Suspend/Reactivate Account, Reset Password, Delete User (with confirmation dialog). |
| **Pagination** | Previous/Next with page indicator. |

**API Endpoints:**

- `GET /api/v1/admin/users` -- list (paginated, filtered)
- `GET /api/v1/admin/users/:id` -- detail
- `PATCH /api/v1/admin/users/:id/role` -- role assignment
- `PATCH /api/v1/admin/users/:id/status` -- activate/suspend
- `POST /api/v1/admin/users/:id/reset-password` -- password reset
- `DELETE /api/v1/admin/users/:id` -- soft delete

### 3.3 Barangay Management

**Route:** `/admin/barangays`
**Component:** `admin/barangays/page.tsx`

Editable directory of all 16 Paranaque City barangays.

| Feature | Description |
|---------|-------------|
| **Risk Summary** | Three cards showing count of High, Moderate, and Low risk barangays. |
| **Search and Filter** | Name search and risk level filter. |
| **Barangay Table** | Columns: Name, Population, Flood Risk (editable dropdown), Evacuation Center (editable text), Coordinates, Edit/Save actions. |
| **Persistence** | Overrides stored in localStorage; defaults from `BARANGAYS` configuration. |

### 3.4 Dataset Management

**Route:** `/admin/data`
**Component:** `admin/data/page.tsx`

Upload, validate, and ingest weather observation data.

| Feature | Description |
|---------|-------------|
| **File Upload** | Accepts CSV and Excel (.xlsx/.xls) files with drag-and-click selection. |
| **Template Download** | One-click download of the expected CSV template. |
| **Validation** | Pre-upload validation with record count, error list, warning list, and data preview table. |
| **Upload** | Ingests validated data into the database with success/failure reporting. |
| **Data Export** | Quick-access buttons to export Weather Data, Predictions, and Alerts as CSV. |

**API Endpoints:**

- `POST /api/v1/upload/csv` -- CSV ingestion
- `POST /api/v1/upload/excel` -- Excel ingestion
- `POST /api/v1/upload/validate` -- pre-upload validation
- `GET /api/v1/upload/template` -- download template
- `GET /api/v1/export/weather`, `/predictions`, `/alerts` -- data export

### 3.5 AI Model Control

**Route:** `/admin/models`
**Component:** `admin/models/page.tsx`

ML model lifecycle management.

| Feature | Description |
|---------|-------------|
| **Status Cards** | Four cards: Load Status, Model Type, Version, Feature Count. |
| **Performance Metrics** | Grid of accuracy scores from the model metadata. |
| **Model Details** | Created date, file name, inference status badge. |
| **Retrain** | Button triggers Celery-based retraining via `/api/v1/admin/models/retrain`. Displays task ID for status tracking. |
| **Rollback** | Dialog to specify a version identifier and load a previous model file. |

**API Endpoints:**

- `GET /api/v1/admin/models` -- model metadata
- `POST /api/v1/admin/models/retrain` -- trigger retraining
- `GET /api/v1/admin/models/retrain/status?task_id=X` -- check status
- `POST /api/v1/admin/models/rollback` -- rollback to version
- `GET /api/v1/admin/models/comparison` -- version comparison

### 3.6 System Logs

**Route:** `/admin/logs`
**Component:** `admin/logs/page.tsx`

Real-time system activity log viewer.

| Feature | Description |
|---------|-------------|
| **Stats Row** | Five cards: Requests Today, Predictions, Logins, Uploads, Errors. |
| **Filters** | Endpoint search, category filter (Prediction, Login, Upload, Report, Health, Admin, Alert), and status filter (Success 2xx, Errors 4xx/5xx). |
| **Log Table** | Paginated table with columns: HTTP Method, Endpoint (monospace), Category (color-coded badge), Status Code (color-coded), Response Time, Timestamp. |
| **Pagination** | Previous/Next with page indicator. |

**API Endpoints:**

- `GET /api/v1/admin/logs` -- list (paginated, filtered by category/status/search)
- `GET /api/v1/admin/logs/stats` -- aggregate counts

### 3.7 System Configuration

**Route:** `/admin/config`
**Component:** `admin/config/page.tsx`

Feature flags and risk threshold management.

| Feature | Description |
|---------|-------------|
| **Feature Flags** | Toggle switches for: SSE Live Alerts, Tidal Monitoring, SMS Simulation, Model Versioning, CSV Export, Advanced Analytics, Decision Support Engine, Public Reports. Changes apply immediately via API. |
| **Risk Thresholds** | Numeric inputs for Low/Moderate/High risk boundaries (percentage) and Alert Cooldown (minutes). Validates ascending order before saving. |

**API Endpoints:**

- `GET /api/v1/feature-flags` -- list flags
- `PATCH /api/v1/feature-flags/:flag` -- toggle flag

---

## 4. Navigation Architecture

### 4.1 Sidebar Navigation Items

All roles see the Resident tier. Additional items are role-gated.

| Route | Icon | Label | Roles |
|-------|------|-------|-------|
| `/dashboard` | Home | Dashboard | all |
| `/map` | Map | Flood Map | all |
| `/predict` | Activity | Prediction | all |
| `/alerts` | Bell | Alerts | all |
| `/history` | Cloud | Weather History | operator, admin |
| `/analytics` | BarChart3 | Analytics | operator, admin |
| `/reports` | FileText | Reports | operator, admin |
| `/admin` | Shield | Admin | admin |
| `/admin/users` | Users | User Management | admin |
| `/admin/barangays` | MapPin | Barangays | admin |
| `/admin/data` | Database | Datasets | admin |
| `/admin/models` | Brain | AI Models | admin |
| `/admin/config` | SlidersHorizontal | Configuration | admin |
| `/settings` | Cog | System Settings | admin |
| `/admin/logs` | ScrollText | System Logs | admin |

### 4.2 Route Protection

All dashboard routes are wrapped in `ProtectedRoute` (requires authentication).
Admin routes additionally use `RequireRole role="admin"` for authorization.
All page routes use `RouteErrorBoundary` for graceful error handling.
Routes are code-split via `React.lazy` for performance.

---

## 5. Technology Stack

| Layer | Technology |
|-------|-----------|
| Frontend Framework | React 18 + TypeScript |
| Build Tool | Vite |
| Styling | Tailwind CSS v4 + shadcn/ui |
| State Management | Zustand |
| Data Fetching | TanStack Query (React Query) |
| Routing | React Router v6 |
| Charts | Recharts |
| Animations | Framer Motion |
| Maps | React Leaflet |
| Backend | Flask (Python 3.13) |
| ORM | SQLAlchemy |
| ML Model | Random Forest (scikit-learn) |
| Task Queue | Celery + Redis |
| Database | PostgreSQL (Supabase) |
| Auth | JWT (Bearer tokens, httpOnly cookies) |

---

## 6. API Endpoint Summary

All endpoints are prefixed with `/api/v1` unless noted otherwise.

### Public / Authenticated

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/login` | User authentication |
| POST | `/auth/register` | User registration |
| POST | `/auth/refresh` | Token refresh |
| GET | `/predict/location` | Flood risk prediction by coordinates |
| GET | `/data/data` | Weather observation data |
| GET | `/tides/current` | Current tidal data |
| GET | `/sse/alerts` | SSE alert stream |
| GET | `/dashboard/stats` | Dashboard KPIs |
| GET | `/predictions` | Prediction history |
| GET | `/export/weather` | Export weather CSV |
| GET | `/export/predictions` | Export predictions CSV |
| GET | `/export/alerts` | Export alerts CSV |
| GET | `/health` | System health check |

### Admin Only

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/admin/users` | List users (paginated) |
| PATCH | `/admin/users/:id/role` | Update user role |
| PATCH | `/admin/users/:id/status` | Activate/suspend user |
| POST | `/admin/users/:id/reset-password` | Reset user password |
| DELETE | `/admin/users/:id` | Soft-delete user |
| GET | `/admin/logs` | List system logs |
| GET | `/admin/logs/stats` | Log aggregate stats |
| GET | `/admin/models` | Model metadata |
| POST | `/admin/models/retrain` | Trigger retraining |
| GET | `/admin/models/retrain/status` | Check retraining status |
| POST | `/admin/models/rollback` | Rollback model version |
| GET | `/feature-flags` | List feature flags |
| PATCH | `/feature-flags/:flag` | Toggle feature flag |

---

## 7. Role Definitions

| Role | Label | Access Scope |
|------|-------|-------------|
| `user` | Resident | Dashboard, Map, Prediction, Alerts, Public Reports |
| `operator` | LGU / MDRRMO | All Resident features + Analytics, Reports, Weather History, Decision Support, SMS Simulation |
| `admin` | System Admin | All Operator features + Admin Panel, User Management, Barangay Management, Dataset Management, AI Model Control, System Logs, System Configuration |

---

*Document generated from the implemented codebase. All features described
are fully functional with corresponding frontend components, backend API
routes, and database models.*
