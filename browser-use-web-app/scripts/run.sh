#!/bin/bash

echo "========================================"
echo "Browser-Use Web Agent - Starting Server"
echo "========================================"
echo

# Change to project root directory
cd "$(dirname "$0")/.."

# Check if virtual environment exists
if [ ! -f "venv/bin/activate" ]; then
    echo "ERROR: Virtual environment not found!"
    echo "Please run ./scripts/setup.sh first"
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Check if required packages are installed
echo "Checking dependencies..."
if ! python -c "import fastapi, playwright" 2>/dev/null; then
    echo "ERROR: Dependencies not installed properly!"
    echo "Please run ./scripts/setup.sh first"
    exit 1
fi

echo "Dependencies OK"
echo

# Start the server
echo "Starting FastAPI server..."
echo "----------------------------------------"
echo "> Server URL: http://127.0.0.1:8000"
echo "> API Docs: http://127.0.0.1:8000/docs"
echo "> Press Ctrl+C to stop"
echo "----------------------------------------"
echo

uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload

echo
echo "Server stopped."