# Floodingnaque - Quick Start Guide

## Prerequisites

Before starting, ensure you have:
- ✅ Python 3.12+ installed
- ✅ Node.js 18+ and npm installed
- ✅ PostgreSQL database (or use SQLite for development)

## Step 1: Start the Backend Server

### Option A: Using the Virtual Environment (Recommended)

1. **Activate the virtual environment:**
   ```powershell
   # From the project root
   # From the project root
   .\venv\Scripts\Activate.ps1
   ```

2. **Navigate to the backend directory:**
   ```powershell
   cd backend
   ```

3. **Check if you have a .env file (if not, copy from .env.development):**
   ```powershell
   # If .env doesn't exist, create it
   if (!(Test-Path .env)) { Copy-Item .env.development .env }
   ```

4. **Start the backend server:**
   ```powershell
   python main.py
   ```

   The server should start on `http://localhost:5000`

### Option B: Using the PowerShell Script

```powershell
cd backend
.\start_server.ps1
```

### Verify Backend is Running

Open a browser and visit: `http://localhost:5000/api/v1/health`

You should see a JSON response indicating the server is healthy.

## Step 2: Start the Frontend Development Server

1. **Open a NEW terminal/PowerShell window**

2. **Navigate to the frontend directory:**
   ```powershell
   cd frontend
   ```

3. **Install dependencies (if not already done):**
   ```powershell
   npm install
   ```

4. **Start the development server:**
   ```powershell
   npm run dev
   ```

   The frontend should start on `http://localhost:3000`

### Access the Frontend

Open your browser and go to: `http://localhost:3000`

You should see the Floodingnaque login/register page.

## Step 3: Create an Admin Account

### Method 1: Using the Registration Form (Easiest)

1. Go to `http://localhost:3000`
2. Click on the **Register** tab
3. Fill in the registration form:
   - **Full Name**: Your name
   - **Email**: admin@floodingnaque.com (or any email)
   - **Password**: Choose a strong password
   - **Confirm Password**: Re-enter the password
4. Click **Register**

**Note:** The first user registered will need to be promoted to admin via the database or backend script.

### Method 2: Create Admin User via Backend Script

If you need to create an admin user directly:

1. **Open a terminal in the backend directory:**
   ```powershell
   cd backend
   .\venv\Scripts\Activate.ps1
   ```

2. **Create a Python script to add an admin user:**
   ```powershell
   # Create a temporary script
   @"
   import sys
   import os
   
   # Add current directory to path
   sys.path.append(os.getcwd())

   from app.models.db import get_db_session, User
   from app.core.security import hash_password

   def create_admin():
       print('Connecting to database...')
       try:
           with get_db_session() as db:
               # Check if admin exists
               existing = db.query(User).filter_by(email='admin@floodingnaque.com').first()
               if existing:
                   print('Admin user already exists!')
                   return
               
               print('Creating admin user...')
               # Create admin user
               admin = User(
                   email='admin@floodingnaque.com',
                   full_name='Admin User',
                   password_hash=hash_password('admin123'),
                   role='admin',
                   is_active=True,
                   is_verified=True
               )
               
               db.add(admin)
               print('Admin user created successfully!')
               print('Email: admin@floodingnaque.com')
               print('Password: admin123')
               print('Please change this password after first login!')
       except Exception as e:
           print(f'Error: {e}')

   if __name__ == '__main__':
       create_admin()
   "@ | Out-File -FilePath create_admin.py -Encoding utf8
   
   python create_admin.py
   ```

## Step 4: Login and Test

1. Go to `http://localhost:3000`
2. Click on the **Login** tab
3. Enter your credentials:
   - **Email**: admin@floodingnaque.com
   - **Password**: admin123 (or the password you set)
4. Click **Login**

You should be redirected to the dashboard!

## Troubleshooting

### Backend Won't Start

**Error: "Database connection failed"**
- Check your `.env` file in the `backend` directory
- For development, you can use SQLite: `DATABASE_URL=sqlite:///data/floodingnaque.db`
- Make sure the `data` directory exists: `mkdir data`

**Error: "Port 5000 already in use"**
- Check what's using port 5000: `Get-Process -Id (Get-NetTCPConnection -LocalPort 5000).OwningProcess`
- Kill the process or change the port in `.env`: `PORT=5001`

### Frontend Won't Start

**Error: "Port 3000 already in use"**
- The frontend will automatically try the next available port (3001, 3002, etc.)
- Or kill the process using port 3000

**Error: "Cannot connect to backend"**
- Make sure the backend is running on port 5000
- Check the frontend `.env.development` file: `VITE_API_BASE_URL=http://localhost:5000`

### Registration Fails

**Error: "Network error"**
- ✅ Verify backend is running: `http://localhost:5000/api/v1/health`
- ✅ Check browser console for detailed error messages (F12 → Console tab)
- ✅ Verify CORS is configured correctly in backend `.env`: `CORS_ORIGINS=http://localhost:3000`

**Error: "Email already exists"**
- This email is already registered
- Try a different email or login with existing credentials

## Quick Commands Reference

### Backend
```powershell
# Start backend
cd backend
.\venv\Scripts\Activate.ps1
python main.py

# Check backend health
curl http://localhost:5000/api/v1/health
```

### Frontend
```powershell
# Start frontend
cd frontend
npm run dev

# Build for production
npm run build
```

## Next Steps

Once you're logged in:
1. 🌊 **Test Predictions**: Go to `/predict` to test flood predictions
2. 🔔 **View Alerts**: Check `/alerts` for flood alerts
3. 📊 **Dashboard**: View statistics and analytics
4. ⚙️ **Settings**: Configure your profile and preferences
5. 👥 **Admin Panel**: Access `/admin` to manage users (admin only)

## Environment Configuration

### Backend (.env)
Key settings in `backend/.env`:
- `PORT=5000` - Backend server port
- `DATABASE_URL` - Database connection string
- `CORS_ORIGINS=http://localhost:3000` - Allow frontend requests
- `AUTH_BYPASS_ENABLED=False` - Set to True for testing without auth

### Frontend (.env.development)
Key settings in `frontend/.env.development`:
- `VITE_API_BASE_URL=http://localhost:5000` - Backend API URL
- `VITE_APP_NAME=Floodingnaque` - Application name

## Support

If you encounter any issues:
1. Check the backend logs in `backend/logs/`
2. Check the browser console (F12 → Console)
3. Verify both servers are running
4. Ensure environment variables are set correctly
