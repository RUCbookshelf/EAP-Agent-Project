#Requires -Version 5.1
# verify_environment.ps1 - READ-ONLY environment verifier.
# ASCII-only, PowerShell 5.1 compatible.
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\dev\verify_environment.ps1 [-Json]
# NEVER mutates (no uv install, no sync, no venv create, no browser install).

param(
    [switch]$Json
)

$ErrorActionPreference = "SilentlyContinue"

# ---------------------------------------------------------------------------
# 0. Resolve repo root and helpers
# ---------------------------------------------------------------------------
$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repoRoot
$helpersPath = Join-Path $repoRoot "scripts\dev\uv_helpers.ps1"
. $helpersPath

# ---------------------------------------------------------------------------
# Results collector
# ---------------------------------------------------------------------------
$script:results = @{}
$script:failedChecks = @()
$script:exitCode = 0

# Helper: add check result
function Add-Check {
    param([string]$Name, [string]$Status, [string]$Detail)
    $script:results[$Name] = @{ status = $Status; detail = $Detail }
    if ($Status -ne "READY") { $script:failedChecks += $Name }
}

# ---------------------------------------------------------------------------
# 1. Repository/worktree identity
# ---------------------------------------------------------------------------
$null = & git --version 2>&1
if ($LASTEXITCODE -eq 0) {
    $gitRoot = & git rev-parse --show-toplevel 2>&1
    $gitBranch = & git branch --show-current 2>&1
    $gitHead = & git rev-parse HEAD 2>&1
    $repoInfo = "root=$gitRoot branch=$gitBranch head=$gitHead"
    Add-Check "repository" "READY" $repoInfo
    Write-Host "[verify] repository: $repoInfo"
} else {
    Add-Check "repository" "NOT_READY" "GIT_NOT_AVAILABLE: git is not usable (parity tests require git subprocesses)"
    Write-Host "[verify] repository: GIT_NOT_AVAILABLE"
}

# ---------------------------------------------------------------------------
# 2. Python executable + version
# ---------------------------------------------------------------------------
$venvPython = Get-VenvPython
$venvState = Test-VenvHealthy
if ($venvState.Healthy) {
    $rangeOk = $false
    try {
        $versionMatch = [regex]::Match($venvState.Version, '\((\d+), (\d+)\)')
        $major = [int]$versionMatch.Groups[1].Value
        $minor = [int]$versionMatch.Groups[2].Value
        $rangeOk = (($major -eq 3) -and ($minor -ge 11) -and ($minor -lt 13))
    } catch {
        $rangeOk = $false
    }
    if ($rangeOk) {
        Add-Check "python" "READY" "$venvPython ($($venvState.Version))"
        Write-Host "[verify] python: $venvPython ($($venvState.Version))"
    } else {
        Add-Check "python" "NOT_READY" "PYTHON_RUNTIME_MISSING: version $($venvState.Version) outside supported range >=3.11,<3.13"
        Write-Host "[verify] python: NOT_READY (version outside >=3.11,<3.13)"
    }
} else {
    Add-Check "python" "NOT_READY" "VENV_MISSING: $($venvState.Reason)"
    Write-Host "[verify] python: VENV_MISSING - $($venvState.Reason)"
}

# ---------------------------------------------------------------------------
# 3. uv version
# ---------------------------------------------------------------------------
$uv = Find-Uv
if ($uv) {
    $uvVer = & $uv --version 2>&1
    Add-Check "uv" "READY" "$uv ($uvVer)"
    Write-Host "[verify] uv: $uv ($uvVer)"
} else {
    Add-Check "uv" "NOT_READY" "UV_NOT_AVAILABLE"
    Write-Host "[verify] uv: UV_NOT_AVAILABLE"
}

# ---------------------------------------------------------------------------
# 4. Environment location
# ---------------------------------------------------------------------------
$pythonDir = Resolve-UvPythonInstallDir
$cacheDir  = Resolve-UvCacheDir
$browsersPath = Resolve-BrowsersPath
$storeOk = Test-PathHealthy $pythonDir
$cacheOk = Test-PathHealthy $cacheDir
$browsersOk = Test-PathHealthy $browsersPath
$envLocation = "store=$pythonDir readable=$storeOk cache=$cacheDir readable=$cacheOk browsers=$browsersPath readable=$browsersOk"
if ($storeOk -and $cacheOk) {
    Add-Check "environment" "READY" $envLocation
} else {
    Add-Check "environment" "NOT_READY" "STORE_OR_CACHE_UNREADABLE: $envLocation"
}
Write-Host "[verify] environment: $envLocation"

# ---------------------------------------------------------------------------
# 5. Dependency lock status
# ---------------------------------------------------------------------------
$lockFile = Join-Path $repoRoot "uv.lock"
$lockStatus = "UNKNOWN"
$lockDetail = ""
if (-not (Test-Path $lockFile)) {
    $lockStatus = "NOT_READY"
    $lockDetail = "uv.lock not found"
} else {
    # Check requires-python range
    $lockContent = Get-Content $lockFile -Raw
    if ($lockContent -match 'requires-python\s*=\s*"[><=]*3\.1[12]') {
        $lockStatus = "READY"
        $lockDetail = "uv.lock exists, requires-python >=3.11,<3.13"
    } else {
        $lockStatus = "NOT_READY"
        $lockDetail = "uv.lock exists but requires-python range missing or wrong"
    }
    # Note: uv lock --check may be unavailable in restricted contexts
    if ($uv) {
        $lockCheckOut = & $uv lock --check 2>&1
        if ($LASTEXITCODE -ne 0) {
            $lockDetail += " (uv lock --check: LOCK_CHECK_UNAVAILABLE or drift)"
        }
    } else {
        $lockDetail += " (uv lock --check: LOCK_CHECK_UNAVAILABLE)"
    }
}
Add-Check "dependency_lock" $lockStatus $lockDetail
Write-Host "[verify] dependency_lock: $lockStatus - $lockDetail"

# ---------------------------------------------------------------------------
# 6. pytest availability
# ---------------------------------------------------------------------------
if ($venvState.Healthy) {
    $pytestOut = & $venvPython -m pytest --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        $pytestVer = ($pytestOut | Out-String).Trim()
        Add-Check "pytest" "READY" $pytestVer
        Write-Host "[verify] pytest: $pytestVer"
    } else {
        Add-Check "pytest" "NOT_READY" "pytest not importable in venv"
        Write-Host "[verify] pytest: NOT_READY"
    }
} else {
    Add-Check "pytest" "NOT_READY" "python venv not available"
    Write-Host "[verify] pytest: NOT_READY (no venv)"
}

# ---------------------------------------------------------------------------
# 7. Application import
# ---------------------------------------------------------------------------
if ($venvState.Healthy) {
    $appOut = & $venvPython -c "from app.config import load_settings; print('OK')" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Add-Check "app_import" "READY" "from app.config import load_settings"
        Write-Host "[verify] app_import: OK"
    } else {
        Add-Check "app_import" "NOT_READY" "app.config import failed"
        Write-Host "[verify] app_import: NOT_READY"
    }
} else {
    Add-Check "app_import" "NOT_READY" "python venv not available"
    Write-Host "[verify] app_import: NOT_READY (no venv)"
}

# ---------------------------------------------------------------------------
# 8. Database tooling (sqlite3)
# ---------------------------------------------------------------------------
if ($venvState.Healthy) {
    $sqliteOut = & $venvPython -c "import sqlite3; print(sqlite3.sqlite_version)" 2>&1
    if ($LASTEXITCODE -eq 0) {
        $sqliteVer = ($sqliteOut | Out-String).Trim()
        Add-Check "sqlite" "READY" "sqlite3.sqlite_version=$sqliteVer"
        Write-Host "[verify] sqlite: $sqliteVer"
    } else {
        Add-Check "sqlite" "NOT_READY" "sqlite3 import failed"
        Write-Host "[verify] sqlite: NOT_READY"
    }
} else {
    Add-Check "sqlite" "NOT_READY" "python venv not available"
    Write-Host "[verify] sqlite: NOT_READY (no venv)"
}

# ---------------------------------------------------------------------------
# 9. spaCy + model status
# ---------------------------------------------------------------------------
if ($venvState.Healthy) {
    $nlpScript = Join-Path $repoRoot "scripts\verify_nlp_resources.py"
    if (Test-Path $nlpScript) {
        $nlpOut = & $venvPython -m scripts.verify_nlp_resources 2>&1
        $nlpJson = $nlpOut | Out-String
        if ($nlpJson -match '"status"\s*:\s*"PASS"') {
            Add-Check "spacy" "READY" "en_core_web_sm installed"
            Write-Host "[verify] spacy: READY (en_core_web_sm installed)"
        } elseif ($nlpJson -match '"status"\s*:\s*"FALLBACK_AVAILABLE"') {
            # Fallback is acceptable for verification
            Add-Check "spacy" "READY" "FALLBACK_AVAILABLE (model missing, BasicAnalyzer available)"
            Write-Host "[verify] spacy: READY (FALLBACK_AVAILABLE)"
        } else {
            Add-Check "spacy" "NOT_READY" "NLP resources check failed"
            Write-Host "[verify] spacy: NOT_READY"
        }
    } else {
        Add-Check "spacy" "NOT_READY" "verify_nlp_resources.py not found"
        Write-Host "[verify] spacy: NOT_READY (script missing)"
    }
} else {
    Add-Check "spacy" "NOT_READY" "python venv not available"
    Write-Host "[verify] spacy: NOT_READY (no venv)"
}

# ---------------------------------------------------------------------------
# 10. Playwright status
# ---------------------------------------------------------------------------
$playwrightReady = $false
$chromiumPath = ""
if ($venvState.Healthy) {
    $pwOut = & $venvPython -c "import playwright; print('OK')" 2>&1
    if ($LASTEXITCODE -eq 0) {
        # Check Chromium path resolution
        $env:PLAYWRIGHT_BROWSERS_PATH = $browsersPath
        $chromiumCheck = & $venvPython -c @"
import os
from playwright.sync_api import sync_playwright
try:
    with sync_playwright() as p:
        path = p.chromium.executable_path
        if path and os.path.exists(path):
            print(path)
        else:
            print('NOT_FOUND')
except Exception:
    print('NOT_FOUND')
"@ 2>&1
        $chromiumPath = ($chromiumCheck | Out-String).Trim()
        if ($chromiumPath -ne "NOT_FOUND" -and (Test-Path $chromiumPath)) {
            $playwrightReady = $true
            Add-Check "playwright" "READY" "Chromium at $chromiumPath"
            Write-Host "[verify] playwright: READY (Chromium found)"
        } else {
            Add-Check "playwright" "NOT_READY" "RESOURCE_MISSING: Chromium not found at $browsersPath. Install: python -m playwright install chromium"
            Write-Host "[verify] playwright: RESOURCE_MISSING"
        }
    } else {
        Add-Check "playwright" "NOT_READY" "playwright not importable"
        Write-Host "[verify] playwright: NOT_READY"
    }
} else {
    Add-Check "playwright" "NOT_READY" "python venv not available"
    Write-Host "[verify] playwright: NOT_READY (no venv)"
}

# ---------------------------------------------------------------------------
# 11. Launcher prerequisites (ports 8000/8501 free check)
# ---------------------------------------------------------------------------
$port8000free = $true
$port8501free = $true
$portDetail = ""

# Port 8000
$socket8000 = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Loopback, 8000)
try {
    $socket8000.Start()
    $socket8000.Stop()
    $port8000free = $true
} catch {
    $port8000free = $false
}

# Port 8501
$socket8501 = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Loopback, 8501)
try {
    $socket8501.Start()
    $socket8501.Stop()
    $port8501free = $true
} catch {
    $port8501free = $false
}

if ($port8000free -and $port8501free) {
    Add-Check "ports" "READY" "8000 and 8501 free"
    Write-Host "[verify] ports: READY (8000 and 8501 free)"
} else {
    $portDetail = "8000=$port8000free, 8501=$port8501free"
    Add-Check "ports" "NOT_READY" "Ports occupied: $portDetail"
    Write-Host "[verify] ports: NOT_READY ($portDetail)"
}

# ---------------------------------------------------------------------------
# 12. Determine overall status
# ---------------------------------------------------------------------------
# Playwright browsers are REQUIRED for full verification (browser suites are core)
$overallReady = ($script:failedChecks.Count -eq 0)

if ($overallReady) {
    Write-Host ""
    Write-Host "ENVIRONMENT READY"
} else {
    Write-Host ""
    Write-Host "ENVIRONMENT NOT READY"
    Write-Host "  Failed checks: $($script:failedChecks -join ', ')"
    foreach ($check in $script:failedChecks) {
        $info = $script:results[$check]
        Write-Host "    $check : $($info.detail)"
    }
    $script:exitCode = 1
}

# ---------------------------------------------------------------------------
# 13. JSON output
# ---------------------------------------------------------------------------
if ($Json) {
    $jsonObj = [ordered]@{}
    foreach ($key in ($results.Keys | Sort-Object)) {
        $jsonObj[$key] = [ordered]@{
            status = $script:results[$key].status
            detail = $script:results[$key].detail
        }
    }
    $jsonObj["overall"] = if ($overallReady) { "READY" } else { "NOT_READY" }
    $jsonObj["failed_checks"] = $script:failedChecks
    $jsonStr = $jsonObj | ConvertTo-Json -Depth 3
    Write-Host ""
    Write-Host $jsonStr
}

exit $script:exitCode
