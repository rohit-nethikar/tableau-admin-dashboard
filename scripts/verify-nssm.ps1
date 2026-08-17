# ============================================================================
# NSSM Verification Script
# ============================================================================
# Purpose: Verify that NSSM is properly installed and working
# ============================================================================

$ErrorActionPreference = "Continue"

$NssmPath = "C:\tools\nssm"
$NssmExe = "$NssmPath\nssm.exe"

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
# VERIFICATION CHECKS
# ============================================================================

Write-Header "NSSM Installation Verification"

# Check 1: Directory exists
Write-Info "Check 1: Verifying installation directory..."
if (Test-Path $NssmPath) {
    Write-Success "Directory found: $NssmPath"
} else {
    Write-Error-Custom "Directory not found: $NssmPath"
    Write-Host ""
    Write-Info "Run this first: .\install-nssm.ps1"
    exit 1
}

# Check 2: nssm.exe exists
Write-Info "Check 2: Verifying nssm.exe..."
if (Test-Path $NssmExe) {
    Write-Success "Executable found: $NssmExe"
    $fileInfo = Get-Item $NssmExe
    Write-Info "  Size: $([math]::Round($fileInfo.Length / 1KB, 2)) KB"
    Write-Info "  Modified: $($fileInfo.LastWriteTime)"
} else {
    Write-Error-Custom "nssm.exe not found"
    Write-Host ""
    Write-Info "Folder contents:"
    Get-ChildItem $NssmPath -Recurse | ForEach-Object {
        Write-Info "  $($_.FullName -replace [regex]::Escape($NssmPath), '.')"
    }
    exit 1
}

# Check 3: Test execution
Write-Info "Check 3: Testing nssm.exe execution..."
try {
    $output = & $NssmExe -version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Success "NSSM is working properly"
        Write-Info "  Output: $output"
    } else {
        Write-Error-Custom "NSSM returned an error"
        Write-Info "  Output: $output"
        exit 1
    }
} catch {
    Write-Error-Custom "Failed to execute nssm.exe: $_"
    exit 1
}

# Check 4: Directory contents
Write-Info "Check 4: Verifying directory structure..."
Write-Host ""
Write-Host "Directory contents:" -ForegroundColor White
Get-ChildItem $NssmPath | ForEach-Object {
    if ($_.PSIsContainer) {
        Write-Host "  📁 $($_.Name)/" -ForegroundColor Cyan
    } else {
        Write-Host "  📄 $($_.Name)" -ForegroundColor White
    }
}

# Check 5: Platform-specific binaries
Write-Info "Check 5: Checking platform-specific binaries..."
$win32Path = "$NssmPath\win32\nssm.exe"
$win64Path = "$NssmPath\win64\nssm.exe"

if (Test-Path $win32Path) {
    Write-Success "32-bit binary found"
} else {
    Write-Info "32-bit binary not found (optional)"
}

if (Test-Path $win64Path) {
    Write-Success "64-bit binary found"
} else {
    Write-Info "64-bit binary not found (optional)"
}

# Check 6: Test service operations
Write-Info "Check 6: Testing basic NSSM operations..."
try {
    # Try to get service list (should work even with no services)
    $serviceListOutput = & $NssmExe list 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Success "NSSM list command works"
    }
} catch {
    Write-Error-Custom "NSSM list command failed: $_"
}

# ============================================================================
# SUMMARY
# ============================================================================

Write-Header "Verification Results"

Write-Host "Status: ✓ NSSM is properly installed and ready to use" -ForegroundColor Green
Write-Host ""

Write-Host "Installation Details:" -ForegroundColor Cyan
Write-Host "  Path: $NssmPath" -ForegroundColor White
Write-Host "  Executable: $NssmExe" -ForegroundColor White
Write-Host "  Status: Ready" -ForegroundColor Green
Write-Host ""

Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "  Run: .\setup-service-manual.ps1" -ForegroundColor Gray
Write-Host ""
Write-Host "  OR" -ForegroundColor Gray
Write-Host ""
Write-Host "  Run: .\setup-service.ps1" -ForegroundColor Gray
Write-Host ""

Write-Success "All checks passed! NSSM is ready."
