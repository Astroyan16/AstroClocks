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

$InnoCandidates = @()
if (${env:ProgramFiles(x86)}) {
    $InnoCandidates += Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"
}
if ($env:ProgramFiles) {
    $InnoCandidates += Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe"
}

$InnoCompiler = $InnoCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if ($InnoCompiler) {
    & $InnoCompiler ".\AstroClocks-v3.0.iss"
    Write-Host "Built installer\Install_AstroClocks3.0.exe"
} else {
    Write-Warning "Inno Setup compiler not found. Install Inno Setup 6 to build the installer."
}
