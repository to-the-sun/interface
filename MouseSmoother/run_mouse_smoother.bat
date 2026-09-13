@echo off
title Mouse Movement Smoother Launcher
cd /d "%~dp0"

echo Checking Python installation...
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python is not found in your system PATH!
    echo Please install Python 3.8+ from https://www.python.org/ and check "Add Python to PATH".
    pause
    exit /b 1
)

echo Checking and updating dependencies...
python -m pip install -r "%~dp0requirements.txt" >nul 2>&1

echo Launching Mouse Movement Smoother...
where pythonw >nul 2>nul
if %errorlevel% equ 0 (
    start "" pythonw "%~dp0mouse_smoother.py"
) else (
    python "%~dp0mouse_smoother.py"
    if %errorlevel% neq 0 (
        echo.
        echo [ERROR] Mouse Smoother exited with error code %errorlevel%.
        pause
    )
)

exit /b 0
