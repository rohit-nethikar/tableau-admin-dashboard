# ============================================================================
# Tableau Admin Dashboard - Manual NSSM Service Setup
# ============================================================================
# Use this if automatic download fails
# NSSM must be downloaded manually first
# ============================================================================

$ErrorActionPreference = "Stop"

# Configuration
$DashboardPath = "C:\Users\m239012\OneDrive - Mayo Clinic\GitHub_claude\tableau-admin-dashboard"
$NssmPath = "C:\tools\nssm"
$NssmExe = "$NssmPath\nssm.exe"
$RunServiceBat = "$DashboardPath\run_service.bat"

$ServiceName = "TableauAdminDash"
$ServiceDisplayName = "Tableau Admin Dashboard"
$ServiceDescription = "Local governance app for Tableau Server administration"

# ============================================================================
# FUNCTIONS
# ============================================================================

function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Write-Header {
    param([string]$Text)
    Write-Host ""
    Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host $Text -ForegroundColor Cyan
    Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
}

function Write-Success {
    param([string]$Text)
    Write-Host "✓ $Text" -ForegroundColor Green
}

function Write-Error-Custom {
    param([string]$Text)
    Write-Host "✗ $Text" -ForegroundColor Red
}

function Write-Info {
    param([string]$Text)
    Write-Host "ℹ $Text" -ForegroundColor Yellow
}

# ============================================================================
# MAIN
# ============================================================================

Write-Header "Manual NSSM Service Setup"

# Check administrator
if (-not (Test-Administrator)) {
    Write-Error-Custom "This script must be run as Administrator"
    exit 1
}

Write-Success "Running as Administrator"

# ============================================================================
# STEP 1: Check NSSM
# ============================================================================

Write-Header "Step 1: Verifying NSSM Installation"

if (-not (Test-Path $NssmExe)) {
    Write-Error-Custom "NSSM not found at: $NssmExe"
    Write-Host ""
    Write-Info "Manual Setup Required:"
    Write-Host ""
    Write-Host "1. Download NSSM from one of these sources:" -ForegroundColor Yellow
    Write-Host "   Option A: https://github.com/nssm-service-manager/nssm/releases" -ForegroundColor White
    Write-Host "   Option B: https://nssm.cc/download" -ForegroundColor White
    Write-Host ""
    Write-Host "2. Download the latest version (look for .zip file, 64-bit)" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "3. Extract to: C:\tools\nssm\" -ForegroundColor Yellow
    Write-Host "   Structure should be:" -ForegroundColor Gray
    Write-Host "     C:\tools\nssm\" -ForegroundColor Gray
    Write-Host "     ├── nssm.exe" -ForegroundColor Gray
    Write-Host "     ├── win32\" -ForegroundColor Gray
    Write-Host "     └── win64\" -ForegroundColor Gray
    Write-Host ""
    Write-Host "4. Run this script again:" -ForegroundColor Yellow
    Write-Host "   .\setup-service-manual.ps1" -ForegroundColor Gray
    Write-Host ""
    exit 1
}

Write-Success "NSSM found at: $NssmExe"

# Test NSSM executable
try {
    $output = & $NssmExe -version 2>&1
    Write-Success "NSSM is working"
} catch {
    Write-Error-Custom "NSSM executable failed: $_"
    exit 1
}

# ============================================================================
# STEP 2: Create Batch Wrapper
# ============================================================================

Write-Header "Step 2: Creating Service Wrapper Script"

$BatchScriptContent = @"
@echo off
REM tableau-admin-dashboard service wrapper for NSSM
REM This script activates the Python virtual environment and runs the app

cd /d "$DashboardPath"

if not exist ".venv\Scripts\activate.bat" (
    echo Error: Virtual environment not found at %CD%\.venv
    exit /b 1
)

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Run the app
python app.py
"@

Write-Info "Creating batch wrapper at: $RunServiceBat"
Set-Content -Path $RunServiceBat -Value $BatchScriptContent -Encoding ASCII -Force
Write-Success "Batch wrapper created"

# ============================================================================
# STEP 3: Uninstall Existing Service
# ============================================================================

Write-Header "Step 3: Checking for Existing Service"

if (Get-Service -Name $ServiceName -ErrorAction SilentlyContinue) {
    Write-Info "Found existing service, removing..."
    Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    & $NssmExe remove $ServiceName confirm 2>&1 | Out-Null
    Start-Sleep -Seconds 2
    Write-Success "Old service removed"
} else {
    Write-Info "No existing service found"
}

# ============================================================================
# STEP 4: Install Service
# ============================================================================

Write-Header "Step 4: Installing Windows Service"

Write-Info "Installing service '$ServiceName'..."
$output = & $NssmExe install $ServiceName "`"$RunServiceBat`"" 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Success "Service installed"
} else {
    Write-Error-Custom "Installation failed: $output"
    exit 1
}

# ============================================================================
# STEP 5: Configure Service
# ============================================================================

Write-Header "Step 5: Configuring Service"

Write-Info "Setting service properties..."

& $NssmExe set $ServiceName DisplayName $ServiceDisplayName 2>&1 | Out-Null
Write-Success "Display name set"

& $NssmExe set $ServiceName Description $ServiceDescription 2>&1 | Out-Null
Write-Success "Description set"

& $NssmExe set $ServiceName Start SERVICE_AUTO_START 2>&1 | Out-Null
Write-Success "Auto-start enabled"

& $NssmExe set $ServiceName AppExit Default Restart 2>&1 | Out-Null
Write-Success "Auto-restart on exit enabled"

& $NssmExe set $ServiceName AppThrottle 30000 2>&1 | Out-Null
Write-Success "Shutdown threshold set"

& $NssmExe set $ServiceName AppPriority NORMAL_PRIORITY_CLASS 2>&1 | Out-Null
Write-Success "Process priority set"

$LogDir = "$env:APPDATA\Local\nssm\$ServiceName"
& $NssmExe set $ServiceName AppStdout "$LogDir\stdout.log" 2>&1 | Out-Null
& $NssmExe set $ServiceName AppStderr "$LogDir\stderr.log" 2>&1 | Out-Null
Write-Success "Logging configured"

# ============================================================================
# STEP 6: Start Service
# ============================================================================

Write-Header "Step 6: Starting Service"

Write-Info "Starting service..."
Start-Service -Name $ServiceName -ErrorAction SilentlyContinue
Start-Sleep -Seconds 3
Write-Success "Service started"

# ============================================================================
# STEP 7: Verify
# ============================================================================

Write-Header "Step 7: Verifying Service"

$service = Get-Service -Name $ServiceName
Write-Host "Service Name: $($service.Name)" -ForegroundColor Cyan
Write-Host "Display Name: $($service.DisplayName)" -ForegroundColor Cyan
Write-Host "Status: $($service.Status)" -ForegroundColor Cyan
Write-Host "Start Type: $($service.StartType)" -ForegroundColor Cyan

if ($service.Status -eq "Running") {
    Write-Success "Service is running!"
} else {
    Write-Error-Custom "Service is not running"
    Write-Info "Check logs at: $LogDir"
    exit 1
}

# ============================================================================
# STEP 8: Test
# ============================================================================

Write-Header "Step 8: Testing Application"

Write-Info "Waiting 5 seconds for app to start..."
Start-Sleep -Seconds 5

Write-Info "Testing http://localhost:5000..."
try {
    $response = Invoke-WebRequest -Uri "http://localhost:5000" -UseBasicParsing -TimeoutSec 5 -ErrorAction SilentlyContinue
    if ($response.StatusCode -eq 200 -or $response.StatusCode -eq 302) {
        Write-Success "Application is responding!"
    }
} catch {
    Write-Info "Application not responding yet (may still be starting)"
}

# ============================================================================
# SUMMARY
# ============================================================================

Write-Header "Setup Complete!"

Write-Host "Service Details:" -ForegroundColor Cyan
Write-Host "  Name: $ServiceName" -ForegroundColor White
Write-Host "  Display Name: $ServiceDisplayName" -ForegroundColor White
Write-Host "  Status: $($service.Status)" -ForegroundColor Green
Write-Host ""

Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "  1. Open browser: http://localhost:5000" -ForegroundColor White
Write-Host "  2. Complete setup" -ForegroundColor White
Write-Host ""

Write-Host "Manage Service:" -ForegroundColor Cyan
Write-Host "  .\manage-service.ps1 -Action status" -ForegroundColor White
Write-Host "  .\manage-service.ps1 -Action logs" -ForegroundColor White
Write-Host ""

Write-Success "tableau-admin-dashboard is running as a Windows Service!"
