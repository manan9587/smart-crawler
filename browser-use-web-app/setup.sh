#!/bin/bash
echo "🚀 Browser-Use Web App Setup"
if ! command -v python3 &> /dev/null; then
echo "❌ Install Python 3.11+ first"; exit 1
fi
python3 -m venv browser_use_env
source browser_use_env/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
playwright install chromium --with-deps
mkdir -p static templates uploads charts
cat > .env <<EOL
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
GOOGLE_API_KEY=your_google_api_key_here
BROWSER_USE_LOGGING_LEVEL=info
PLAYWRIGHT_BROWSERS_PATH=0
HOST=127.0.0.1
PORT=8000
DEBUG=true
MAX_FILE_SIZE=10485760
UPLOAD_DIRECTORY=uploads
EOL
echo "✅ Setup complete. Activate venv and run python fastapi_backend.py"