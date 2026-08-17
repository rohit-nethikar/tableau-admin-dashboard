# ============================================================================
# Setup Automated Health Check Task
# ============================================================================
# Run this ONCE to create the weekly health check schedule
# Prerequisites: Run as Administrator
# ============================================================================

$ErrorActionPreference = "Stop"

# Configuration
$TaskName = "TableauDashboardHealthCheck"
$ScriptPath = "C:\Users\m239012\OneDrive - Mayo Clinic\GitHub_claude\tableau-admin-dashboard\health-check.ps1"
$DayOfWeek = "Monday"
$TimeOfDay = "09:00:00"  # 9 AM
$EmailEnabled = $false  # Set to $true if you want email alerts

# ============================================================================
# Functions
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

function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# ============================================================================
# Main
# ============================================================================

Write-Header "Setup Automated Health Check"

# Check administrator
if (-not (Test-Administrator)) {
    Write-Error-Custom "This script requires Administrator privileges"
    Write-Info "Please run PowerShell as Administrator and try again"
    exit 1
}

Write-Success "Running as Administrator"

# Verify script exists
if (-not (Test-Path $ScriptPath)) {
    Write-Error-Custom "Health check script not found at: $ScriptPath"
    exit 1
}

Write-Success "Health check script found"

# Check if task already exists
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Write-Info "Task '$TaskName' already exists"
    $response = Read-Host "Do you want to remove and recreate it? (y/n)"

    if ($response -eq "y") {
        Write-Info "Removing existing task..."
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Success "Old task removed"
    } else {
        Write-Info "Using existing task"
        exit 0
    }
}

# Create the task action
Write-Info "Creating scheduled task..."

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$ScriptPath`""

# Create the trigger (Weekly on Monday at 9 AM)
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $DayOfWeek -At $TimeOfDay

# Create task settings
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew

# Register the task
try {
    Register-ScheduledTask -TaskName $TaskName `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Description "Weekly health check for Tableau Admin Dashboard" `
        -Force | Out-Null

    Write-Success "Scheduled task created successfully!"
} catch {
    Write-Error-Custom "Failed to create task: $_"
    exit 1
}

# Display task details
Write-Header "Task Details"

$task = Get-ScheduledTask -TaskName $TaskName
Write-Host "Task Name:      $($task.TaskName)" -ForegroundColor White
Write-Host "Status:         $($task.State)" -ForegroundColor White
Write-Host "Trigger:        Weekly on $DayOfWeek at $TimeOfDay" -ForegroundColor White
Write-Host "Next Run:       $(($task | Get-ScheduledTaskInfo).NextRunTime)" -ForegroundColor White
Write-Host "Script:         $ScriptPath" -ForegroundColor White

# Option to run immediately
Write-Header "Test Run"
Write-Info "You can test the health check now by running:"
Write-Host "  Start-ScheduledTask -TaskName '$TaskName'" -ForegroundColor Gray
Write-Host ""
Write-Info "Or run manually with:"
Write-Host "  & '$ScriptPath'" -ForegroundColor Gray

# Ask if they want to run now
$runNow = Read-Host "Run health check now? (y/n)"
if ($runNow -eq "y") {
    Write-Header "Running Health Check"
    & $ScriptPath
}

# Display log location
Write-Header "Log Location"
Write-Host "Health check results are logged to:" -ForegroundColor Cyan
Write-Host "  C:\Users\m239012\OneDrive - Mayo Clinic\GitHub_claude\tableau-admin-dashboard\health-check-log.txt" -ForegroundColor White

Write-Host ""
Write-Host "View latest log:" -ForegroundColor Cyan
Write-Host "  Get-Content 'C:\Users\m239012\OneDrive - Mayo Clinic\GitHub_claude\tableau-admin-dashboard\health-check-log.txt' -Tail 50" -ForegroundColor Gray

# Configure email alerts (optional)
if ($EmailEnabled) {
    Write-Header "Email Alerts Configuration"
    Write-Info "Email alerts are currently DISABLED"
    Write-Info "To enable, edit health-check.ps1 and set \$SendEmail = \$true"
} else {
    Write-Header "Email Alerts"
    Write-Info "Email alerts are DISABLED"
    Write-Info "To enable email notifications:"
    Write-Host "  1. Edit: $ScriptPath" -ForegroundColor Gray
    Write-Host "  2. Find the 'Send email if configured' section" -ForegroundColor Gray
    Write-Host "  3. Run this script again with -SendEmail flag" -ForegroundColor Gray
}

Write-Header "Setup Complete! ✓"

Write-Host "Your dashboard will be checked EVERY" -ForegroundColor Green
Write-Host "  $DayOfWeek at $TimeOfDay" -ForegroundColor Green
Write-Host ""
Write-Host "Results logged to:" -ForegroundColor Cyan
Write-Host "  C:\Users\m239012\OneDrive - Mayo Clinic\GitHub_claude\tableau-admin-dashboard\health-check-log.txt" -ForegroundColor Gray
