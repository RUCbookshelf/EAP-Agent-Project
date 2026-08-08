#Requires -Version 5.1
# bootstrap_environment.ps1 - Canonical, idempotent environment bootstrap.
# ASCII-only, PowerShell 5.1 compatible.
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\dev\bootstrap_environment.ps1

$ErrorActionPreference = "Continue"

# ---------------------------------------------------------------------------
# 0. Resolve repo root and helpers
# ---------------------------------------------------------------------------
$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repoRoot
$helpersPath = Join-Path $repoRoot "scripts\dev\uv_helpers.ps1"
. $helpersPath

Write-Host "[bootstrap] repository root: $repoRoot"

# ---------------------------------------------------------------------------
# 1. Windows check
# ---------------------------------------------------------------------------
$osPlatform = [System.Environment]::OSVersion.Platform
if ($osPlatform -ne "Win32NT") {
    Write-Host "UNSUPPORTED_OS: this bootstrap requires Windows (Win32NT). Detected: $osPlatform"
    exit 1
}

# ---------------------------------------------------------------------------
# 2. Discover uv
# ---------------------------------------------------------------------------
$uv = Find-Uv
if (-not $uv) {
    Write-Host "UV_NOT_AVAILABLE"
    Write-Host "  Action: install uv 0.12.x user-space from official sources."
    Write-Host "    Option A (recommended): powershell -ExecutionPolicy Bypass -c `"iwr https://astral.sh/uv/install.ps1 -UseBasicParsing | iex`""
    Write-Host "    Option B: python -m pip install uv"
    Write-Host "  Then re-run this bootstrap."
    exit 1
}
Write-Host "[bootstrap] uv found at: $uv"
$uvVersion = & $uv --version 2>&1
Write-Host "[bootstrap] uv version: $uvVersion"

# ---------------------------------------------------------------------------
# 3. Compute environment
# ---------------------------------------------------------------------------
$pythonDir = Resolve-UvPythonInstallDir
$cacheDir  = Resolve-UvCacheDir
$browsersPath = Resolve-BrowsersPath

$env:UV_PYTHON_INSTALL_DIR = $pythonDir
$env:UV_CACHE_DIR          = $cacheDir
$env:PLAYWRIGHT_BROWSERS_PATH = $browsersPath

Write-Host "[bootstrap] UV_PYTHON_INSTALL_DIR = $pythonDir"
Write-Host "[bootstrap] UV_CACHE_DIR = $cacheDir"
Write-Host "[bootstrap] PLAYWRIGHT_BROWSERS_PATH = $browsersPath"

# ---------------------------------------------------------------------------
# 4. Ensure managed Python 3.12.13
# ---------------------------------------------------------------------------
# Try to find managed Python
$prevErrorActionPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
$findPy = & $uv python find 3.12.13 2>&1
$uvExitCode = $LASTEXITCODE
$ErrorActionPreference = $prevErrorActionPreference

# Check for cache initialization errors
$findPyStr = $findPy | Out-String
if ($findPyStr -match "Failed to initialize cache") {
    Write-Host "UV_CACHE_UNUSABLE: cannot initialize cache at $cacheDir"
    Write-Host "  Action: ensure write access to $cacheDir or set UV_CACHE_DIR to a writable location."
    Write-Host "    Current user may not have write permission to this directory."
    exit 1
}

if ($uvExitCode -ne 0) {
    Write-Host "PYTHON_RUNTIME_MISSING"
    Write-Host "  Action: install Python 3.12.13 via uv (downloading ~21 MB)."
    Write-Host "    Command: & `"$uv`" python install 3.12.13"
    & $uv python install 3.12.13
    if ($LASTEXITCODE -ne 0) {
        Write-Host "PYTHON_RUNTIME_MISSING: install failed."
        exit 1
    }
    # Re-check
    $findPy = & $uv python find 3.12.13 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "PYTHON_RUNTIME_MISSING: could not locate Python 3.12.13 after install."
        exit 1
    }
}
Write-Host "[bootstrap] managed Python 3.12.13 located: $findPy"

# ---------------------------------------------------------------------------
# 5. Venv health
# ---------------------------------------------------------------------------
$venvPython = Get-VenvPython
$venvState = Test-VenvHealthy

if (-not $venvState.Healthy) {
    Write-Host "VENV_INTERPRETER_BROKEN: $($venvState.Reason)"
    # Remove broken venv
    if (Test-Path $venvPython) {
        # $venvPython = <venv>\Scripts\python.exe -> remove the <venv> root
        Remove-VenvLongPath (Split-Path (Split-Path $venvPython))
    }
    Write-Host "[bootstrap] rebuilding .venv"
    & $uv sync
    if ($LASTEXITCODE -ne 0) {
        $lastErr = $Error[0]
        Write-Host "DEPENDENCY_SYNC_FAILED: $lastErr"
        exit 1
    }
} else {
    Write-Host "[bootstrap] venv healthy: $($venvState.Version)"
    # Sync against the committed lock (fast no-op on a correct environment)
    $null = & $uv sync 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "DEPENDENCY_SYNC_FAILED: uv sync exited $LASTEXITCODE"
        exit 1
    }
    # Deterministic drift check
    $null = & $uv sync --check 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "LOCKFILE_DRIFT"
        Write-Host "  Action: run `"$uv`" sync --check for details, then have Shared Platform & Core"
        Write-Host "  update pyproject.toml/uv.lock together with a verification record."
        exit 1
    }
}

# ---------------------------------------------------------------------------
# 6. Verify interpreter identity
# ---------------------------------------------------------------------------
$venvPython = Get-VenvPython
& $venvPython -c "import sys; assert (3,12) <= sys.version_info[:2] < (3,13)"
if ($LASTEXITCODE -ne 0) {
    Write-Host "PYTHON_RUNTIME_MISSING: venv python is not CPython 3.12.x"
    exit 1
}
$pyVer = & $venvPython -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"
Write-Host "[bootstrap] interpreter verified: Python $pyVer"

# ---------------------------------------------------------------------------
# 7. Verify dependency state
# ---------------------------------------------------------------------------
& $venvPython -m pytest --version 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "DEPENDENCY_SYNC_FAILED: pytest not importable"
    exit 1
}
Write-Host "[bootstrap] pytest available"

$nlpScript = Join-Path $repoRoot "scripts\verify_nlp_resources.py"
if (Test-Path $nlpScript) {
    $nlpOut = & $venvPython -m scripts.verify_nlp_resources 2>&1
    $nlpStr = $nlpOut | Out-String
    Write-Host "[bootstrap] NLP resources: $nlpStr"
} else {
    Write-Host "[bootstrap] NLP resources: verify_nlp_resources.py not found (skipped)"
}

# ---------------------------------------------------------------------------
# 8. Verify required dev tools
# ---------------------------------------------------------------------------
try {
    $null = Get-Command git -ErrorAction Stop
    $gitVer = & git --version 2>&1
    Write-Host "[bootstrap] git: $gitVer"
} catch {
    Write-Host "GIT_NOT_AVAILABLE: git is not on PATH (non-fatal warning)"
}

# ---------------------------------------------------------------------------
# 9. Final output
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "ENVIRONMENT READY"
Write-Host "  python:   $pyVer"
Write-Host "  uv:       $uvVersion"
Write-Host "  venv:     $(Split-Path $venvPython)"
Write-Host "  store:    $pythonDir"
Write-Host "  cache:    $cacheDir"
Write-Host "  browsers: $browsersPath"
exit 0
