@echo off
setlocal

echo ========================================
echo Restarting Browser-Use Web Agent
echo ========================================
echo.

cd /d "%~dp0\.."

REM Clean up any existing processes
taskkill /f /im python.exe 2>nul
taskkill /f /im uvicorn.exe 2>nul

echo Cleaned up any running processes.
echo.

REM Activate virtual environment
if not exist "venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    echo Please run scripts\setup.bat first
    pause
    exit /b 1
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo Installing any missing packages...
pip install --no-deps fastapi uvicorn websockets playwright pydantic pydantic-settings > nul 2>&1

echo.
echo Starting server with clean slate...
echo ----------------------------------------
echo ^> Server URL: http://127.0.0.1:8000
echo ^> Press Ctrl+C to stop
echo ----------------------------------------
echo.

uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload

echo.
echo Server stopped.
pause