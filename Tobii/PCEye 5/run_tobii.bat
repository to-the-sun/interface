@echo off
cd /d "%~dp0"
echo Installing/Checking dependencies...
pip install tobii-research python-osc

echo.
echo Starting Tobii PCEye 5 OSC Streamer...
python tobii_osc.py

if %ERRORLEVEL% neq 0 (
    echo.
    echo script failed or was interrupted.
    pause
)
