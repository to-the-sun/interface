@echo off
title Tobii 4C OSC Streamer Launcher
cd /d "%~dp0"

set "ENV_DIR=%~dp0env_32"

rem Check if local 32-bit environment already exists and is complete
if exist "%ENV_DIR%\python.exe" (
    echo Launching Tobii 4C OSC Streamer via local 32-bit Python environment...
    "%ENV_DIR%\python.exe" "%~dp0tobii_4c_osc.py"
    if %errorlevel% equ 0 goto :END
)

rem Try 32-bit Python via launcher first if installed on system
where py >nul 2>nul
if %errorlevel% equ 0 (
    py -3-32 -c "import sys" >nul 2>&1
    if %errorlevel% equ 0 (
        echo Found system Python 32-bit via launcher!
        echo Installing / verifying required dependencies...
        py -3-32 -m pip install -r requirements.txt
        echo.
        echo Launching Tobii 4C OSC Streamer with system 32-bit Python...
        py -3-32 "%~dp0tobii_4c_osc.py"
        if %errorlevel% equ 0 goto :END
    )
)

rem Check if standard system Python can load the script without 32-bit architecture mismatch error
where python >nul 2>nul
if %errorlevel% equ 0 (
    echo Testing system Python...
    python -c "import ctypes; sys_bit=ctypes.sizeof(ctypes.c_void_p)*8; exit(0 if sys_bit==32 else 1)" >nul 2>&1
    if %errorlevel% equ 0 (
        echo System Python is 32-bit. Installing dependencies and launching...
        python -m pip install -r requirements.txt
        python "%~dp0tobii_4c_osc.py"
        if %errorlevel% equ 0 goto :END
    )
)

echo.
echo ========================================================================
echo Notice: 32-bit Tobii Stream Engine DLL requires a 32-bit Python runtime.
echo Creating local 32-bit Python environment in folder: env_32 ...
echo ========================================================================
echo.

if not exist "%ENV_DIR%" mkdir "%ENV_DIR%"

set "PY_ZIP=%ENV_DIR%\python-3.10.11-embed-win32.zip"
set "GET_PIP=%ENV_DIR%\get-pip.py"
set "PY_URL=https://www.python.org/ftp/python/3.10.11/python-3.10.11-embed-win32.zip"
set "PIP_URL=https://bootstrap.pypa.io/get-pip.py"

if not exist "%ENV_DIR%\python.exe" (
    echo Downloading 32-bit Python 3.10 embeddable runtime...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%PY_URL%' -OutFile '%PY_ZIP%'"
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to download 32-bit Python package.
        pause
        exit /b 1
    )

    echo Extracting 32-bit Python package...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -LiteralPath '%PY_ZIP%' -DestinationPath '%ENV_DIR%' -Force"
    del "%PY_ZIP%" 2>nul

    rem Uncomment 'import site' in python310._pth to enable site-packages / pip
    if exist "%ENV_DIR%\python310._pth" (
        powershell -NoProfile -ExecutionPolicy Bypass -Command "(Get-Content -LiteralPath '%ENV_DIR%\python310._pth') -replace '#import site', 'import site' | Set-Content -LiteralPath '%ENV_DIR%\python310._pth'"
    )
)

if not exist "%ENV_DIR%\Scripts\pip.exe" (
    echo Downloading get-pip.py...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%PIP_URL%' -OutFile '%GET_PIP%'"

    echo Installing pip into 32-bit Python environment...
    "%ENV_DIR%\python.exe" "%GET_PIP%" --no-warn-script-location
    del "%GET_PIP%" 2>nul
)

echo Installing dependencies into local 32-bit Python environment...
"%ENV_DIR%\python.exe" -m pip install -r requirements.txt --no-warn-script-location

echo.
echo Launching Tobii 4C OSC Streamer via local 32-bit Python environment...
"%ENV_DIR%\python.exe" "%~dp0tobii_4c_osc.py"

:END
if %errorlevel% neq 0 (
    echo.
    echo [NOTICE] Script exited with code %errorlevel%.
    pause
)
