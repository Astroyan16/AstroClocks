$ErrorActionPreference = "Continue"

$repoApiUrl = "https://api.github.com/repos/Astroyan16/AstroClocks/releases"
$downloadUrl = "https://github.com/Astroyan16/AstroClocks/releases/latest"
$referenceTimeUrl = "https://api.github.com/"
$scriptDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$reportPath = Join-Path $scriptDirectory ("AstroClocks-Update-Diagnostic-{0}.txt" -f $timestamp)

$script:ReportLines = New-Object System.Collections.Generic.List[string]

function Write-Section($title) {
    Write-Host ""
    Write-Host "=== $title ===" -ForegroundColor Cyan
    $script:ReportLines.Add("")
    $script:ReportLines.Add("=== $title ===")
}

function Write-Result($label, $value) {
    $line = "{0,-28} {1}" -f $label, $value
    Write-Host $line
    $script:ReportLines.Add($line)
}

function Show-ExceptionDetails($prefix, $ex) {
    Write-Host "$prefix $($ex.GetType().FullName)" -ForegroundColor Yellow
    $script:ReportLines.Add("$prefix $($ex.GetType().FullName)")
    if ($ex.Message) {
        Write-Host "Message: $($ex.Message)" -ForegroundColor Yellow
        $script:ReportLines.Add("Message: $($ex.Message)")
    }
    if ($ex.InnerException) {
        Write-Host "Inner:   $($ex.InnerException.GetType().FullName)" -ForegroundColor DarkYellow
        Write-Host "         $($ex.InnerException.Message)" -ForegroundColor DarkYellow
        $script:ReportLines.Add("Inner:   $($ex.InnerException.GetType().FullName)")
        $script:ReportLines.Add("         $($ex.InnerException.Message)")
    }
}

function Write-PlainLine($text = "") {
    Write-Host $text
    $script:ReportLines.Add($text)
}

Write-Host "Diagnostic connectivite mise a jour AstroClocks" -ForegroundColor Green
Write-Host "Date locale: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz')"
$script:ReportLines.Add("Diagnostic connectivite mise a jour AstroClocks")
$script:ReportLines.Add("Date locale: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz')")
$script:ReportLines.Add("Rapport: $reportPath")

Write-Section "Systeme"
Write-Result "Nom machine" $env:COMPUTERNAME
Write-Result "Utilisateur" $env:USERNAME
Write-Result "Windows" ([System.Environment]::OSVersion.VersionString)
Write-Result "PowerShell" $PSVersionTable.PSVersion

Write-Section "Proxy WinHTTP"
try {
    $proxyOutput = netsh winhttp show proxy
    $proxyOutput | ForEach-Object { Write-PlainLine $_ }
} catch {
    Show-ExceptionDetails "Echec lecture proxy:" $_.Exception
}

Write-Section "DNS api.github.com"
try {
    Resolve-DnsName api.github.com -ErrorAction Stop |
        Select-Object Name, Type, IPAddress |
        Format-Table -AutoSize
} catch {
    Show-ExceptionDetails "Resolve-DnsName a echoue:" $_.Exception
    try {
        nslookup api.github.com
    } catch {
        Show-ExceptionDetails "nslookup a echoue:" $_.Exception
    }
}

Write-Section "Test HTTPS GitHub API via Invoke-WebRequest"
try {
    $response = Invoke-WebRequest -Uri $repoApiUrl -UseBasicParsing -TimeoutSec 20 -Headers @{
        "Accept" = "application/vnd.github+json"
        "User-Agent" = "AstroClocks-Updater-Diagnostic"
        "X-GitHub-Api-Version" = "2022-11-28"
    }
    Write-Result "StatusCode" $response.StatusCode
    Write-Result "ContentLength" ($response.Content.Length)
    $rateLimit = $response.Headers["X-RateLimit-Remaining"]
    if ($rateLimit) {
        Write-Result "RateLimit remaining" $rateLimit
    }
    $snippet = $response.Content
    if ($snippet.Length -gt 300) {
        $snippet = $snippet.Substring(0, 300) + "..."
    }
    Write-PlainLine "Apercu contenu:"
    Write-PlainLine $snippet
} catch {
    Show-ExceptionDetails "Invoke-WebRequest a echoue:" $_.Exception
}

Write-Section "Test HTTPS GitHub API via curl.exe"
try {
    $curlOutput = & curl.exe -I --max-time 20 $repoApiUrl 2>&1
    $curlOutput | ForEach-Object { Write-PlainLine $_ }
} catch {
    Show-ExceptionDetails "curl.exe a echoue:" $_.Exception
}

Write-Section "Test page release GitHub classique"
try {
    $releasePage = Invoke-WebRequest -Uri $downloadUrl -UseBasicParsing -TimeoutSec 20
    Write-Result "StatusCode" $releasePage.StatusCode
    Write-Result "FinalUri" $releasePage.BaseResponse.ResponseUri.AbsoluteUri
} catch {
    Show-ExceptionDetails "Page release GitHub a echoue:" $_.Exception
}

Write-Section "Horloge"
Write-Result "Date/heure locale" (Get-Date)
Write-Result "Date/heure UTC" ((Get-Date).ToUniversalTime().ToString("yyyy-MM-dd HH:mm:ss 'UTC'"))
try {
    $tz = Get-TimeZone
    Write-Result "Fuseau" $tz.Id
} catch {
    Show-ExceptionDetails "Lecture fuseau a echoue:" $_.Exception
}

try {
    $referenceResponse = Invoke-WebRequest -Uri $referenceTimeUrl -Method Head -UseBasicParsing -TimeoutSec 20 -Headers @{
        "User-Agent" = "AstroClocks-Updater-Diagnostic"
    }
    $referenceDateHeader = $referenceResponse.Headers["Date"]
    if ($referenceDateHeader) {
        $referenceUtc = [DateTimeOffset]::Parse($referenceDateHeader).ToUniversalTime()
        $localUtc = [DateTimeOffset]::UtcNow
        $delta = $localUtc - $referenceUtc
        Write-Result "Reference serveur UTC" $referenceUtc.ToString("yyyy-MM-dd HH:mm:ss 'UTC'")
        Write-Result "Ecart local-reference" ("{0:N1} secondes" -f $delta.TotalSeconds)
    }
    else {
        Write-Host "Reference serveur UTC: entete Date absente" -ForegroundColor Yellow
    }
} catch {
    Show-ExceptionDetails "Lecture heure de reference a echoue:" $_.Exception
}

Write-Host ""
Write-Host "Fin du diagnostic." -ForegroundColor Green
$script:ReportLines.Add("")
$script:ReportLines.Add("Fin du diagnostic.")

try {
    [System.IO.File]::WriteAllLines($reportPath, $script:ReportLines)
    Write-Host "Rapport enregistre: $reportPath" -ForegroundColor Green
} catch {
    Show-ExceptionDetails "Ecriture du rapport a echoue:" $_.Exception
}

Write-Host ""
Read-Host "Appuyez sur Entree pour fermer"
