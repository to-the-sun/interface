@echo off
title Tobii 4C OSC Streamer Launcher
cd /d "%~dp0"

echo Searching for Python installation...

rem Try 32-bit Python via launcher first if 32-bit DLL is present
where py >nul 2>nul
if %errorlevel% equ 0 (
    echo Checking Python Launcher (py -3-32)...
    py -3-32 -c "import sys" >nul 2>&1
    if %errorlevel% equ 0 (
        echo Found Python 32-bit via launcher!
        echo Installing / verifying required dependencies...
        py -3-32 -m pip install -r requirements.txt
        echo.
        echo Launching Tobii 4C OSC Streamer with 32-bit Python...
        py -3-32 "%~dp0tobii_4c_osc.py"
        goto :END
    )
)

rem Fallback to default system Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python was not found in your system PATH or Launcher!
    echo Please install Python 3.8+ from https://www.python.org/ and check "Add Python to PATH".
    pause
    exit /b 1
)

echo Installing / verifying required dependencies (python-osc, opencv-python, numpy)...
python -m pip install -r requirements.txt

echo.
echo Launching Tobii 4C OSC Streamer...
python "%~dp0tobii_4c_osc.py"

:END
if %errorlevel% neq 0 (
    echo.
    echo [NOTICE] Script exited with error code %errorlevel%.
    pause
)
