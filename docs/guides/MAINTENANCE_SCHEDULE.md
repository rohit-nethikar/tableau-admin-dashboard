# Tableau Admin Dashboard - Daily & Weekly Check Schedule

Complete guide for monitoring and maintaining your dashboard.

---

## 📅 Maintenance Schedule Overview

| Frequency | Duration | What to Check | Status |
|-----------|----------|---------------|--------|
| **Daily** | 2 minutes | Quick status | Automated ✓ |
| **Weekly** | 5 minutes | Health report review | Automated ✓ |
| **Monthly** | 15 minutes | Deep audit | Manual |
| **Quarterly** | 30 minutes | Performance review | Manual |

---

## 🔵 Daily Check (2 minutes)

### When
- **Best time:** Early morning (8-9 AM) before team uses dashboard
- **How often:** Once per day, Monday-Friday
- **How:** Automated or manual

### Automated Daily Check (EASIEST)

**No action needed!** The dashboard auto-restarts if it crashes.

### Manual Daily Check (If You Prefer)

Open PowerShell and run:

```powershell
# Quick 30-second status check
Write-Host "Dashboard Status:" -ForegroundColor Cyan
$task = Get-ScheduledTask -TaskName "TableauAdminDashboard"
Write-Host "  Task: $($task.State)" -ForegroundColor $(if ($task.State -eq 'Running') { 'Green' } else { 'Red' })

Write-Host "Port Check:" -ForegroundColor Cyan
if (netstat -ano 2>$null | findstr :5000) { 
    Write-Host "  Port 5000: Listening ✓" -ForegroundColor Green
} else { 
    Write-Host "  Port 5000: NOT Listening ✗" -ForegroundColor Red
}

Write-Host "Browser Access:" -ForegroundColor Cyan
$web = Invoke-WebRequest -Uri "http://localhost:5000" -UseBasicParsing -ErrorAction SilentlyContinue
if ($web.StatusCode -eq 200) {
    Write-Host "  Dashboard: Accessible ✓" -ForegroundColor Green
} else {
    Write-Host "  Dashboard: NOT Accessible ✗" -ForegroundColor Red
}
```

### What's Healthy?
✅ Task shows "Running"  
✅ Port 5000 shows "Listening"  
✅ Dashboard shows "Accessible"

### If Something's Wrong
👉 See the **Troubleshooting** section at the end of this guide

---

## 🟡 Weekly Check (5 minutes)

### When
- **Scheduled:** Every Monday at 9:00 AM (Automatic)
- **Manual review:** Monday morning after 9:15 AM
- **Duration:** 5 minutes

### What Happens Automatically

Every Monday at 9 AM:
- Dashboard health check runs automatically
- Results saved to log file
- You just need to review them

### How to Review Results

#### Method 1: View the Log (Easiest)

```powershell
# Open the health check log
notepad "C:\Users\m239012\OneDrive - Mayo Clinic\GitHub_claude\tableau-admin-dashboard\health-check-log.txt"
```

#### Method 2: View in PowerShell

```powershell
# Show last 50 lines
Get-Content "C:\Users\m239012\OneDrive - Mayo Clinic\GitHub_claude\tableau-admin-dashboard\health-check-log.txt" -Tail 50
```

#### Method 3: Run Health Check Manually

```powershell
cd "C:\Users\m239012\OneDrive - Mayo Clinic\GitHub_claude\tableau-admin-dashboard"
.\health-check.ps1
```

### Reading the Health Check Report

**Look for this format:**

```
================================================================================
TABLEAU ADMIN DASHBOARD - HEALTH CHECK
================================================================================
2026-08-11 09:00:00
================================================================================

✓ Task Status: RUNNING
✓ Port 5000: LISTENING
✓ Dashboard Access: OK (HTTP 200)
✓ No recent errors in log

================================================================================
HEALTH CHECK SUMMARY
================================================================================
✓ All checks PASSED - Dashboard is HEALTHY ✓
```

### What Each Check Means

| Check | Healthy | Not Healthy |
|-------|---------|-------------|
| **Task Status** | RUNNING | STOPPED or PAUSED |
| **Port 5000** | LISTENING | NOT LISTENING |
| **Dashboard Access** | OK (HTTP 200) | Failed or HTTP error |
| **Recent Errors** | No recent errors | Has errors in log |

### Weekly Action Items

- [ ] Review health check log (Monday morning)
- [ ] Note any issues found
- [ ] Check if dashboard is accessible in browser
- [ ] If issues: Apply fixes from troubleshooting guide
- [ ] If all good: Continue to next week

---

## 🟠 Monthly Check (15 minutes)

### When
- **Schedule:** First Monday of each month at 2:00 PM
- **Duration:** 15 minutes
- **This is a deeper dive**

### Monthly Checklist

#### 1. Review Last 4 Weekly Reports (5 min)

```powershell
# View entire log file
notepad "C:\Users\m239012\OneDrive - Mayo Clinic\GitHub_claude\tableau-admin-dashboard\health-check-log.txt"
```

**Questions to answer:**
- Were there any failures this month?
- Were there patterns in the errors?
- How many times did it restart?

#### 2. Check Dashboard Performance (5 min)

Open in browser: `http://localhost:5000`

- [ ] Does it load quickly (under 3 seconds)?
- [ ] Are all pages accessible?
- [ ] Are there any error messages?
- [ ] Is the data up-to-date?

**Check these pages:**
- [ ] Overview
- [ ] Workbooks
- [ ] Analytics
- [ ] Health
- [ ] Findings

#### 3. Review Configuration (5 min)

```powershell
# Check if config files are accessible
notepad "C:\Users\m239012\OneDrive - Mayo Clinic\GitHub_claude\tableau-admin-dashboard\config.yaml"
```

**Verify:**
- [ ] Server URL is correct
- [ ] No configuration changes needed
- [ ] Credentials are still valid

#### 4. Check Resource Usage (Optional)

```powershell
# See how much memory/CPU the app uses
Get-Process python | Where-Object {$_.Name -eq "python"} | Select-Object Name, CPU, Memory
```

**Healthy ranges:**
- Memory: 200-500 MB
- CPU: <5% at idle

### Monthly Summary Report

**Create a quick record:**

```
Month: August 2026

Health Checks Passed: 4/4
Issues Found: None
Performance: Good
User Issues: None

Notes:
- All systems operating normally
- No action needed this month

Next Review: September 1, 2026
```

---

## 🔴 Quarterly Check (30 minutes)

### When
- **Schedule:** First week of Q2, Q3, Q4, Q1
- **Examples:** Feb 1, May 1, Aug 1, Nov 1
- **Duration:** 30 minutes

### Quarterly Checklist

- [ ] **Review all monthly reports** (5 min)
  - Any patterns in issues?
  - Any recurring problems?

- [ ] **Check system resources** (5 min)
  ```powershell
  # Disk space
  Get-Volume
  
  # CPU usage over time
  Get-Process python | Measure-Object CPU -Maximum
  ```

- [ ] **Verify backups exist** (5 min)
  ```powershell
  # Check backup locations
  Test-Path "C:\Users\m239012\OneDrive - Mayo Clinic\GitHub_claude\tableau-admin-dashboard\config.yaml.backup"
  Test-Path "C:\Users\m239012\OneDrive - Mayo Clinic\GitHub_claude\tableau-admin-dashboard\instance\cache.db.backup"
  ```

- [ ] **Update Python packages** (10 min)
  ```powershell
  cd "C:\Users\m239012\OneDrive - Mayo Clinic\GitHub_claude\tableau-admin-dashboard"
  .\.venv\Scripts\pip install --upgrade -r requirements.txt
  ```

- [ ] **Test disaster recovery** (5 min)
  - Can you restart the service manually?
  - Do you have the setup documentation?

---

## ⚠️ Issue Response Guide

### Issue: "Dashboard Not Responding"

**Priority:** 🔴 High (1 hour)

**Steps:**
```powershell
# 1. Restart the service
Restart-ScheduledTask -TaskName "TableauAdminDashboard"

# 2. Wait 30 seconds
Start-Sleep -Seconds 30

# 3. Test
Start-Process "http://localhost:5000"

# 4. If still fails, check logs
Get-Content "C:\Users\m239012\AppData\Local\nssm\TableauAdminDash\stderr.log" -Tail 50
```

### Issue: "Port 5000 Not Listening"

**Priority:** 🔴 High (1 hour)

**Steps:**
```powershell
# 1. Check what's using the port
netstat -ano | findstr :5000

# 2. Check if task is running
Get-ScheduledTask -TaskName "TableauAdminDashboard" | Select-Object State

# 3. Restart task
Stop-ScheduledTask -TaskName "TableauAdminDashboard"
Start-Sleep -Seconds 5
Start-ScheduledTask -TableName "TableauAdminDashboard"

# 4. Verify
netstat -ano | findstr :5000
```

### Issue: "Repeated Crashes/Restarts"

**Priority:** 🟠 Medium (4 hours)

**Steps:**
```powershell
# 1. Check the logs
Get-Content "C:\Users\m239012\AppData\Local\nssm\TableauAdminDash\stderr.log" -Tail 100

# 2. Look for patterns in error messages

# 3. If database issue:
Stop-ScheduledTask -TaskName "TableauAdminDashboard"
Remove-Item "C:\Users\m239012\OneDrive - Mayo Clinic\GitHub_claude\tableau-admin-dashboard\instance\cache.db" -Force
Start-ScheduledTask -TaskName "TableauAdminDashboard"

# 4. If dependency issue:
cd "C:\Users\m239012\OneDrive - Mayo Clinic\GitHub_claude\tableau-admin-dashboard"
.\.venv\Scripts\pip install -r requirements.txt
Restart-ScheduledTask -TaskName "TableauAdminDashboard"
```

### Issue: "High CPU or Memory Usage"

**Priority:** 🟡 Medium (8 hours)

**Steps:**
```powershell
# 1. Monitor usage
Get-Process python | Where-Object {$_.Name -eq "python"} | Select-Object Name, CPU, Memory

# 2. Restart for cleanup
Restart-ScheduledTask -TableName "TableauAdminDashboard"

# 3. Check if specific page causes issue
# Try accessing different pages in browser and note which uses resources

# 4. If problem persists, check logs for queries running too long
Get-Content "C:\Users\m239012\AppData\Local\nssm\TableauAdminDash\stdout.log" | Select-String "slow\|query\|processing"
```

---

## 📍 Log Locations Quick Reference

```
Daily/Weekly Check Results:
  C:\Users\m239012\OneDrive - Mayo Clinic\GitHub_claude\tableau-admin-dashboard\health-check-log.txt

Application Logs:
  C:\Users\m239012\AppData\Local\nssm\TableauAdminDash\stdout.log
  C:\Users\m239012\AppData\Local\nssm\TableauAdminDash\stderr.log

Configuration:
  C:\Users\m239012\OneDrive - Mayo Clinic\GitHub_claude\tableau-admin-dashboard\config.yaml

Database:
  C:\Users\m239012\OneDrive - Mayo Clinic\GitHub_claude\tableau-admin-dashboard\instance\cache.db
```

---

## 📋 Quick Copy-Paste Commands

### Daily Check (Copy & Paste This)

```powershell
Write-Host "=== DAILY HEALTH CHECK ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Task Status:" -ForegroundColor Yellow
Get-ScheduledTask -TaskName "TableauAdminDashboard" | Select-Object TaskName, State
Write-Host ""
Write-Host "Port 5000:" -ForegroundColor Yellow
if (netstat -ano 2>$null | findstr :5000) { Write-Host "✓ Listening" -ForegroundColor Green } else { Write-Host "✗ Not Listening" -ForegroundColor Red }
Write-Host ""
Write-Host "Dashboard:" -ForegroundColor Yellow
$web = Invoke-WebRequest -Uri "http://localhost:5000" -UseBasicParsing -ErrorAction SilentlyContinue
if ($web.StatusCode -eq 200) { Write-Host "✓ Accessible" -ForegroundColor Green } else { Write-Host "✗ Not Accessible" -ForegroundColor Red }
```

### Weekly Check (Copy & Paste This)

```powershell
Write-Host "=== WEEKLY HEALTH REPORT ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Last Health Check:" -ForegroundColor Yellow
Get-Content "C:\Users\m239012\OneDrive - Mayo Clinic\GitHub_claude\tableau-admin-dashboard\health-check-log.txt" -Tail 30
Write-Host ""
Write-Host "If all checks show ✓, everything is healthy!" -ForegroundColor Green
```

### Restart Dashboard (Copy & Paste This)

```powershell
Write-Host "Restarting dashboard..." -ForegroundColor Yellow
Restart-ScheduledTask -TaskName "TableauAdminDashboard"
Start-Sleep -Seconds 5
Write-Host "Restart complete!" -ForegroundColor Green
Write-Host "Dashboard should be accessible at: http://localhost:5000" -ForegroundColor Cyan
```

---

## 📞 Need Help?

**Quick diagnostics:**

```powershell
# Run this if something seems wrong
Write-Host "=== DIAGNOSTIC REPORT ===" -ForegroundColor Red
Write-Host ""
Write-Host "1. Task Status:"
Get-ScheduledTask -TaskName "TableauAdminDashboard" | Select-Object State
Write-Host ""
Write-Host "2. Port Listening:"
netstat -ano | findstr :5000
Write-Host ""
Write-Host "3. Recent Errors:"
Get-Content "C:\Users\m239012\AppData\Local\nssm\TableauAdminDash\stderr.log" -Tail 10
Write-Host ""
Write-Host "4. Health Check Status:"
Get-Content "C:\Users\m239012\OneDrive - Mayo Clinic\GitHub_claude\tableau-admin-dashboard\health-check-log.txt" -Tail 5
```

---

## 📅 Sample Annual Schedule

```
January: Quarterly check + system updates
February: Monthly checks (Feb 1, 8, 15, 22, 29)
March: Monthly checks
April: Quarterly check + package updates
May: Monthly checks
June: Monthly checks
July: Monthly checks
August: Quarterly check + performance review
September: Monthly checks
October: Monthly checks
November: Monthly checks + year-end audit
December: Quarterly check + year-end backup
```

---

## ✅ Maintenance Checklist Template

Print and use this for monthly/quarterly reviews:

```
Month/Quarter: ______________  Date: ______________

Daily Health Checks:
  □ Monday - Task: _____ Port: _____ Dashboard: _____
  □ Tuesday - Task: _____ Port: _____ Dashboard: _____
  □ Wednesday - Task: _____ Port: _____ Dashboard: _____
  □ Thursday - Task: _____ Port: _____ Dashboard: _____
  □ Friday - Task: _____ Port: _____ Dashboard: _____

Issues Found: ___________________________________________

Actions Taken: __________________________________________

Performance: CPU _____ Memory _____ Disk Space: _____

Sign-off: ______________________ Date: ______________
```

---

**Last Updated:** 2026-08-11  
**Version:** 1.0  
**Review Date:** Monthly

---

**Developed by:** Rohit Nethikar
