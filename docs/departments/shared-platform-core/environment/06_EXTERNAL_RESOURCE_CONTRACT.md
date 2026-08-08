# 06 — External Resource Contract

**Department:** Shared Platform & Core
**Goal:** Developer Environment Reproducibility Foundation
**Date:** 2026-08-08

Python packages are not the only runtime dependencies. This contract defines every external
resource required by repository development/verification.

## 1. Resource registry

| Resource | Owner | Version | Required for | Bootstrap behavior | Verification behavior | Storage location | Offline behavior | Failure state |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| spaCy model `en_core_web_sm` | Shared Platform & Core (via lock) | 3.8.0 | default analyzer `spacy-analyzer-v0.8.0`; NLP metrics | `uv sync` (`nlp` group, default) | `scripts/verify_nlp_resources.py` (import + load + metadata version); verifier reports `RESOURCE_MISSING`/`FALLBACK_AVAILABLE` | worktree `.venv` site-packages (from lock) | documented `BasicAnalyzer` fallback; health reports fallback | `FALLBACK_AVAILABLE` (product works degraded); `--require-model` exits non-zero |
| Playwright 1.61.0 + Chromium | Shared Platform & Core | playwright 1.61.0; Chromium pinned by the package | browser/DOM suites inside the non-live core; `tests/live` (excluded from core) | `uv sync` (dev group) installs the driver; `python -m playwright install chromium` with `PLAYWRIGHT_BROWSERS_PATH` set (never the ACL-broken default store on this machine) | verifier checks `playwright` import and the Chromium executable path; reports `RESOURCE_MISSING` with the exact install command | user-level writable directory: `$env:USERPROFILE\.cache\wfm-ms-playwright` (override `WF_PLAYWRIGHT_BROWSERS_PATH`); browsers are immutable after install, shared read-mostly across worktrees | verify succeeds without browsers (reports not-ready for browser suites with actionable install command); browser tests fail with explicit message | `RESOURCE_MISSING` (actionable: run the documented install command) |
| SQLite | Shared Platform & Core (stdlib) | Python stdlib `sqlite3` | persistence layer, migrations, research exports | none | verifier imports `sqlite3` and reports `sqlite3.sqlite_version` | interpreter stdlib | always available | n/a |
| Node/npm | not required by this repository's Python product/tests | — | — | — | informational only | — | — | — |
| Corpus source data / licensed packages | **Corpus & NLP** | corpus-owned | Corpus Stage-5 tests and readiness scripts (36 tests in core) | **NEVER provisioned, copied, or redistributed by the environment layer** | presence-only check where an authorized test genuinely requires it; absence surfaces as `RESOURCE_MISSING` for that test | corpus-owned locations | corpus tests that require data fail with an actionable message | `RESOURCE_MISSING` (corpus-owned; environment does not repair) |

## 2. Key policies

1. **Corpus data is not an ordinary developer dependency.** The environment layer only verifies
   its configured presence where an authorized test requires it, and never downloads, copies, or
   provisions it. Licensing/distribution decisions belong to Corpus & NLP
   (Goal §5, §13, §26).
2. **Browser storage is explicit.** The default `%LOCALAPPDATA%\ms-playwright` store is
   machine-healthy on this machine (chromium-1228 installed) but sandbox-restricted, so every
   environment command that needs browsers sets `PLAYWRIGHT_BROWSERS_PATH` deterministically
   (user-level writable directory; fallback for restricted contexts). The bootstrap, verifier,
   and test launcher share one documented override point (`WF_PLAYWRIGHT_BROWSERS_PATH`).
3. **Downloads are reported, not silent.** Any resource download performed by the bootstrap
   prints what it is downloading, from where, and its size; large resources are never fetched
   without the operator seeing it.
4. **Failure states are actionable.** Every resource has a defined failure state and a repair
   command (e.g., `python -m playwright install chromium`; `uv sync`).
5. **NLP model stays in the lock.** `en_core_web_sm` is a locked dependency (GitHub wheel,
   hash-pinned by uv.lock), so it is reproducible per worktree and never shared-mutable.

## 3. Machine-specific notes (recorded, not hidden)

- `%LOCALAPPDATA%\ms-playwright` is sandbox-restricted but machine-healthy on this machine;
  the override makes browser usage deterministic in both contexts.
- The uv-managed Python store default path is ACL-broken → `UV_PYTHON_INSTALL_DIR` override to a
  healthy user directory (see 03/04 docs).
- `D:\Python\python.exe` (CPython 3.14.4) exists on this machine but is outside the supported
  range and is never selected by the contract.

## 4. Gate statement

**WU7 GREEN (draft) — every external resource has an owner, version, required-for, bootstrap and
verification behavior, storage location, offline behavior, and failure state; corpus data is
verification-only; downloads are reported.**
