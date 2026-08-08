# 11 — Integration Handoff

**Department:** Shared Platform & Core
**Goal:** Developer Environment Reproducibility Foundation
**Date:** 2026-08-08

## 1. Handoff summary

| Item | Value |
| --- | --- |
| Starting baseline | `4d9e56d659541f27a3c0305d4fa19a587ef6cbc6` (Wave-1 Integrated Baseline) |
| Final department HEAD | see closure commit below (branch `dept/shared-core-environment`) |
| Canonical Python policy | `requires-python ">=3.11,<3.13"` |
| Preferred Python runtime | 3.12.13 (exact pin `.python-version`) |
| Supported Python range | 3.11 (supported; full-core verified this Goal) and 3.12 (preferred; full-core verified); ≥3.13 unsupported (untested) |
| Python 3.11 debt disposition | **Option B, now closed**: full non-live core on 3.11.15 → 1851/8/0, exit 0 (Wave-1 follow-up executed) |
| uv ownership/version | user-space uv (0.12.x minimum); provisioning in bootstrap; dependency mutation single-owner: Shared Platform & Core |
| Authoritative dependency files | `pyproject.toml` → `uv.lock` (87 packages) → worktree `.venv`; `requirements.txt`/`requirements-nlp.txt` = drift-guarded COMPATIBILITY EXPORT |
| Runtime architecture | **Candidate C**: worktree-local `.venv` + shared uv runtime/cache stores (uv-locked); no central venv; no sibling `.pth` links |
| Worktree environment location | `<worktree>\.venv` (gitignored); store/cache/browser paths probed with fallbacks |
| Bootstrap command | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\dev\bootstrap_environment.ps1` (idempotent) |
| Verification command | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\dev\verify_environment.ps1` (read-only; `-Json`) |
| Test invocation command | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\dev\run_tests.ps1 [-Full | -Targets …]` |
| External resource policy | spaCy model via lock (nlp group); Playwright/Chromium via probed store + documented install command; corpus data verification-only (owner Corpus & NLP) |
| Parallel-agent safety | per-worktree writes disjoint; uv self-locks shared stores (concurrent bootstrap evidence); browsers/cache lifecycle single-owner |
| CI/local parity | one contract (`uv sync` from lock, same runner); future CI contract documented; no CI platform created |
| Windows-specific findings | sandbox-vs-machine ACL distinction; uv venv launcher depends on interpreter store; Playwright store probe via playwright's own resolution; LF pins (`.gitattributes`) for machine-readable files; CRLF policy-hash debt re-confirmed (Research owner) |
| Environment drift guards | `tests/test_environment_drift.py` — 10 checks, all passing (includes 3.11 syntax gate) |
| Product regression | full non-live core 3.12: **1851/8/0** exit 0; 3.11: **1851/8/0** exit 0; focused suites 604; launcher PASS; no product behavior change |
| Files likely to conflict | `run.bat`, `README.md`, `INSTALL.md` (launcher/docs migration); `verification/v0.9.5-h2a/isolated_pytest_runner.py` (fresh-worktree dev-DB guard); `tests/test_v096dp0_v2_launcher_isolation.py` (label alignment) |

## 2. Verification recipe for Architecture & Integration

On any department worktree (fresh checkout, no environment):

```powershell
cd <worktree>
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\dev\bootstrap_environment.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\dev\verify_environment.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\dev\run_tests.ps1 -Full
cmd /c run.bat --verify
```

Expected: `ENVIRONMENT READY` (bootstrap + verify), full core **1851 passed / 8 skipped /
0 failed / exit 0** (isolated temp DB; dev DB untouched), launcher PASS. If any step reports a
code (`UV_NOT_AVAILABLE`, `PYTHON_RUNTIME_MISSING`, `VENV_INTERPRETER_BROKEN`,
`DEPENDENCY_SYNC_FAILED`, `LOCKFILE_DRIFT`, `RESOURCE_MISSING`, `PERMISSION_DENIED`), follow the
repair table in 05_BOOTSTRAP_AND_VERIFICATION.md.

Notes for the integration gate:
- This Goal is **DEPARTMENT GREEN only**; the cross-department Integration Gate is NOT claimed.
- The CRLF policy-hash issue (2 governance tests) requires the recorded Research Evaluation
  fix or the local LF materialization workaround before a fresh Windows checkout passes those
  two tests; on any CI that checks out LF, they pass natively.
- Browser suites require the Playwright store; on restricted agents set the documented
  `PLAYWRIGHT_BROWSERS_PATH` policy or run with normal user rights.

## 3. Integration-only follow-ups (not done here)

- Cross-department compatibility re-verification of the environment contract (Architecture &
  Integration, next Integration Gate).
- Research Evaluation: policy-artifact hash robustness to checkout line endings (unchanged
  owner; Wave-1 follow-up still open).
- Corpus & NLP: corpus-owned scripts carry machine-specific absolute paths
  (`scripts/corpus_readiness/*` CORPUS_ROOT/REPO_ROOT, `scripts/corpus_intelligence/build_stage5.py`
  `sys.path.insert` of the main checkout `A:\EAP Agent Project\writing-feedback-mvp`) — these
  break on fresh clones; allowlisted in the drift guard with owner Corpus & NLP.
- Future CI introduction must consume `uv.lock` with `uv sync --locked` per 08 doc.
- Optional: persist user-level env overrides (`UV_PYTHON_INSTALL_DIR` etc.) on machines with
  genuinely broken default stores (bootstrap already handles per-invocation).
