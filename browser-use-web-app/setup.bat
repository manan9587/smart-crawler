@echo off
echo 🚀 Browser-Use Web App Setup (Windows)
python -m venv browser_use_env
call browser_use_env\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
playwright install chromium --with-deps
mkdir static templates uploads charts
> .env (
  echo OPENAI_API_KEY=your_openai_api_key_here
  echo ANTHROPIC_API_KEY=your_anthropic_api_key_here
  echo GOOGLE_API_KEY=your_google_api_key_here
  echo BROWSER_USE_LOGGING_LEVEL=info
  echo PLAYWRIGHT_BROWSERS_PATH=0
  echo HOST=127.0.0.1
  echo PORT=8000
  echo DEBUG=true
  echo MAX_FILE_SIZE=10485760
  echo UPLOAD_DIRECTORY=uploads
)
echo ✅ Setup complete. Run python fastapi_backend.py
pause