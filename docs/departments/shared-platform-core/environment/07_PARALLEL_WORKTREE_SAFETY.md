# 07 — Parallel Worktree Safety

**Department:** Shared Platform & Core
**Goal:** Developer Environment Reproducibility Foundation
**Date:** 2026-08-08

## 1. Concurrency model

```text
worktree A (.venv A) ─┐
                      ├─> shared, read-mostly: uv runtime store, uv package cache,
worktree B (.venv B) ─┘     optional shared Playwright browser store
```

The only shared mutable state is owned by uv (runtime store + package cache) and the optional
shared browser store. Everything else is per-worktree.

## 2. Operation safety table

| Operation | Same worktree | Different worktrees | Mechanism |
| --- | --- | --- | --- |
| environment verification (read-only) | safe | **safe concurrently** | no writes; only reads + venv probes (verified) |
| `uv sync` / bootstrap | serialized by uv project lock | **safe concurrently** | uv self-locks its cache/store (verified: `.lock` file in store; two concurrent bootstraps both PASSED) |
| test execution | safe (isolated DBs per runner) | **safe concurrently** | per-run temp databases; dev-DB digest guards |
| `uv python install` | serialized by uv | serialized by uv | uv locks the runtime store |
| `playwright install` into shared browser store | one-time; serialized by policy | must not run concurrently (not uv-managed) | policy: single owner installs once; verifiers only read afterwards |
| `uv cache clean` | single-owner only | degrades all worktrees | policy: Shared Platform & Core owns cache lifecycle |

## 3. Executable evidence (2026-08-08)

1. **Concurrent bootstraps**: `bootstrap_environment.ps1` launched simultaneously in
   `shared-core-environment` and the disposable `wu8-environment-test` worktree — both
   completed with `ENVIRONMENT READY` (exit 0) against the same uv cache/store. No lock
   contention, no corruption, no drift.
2. **Concurrent verifiers**: `verify_environment.ps1` launched simultaneously in both worktrees
   — both completed without interference (results: worktree A NOT READY only for sandbox-hidden
   browsers; worktree B NOT READY only for sandbox-restricted interpreter store — both
   restricted-context artifacts, not interference).
3. **uv store lock**: the uv-managed store contains a `.lock` file; uv serializes store/cache
   mutation internally.

## 4. Rules for agents

- One agent per worktree is the recommended rule (no shared-write scenario is required).
- Agents run `uv sync` only through the bootstrap (lock-respecting); direct `pip install` into a
  worktree `.venv` is unsupported and surfaced by `uv sync --check` on the next bootstrap.
- No home-grown lock manager is introduced: uv's own locking suffices for uv-managed state.
- Playwright browser installs are a one-time, single-owner action (Shared Platform & Core);
  all other consumers only verify.
- `uv cache clean` / dependency updates are single-owner (Shared Platform & Core), matching the
  dependency-mutation rule in 03_DEPENDENCY_AND_UV_CONTRACT.md.

## 5. Restricted-context nuance (recorded)

uv-created Windows venvs launch the base interpreter from the uv runtime store
(`pyvenv.cfg` home). When an agent context cannot access that store (sandbox restriction), the
venv reports the historical "Unable to create process" signature; the verifier classifies it as
venv-not-executable and the repair is to run the bootstrap/verifier with normal user rights.
This is a context artifact, not environment corruption — machine-level probes with user rights
remain READY.

## 6. Gate statement

**WU9 GREEN — parallel behavior is defined per operation, executable evidence collected
(concurrent bootstrap + concurrent verification), and shared mutable state is either uv-locked
or single-owner by policy.**
