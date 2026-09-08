@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

set "ENV_DIR=%~dp0py310_env"
set "PYTHON_EXE=%ENV_DIR%\Scripts\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=%ENV_DIR%\python.exe"

if exist "%PYTHON_EXE%" goto :run_env

echo ========================================================================
echo Setting up isolated Python 3.10 environment for Tobii PCEye 5...
echo ========================================================================
echo.

:: Option A: Try to create venv using existing Python 3.10 launcher
py -3.10 -c "import sys" >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo Creating virtual environment using system Python 3.10...
    py -3.10 -m venv "%ENV_DIR%"
    set "PYTHON_EXE=%ENV_DIR%\Scripts\python.exe"
    if exist "%PYTHON_EXE%" goto :install_deps
)

:: Option B: Try to create venv using existing Python 3.8 launcher
py -3.8 -c "import sys" >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo Creating virtual environment using system Python 3.8...
    py -3.8 -m venv "%ENV_DIR%"
    set "PYTHON_EXE=%ENV_DIR%\Scripts\python.exe"
    if exist "%PYTHON_EXE%" goto :install_deps
)

:: Option C: Try using active 'python' if it is Python 3.10 or 3.8
python -c "import sys; sys.exit(0 if sys.version_info[:2] in [(3,10),(3,8)] else 1)" >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo Creating virtual environment using active Python...
    python -m venv "%ENV_DIR%"
    set "PYTHON_EXE=%ENV_DIR%\Scripts\python.exe"
    if exist "%PYTHON_EXE%" goto :install_deps
)

:: Option D: Download and extract official standalone portable Python 3.10 package
echo System Python 3.10 not detected. Downloading portable Python 3.10 embeddable package...
set "ZIP_PATH=%TEMP%\python-3.10.11-embed-amd64.zip"
set "GET_PIP_PATH=%TEMP%\get-pip.py"

powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Write-Host 'Downloading Python 3.10.11 zip...'; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.10.11/python-3.10.11-embed-amd64.zip' -OutFile '%ZIP_PATH%'"
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to download portable Python 3.10 package.
    pause
    exit /b 1
)

echo Extracting portable Python 3.10 package to %ENV_DIR%...
powershell -Command "Expand-Archive -Path '%ZIP_PATH%' -DestinationPath '%ENV_DIR%' -Force"
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to extract Python 3.10 package.
    pause
    exit /b 1
)

:: Enable site-packages in python310._pth
if exist "%ENV_DIR%\python310._pth" (
    powershell -Command "(Get-Content '%ENV_DIR%\python310._pth') -replace '#import site', 'import site' | Set-Content '%ENV_DIR%\python310._pth'"
)

echo Downloading get-pip.py...
powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://bootstrap.pypa.gov/get-pip.py' -OutFile '%GET_PIP_PATH%'"
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to download get-pip.py.
    pause
    exit /b 1
)

echo Installing pip into portable Python 3.10...
"%ENV_DIR%\python.exe" "%GET_PIP_PATH%" --no-warn-script-location
set "PYTHON_EXE=%ENV_DIR%\python.exe"

:install_deps
if not exist "%PYTHON_EXE%" (
    echo ERROR: Failed to initialize Python 3.10 environment.
    pause
    exit /b 1
)

echo.
echo Installing/Checking dependencies in isolated Python 3.10 environment...
"%PYTHON_EXE%" -m pip install -r "%~dp0requirements.txt"

if %ERRORLEVEL% neq 0 (
    echo.
    echo ERROR: Failed to install required dependencies.
    pause
    exit /b 1
)

:run_env
echo.
echo Starting Tobii PCEye 5 OSC Streamer (Python 3.10 environment)...
"%PYTHON_EXE%" "%~dp0tobii_osc.py" %*

if %ERRORLEVEL% neq 0 (
    echo.
    echo Script failed or was interrupted.
    pause
)
