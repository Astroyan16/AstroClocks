$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    throw "Python virtual environment not found: $Python"
}

Set-Location $ProjectRoot

& $Python -m pip install -e ".[build]"

& $Python -m PyInstaller `
    --noconfirm `
    --clean `
    --onedir `
    --windowed `
    --name "AstroClocks-v3.0" `
    --distpath "output" `
    --workpath "build" `
    --icon "AppIcon.ico" `
    --add-data "AppIcon.ico;." `
    --collect-all "astropy" `
    --collect-all "astroplan" `
    --collect-all "zeep" `
    --collect-all "tzdata" `
    ".\AstroClocks-v3.0.py"

Write-Host "Built output\AstroClocks-v3.0\AstroClocks-v3.0.exe"
