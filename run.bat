@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo 🐱 桌面宠物启动中...
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未找到 Python，请先安装 Python 3
    pause
    exit /b 1
)

REM Install dependencies if needed
python -c "import PyQt5" >nul 2>&1
if errorlevel 1 (
    echo 📦 正在安装依赖 (PyQt5 + openai)...
    python -m pip install PyQt5 openai
    echo.
)

REM Check config
if not exist "config.json" (
    echo {"api_key": "", "model": "deepseek-chat"} > config.json
    echo 📝 已创建 config.json，请先填入 API Key 后再启动
    start notepad config.json
    pause
    exit /b 0
)

echo 🚀 启动！
python main.py
pause
