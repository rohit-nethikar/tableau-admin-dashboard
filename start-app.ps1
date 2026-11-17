# Tableau Admin Dashboard Startup Script
Set-Location $PSScriptRoot

# Activate virtual environment
$venvPath = Join-Path $PSScriptRoot ".venv\Scripts\Activate.ps1"
& $venvPath

# Start the app
& python app.py
