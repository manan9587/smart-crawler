python -m venv venv
call venv\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt
playwright install --with-deps chromium firefox webkit
copy config\.env.example config\.env
echo Edit config\.env with your API keys
pause
