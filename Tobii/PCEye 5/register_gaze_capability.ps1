# PowerShell script to register AppxManifest.xml for gazeInput capability
$ErrorActionPreference = "Continue"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$manifestPath = Join-Path $scriptDir "AppxManifest.xml"

if (-not (Test-Path -LiteralPath $manifestPath)) {
    $srcManifest = Join-Path $scriptDir "Package.appxmanifest"
    if (Test-Path -LiteralPath $srcManifest) {
        Copy-Item -LiteralPath $srcManifest -Destination $manifestPath -Force
    }
}

if (-not (Test-Path -LiteralPath $manifestPath)) {
    Write-Host "AppxManifest.xml not found at: $manifestPath" -ForegroundColor Red
    exit 1
}

Write-Host "Registering app package manifest with gazeInput capability..." -ForegroundColor Green
try {
    Add-AppxPackage -Register -LiteralPath $manifestPath -DisableDevelopmentMode
    Write-Host "App package registered successfully with gazeInput capability." -ForegroundColor Green
} catch {
    Write-Host "Notice during package registration: $_" -ForegroundColor Yellow
}
