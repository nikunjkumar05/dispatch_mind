@echo off
echo ========================================
echo   DispatchMind v2.0 — Startup Script
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.8+
    pause
    exit /b 1
)

REM Check if Node.js is available
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js not found. Please install Node.js 18+
    pause
    exit /b 1
)

REM Install backend dependencies
echo [1/4] Installing backend dependencies...
pip install fastapi uvicorn >nul 2>&1

REM Install frontend dependencies
echo [2/4] Installing frontend dependencies...
cd frontend
call npm install >nul 2>&1
cd ..

REM Start backend
echo [3/4] Starting backend API on port 8000...
start "DispatchMind Backend" cmd /k "python -m uvicorn backend.api:app --reload --port 8000"

REM Wait for backend to start
timeout /t 5 /nobreak >nul

REM Start frontend
echo [4/4] Starting frontend on port 3000...
cd frontend
start "DispatchMind Frontend" cmd /k "npm run dev"
cd ..

echo.
echo ========================================
echo   DispatchMind is running!
echo ========================================
echo   Backend:  http://localhost:8000
echo   Frontend: http://localhost:3000
echo ========================================
echo.
pause
