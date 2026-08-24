# Tableau Admin Dashboard Startup Script
Set-Location "C:\Users\m239012\OneDrive - Mayo Clinic\GitHub_claude\tableau-admin-dashboard"

# Activate virtual environment
$venvPath = "C:\Users\m239012\OneDrive - Mayo Clinic\GitHub_claude\tableau-admin-dashboard\.venv\Scripts\Activate.ps1"
& $venvPath

# Start the app
& python app.py
