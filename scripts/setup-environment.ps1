# ============================================================================
# Tableau Admin Dashboard - Python Environment Setup Script
# ============================================================================
# Purpose: Create virtual environment and install dependencies
# Prerequisites: Python 3.10+ must be installed
# ============================================================================

param(
    [switch]$Reset = $false
)

$ErrorActionPreference = "Stop"
$WarningPreference = "Continue"

# Configuration
$DashboardPath = "C:\Users\m239012\OneDrive - Mayo Clinic\GitHub_claude\tableau-admin-dashboard"
$VenvPath = "$DashboardPath\.venv"
$RequirementsFile = "$DashboardPath\requirements.txt"

# ============================================================================
# FUNCTIONS
# ============================================================================

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

Write-Header "Tableau Admin Dashboard - Python Environment Setup"

# Check if working directory exists
if (-not (Test-Path $DashboardPath)) {
    Write-Error-Custom "Dashboard directory not found: $DashboardPath"
    exit 1
}

Write-Success "Dashboard directory found: $DashboardPath"

# Check Python installation
Write-Header "Step 1: Checking Python Installation"

$pythonPath = (Get-Command python -ErrorAction SilentlyContinue).Source
if ($pythonPath) {
    Write-Success "Python found at: $pythonPath"
    $pythonVersion = python --version 2>&1
    Write-Info "Version: $pythonVersion"
} else {
    Write-Error-Custom "Python not found in PATH"
    Write-Info "Please install Python 3.10+ from https://www.python.org/downloads/"
    exit 1
}

# Verify Python version is 3.10+
$versionOutput = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
$major, $minor = $versionOutput -split '\.'
if ([int]$major -lt 3 -or ([int]$major -eq 3 -and [int]$minor -lt 10)) {
    Write-Error-Custom "Python 3.10+ required, found $versionOutput"
    exit 1
}

Write-Success "Python version is compatible"

# Check if requirements.txt exists
Write-Header "Step 2: Checking Dependencies"

if (-not (Test-Path $RequirementsFile)) {
    Write-Error-Custom "requirements.txt not found at: $RequirementsFile"
    exit 1
}

Write-Success "requirements.txt found"

# Handle virtual environment reset
if ($Reset) {
    Write-Header "Resetting Virtual Environment"

    if (Test-Path $VenvPath) {
        Write-Info "Removing existing virtual environment..."
        Remove-Item -Path $VenvPath -Recurse -Force -ErrorAction SilentlyContinue
        Write-Success "Old virtual environment removed"
    }
}

# Check if virtual environment exists
Write-Header "Step 3: Creating Virtual Environment"

if (Test-Path $VenvPath) {
    Write-Info "Virtual environment already exists at: $VenvPath"
    Write-Info "Virtual environment was previously created successfully"
} else {
    Write-Info "Creating new virtual environment..."
    Write-Info "This may take 1-2 minutes..."

    try {
        Push-Location $DashboardPath
        python -m venv .venv
        Pop-Location
        Write-Success "Virtual environment created"
    } catch {
        Write-Error-Custom "Failed to create virtual environment: $_"
        exit 1
    }
}

# Check if activation script exists
$activateScript = "$VenvPath\Scripts\activate.bat"
if (-not (Test-Path $activateScript)) {
    Write-Error-Custom "Virtual environment activation script not found"
    Write-Info "Virtual environment may be corrupted. Run with -Reset flag:"
    Write-Info "  .\setup-environment.ps1 -Reset"
    exit 1
}

Write-Success "Virtual environment is ready"

# ============================================================================
# Install dependencies
# ============================================================================

Write-Header "Step 4: Installing Dependencies"

Write-Info "Installing packages from requirements.txt..."
Write-Info "This may take several minutes depending on your internet connection..."
Write-Host ""

try {
    # Use the venv's pip directly
    $pipPath = "$VenvPath\Scripts\pip.exe"

    if (-not (Test-Path $pipPath)) {
        Write-Error-Custom "pip not found in virtual environment"
        exit 1
    }

    # Upgrade pip first
    Write-Info "Upgrading pip..."
    & $pipPath install --upgrade pip 2>&1 | ForEach-Object {
        if ($_ -match "Successfully installed|Requirement already satisfied") {
            Write-Success $_
        } elseif ($_ -match "WARNING|Error|error") {
            Write-Warning $_
        }
    }

    # Install requirements
    Write-Info "Installing requirements from requirements.txt..."
    $output = & $pipPath install -r $RequirementsFile 2>&1
    $output | ForEach-Object {
        if ($_ -match "Successfully installed") {
            Write-Success $_
        } elseif ($_ -match "Requirement already satisfied") {
            Write-Info $_
        } elseif ($_ -match "WARNING") {
            Write-Warning $_
        }
    }

    Write-Success "Dependencies installed successfully"
} catch {
    Write-Error-Custom "Failed to install dependencies: $_"
    exit 1
}

# ============================================================================
# Verify installation
# ============================================================================

Write-Header "Step 5: Verifying Installation"

try {
    # Activate venv and check imports
    $pythonCheck = @"
import sys
print(f"Python version: {sys.version}")
print(f"Virtual environment: {sys.prefix}")

# Try importing key modules
try:
    import flask
    print("✓ Flask installed")
except ImportError:
    print("✗ Flask not found")

try:
    import tableauserverclient
    print("✓ tableauserverclient installed")
except ImportError:
    print("✗ tableauserverclient not found")

try:
    import yaml
    print("✓ pyyaml installed")
except ImportError:
    print("✗ pyyaml not found")
"@

    $activateCmd = "& `"$activateScript`" > `$null 2>&1; python -c `"$pythonCheck`""
    $result = Invoke-Expression -Command $activateCmd

    Write-Host $result -ForegroundColor Cyan
    Write-Success "Installation verification complete"

} catch {
    Write-Error-Custom "Failed to verify installation: $_"
    exit 1
}

# ============================================================================
# Check configuration files
# ============================================================================

Write-Header "Step 6: Checking Configuration Files"

$configFile = "$DashboardPath\config.yaml"
$governanceFile = "$DashboardPath\governance.yaml"

if (Test-Path $configFile) {
    Write-Success "config.yaml found"
    Write-Info "Remember to configure server_url and site_name in config.yaml"
} else {
    Write-Error-Custom "config.yaml not found"
}

if (Test-Path $governanceFile) {
    Write-Success "governance.yaml found"
} else {
    Write-Error-Custom "governance.yaml not found"
}

# ============================================================================
# SUMMARY
# ============================================================================

Write-Header "Environment Setup Complete!"

Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Configure the application:" -ForegroundColor White
Write-Host "   - Edit config.yaml" -ForegroundColor Gray
Write-Host "   - Set server_url to your Tableau Server URL" -ForegroundColor Gray
Write-Host "   - Set site_name (leave empty for Default)" -ForegroundColor Gray
Write-Host ""

Write-Host "2. Review governance settings:" -ForegroundColor White
Write-Host "   - Edit governance.yaml" -ForegroundColor Gray
Write-Host "   - Adjust weights and thresholds as needed" -ForegroundColor Gray
Write-Host ""

Write-Host "3. Obtain a Tableau Personal Access Token:" -ForegroundColor White
Write-Host "   - Tableau Server → Account Menu → My Account Settings" -ForegroundColor Gray
Write-Host "   - Personal Access Tokens → Create new token" -ForegroundColor Gray
Write-Host ""

Write-Host "4. Test the application:" -ForegroundColor White
Write-Host "   - Run: cd `"$DashboardPath`"" -ForegroundColor Gray
Write-Host "   - Run: .\.venv\Scripts\activate" -ForegroundColor Gray
Write-Host "   - Run: python app.py" -ForegroundColor Gray
Write-Host "   - Open: http://localhost:5000" -ForegroundColor Gray
Write-Host ""

Write-Host "5. Set up as Windows Service:" -ForegroundColor White
Write-Host "   - Run: .\setup-service.ps1" -ForegroundColor Gray
Write-Host "   - (Requires Administrator privileges)" -ForegroundColor Gray
Write-Host ""

Write-Success "Python environment is ready!"
Write-Info "You can now proceed to service setup, or run the app manually for testing"
