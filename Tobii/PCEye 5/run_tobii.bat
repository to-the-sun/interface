@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ========================================================================
echo  Tobii PCEye 5 - Windows Gaze Input API Launcher
echo ========================================================================
echo.

:: Register sparse package manifest with gazeInput capability if powershell is available
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0register_gaze_capability.ps1" >nul 2>&1

:: Check if dotnet CLI is installed for C# execution
where dotnet >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo [.NET SDK Detected] Building and running C# Gaze Input API application...
    dotnet run -c Release -- %*
    if %ERRORLEVEL% equ 0 goto :end
    echo.
    echo C# build failed or exited. Falling back to Python environment...
    echo.
)

:: Python execution path
set "ENV_DIR=%~dp0env"
set "PYTHON_EXE=%ENV_DIR%\Scripts\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=%ENV_DIR%\python.exe"

if exist "%PYTHON_EXE%" goto :install_deps

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

echo ERROR: Neither .NET SDK nor Python was found on PATH.
echo Please install .NET 8 SDK or Python 64-bit to run the Windows Gaze API application.
pause
exit /b 1

:create_venv
echo Setting up Python environment for Tobii PCEye 5 (Windows Gaze API)...
"%SYS_PYTHON%" -m venv "%ENV_DIR%"
set "PYTHON_EXE=%ENV_DIR%\Scripts\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=%ENV_DIR%\python.exe"

:install_deps
if not exist "%PYTHON_EXE%" (
    echo ERROR: Failed to initialize Python environment.
    pause
    exit /b 1
)

echo Installing/Checking dependencies in Python environment...
"%PYTHON_EXE%" -m pip install -r "%~dp0requirements.txt"

if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to install required dependencies.
    pause
    exit /b 1
)

:run_env
echo Starting Tobii PCEye 5 Python OSC Streamer (Windows Gaze Input API)...
"%PYTHON_EXE%" "%~dp0tobii_osc.py" %*

:end
if %ERRORLEVEL% neq 0 (
    echo.
    echo Application exited with error.
    pause
)
