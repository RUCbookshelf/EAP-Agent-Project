# 05 — Bootstrap and Verification

**Department:** Shared Platform & Core
**Goal:** Developer Environment Reproducibility Foundation
**Date:** 2026-08-08

## 1. Purpose

This document defines the three canonical commands for environment setup, verification, and
testing. They make a newly opened worktree reach one of two deterministic outcomes —
`ENVIRONMENT READY` or `ENVIRONMENT NOT READY <precise reason>` — without searching sibling
worktrees for a usable environment.

## 2. Commands

### 2.1 Bootstrap environment (provisions; idempotent)

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\dev\bootstrap_environment.ps1"
```

Expected output on a healthy environment:

```text
[bootstrap] repository root: A:\EAP Agent Project\worktrees\shared-core-environment
[bootstrap] uv found at: C:\Users\16073\.local\bin\uv.exe
[bootstrap] uv version: uv 0.12.3
[bootstrap] UV_PYTHON_INSTALL_DIR = C:\Users\16073\AppData\Roaming\uv\python
[bootstrap] UV_CACHE_DIR = C:\Users\16073\AppData\Local\uv\cache
[bootstrap] PLAYWRIGHT_BROWSERS_PATH = C:\Users\16073\AppData\Local\ms-playwright
[bootstrap] managed Python 3.12.13 located: <store>\cpython-3.12.13-windows-x86_64-none\python.exe
[bootstrap] venv healthy: (3, 12)
[bootstrap] interpreter verified: Python 3.12.13
[bootstrap] pytest available
[bootstrap] NLP resources: {"status": "PASS", ...}
[bootstrap] git: git version 2.x.x

ENVIRONMENT READY
  python:   3.12.13
  uv:       uv 0.12.3
  venv:     A:\EAP Agent Project\worktrees\shared-core-environment\.venv
  store:    C:\Users\16073\AppData\Roaming\uv\python
  cache:    C:\Users\16073\AppData\Local\uv\cache
  browsers: C:\Users\16073\AppData\Local\ms-playwright
```

Store/cache/browser paths are probed: machine defaults are preferred when healthy; user-level
fallbacks are used when a default is unusable in the current context (restricted agent contexts
on this machine provision into `C:\Users\16073\.uv-python`, `C:\Users\16073\.uv-cache`, and
`C:\Users\16073\.cache\wfm-ms-playwright`). The bootstrap probes **writability** (probe file)
before selecting a store/cache; the verifier is read-only and reports path readability only.
The example paths above are this machine's recorded values, not the contract.

### 2.2 Verify environment (read-only)

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\dev\verify_environment.ps1"
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\dev\verify_environment.ps1" -Json
```

The verifier NEVER mutates the environment. It reports repository/worktree identity, branch,
Python executable and version, uv version, environment location, dependency-lock status,
pytest availability, application import, SQLite tooling, spaCy/model status, Playwright/
Chromium status, and launcher prerequisites (ports 8000/8501 free). It terminates with exactly
`ENVIRONMENT READY` (exit 0) or `ENVIRONMENT NOT READY` with the failed checks (exit 1).

### 2.3 Run tests (canonical launcher)

```powershell
# focused/default (tests minus tests/live)
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\dev\run_tests.ps1"
# specific targets
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\dev\run_tests.ps1" -Targets tests/test_v095h2a_removed_contracts.py
# full non-live core via the isolated runner
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\dev\run_tests.ps1" -Full
# pass-through pytest arguments
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\dev\run_tests.ps1" -Targets tests/test_analyzer.py -v -k "spacy"
```

The launcher bootstraps first (idempotent), then invokes the worktree `.venv` interpreter
explicitly — never a PATH python.

## 3. Failure codes

| Code | Meaning | Repair |
| --- | --- | --- |
| `UNSUPPORTED_OS` | bootstrap requires Windows (Win32NT) | run on a Windows machine |
| `UV_NOT_AVAILABLE` | uv binary not found | install uv 0.12.x user-space (official installer or `python -m pip install uv`) and re-run |
| `PYTHON_RUNTIME_MISSING` | managed Python 3.12.13 not found or failed | `uv python install 3.12.13` (about 21 MB), then re-run bootstrap |
| `UV_CACHE_UNUSABLE` | uv cache cannot initialize | ensure write access to `UV_CACHE_DIR` or set a writable one; bootstrap falls back |
| `VENV_INTERPRETER_BROKEN` | venv python.exe does not execute / pyvenv.cfg missing | bootstrap auto-rebuilds (long-path-safe); manual: remove `.venv` and `uv sync` |
| `DEPENDENCY_SYNC_FAILED` | `uv sync` failed or pytest not importable | check network, run `uv sync`; inspect error output |
| `LOCKFILE_DRIFT` | `uv sync --check` found changes not in the lock | Shared Platform & Core regenerates and commits `uv.lock` with a verification record |
| `RESOURCE_MISSING` | Chromium or another required resource absent | `python -m playwright install chromium` with the contract's `PLAYWRIGHT_BROWSERS_PATH` |
| `VENV_MISSING` | `.venv\Scripts\python.exe` does not exist | run the bootstrap |
| `GIT_NOT_AVAILABLE` | git is not usable (parity tests spawn git subprocesses) | install Git for Windows / fix PATH |
| `PERMISSION_DENIED` | access denied to user-level stores | run with normal user rights; bootstrap falls back to alternative user locations |

## 4. Idempotence

- **bootstrap**: on a correct environment, `uv sync` is a fast no-op, `uv sync --check` passes,
  and no downloads, rebuilds, or mutations occur. A second run changes nothing.
- **verify**: read-only by construction.
- **run_tests**: bootstraps first (idempotent), then runs pytest; no environment mutation
  beyond normal test artifacts.

## 5. Restricted-context behavior

- The verifier is read-only and works in restricted agent contexts (everything it needs is
  inside the worktree or is probed tolerantly; `uv lock --check` reports
  `LOCK_CHECK_UNAVAILABLE` instead of failing when the uv cache is inaccessible).
- The bootstrap provisions user-level stores and therefore needs normal user rights; in fully
  restricted contexts it fails with an actionable code rather than a generic message.

## 6. Environment variables

| Variable | Purpose | Default | Override |
| --- | --- | --- | --- |
| `WF_UV_EXE` | explicit uv.exe path | auto-discovered | set to override discovery |
| `WF_VENV_PATH` | worktree venv path | `<repo root>\.venv` | set for a custom venv location; the bootstrap routes `uv sync` there via `UV_PROJECT_ENVIRONMENT` |
| `UV_PYTHON_INSTALL_DIR` | managed Python runtime store | `%APPDATA%\uv\python` | fallback `~\.uv-python` |
| `UV_CACHE_DIR` | uv package cache | `%LOCALAPPDATA%\uv\cache` | fallback `~\.uv-cache` |
| `PLAYWRIGHT_BROWSERS_PATH` / `WF_PLAYWRIGHT_BROWSERS_PATH` | Playwright browser binaries | `%LOCALAPPDATA%\ms-playwright` when healthy, else `~\.cache\wfm-ms-playwright` | set to override |
| `WRITING_FEEDBACK_VENV` | legacy venv path (run.bat) | `.venv` | mapped to `WF_VENV_PATH` |
| `WRITING_FEEDBACK_ENV_FILE` | custom .env path (run.bat) | `.env` | set to override |

## 7. Gate statement

**WU5/WU6/WU11 implementation delivered; executable verification (bootstrap idempotence,
verifier output, focused tests, broken-state repair) is recorded in 10_VERIFICATION.md (WU8/WU13).**
