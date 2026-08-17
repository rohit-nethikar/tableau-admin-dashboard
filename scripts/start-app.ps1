# Use the full path to python in the venv (not relying on activation)
$pythonExe = "C:\Users\m239012\OneDrive - Mayo Clinic\GitHub_claude\tableau-admin-dashboard\.venv\Scripts\python.exe"
$appPath = "C:\Users\m239012\OneDrive - Mayo Clinic\GitHub_claude\tableau-admin-dashboard\app.py"

while ($true) {
    & $pythonExe $appPath
    
    # If app crashes, restart after 10 seconds
    Start-Sleep -Seconds 10
}
