# ============================================================================
# NSSM Download and Installation Script
# ============================================================================
# Purpose: Download NSSM from GitHub and extract to C:\tools\nssm\
# This script handles the complete NSSM setup process
# ============================================================================

$ErrorActionPreference = "Stop"

# Configuration
$ToolsPath = "C:\tools"
$NssmPath = "$ToolsPath\nssm"
$NssmZipFile = "$ToolsPath\nssm-download.zip"

# GitHub Release URL (latest stable)
$GithubUrl = "https://github.com/nssm-service-manager/nssm/releases/download/2.24-101-g897c7ad/nssm-2.24-101-g897c7ad.zip"

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
# STEP 1: Create Tools Directory
# ============================================================================

Write-Header "NSSM Installation Script"

Write-Info "Creating tools directory if it doesn't exist..."

if (-not (Test-Path $ToolsPath)) {
    try {
        New-Item -ItemType Directory -Path $ToolsPath -Force | Out-Null
        Write-Success "Created: $ToolsPath"
    } catch {
        Write-Error-Custom "Failed to create directory: $_"
        exit 1
    }
} else {
    Write-Success "Tools directory already exists: $ToolsPath"
}

# ============================================================================
# STEP 2: Download NSSM
# ============================================================================

Write-Header "Step 1: Downloading NSSM"

Write-Info "URL: $GithubUrl"
Write-Info "Destination: $NssmZipFile"
Write-Info "This may take 1-2 minutes..."

try {
    # Download with progress
    Write-Host ""
    $ProgressPreference = 'SilentlyContinue'
    Invoke-WebRequest -Uri $GithubUrl -OutFile $NssmZipFile -UseBasicParsing

    # Verify file was downloaded
    if (Test-Path $NssmZipFile) {
        $fileSize = (Get-Item $NssmZipFile).Length / 1MB
        Write-Success "Downloaded successfully ($([math]::Round($fileSize, 2)) MB)"
    } else {
        Write-Error-Custom "Download failed - file not found"
        exit 1
    }
} catch {
    Write-Error-Custom "Failed to download NSSM: $_"
    Write-Info "Troubleshooting:"
    Write-Info "1. Check your internet connection"
    Write-Info "2. Try the URL manually in a browser: $GithubUrl"
    Write-Info "3. If GitHub is blocked, try the alternative: https://nssm.cc/download"
    exit 1
}

# ============================================================================
# STEP 3: Clean Up Existing Installation
# ============================================================================

Write-Header "Step 2: Preparing Installation Directory"

if (Test-Path $NssmPath) {
    Write-Info "Existing NSSM directory found, backing up..."
    $backupPath = "$NssmPath.backup.$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    try {
        Rename-Item -Path $NssmPath -NewName $backupPath -Force
        Write-Success "Backed up to: $backupPath"
    } catch {
        Write-Error-Custom "Failed to backup existing installation: $_"
        Write-Info "Trying to remove instead..."
        Remove-Item -Path $NssmPath -Recurse -Force -ErrorAction SilentlyContinue
    }
}

# Create fresh nssm directory
try {
    New-Item -ItemType Directory -Path $NssmPath -Force | Out-Null
    Write-Success "Created fresh directory: $NssmPath"
} catch {
    Write-Error-Custom "Failed to create directory: $_"
    exit 1
}

# ============================================================================
# STEP 4: Extract NSSM
# ============================================================================

Write-Header "Step 3: Extracting NSSM"

Write-Info "Extracting $NssmZipFile..."
Write-Info "This may take 30 seconds..."

try {
    Expand-Archive -Path $NssmZipFile -DestinationPath $ToolsPath -Force
    Write-Success "Extraction completed"
} catch {
    Write-Error-Custom "Failed to extract: $_"
    exit 1
}

# ============================================================================
# STEP 5: Organize Files
# ============================================================================

Write-Header "Step 4: Organizing Files"

Write-Info "Finding and organizing NSSM files..."

# Look for extracted folder
$extractedFolders = Get-ChildItem -Path $ToolsPath -Directory -Name | Where-Object { $_ -match "nssm.*" -and $_ -ne "nssm" }

if ($extractedFolders) {
    $sourcePath = "$ToolsPath\$($extractedFolders[0])"
    Write-Info "Found extracted folder: $sourcePath"

    # Move contents to nssm folder
    try {
        Get-ChildItem -Path $sourcePath | Move-Item -Destination $NssmPath -Force
        Write-Success "Files moved to: $NssmPath"

        # Remove empty extracted folder
        Remove-Item -Path $sourcePath -Force -ErrorAction SilentlyContinue
        Write-Success "Cleaned up extracted folder"
    } catch {
        Write-Error-Custom "Failed to organize files: $_"
        exit 1
    }
}

# ============================================================================
# STEP 6: Verify Installation
# ============================================================================

Write-Header "Step 5: Verifying Installation"

$NssmExe = "$NssmPath\nssm.exe"

# Check if nssm.exe exists in root
if (Test-Path $NssmExe) {
    Write-Success "nssm.exe found in: $NssmPath"
} else {
    # Check if it's in win64 folder
    $NssmInWin64 = "$NssmPath\win64\nssm.exe"
    if (Test-Path $NssmInWin64) {
        Write-Info "Found nssm.exe in win64 folder, copying to root..."
        Copy-Item -Path $NssmInWin64 -Destination $NssmExe -Force
        Write-Success "nssm.exe copied to: $NssmPath"
    } else {
        Write-Error-Custom "nssm.exe not found in expected locations"
        Write-Info "Folder contents:"
        Get-ChildItem $NssmPath -Recurse | ForEach-Object {
            Write-Info "  $($_.FullName -replace [regex]::Escape($NssmPath), '.')"
        }
        exit 1
    }
}

# Test NSSM executable
Write-Info "Testing nssm.exe..."
try {
    $output = & $NssmExe -version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Success "NSSM is working: $output"
    } else {
        Write-Error-Custom "NSSM test failed"
        exit 1
    }
} catch {
    Write-Error-Custom "Failed to execute nssm.exe: $_"
    exit 1
}

# ============================================================================
# STEP 7: Cleanup
# ============================================================================

Write-Header "Step 6: Cleanup"

# Remove downloaded zip file
if (Test-Path $NssmZipFile) {
    Write-Info "Removing temporary zip file..."
    Remove-Item -Path $NssmZipFile -Force
    Write-Success "Cleaned up: $NssmZipFile"
}

# ============================================================================
# SUMMARY
# ============================================================================

Write-Header "Installation Complete!"

Write-Host "NSSM Installation Summary:" -ForegroundColor Cyan
Write-Host "  Installation Path: $NssmPath" -ForegroundColor White
Write-Host "  Executable: $NssmExe" -ForegroundColor White
Write-Host "  Status: ✓ Ready" -ForegroundColor Green
Write-Host ""

Write-Host "Directory Structure:" -ForegroundColor Cyan
Get-ChildItem $NssmPath -Directory | ForEach-Object {
    Write-Host "  📁 $($_.Name)" -ForegroundColor White
}
Write-Host "  📄 nssm.exe" -ForegroundColor White

Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "  1. Run the service setup script:" -ForegroundColor White
Write-Host "     .\setup-service-manual.ps1" -ForegroundColor Gray
Write-Host ""
Write-Host "  OR use the automatic setup script:" -ForegroundColor White
Write-Host "     .\setup-service.ps1" -ForegroundColor Gray
Write-Host ""

Write-Success "NSSM is ready to use!"
