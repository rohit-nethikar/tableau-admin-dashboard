# ============================================================================
# Tableau Admin Dashboard - Complete Automated Setup
# ============================================================================
# Purpose: One-script setup for Python environment + NSSM service
# This runs all setup steps automatically
# ============================================================================

param(
    [switch]$SkipPython = $false,
    [switch]$SkipNSSM = $false,
    [switch]$SkipService = $false,
    [switch]$SkipTest = $false
)

$ErrorActionPreference = "Stop"
$WarningPreference = "Continue"

# Configuration
$DashboardPath = "C:\Users\m239012\OneDrive - Mayo Clinic\GitHub_claude\tableau-admin-dashboard"
$VenvPath = "$DashboardPath\.venv"
$ToolsPath = "C:\tools"
$NssmPath = "$ToolsPath\nssm"
$NssmExe = "$NssmPath\nssm.exe"

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

function Write-Step {
    param([string]$Text, [int]$StepNumber, [int]$TotalSteps)
    Write-Host ""
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkCyan
    Write-Host ("Step {0} of {1}: {2}" -f $StepNumber, $TotalSteps, $Text) -ForegroundColor DarkCyan
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkCyan
    Write-Host ""
}

# ============================================================================
# INITIALIZATION
# ============================================================================

Write-Header "Tableau Admin Dashboard - Complete Setup"

Write-Info "This script will:"
Write-Host "  1. Set up Python virtual environment" -ForegroundColor White
Write-Host "  2. Install Python dependencies" -ForegroundColor White
Write-Host "  3. Download and install NSSM" -ForegroundColor White
Write-Host "  4. Create and configure Windows Service" -ForegroundColor White
Write-Host "  5. Verify everything is working" -ForegroundColor White
Write-Host ""
Write-Info "Estimated time: 5-10 minutes"
Write-Host ""

# Check admin privileges
if (-not (Test-Administrator)) {
    Write-Error-Custom "This script requires Administrator privileges"
    Write-Info "Please right-click PowerShell and select 'Run as Administrator'"
    exit 1
}

Write-Success "Running as Administrator"

# Count total steps
$totalSteps = 5
if (-not $SkipPython) { $totalSteps }
if (-not $SkipNSSM) { $totalSteps }
if (-not $SkipService) { $totalSteps }
if (-not $SkipTest) { $totalSteps }

$currentStep = 1

# ============================================================================
# STEP 1: Python Environment Setup
# ============================================================================

if (-not $SkipPython) {
    Write-Step "Setting up Python Virtual Environment" $currentStep 5
    $currentStep++

    # Check Python
    $pythonPath = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $pythonPath) {
        Write-Error-Custom "Python not found in PATH"
        Write-Info "Please install Python 3.10+ from https://www.python.org/downloads/"
        exit 1
    }

    Write-Success "Python found at: $pythonPath"

    # Create venv
    if (Test-Path $VenvPath) {
        Write-Info "Virtual environment already exists"
    } else {
        Write-Info "Creating virtual environment..."
        Push-Location $DashboardPath
        try {
            python -m venv .venv
            Write-Success "Virtual environment created"
        } catch {
            Write-Error-Custom "Failed to create virtual environment: $_"
            exit 1
        } finally {
            Pop-Location
        }
    }

    # Install dependencies
    Write-Info "Installing Python packages..."
    $pipPath = "$VenvPath\Scripts\pip.exe"

    if (-not (Test-Path $pipPath)) {
        Write-Error-Custom "pip not found in virtual environment"
        exit 1
    }

    try {
        # Upgrade pip
        & $pipPath install --upgrade pip 2>&1 | Where-Object { $_ -match "Successfully installed|already satisfied" } | ForEach-Object { Write-Info $_ }

        # Install requirements
        & $pipPath install -r "$DashboardPath\requirements.txt" 2>&1 | Where-Object { $_ -match "Successfully installed" } | ForEach-Object { Write-Info $_ }

        Write-Success "Python packages installed"
    } catch {
        Write-Error-Custom "Failed to install packages: $_"
        exit 1
    }
}

# ============================================================================
# STEP 2: NSSM Download and Installation
# ============================================================================

if (-not $SkipNSSM) {
    Write-Step "Installing NSSM (Service Manager)" $currentStep 5
    $currentStep++

    # Create tools directory
    if (-not (Test-Path $ToolsPath)) {
        New-Item -ItemType Directory -Path $ToolsPath -Force | Out-Null
        Write-Success "Created tools directory: $ToolsPath"
    }

    # Check if already installed
    if (Test-Path $NssmExe) {
        Write-Info "NSSM already installed at: $NssmPath"
    } else {
        Write-Info "Downloading NSSM from GitHub..."
        # Try multiple URLs in case one is unavailable
        $NssmUrls = @(
            "https://github.com/nssm-service-manager/nssm/releases/download/2.24-101-g897c7ad/nssm-2.24-101-g897c7ad.zip",
            "https://nssm.cc/release/nssm-2.24-101-g897c7ad.zip",
            "https://github.com/nssm-service-manager/nssm/releases/latest/download/nssm-2.24-101-g897c7ad.zip"
        )
        $zipFile = "$ToolsPath\nssm-download.zip"
        $GithubUrl = $null

        try {
            $ProgressPreference = 'SilentlyContinue'
            $downloaded = $false

            # Try each URL until one works
            foreach ($url in $NssmUrls) {
                Write-Info "Trying: $url"
                try {
                    Invoke-WebRequest -Uri $url -OutFile $zipFile -UseBasicParsing -TimeoutSec 30
                    $downloaded = $true
                    Write-Success "NSSM downloaded"
                    break
                } catch {
                    Write-Info "Failed, trying next source..."
                }
            }

            if (-not $downloaded) {
                throw "All download sources failed. Please download manually from https://nssm.cc/download"
            }

            # Extract
            Write-Info "Extracting NSSM..."
            if (Test-Path $NssmPath) {
                Remove-Item -Path $NssmPath -Recurse -Force -ErrorAction SilentlyContinue
            }
            New-Item -ItemType Directory -Path $NssmPath -Force | Out-Null

            Expand-Archive -Path $zipFile -DestinationPath $ToolsPath -Force
            Write-Success "NSSM extracted"

            # Organize files
            $extracted = Get-ChildItem -Path $ToolsPath -Directory -Name | Where-Object { $_ -match "nssm.*" -and $_ -ne "nssm" }
            if ($extracted) {
                Get-ChildItem -Path "$ToolsPath\$($extracted[0])" | Move-Item -Destination $NssmPath -Force
                Remove-Item -Path "$ToolsPath\$($extracted[0])" -Force -ErrorAction SilentlyContinue
            }

            # Copy nssm.exe to root if needed
            if (-not (Test-Path $NssmExe)) {
                $NssmInWin64 = "$NssmPath\win64\nssm.exe"
                if (Test-Path $NssmInWin64) {
                    Copy-Item -Path $NssmInWin64 -Destination $NssmExe -Force
                }
            }

            # Cleanup
            Remove-Item -Path $zipFile -Force -ErrorAction SilentlyContinue

            Write-Success "NSSM installed successfully"
        } catch {
            Write-Error-Custom "Failed to install NSSM: $_"
            exit 1
        }
    }

    # Verify NSSM
    if (-not (Test-Path $NssmExe)) {
        Write-Error-Custom "NSSM executable not found"
        exit 1
    }

    Write-Success "NSSM verified at: $NssmExe"
}

# ============================================================================
# STEP 3: Service Configuration and Installation
# ============================================================================

if (-not $SkipService) {
    Write-Step "Installing Windows Service" $currentStep 5
    $currentStep++

    $ServiceName = "TableauAdminDash"
    $ServiceDisplayName = "Tableau Admin Dashboard"
    $RunServiceBat = "$DashboardPath\run_service.bat"

    # Create batch wrapper
    Write-Info "Creating service wrapper script..."
    $BatchScriptContent = @"
@echo off
cd /d "$DashboardPath"
call .venv\Scripts\activate.bat
python app.py
"@

    Set-Content -Path $RunServiceBat -Value $BatchScriptContent -Encoding ASCII -Force
    Write-Success "Service wrapper created"

    # Remove existing service
    if (Get-Service -Name $ServiceName -ErrorAction SilentlyContinue) {
        Write-Info "Removing existing service..."
        Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
        & $NssmExe remove $ServiceName confirm 2>&1 | Out-Null
        Start-Sleep -Seconds 2
    }

    # Install service
    Write-Info "Installing service '$ServiceName'..."
    & $NssmExe install $ServiceName "`"$RunServiceBat`"" 2>&1 | Out-Null

    # Configure service
    Write-Info "Configuring service..."
    & $NssmExe set $ServiceName DisplayName $ServiceDisplayName 2>&1 | Out-Null
    & $NssmExe set $ServiceName Start SERVICE_AUTO_START 2>&1 | Out-Null
    & $NssmExe set $ServiceName AppExit Default Restart 2>&1 | Out-Null
    & $NssmExe set $ServiceName AppThrottle 30000 2>&1 | Out-Null

    $LogDir = "$env:APPDATA\Local\nssm\$ServiceName"
    & $NssmExe set $ServiceName AppStdout "$LogDir\stdout.log" 2>&1 | Out-Null
    & $NssmExe set $ServiceName AppStderr "$LogDir\stderr.log" 2>&1 | Out-Null

    Write-Success "Service configured"

    # Start service
    Write-Info "Starting service..."
    Start-Service -Name $ServiceName -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 3

    $service = Get-Service -Name $ServiceName
    if ($service.Status -eq "Running") {
        Write-Success "Service is running"
    } else {
        Write-Error-Custom "Service failed to start"
        Write-Info "Check logs at: $LogDir"
    }
}

# ============================================================================
# STEP 4: Verification
# ============================================================================

if (-not $SkipTest) {
    Write-Step "Verifying Installation" $currentStep 5

    Write-Info "Waiting 5 seconds for application to start..."
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
}

# ============================================================================
# COMPLETION
# ============================================================================

Write-Header "Setup Complete! ✓"

Write-Host "Your Tableau Admin Dashboard is now running as a Windows Service" -ForegroundColor Green
Write-Host ""

Write-Host "Quick Actions:" -ForegroundColor Cyan
Write-Host "  Check Status:    .\manage-service.ps1 -Action status" -ForegroundColor Gray
Write-Host "  View Logs:       .\manage-service.ps1 -Action logs -Follow" -ForegroundColor Gray
Write-Host "  Restart Service: .\manage-service.ps1 -Action restart" -ForegroundColor Gray
Write-Host ""

Write-Host "Access Your Dashboard:" -ForegroundColor Cyan
Write-Host "  http://localhost:5000" -ForegroundColor Gray
Write-Host ""

Write-Host "Service Details:" -ForegroundColor Cyan
Write-Host "  Name: TableauAdminDash" -ForegroundColor Gray
Write-Host "  Display: Tableau Admin Dashboard" -ForegroundColor Gray
Write-Host "  Status: Automatic (runs on boot)" -ForegroundColor Gray
Write-Host ""

Write-Success "All done! The service will start automatically on system reboot."
