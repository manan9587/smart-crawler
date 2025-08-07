#!/bin/bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
playwright install --with-deps chromium firefox webkit
cp config/.env.example config/.env
echo "Edit config/.env with your API keys"
