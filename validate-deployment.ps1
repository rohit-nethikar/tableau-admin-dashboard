param(
    [switch]$SkipImportTest,
    [switch]$SkipSecretScan
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

$failures = New-Object System.Collections.Generic.List[string]

function Check($Condition, $Success, $Failure) {
    if ($Condition) {
        Write-Host "[OK] $Success" -ForegroundColor Green
    } else {
        Write-Host "[FAIL] $Failure" -ForegroundColor Red
        $failures.Add($Failure)
    }
}

Write-Host ""
Write-Host "Deployment readiness validation" -ForegroundColor Cyan
Write-Host "Project: $ProjectRoot"
Write-Host ""

$required = @(
    "app.py",
    "config.py",
    "requirements.txt",
    "Dockerfile",
    ".dockerignore",
    ".env.example",
    "startup.ps1",
    "startup.sh",
    "DEPLOYMENT.md"
)

foreach ($f in $required) {
    Check (Test-Path $f) "$f exists" "$f is missing"
}

$python = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    $python = "python"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $python = "py"
} else {
    $failures.Add("Python executable was not found")
    Write-Host "[FAIL] Python executable was not found" -ForegroundColor Red
}

if ($python) {
    Write-Host ""
    Write-Host "Compiling project Python files..." -ForegroundColor Cyan
    $pythonFiles = Get-ChildItem -Recurse -Filter *.py |
        Where-Object {
            $_.FullName -notmatch '\\.venv\\|\\venv\\|\\env\\|\\__pycache__\\'
        }

    foreach ($f in $pythonFiles) {
        if ($python -eq "python") {
            & python -m py_compile $f.FullName
        } else {
            & py -m py_compile $f.FullName
        }

        if ($LASTEXITCODE -ne 0) {
            $failures.Add("Python syntax validation failed: $($f.FullName)")
            break
        }
    }

    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] Python syntax validation passed" -ForegroundColor Green
    }

    if (-not $SkipImportTest -and $failures.Count -eq 0) {
        Write-Host ""
        Write-Host "Checking Flask URL map..." -ForegroundColor Cyan

        $oldSkip = $env:DEPLOYMENT_VALIDATE_ONLY
        $env:DEPLOYMENT_VALIDATE_ONLY = "1"

        try {
            if ($python -eq "python") {
                $output = & python -c "import app; print('HEALTHZ_ROUTE=' + str(any(r.rule == '/healthz' for r in app.app.url_map.iter_rules())))" 2>&1
            } else {
                $output = & py -c "import app; print('HEALTHZ_ROUTE=' + str(any(r.rule == '/healthz' for r in app.app.url_map.iter_rules())))" 2>&1
            }

            $healthLine = $output | Where-Object { $_ -match '^HEALTHZ_ROUTE=' } | Select-Object -Last 1
            if ($healthLine -eq "HEALTHZ_ROUTE=True") {
                Write-Host "[OK] /healthz is registered" -ForegroundColor Green
            } else {
                Write-Host "[FAIL] /healthz was not found in Flask URL map" -ForegroundColor Red
                $failures.Add("/healthz was not found in Flask URL map")
            }
        } catch {
            Write-Host "[WARN] Import test could not complete: $($_.Exception.Message)" -ForegroundColor Yellow
            Write-Host "       Re-run with -SkipImportTest if external services are required during import."
        } finally {
            if ($null -eq $oldSkip) {
                Remove-Item Env:DEPLOYMENT_VALIDATE_ONLY -ErrorAction SilentlyContinue
            } else {
                $env:DEPLOYMENT_VALIDATE_ONLY = $oldSkip
            }
        }
    }
}

Write-Host ""
Write-Host "Checking git hygiene..." -ForegroundColor Cyan

if (Get-Command git -ErrorAction SilentlyContinue) {
    $trackedSecrets = @(
        "bigquery-credentials.json",
        "instance/cache.db",
        "instance/secret.key",
        "instance/flask_secret.key"
    )

    foreach ($candidate in $trackedSecrets) {
        $tracked = git ls-files --error-unmatch -- $candidate 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[FAIL] Sensitive/runtime file is tracked by git: $candidate" -ForegroundColor Red
            $failures.Add("Sensitive/runtime file is tracked by git: $candidate")
        } else {
            Write-Host "[OK] Not tracked: $candidate" -ForegroundColor Green
        }
    }

    if (-not $SkipSecretScan) {
        $credentialMatches = git ls-files | Select-String -Pattern '(^|/)(.*credentials.*\.json|.*secret.*\.key|\.env)$'
        if ($credentialMatches) {
            Write-Host "[WARN] Review these tracked filenames for secrets:" -ForegroundColor Yellow
            $credentialMatches | ForEach-Object { Write-Host "       $($_.Line)" }
        }
    }
} else {
    Write-Host "[WARN] git command not found; repository hygiene checks skipped" -ForegroundColor Yellow
}

Write-Host ""
if ($failures.Count -gt 0) {
    Write-Host "Validation FAILED with $($failures.Count) issue(s):" -ForegroundColor Red
    foreach ($f in $failures) {
        Write-Host " - $f"
    }
    exit 1
}

Write-Host "Validation PASSED." -ForegroundColor Green
Write-Host "This validates packaging and basic runtime structure; it does not prove"
Write-Host "network, Tableau, BigQuery, or corporate hosting connectivity."

