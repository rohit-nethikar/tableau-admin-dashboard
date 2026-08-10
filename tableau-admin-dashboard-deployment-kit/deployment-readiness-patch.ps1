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

function Restore($BackupDir) {
    Step "Restoring backup: $BackupDir"

    $manifest = Join-Path $BackupDir "manifest.txt"
    if (-not (Test-Path $manifest)) {
        Fail "Backup manifest missing: $manifest"
    }

    $entries = Get-Content $manifest
    foreach ($entry in $entries) {
        if ([string]::IsNullOrWhiteSpace($entry)) { continue }

        $parts = $entry -split '\|', 2
        $state = $parts[0]
        $name = $parts[1]
        $target = Join-Path $ProjectRoot $name
        $backup = Join-Path $BackupDir $name

        if ($state -eq "EXISTED") {
            $parent = Split-Path -Parent $target
            if ($parent) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }
            Copy-Item $backup $target -Force
            Write-Host "Restored $name"
        } elseif ($state -eq "ABSENT") {
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

    Restore $BackupDir
    exit 0
}

$RequiredExisting = @("app.py", "config.py", "requirements.txt")
foreach ($name in $RequiredExisting) {
    if (-not (Test-Path $name)) {
        Fail "$name was not found. Put this kit in the project root before running it."
    }
}

$KitFiles = @(
    "Dockerfile",
    ".dockerignore",
    ".env.example",
    "startup.ps1",
    "startup.sh",
    "validate-deployment.ps1",
    "DEPLOYMENT.md"
)

foreach ($name in $KitFiles) {
    if (-not (Test-Path $name)) {
        Fail "Deployment kit file missing: $name"
    }
}

Step "Creating rollback backup"

New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$BackupDir = Join-Path $BackupRoot $stamp
New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null

$Managed = @(
    "app.py",
    "config.py",
    "Dockerfile",
    ".dockerignore",
    ".env.example",
    "startup.ps1",
    "startup.sh",
    "validate-deployment.ps1",
    "DEPLOYMENT.md"
)

$manifestLines = @()

foreach ($name in $Managed) {
    $path = Join-Path $ProjectRoot $name
    if (Test-Path $path) {
        $backupPath = Join-Path $BackupDir $name
        $backupParent = Split-Path -Parent $backupPath
        if ($backupParent) { New-Item -ItemType Directory -Force -Path $backupParent | Out-Null }
        Copy-Item $path $backupPath -Force
        $manifestLines += "EXISTED|$name"
    } else {
        $manifestLines += "ABSENT|$name"
    }
}

Set-Content (Join-Path $BackupDir "manifest.txt") $manifestLines -Encoding UTF8
Set-Content $LatestFile $BackupDir -Encoding UTF8

Write-Host "Backup: $BackupDir"
Write-Host "Rollback: .\deployment-readiness-patch.ps1 -Rollback" -ForegroundColor Yellow

Step "Patching config.py for environment-variable overrides"

$configPath = Join-Path $ProjectRoot "config.py"
$config = Get-Content $configPath -Raw

if ($config -notmatch 'APP_DATA_DIR') {
    $oldConstants = @'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.yaml")
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
DB_PATH = os.path.join(INSTANCE_DIR, "cache.db")
SECRET_KEY_PATH = os.path.join(INSTANCE_DIR, "secret.key")
'@

    $newConstants = @'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.yaml")

# Deployment-friendly persistent runtime directory.
# Local behavior remains unchanged when APP_DATA_DIR is not set.
APP_DATA_DIR = os.path.abspath(
    os.environ.get("APP_DATA_DIR", os.path.join(BASE_DIR, "instance"))
)
INSTANCE_DIR = APP_DATA_DIR
DB_PATH = os.path.join(INSTANCE_DIR, "cache.db")
SECRET_KEY_PATH = os.path.join(INSTANCE_DIR, "secret.key")
'@

    if (-not $config.Contains($oldConstants)) {
        Restore $BackupDir
        Fail "config.py did not match the expected path constants. Nothing was left partially patched."
    }

    $config = $config.Replace($oldConstants, $newConstants)
}

if ($config -notmatch 'TABLEAU_SERVER_URL') {
    $oldInit = @'
    def __init__(self, data):
        self.server_url = data["server_url"].rstrip("/")
        self.host = data.get("host", "127.0.0.1")
        self.port = int(data.get("port", 5000))
        self.sites = data["sites"]
        self.default_site = data.get("default_site", self.sites[0])
        self.refresh_interval_minutes = int(data.get("refresh_interval_minutes", 60))
        self.site_switch_staleness_minutes = int(data.get("site_switch_staleness_minutes", 5))
        self.stale_threshold_days = int(data.get("stale_threshold_days", 90))
        # Extract-failure email alerting - optional; leave smtp_host unset to disable.
        self.smtp_host = data.get("smtp_host")
        self.smtp_port = int(data.get("smtp_port", 25))
        self.alert_email_from = data.get("alert_email_from")
        self.alert_email_to = data.get("alert_email_to")
'@

    $newInit = @'
    def __init__(self, data):
        self.server_url = os.environ.get(
            "TABLEAU_SERVER_URL", data["server_url"]
        ).rstrip("/")

        self.host = os.environ.get(
            "APP_HOST", data.get("host", "127.0.0.1")
        )
        self.port = int(os.environ.get(
            "APP_PORT", data.get("port", 5000)
        ))

        sites_env = os.environ.get("TABLEAU_SITES")
        self.sites = (
            [site.strip() for site in sites_env.split(",") if site.strip()]
            if sites_env
            else data["sites"]
        )

        self.default_site = os.environ.get(
            "TABLEAU_DEFAULT_SITE",
            data.get("default_site", self.sites[0]),
        )

        self.refresh_interval_minutes = int(os.environ.get(
            "REFRESH_INTERVAL_MINUTES",
            data.get("refresh_interval_minutes", 60),
        ))
        self.site_switch_staleness_minutes = int(os.environ.get(
            "SITE_SWITCH_STALENESS_MINUTES",
            data.get("site_switch_staleness_minutes", 5),
        ))
        self.stale_threshold_days = int(os.environ.get(
            "STALE_THRESHOLD_DAYS",
            data.get("stale_threshold_days", 90),
        ))

        # Extract-failure email alerting - optional.
        self.smtp_host = os.environ.get("SMTP_HOST", data.get("smtp_host"))
        self.smtp_port = int(os.environ.get(
            "SMTP_PORT", data.get("smtp_port", 25)
        ))
        self.alert_email_from = os.environ.get(
            "ALERT_EMAIL_FROM", data.get("alert_email_from")
        )
        self.alert_email_to = os.environ.get(
            "ALERT_EMAIL_TO", data.get("alert_email_to")
        )
'@

    if (-not $config.Contains($oldInit)) {
        Restore $BackupDir
        Fail "config.py Settings.__init__ did not match the expected source. Backup restored."
    }

    $config = $config.Replace($oldInit, $newInit)
}

Set-Content $configPath $config -Encoding UTF8
Write-Host "Environment-variable config support applied"

Step "Adding a lightweight /health route when the app does not already define one"

$appPath = Join-Path $ProjectRoot "app.py"
$app = Get-Content $appPath -Raw

$healthMarker = "# DEPLOYMENT_HEALTH_ROUTE"

if (-not $app.Contains($healthMarker)) {
    $returnMarker = "    scheduler.start()"

    if (-not $app.Contains($returnMarker)) {
        Restore $BackupDir
        Fail "Could not find scheduler.start() in app.py. Backup restored."
    }

    $healthBlock = @'
    # DEPLOYMENT_HEALTH_ROUTE
    # Preserve an existing /health route if the application already has one.
    # Otherwise register a dependency-free liveness endpoint for hosting probes.
    if not any(rule.rule == "/health" for rule in app.url_map.iter_rules()):
        @app.get("/health")
        def deployment_health():
            return {"status": "ok"}, 200

'@

    $app = $app.Replace($returnMarker, $healthBlock + $returnMarker)
    Set-Content $appPath $app -Encoding UTF8
    Write-Host "Health-route safeguard applied"
} else {
    Write-Host "Deployment health safeguard already present"
}

Step "Ensuring deployment backup directory is ignored by Git"

$gitignore = Join-Path $ProjectRoot ".gitignore"
if (Test-Path $gitignore) {
    $ignoreText = Get-Content $gitignore -Raw
    if ($ignoreText -notmatch '(?m)^\.deployment-backups/\s*$') {
        Add-Content $gitignore "`r`n# Deployment rollback backups`r`n.deployment-backups/"
        Write-Host "Added .deployment-backups/ to .gitignore"
    }
} else {
    @'
# Deployment/runtime
.deployment-backups/
.patch-backups/
.env
.env.*
instance/
data/
*.db
*.sqlite
*.sqlite3
*.log
*.pid
bigquery-credentials.json
*-credentials.json
__pycache__/
*.py[cod]
.venv/
venv/
'@ | Set-Content $gitignore -Encoding UTF8
    Write-Host "Created .gitignore"
}

Step "Validating Python syntax"

$python = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    $python = "python"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $python = "py"
} else {
    Restore $BackupDir
    Fail "Python was not found. Backup restored."
}

foreach ($name in @("app.py", "config.py")) {
    if ($python -eq "python") {
        & python -m py_compile $name
    } else {
        & py -m py_compile $name
    }

    if ($LASTEXITCODE -ne 0) {
        Restore $BackupDir
        Fail "Syntax validation failed for $name. Backup restored."
    }
}

Write-Host "[OK] Python syntax passed" -ForegroundColor Green

Step "Checking whether credential JSON is already tracked by Git"

if (Get-Command git -ErrorAction SilentlyContinue) {
    git ls-files --error-unmatch -- bigquery-credentials.json 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "WARNING: bigquery-credentials.json is ALREADY TRACKED by Git." -ForegroundColor Red
        Write-Host "Do not delete history blindly. Rotate the credential if it is real and"
        Write-Host "follow your approved repository secret-removal process."
    } else {
        Write-Host "[OK] bigquery-credentials.json is not tracked by Git" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "Deployment-readiness patch completed." -ForegroundColor Green
Write-Host ""
Write-Host "Next:"
Write-Host "  .\validate-deployment.ps1"
Write-Host ""
Write-Host "Local start:"
Write-Host "  .\startup.ps1"
Write-Host ""
Write-Host "Rollback:"
Write-Host "  .\deployment-readiness-patch.ps1 -Rollback" -ForegroundColor Yellow
