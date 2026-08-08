#Requires -Version 5.1
# uv_helpers.ps1 - Dot-sourced helper library for environment bootstrap/verify/run_tests.
# ASCII-only, PowerShell 5.1 compatible.

# ---------------------------------------------------------------------------
# Get-RepoRoot
# ---------------------------------------------------------------------------
function Get-RepoRoot {
    # Resolve from this script's location; parent[1] is the worktree root.
    $scriptDir = Split-Path -Parent $MyInvocation.ScriptName
    if (-not $scriptDir) {
        # Fallback: assume scripts/dev relative to cwd
        $scriptDir = Join-Path (Get-Location) "scripts\dev"
    }
    $parent1 = Split-Path -Parent $scriptDir   # scripts\
    $parent2 = Split-Path -Parent $parent1      # worktree root
    return $parent2
}

# ---------------------------------------------------------------------------
# Find-Uv
# ---------------------------------------------------------------------------
function Find-Uv {
    # 1. Honor explicit override
    if ($env:WF_UV_EXE -and (Test-Path $env:WF_UV_EXE)) {
        return (Resolve-Path $env:WF_UV_EXE).Path
    }
    # 2. Get-Command uv
    try {
        $cmd = Get-Command uv -ErrorAction Stop
        if ($cmd.Source) { return $cmd.Source }
    } catch {}
    # 3. Known user-space locations
    $localBin = Join-Path $env:USERPROFILE ".local\bin\uv.exe"
    if (Test-Path $localBin) { return $localBin }
    return $null
}

# ---------------------------------------------------------------------------
# Test-PathHealthy
# ---------------------------------------------------------------------------
function Test-PathHealthy {
    param([string]$Path)
    if (-not (Test-Path $Path)) { return $false }
    try {
        $null = Get-ChildItem -Path $Path -Force -ErrorAction Stop
        return $true
    } catch {
        return $false
    }
}

# ---------------------------------------------------------------------------
# Test-PathWritable - creates and removes a probe file (bootstrap use only;
# the verifier is read-only and must never call this).
# ---------------------------------------------------------------------------
function Test-PathWritable {
    param([string]$Path)
    if (-not (Test-Path $Path)) { return $false }
    $probe = Join-Path $Path (".wfm-write-probe-" + [System.Guid]::NewGuid().ToString("N"))
    try {
        $null = [System.IO.File]::Open($probe, [System.IO.FileMode]::CreateNew,
            [System.IO.FileAccess]::Write, [System.IO.FileShare]::None).Close()
        Remove-Item -LiteralPath $probe -Force -ErrorAction Stop
        return $true
    } catch {
        return $false
    }
}

# ---------------------------------------------------------------------------
# Resolve-UvPythonInstallDir
# ---------------------------------------------------------------------------
function Resolve-UvPythonInstallDir {
    param([switch]$ProbeWritable)
    $defaultDir = Join-Path $env:APPDATA "uv\python"
    if (Test-PathHealthy $defaultDir) {
        if (-not $ProbeWritable -or (Test-PathWritable $defaultDir)) {
            $script:UV_PYTHON_INSTALL_DIR = $defaultDir
            return $defaultDir
        }
    }
    $fallback = Join-Path $env:USERPROFILE ".uv-python"
    $script:UV_PYTHON_INSTALL_DIR = $fallback
    return $fallback
}

# ---------------------------------------------------------------------------
# Resolve-UvCacheDir
# ---------------------------------------------------------------------------
function Resolve-UvCacheDir {
    param([switch]$ProbeWritable)
    $defaultCache = Join-Path $env:LOCALAPPDATA "uv\cache"
    if (Test-PathHealthy $defaultCache) {
        if (-not $ProbeWritable -or (Test-PathWritable $defaultCache)) {
            $script:UV_CACHE_DIR = $defaultCache
            return $defaultCache
        }
    }
    $fallback = Join-Path $env:USERPROFILE ".uv-cache"
    # Try to create fallback if it doesn't exist
    if (-not (Test-Path $fallback)) {
        try {
            $null = New-Item -ItemType Directory -Path $fallback -Force -ErrorAction Stop
        } catch {
            # If we can't create it, use it anyway (uv will report error)
        }
    }
    $script:UV_CACHE_DIR = $fallback
    return $fallback
}

# ---------------------------------------------------------------------------
# Resolve-BrowsersPath
# ---------------------------------------------------------------------------
function Resolve-BrowsersPath {
    param([switch]$ProbeWritable)
    if ($env:WF_PLAYWRIGHT_BROWSERS_PATH -and (Test-Path $env:WF_PLAYWRIGHT_BROWSERS_PATH)) {
        $script:PLAYWRIGHT_BROWSERS_PATH = $env:WF_PLAYWRIGHT_BROWSERS_PATH
        return $env:WF_PLAYWRIGHT_BROWSERS_PATH
    }
    # Prefer the machine-default Playwright store when it is healthy
    # (mirrors the uv store/cache probe policy).
    $defaultStore = Join-Path $env:LOCALAPPDATA "ms-playwright"
    if (Test-PathHealthy $defaultStore) {
        if (-not $ProbeWritable -or (Test-PathWritable $defaultStore)) {
            $script:PLAYWRIGHT_BROWSERS_PATH = $defaultStore
            return $defaultStore
        }
    }
    $default = Join-Path $env:USERPROFILE ".cache\wfm-ms-playwright"
    $script:PLAYWRIGHT_BROWSERS_PATH = $default
    return $default
}

# ---------------------------------------------------------------------------
# Get-VenvPython
# ---------------------------------------------------------------------------
function Get-VenvPython {
    $repoRoot = Get-RepoRoot
    $venvDir = $env:WF_VENV_PATH
    if (-not $venvDir) {
        $venvDir = Join-Path $repoRoot ".venv"
    } elseif (-not [System.IO.Path]::IsPathRooted($venvDir)) {
        $venvDir = Join-Path $repoRoot $venvDir
    }
    return Join-Path $venvDir "Scripts\python.exe"
}

# ---------------------------------------------------------------------------
# Test-VenvHealthy
# ---------------------------------------------------------------------------
function Test-VenvHealthy {
    $venvPython = Get-VenvPython
    $result = @{ Healthy = $false; Version = ""; Reason = "" }

    if (-not (Test-Path $venvPython)) {
        $result.Reason = "python.exe not found at $venvPython"
        return $result
    }

    # Run version check
    try {
        $out = & $venvPython -c "import sys; print(sys.version_info[:2])" 2>&1
        if ($LASTEXITCODE -ne 0) { throw "exit code $LASTEXITCODE" }
        $result.Version = ($out | Out-String).Trim()
    } catch {
        $result.Reason = "python.exe does not execute: $($_.Exception.Message)"
        return $result
    }

    # Check pyvenv.cfg
    $cfg = Join-Path (Split-Path $venvPython) "..\pyvenv.cfg" | Resolve-Path -ErrorAction SilentlyContinue
    if (-not $cfg -or -not (Test-Path $cfg)) {
        $result.Reason = "pyvenv.cfg not found"
        return $result
    }

    $result.Healthy = $true
    $result.Reason = "OK"
    return $result
}

# ---------------------------------------------------------------------------
# Remove-VenvLongPath
# ---------------------------------------------------------------------------
function Remove-VenvLongPath {
    param([string]$Path)
    $fullPath = (Resolve-Path $Path -ErrorAction SilentlyContinue)
    if (-not $fullPath) { return }
    $fullStr = $fullPath.Path
    # Prefix with \\?\ for long-path support (full absolute path required)
    $longPath = "\\?\" + $fullStr.TrimEnd('\')
    try {
        [System.IO.Directory]::Delete($longPath, $true)
    } catch {
        # Fallback: try without prefix (short paths)
        try {
            [System.IO.Directory]::Delete($fullStr, $true)
        } catch {
            Write-Warning "Remove-VenvLongPath: failed to delete ${fullStr}: $($_.Exception.Message)"
        }
    }
}

# ---------------------------------------------------------------------------
# Assert-Script
# ---------------------------------------------------------------------------
function Assert-Script {
    param([string]$ScriptPath)
    if (-not (Test-Path $ScriptPath)) {
        throw "Assert-Script: file not found: $ScriptPath"
    }
    . $ScriptPath
}
