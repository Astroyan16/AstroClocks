$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    throw "Python virtual environment not found: $Python"
}

Set-Location $ProjectRoot

$metadata = & $Python -c @"
from astroclocks.version import (
    APP_EXECUTABLE_NAME,
    APP_EXECUTABLE_STEM,
    APP_RELEASE_DATE,
    APP_VERSION,
    installer_name,
)
print(APP_VERSION)
print(APP_EXECUTABLE_STEM)
print(APP_EXECUTABLE_NAME)
print(APP_RELEASE_DATE.isoformat())
print(installer_name())
"@

if ($LASTEXITCODE -ne 0) {
    throw "Unable to load AstroClocks version metadata."
}

$metadataLines = @($metadata | Where-Object { $_ -ne "" })
if ($metadataLines.Count -lt 5) {
    throw "Incomplete AstroClocks version metadata."
}

$Version = $metadataLines[0].Trim()
$ExecutableStem = $metadataLines[1].Trim()
$ExecutableName = $metadataLines[2].Trim()
$ReleaseDate = $metadataLines[3].Trim()
$InstallerName = $metadataLines[4].Trim()
$InstallerBaseName = [System.IO.Path]::GetFileNameWithoutExtension($InstallerName)

$checks = @(
    @{
        Label = "pyproject version"
        Path = "pyproject.toml"
        Pattern = ('version = "{0}"' -f $Version)
    },
    @{
        Label = "Inno Setup version"
        Path = "AstroClocks-v3.3.iss"
        Pattern = ('#define MyAppVersion "{0}"' -f $Version)
    },
    @{
        Label = "Inno Setup executable"
        Path = "AstroClocks-v3.3.iss"
        Pattern = ('#define MyAppExeName "{0}"' -f $ExecutableName)
    },
    @{
        Label = "Inno Setup source dir"
        Path = "AstroClocks-v3.3.iss"
        Pattern = ('#define MyAppSourceDir "output\{0}"' -f $ExecutableStem)
    },
    @{
        Label = "Inno Setup installer output"
        Path = "AstroClocks-v3.3.iss"
        Pattern = ("OutputBaseFilename={0}" -f $InstallerBaseName)
    },
    @{
        Label = "README executable path"
        Path = "README.md"
        Pattern = ('`output/{0}/`' -f $ExecutableStem)
    },
    @{
        Label = "Changelog heading"
        Path = "CHANGELOG.md"
        Pattern = ("## AstroClocks v{0} stable - {1}" -f $Version, $ReleaseDate)
    }
)

$failures = New-Object System.Collections.Generic.List[string]

foreach ($check in $checks) {
    $content = Get-Content $check.Path -Raw
    if ($content -notmatch [regex]::Escape($check.Pattern)) {
        $failures.Add("Missing $($check.Label) in $($check.Path): $($check.Pattern)")
    }
}

$expectedPaths = @(
    (Join-Path $ProjectRoot "output\$ExecutableStem\$ExecutableName"),
    (Join-Path $ProjectRoot "installer\$InstallerName")
)

foreach ($path in $expectedPaths) {
    if (-not (Test-Path $path)) {
        $failures.Add("Missing expected artefact: $path")
    }
}

if ($failures.Count -gt 0) {
    Write-Host "AstroClocks release verification failed:" -ForegroundColor Red
    foreach ($failure in $failures) {
        Write-Host " - $failure" -ForegroundColor Red
    }
    exit 1
}

Write-Host "AstroClocks release verification OK" -ForegroundColor Green
Write-Host "Version      : $Version"
Write-Host "Executable   : output\$ExecutableStem\$ExecutableName"
Write-Host "Installer    : installer\$InstallerName"
Write-Host "Release date : $ReleaseDate"
