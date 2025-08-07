@echo off
setlocal

echo ========================================
echo Browser-Use Web Agent - Starting Server
echo ========================================
echo.

cd /d "%~dp0\.."

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    echo Please run scripts\setup.bat first
    pause
    exit /b 1
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Check if required packages are installed
echo Checking dependencies...
python -c "import fastapi, playwright" >nul 2>&1
if errorlevel 1 (
    echo ERROR: Dependencies not installed properly!
    echo Please run scripts\setup.bat first
    pause
    exit /b 1
)

echo Dependencies OK
echo.

REM Start the server
echo Starting FastAPI server...
echo ----------------------------------------
echo ^> Server URL: http://127.0.0.1:8000
echo ^> API Docs: http://127.0.0.1:8000/docs
echo ^> Press Ctrl+C to stop
echo ----------------------------------------
echo.

uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload

echo.
echo Server stopped.
pause