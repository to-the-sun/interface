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
set "ZIP_URL=https://www.python.org/ftp/python/3.10.11/python-3.10.11-embed-amd64.zip"

curl.exe -sSL "%ZIP_URL%" -o "%ZIP_PATH%" 2>nul
if not exist "%ZIP_PATH%" (
    powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri $env:ZIP_URL -OutFile $env:ZIP_PATH"
)

if not exist "%ZIP_PATH%" (
    echo ERROR: Failed to download portable Python 3.10 package.
    pause
    exit /b 1
)

echo Extracting portable Python 3.10 package to %ENV_DIR%...
powershell -Command "Expand-Archive -LiteralPath $env:ZIP_PATH -DestinationPath $env:ENV_DIR -Force"
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to extract Python 3.10 package.
    pause
    exit /b 1
)

:: Enable site-packages in python310._pth
if exist "%ENV_DIR%\python310._pth" (
    powershell -Command "$pth = Join-Path $env:ENV_DIR 'python310._pth'; if (Test-Path -LiteralPath $pth) { (Get-Content -LiteralPath $pth) -replace '#import site', 'import site' | Set-Content -LiteralPath $pth }"
)

echo Downloading get-pip.py...
set "PIP_DOWNLOADED=0"

curl.exe -sSL "https://bootstrap.pypa.gov/get-pip.py" -o "%GET_PIP_PATH%" 2>nul
if exist "%GET_PIP_PATH%" set "PIP_DOWNLOADED=1"

if "!PIP_DOWNLOADED!"=="0" (
    curl.exe -sSL "https://raw.githubusercontent.com/pypa/get-pip/main/public/get-pip.py" -o "%GET_PIP_PATH%" 2>nul
    if exist "%GET_PIP_PATH%" set "PIP_DOWNLOADED=1"
)

if "!PIP_DOWNLOADED!"=="0" (
    powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; try { Invoke-WebRequest -Uri 'https://bootstrap.pypa.gov/get-pip.py' -OutFile $env:GET_PIP_PATH } catch { try { Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/pypa/get-pip/main/public/get-pip.py' -OutFile $env:GET_PIP_PATH } catch { Invoke-WebRequest -Uri 'https://pip.pypa.io/get-pip.py' -OutFile $env:GET_PIP_PATH } }"
    if exist "%GET_PIP_PATH%" set "PIP_DOWNLOADED=1"
)

if "!PIP_DOWNLOADED!"=="0" (
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
