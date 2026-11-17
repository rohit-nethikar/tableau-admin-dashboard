param(
    [switch]$Rollback
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

$BackupRoot = Join-Path $ProjectRoot ".deployment-backups"
$LatestFile = Join-Path $BackupRoot "LATEST-healthz.txt"

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
        Fail "No healthz backup metadata was found."
    }

    $BackupDir = (Get-Content $LatestFile -Raw).Trim()

    if (-not (Test-Path $BackupDir)) {
        Fail "Backup directory does not exist: $BackupDir"
    }

    Restore-Backup $BackupDir
    exit 0
}

foreach ($required in @("app.py", "Dockerfile", "validate-deployment.ps1", "DEPLOYMENT.md")) {
    if (-not (Test-Path $required)) {
        Fail "$required was not found. Run this script from the project root."
    }
}

Step "Creating rollback backup"

New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$BackupDir = Join-Path $BackupRoot ("healthz-" + $stamp)
New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null

$ManagedFiles = @(
    "app.py",
    "Dockerfile",
    "validate-deployment.ps1",
    "DEPLOYMENT.md"
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
Write-Host "  .\deployment-healthz-patch.ps1 -Rollback" -ForegroundColor Yellow

try {
    Step "Adding lightweight /healthz route"

    $appPath = Join-Path $ProjectRoot "app.py"
    $app = Get-Content $appPath -Raw

    if ($app -match '(?m)^\s*@app\.(get|route)\("/healthz"') {
        Write-Host "[OK] /healthz already exists"
    }
    else {
        $schedulerPattern = '(?m)^(\s*)scheduler\.start\(\)\s*$'

        if (-not ($app -match $schedulerPattern)) {
            throw "Could not find scheduler.start() in app.py."
        }

        $healthzBlock = @'
$1# DEPLOYMENT_LIVENESS_ROUTE
$1@app.get("/healthz")
$1def deployment_liveness():
$1    return {"status": "ok"}, 200

$1scheduler.start()
'@

        $newApp = [regex]::Replace(
            $app,
            $schedulerPattern,
            $healthzBlock.TrimEnd(),
            1
        )

        if ($newApp -eq $app) {
            throw "Could not insert /healthz route."
        }

        Set-Content $appPath $newApp -Encoding UTF8
        Write-Host "[OK] Added /healthz"
    }

    Step "Updating Docker health check"

    $dockerPath = Join-Path $ProjectRoot "Dockerfile"
    $docker = Get-Content $dockerPath -Raw

    $dockerNew = $docker -replace "/health'", "/healthz'"
    $dockerNew = $dockerNew -replace '/health"', '/healthz"'

    if ($dockerNew -eq $docker) {
        if ($docker -match '/healthz') {
            Write-Host "[OK] Dockerfile already probes /healthz"
        }
        else {
            throw "Could not find the Docker health-check URL."
        }
    }
    else {
        Set-Content $dockerPath $dockerNew -Encoding UTF8
        Write-Host "[OK] Dockerfile now probes /healthz"
    }

    Step "Updating deployment validator"

    $validatorPath = Join-Path $ProjectRoot "validate-deployment.ps1"
    $validator = Get-Content $validatorPath -Raw

    $validatorNew = $validator
    $validatorNew = $validatorNew -replace "HEALTH_ROUTE=", "HEALTHZ_ROUTE="
    $validatorNew = $validatorNew -replace "r\.rule == '/health'", "r.rule == '/healthz'"
    $validatorNew = $validatorNew -replace 'HEALTH_ROUTE=True', 'HEALTHZ_ROUTE=True'
    $validatorNew = $validatorNew -replace '/health is registered', '/healthz is registered'
    $validatorNew = $validatorNew -replace '/health was not found', '/healthz was not found'

    if ($validatorNew -eq $validator) {
        if ($validator -match '/healthz') {
            Write-Host "[OK] Validator already checks /healthz"
        }
        else {
            throw "Could not update validate-deployment.ps1 to check /healthz."
        }
    }
    else {
        Set-Content $validatorPath $validatorNew -Encoding UTF8
        Write-Host "[OK] Validator now checks /healthz"
    }

    Step "Updating deployment documentation"

    $docPath = Join-Path $ProjectRoot "DEPLOYMENT.md"
    $doc = Get-Content $docPath -Raw
    $docNew = $doc -replace 'http://127\.0\.0\.1:5000/health\b', 'http://127.0.0.1:5000/healthz'
    $docNew = $doc -replace 'against `/health`', 'against `/healthz`'

    if ($docNew -ne $doc) {
        Set-Content $docPath $docNew -Encoding UTF8
        Write-Host "[OK] DEPLOYMENT.md now documents /healthz"
    }
    else {
        Write-Host "[OK] DEPLOYMENT.md already appears current"
    }

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

    if ($python -eq "python") {
        & python -m py_compile app.py
    }
    else {
        & py -m py_compile app.py
    }

    if ($LASTEXITCODE -ne 0) {
        throw "Python syntax validation failed for app.py."
    }

    Write-Host "[OK] app.py syntax passed" -ForegroundColor Green

    Write-Host ""
    Write-Host "Healthz patch completed successfully." -ForegroundColor Green
    Write-Host ""
    Write-Host "Next:"
    Write-Host "  .\validate-deployment.ps1"
    Write-Host ""
    Write-Host "Then start:"
    Write-Host "  .\startup.ps1"
    Write-Host ""
    Write-Host "Test:"
    Write-Host "  http://127.0.0.1:5000/healthz"
}
catch {
    Write-Host ""
    Write-Host "Patch failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Restoring original files..."
    Restore-Backup $BackupDir
    exit 1
}
