@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

set "ENV_DIR=%~dp0env"
set "PYTHON_EXE=%ENV_DIR%\Scripts\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=%ENV_DIR%\python.exe"

if exist "%PYTHON_EXE%" goto :install_deps

:: Check if py launcher or system python is available
where python >nul 2>&1
if %ERRORLEVEL% equ 0 (
    set "SYS_PYTHON=python"
    goto :create_venv
)

where py >nul 2>&1
if %ERRORLEVEL% equ 0 (
    set "SYS_PYTHON=py"
    goto :create_venv
)

echo ERROR: Python is not installed or not found in PATH.
echo Please install Python 64-bit (Python 3.8, 3.10, 3.12, etc.) from python.org or the Microsoft Store.
pause
exit /b 1

:create_venv
echo ========================================================================
echo Setting up Python environment for Tobii PCEye 5 (Windows Gaze API)...
echo ========================================================================
echo.
"%SYS_PYTHON%" -m venv "%ENV_DIR%"
set "PYTHON_EXE=%ENV_DIR%\Scripts\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=%ENV_DIR%\python.exe"

:install_deps
if not exist "%PYTHON_EXE%" (
    echo ERROR: Failed to initialize Python environment.
    pause
    exit /b 1
)

echo.
echo Installing/Checking dependencies in Python environment...
"%PYTHON_EXE%" -m pip install -r "%~dp0requirements.txt"

if %ERRORLEVEL% neq 0 (
    echo.
    echo ERROR: Failed to install required dependencies.
    pause
    exit /b 1
)

:run_env
echo.
echo Starting Tobii PCEye 5 OSC Streamer (Windows Gaze Input API)...
"%PYTHON_EXE%" "%~dp0tobii_osc.py" %*

if %ERRORLEVEL% neq 0 (
    echo.
    echo Script failed or was interrupted.
    pause
)
