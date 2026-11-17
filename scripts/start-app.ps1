# Use the full path to python in the venv (not relying on activation)
$pythonExe = Join-Path (Split-Path -Parent $PSScriptRoot) ".venv\Scripts\python.exe"
$appPath = Join-Path (Split-Path -Parent $PSScriptRoot) "app.py"

while ($true) {
    & $pythonExe $appPath
    
    # If app crashes, restart after 10 seconds
    Start-Sleep -Seconds 10
}
