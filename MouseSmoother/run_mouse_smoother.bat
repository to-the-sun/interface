@echo off
title Mouse Movement Smoother Launcher
cd /d "%~dp0"

echo ===================================================
echo   Mouse Movement Smoother Launcher
echo ===================================================
echo.

echo Checking Python installation...
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Python is not found in your system PATH!
    echo Please install Python 3.8+ from https://www.python.org/ and check "Add Python to PATH".
    echo.
    pause
    exit /b 1
)

echo.
echo Checking and installing dependencies...
python -m pip install -r "%~dp0requirements.txt"
echo.

echo Launching Mouse Movement Smoother...
python "%~dp0mouse_smoother.py"
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Application exited with error code %errorlevel%.
) else (
    echo.
    echo Application closed normally.
)

echo.
pause
exit /b 0
