@echo off
REM career-ops Streamlit dashboard launcher
REM First run: installs Python deps into a local venv, then starts the app.

setlocal
cd /d "%~dp0"

set VENV=dashboard-web\.venv
set PY=%VENV%\Scripts\python.exe

if not exist "%PY%" (
    echo Creating virtualenv at %VENV% ...
    python -m venv "%VENV%"
    if errorlevel 1 (
        echo Failed to create venv. Is Python on PATH?
        exit /b 1
    )
    "%PY%" -m pip install --upgrade pip
    "%PY%" -m pip install -r dashboard-web\requirements.txt
)

echo Launching career-ops dashboard at http://localhost:8765 ...
"%PY%" -m streamlit run dashboard-web\app.py
