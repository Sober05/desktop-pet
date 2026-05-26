@echo off
cd /d "%~dp0"

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Python not found. Please install Python 3.
    pause
    exit /b 1
)

REM Install if needed
python -c "import PyQt5" >nul 2>&1
if errorlevel 1 (
    python -m pip install PyQt5 openai
)

REM Check config
if not exist "config.json" (
    copy config.example.json config.json >nul
)

REM Launch without console window
start "" pythonw main.py
