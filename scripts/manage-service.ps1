# ============================================================================
# Tableau Admin Dashboard - Service Management Script
# ============================================================================
# Purpose: Quick commands to manage the Windows Service
# Usage: .\manage-service.ps1 -Action [start|stop|restart|status|logs|uninstall]
# ============================================================================

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("start", "stop", "restart", "status", "logs", "uninstall", "gui")]
    [string]$Action = "status",

    [switch]$Follow = $false
)

$ErrorActionPreference = "Stop"

# Configuration
$ServiceName = "TableauAdminDash"
$ServiceDisplayName = "Tableau Admin Dashboard"
$NssmPath = "C:\tools\nssm"
$NssmExe = "$NssmPath\nssm.exe"
$LogDir = "$env:APPDATA\Local\nssm\TableauAdminDash"

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
# ACTION HANDLERS
# ============================================================================

function Start-Service-Action {
    Write-Header "Starting Service"

    if (-not (Test-Administrator)) {
        Write-Error-Custom "This action requires Administrator privileges"
        exit 1
    }

    $service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if (-not $service) {
        Write-Error-Custom "Service '$ServiceName' not found. Run setup-service.ps1 first."
        exit 1
    }

    if ($service.Status -eq "Running") {
        Write-Info "Service is already running"
        return
    }

    Write-Info "Starting $ServiceDisplayName..."
    Start-Service -Name $ServiceName
    Start-Sleep -Seconds 2

    $service = Get-Service -Name $ServiceName
    if ($service.Status -eq "Running") {
        Write-Success "Service started successfully"
    } else {
        Write-Error-Custom "Failed to start service"
        exit 1
    }
}

function Stop-Service-Action {
    Write-Header "Stopping Service"

    if (-not (Test-Administrator)) {
        Write-Error-Custom "This action requires Administrator privileges"
        exit 1
    }

    $service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if (-not $service) {
        Write-Error-Custom "Service '$ServiceName' not found"
        exit 1
    }

    if ($service.Status -eq "Stopped") {
        Write-Info "Service is already stopped"
        return
    }

    Write-Info "Stopping $ServiceDisplayName..."
    Stop-Service -Name $ServiceName -Force
    Start-Sleep -Seconds 2

    $service = Get-Service -Name $ServiceName
    if ($service.Status -eq "Stopped") {
        Write-Success "Service stopped successfully"
    } else {
        Write-Error-Custom "Failed to stop service"
        exit 1
    }
}

function Restart-Service-Action {
    Write-Header "Restarting Service"

    if (-not (Test-Administrator)) {
        Write-Error-Custom "This action requires Administrator privileges"
        exit 1
    }

    $service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if (-not $service) {
        Write-Error-Custom "Service '$ServiceName' not found"
        exit 1
    }

    Write-Info "Restarting $ServiceDisplayName..."
    Restart-Service -Name $ServiceName -Force
    Start-Sleep -Seconds 3

    $service = Get-Service -Name $ServiceName
    if ($service.Status -eq "Running") {
        Write-Success "Service restarted successfully"
    } else {
        Write-Error-Custom "Failed to restart service"
        exit 1
    }
}

function Get-Status-Action {
    Write-Header "Service Status"

    $service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if (-not $service) {
        Write-Error-Custom "Service '$ServiceName' not found"
        exit 1
    }

    Write-Host "Service Name:      $($service.Name)" -ForegroundColor Cyan
    Write-Host "Display Name:      $($service.DisplayName)" -ForegroundColor Cyan

    $statusColor = if ($service.Status -eq "Running") { "Green" } else { "Red" }
    Write-Host "Status:            $($service.Status)" -ForegroundColor $statusColor
    Write-Host "Start Type:        $($service.StartType)" -ForegroundColor Cyan

    Write-Host ""
    Write-Info "Testing connectivity to http://localhost:5000..."
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:5000" -UseBasicParsing -TimeoutSec 5 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200 -or $response.StatusCode -eq 302) {
            Write-Success "Application is responding (HTTP $($response.StatusCode))"
        } else {
            Write-Info "Application returned status: $($response.StatusCode)"
        }
    } catch {
        if ($service.Status -eq "Running") {
            Write-Info "Service is running but application not responding yet"
        } else {
            Write-Error-Custom "Application not responding"
        }
    }
}

function Get-Logs-Action {
    Write-Header "Service Logs"

    if (-not (Test-Path $LogDir)) {
        Write-Error-Custom "Log directory not found at: $LogDir"
        Write-Info "Make sure the service has been started at least once"
        exit 1
    }

    Write-Info "Log directory: $LogDir"
    Write-Info "Available log files:"
    Get-ChildItem $LogDir -Filter "*.log" | ForEach-Object {
        $size = $_.Length / 1KB
        Write-Host "  - $($_.Name) ($([math]::Round($size, 2)) KB)"
    }

    Write-Host ""
    $latestLog = Get-ChildItem $LogDir -Filter "stdout.log" | Select-Object -First 1

    if ($latestLog) {
        if ($Follow) {
            Write-Info "Following log file (Ctrl+C to stop): $($latestLog.FullName)"
            Write-Host ""
            Get-Content $latestLog.FullName -Wait
        } else {
            Write-Info "Displaying last 30 lines of: $($latestLog.Name)"
            Write-Host ""
            Get-Content $latestLog.FullName -Tail 30
            Write-Host ""
            Write-Info "For full log, run: Get-Content '$($latestLog.FullName)'"
            Write-Info "To follow in real-time, run: .\manage-service.ps1 -Action logs -Follow"
        }
    } else {
        Write-Error-Custom "No log files found"
    }
}

function Open-GUI-Action {
    Write-Header "Opening Services GUI"

    Write-Info "Opening Windows Services management console..."
    Write-Info "Look for: $ServiceDisplayName"

    Start-Process "services.msc" -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}

function Uninstall-Service-Action {
    Write-Header "Uninstalling Service"

    if (-not (Test-Administrator)) {
        Write-Error-Custom "This action requires Administrator privileges"
        exit 1
    }

    $service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if (-not $service) {
        Write-Error-Custom "Service '$ServiceName' not found"
        exit 1
    }

    Write-Error-Custom "This will completely remove the service"
    Write-Host ""
    $confirmation = Read-Host "Are you sure? (type 'yes' to confirm)"

    if ($confirmation -ne "yes") {
        Write-Info "Uninstall cancelled"
        return
    }

    Write-Info "Stopping service..."
    Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2

    if (Test-Path $NssmExe) {
        Write-Info "Removing service via NSSM..."
        & $NssmExe remove $ServiceName confirm 2>&1 | Out-Null
    }

    Start-Sleep -Seconds 2

    $service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if ($service) {
        Write-Error-Custom "Service still exists"
        exit 1
    }

    Write-Success "Service uninstalled successfully"
}

# ============================================================================
# MAIN
# ============================================================================

switch ($Action.ToLower()) {
    "start" {
        Start-Service-Action
    }
    "stop" {
        Stop-Service-Action
    }
    "restart" {
        Restart-Service-Action
    }
    "status" {
        Get-Status-Action
    }
    "logs" {
        Get-Logs-Action
    }
    "gui" {
        Open-GUI-Action
    }
    "uninstall" {
        Uninstall-Service-Action
    }
    default {
        Write-Header "Service Management Commands"
        Write-Host "Usage: .\manage-service.ps1 -Action [action]" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "Actions:" -ForegroundColor Cyan
        Write-Host "  status     - Show current service status (default)" -ForegroundColor White
        Write-Host "  start      - Start the service" -ForegroundColor White
        Write-Host "  stop       - Stop the service" -ForegroundColor White
        Write-Host "  restart    - Restart the service" -ForegroundColor White
        Write-Host "  logs       - View service logs (last 30 lines)" -ForegroundColor White
        Write-Host "  logs -Follow - Follow logs in real-time" -ForegroundColor White
        Write-Host "  gui        - Open Windows Services management GUI" -ForegroundColor White
        Write-Host "  uninstall  - Remove the service" -ForegroundColor White
        Write-Host ""
        Write-Host "Examples:" -ForegroundColor Cyan
        Write-Host "  .\manage-service.ps1 -Action start" -ForegroundColor White
        Write-Host "  .\manage-service.ps1 -Action logs -Follow" -ForegroundColor White
    }
}
