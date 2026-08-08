# 00 — Environment Foundation Executive Summary

**Department:** Shared Platform & Core
**Goal:** Developer Environment Reproducibility Foundation
**Date:** 2026-08-08
**Baseline:** `4d9e56d` (Wave-1 Integrated Baseline) → final department HEAD (see 11 doc)

## What was delivered

A deterministic, worktree-safe developer environment contract for the whole repository, so a
newly opened department worktree reaches `ENVIRONMENT READY` or a precise `ENVIRONMENT NOT
READY` reason with one documented command — never by searching sibling worktrees for a working
`.venv`.

## Why it was needed (Wave-1 debt)

Wave-1 completed the integrated baseline (1837/8/0) by borrowing `shared-core-h1\.venv` through
a `.pth` link (`architecture-integration\.venv\_wave1_integration_shared_site.pth`) and recorded
Python/runtime reproducibility as environment debt. Symptoms: no `python`/`py`/`uv` on PATH,
venvs pointing at an interpreter store agents could not access, a missing uv toolchain, an
ACL-restricted Playwright store, and no lockfile — dependency drift was undetectable.

## What was built

| Artifact | Purpose |
| --- | --- |
| `pyproject.toml` + `uv.lock` (87 packages) | authoritative dependency chain; requirements*.txt = drift-guarded compatibility exports |
| `.python-version` (3.12.13) + `requires-python ">=3.11,<3.13"` | explicit, machine-readable Python policy (Option B for the 3.11 debt) |
| `scripts/dev/bootstrap_environment.ps1` | idempotent provisioning: uv discovery, store/cache/browser path probing with fallbacks, managed Python, venv health/rebuild, `uv sync` + drift check, deterministic failure codes |
| `scripts/dev/verify_environment.ps1` | read-only verifier (`ENVIRONMENT READY`/`NOT READY`, `--json`) |
| `scripts/dev/run_tests.ps1` | canonical test launcher (focused/default/full) over the authorized venv |
| `run.bat` migration | launcher delegates to the bootstrap; `--verify`/`--install-only` semantics preserved; Python 3.11 hard requirement removed |
| `tests/test_environment_drift.py` | 10 drift guards (version pins, lock consistency, no sibling `.venv` refs, no machine-specific paths, 3.11 syntax gate) |
| 12 environment contract docs | `00`–`11` under `docs/departments/shared-platform-core/environment/` |

## Key results

- Architecture: **Candidate C** — worktree-local `.venv` + shared uv runtime/cache stores
  (uv-locked), approved by fresh independent review.
- Clean disposable worktree bootstrapped from zero → `ENVIRONMENT READY`; broken venv repaired
  deterministically; second bootstrap idempotent.
- Two worktrees bootstrap/verify concurrently with no interference (uv self-locking).
- Full non-live core through the canonical environment: **1851 passed / 8 skipped / 0 failed,
  exit 0** on Python 3.12.13 (isolated DB; dev DB untouched).
- Python 3.11 debt closed: canonical full-core re-run on Python 3.11.15 (Wave-1 recorded
  follow-up, interpreter now available) — see 10 doc.
- Launcher/startup: `run.bat --verify` PASS (auto-provisioned temp DB, migration, health/docs/
  Streamlit 200).
- Windows findings: sandbox-vs-machine ACL distinction recorded; uv venv launcher depends on the
  interpreter store; Playwright store probed via Playwright's own resolution; LF pins for
  machine-readable files; CRLF policy-hash debt re-confirmed (Research Evaluation owner).

## Boundaries honored

- No product semantics changed; all pre-existing suites pass through the canonical environment.
- No push / no PR / no master merge; scoped commits only.
- Research policy artifact hashing stays owned by Research Evaluation (recorded follow-up).
- Corpus data is verification-only (never provisioned by the environment layer).
- **DEPARTMENT GREEN** is claimed; this Goal does NOT claim `INTEGRATION GREEN`.
