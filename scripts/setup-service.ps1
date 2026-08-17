# ============================================================================
# Tableau Admin Dashboard - NSSM Service Setup Script
# ============================================================================
# Purpose: Complete automated setup of tableau-admin-dashboard as Windows Service
# Prerequisites: Run as Administrator
# ============================================================================

param(
    [switch]$SkipNSSMDownload = $false,
    [switch]$Uninstall = $false
)

# ============================================================================
# CONFIGURATION
# ============================================================================

$ErrorActionPreference = "Stop"
$WarningPreference = "Continue"

# Paths
$DashboardPath = "C:\Users\m239012\OneDrive - Mayo Clinic\GitHub_claude\tableau-admin-dashboard"
$ToolsPath = "C:\tools"
$NSsrPath = "$ToolsPath\nssm"
$NSsmExe = "$NssmPath\nssm.exe"
$RunServiceBat = "$DashboardPath\run_service.bat"
$NSsmLogPath = "$env:APPDATA\Local\nssm\TableauAdminDash"

# Service Configuration
$ServiceName = "TableauAdminDash"
$ServiceDisplayName = "Tableau Admin Dashboard"
$ServiceDescription = "Local governance app for Tableau Server administration"

# NSSM Download URLs (64-bit)
# Using GitHub releases for reliability
$NssmDownloadUrl = "https://github.com/nssm-service-manager/nssm/releases/download/2.24-101-g897c7ad/nssm-2.24-101-g897c7ad.zip"
$NssmZipFile = "$ToolsPath\nssm-2.24.zip"

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
# MAIN SCRIPT
# ============================================================================

Write-Header "Tableau Admin Dashboard - Windows Service Setup"

# Check if running as Administrator
if (-not (Test-Administrator)) {
    Write-Error-Custom "This script must be run as Administrator"
    Write-Info "Please right-click PowerShell and select 'Run as Administrator'"
    exit 1
}

Write-Success "Running as Administrator"

# ============================================================================
# UNINSTALL MODE
# ============================================================================

if ($Uninstall) {
    Write-Header "Uninstalling Service"

    # Check if service exists
    if (Get-Service -Name $ServiceName -ErrorAction SilentlyContinue) {
        Write-Info "Stopping service..."
        Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2

        Write-Info "Removing service..."
        & $NssmExe remove $ServiceName confirm

        if ($LASTEXITCODE -eq 0) {
            Write-Success "Service uninstalled successfully"
        } else {
            Write-Error-Custom "Failed to uninstall service"
            exit 1
        }
    } else {
        Write-Info "Service not found, nothing to uninstall"
    }

    exit 0
}

# ============================================================================
# DOWNLOAD AND EXTRACT NSSM
# ============================================================================

Write-Header "Step 1: Setting up NSSM (Non-Sucking Service Manager)"

# Create tools directory if it doesn't exist
if (-not (Test-Path $ToolsPath)) {
    Write-Info "Creating tools directory: $ToolsPath"
    New-Item -ItemType Directory -Path $ToolsPath -Force | Out-Null
}

# Check if NSSM already exists
if (Test-Path $NssmExe) {
    Write-Success "NSSM already installed at: $NssmPath"
} else {
    if ($SkipNSSMDownload) {
        Write-Error-Custom "NSSM not found and download skipped. Please download manually from https://nssm.cc/download"
        exit 1
    }

    Write-Info "Downloading NSSM from: $NssmDownloadUrl"
    try {
        # Download with progress
        $ProgressPreference = 'SilentlyContinue'
        Invoke-WebRequest -Uri $NssmDownloadUrl -OutFile $NssmZipFile -UseBasicParsing
        Write-Success "NSSM downloaded"

        Write-Info "Extracting NSSM to: $NssmPath"
        Expand-Archive -Path $NssmZipFile -DestinationPath $ToolsPath -Force

        # Rename extracted folder to 'nssm'
        $ExtractedFolder = Get-ChildItem -Path $ToolsPath -Name "nssm-*" | Select-Object -First 1
        if ($ExtractedFolder) {
            Rename-Item -Path "$ToolsPath\$ExtractedFolder" -NewName "nssm" -Force
        }

        # Copy nssm.exe to root of nssm folder if needed
        if (-not (Test-Path $NssmExe)) {
            $NssmInWin64 = "$NssmPath\win64\nssm.exe"
            if (Test-Path $NssmInWin64) {
                Copy-Item -Path $NssmInWin64 -Destination $NssmExe -Force
                Write-Success "Extracted nssm.exe"
            }
        }

        Write-Success "NSSM extracted successfully"
    } catch {
        Write-Error-Custom "Failed to download/extract NSSM: $_"
        exit 1
    }
}

# Verify NSSM executable exists
if (-not (Test-Path $NssmExe)) {
    Write-Error-Custom "NSSM executable not found at: $NssmExe"
    exit 1
}

Write-Success "NSSM ready at: $NssmExe"

# ============================================================================
# CREATE BATCH WRAPPER SCRIPT
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
try {
    Set-Content -Path $RunServiceBat -Value $BatchScriptContent -Encoding ASCII -Force
    Write-Success "Batch wrapper script created"
} catch {
    Write-Error-Custom "Failed to create batch wrapper: $_"
    exit 1
}

# Test that the batch file is valid
if (-not (Test-Path $RunServiceBat)) {
    Write-Error-Custom "Batch script not found after creation"
    exit 1
}

Write-Success "Wrapper script ready at: $RunServiceBat"

# ============================================================================
# UNINSTALL EXISTING SERVICE (if present)
# ============================================================================

Write-Header "Step 3: Checking for Existing Service"

if (Get-Service -Name $ServiceName -ErrorAction SilentlyContinue) {
    Write-Info "Service '$ServiceName' already exists, removing old installation..."

    try {
        Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
        & $NssmExe remove $ServiceName confirm 2>&1 | Out-Null

        # Wait for service to be removed
        Start-Sleep -Seconds 3
        Write-Success "Old service removed"
    } catch {
        Write-Error-Custom "Failed to remove old service: $_"
        exit 1
    }
} else {
    Write-Success "No existing service found"
}

# ============================================================================
# INSTALL SERVICE
# ============================================================================

Write-Header "Step 4: Installing Windows Service"

Write-Info "Installing service: $ServiceName"
Write-Info "Service will run: $RunServiceBat"

try {
    $output = & $NssmExe install $ServiceName "`"$RunServiceBat`"" 2>&1

    if ($LASTEXITCODE -eq 0) {
        Write-Success "Service installed successfully"
    } else {
        Write-Error-Custom "NSSM install failed: $output"
        exit 1
    }
} catch {
    Write-Error-Custom "Failed to install service: $_"
    exit 1
}

# ============================================================================
# CONFIGURE SERVICE
# ============================================================================

Write-Header "Step 5: Configuring Service"

Write-Info "Configuring service parameters..."

# Set display name
& $NssmExe set $ServiceName DisplayName $ServiceDisplayName 2>&1 | Out-Null
Write-Success "Display name set"

# Set description
& $NssmExe set $ServiceName Description $ServiceDescription 2>&1 | Out-Null
Write-Success "Description set"

# Set startup type to Automatic
& $NssmExe set $ServiceName Start SERVICE_AUTO_START 2>&1 | Out-Null
Write-Success "Startup type set to Automatic"

# Set restart behavior
& $NssmExe set $ServiceName AppExit Default Restart 2>&1 | Out-Null
Write-Success "Auto-restart on exit enabled"

# Set shutdown threshold (30 seconds)
& $NssmExe set $ServiceName AppThrottle 30000 2>&1 | Out-Null
Write-Success "Shutdown threshold set to 30 seconds"

# Set app priority
& $NssmExe set $ServiceName AppPriority NORMAL_PRIORITY_CLASS 2>&1 | Out-Null
Write-Success "Process priority set"

# Set output/error redirection for logging
$LogDir = "$env:APPDATA\Local\nssm\$ServiceName"
& $NssmExe set $ServiceName AppStdout "$LogDir\stdout.log" 2>&1 | Out-Null
& $NssmExe set $ServiceName AppStderr "$LogDir\stderr.log" 2>&1 | Out-Null
Write-Success "Logging configured to: $LogDir"

Write-Success "Service configuration complete"

# ============================================================================
# START SERVICE
# ============================================================================

Write-Header "Step 6: Starting Service"

Write-Info "Starting service '$ServiceName'..."
try {
    Start-Service -Name $ServiceName -ErrorAction Stop
    Start-Sleep -Seconds 3
    Write-Success "Service started"
} catch {
    Write-Error-Custom "Failed to start service: $_"
    Write-Info "Checking service status and logs..."
    & $NssmExe status $ServiceName
    exit 1
}

# ============================================================================
# VERIFY SERVICE
# ============================================================================

Write-Header "Step 7: Verifying Service"

$serviceStatus = Get-Service -Name $ServiceName
Write-Host "Service Name: $($serviceStatus.Name)" -ForegroundColor Cyan
Write-Host "Display Name: $($serviceStatus.DisplayName)" -ForegroundColor Cyan
Write-Host "Status: $($serviceStatus.Status)" -ForegroundColor Cyan
Write-Host "Start Type: $($serviceStatus.StartType)" -ForegroundColor Cyan

if ($serviceStatus.Status -eq "Running") {
    Write-Success "Service is running!"
} else {
    Write-Error-Custom "Service is not running"
    Write-Info "Checking logs at: $LogDir"
    if (Test-Path $LogDir) {
        Get-ChildItem $LogDir
    }
    exit 1
}

# ============================================================================
# TEST CONNECTIVITY
# ============================================================================

Write-Header "Step 8: Testing Application"

Write-Info "Waiting for application to become ready (5 seconds)..."
Start-Sleep -Seconds 5

Write-Info "Attempting to connect to http://localhost:5000..."
try {
    $response = Invoke-WebRequest -Uri "http://localhost:5000" -UseBasicParsing -TimeoutSec 5 -ErrorAction SilentlyContinue
    if ($response.StatusCode -eq 200 -or $response.StatusCode -eq 302) {
        Write-Success "Application is responding!"
        Write-Info "Open your browser to: http://localhost:5000"
    } else {
        Write-Info "Application returned status: $($response.StatusCode)"
    }
} catch {
    Write-Info "Could not connect to application yet (may still be starting)"
    Write-Info "Check logs at: $LogDir"
}

# ============================================================================
# SUMMARY
# ============================================================================

Write-Header "Setup Complete!"

Write-Host "Service Details:" -ForegroundColor Cyan
Write-Host "  Name: $ServiceName" -ForegroundColor White
Write-Host "  Display Name: $ServiceDisplayName" -ForegroundColor White
Write-Host "  Status: Running" -ForegroundColor Green
Write-Host "  Start Type: Automatic (starts on reboot)" -ForegroundColor Green
Write-Host ""

Write-Host "Useful Commands:" -ForegroundColor Cyan
Write-Host "  Start service:   Start-Service -Name $ServiceName" -ForegroundColor White
Write-Host "  Stop service:    Stop-Service -Name $ServiceName -Force" -ForegroundColor White
Write-Host "  Restart service: Restart-Service -Name $ServiceName" -ForegroundColor White
Write-Host "  Check status:    Get-Service -Name $ServiceName" -ForegroundColor White
Write-Host ""

Write-Host "View Logs:" -ForegroundColor Cyan
Write-Host "  Location: $LogDir" -ForegroundColor White
Write-Host "  Command:  Get-Content '$LogDir\stdout.log' -Wait" -ForegroundColor White
Write-Host ""

Write-Host "Manage Service (GUI):" -ForegroundColor Cyan
Write-Host "  Press: Win + R" -ForegroundColor White
Write-Host "  Type:  services.msc" -ForegroundColor White
Write-Host "  Find:  $ServiceDisplayName" -ForegroundColor White
Write-Host ""

Write-Host "Access Dashboard:" -ForegroundColor Cyan
Write-Host "  URL: http://localhost:5000" -ForegroundColor White
Write-Host ""

Write-Success "tableau-admin-dashboard is now running as a Windows Service!"
Write-Info "The service will automatically start on system reboot."
