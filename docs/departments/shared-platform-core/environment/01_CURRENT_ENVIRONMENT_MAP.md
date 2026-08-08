# 01 — Current Environment Map

**Department:** Shared Platform & Core
**Goal:** Developer Environment Reproducibility Foundation
**Date:** 2026-08-08
**Baseline:** `4d9e56d659541f27a3c0305d4fa19a587ef6cbc6` (Wave-1 Integrated Baseline)
**Method:** read-only inspection of the repository and all department worktrees; direct
executable probes of interpreters, virtual environments, and machine-level runtime
resources. No sibling worktree was modified.

## 1. Repository environment contract (as committed)

| Item | State |
| --- | --- |
| `pyproject.toml` | ABSENT |
| `uv.lock` | ABSENT |
| `requirements.txt` | PRESENT — header "v0.2 runtime and test dependencies (Python 3.11)"; pins streamlit 1.60.0, fastapi 0.135.2, uvicorn 0.41.0, httpx 0.28.1, pydantic 2.13.4, python-dotenv 1.2.2, pytest 9.1.1, spacy 3.8.7, playwright 1.61.0 |
| `requirements-nlp.txt` | PRESENT — `en-core-web-sm @ https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl` |
| `.python-version` / `.tool-versions` | ABSENT |
| `environment*.yml` | ABSENT |
| `.github/` (CI) | ABSENT — no CI exists |
| `pytest.ini` / `tox.ini` / `setup.cfg` | ABSENT — no pytest configuration file |
| `run.bat` | Hard-requires Python 3.11 via the Windows `py` launcher (`py -V:Astral/CPython3.11.15` else `py -3.11`); creates worktree-local `.venv`; pip-installs `requirements.txt` then `requirements-nlp.txt`; then migrate/initialize/start, or `--verify` (delegates to `scripts.verify_launcher`), or `--install-only` |
| `README.md` / `INSTALL.md` | Document the Python 3.11 + `py` launcher requirement (Chinese) |
| `.gitignore` | `.venv/`, `.venv*/`, `.env`, `__pycache__`, `*.db`, `research_exports/`, `.streamlit/`, `models/`, etc. |
| `.gitattributes` | ABSENT; `core.autocrlf=true` (Wave-1 CRLF-sensitive policy-hash issue; owner Research Evaluation — see §5.7) |
| Settings | `app/config/settings.py`: `PROJECT_ROOT` derived from file location; `DATABASE_URL` (`sqlite:///` prefix) else `DATABASE_PATH` (default `data/writing_feedback.db`); `PYTHON_DOTENV_DISABLED` respected |

## 2. How scripts and tests invoke the runtime today

- Product scripts (`scripts/run_local.py`, `scripts/service_processes.py`, `scripts/smoke_stack.py`,
  `scripts/verify_launcher.py`) use the interpreter that launched them (`os.sys.executable` or a
  `--python` argument). They do not depend on PATH python.
- `scripts/verify_launcher.py` enforces mandatory database isolation: an explicit `DATABASE_URL`
  must not resolve inside the repository `data/`; absent `DATABASE_URL` auto-provisions a fresh
  temporary database outside the repository (v0.9.6-DP0-V2 hardening).
- `scripts/verify_nlp_resources.py` checks spaCy + `en_core_web_sm` and reports
  `PASS` / `FALLBACK_AVAILABLE` (BasicAnalyzer fallback); `--require-model` exits 1 when missing.
- Hard-coded local-environment assumptions found:
  - `scripts/demo_journey.py` docstring: `.venv\Scripts\python.exe scripts/demo_journey.py …`
  - `scripts/smoke_streamlit.py`: default `PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"`
- Canonical full-suite runner exists and is well-isolated:
  `verification/v0.9.5-h2a/isolated_pytest_runner.py` — fresh temp DB, `DATABASE_PATH` inside temp
  dir assertion, dev-DB SHA-256/size/mtime guard before and after, ports 8000/8501 free check,
  `SERVICE_API_DIFF_ALLOWLIST`, `LLM_PROVIDER=local`, `PYTHON_DOTENV_DISABLED=1`;
  `--full` = `pytest -q -p no:cacheprovider --ignore=tests/live tests`.
- Tests: 92 top-level `test_*.py` files plus `tests/{academic,contracts,corpus,fixtures,live,shared}`;
  `tests/live` (3 Playwright files) is excluded from the canonical non-live core by convention.

## 3. Machine runtime state (probed 2026-08-08)

| Resource | State |
| --- | --- |
| `python` / `python3` / `py` on PATH | ABSENT (all three) |
| `uv` on PATH | ABSENT |
| Working interpreter | Only the bundled Codex runtime: `C:\Users\16073\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe` → **Python 3.12.13** |
| uv-managed Python 3.11.15 | `C:\Users\16073\AppData\Roaming\uv\python\cpython-3.11.15-windows-x86_64-none` — **machine-healthy** (escalated probe 2026-08-08: user full control, complete contents, `python.exe --version` → `Python 3.11.15`); inaccessible from the sandboxed agent context, which is what Wave-1 recorded as "ACL-broken" |
| uv trampoline | `C:\Users\16073\.local\bin\python3.11.exe` is a uv trampoline; running it fails: `uv trampoline failed to spawn Python child process` → `permission denied (os error 5)` |
| Network | Available (pypi.org:443 reachable; direct TLS works) |

## 4. Per-worktree virtual environment state (read-only probes)

| Worktree | Branch | `.venv` | Interpreter resolution | Classification |
| --- | --- | --- | --- | --- |
| `writing-feedback-mvp` (main) | master | present | home = `%APPDATA%\uv\python\cpython-3.11.15-…`; fails to spawn in the sandboxed context, runs `Python 3.11.15` under machine-level rights | SANDBOX-BROKEN / MACHINE-FUNCTIONAL |
| `shared-core-h1` | dept/shared-core-h1 | present | home = bundled runtime; runs **Python 3.12.13**; contains spacy 3.8.7, en_core_web_sm 3.8.0, playwright 1.61.0, pytest 9.1.1, fastapi 0.135.2, streamlit 1.60.0, uvicorn 0.41.0, httpx 0.28.1, pydantic 2.13.4 | FUNCTIONAL (full working environment) |
| `architecture-integration` | integration/wave1 | present | home = bundled runtime; runs 3.12.13; contains `_wave1_integration_shared_site.pth` → `shared-core-h1\.venv\Lib\site-packages` | FUNCTIONAL BUT BORROWED (Wave-1 `.pth` link to sibling `.venv`) |
| `academic-foundation` | dept/academic-foundation | present | home = `%APPDATA%\uv\python\cpython-3.11.15-…`; fails to spawn in the sandboxed context, runs `Python 3.11.15` under machine-level rights | SANDBOX-BROKEN / MACHINE-FUNCTIONAL |
| `research-governance` | dept/research-governance-foundation | absent | — | NONE |
| `corpus-l2` | dept/corpus-l2 | absent | — | NONE |
| `shared-core-environment` (this worktree) | dept/shared-core-environment | absent | — | NONE (clean start) |

## 5. Failure reconstruction and classification

### 5.1 The Python 3.11 chain: sandbox-context failure, machine-healthy runtime

Observed in the agent sandbox: uv-managed CPython 3.11.15 under `%APPDATA%\uv\python` was
unreadable, the uv trampoline in `%USERPROFILE%\.local\bin` failed to spawn
("permission denied (os error 5)"), every `.venv` whose `pyvenv.cfg` points there failed with
"Unable to create process", and `uv.exe` was genuinely absent from PATH and user dirs.

Escalated machine-level probes (2026-08-08) correct the classification:

- **Interpreter availability:** 3.11.15 is **machine-healthy** (ACLs grant the user full
  control; `python.exe --version` → `Python 3.11.15`). The failure is a **sandbox-context
  restriction** on user-profile stores, not a machine ACL failure.
- **Venvs:** `writing-feedback-mvp\.venv` and `academic-foundation\.venv` run
  `Python 3.11.15` under machine-level rights → **context-restricted venv spawn**, not a broken
  environment.
- **PATH:** no `python`/`py`/`python3` on PATH → **PATH failure** (no system Python installed) —
  genuinely true at machine level.
- **uv:** not installed/not on PATH at Goal start → **uv installation/availability failure** —
  genuinely true; uv 0.12.3 was provisioned by this Goal.
- **Browser store:** `%LOCALAPPDATA%\ms-playwright` is machine-healthy (chromium-1228 installed);
  sandbox-denied. Same context-restriction class.
- **Implication:** the environment contract must work in BOTH contexts: provisioning from a
  normal shell (defaults work), verification usable from a restricted context (worktree-local
  `.venv`), and the bootstrap probes/fallbacks protect machines that DO have real ACL breakage.

### 5.2 Borrowed sibling environment (the documented Wave-1 anti-pattern)

`architecture-integration\.venv\Lib\site-packages\_wave1_integration_shared_site.pth` contains
`A:\EAP Agent Project\worktrees\shared-core-h1\.venv\Lib\site-packages`. The Wave-1 verification
record (`docs/integration/wave1/10_INTEGRATION_VERIFICATION.md`) confirms the canonical 1837-test
run used this linked environment. This is exactly the "find a sibling worktree whose .venv happens
to work" workflow this Goal must eliminate. The `.pth` is inside a gitignored `.venv` (untracked),
so it carries no committed reference — but it proves the machine workflow still borrows.

### 5.3 Playwright browsers

`%LOCALAPPDATA%\ms-playwright` is sandbox-denied but machine-healthy (chromium 1228 and
companion binaries installed). Wave-1 used `PLAYWRIGHT_BROWSERS_PATH` pointing to a writable temp
location because of the restricted agent context. The environment contract keeps an explicit
browser-path policy so behavior is deterministic in both contexts (see 06_EXTERNAL_RESOURCE_CONTRACT.md).

### 5.4 Hard-coded `.venv` assumptions

`scripts/demo_journey.py` (docstring) and `scripts/smoke_streamlit.py` (default argument) assume
`.venv\Scripts\python.exe` relative to the repo root. Not broken per se (the contract will keep a
worktree-local `.venv`), but these are drift-prone and belong under a single canonical environment
location definition.

### 5.5 Git shadowing (machine-level, recorded by Wave-1)

Wave-1 recorded that an ACL-broken hermes `git.exe` on the sanitized PATH shadowed the runtime git,
requiring a local wrapper (`run_full_suite.py`) that prepends the bundled git dir to PATH. This is a
machine-level PATH hazard that the environment verifier can detect (bare `git` subprocess checks in
parity tests).

### 5.6 CRLF / policy-artifact hashing

`core.autocrlf=true`, no `.gitattributes`. Wave-1 recorded that policy-artifact SHA-256 validation
requires LF checkouts on this machine; owner follow-up is Research Evaluation
(`docs/integration/wave1/12_NEXT_WAVE_HANDOFF.md`). Research policy artifact hashing semantics are
out of scope for this Goal; the environment contract records the follow-up rather than changing
Research ownership.

### 5.7 Data-safety incident class (v0.9.6-DP0-V2)

Verification that silently falls back to the development database is a known incident class
(V2-DB-A). The launcher isolation guard (`scripts/verify_launcher.py`) already hardens this; the
environment verification entry point must keep the same isolation semantics (no writes, no dev-DB
touch).

## 6. What currently works (verified by probes and Wave-1 records)

- The bundled Codex runtime Python 3.12.13 is a working interpreter.
- `shared-core-h1\.venv` is a complete, working 3.12.13 environment containing every pinned
  dependency and the pinned spaCy model — proof the dependency set installs cleanly on 3.12.
- The isolated pytest runner and the hardened launcher verification exist and encode the correct
  isolation semantics.
- Wave-1 proved the full non-live core passes on 3.12.13: **1837 passed / 8 skipped / 0 failed,
  exit 0**.

## 7. External runtime resources referenced today

| Resource | Reference | Provisioning today | Verification today | Notes |
| --- | --- | --- | --- | --- |
| spaCy `en_core_web_sm` 3.8.0 | `requirements-nlp.txt` (GitHub wheel) | pip into venv | `scripts/verify_nlp_resources.py` | BasicAnalyzer fallback; analyzer default |
| Playwright 1.61.0 + Chromium | `requirements.txt`; browser binary | `playwright install` (default store machine-healthy; explicit `PLAYWRIGHT_BROWSERS_PATH` policy for restricted contexts) | browser/DOM tests in the core suite | `tests/live` excluded from core; core includes browser/DOM suites |
| SQLite | Python stdlib | — | import check | no external binary needed |
| Node/npm | not required by product or tests | — | — | no `.github`/frontend build |
| Corpus source data | `tests/corpus` + `scripts/corpus_readiness` + Stage-5 build | NOT provisioned by environment (owner: Corpus) | presence-only where tests require | licensed data; never auto-provisioned |

## 8. Implications for the environment contract (inputs to WU2–WU4)

1. The repository has **no lockfile**: `pip install -r requirements.txt` resolves today's latest
   compatible versions each time → dependency drift is undetectable today.
2. The committed contract says **Python 3.11 only** (`run.bat`, README, INSTALL), while all current
   evidence (Wave-1, departmental suites) is on **Python 3.12.13**. The runtime policy (WU2) must
   reconcile these on evidence, not convenience.
3. There is **no uv** available on this machine and the previous uv-managed runtime store is
   ACL-broken → the bootstrap must provision uv/user-managed runtimes defensively, or fall back to
   an explicit documented path, and must never reuse the broken store.
4. The environment contract must make the borrowed-`.pth` pattern impossible by giving every
   worktree a self-contained, reproducible environment and a deterministic verifier.
5. Playwright browser storage and the `%LOCALAPPDATA%\ms-playwright` ACL failure require an
   explicit `PLAYWRIGHT_BROWSERS_PATH` policy.
6. All environment entry points must keep the database-isolation semantics of
   `verify_launcher.py` / `isolated_pytest_runner.py`.

## 9. Gate statement

**WU1 GREEN — the observed failure modes are reproduced and classified (ACL-broken uv runtime,
broken venvs, PATH absence, uv absence, borrowed sibling environment, ACL-broken browser store,
machine git shadowing, CRLF hashing), and the working state (bundled 3.12.13 runtime,
shared-core-h1 full env, isolated runners) is mapped.**
