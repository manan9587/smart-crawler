#!/bin/bash

echo "========================================"
echo "Browser-Use Web Agent Setup (Linux/Mac)"
echo "========================================"
echo

# Change to project root directory
cd "$(dirname "$0")/.."

echo "[1/6] Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 not found. Please install Python 3.10+ from https://python.org"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1)
echo "Found $PYTHON_VERSION"

echo
echo "[2/6] Setting up virtual environment..."
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
else
    echo "Virtual environment already exists"
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo
echo "[3/6] Upgrading pip..."
python -m pip install --upgrade pip

echo
echo "[4/6] Installing Python dependencies..."
pip install -r requirements.txt

echo
echo "[5/6] Installing Playwright browsers..."
playwright install chromium

echo
echo "[6/6] Setting up configuration..."
if [ ! -f ".env" ]; then
    if [ -f "config/.env.example" ]; then
        cp "config/.env.example" ".env"
        echo "Created .env file from template"
    else
        cat > .env << EOF
BROWSER_HEADLESS=false
BROWSER_TIMEOUT=30000
EOF
        echo "Created basic .env file"
    fi
else
    echo ".env file already exists"
fi

# Make run script executable
chmod +x scripts/run.sh

echo
echo "========================================"
echo "Setup Complete!"
echo "========================================"
echo
echo "To start the server:"
echo "1. source venv/bin/activate"
echo "2. uvicorn backend.main:app --host 127.0.0.1 --port 8000"
echo "3. Open: http://127.0.0.1:8000"
echo
echo "Or simply run: ./scripts/run.sh"
echo