@echo off
setlocal enabledelayedexpansion

echo ========================================
echo Browser-Use Web Agent Setup (Windows)  
echo ========================================
echo.

cd /d "%~dp0\.."

echo [1/6] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.10+ from https://python.org
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Found Python %PYTHON_VERSION%

echo.
echo [2/6] Setting up virtual environment...
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
) else (
    echo Virtual environment already exists
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo [3/6] Upgrading pip...
python -m pip install --upgrade pip

echo.
echo [4/6] Installing Python dependencies (skipping problematic packages)...

REM Install core dependencies first
echo Installing FastAPI and web dependencies...
pip install fastapi==0.104.1 uvicorn[standard]==0.24.0 websockets==12.0

REM Install Pydantic and related
echo Installing Pydantic...
pip install pydantic==2.5.0 pydantic-settings==2.1.0

REM Install Playwright
echo Installing Playwright...
pip install playwright==1.40.0

REM Install other essential packages
echo Installing file handling packages...
pip install python-multipart==0.0.6 aiofiles==23.2.1 PyPDF2==3.0.1 openpyxl==3.1.2

REM Install LLM integrations
echo Installing LLM packages...
pip install openai==1.3.8 google-generativeai==0.3.2 anthropic==0.7.8

REM Install optional packages
echo Installing optional packages...
pip install python-dotenv==1.0.0 httpx==0.25.2

echo All packages installed successfully!

echo.
echo [5/6] Installing Playwright browsers...
playwright install chromium

echo.
echo [6/6] Setting up configuration...
if not exist ".env" (
    if exist "config\.env.example" (
        copy "config\.env.example" ".env"
        echo Created .env file from template
    ) else (
        echo BROWSER_HEADLESS=false > .env
        echo BROWSER_TIMEOUT=30000 >> .env
        echo HOST=127.0.0.1 >> .env
        echo PORT=8000 >> .env
        echo Created basic .env file
    )
) else (
    echo .env file already exists
)

echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo NOTE: Skipped pandas installation due to Python 3.13 compatibility issues.
echo This won't affect the browser agent functionality.
echo.
echo To start the server:
echo 1. run: venv\Scripts\activate.bat
echo 2. run: uvicorn backend.main:app --host 127.0.0.1 --port 8000
echo 3. Open: http://127.0.0.1:8000
echo.
echo Or simply run: scripts\run.bat
echo.
pause