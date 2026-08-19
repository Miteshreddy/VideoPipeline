@echo off
title DubFlow — Automated Video Dubbing System Launcher
color 0B

echo ================================================================
echo           DUBFLOW - AI VIDEO DUBBING SYSTEM LAUNCHER
echo ================================================================
echo.

cd /d "%~dp0"

:: 1. Check Python
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    color 0C
    echo [ERROR] Python is not found in system PATH.
    echo Please install Python 3.10+ from https://www.python.org/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

:: 2. Check Node.js
where npm >nul 2>nul
if %ERRORLEVEL% neq 0 (
    color 0C
    echo [ERROR] Node.js / npm is not found in system PATH.
    echo Please install Node.js 18+ from https://nodejs.org/
    pause
    exit /b 1
)

:: 3. Check FFmpeg
where ffmpeg >nul 2>nul
if %ERRORLEVEL% neq 0 (
    color 0E
    echo [WARNING] FFmpeg was not detected in system PATH.
    echo Dubbing requires FFmpeg for audio processing and video remixing.
    echo Please install FFmpeg (e.g., winget install Gyan.FFmpeg or from https://ffmpeg.org/)
    echo.
)

:: 4. Setup Backend Environment
echo [1/3] Setting up Python backend environment...
cd backend
if not exist "venv" (
    echo       Creating virtual environment in backend\venv...
    python -m venv venv
)

if not exist "venv\Scripts\python.exe" (
    echo       Recreating virtual environment...
    python -m venv venv
)

echo       Verifying Python dependencies...
call .\venv\Scripts\activate.bat
pip install -r requirements.txt --quiet

cd ..

:: 5. Setup Frontend Environment
echo [2/3] Setting up Frontend environment...
cd frontend
if not exist "node_modules" (
    echo       Installing npm packages...
    call npm install --silent
)
cd ..

:: 6. Launch Backend & Frontend
echo [3/3] Starting DubFlow Services...
echo.
echo   * Backend API:    http://127.0.0.1:8000
echo   * Health Check:   http://127.0.0.1:8000/api/health
echo   * Frontend Web:   http://localhost:5173
echo.
echo ================================================================
echo Press Ctrl+C in the service windows to stop DubFlow.
echo ================================================================
echo.

:: Start Backend in separate window
start "DubFlow Backend API (Port 8000)" cmd /k "cd /d "%~dp0backend" && call .\venv\Scripts\activate.bat && uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

:: Wait 2 seconds for backend initialization
timeout /t 2 /nobreak >nul

:: Start Frontend in separate window
start "DubFlow Frontend Dashboard (Port 5173)" cmd /k "cd /d "%~dp0frontend" && npm run dev"

:: Wait 2 seconds for frontend Vite server to bind
timeout /t 2 /nobreak >nul

:: Open Default Browser
start http://localhost:5173

echo DubFlow launched successfully! You can close this launcher window.
timeout /t 5 >nul
exit /b 0
