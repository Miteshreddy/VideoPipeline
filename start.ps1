# DubFlow Automated Video Dubbing System — PowerShell Launcher

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "          DUBFLOW - AI VIDEO DUBBING SYSTEM LAUNCHER           " -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# 1. Check Python
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] Python is not found in system PATH." -ForegroundColor Red
    Write-Host "Please install Python 3.10+ from https://www.python.org/ and check 'Add Python to PATH'."
    Read-Host "Press Enter to exit..."
    exit 1
}

# 2. Check Node.js
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] Node.js / npm is not found in system PATH." -ForegroundColor Red
    Write-Host "Please install Node.js 18+ from https://nodejs.org/"
    Read-Host "Press Enter to exit..."
    exit 1
}

# 3. Check FFmpeg
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Write-Host "[WARNING] FFmpeg was not detected in system PATH." -ForegroundColor Yellow
    Write-Host "Dubbing requires FFmpeg for audio processing and video remixing."
    Write-Host "Install FFmpeg with: winget install Gyan.FFmpeg" -ForegroundColor Yellow
    Write-Host ""
}

# 4. Backend setup
Write-Host "[1/3] Setting up Python backend environment..." -ForegroundColor Green
$BackendDir = Join-Path $ScriptDir "backend"
$VenvDir = Join-Path $BackendDir "venv"

if (-not (Test-Path $VenvDir)) {
    Write-Host "      Creating virtual environment in backend\venv..." -ForegroundColor Gray
    python -m venv $VenvDir
}

$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$VenvPip = Join-Path $VenvDir "Scripts\pip.exe"
$VenvUvicorn = Join-Path $VenvDir "Scripts\uvicorn.exe"

Write-Host "      Verifying Python dependencies..." -ForegroundColor Gray
& $VenvPip install -r (Join-Path $BackendDir "requirements.txt") --quiet

# 5. Frontend setup
Write-Host "[2/3] Setting up Frontend environment..." -ForegroundColor Green
$FrontendDir = Join-Path $ScriptDir "frontend"
$NodeModules = Join-Path $FrontendDir "node_modules"

if (-not (Test-Path $NodeModules)) {
    Write-Host "      Installing npm packages..." -ForegroundColor Gray
    Push-Location $FrontendDir
    npm install --silent
    Pop-Location
}

# 6. Launch Services
Write-Host "[3/3] Starting DubFlow Services..." -ForegroundColor Green
Write-Host ""
Write-Host "  * Backend API:    http://127.0.0.1:8000" -ForegroundColor White
Write-Host "  * Health Check:   http://127.0.0.1:8000/api/health" -ForegroundColor White
Write-Host "  * Frontend Web:   http://localhost:5173" -ForegroundColor White
Write-Host ""

# Start Backend in background terminal
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$BackendDir'; & '$VenvUvicorn' app.main:app --host 127.0.0.1 --port 8000 --reload"

Start-Sleep -Seconds 2

# Start Frontend in background terminal
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$FrontendDir'; npm run dev"

Start-Sleep -Seconds 2

# Open default browser
Start-Process "http://localhost:5173"

Write-Host "DubFlow launched successfully!" -ForegroundColor Cyan
Write-Host "You can close this launcher window." -ForegroundColor Gray
Start-Sleep -Seconds 3
