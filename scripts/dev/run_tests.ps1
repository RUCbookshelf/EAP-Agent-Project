#Requires -Version 5.1
# run_tests.ps1 - Canonical test launcher.
# ASCII-only, PowerShell 5.1 compatible.
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\dev\run_tests.ps1 [-Full] [-Targets path1,path2] [pytest args...]

param(
    [switch]$Full,
    [string[]]$Targets,
    [Parameter(ValueFromRemainingArguments)]
    $PytestArgs
)

# `powershell -File` binds comma-separated values as a single string;
# normalize so both `-Targets a.py,b.py` and repeated `-Targets` work.
if ($Targets) {
    $normalized = @()
    foreach ($t in $Targets) {
        if ($t -match ',') {
            $normalized += ($t -split ',' | ForEach-Object { $_.Trim() })
        } else {
            $normalized += $t
        }
    }
    $Targets = $normalized
}

$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# 0. Resolve repo root and helpers
# ---------------------------------------------------------------------------
$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repoRoot
$helpersPath = Join-Path $repoRoot "scripts\dev\uv_helpers.ps1"
. $helpersPath

# ---------------------------------------------------------------------------
# 1. Bootstrap environment (idempotent)
# ---------------------------------------------------------------------------
$bootstrapScript = Join-Path $repoRoot "scripts\dev\bootstrap_environment.ps1"
& $bootstrapScript
if ($LASTEXITCODE -ne 0) {
    Write-Host "BOOTSTRAP_FAILED: environment bootstrap failed (see messages above)"
    exit 1
}

# ---------------------------------------------------------------------------
# 2. Verify venv python exists
# ---------------------------------------------------------------------------
$venvPython = Get-VenvPython
if (-not (Test-Path $venvPython)) {
    Write-Host "VENV_MISSING: $venvPython does not exist"
    Write-Host "  Run: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\dev\bootstrap_environment.ps1"
    exit 1
}

# ---------------------------------------------------------------------------
# 3. Set environment variables from helpers
# ---------------------------------------------------------------------------
$pythonDir = Resolve-UvPythonInstallDir
$cacheDir  = Resolve-UvCacheDir
$browsersPath = Resolve-BrowsersPath
$env:UV_PYTHON_INSTALL_DIR = $pythonDir
$env:UV_CACHE_DIR          = $cacheDir
$env:PLAYWRIGHT_BROWSERS_PATH = $browsersPath

# ---------------------------------------------------------------------------
# 4. Run tests (all modes route through the isolated runner so DB isolation,
#    dev-DB digest guard, ports check, and LLM_PROVIDER=local always apply)
# ---------------------------------------------------------------------------
$runnerScript = Join-Path $repoRoot "verification\v0.9.5-h2a\isolated_pytest_runner.py"
if (-not (Test-Path $runnerScript)) {
    Write-Host "ERROR: isolated_pytest_runner.py not found at $runnerScript"
    exit 1
}

if ($Full -or -not $Targets) {
    # Full non-live core (default mode is the same canonical suite)
    & $venvPython $runnerScript --full
    exit $LASTEXITCODE
}

if (-not $PytestArgs) {
    # Focused targets through the isolated runner
    & $venvPython $runnerScript --targets @Targets
    exit $LASTEXITCODE
}

# Advanced mode: extra pytest arguments (e.g. -k) cannot pass through the
# runner; run direct pytest with the same database-isolation environment
# (fresh temp DB outside the repository, LLM_PROVIDER=local). The dev-DB
# digest guard does not apply in this advanced mode.
$tmpDb = Join-Path $env:TEMP ("wfm-run-{0}.db" -f ([System.Guid]::NewGuid().ToString("N")))
$env:PYTHON_DOTENV_DISABLED = "1"
Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
$env:DATABASE_PATH = $tmpDb
$env:LLM_PROVIDER = "local"
Write-Host "WARNING: advanced pytest-args mode uses isolated temp DB ($tmpDb) without the dev-DB digest guard."
$pytestArgsList = @("-m", "pytest", "-q", "-p", "no:cacheprovider")
foreach ($t in $Targets) { $pytestArgsList += $t }
foreach ($arg in $PytestArgs) { $pytestArgsList += $arg }
& $venvPython @pytestArgsList
$code = $LASTEXITCODE
Remove-Item -LiteralPath $tmpDb -Force -ErrorAction SilentlyContinue
exit $code
