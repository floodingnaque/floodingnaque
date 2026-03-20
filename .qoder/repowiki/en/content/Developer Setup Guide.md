# Developer Setup Guide

<cite>
**Referenced Files in This Document**  
- [main.py](file://backend/main.py)
- [requirements.txt](file://backend/requirements.txt)
- [.env.example](file://backend/.env.example)
- [db.py](file://backend/app/models/db.py)
- [config.py](file://backend/app/core/config.py)
- [download.ps1](file://download.ps1)
- [DATABASE_SETUP.md](file://backend/docs/DATABASE_SETUP.md)
- [SETUP_COMPLETE.md](file://backend/docs/SETUP_COMPLETE.md)
- [POWERSHELL_API_EXAMPLES.md](file://backend/docs/POWERSHELL_API_EXAMPLES.md)
</cite>

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Clone the Repository](#clone-the-repository)
3. [Set Up Python Environment](#set-up-python-environment)
4. [Install Dependencies](#install-dependencies)
5. [Configure Environment Variables](#configure-environment-variables)
6. [Database Setup](#database-setup)
7. [Run the Application](#run-the-application)
8. [Verify Installation](#verify-installation)
9. [Automated Setup with PowerShell](#automated-setup-with-powershell)
10. [Troubleshooting](#troubleshooting)

## Prerequisites

Before setting up the floodingnaque project, ensure your system meets these requirements:

- **Python 3.8 or higher**: The application is built using Python and requires a compatible version.
- **pip**: Python's package installer, used to install project dependencies.
- **virtualenv** (recommended): For creating isolated Python environments to avoid dependency conflicts.
- **Git**: For cloning the repository from version control.
- **PowerShell 5.1+ or Windows Terminal** (Windows users): For running the automated setup script.

To verify your Python installation:
```bash
python --version
pip --version
```

**Section sources**
- [requirements.txt](file://backend/requirements.txt)

## Clone the Repository

Start by cloning the floodingnaque repository to your local machine:

```bash
git clone https://github.com/your-organization/floodingnaque.git
cd floodingnaque
```

This creates a local copy of the project with the following key directories:
- `backend/`: Main application code, configuration, and models
- `frontend/`: User interface components (if applicable)
- `docs/`: Project documentation

**Section sources**
- [README.md](file://backend/README.md)

## Set Up Python Environment

It's recommended to use a virtual environment to isolate project dependencies:

```bash
# Navigate to the backend directory
cd backend

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

You should see `(venv)` in your command prompt, indicating the virtual environment is active.

**Section sources**
- [requirements.txt](file://backend/requirements.txt)

## Install Dependencies

Install all required Python packages using pip and the provided requirements.txt file:

```bash
pip install -r requirements.txt
```

This installs essential packages including:
- **Flask**: Web framework for the API
- **Flask-CORS**: Enables cross-origin resource sharing
- **SQLAlchemy**: Database ORM
- **python-dotenv**: Environment variable management
- **scikit-learn**: Machine learning library
- **pandas, numpy**: Data processing libraries
- **gunicorn**: Production WSGI server

The installation may take a few minutes depending on your internet connection.

**Section sources**
- [requirements.txt](file://backend/requirements.txt)

## Configure Environment Variables

Create a `.env` file in the `backend/` directory by copying the example:

```bash
# On Windows
copy .env.example .env
# On macOS/Linux
cp .env.example .env
```

Edit the `.env` file with your preferred text editor and update the values:

```env
***REMOVED*** (required for data ingestion)
OWM_API_KEY=your_openweathermap_api_key_here

# Meteostat API Key (optional for additional weather data)
METEOSTAT_API_KEY=your_meteostat_api_key_here

# Database configuration (SQLite by default)
DATABASE_URL=sqlite:///floodingnaque.db

# Server configuration
PORT=5000
HOST=0.0.0.0
FLASK_DEBUG=False
```

**API Key Registration**:
- **OpenWeatherMap**: Sign up at [openweathermap.org](https://openweathermap.org/api) for a free API key
- **Meteostat**: Register at [meteostat.net](https://meteostat.net/en/) for historical weather data access

**Section sources**
- [.env.example](file://backend/.env.example)
- [config.py](file://backend/app/core/config.py)

## Database Setup

The application supports both SQLite (default) and PostgreSQL database options.

### Option 1: SQLite (Default)

SQLite requires no additional setup. When you run the application:
- The database file `floodingnaque.db` will be created automatically in the `backend/` directory
- Tables will be initialized on first run

### Option 2: PostgreSQL

For production use, PostgreSQL is recommended. First, update your `.env` file:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/floodingnaque
```

Then set up PostgreSQL:
1. Install PostgreSQL (version 13 or higher)
2. Create the database:
```bash
createdb floodingnaque
```
3. Or use Docker with the provided docker-compose.yml:
```bash
docker-compose up -d db
```

The application will automatically create the required tables when started.

### Manual Database Initialization

To manually initialize the database schema:
```bash
python -c "from app.models.db import init_db; init_db()"
```

Verify the database setup:
```bash
python scripts/inspect_db.py
```

Expected output:
```
Tables: [('weather_data',)]
Columns in weather_data: [(0, 'id', 'INTEGER', 0, None, 1), ...]
Records in weather_data: 0
```

```mermaid
flowchart TD
Start([Start Setup]) --> ChooseDB["Choose Database Type"]
ChooseDB --> |SQLite| SetupSQLite["No setup needed<br/>File created automatically"]
ChooseDB --> |PostgreSQL| SetupPostgreSQL["Install PostgreSQL<br/>Create database<br/>Update DATABASE_URL"]
SetupSQLite --> Initialize["Initialize Database"]
SetupPostgreSQL --> Initialize
Initialize --> CreateTables["Create tables using init_db()"]
CreateTables --> Verify["Verify with inspect_db.py"]
Verify --> Complete([Setup Complete])
```

**Diagram sources**
- [db.py](file://backend/app/models/db.py)
- [DATABASE_SETUP.md](file://backend/docs/DATABASE_SETUP.md)

**Section sources**
- [db.py](file://backend/app/models/db.py)
- [DATABASE_SETUP.md](file://backend/docs/DATABASE_SETUP.md)

## Run the Application

Once all setup is complete, start the application:

```bash
# Ensure you're in the backend directory
cd backend

# Activate virtual environment if not already active
venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux

# Start the development server
python main.py
```

Expected output:
```
Starting Floodingnaque API on 0.0.0.0:5000 (debug=False)
 * Running on http://0.0.0.0:5000 (Press CTRL+C to quit)
```

The server will be accessible at `http://localhost:5000`.

**For production deployment**, use gunicorn:
```bash
gunicorn --bind 0.0.0.0:5000 --workers 4 --threads 2 --timeout 120 main:app
```

**Section sources**
- [main.py](file://backend/main.py)
- [README.md](file://backend/README.md)

## Verify Installation

After starting the server, verify everything is working correctly through these health checks:

### 1. Basic Status Check
```bash
curl http://localhost:5000/status
```
Expected response:
```json
{
  "status": "running",
  "database": "connected",
  "model": "not found"
}
```

### 2. Detailed Health Check
```bash
curl http://localhost:5000/health
```
Expected response:
```json
{
  "status": "healthy",
  "database": "connected",
  "model_available": false,
  "scheduler_running": false
}
```

### 3. Test API Endpoints
```bash
# Get API information
curl http://localhost:5000/

# View API documentation
curl http://localhost:5000/api/docs
```

### 4. Database Verification
Run the inspection script to confirm database connectivity:
```bash
python scripts/inspect_db.py
```

If all checks pass, your local environment is properly configured.

**Section sources**
- [SETUP_COMPLETE.md](file://backend/docs/SETUP_COMPLETE.md)

## Automated Setup with PowerShell

The project includes a PowerShell script (`download.ps1`) to automate the setup process on Windows systems.

### Running the PowerShell Script

1. Open PowerShell as Administrator
2. Navigate to the project root directory
3. Run the setup script:

```powershell
.\download.ps1
```

### Script Capabilities

The PowerShell script automates:
- Python and pip verification
- Virtual environment creation
- Dependency installation
- Environment file configuration
- Database initialization
- Service status verification

### PowerShell API Testing

Once the server is running, you can test API endpoints using PowerShell:

```powershell
# Health check
Invoke-RestMethod -Uri "http://localhost:5000/health" -Method GET

# Predict flood risk
$body = @{
    temperature = 298.15
    humidity = 90.0
    precipitation = 50.0
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:5000/predict" -Method POST -ContentType "application/json" -Body $body
```

Refer to `backend/docs/POWERSHELL_API_EXAMPLES.md` for more PowerShell examples and troubleshooting tips.

```mermaid
sequenceDiagram
participant User
participant PowerShell
participant API
participant Database
User->>PowerShell : Run download.ps1
PowerShell->>PowerShell : Verify Python/pip
PowerShell->>PowerShell : Create virtual environment
PowerShell->>PowerShell : Install dependencies
PowerShell->>PowerShell : Configure .env file
PowerShell->>API : Start Flask server
API->>Database : Initialize tables
Database-->>API : Confirmation
API-->>PowerShell : Server running
PowerShell-->>User : Setup complete
```

**Diagram sources**
- [download.ps1](file://download.ps1)
- [main.py](file://backend/main.py)
- [db.py](file://backend/app/models/db.py)

**Section sources**
- [download.ps1](file://download.ps1)
- [POWERSHELL_API_EXAMPLES.md](file://backend/docs/POWERSHELL_API_EXAMPLES.md)

## Troubleshooting

### Common Issues and Solutions

#### Port Already in Use
**Error**: `OSError: [Errno 98] Address already in use`
**Solution**: Change the PORT in your `.env` file or stop the conflicting process:
```bash
# Find process using port 5000
netstat -ano | findstr :5000
# Kill the process (replace PID)
taskkill /PID <PID> /F
```

#### Missing Dependencies
**Error**: `ModuleNotFoundError: No module named 'flask'`
**Solution**: Ensure your virtual environment is activated and reinstall dependencies:
```bash
venv\Scripts\activate
pip install -r requirements.txt
```

#### API Key Configuration
**Issue**: `/ingest` endpoint returns authentication errors
**Solution**: Verify your API keys in `.env`:
- OWM_API_KEY is required
- Keys should not have quotes or spaces
- Restart the server after updating `.env`

#### Database Connection Issues
**SQLite**: Ensure the `backend/` directory has write permissions
**PostgreSQL**: Verify the database server is running and credentials are correct

#### PowerShell Script Execution Policy
**Error**: "File cannot be loaded because running scripts is disabled"
**Solution**: Change execution policy:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Verification Checklist
- [ ] Python and pip are installed and accessible
- [ ] Virtual environment is created and activated
- [ ] requirements.txt dependencies are installed
- [ ] .env file is configured with valid API keys
- [ ] Database is initialized and accessible
- [ ] Server starts without errors on http://localhost:5000
- [ ] Health check endpoints return successful responses

**Section sources**
- [SETUP_COMPLETE.md](file://backend/docs/SETUP_COMPLETE.md)
- [DATABASE_SETUP.md](file://backend/docs/DATABASE_SETUP.md)
- [POWERSHELL_API_EXAMPLES.md](file://backend/docs/POWERSHELL_API_EXAMPLES.md)
