param(
    [switch]$Rollback
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

$BackupRoot = Join-Path $ProjectRoot ".deployment-backups"
$LatestFile = Join-Path $BackupRoot "LATEST.txt"

function Step($Message) {
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Fail($Message) {
    Write-Host ""
    Write-Host "ERROR: $Message" -ForegroundColor Red
    exit 1
}

function Restore-Backup($BackupDir) {
    Step "Restoring backup: $BackupDir"

    $manifest = Join-Path $BackupDir "manifest.txt"
    if (-not (Test-Path $manifest)) {
        Fail "Backup manifest missing: $manifest"
    }

    foreach ($entry in Get-Content $manifest) {
        if ([string]::IsNullOrWhiteSpace($entry)) { continue }

        $parts = $entry -split '\|', 2
        $state = $parts[0]
        $name = $parts[1]

        $target = Join-Path $ProjectRoot $name
        $backup = Join-Path $BackupDir $name

        if ($state -eq "EXISTED") {
            Copy-Item $backup $target -Force
            Write-Host "Restored $name"
        }
        elseif ($state -eq "ABSENT") {
            if (Test-Path $target) {
                Remove-Item $target -Force
                Write-Host "Removed patch-created $name"
            }
        }
    }

    Write-Host ""
    Write-Host "Rollback complete." -ForegroundColor Green
}

if ($Rollback) {
    if (-not (Test-Path $LatestFile)) {
        Fail "No deployment backup metadata was found."
    }

    $BackupDir = (Get-Content $LatestFile -Raw).Trim()

    if (-not (Test-Path $BackupDir)) {
        Fail "Backup directory does not exist: $BackupDir"
    }

    Restore-Backup $BackupDir
    exit 0
}

foreach ($required in @("app.py", "config.py", "requirements.txt")) {
    if (-not (Test-Path $required)) {
        Fail "$required was not found. Run this script from the tableau-admin-dashboard project root."
    }
}

Step "Creating rollback backup"

New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$BackupDir = Join-Path $BackupRoot $stamp
New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null

$ManagedFiles = @(
    "app.py",
    "config.py",
    ".gitignore"
)

$manifestLines = @()

foreach ($name in $ManagedFiles) {
    $path = Join-Path $ProjectRoot $name

    if (Test-Path $path) {
        Copy-Item $path (Join-Path $BackupDir $name) -Force
        $manifestLines += "EXISTED|$name"
    }
    else {
        $manifestLines += "ABSENT|$name"
    }
}

Set-Content (Join-Path $BackupDir "manifest.txt") $manifestLines -Encoding UTF8
Set-Content $LatestFile $BackupDir -Encoding UTF8

Write-Host "Backup created:"
Write-Host "  $BackupDir"
Write-Host ""
Write-Host "Rollback command:"
Write-Host "  .\deployment-readiness-patch-v2.ps1 -Rollback" -ForegroundColor Yellow

try {
    Step "Patching config.py"

    $configPath = Join-Path $ProjectRoot "config.py"
    $config = Get-Content $configPath -Raw

    # ------------------------------------------------------------
    # Persistent runtime directory
    # ------------------------------------------------------------
    if ($config -notmatch '(?m)^APP_DATA_DIR\s*=') {
        $pattern = '(?m)^INSTANCE_DIR\s*=\s*os\.path\.join\(BASE_DIR,\s*"instance"\)\s*$'
        $replacement = @'
APP_DATA_DIR = os.path.abspath(
    os.environ.get("APP_DATA_DIR", os.path.join(BASE_DIR, "instance"))
)
INSTANCE_DIR = APP_DATA_DIR
'@

        $newConfig = [regex]::Replace($config, $pattern, $replacement.TrimEnd(), 1)

        if ($newConfig -eq $config) {
            throw "Could not locate the INSTANCE_DIR assignment in config.py."
        }

        $config = $newConfig
        Write-Host "[OK] Added APP_DATA_DIR support"
    }
    else {
        Write-Host "[OK] APP_DATA_DIR support already present"
    }

    # ------------------------------------------------------------
    # Settings overrides
    # ------------------------------------------------------------
    $replacements = @(
        @{
            Pattern = '(?m)^(\s*)self\.server_url\s*=\s*data\["server_url"\]\.rstrip\("/"\)\s*$'
            Replacement = '$1self.server_url = os.environ.get("TABLEAU_SERVER_URL", data["server_url"]).rstrip("/")'
            Label = "TABLEAU_SERVER_URL"
        },
        @{
            Pattern = '(?m)^(\s*)self\.host\s*=\s*data\.get\("host",\s*"127\.0\.0\.1"\)\s*$'
            Replacement = '$1self.host = os.environ.get("APP_HOST", data.get("host", "127.0.0.1"))'
            Label = "APP_HOST"
        },
        @{
            Pattern = '(?m)^(\s*)self\.port\s*=\s*int\(data\.get\("port",\s*5000\)\)\s*$'
            Replacement = '$1self.port = int(os.environ.get("APP_PORT", data.get("port", 5000)))'
            Label = "APP_PORT"
        },
        @{
            Pattern = '(?m)^(\s*)self\.refresh_interval_minutes\s*=\s*int\(data\.get\("refresh_interval_minutes",\s*60\)\)\s*$'
            Replacement = '$1self.refresh_interval_minutes = int(os.environ.get("REFRESH_INTERVAL_MINUTES", data.get("refresh_interval_minutes", 60)))'
            Label = "REFRESH_INTERVAL_MINUTES"
        },
        @{
            Pattern = '(?m)^(\s*)self\.site_switch_staleness_minutes\s*=\s*int\(data\.get\("site_switch_staleness_minutes",\s*5\)\)\s*$'
            Replacement = '$1self.site_switch_staleness_minutes = int(os.environ.get("SITE_SWITCH_STALENESS_MINUTES", data.get("site_switch_staleness_minutes", 5)))'
            Label = "SITE_SWITCH_STALENESS_MINUTES"
        },
        @{
            Pattern = '(?m)^(\s*)self\.stale_threshold_days\s*=\s*int\(data\.get\("stale_threshold_days",\s*90\)\)\s*$'
            Replacement = '$1self.stale_threshold_days = int(os.environ.get("STALE_THRESHOLD_DAYS", data.get("stale_threshold_days", 90)))'
            Label = "STALE_THRESHOLD_DAYS"
        },
        @{
            Pattern = '(?m)^(\s*)self\.smtp_host\s*=\s*data\.get\("smtp_host"\)\s*$'
            Replacement = '$1self.smtp_host = os.environ.get("SMTP_HOST", data.get("smtp_host"))'
            Label = "SMTP_HOST"
        },
        @{
            Pattern = '(?m)^(\s*)self\.smtp_port\s*=\s*int\(data\.get\("smtp_port",\s*25\)\)\s*$'
            Replacement = '$1self.smtp_port = int(os.environ.get("SMTP_PORT", data.get("smtp_port", 25)))'
            Label = "SMTP_PORT"
        },
        @{
            Pattern = '(?m)^(\s*)self\.alert_email_from\s*=\s*data\.get\("alert_email_from"\)\s*$'
            Replacement = '$1self.alert_email_from = os.environ.get("ALERT_EMAIL_FROM", data.get("alert_email_from"))'
            Label = "ALERT_EMAIL_FROM"
        },
        @{
            Pattern = '(?m)^(\s*)self\.alert_email_to\s*=\s*data\.get\("alert_email_to"\)\s*$'
            Replacement = '$1self.alert_email_to = os.environ.get("ALERT_EMAIL_TO", data.get("alert_email_to"))'
            Label = "ALERT_EMAIL_TO"
        }
    )

    foreach ($item in $replacements) {
        if ($config -match [regex]::Escape($item.Label)) {
            Write-Host "[OK] $($item.Label) override already present"
            continue
        }

        $newConfig = [regex]::Replace(
            $config,
            $item.Pattern,
            $item.Replacement,
            1
        )

        if ($newConfig -ne $config) {
            $config = $newConfig
            Write-Host "[OK] Added $($item.Label) override"
        }
        else {
            Write-Host "[WARN] Could not match setting for $($item.Label); leaving existing behavior unchanged" -ForegroundColor Yellow
        }
    }

    # ------------------------------------------------------------
    # Sites and default site overrides
    # ------------------------------------------------------------
    if ($config -notmatch 'TABLEAU_SITES') {
        $pattern = '(?m)^(\s*)self\.sites\s*=\s*data\["sites"\]\s*$'
        $replacement = @'
$1sites_env = os.environ.get("TABLEAU_SITES")
$1self.sites = (
$1    [site.strip() for site in sites_env.split(",") if site.strip()]
$1    if sites_env
$1    else data["sites"]
$1)
'@
        $newConfig = [regex]::Replace($config, $pattern, $replacement.TrimEnd(), 1)

        if ($newConfig -ne $config) {
            $config = $newConfig
            Write-Host "[OK] Added TABLEAU_SITES override"
        }
        else {
            Write-Host "[WARN] Could not match self.sites assignment" -ForegroundColor Yellow
        }
    }
    else {
        Write-Host "[OK] TABLEAU_SITES override already present"
    }

    if ($config -notmatch 'TABLEAU_DEFAULT_SITE') {
        $pattern = '(?m)^(\s*)self\.default_site\s*=\s*data\.get\("default_site",\s*self\.sites\[0\]\)\s*$'
        $replacement = '$1self.default_site = os.environ.get("TABLEAU_DEFAULT_SITE", data.get("default_site", self.sites[0]))'
        $newConfig = [regex]::Replace($config, $pattern, $replacement, 1)

        if ($newConfig -ne $config) {
            $config = $newConfig
            Write-Host "[OK] Added TABLEAU_DEFAULT_SITE override"
        }
        else {
            Write-Host "[WARN] Could not match self.default_site assignment" -ForegroundColor Yellow
        }
    }
    else {
        Write-Host "[OK] TABLEAU_DEFAULT_SITE override already present"
    }

    Set-Content $configPath $config -Encoding UTF8

    # ------------------------------------------------------------
    # app.py changes
    # ------------------------------------------------------------
    Step "Patching app.py"

    $appPath = Join-Path $ProjectRoot "app.py"
    $app = Get-Content $appPath -Raw

    # Make Waitress use settings.host so APP_HOST/config.yaml can control it.
    $servePattern = 'serve\(app,\s*host=(?:"0\.0\.0\.0"|settings\.host),\s*port=settings\.port\)'
    $serveReplacement = 'serve(app, host=settings.host, port=settings.port)'
    $newApp = [regex]::Replace($app, $servePattern, $serveReplacement, 1)

    if ($newApp -ne $app) {
        $app = $newApp
        Write-Host "[OK] Waitress now uses settings.host"
    }
    elseif ($app -match 'serve\(app,\s*host=settings\.host,\s*port=settings\.port\)') {
        Write-Host "[OK] Waitress already uses settings.host"
    }
    else {
        Write-Host "[WARN] Could not find expected Waitress serve(...) line" -ForegroundColor Yellow
    }

    # Add a fallback health route only if no /health endpoint is registered.
    if ($app -notmatch 'DEPLOYMENT_HEALTH_ROUTE') {
        $schedulerPattern = '(?m)^(\s*)scheduler\.start\(\)\s*$'

        if ($app -match $schedulerPattern) {
            $healthBlock = @'
$1# DEPLOYMENT_HEALTH_ROUTE
$1# Register a dependency-free liveness route only if /health does not already exist.
$1if not any(rule.rule == "/health" for rule in app.url_map.iter_rules()):
$1    @app.get("/health")
$1    def deployment_health():
$1        return {"status": "ok"}, 200

$1scheduler.start()
'@
            $newApp = [regex]::Replace($app, $schedulerPattern, $healthBlock.TrimEnd(), 1)

            if ($newApp -ne $app) {
                $app = $newApp
                Write-Host "[OK] Added lightweight /health fallback"
            }
        }
        else {
            Write-Host "[WARN] scheduler.start() not found; health fallback not added" -ForegroundColor Yellow
        }
    }
    else {
        Write-Host "[OK] Deployment health fallback already present"
    }

    Set-Content $appPath $app -Encoding UTF8

    # ------------------------------------------------------------
    # Git ignore
    # ------------------------------------------------------------
    Step "Updating .gitignore"

    $gitignorePath = Join-Path $ProjectRoot ".gitignore"

    if (-not (Test-Path $gitignorePath)) {
        New-Item -ItemType File -Path $gitignorePath | Out-Null
    }

    $ignoreText = Get-Content $gitignorePath -Raw -ErrorAction SilentlyContinue

    foreach ($entry in @(".deployment-backups/", ".patch-backups/")) {
        if ($ignoreText -notmatch "(?m)^$([regex]::Escape($entry))\s*$") {
            Add-Content $gitignorePath "`r`n$entry"
            Write-Host "[OK] Added $entry"
            $ignoreText += "`r`n$entry"
        }
        else {
            Write-Host "[OK] Already ignored: $entry"
        }
    }

    # ------------------------------------------------------------
    # Syntax validation
    # ------------------------------------------------------------
    Step "Validating Python syntax"

    $python = $null

    if (Get-Command python -ErrorAction SilentlyContinue) {
        $python = "python"
    }
    elseif (Get-Command py -ErrorAction SilentlyContinue) {
        $python = "py"
    }
    else {
        throw "Neither python nor py is available."
    }

    foreach ($name in @("config.py", "app.py")) {
        if ($python -eq "python") {
            & python -m py_compile $name
        }
        else {
            & py -m py_compile $name
        }

        if ($LASTEXITCODE -ne 0) {
            throw "Python syntax validation failed for $name."
        }

        Write-Host "[OK] $name syntax passed"
    }

    # ------------------------------------------------------------
    # Git credential hygiene check
    # ------------------------------------------------------------
    Step "Checking credential file tracking"

    if (Get-Command git -ErrorAction SilentlyContinue) {
        git ls-files --error-unmatch -- bigquery-credentials.json 2>$null | Out-Null

        if ($LASTEXITCODE -eq 0) {
            Write-Host ""
            Write-Host "WARNING: bigquery-credentials.json is already tracked by Git." -ForegroundColor Red
            Write-Host "Do not commit or push additional credential changes."
            Write-Host "If this is a real credential, rotate/revoke it and follow your approved"
            Write-Host "repository secret-removal process."
        }
        else {
            Write-Host "[OK] bigquery-credentials.json is not tracked by Git" -ForegroundColor Green
        }
    }

    Write-Host ""
    Write-Host "Deployment-readiness patch completed successfully." -ForegroundColor Green
    Write-Host ""
    Write-Host "Next command:"
    Write-Host "  .\validate-deployment.ps1"
    Write-Host ""
    Write-Host "Rollback command:"
    Write-Host "  .\deployment-readiness-patch-v2.ps1 -Rollback" -ForegroundColor Yellow
}
catch {
    Write-Host ""
    Write-Host "Patch failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Restoring original files..."
    Restore-Backup $BackupDir
    exit 1
}
