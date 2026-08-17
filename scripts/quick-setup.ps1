# ============================================================================
# Quick NSSM Download & Service Setup (Manual Fallback)
# ============================================================================

$DashboardPath = "C:\Users\m239012\OneDrive - Mayo Clinic\GitHub_claude\tableau-admin-dashboard"

Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "NSSM Quick Setup - Fallback Method" -ForegroundColor Cyan
Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Step 1: Manual download
Write-Host "STEP 1: Manual NSSM Download" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Open your browser to:" -ForegroundColor White
Write-Host "   https://nssm.cc/download" -ForegroundColor Cyan
Write-Host ""
Write-Host "2. Click on the latest version link" -ForegroundColor White
Write-Host "3. Save the ZIP file" -ForegroundColor White
Write-Host "4. Extract to: C:\tools\nssm\" -ForegroundColor Cyan
Write-Host ""
Write-Host "5. When done, come back and press ENTER..." -ForegroundColor Green
Read-Host "Press ENTER to continue"

Write-Host ""
Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "STEP 2: Verifying NSSM Installation" -ForegroundColor Cyan
Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$NssmExe = "C:\tools\nssm\nssm.exe"

if (Test-Path $NssmExe) {
    Write-Host "✓ NSSM found at: $NssmExe" -ForegroundColor Green
} else {
    # Try to find it in win64 folder
    $NssmInWin64 = "C:\tools\nssm\win64\nssm.exe"
    if (Test-Path $NssmInWin64) {
        Write-Host "✓ Found nssm.exe in win64 folder" -ForegroundColor Green
        Write-Host "  Copying to main directory..." -ForegroundColor Yellow
        Copy-Item -Path $NssmInWin64 -Destination $NssmExe -Force
        Write-Host "✓ Copied successfully" -ForegroundColor Green
    } else {
        Write-Host "✗ NSSM not found" -ForegroundColor Red
        Write-Host ""
        Write-Host "Make sure to:" -ForegroundColor Yellow
        Write-Host "  1. Extract NSSM ZIP to: C:\tools\nssm\" -ForegroundColor White
        Write-Host "  2. The folder should contain nssm.exe (or win64\nssm.exe)" -ForegroundColor White
        exit 1
    }
}

Write-Host ""
Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "STEP 3: Installing Service" -ForegroundColor Cyan
Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Check admin
$isAdmin = ([Security.Principal.WindowsIdentity]::GetCurrent()).Groups -contains 'S-1-5-32-544'
if (-not $isAdmin) {
    Write-Host "✗ This script requires Administrator privileges" -ForegroundColor Red
    Write-Host "  Please run PowerShell as Administrator and try again" -ForegroundColor Yellow
    exit 1
}

Write-Host "✓ Running as Administrator" -ForegroundColor Green
Write-Host ""

# Create batch wrapper
$RunServiceBat = "$DashboardPath\run_service.bat"
$BatchScriptContent = @"
@echo off
cd /d "$DashboardPath"
call .venv\Scripts\activate.bat
python app.py
"@

Write-Host "Creating service wrapper..." -ForegroundColor Yellow
Set-Content -Path $RunServiceBat -Value $BatchScriptContent -Encoding ASCII -Force
Write-Host "✓ Service wrapper created" -ForegroundColor Green
Write-Host ""

# Remove existing service
$ServiceName = "TableauAdminDash"
if (Get-Service -Name $ServiceName -ErrorAction SilentlyContinue) {
    Write-Host "Found existing service, removing..." -ForegroundColor Yellow
    Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    & $NssmExe remove $ServiceName confirm 2>&1 | Out-Null
    Start-Sleep -Seconds 2
}

# Install service
Write-Host "Installing service..." -ForegroundColor Yellow
& $NssmExe install $ServiceName "`"$RunServiceBat`"" 2>&1 | Out-Null

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Service installed" -ForegroundColor Green
} else {
    Write-Host "✗ Service installation failed" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Configure service
Write-Host "Configuring service..." -ForegroundColor Yellow
& $NssmExe set $ServiceName DisplayName "Tableau Admin Dashboard" 2>&1 | Out-Null
& $NssmExe set $ServiceName Start SERVICE_AUTO_START 2>&1 | Out-Null
& $NssmExe set $ServiceName AppExit Default Restart 2>&1 | Out-Null
& $NssmExe set $ServiceName AppThrottle 30000 2>&1 | Out-Null
Write-Host "✓ Service configured" -ForegroundColor Green
Write-Host ""

# Start service
Write-Host "Starting service..." -ForegroundColor Yellow
Start-Service -Name $ServiceName -ErrorAction SilentlyContinue
Start-Sleep -Seconds 3

$service = Get-Service -Name $ServiceName
if ($service.Status -eq "Running") {
    Write-Host "✓ Service is running" -ForegroundColor Green
} else {
    Write-Host "⚠ Service is not running yet" -ForegroundColor Yellow
    Write-Host "  Waiting 5 more seconds..." -ForegroundColor Gray
    Start-Sleep -Seconds 5
}

Write-Host ""
Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

Write-Host "Service Details:" -ForegroundColor Cyan
Write-Host "  Name: $ServiceName" -ForegroundColor White
Write-Host "  Status: $($(Get-Service $ServiceName).Status)" -ForegroundColor White
Write-Host "  Auto-start: Enabled" -ForegroundColor White
Write-Host ""

Write-Host "Access Dashboard:" -ForegroundColor Cyan
Write-Host "  http://localhost:5000" -ForegroundColor White
Write-Host ""

Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "  1. Open browser: http://localhost:5000" -ForegroundColor Gray
Write-Host "  2. Check service: .\manage-service.ps1 -Action status" -ForegroundColor Gray
Write-Host "  3. View logs: .\manage-service.ps1 -Action logs -Follow" -ForegroundColor Gray
Write-Host ""

Write-Host "✓ tableau-admin-dashboard is now running as a Windows Service!" -ForegroundColor Green
