Browser-Use Web App — Windows Setup Guide
Prerequisites
Windows 10 or later

Python 3.11+ installed and on your PATH

Git (for cloning the repository)

1. Clone the Repository
Open PowerShell and run:

powershell
git clone <repo_url>
cd browser-use-web-app
2. Create & Activate Virtual Environment
powershell
python -m venv venv
.\venv\Scripts\activate.ps1
If you see an execution policy error, run:

powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
Then retry activating.

3. Install Dependencies
powershell
pip install --upgrade pip
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
4. Install Playwright Browsers
powershell
playwright install --with-deps chromium firefox webkit
5. Configure Environment
Copy example environment file and add your API keys:

powershell
copy config\.env.example config\.env
notepad config\.env
In config\.env, set:

text
OPENAI_API_KEY=sk-your-openai-key
GOOGLE_API_KEY=your-google-key
ANTHROPIC_API_KEY=your-anthropic-key
6. Run the Application
powershell
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
You should see:

text
INFO: Uvicorn running on http://127.0.0.1:8000
7. Open in Browser
Navigate to:

text
http://127.0.0.1:8000
Features
OpenAI & Google Gemini & Anthropic support

Real-time browser view & activity logs

Pause / Resume / Stop agent controls

PDF / TXT / CSV file upload for context

Export extracted results as CSV or JSON

Enjoy automating your workflows with the agent!