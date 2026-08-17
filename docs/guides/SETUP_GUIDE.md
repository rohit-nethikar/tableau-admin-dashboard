# Tableau Admin Dashboard - Windows Service Setup Guide

Complete automated setup scripts to run the tableau-admin-dashboard as a 24/7 Windows Service.

## Quick Start (5 minutes)

### Prerequisites
- Windows 11 or Windows Server
- Python 3.10+ installed
- Administrator privileges
- PowerShell 5.0+

### Installation

1. **Open PowerShell as Administrator**
   - Right-click PowerShell icon → "Run as Administrator"
   - Navigate to the dashboard folder:
   ```powershell
   cd "C:\Users\m239012\OneDrive - Mayo Clinic\GitHub_claude\tableau-admin-dashboard"
   ```

2. **Set execution policy** (one-time, if needed)
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
   ```

3. **Set up Python environment**
   ```powershell
   .\setup-environment.ps1
   ```
   This creates the virtual environment and installs all dependencies.

4. **Configure the application**
   ```powershell
   notepad config.yaml
   ```
   - Set `server_url` to your Tableau Server URL
   - Set `site_name` (leave empty for "Default")
   - Save and close

5. **Install and start as Windows Service**
   ```powershell
   .\setup-service.ps1
   ```
   This will:
   - Download NSSM (Non-Sucking Service Manager)
   - Create the service wrapper script
   - Install the Windows Service
   - Configure auto-restart on crash
   - Start the service
   - Test connectivity

6. **Verify it's running**
   ```
   Open browser: http://localhost:5000
   ```
   You should see the dashboard setup page.

---

## Available Scripts

### 1. `setup-environment.ps1`
**Purpose:** Create Python virtual environment and install dependencies

**Usage:**
```powershell
.\setup-environment.ps1                    # Initial setup
.\setup-environment.ps1 -Reset             # Reset/reinstall dependencies
```

**What it does:**
- Verifies Python 3.10+ is installed
- Creates `.venv` virtual environment
- Installs packages from `requirements.txt`
- Verifies all key packages are available

**When to use:**
- First time installation
- After updating `requirements.txt`
- To fix missing dependencies

---

### 2. `setup-service.ps1`
**Purpose:** Install and configure Windows Service using NSSM

**Usage:**
```powershell
.\setup-service.ps1                        # Install/configure service
.\setup-service.ps1 -Uninstall             # Remove service
.\setup-service.ps1 -SkipNSSMDownload      # Skip NSSM download (if already installed)
```

**What it does:**
- Downloads NSSM from nssm.cc
- Creates `run_service.bat` wrapper script
- Registers Windows Service with auto-restart
- Sets service to start automatically on reboot
- Starts the service
- Tests connectivity

**Requires:** Administrator privileges

**When to use:**
- First time setup
- To reinstall service after removal
- To update service configuration

---

### 3. `manage-service.ps1`
**Purpose:** Quick management commands for the running service

**Usage:**
```powershell
.\manage-service.ps1                       # Show status (default)
.\manage-service.ps1 -Action start         # Start service
.\manage-service.ps1 -Action stop          # Stop service
.\manage-service.ps1 -Action restart       # Restart service
.\manage-service.ps1 -Action logs          # View last 30 lines of logs
.\manage-service.ps1 -Action logs -Follow  # Follow logs in real-time
.\manage-service.ps1 -Action gui           # Open Services GUI
.\manage-service.ps1 -Action uninstall     # Uninstall service
```

**What it shows:**
- Service status (Running/Stopped)
- Start type (Automatic)
- Application connectivity test
- Log file locations

**Requires:** Administrator privileges (for start/stop/restart)

**When to use:**
- Daily monitoring
- Checking logs
- Troubleshooting issues
- Managing the service

---

## Complete Setup Workflow

### First Time Installation (Follow in order)

#### Step 1: Prepare (No scripts needed)
```powershell
# Navigate to dashboard
cd "C:\Users\m239012\OneDrive - Mayo Clinic\GitHub_claude\tableau-admin-dashboard"

# View current setup
dir
# You should see: config.yaml, governance.yaml, requirements.txt, setup-*.ps1, etc.
```

#### Step 2: Create Python Environment
```powershell
# Takes 2-3 minutes
.\setup-environment.ps1

# Wait for "Environment Setup Complete!" message
```

#### Step 3: Configure Application
```powershell
# Edit config.yaml
notepad config.yaml

# Change:
#   server_url: "https://your-tableau-server.example.com"
#   site_name: ""              # or your site name
#   host: "0.0.0.0"            # accessible from network
#   port: 5000

# Save and close (Ctrl+S, Ctrl+W)
```

#### Step 4: Install Windows Service
```powershell
# Requires Administrator - right-click PowerShell, "Run as Administrator"
.\setup-service.ps1

# Wait for "Setup Complete!" message
# Service should now be running
```

#### Step 5: Verify
```powershell
# Check status
.\manage-service.ps1 -Action status

# Open browser to test
Start-Process "http://localhost:5000"
```

---

## Common Tasks

### Check if Service is Running
```powershell
.\manage-service.ps1
```

Output will show:
- Service Status: Running ✓
- Start Type: Automatic
- Application: Responding

---

### View Application Logs
```powershell
# Last 30 lines
.\manage-service.ps1 -Action logs

# Real-time follow (Ctrl+C to stop)
.\manage-service.ps1 -Action logs -Follow
```

Logs are stored in:
```
C:\Users\m239012\AppData\Local\nssm\TableauAdminDash\
```

---

### Restart the Service
```powershell
# Quick restart
.\manage-service.ps1 -Action restart

# Or stop then start
.\manage-service.ps1 -Action stop
.\manage-service.ps1 -Action start
```

---

### Stop the Service
```powershell
.\manage-service.ps1 -Action stop
```

Service will not restart until you start it again manually.

---

### Update Dependencies
```powershell
# If requirements.txt was updated
.\setup-environment.ps1

# Then restart service
.\manage-service.ps1 -Action restart
```

---

### Remove Service (Uninstall)
```powershell
# Interactive uninstall
.\manage-service.ps1 -Action uninstall

# Or use setup script
.\setup-service.ps1 -Uninstall
```

---

## Troubleshooting

### Service won't start
```powershell
# Check detailed logs
.\manage-service.ps1 -Action logs -Follow

# Common issues:
# 1. Port 5000 already in use
#    - Check: netstat -ano | findstr :5000
#    - Change port in config.yaml

# 2. config.yaml has errors
#    - Validate YAML syntax
#    - Check indentation (use spaces, not tabs)

# 3. Virtual environment corrupted
#    - Run: .\setup-environment.ps1 -Reset
#    - Then: .\manage-service.ps1 -Action restart
```

---

### Can't access http://localhost:5000
```powershell
# 1. Verify service is running
.\manage-service.ps1 -Action status

# 2. Check if port is accessible
Test-NetConnection -ComputerName localhost -Port 5000

# 3. Try from another machine (if host: 0.0.0.0 is set)
# Replace "localhost" with actual machine IP/hostname

# 4. Check Windows Firewall
# Windows Defender Firewall → Allow an app through firewall
# Add Python.exe and port 5000
```

---

### Service crashes repeatedly
```powershell
# 1. View logs for error messages
.\manage-service.ps1 -Action logs -Follow

# 2. Check if Tableau Server is accessible
# Try opening your server URL in browser

# 3. Verify PAT (Personal Access Token) is valid
# In config.yaml, make sure pat_name and pat_secret are correct

# 4. Check config.yaml syntax
notepad config.yaml
# All YAML must be properly indented

# 5. Restart service
.\manage-service.ps1 -Action restart
```

---

### Application works manually but not as service
```powershell
# The service uses a batch wrapper script
# Check if batch script exists and works:

# 1. View the wrapper
notepad run_service.bat

# 2. Run it manually to see errors
cd "C:\Users\m239012\OneDrive - Mayo Clinic\GitHub_claude\tableau-admin-dashboard"
.\run_service.bat

# 3. If batch fails, check:
#    - Virtual environment still exists
#    - config.yaml is in correct location
#    - Port is available
```

---

## Advanced Configuration

### Change Service Port
```powershell
# 1. Edit config.yaml
notepad config.yaml

# Change: port: 5001  (or any port 1024-65535)

# 2. Restart service
.\manage-service.ps1 -Action restart

# 3. Access at new port
Start-Process "http://localhost:5001"
```

---

### Make Service Accessible from Network
```powershell
# 1. Verify config.yaml has:
notepad config.yaml
# host: "0.0.0.0"     # accessible from other machines
# port: 5000

# 2. Get your machine's IP
ipconfig

# 3. Share URL with team (e.g., http://192.168.1.50:5000)

# 4. Configure Windows Firewall
# Windows Defender Firewall → Allow an app through firewall
# Add Python.exe for both Private and Public networks
```

---

### Set Up TLS/HTTPS (Healthcare Recommended)
The app currently runs on HTTP. For healthcare data, use a reverse proxy:

**Option 1: IIS (Microsoft Internet Information Services)**
- Install IIS on Windows
- Add reverse proxy role
- Configure SSL certificate
- Forward traffic to http://localhost:5000

**Option 2: nginx**
- Install nginx
- Configure nginx.conf with upstream
- Configure SSL certificate
- Forward traffic to http://localhost:5000

---

## Service Details

### Service Configuration
| Setting | Value |
|---------|-------|
| Service Name | `TableauAdminDash` |
| Display Name | `Tableau Admin Dashboard` |
| Startup Type | Automatic (starts on reboot) |
| Startup Account | Current user (or service account) |
| Auto-restart | Yes (on any exit) |
| Restart Delay | 30 seconds |
| Log Location | `%APPDATA%\Local\nssm\TableauAdminDash\` |

### Log Files
- **stdout.log** - Application output
- **stderr.log** - Error output
- **TableauAdminDash_*.log** - NSSM combined logs

---

## Managing via Windows Services GUI

You can also manage the service using the Windows Services management console:

```powershell
# Open Services GUI
.\manage-service.ps1 -Action gui

# Or press: Win + R, type "services.msc", Enter

# Find: "Tableau Admin Dashboard"
# Right-click → Start/Stop/Restart/Properties
```

---

## Monitoring and Alerting

### Daily Health Check
```powershell
# Run this daily (or set up Task Scheduler)
.\manage-service.ps1 -Action status

# It will show:
# - Service running status
# - Application connectivity
# - Any issues
```

### Set Up Monitoring Alert (Optional)
```powershell
# Create a scheduled task to monitor service
# Windows Task Scheduler → Create Basic Task
# Trigger: Daily at 9 AM
# Action: Run script: manage-service.ps1 -Action status

# Save output to a file for review
# Add >> "C:\logs\dashboard-health.log" to script
```

---

## Backup and Recovery

### Backup Configuration
```powershell
# Backup these files regularly
Copy-Item "config.yaml" "config.yaml.backup"
Copy-Item "governance.yaml" "governance.yaml.backup"
Copy-Item "instance\cache.db" "instance\cache.db.backup"

# Store backups in secure location
```

### Restore from Backup
```powershell
# Stop service
.\manage-service.ps1 -Action stop

# Restore files
Copy-Item "config.yaml.backup" "config.yaml" -Force

# Restart service
.\manage-service.ps1 -Action start
```

---

## Support and Troubleshooting

### Useful PowerShell Commands
```powershell
# View service in PowerShell
Get-Service TableauAdminDash

# View service properties
Get-Service TableauAdminDash | Select-Object *

# Check if port is listening
netstat -ano | findstr :5000

# View process info
Get-Process python | Where-Object { $_.ProcessName -eq "python" }

# Test network connectivity
Test-NetConnection -ComputerName localhost -Port 5000
```

### NSSM Useful Commands
```powershell
# Direct NSSM commands (if needed)
$NssmPath = "C:\tools\nssm\nssm.exe"

# Query service status
& $NssmPath status TableauAdminDash

# Edit configuration (GUI)
& $NssmPath edit TableauAdminDash

# View all config
& $NssmPath get TableauAdminDash
```

### Log Locations
```
Application Logs:
  C:\Users\m239012\AppData\Local\nssm\TableauAdminDash\

Configuration Files:
  C:\Users\m239012\OneDrive - Mayo Clinic\GitHub_claude\tableau-admin-dashboard\

Database:
  C:\Users\m239012\OneDrive - Mayo Clinic\GitHub_claude\tableau-admin-dashboard\instance\cache.db

NSSM Installation:
  C:\tools\nssm\
```

---

## Performance and Resource Usage

The service typically uses:
- **Memory:** 150-300 MB (baseline) + 50-100 MB per concurrent browser session
- **CPU:** <5% at idle, 20-40% during sync operations
- **Disk:** 50-100 MB (database size depends on Tableau content)

### Monitor Resource Usage
```powershell
# Real-time monitoring
Get-Process python | Where-Object { $_.MainWindowTitle -like "*tableau*" } | Select-Object Name, CPU, Memory
```

---

## Security Considerations

### For Healthcare/Compliance
1. **HTTPS Required** - Use reverse proxy with TLS
2. **Passcode** - Unique passcode (not shared with others recommended)
3. **Network Access** - Restrict to trusted networks only
4. **Logging** - All activities logged to local database
5. **Service Account** - Use dedicated service account (not personal account)

### Firewall Configuration
```powershell
# Allow Python through Windows Firewall
# Windows Defender Firewall → Allow an app through firewall
# Check "Python" for Private networks only
```

### PAT Security
- Store PAT securely in config.yaml
- It's encrypted at rest (`instance/secret.key`)
- Restrict config.yaml permissions if needed

---

## Support

### Get Help
- View help on any script:
  ```powershell
  .\manage-service.ps1 -Help
  ```

- Check service status:
  ```powershell
  .\manage-service.ps1 -Action status
  ```

- View detailed logs:
  ```powershell
  .\manage-service.ps1 -Action logs -Follow
  ```

### Useful References
- NSSM Documentation: https://nssm.cc/usage
- Python venv: https://docs.python.org/3/library/venv.html
- Windows Services: https://docs.microsoft.com/windows/win32/services/

---

## Script File Locations

All setup scripts are in the dashboard directory:
```
C:\Users\m239012\OneDrive - Mayo Clinic\GitHub_claude\tableau-admin-dashboard\
├── setup-environment.ps1      # Create venv and install packages
├── setup-service.ps1          # Install Windows Service
├── manage-service.ps1         # Daily management commands
├── run_service.bat            # Created by setup-service.ps1
├── config.yaml                # Application configuration
├── governance.yaml            # Scoring rules
└── SETUP_GUIDE.md             # This file
```

---

**Version:** 1.0  
**Last Updated:** 2026-08-11  
**Status:** Ready for Production
