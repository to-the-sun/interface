@echo off
title Video Downloader Launcher
cd /d "%~dp0"

echo Checking Python installation...
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python is not found in your system PATH!
    echo Please install Python 3.8+ from https://www.python.org/ and ensure "Add Python to PATH" is checked.
    pause
    exit /b 1
)

echo Checking and installing required dependencies (yt-dlp)...
python -m pip install -r requirements.txt >nul 2>&1

echo Launching Video Downloader...
where pythonw >nul 2>nul
if %errorlevel% equ 0 (
    start "" pythonw "%~dp0video_downloader.py"
) else (
    start "" python "%~dp0video_downloader.py"
)

exit /b 0
