$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$Version = "3.2"
$AppName = "AstroClocks-v$Version"
$InstallerName = "Install_AstroClocks$Version.exe"

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

& $Python -m pip install -e ".[build]"
if ($LASTEXITCODE -ne 0) {
    throw "Dependency installation failed with exit code $LASTEXITCODE"
}

Remove-GeneratedPath (Join-Path $ProjectRoot "build\$AppName")
Remove-GeneratedPath (Join-Path $ProjectRoot "output\$AppName")

& $Python -m PyInstaller `
    --noconfirm `
    --onedir `
    --windowed `
    --name $AppName `
    --distpath "output" `
    --workpath "build" `
    --icon "AppIcon.ico" `
    --add-data "AppIcon.ico;." `
    --collect-all "astropy" `
    --collect-all "astroplan" `
    --collect-all "zeep" `
    --collect-all "tzdata" `
    ".\$AppName.py"
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller build failed with exit code $LASTEXITCODE"
}

Write-Host "Built output\$AppName\$AppName.exe"

$InnoCandidates = @()
if (${env:ProgramFiles(x86)}) {
    $InnoCandidates += Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"
}
if ($env:ProgramFiles) {
    $InnoCandidates += Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe"
}

$InnoCompiler = $InnoCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if ($InnoCompiler) {
    & $InnoCompiler ".\$AppName.iss"
    if ($LASTEXITCODE -ne 0) {
        throw "Inno Setup build failed with exit code $LASTEXITCODE"
    }
    Write-Host "Built installer\$InstallerName"
} else {
    Write-Warning "Inno Setup compiler not found. Install Inno Setup 6 to build the installer."
}
