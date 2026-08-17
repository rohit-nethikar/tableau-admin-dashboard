# ============================================================================
# Tableau Admin Dashboard - Automated Health Check Script
# ============================================================================
# Purpose: Monitor dashboard status and log results
# Run: Weekly via Windows Task Scheduler
# ============================================================================

param(
    [switch]$SendEmail = $false,
    [string]$EmailTo = "your-email@mayo.edu",
    [string]$SmtpServer = "smtprelay.mayo.edu"
)

# Configuration
$ServiceName = "TableauAdminDashboard"
$DashboardUrl = "http://localhost:5000"
$Port = 5000
$LogFile = "C:\Users\m239012\OneDrive - Mayo Clinic\GitHub_claude\tableau-admin-dashboard\health-check-log.txt"

# ============================================================================
# Functions
# ============================================================================

function Write-Header {
    param([string]$Text)
    $line = "=" * 80
    $output = @"
$line
$Text
$line
$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
$line
"@
    Write-Host $output -ForegroundColor Cyan
    Add-Content -Path $LogFile -Value $output
}

function Write-Success {
    param([string]$Text)
    $line = "✓ $Text"
    Write-Host $line -ForegroundColor Green
    Add-Content -Path $LogFile -Value $line
}

function Write-Error-Custom {
    param([string]$Text)
    $line = "✗ $Text"
    Write-Host $line -ForegroundColor Red
    Add-Content -Path $LogFile -Value $line
}

function Write-Info {
    param([string]$Text)
    $line = "ℹ $Text"
    Write-Host $line -ForegroundColor Yellow
    Add-Content -Path $LogFile -Value $line
}

function Check-TaskStatus {
    try {
        $task = Get-ScheduledTask -TaskName $ServiceName -ErrorAction Stop

        if ($task.State -eq "Running") {
            Write-Success "Task Status: RUNNING"
            return $true
        } else {
            Write-Error-Custom "Task Status: $($task.State)"
            return $false
        }
    } catch {
        Write-Error-Custom "Failed to get task status: $_"
        return $false
    }
}

function Check-PortListening {
    try {
        $portCheck = netstat -ano 2>$null | findstr ":$Port"

        if ($portCheck) {
            Write-Success "Port $Port: LISTENING"
            return $true
        } else {
            Write-Error-Custom "Port $Port: NOT LISTENING"
            return $false
        }
    } catch {
        Write-Error-Custom "Failed to check port: $_"
        return $false
    }
}

function Check-DashboardAccess {
    try {
        $response = Invoke-WebRequest -Uri $DashboardUrl -UseBasicParsing -TimeoutSec 10 -ErrorAction Stop

        if ($response.StatusCode -eq 200) {
            Write-Success "Dashboard Access: OK (HTTP 200)"
            return $true
        } else {
            Write-Error-Custom "Dashboard Access: Failed (HTTP $($response.StatusCode))"
            return $false
        }
    } catch {
        Write-Error-Custom "Dashboard Access: Failed - $_"
        return $false
    }
}

function Check-RecentErrors {
    try {
        $logPath = "$env:APPDATA\Local\nssm\TableauAdminDash\stderr.log"

        if (Test-Path $logPath) {
            $recentErrors = Get-Content $logPath -Tail 10 -ErrorAction SilentlyContinue

            if ($recentErrors) {
                Write-Info "Recent errors in log (last 10 lines):"
                $recentErrors | ForEach-Object {
                    Add-Content -Path $LogFile -Value "  $_"
                    Write-Host "  $_" -ForegroundColor Yellow
                }
                return $true
            } else {
                Write-Success "No recent errors in log"
                return $false
            }
        } else {
            Write-Info "Log file not found yet"
            return $false
        }
    } catch {
        Write-Error-Custom "Failed to check logs: $_"
        return $false
    }
}

function Send-HealthAlert {
    param(
        [bool]$AllHealthy,
        [string]$Summary
    )

    if (-not $SendEmail) {
        return
    }

    try {
        $subject = if ($AllHealthy) {
            "✓ Dashboard Health Check PASSED - $(Get-Date -Format 'yyyy-MM-dd')"
        } else {
            "⚠ Dashboard Health Check FAILED - $(Get-Date -Format 'yyyy-MM-dd')"
        }

        $body = @"
Dashboard Health Check Report
Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')

Status: $(if ($AllHealthy) { 'HEALTHY ✓' } else { 'ISSUES DETECTED ✗' })

Summary:
$Summary

Check Details:
- Service Name: $ServiceName
- Dashboard URL: $DashboardUrl
- Port: $Port

For more details, check the health check log at:
$LogFile

Log Location: $env:APPDATA\Local\nssm\TableauAdminDash\

---
This is an automated message. Do not reply to this email.
"@

        Send-MailMessage -From "tableau-dashboard@mayo.edu" `
                        -To $EmailTo `
                        -Subject $subject `
                        -Body $body `
                        -SmtpServer $SmtpServer `
                        -ErrorAction Stop

        Write-Success "Health alert email sent to: $EmailTo"
    } catch {
        Write-Error-Custom "Failed to send email: $_"
    }
}

# ============================================================================
# Main Execution
# ============================================================================

Write-Header "TABLEAU ADMIN DASHBOARD - HEALTH CHECK"

# Initialize results
$results = @{
    TaskRunning = $false
    PortListening = $false
    DashboardAccessing = $false
    HasRecentErrors = $false
}

# Run checks
$results.TaskRunning = Check-TaskStatus
Write-Host ""

$results.PortListening = Check-PortListening
Write-Host ""

$results.DashboardAccessing = Check-DashboardAccess
Write-Host ""

$results.HasRecentErrors = Check-RecentErrors
Write-Host ""

# Determine overall health
$allHealthy = $results.TaskRunning -and $results.PortListening -and $results.DashboardAccessing -and -not $results.HasRecentErrors

# Summary
Write-Host ""
Write-Header "HEALTH CHECK SUMMARY"

if ($allHealthy) {
    Write-Success "All checks PASSED - Dashboard is HEALTHY ✓"
    $summary = "All systems operational. No issues detected."
} else {
    Write-Error-Custom "Some checks FAILED - Dashboard may have issues"
    $summary = @"
Failed Checks:
$(if (-not $results.TaskRunning) { "- Task is not running`n" })
$(if (-not $results.PortListening) { "- Port $Port is not listening`n" })
$(if (-not $results.DashboardAccessing) { "- Dashboard is not accessible`n" })
$(if ($results.HasRecentErrors) { "- Recent errors found in logs`n" })
"@
}

Write-Info "Summary: $summary"

# Send email if configured
if ($SendEmail) {
    Write-Host ""
    Send-HealthAlert -AllHealthy $allHealthy -Summary $summary
}

# Final status
Write-Host ""
Write-Host "Log saved to: $LogFile" -ForegroundColor Cyan
Write-Host ""

# Return exit code
exit if ($allHealthy) { 0 } else { 1 }
