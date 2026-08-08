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
# 2. Discover or provision uv
# ---------------------------------------------------------------------------
$uv = Find-Uv
if (-not $uv) {
    Write-Host "UV_NOT_AVAILABLE: attempting best-effort user-space provisioning from the"
    Write-Host "  official Astral installer (https://astral.sh/uv/install.ps1)..."
    try {
        $webClient = New-Object System.Net.WebClient
        $installerScript = $webClient.DownloadString("https://astral.sh/uv/install.ps1")
        $scriptBlock = [scriptblock]::Create($installerScript)
        & $scriptBlock
    } catch {
        Write-Host "  Provisioning attempt failed: $($_.Exception.Message)"
    }
    $uv = Find-Uv
    if (-not $uv) {
        Write-Host "UV_NOT_AVAILABLE"
        Write-Host "  Action: install uv 0.12.x user-space from official sources, then re-run."
        Write-Host "    Option A (recommended): powershell -ExecutionPolicy Bypass -c `"iwr https://astral.sh/uv/install.ps1 -UseBasicParsing | iex`""
        Write-Host "    Option B: python -m pip install uv"
        exit 1
    }
    Write-Host "[bootstrap] uv provisioned: $uv"
}
Write-Host "[bootstrap] uv found at: $uv"
$uvVersion = (& $uv --version 2>&1 | Out-String).Trim()
Write-Host "[bootstrap] uv version: $uvVersion"

# ---------------------------------------------------------------------------
# 3. Compute environment (writability-aware; bootstrap may probe-write)
# ---------------------------------------------------------------------------
$pythonDir = Resolve-UvPythonInstallDir -ProbeWritable
$cacheDir  = Resolve-UvCacheDir -ProbeWritable
$browsersPath = Resolve-BrowsersPath -ProbeWritable

$env:UV_PYTHON_INSTALL_DIR = $pythonDir
$env:UV_CACHE_DIR          = $cacheDir
$env:PLAYWRIGHT_BROWSERS_PATH = $browsersPath
# Route `uv sync` to the contract environment location (honors WF_VENV_PATH).
$env:UV_PROJECT_ENVIRONMENT = Split-Path (Split-Path (Get-VenvPython))

Write-Host "[bootstrap] UV_PYTHON_INSTALL_DIR = $pythonDir"
Write-Host "[bootstrap] UV_CACHE_DIR = $cacheDir"
Write-Host "[bootstrap] PLAYWRIGHT_BROWSERS_PATH = $browsersPath"

# ---------------------------------------------------------------------------
# 4. Ensure managed Python 3.12.13
# ---------------------------------------------------------------------------
$findPy = & $uv python find 3.12.13 2>&1
$uvExitCode = $LASTEXITCODE
$findPyStr = $findPy | Out-String

if ($findPyStr -match "Failed to initialize cache") {
    Write-Host "UV_CACHE_UNUSABLE: cannot initialize cache at $cacheDir"
    Write-Host "  Action: ensure write access to $cacheDir or set UV_CACHE_DIR to a writable location."
    exit 1
}

if ($uvExitCode -ne 0) {
    Write-Host "PYTHON_RUNTIME_MISSING: installing Python 3.12.13 via uv (~21 MB)..."
    & $uv python install 3.12.13
    if ($LASTEXITCODE -ne 0) {
        Write-Host "PYTHON_RUNTIME_MISSING: install failed."
        exit 1
    }
    $findPy = & $uv python find 3.12.13 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "PYTHON_RUNTIME_MISSING: could not locate Python 3.12.13 after install."
        exit 1
    }
}
Write-Host "[bootstrap] managed Python 3.12.13 located: $findPy"

# ---------------------------------------------------------------------------
# 5. Lock-first enforcement and venv health
# ---------------------------------------------------------------------------
# Manifest/lock drift is detected BEFORE any sync can rewrite uv.lock (the
# bootstrap never rewrites the lock; matches future CI `uv sync --locked`).
$null = & $uv lock --check 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "LOCKFILE_DRIFT"
    Write-Host "  uv.lock does not match pyproject.toml. This bootstrap never rewrites the"
    Write-Host "  lock; Shared Platform & Core must regenerate and commit it with a"
    Write-Host "  verification record. Run: `"$uv`" lock --check"
    exit 1
}

$null = & $uv sync --check 2>&1
$envInSync = ($LASTEXITCODE -eq 0)

$venvPython = Get-VenvPython
$venvState = Test-VenvHealthy

if (-not $venvState.Healthy) {
    Write-Host "VENV_INTERPRETER_BROKEN: $($venvState.Reason)"
    if (Test-Path $venvPython) {
        # $venvPython = <venv>\Scripts\python.exe -> remove the <venv> root
        Remove-VenvLongPath (Split-Path (Split-Path $venvPython))
    }
    Write-Host "[bootstrap] rebuilding .venv"
    & $uv sync --locked
    if ($LASTEXITCODE -ne 0) {
        Write-Host "DEPENDENCY_SYNC_FAILED: uv sync exited $LASTEXITCODE"
        exit 1
    }
    $null = & $uv sync --check 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "DEPENDENCY_SYNC_FAILED: environment still out of sync after rebuild"
        exit 1
    }
} else {
    Write-Host "[bootstrap] venv healthy: $($venvState.Version)"
    if (-not $envInSync) {
        Write-Host "[bootstrap] environment out of sync with lock; syncing..."
        & $uv sync --locked
        if ($LASTEXITCODE -ne 0) {
            Write-Host "DEPENDENCY_SYNC_FAILED: uv sync exited $LASTEXITCODE"
            exit 1
        }
        $null = & $uv sync --check 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Host "DEPENDENCY_SYNC_FAILED: environment still out of sync after sync"
            exit 1
        }
    } else {
        Write-Host "[bootstrap] environment in sync with lock (no changes needed)"
    }
}

# ---------------------------------------------------------------------------
# 6. Verify interpreter identity
# ---------------------------------------------------------------------------
$venvPython = Get-VenvPython
& $venvPython -c "import sys; assert (3,11) <= sys.version_info[:2] < (3,13)"
if ($LASTEXITCODE -ne 0) {
    Write-Host "PYTHON_RUNTIME_MISSING: venv python outside supported range >=3.11,<3.13"
    exit 1
}
$pyVer = (& $venvPython -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')" 2>&1 | Out-String).Trim()
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
    Write-Host "[bootstrap] NLP resources: $($nlpOut | Out-String)"
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
    Write-Host "GIT_NOT_AVAILABLE: git is not usable (parity tests spawn git subprocesses)"
}

# ---------------------------------------------------------------------------
# 9. Final output
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "ENVIRONMENT READY"
Write-Host "  python:   $pyVer"
Write-Host "  uv:       $uvVersion"
Write-Host "  venv:     $(Split-Path (Split-Path $venvPython))"
Write-Host "  store:    $pythonDir"
Write-Host "  cache:    $cacheDir"
Write-Host "  browsers: $browsersPath"
exit 0
