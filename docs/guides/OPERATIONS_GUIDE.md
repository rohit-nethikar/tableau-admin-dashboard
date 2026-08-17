# Tableau Admin Dashboard - Operations Guide

Complete guide for running, monitoring, and troubleshooting the dashboard.

---

## 📊 Quick Start

### Start the Dashboard
The dashboard **automatically starts** when your computer boots up via Windows Task Scheduler.

**To manually start it:**
```powershell
Start-ScheduledTask -TaskName "TableauAdminDashboard"
```

### Access the Dashboard
Open your browser and go to:
```
http://localhost:5000
```

---

## ✅ How to Check If It's Running

### Method 1: Check Task Scheduler (Recommended)
```powershell
Get-ScheduledTask -TaskName "TableauAdminDashboard" | Select-Object TaskName, State
```

**Expected output:**
```
TaskName                    State
--------                    -----
TableauAdminDashboard       Running
```

### Method 2: Check if Port 5000 is Listening
```powershell
netstat -ano | findstr :5000
```

**Expected output:** (Shows connections on port 5000)
```
TCP    127.0.0.1:5000         127.0.0.1:xxxxx        ESTABLISHED
```

### Method 3: Test in Browser
Open: `http://localhost:5000`

**If it loads:** ✅ Running
**If "Connection refused":** ❌ Not running

---

## 🔍 Where to Check for Issues

### Dashboard Logs Location
```
C:\Users\m239012\AppData\Local\nssm\TableauAdminDash\
```

**Log files:**
- `stdout.log` - Application output and info messages
- `stderr.log` - Error messages

### View Logs

**Last 50 lines of output:**
```powershell
Get-Content "C:\Users\m239012\AppData\Local\nssm\TableauAdminDash\stdout.log" -Tail 50
```

**Last 50 lines of errors:**
```powershell
Get-Content "C:\Users\m239012\AppData\Local\nssm\TableauAdminDash\stderr.log" -Tail 50
```

**Follow logs live (Ctrl+C to stop):**
```powershell
Get-Content "C:\Users\m239012\AppData\Local\nssm\TableauAdminDash\stdout.log" -Wait
```

---

## 🛠️ Common Tasks

### Start the Dashboard
```powershell
Start-ScheduledTask -TaskName "TableauAdminDashboard"
```

### Stop the Dashboard
```powershell
Stop-ScheduledTask -TaskName "TableauAdminDashboard"
```

### Restart the Dashboard
```powershell
Restart-ScheduledTask -TaskName "TableauAdminDashboard"
```

### Run Manually (for debugging)
```powershell
cd "C:\Users\m239012\OneDrive - Mayo Clinic\GitHub_claude\tableau-admin-dashboard"
.\.venv\Scripts\python.exe app.py
```

**This will show all output and errors in the console.**

---

## ⚠️ Troubleshooting

### Issue: Dashboard won't start

**Step 1: Check the task status**
```powershell
Get-ScheduledTask -TableName "TableauAdminDashboard" | Select-Object TaskName, State
```

**Step 2: Check the logs**
```powershell
Get-Content "C:\Users\m239012\AppData\Local\nssm\TableauAdminDash\stderr.log" -Tail 100
```

**Step 3: Try running manually**
```powershell
cd "C:\Users\m239012\OneDrive - Mayo Clinic\GitHub_claude\tableau-admin-dashboard"
.\.venv\Scripts\python.exe app.py
```

**Step 4: Check Python environment**
```powershell
cd "C:\Users\m239012\OneDrive - Mayo Clinic\GitHub_claude\tableau-admin-dashboard"
.\.venv\Scripts\python --version
.\.venv\Scripts\pip list | grep -i flask
```

---

### Issue: "Connection refused" when accessing http://localhost:5000

**Check 1: Is the task running?**
```powershell
Get-ScheduledTask -TaskName "TableauAdminDashboard" | Select-Object State
# Should show: Running
```

**Check 2: Is port 5000 open?**
```powershell
netstat -ano | findstr :5000
# Should show active connections
```

**Check 3: Check Windows Firewall**
- Windows Defender Firewall → Allow an app through firewall
- Verify `Python.exe` is allowed for Private networks

**Check 4: Try from another computer**
```powershell
# Replace YOUR-MACHINE-NAME with actual computer name
http://YOUR-MACHINE-NAME:5000
```

---

### Issue: Dashboard shows "Internal Server Error"

**Step 1: Stop the task**
```powershell
Stop-ScheduledTask -TaskName "TableauAdminDashboard"
```

**Step 2: Run manually to see the error**
```powershell
cd "C:\Users\m239012\OneDrive - Mayo Clinic\GitHub_claude\tableau-admin-dashboard"
.\.venv\Scripts\python.exe app.py
```

**Step 3: Open the page in browser and watch the console output**

The error message in the console will tell you what's wrong.

**Step 4: Common errors:**

- **"ModuleNotFoundError: No module named 'xxx'"**
  ```powershell
  # Reinstall packages
  .\.venv\Scripts\pip install -r requirements.txt
  ```

- **"Could not connect to Tableau Server"**
  ```powershell
  # Check config.yaml
  notepad config.yaml
  # Verify server_url is correct
  ```

- **"Database locked"**
  ```powershell
  # Delete the database and let it recreate
  Remove-Item instance\cache.db -Force
  # Restart the app
  ```

---

### Issue: Dashboard keeps crashing

**Check the logs:**
```powershell
Get-Content "C:\Users\m239012\AppData\Local\nssm\TableauAdminDash\stderr.log" -Tail 200
```

**Possible causes:**
1. Missing configuration in `config.yaml`
2. Tableau Server connection issue
3. Database corruption
4. Out of disk space

---

## 📍 Important File Locations

```
Application:
  C:\Users\m239012\OneDrive - Mayo Clinic\GitHub_claude\tableau-admin-dashboard\

Python Virtual Environment:
  C:\Users\m239012\OneDrive - Mayo Clinic\GitHub_claude\tableau-admin-dashboard\.venv\

Configuration:
  C:\Users\m239012\OneDrive - Mayo Clinic\GitHub_claude\tableau-admin-dashboard\config.yaml

Database:
  C:\Users\m239012\OneDrive - Mayo Clinic\GitHub_claude\tableau-admin-dashboard\instance\cache.db

NSSM Installation:
  C:\tools\nssm\

Logs:
  C:\Users\m239012\AppData\Local\nssm\TableauAdminDash\
  ├── stdout.log
  └── stderr.log
```

---

## 🔄 Service Health Check (Daily)

Run this daily to verify everything is working:

```powershell
# Check 1: Task is running
Get-ScheduledTask -TaskName "TableauAdminDashboard" | Select-Object TaskName, State

# Check 2: Port 5000 is listening
netstat -ano | findstr :5000

# Check 3: Dashboard responds
$response = Invoke-WebRequest -Uri "http://localhost:5000" -UseBasicParsing -ErrorAction SilentlyContinue
if ($response.StatusCode -eq 200) {
    Write-Host "✓ Dashboard is responding" -ForegroundColor Green
} else {
    Write-Host "✗ Dashboard is not responding" -ForegroundColor Red
}

# Check 4: Recent errors in logs
Write-Host "Recent errors:" -ForegroundColor Cyan
Get-Content "C:\Users\m239012\AppData\Local\nssm\TableauAdminDash\stderr.log" -Tail 10
```

---

## 🚀 Performance Tips

### Monitor Resource Usage
```powershell
Get-Process python | Select-Object Name, CPU, Memory
```

**Expected usage:**
- Memory: 200-400 MB
- CPU: <5% at idle

### Restart if Slow
```powershell
Restart-ScheduledTask -TaskName "TableauAdminDashboard"
```

---

## 🔐 Security Notes

1. **Passcode:** Set during setup at http://localhost:5000/setup
2. **Tableau PAT:** Stored encrypted in `instance/secret.key`
3. **Access:** Currently HTTP only
   - For production, use reverse proxy with HTTPS (IIS, nginx)

---

## 📞 Quick Reference Card

| Task | Command |
|------|---------|
| **Check Status** | `Get-ScheduledTask -TaskName "TableauAdminDashboard"` |
| **Start** | `Start-ScheduledTask -TaskName "TableauAdminDashboard"` |
| **Stop** | `Stop-ScheduledTask -TaskName "TableauAdminDashboard"` |
| **Restart** | `Restart-ScheduledTask -TaskName "TableauAdminDashboard"` |
| **View Logs** | `Get-Content "C:\Users\m239012\AppData\Local\nssm\TableauAdminDash\stdout.log" -Tail 50` |
| **View Errors** | `Get-Content "C:\Users\m239012\AppData\Local\nssm\TableauAdminDash\stderr.log" -Tail 50` |
| **Run Manually** | `cd "C:\Users\m239012\OneDrive - Mayo Clinic\GitHub_claude\tableau-admin-dashboard"` then `.\.venv\Scripts\python.exe app.py` |
| **Access Dashboard** | `http://localhost:5000` |

---

## 📋 Maintenance Schedule

### Daily
- Check dashboard is accessible: `http://localhost:5000`
- Monitor logs for errors

### Weekly
- Review findings and remediation queue
- Check refresh health status

### Monthly
- Review health scores and trends
- Archive or export audit logs

### Quarterly
- Update Python packages
  ```powershell
  cd "C:\Users\m239012\OneDrive - Mayo Clinic\GitHub_claude\tableau-admin-dashboard"
  .\.venv\Scripts\pip install --upgrade -r requirements.txt
  ```
- Backup configuration and database

---

## 📞 Support

If you encounter issues:

1. **Check the logs** - Most errors are described there
2. **Run manually** - See actual error messages
3. **Check config.yaml** - Verify Tableau Server URL and credentials
4. **Restart the service** - Sometimes a fresh start fixes issues

```powershell
Stop-ScheduledTask -TaskName "TableauAdminDashboard"
Start-Sleep -Seconds 5
Start-ScheduledTask -TaskName "TableauAdminDashboard"
```

---

**Last Updated:** 2026-08-11  
**Version:** 1.0  
**Status:** Production Ready ✓

---

**Developed by:** Rohit Nethikar
