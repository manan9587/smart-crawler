@echo off
echo Smart Crawler - AI-Powered Web Scraper
echo =====================================
echo.
echo Checking Python installation...
python --version
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

echo.
echo Installing/updating dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo Error: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo Installing Playwright browsers...
playwright install chromium
if errorlevel 1 (
    echo Warning: Failed to install Playwright browsers
    echo AI mode may not work properly
)

echo.
echo Starting Smart Crawler GUI...
python smart_crawler_gui.py

echo.
pause