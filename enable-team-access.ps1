# enable-team-access.ps1
# Safely configures the Tableau Admin Dashboard for LAN/team access.
# It creates a backup before changing app.py.
#
# Run from PowerShell:
#   Set-ExecutionPolicy -Scope Process Bypass
#   .\enable-team-access.ps1

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "=============================================="
Write-Host " Tableau Admin Dashboard - Team Access Setup"
Write-Host "=============================================="
Write-Host ""

# ------------------------------------------------------------
# 1. Verify we're in the project directory
# ------------------------------------------------------------

if (-not (Test-Path ".\app.py")) {
    Write-Host "ERROR: app.py was not found." -ForegroundColor Red
    Write-Host "Run this script from the tableau-admin-dashboard folder."
    exit 1
}

Write-Host "[OK] Found app.py"

# ------------------------------------------------------------
# 2. Create a backup
# ------------------------------------------------------------

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backup = ".\app.py.backup-$timestamp"

Copy-Item ".\app.py" $backup

Write-Host "[OK] Backup created:"
Write-Host "     $backup"
Write-Host ""

# ------------------------------------------------------------
# 3. Read app.py
# ------------------------------------------------------------

$content = Get-Content ".\app.py" -Raw

# ------------------------------------------------------------
# 4. Change Waitress from settings.host to 0.0.0.0
# ------------------------------------------------------------

$oldLine = 'serve(app, host=settings.host, port=settings.port)'
$newLine = 'serve(app, host="0.0.0.0", port=settings.port)'

if ($content.Contains($oldLine)) {

    $content = $content.Replace($oldLine, $newLine)

    Set-Content ".\app.py" $content -Encoding UTF8

    Write-Host "[OK] Changed Waitress host:"
    Write-Host ""
    Write-Host "     OLD: $oldLine"
    Write-Host "     NEW: $newLine"
    Write-Host ""

}
elseif ($content.Contains('host="0.0.0.0"')) {

    Write-Host "[OK] app.py already appears configured for team access."
    Write-Host ""

}
else {

    Write-Host "WARNING: Could not find the expected Waitress line." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "No automatic change was made."
    Write-Host "Backup is available at:"
    Write-Host "  $backup"
    Write-Host ""
    Write-Host "Look near the bottom of app.py for:"
    Write-Host ""
    Write-Host 'serve(app, host=..., port=...)'
    exit 1
}

# ------------------------------------------------------------
# 5. Verify Python syntax
# ------------------------------------------------------------

Write-Host "Checking Python syntax..."

python -m py_compile app.py

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "ERROR: Python syntax check failed." -ForegroundColor Red
    Write-Host "Restoring original app.py..."

    Copy-Item $backup ".\app.py" -Force

    Write-Host "[OK] Original file restored."
    exit 1
}

Write-Host "[OK] Python syntax is valid."
Write-Host ""

# ------------------------------------------------------------
# 6. Show this computer's IPv4 addresses
# ------------------------------------------------------------

Write-Host "Possible addresses teammates can use:"
Write-Host ""

$addresses = Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object {
        $_.IPAddress -ne "127.0.0.1" -and
        $_.IPAddress -notlike "169.254.*"
    } |
    Select-Object -ExpandProperty IPAddress

if ($addresses) {
    foreach ($ip in $addresses) {
        Write-Host "     http://${ip}:<PORT>"
    }
}
else {
    Write-Host "Could not automatically determine an IPv4 address."
    Write-Host "Run: ipconfig"
}

Write-Host ""

# ------------------------------------------------------------
# 7. Important notes
# ------------------------------------------------------------

Write-Host "IMPORTANT:"
Write-Host ""
Write-Host "1. This script DOES NOT change Windows Firewall."
Write-Host "2. This script DOES NOT expose anything to the public internet."
Write-Host "3. Your teammates must be able to reach your computer over the"
Write-Host "   approved corporate network/VPN."
Write-Host "4. Your BigQuery account-number sync still runs before the"
Write-Host "   web server starts, so startup may take several minutes."
Write-Host ""

# ------------------------------------------------------------
# 8. Ask whether to start the application
# ------------------------------------------------------------

$response = Read-Host "Start the dashboard now? (Y/N)"

if ($response -match "^[Yy]") {

    Write-Host ""
    Write-Host "Starting dashboard..."
    Write-Host ""
    Write-Host "DO NOT close this PowerShell window while the app is needed."
    Write-Host ""
    Write-Host "Waiting for BigQuery initialization may take some time."
    Write-Host ""

    python app.py

}
else {

    Write-Host ""
    Write-Host "Setup complete."
    Write-Host ""
    Write-Host "Start the dashboard later with:"
    Write-Host ""
    Write-Host "     python app.py"
}