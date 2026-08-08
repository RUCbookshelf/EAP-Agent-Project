# 04 — Worktree Runtime Architecture Decision

**Department:** Shared Platform & Core
**Goal:** Developer Environment Reproducibility Foundation
**Date:** 2026-08-08
**Status:** WU4 GREEN — approved by fresh independent review (APPROVE_WITH_FINDINGS; blockers
1–4 and findings 5–9 resolved in this revision; see §6). No bootstrap tooling was implemented
before this decision was approved.

## 1. Decision

**Candidate C — worktree-local virtual environments + shared uv package/runtime cache.**

```text
uv (user-space tool, provisioned by bootstrap)
   ├── managed Python runtimes   -> user-level store (UV_PYTHON_INSTALL_DIR)
   ├── package cache             -> user-level uv cache (self-locked by uv)
   └── per-worktree .venv        -> <worktree>\.venv (gitignored, from uv.lock)
```

Every worktree owns a complete, disposable `.venv` built exclusively from the committed
`uv.lock`. Nothing in the repository ever references another worktree's environment.

## 2. Candidate assessment

| Criterion | A. central immutable env | B. shared runtime + light venvs | **C. local venv + shared uv cache** | D. other |
| --- | --- | --- | --- | --- |
| Parallel write safety | FAIL (contention) | MEDIUM (runtime store shared) | **PASS (per-worktree writes; uv self-locks cache)** | n/a |
| Disk usage | BEST (one env) | GOOD | **GOOD (533 MB per worktree; cache shared, rebuild fast)** | n/a |
| Bootstrap time | n/a | MEDIUM | **WARM <1 min; COLD 2–5 min (downloads)** | n/a |
| Failure isolation | FAIL (one broken env breaks all) | MEDIUM | **PASS (per-worktree; repair = rebuild)** | n/a |
| uv compatibility | PARTIAL (uv sync assumes project env) | PARTIAL | **FULL (native uv workflow)** | n/a |
| Windows behavior | POOR (long paths, ACLs) | MEDIUM | **GOOD (verified: uv uses file copies, no junctions/symlinks needed)** | n/a |
| Path stability | POOR (central path churn) | MEDIUM | **GOOD (`.venv` at worktree root; user store machine-level but stable)** | n/a |
| Agent ergonomics | POOR | MEDIUM | **GOOD (one documented bootstrap; no sibling search)** | n/a |
| CI parity | POOR | MEDIUM | **GOOD (CI runs the same `uv sync` commands)** | n/a |
| Repair procedure | HARD | MEDIUM | **EASY (`Remove-Item .venv` + `uv sync`; non-admin)** | n/a |

Rejected alternatives: **A** creates cross-agent contamination and a single point of failure
(the Wave-1 `.pth` borrow was effectively a broken variant of A). **B** is C without uv's
lockfile guarantees. **D** (e.g., per-worktree full toolchains, conda) adds weight or licensing
complexity without evidence of benefit.

## 3. Explicit architecture answers

| Question | Answer |
| --- | --- |
| Does each worktree own a `.venv`? | **YES** — `<worktree>\.venv`, gitignored, built by `uv sync` from the committed lock. |
| Is a central venv allowed? | **NO** — no shared site-packages, no `.pth` links to sibling worktrees (drift guard bans them). |
| Are shared environments writable? | The uv runtime store and package cache are written **only by uv itself** (locked); agents never write into them directly. |
| What is shared? | (1) uv-managed Python installations (user-level `UV_PYTHON_INSTALL_DIR`; on this machine `C:\Users\16073\.uv-python`, bypassing the ACL-broken default store); (2) uv package cache (user-level, self-locked); (3) Playwright browser binaries in a user-level writable directory (`PLAYWRIGHT_BROWSERS_PATH` policy — see 06_EXTERNAL_RESOURCE_CONTRACT.md). |
| What is worktree-local? | `.venv` (including the pinned spaCy model from the lock), pytest caches, run artifacts, worktree databases. |
| Who may mutate dependency state? | Shared Platform & Core owns `pyproject.toml`/`uv.lock`. Agents may run `uv sync` (lock-respecting); `pip install` into a worktree `.venv` is not a supported workflow and is surfaced by `uv sync --check`. |
| Symlinks/junctions on Windows | Not required and not used: uv fell back to ordinary file copies on this machine (no Developer Mode); verified `LinkType` is empty for `Scripts\python.exe`. No Administrator rights are required for bootstrap. |

### 3.1 Interpreter provenance and invocation rules

- The canonical interpreter is **uv-managed CPython 3.12.13** (per `.python-version`), resolved
  through the uv runtime store. The bundled Codex runtime is never the canonical interpreter
  (it is used only as a bootstrap seed to install uv on machines with no other Python).
- `uv` is invoked **by absolute path** discovered by the bootstrap (PATH is never assumed:
  `python`/`py`/`uv` are absent from PATH on this machine).

## 3bis. Environment configuration contract (resolves review blocker 1)

- The bootstrap is the single place that computes environment variables before any `uv`
  invocation: `UV_PYTHON_INSTALL_DIR` (default `%APPDATA%\uv\python`; falls back to a healthy
  user-level store when the default is unusable in the current context) and `UV_CACHE_DIR`
  (default `%LOCALAPPDATA%\uv\cache`; same fallback logic). It also computes
  `PLAYWRIGHT_BROWSERS_PATH` (06 doc).
- Direct `uv` invocation by a human without the bootstrap is documented as unsupported: the
  supported entry point is `scripts/dev/bootstrap_environment.ps1`.
- The verifier (WU6) reports the effective store/cache/browser paths and their health, so
  "store/cache unusable" is a first-class, reported state, never a silent surprise.
- Machine-level truth recorded 2026-08-08: the default uv store, uv cache, and Playwright store
  are all healthy with real-user rights; the fallbacks exist for restricted contexts and for
  machines with genuine ACL breakage (the class Wave-1 described).

## 3ter. Tiered repair classification (resolves review blocker 2)

| Layer | Failure state | Repair command | Owner |
| --- | --- | --- | --- |
| uv binary | `UV_NOT_AVAILABLE` | run `scripts/dev/bootstrap_environment.ps1` (provisions uv user-space from official sources) | Shared Platform & Core |
| uv runtime store | `PYTHON_RUNTIME_MISSING` / store unusable | bootstrap selects a healthy `UV_PYTHON_INSTALL_DIR` and runs `uv python install 3.12.13`; a genuinely ACL-broken store is bypassed, never repaired in-place | Shared Platform & Core |
| uv package cache | `CACHE_UNUSABLE` | bootstrap falls back to a healthy `UV_CACHE_DIR`; `uv cache clean` under single-owner policy | Shared Platform & Core |
| venv | `VENV_INTERPRETER_BROKEN` / `DEPENDENCY_SYNC_FAILED` | `Remove-Item` the worktree `.venv` using the long-path-safe procedure (`\\?\` prefix) and re-run `uv sync` | Shared Platform & Core |
| browsers | `RESOURCE_MISSING` | `python -m playwright install chromium` with the contract's `PLAYWRIGHT_BROWSERS_PATH` | Shared Platform & Core |
| corpus data | `RESOURCE_MISSING` (corpus-owned) | Corpus & NLP owner decides; environment never provisions | Corpus & NLP |

Long-path note: on Windows the standard delete can fail at 260 characters inside deep
site-packages trees; the repair procedure uses `\\?\`-prefixed deletion or
`LongPathsEnabled`, and WU8 exercises it.

## 3quater. Shared-state and concurrency claims (scoped; full evidence in WU9)

- Per-worktree writes (`.venv`, caches, artifacts) are disjoint → concurrent `uv sync`,
  verification, and test execution across DIFFERENT worktrees are safe; uv serializes its own
  cache/store writes with locks (a `.lock` file was verified inside the uv store).
- Two agents syncing the SAME worktree concurrently: uv operations serialize on the project
  lock; the recommended agent rule is one agent per worktree (documented in 07).
- Playwright browser install into the shared `PLAYWRIGHT_BROWSERS_PATH` is NOT uv-managed:
  installs are serialized by policy (one-time install; verify only afterwards). Full executable
  evidence lands in WU9.
- The uv cache lifecycle (including `uv cache clean`) follows the same single-owner mutation
  rule as the dependency manifest: Shared Platform & Core.

## 4. Observed behavior (executable evidence, 2026-08-08)

- `uv sync` from the committed lock created the full environment in this worktree:
  `.venv\Scripts\python.exe` → Python 3.12.13; `pyvenv.cfg` home =
  `C:\Users\16073\.uv-python\cpython-3.12.13-windows-x86_64-none`; `uv = 0.12.3` recorded;
  all 85 packages + en_core_web_sm 3.8.0 installed; venv footprint 533 MB.
- `uv sync --check` → "Would make no changes" (idempotent).
- Two broken-venv states from the Wave-1 era were classified (see 01_CURRENT_ENVIRONMENT_MAP.md):
  both fail with "Unable to create process" because their `pyvenv.cfg` references the
  3.11.15 store, which is sandbox-inaccessible but machine-healthy. Under this architecture the
  repair is deterministic: long-path-safe removal of the worktree `.venv` (gitignored, safe) +
  `uv sync`.
- Junction note: the uv runtime store itself contains a junction (`cpython-3.12-windows-x86_64-none`
  → `cpython-3.12.13-windows-x86_64-none`). Reparse points are uv-owned; backup/restore and ACL
  tooling must preserve them. The worktree `.venv` uses no junctions.

## 6. Review resolution

Independent review (fresh DeepSeek, 2026-08-08) approved Candidate C with findings; all resolved:
1. BLOCKING clean-session store/cache config → §3bis config contract + verifier reporting.
2. BLOCKING repair coverage → §3ter tiered repair classification.
3. HIGH manifests untracked → commit sequencing: manifests + contract docs committed as the
   first scoped commit immediately after this gate, before any bootstrap tooling.
4. HIGH parallel-safety overclaim → §3quater scoped claims; executable evidence in WU9 (07 doc).
5. MEDIUM store junction → recorded in §4.
6. MEDIUM long-path delete → §3ter long-path-safe procedure, exercised in WU8.
7. MEDIUM answers-table gaps → §3.1 interpreter provenance/invocation rules.
8. LOW cache lifecycle ownership → §3quater single-owner rule; cross-volume copy cost noted
   (worktrees on A:, cache on C: → each new worktree is a fresh 533 MB venv copy; accepted).
9. LOW broader ACL probes → WU6 verifier probes default store/cache/browser paths generically.

## 5. Gate statement

**WU4 GREEN — exactly one canonical architecture is selected (Candidate C) with explicit answers
to all required questions, Windows link behavior tested, tiered repair and configuration
contracts defined, parallel-safety claims scoped to WU9 evidence, and no bootstrap tooling
implemented before this approval.**
