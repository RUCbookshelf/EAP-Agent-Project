# 10 — Verification

**Department:** Shared Platform & Core
**Goal:** Developer Environment Reproducibility Foundation
**Date:** 2026-08-08

All verification below ran through the **canonical environment workflow** (bootstrap → verify →
launcher), never a borrowed sibling `.venv`.

## 1. Canonical environment (as executed)

| Item | Value |
| --- | --- |
| Python | 3.12.13 (uv-managed, per `.python-version`; venv at worktree root) |
| uv | 0.12.3 (user-space, `C:\Users\16073\.local\bin\uv.exe`) |
| Environment path | `A:\EAP Agent Project\worktrees\shared-core-environment\.venv` |
| Runtime store | `%APPDATA%\uv\python` (machine-healthy; restricted contexts use `C:\Users\16073\.uv-python`) |
| uv cache | `%LOCALAPPDATA%\uv\cache` |
| Playwright store | `%LOCALAPPDATA%\ms-playwright` (chromium-1228, machine-healthy) |
| Lockfile | `uv.lock` (87 packages, revision 3); `uv sync --check` → no changes; `uv lock --check` → clean |

## 2. Commands and results

| Gate | Command (canonical) | Result |
| --- | --- | --- |
| Bootstrap (idempotent) | `powershell -File scripts\dev\bootstrap_environment.ps1` | `ENVIRONMENT READY`, exit 0, twice on the same worktree — second run made no changes |
| Verifier | `powershell -File scripts\dev\verify_environment.ps1` | `ENVIRONMENT READY`, exit 0 (machine-level); in restricted sandbox: `ENVIRONMENT NOT READY` with precise reason (`RESOURCE_MISSING` browsers / interpreter store) |
| Fresh-worktree bootstrap | disposable worktree `wu8-environment-test` (branch `codex/wu8-env-test`, HEAD 9f1682d, no `.venv`) | `ENVIRONMENT READY` from zero; verify READY; focused 13 passed; broken venv (python.exe renamed) → `VENV_INTERPRETER_BROKEN` → auto-rebuild → READY; second bootstrap idempotent; worktree removed |
| Parallel safety | bootstrap + verify simultaneously in two worktrees | both bootstraps `ENVIRONMENT READY`; verifiers completed without interference |
| Shared Core focused | `tests/shared tests/test_composition_root.py tests/test_shared_core_drift.py` | **175 passed** |
| Research Governance | `tests/test_research_governance_v01.py` | **28 passed** (after recorded LF workaround, §5) |
| Corpus Stage-5 | `tests/corpus` | **36 passed** |
| Academic | `tests/academic` | **322 passed** |
| Wave-1 contract gates | `tests/contracts` | **43 passed** |
| **Full non-live core (3.12)** | `scripts\dev\run_tests.ps1 -Full` → `isolated_pytest_runner.py --full` | **1851 passed / 8 skipped / 0 failed / exit 0 / 882 s**; isolated temp DB; dev DB guard: absent before/after (not created) |
| **Full non-live core (3.11)** | same runner with Python 3.11.15 check env (temp venv, pinned deps) | **1851 passed / 8 skipped / 0 failed / exit 0 / 883 s** — Wave-1 recorded 3.11 debt CLOSED |
| Launcher / startup | `cmd /c run.bat --verify` | PASS — bootstrap → migrate → initialize → smoke_stack (health/docs/Streamlit 200), auto-provisioned temp DB, exit 0 |
| Locale parity | in-core `test_feature_locale_keys_resolve_and_parity_holds` | PASS (part of the 1851; zero locale file changes) |
| Drift guards | `tests/test_environment_drift.py` | **10/10 passed** |
| DB mutation | isolated runners + `verify_launcher` DATABASE_URL guard | dev DB never touched; temp DBs only |

Collected count note: 1859 collected (1851 + 8 skipped) vs Wave-1's 1845 — the +14 are the 10 new
environment drift guards plus additional collected tests in the integrated baseline; all
pre-existing suites pass unchanged.

## 3. Focused-suite totals (3.12 canonical)

175 + 28 + 36 + 322 + 43 = **604 focused tests passed**; plus drift guards 10/10.

## 4. Intentional changes to tracked verification/test files

1. `verification/v0.9.5-h2a/isolated_pytest_runner.py` — dev-DB guard now handles a fresh
   worktree where `data/writing_feedback.db` does not exist (before/after = None; creating the
   dev DB during verification fails the run). Environment-scoped robustness; no product change.
2. `tests/test_v096dp0_v2_launcher_isolation.py` — one assertion aligned to the migrated
   launcher: the `:python_missing` label (removed with the Python 3.11 hard requirement) became
   `:bootstrap_failed`; the asserted invariant (verify_launcher only in the `--verify` branch)
   is unchanged. Suite 22/22 passes.

## 5. Environment limitations / recorded follow-ups

1. **CRLF policy-artifact hashing (Research Evaluation owner, unchanged from Wave-1):** the
   research-governance registry hashes policy JSON artifacts on LF content; a fresh checkout
   with `core.autocrlf=true` materializes CRLF and the two registry-consistency tests fail.
   This Goal used the Wave-1-recorded local workaround (LF materialization during verification,
   then restore; no committed change). The underlying fix (`.gitattributes`/LF policy) remains
   owned by Research Evaluation per Wave-1 handoff.
2. **Sandbox-vs-machine ACL distinction:** user-level stores (`%APPDATA%\uv\python`,
   `%LOCALAPPDATA%\uv\cache`, `%LOCALAPPDATA%\ms-playwright`) are machine-healthy but
   restricted-context-inaccessible; the contract probes and falls back, and verification
   reports precise codes rather than failing generically. uv-created Windows venvs launch the
   base interpreter from the store, so store accessibility is part of venv health.
3. **Hermes git shadowing (machine-level):** recorded by Wave-1; parity tests spawn `git`;
   the verifier checks git availability explicitly.
4. **Python 3.11:** supported range; canonical 3.11 full-core re-run completed (this Goal) —
   the recorded Wave-1 follow-up is closed. 3.13+ remains untested/unsupported.

## 6. Gate statement

**WU13 GREEN — all department focused suites, the full non-live core on the canonical 3.12.13
environment (1851/8/0), the Python 3.11 canonical re-run (1851/8/0), launcher/startup
verification, locale parity, and drift guards pass; dev-DB isolation holds; product behavior
is unchanged (only documented verification/test alignments).**

## 7. Post-final-review revalidation (same session)

After the fresh independent review (APPROVE_WITH_FINDINGS), all findings were resolved and the
affected tooling revalidated: bootstrap (lock-first enforcement, writability probes,
`UV_PROJECT_ENVIRONMENT` routing) → `ENVIRONMENT READY`, no changes; verifier (version-range
check + store/cache/browser readability) → `ENVIRONMENT READY`; focused tests via the isolated
runner (temp DB + digest guard) → PASS; `run.bat --verify` → PASS; `WF_VENV_PATH` custom-venv
bootstrap → `ENVIRONMENT READY` (custom path honored); drift guards → 10/10. No product code or
test behavior changed, so the full-core totals above remain the canonical record.
