@echo off
title Audio Compressor Router Setup & Launcher
cd /d "%~dp0"

echo Checking Python installation and dependencies...
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python is not found in your system PATH!
    echo Please install Python 3.8+ from https://www.python.org/ and check "Add Python to PATH".
    pause
    exit /b 1
)

echo Installing / updating required dependencies (sounddevice, numpy)...
python -m pip install sounddevice numpy >nul 2>&1

echo Launching Audio Compressor application...
where pythonw >nul 2>nul
if %errorlevel% equ 0 (
    start "" pythonw "%~dp0audio_compressor.py"
) else (
    start "" python "%~dp0audio_compressor.py"
)

exit /b 0
