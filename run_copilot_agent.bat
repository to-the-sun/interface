@echo off
setlocal
cd /d "%~dp0"

echo Starting Jules GitHub Copilot Agent...
python -m GitHubCopilotAgent.cli --web

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo An error occurred while running Jules GitHub Copilot Agent.
    pause
)
