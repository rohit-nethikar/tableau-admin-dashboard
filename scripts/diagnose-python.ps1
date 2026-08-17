# ============================================================================
# Python Environment Diagnostic Script
# ============================================================================
# Purpose: Diagnose and fix Python/venv issues
# ============================================================================

$ErrorActionPreference = "Continue"

$DashboardPath = "C:\Users\m239012\OneDrive - Mayo Clinic\GitHub_claude\tableau-admin-dashboard"
$VenvPath = "$DashboardPath\.venv"

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

Write-Header "Python Environment Diagnostic"

# ============================================================================
# CHECK 1: Python Installation
# ============================================================================

Write-Header "Step 1: Checking Python Installation"

$pythonPath = (Get-Command python -ErrorAction SilentlyContinue).Source
if ($pythonPath) {
    Write-Success "Python found at: $pythonPath"
} else {
    Write-Error-Custom "Python not found in PATH"
    Write-Info "Installing Python..."
    Write-Info "1. Download Python 3.10+ from https://www.python.org/downloads/"
    Write-Info "2. Run installer"
    Write-Info "3. ✓ CHECK 'Add Python to PATH' during installation"
    Write-Info "4. Restart PowerShell and try again"
    exit 1
}

# Get Python version
$pythonVersion = python --version 2>&1
Write-Info "Version: $pythonVersion"

# ============================================================================
# CHECK 2: Virtual Environment Existence
# ============================================================================

Write-Header "Step 2: Checking Virtual Environment"

if (Test-Path $VenvPath) {
    Write-Success "Virtual environment exists at: $VenvPath"

    # Check key files
    $activateScript = "$VenvPath\Scripts\activate.bat"
    $pipPath = "$VenvPath\Scripts\pip.exe"
    $pythonExe = "$VenvPath\Scripts\python.exe"

    Write-Info "Checking virtual environment files..."

    if (Test-Path $activateScript) {
        Write-Success "  ✓ activate.bat found"
    } else {
        Write-Error-Custom "  ✗ activate.bat NOT found"
    }

    if (Test-Path $pythonExe) {
        Write-Success "  ✓ python.exe found"
    } else {
        Write-Error-Custom "  ✗ python.exe NOT found - venv corrupted"
    }

    if (Test-Path $pipPath) {
        Write-Success "  ✓ pip.exe found"
    } else {
        Write-Error-Custom "  ✗ pip.exe NOT found - venv may be corrupted"
    }
} else {
    Write-Error-Custom "Virtual environment NOT found at: $VenvPath"
    Write-Info "Virtual environment needs to be created"
}

# ============================================================================
# CHECK 3: Directory Listing
# ============================================================================

Write-Header "Step 3: Virtual Environment Contents"

if (Test-Path $VenvPath) {
    Write-Info "Contents of .venv directory:"
    Get-ChildItem $VenvPath -Directory | ForEach-Object {
        Write-Host "  📁 $($_.Name)"
    }

    Write-Info ""
    Write-Info "Contents of .venv\Scripts directory:"
    Get-ChildItem "$VenvPath\Scripts" -File | Select-Object Name | ForEach-Object {
        Write-Host "    📄 $($_.Name)"
    }
}

# ============================================================================
# CHECK 4: Test Python in venv
# ============================================================================

Write-Header "Step 4: Testing Virtual Environment"

if (Test-Path "$VenvPath\Scripts\python.exe") {
    Write-Info "Testing Python in venv..."
    try {
        $output = & "$VenvPath\Scripts\python.exe" --version 2>&1
        Write-Success "Python version in venv: $output"
    } catch {
        Write-Error-Custom "Failed to run python.exe from venv: $_"
    }
}

if (Test-Path "$VenvPath\Scripts\pip.exe") {
    Write-Info "Testing pip in venv..."
    try {
        $output = & "$VenvPath\Scripts\pip.exe" --version 2>&1
        Write-Success "pip: $output"
    } catch {
        Write-Error-Custom "Failed to run pip.exe from venv: $_"
    }
}

# ============================================================================
# SOLUTION SUGGESTIONS
# ============================================================================

Write-Header "Diagnosis Complete"

Write-Host "If you see errors above, try these solutions:" -ForegroundColor Cyan
Write-Host ""

Write-Host "SOLUTION 1: Reset Virtual Environment (Recommended)" -ForegroundColor Yellow
Write-Host "  This will delete and recreate the venv from scratch:" -ForegroundColor White
Write-Host ""
Write-Host "  Step 1: Delete old venv" -ForegroundColor Gray
Write-Host "    Remove-Item -Path `"$VenvPath`" -Recurse -Force -ErrorAction SilentlyContinue" -ForegroundColor Gray
Write-Host ""
Write-Host "  Step 2: Recreate venv" -ForegroundColor Gray
Write-Host "    cd `"$DashboardPath`"" -ForegroundColor Gray
Write-Host "    python -m venv .venv" -ForegroundColor Gray
Write-Host ""
Write-Host "  Step 3: Verify pip works" -ForegroundColor Gray
Write-Host "    .\.venv\Scripts\pip --version" -ForegroundColor Gray
Write-Host ""
Write-Host "  Step 4: Install requirements" -ForegroundColor Gray
Write-Host "    .\.venv\Scripts\pip install -r requirements.txt" -ForegroundColor Gray
Write-Host ""

Write-Host "SOLUTION 2: Upgrade pip (Common Fix)" -ForegroundColor Yellow
Write-Host "  Open PowerShell as Administrator and run:" -ForegroundColor White
Write-Host ""
Write-Host "    cd `"$DashboardPath`"" -ForegroundColor Gray
Write-Host "    .\.venv\Scripts\python -m pip install --upgrade pip" -ForegroundColor Gray
Write-Host ""

Write-Host "SOLUTION 3: Reinstall Python" -ForegroundColor Yellow
Write-Host "  If Python installation is broken:" -ForegroundColor White
Write-Host ""
Write-Host "  1. Uninstall Python from Windows Settings" -ForegroundColor Gray
Write-Host "  2. Download Python 3.10+ from https://www.python.org/downloads/" -ForegroundColor Gray
Write-Host "  3. Run installer with 'Add Python to PATH' checked" -ForegroundColor Gray
Write-Host "  4. Restart PowerShell" -ForegroundColor Gray
Write-Host "  5. Try setup again: .\setup-environment.ps1 -Reset" -ForegroundColor Gray
Write-Host ""

Write-Host "SOLUTION 4: Manual Setup (If scripts fail)" -ForegroundColor Yellow
Write-Host "  Run these commands manually:" -ForegroundColor White
Write-Host ""
Write-Host "    cd `"$DashboardPath`"" -ForegroundColor Gray
Write-Host "    python -m venv .venv" -ForegroundColor Gray
Write-Host "    .\.venv\Scripts\activate.bat" -ForegroundColor Gray
Write-Host "    pip install --upgrade pip" -ForegroundColor Gray
Write-Host "    pip install -r requirements.txt" -ForegroundColor Gray
Write-Host ""

Write-Host ""
Write-Info "After trying a solution, re-run this diagnostic to verify:"
Write-Host "  .\diagnose-python.ps1" -ForegroundColor Cyan
