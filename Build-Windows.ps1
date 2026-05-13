$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

function Remove-GeneratedPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if (-not (Test-Path $Path)) {
        return
    }

    $resolvedProjectRoot = (Resolve-Path $ProjectRoot).Path
    $resolvedPath = (Resolve-Path $Path).Path
    if (-not $resolvedPath.StartsWith($resolvedProjectRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to remove generated path outside project: $resolvedPath"
    }

    Remove-Item -LiteralPath $resolvedPath -Recurse -Force
}

if (-not (Test-Path $Python)) {
    throw "Python virtual environment not found: $Python"
}

Set-Location $ProjectRoot

$Version = (& $Python -c "from astroclocks.version import APP_VERSION; print(APP_VERSION, end='')").Trim()
if (-not $Version) {
    throw "Unable to determine AstroClocks version from astroclocks.version"
}
$ExecutableStem = (& $Python -c "from astroclocks.version import APP_EXECUTABLE_STEM; print(APP_EXECUTABLE_STEM, end='')").Trim()
if (-not $ExecutableStem) {
    throw "Unable to determine AstroClocks executable stem from astroclocks.version"
}
$ExecutableName = "$ExecutableStem.exe"
$InstallerName = "Install_AstroClocks$Version.exe"

& $Python -m pip install -e ".[build]"
if ($LASTEXITCODE -ne 0) {
    throw "Dependency installation failed with exit code $LASTEXITCODE"
}

Remove-GeneratedPath (Join-Path $ProjectRoot "build\$ExecutableStem")
Remove-GeneratedPath (Join-Path $ProjectRoot "output\$ExecutableStem")

& $Python -m PyInstaller `
    --noconfirm `
    --onedir `
    --windowed `
    --name $ExecutableStem `
    --distpath "output" `
    --workpath "build" `
    --icon "AppIcon.ico" `
    --add-data "AppIcon.ico;." `
    --hidden-import "win32com" `
    --hidden-import "win32com.client" `
    --hidden-import "pythoncom" `
    --hidden-import "pywintypes" `
    --collect-submodules "win32com" `
    --collect-data "win32com" `
    --collect-all "astropy" `
    --collect-all "astroplan" `
    --collect-all "zeep" `
    --collect-all "tzdata" `
    ".\AstroClocks-v3.3.py"
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller build failed with exit code $LASTEXITCODE"
}

Write-Host "Built output\$ExecutableStem\$ExecutableName"

$InnoCandidates = @()
if (${env:ProgramFiles(x86)}) {
    $InnoCandidates += Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"
}
if ($env:ProgramFiles) {
    $InnoCandidates += Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe"
}

$InnoCompiler = $InnoCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if ($InnoCompiler) {
    & $InnoCompiler ".\AstroClocks-v3.3.iss"
    if ($LASTEXITCODE -ne 0) {
        throw "Inno Setup build failed with exit code $LASTEXITCODE"
    }
    Write-Host "Built installer\$InstallerName"
} else {
    Write-Warning "Inno Setup compiler not found. Install Inno Setup 6 to build the installer."
}
