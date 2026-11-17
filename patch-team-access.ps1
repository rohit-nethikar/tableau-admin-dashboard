param(
    [switch]$Rollback
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

$BackupRoot = Join-Path $ProjectRoot ".patch-backups"
$LatestFile = Join-Path $BackupRoot "LATEST.txt"

function Write-Step($Message) {
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Fail($Message) {
    Write-Host ""
    Write-Host "ERROR: $Message" -ForegroundColor Red
    exit 1
}

function Restore-Backup($BackupDir) {
    Write-Step "Restoring backup from $BackupDir"

    foreach ($name in @("app.py", "bigquery_sync.py", "scheduler.py")) {
        $src = Join-Path $BackupDir $name
        if (Test-Path $src) {
            Copy-Item $src (Join-Path $ProjectRoot $name) -Force
            Write-Host "Restored $name"
        }
    }

    Write-Host ""
    Write-Host "Rollback complete." -ForegroundColor Green
}

if ($Rollback) {
    if (-not (Test-Path $LatestFile)) {
        Fail "No backup metadata was found at $LatestFile"
    }

    $BackupDir = (Get-Content $LatestFile -Raw).Trim()
    if (-not (Test-Path $BackupDir)) {
        Fail "Backup directory does not exist: $BackupDir"
    }

    Restore-Backup $BackupDir
    exit 0
}

Write-Step "Checking required project files"

$RequiredFiles = @("app.py", "bigquery_sync.py", "scheduler.py")
foreach ($name in $RequiredFiles) {
    if (-not (Test-Path (Join-Path $ProjectRoot $name))) {
        Fail "$name was not found. Put this script in the tableau-admin-dashboard project folder and run it there."
    }
    Write-Host "Found $name"
}

Write-Step "Creating timestamped backup"

New-Item -ItemType Directory -Path $BackupRoot -Force | Out-Null
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$BackupDir = Join-Path $BackupRoot $Stamp
New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null

foreach ($name in $RequiredFiles) {
    Copy-Item (Join-Path $ProjectRoot $name) (Join-Path $BackupDir $name) -Force
}

Set-Content -Path $LatestFile -Value $BackupDir -Encoding UTF8

Write-Host "Backup created at:"
Write-Host "  $BackupDir"
Write-Host ""
Write-Host "Rollback command:"
Write-Host "  .\patch-team-access.ps1 -Rollback" -ForegroundColor Yellow

Write-Step "Patching app.py"

$appPath = Join-Path $ProjectRoot "app.py"
$app = Get-Content $appPath -Raw

# 1) Add threading import if it is not already present.
if ($app -notmatch '(?m)^import threading\s*$') {
    if ($app -match '(?m)^import os\s*$') {
        $app = [regex]::Replace(
            $app,
            '(?m)^import os\s*$',
            "import os`r`nimport threading",
            1
        )
        Write-Host "Added: import threading"
    }
    else {
        Fail "Could not find 'import os' in app.py, so the script stopped without applying changes."
    }
}

# 2) Add a lock and background-sync helper once.
if ($app -notmatch '(?m)^_account_sync_lock\s*=\s*threading\.Lock\(\)\s*$') {
    $secretMarker = 'FLASK_SECRET_PATH = os.path.join(INSTANCE_DIR, "flask_secret.key")'
    if (-not $app.Contains($secretMarker)) {
        Fail "Could not find FLASK_SECRET_PATH in app.py."
    }

    $helper = @'

# Prevent duplicate account-number syncs inside this process.
_account_sync_lock = threading.Lock()


def _sync_account_numbers_background():
    """Run the existing account-number startup work without blocking Waitress."""
    if not _account_sync_lock.acquire(blocking=False):
        print("Account number sync is already running; skipping duplicate trigger")
        return

    try:
        print("Background account-number sync started")
        import bigquery_sync
        import uuid
        import sqlite3

        # Preserve the existing behavior: add missing custom-view owners first.
        with db.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT owner_name FROM custom_views")
            custom_view_owners = [row[0] for row in cursor.fetchall()]

            added_count = 0
            for owner in custom_view_owners:
                cursor.execute(
                    "SELECT id FROM users WHERE LOWER(email) = LOWER(?)",
                    (owner,),
                )
                if not cursor.fetchone():
                    cursor.execute(
                        "SELECT site FROM custom_views WHERE owner_name = ? LIMIT 1",
                        (owner,),
                    )
                    site_row = cursor.fetchone()
                    if site_row:
                        site = site_row[0]
                        user_id = str(uuid.uuid4())
                        name_part = owner.split("@")[0]
                        try:
                            cursor.execute(
                                """
                                INSERT INTO users
                                    (id, name, email, site, site_role, fetched_at, account_number)
                                VALUES
                                    (?, ?, ?, ?, ?, datetime('now'), NULL)
                                """,
                                (user_id, name_part, owner, site, "Unknown"),
                            )
                            added_count += 1
                        except sqlite3.IntegrityError:
                            pass

            if added_count > 0:
                conn.commit()
                print(f"Added {added_count} custom view owners to users table")

        result = bigquery_sync.sync_account_numbers_to_database(db)
        print(
            f"Account number sync: {result['message']} "
            f"(Updated: {result['updated_count']})"
        )

        with db.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM users
                WHERE account_number IS NOT NULL
                  AND account_number != ''
                """
            )
            count = cursor.fetchone()[0]
            print(f"Verification: {count} users now have account numbers")

        try:
            from account_number_watchdog import get_watchdog

            watchdog = get_watchdog()
            if not watchdog.verify_accounts():
                print(
                    "WARNING: Account numbers were lost and have been "
                    "auto-restored from backup"
                )
        except Exception as watchdog_error:
            print(f"WARNING: Account watchdog error: {watchdog_error}")

    except Exception as error:
        print(f"WARNING: Background account number sync failed: {error}")
        import traceback

        traceback.print_exc()
    finally:
        _account_sync_lock.release()


def _start_account_number_sync_async():
    """Start account-number synchronization in a daemon thread."""
    thread = threading.Thread(
        target=_sync_account_numbers_background,
        name="account-number-sync",
        daemon=True,
    )
    thread.start()
    return thread
'@

    $app = $app.Replace($secretMarker, $secretMarker + $helper)
    Write-Host "Added guarded background account-number sync helper"
}
else {
    Write-Host "Background sync helper already present"
}

# 3) Remove the old synchronous/blocking startup block.
$startMarker = '    # Sync account numbers from BigQuery BEFORE app starts (synchronous, blocking)'
$endMarker = '        print(f"WARNING: Account watchdog error: {e}")'

if ($app.Contains($startMarker)) {
    $startIndex = $app.IndexOf($startMarker)
    $endIndex = $app.IndexOf($endMarker, $startIndex)

    if ($endIndex -lt 0) {
        Fail "Found the old BigQuery startup block, but could not find its expected end marker."
    }

    $endIndex = $endIndex + $endMarker.Length

    while ($endIndex -lt $app.Length -and ($app[$endIndex] -eq "`r" -or $app[$endIndex] -eq "`n")) {
        $endIndex++
    }

    $app = $app.Remove($startIndex, $endIndex - $startIndex)
    Write-Host "Removed blocking BigQuery startup sync"
}
else {
    Write-Host "Old blocking BigQuery startup block not found; it may already have been patched"
}

# 4) Start the background sync after the normal scheduler starts.
if ($app -notmatch '(?m)^\s{4}_start_account_number_sync_async\(\)\s*$') {
    $schedulerStart = '    scheduler.start()'
    if (-not $app.Contains($schedulerStart)) {
        Fail "Could not find 'scheduler.start()' in app.py."
    }

    $replacement = @'
    scheduler.start()

    # Do not hold up Waitress while BigQuery processes millions of rows.
    _start_account_number_sync_async()
'@

    $app = $app.Replace($schedulerStart, $replacement.TrimEnd("`r", "`n"))
    Write-Host "Configured account-number sync to start in background"
}
else {
    Write-Host "Background sync startup call already present"
}

# 5) Bind Waitress to all local network interfaces.
$oldServe = 'serve(app, host=settings.host, port=settings.port)'
$newServe = 'serve(app, host="0.0.0.0", port=settings.port)'

if ($app.Contains($oldServe)) {
    $app = $app.Replace($oldServe, $newServe)
    Write-Host 'Changed Waitress host from settings.host to 0.0.0.0'
}
elseif ($app.Contains($newServe)) {
    Write-Host "Waitress is already bound to 0.0.0.0"
}
else {
    Fail "Could not find the expected Waitress serve(...) line in app.py."
}

Set-Content -Path $appPath -Value $app -Encoding UTF8

Write-Step "Validating Python syntax"

$PythonCommand = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    $PythonCommand = "python"
}
elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $PythonCommand = "py"
}
else {
    Restore-Backup $BackupDir
    Fail "Neither 'python' nor 'py' was found. The original files were restored."
}

$ValidationFailed = $false
foreach ($name in $RequiredFiles) {
    Write-Host "Checking $name ..."
    if ($PythonCommand -eq "python") {
        & python -m py_compile $name
    }
    else {
        & py -m py_compile $name
    }

    if ($LASTEXITCODE -ne 0) {
        $ValidationFailed = $true
        break
    }
}

if ($ValidationFailed) {
    Write-Host ""
    Write-Host "Python syntax validation failed. Restoring backup..." -ForegroundColor Red
    Restore-Backup $BackupDir
    exit 1
}

Write-Host "Python syntax validation passed." -ForegroundColor Green

Write-Step "Showing the effective Waitress binding"

Select-String -Path $appPath -Pattern 'serve\(app,' | ForEach-Object {
    Write-Host $_.Line.Trim()
}

Write-Step "Checking current IPv4 addresses"

try {
    $addresses = Get-NetIPAddress -AddressFamily IPv4 |
        Where-Object {
            $_.IPAddress -ne "127.0.0.1" -and
            $_.IPAddress -notlike "169.254.*"
        } |
        Select-Object -ExpandProperty IPAddress -Unique

    if ($addresses) {
        Write-Host "Possible addresses for an approved teammate on a reachable internal network:"
        foreach ($ip in $addresses) {
            Write-Host "  http://${ip}:<YOUR_PORT>"
        }
    }
    else {
        Write-Host "No non-loopback IPv4 address was detected. Run: ipconfig"
    }
}
catch {
    Write-Host "Could not query IPv4 addresses automatically. Run: ipconfig"
}

Write-Host ""
Write-Host "IMPORTANT" -ForegroundColor Yellow
Write-Host "  - This script does NOT change Windows Firewall."
Write-Host "  - This script does NOT create a public tunnel or expose the app to the Internet."
Write-Host "  - Team access still depends on approved corporate network/VPN routing and endpoint policy."
Write-Host "  - The BigQuery sync now starts in a daemon background thread, so Waitress can start without waiting for it."
Write-Host ""
Write-Host "Patch completed successfully." -ForegroundColor Green
Write-Host ""
Write-Host "Start the app with:"
Write-Host "  python app.py"
Write-Host ""
Write-Host "If you need to undo this patch:"
Write-Host "  .\patch-team-access.ps1 -Rollback" -ForegroundColor Yellow
