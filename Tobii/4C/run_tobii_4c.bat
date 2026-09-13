@echo off
title Tobii 4C OSC Streamer Launcher
cd /d "%~dp0"

echo Checking Python installation...
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python was not found in your system PATH!
    echo Please install Python 3.8+ from https://www.python.org/ and check "Add Python to PATH".
    pause
    exit /b 1
)

echo Installing / verifying required dependencies (python-osc, opencv-python, numpy)...
python -m pip install -r requirements.txt

echo.
echo Launching Tobii 4C OSC Streamer...
python "%~dp0tobii_4c_osc.py"

if %errorlevel% neq 0 (
    echo.
    echo [NOTICE] Script exited with error code %errorlevel%.
    pause
)
