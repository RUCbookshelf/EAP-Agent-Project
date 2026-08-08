# 02 — Python Runtime Contract

**Department:** Shared Platform & Core
**Goal:** Developer Environment Reproducibility Foundation
**Date:** 2026-08-08
**Status:** WU2 GREEN — policy approved by fresh independent review
(APPROVE_WITH_FINDINGS; all findings resolved below)

## 1. Policy (proposed)

| Dimension | Value |
| --- | --- |
| Minimum supported version | Python 3.11 |
| Maximum supported/tested version | Python 3.12 |
| Preferred development version | Python 3.12.x (canonical today: 3.12.13) |
| CI test versions (future CI contract) | 3.12 primary; 3.11 optional/best-effort |
| Unsupported versions | Python <3.11, Python ≥3.13 |
| Machine-readable declarations | `.python-version` = `3.12.13` (exact patch, committed — this Goal); `requires-python = ">=3.11,<3.13"` in `pyproject.toml` (committed in WU3); enforced by the environment verifier (WU6) |

`requires-python = ">=3.11,<3.13"` (not `<3.12`): Python 3.11 remains **supported** per the evidence
below and per historical verification; the canonical preferred runtime is 3.12.x. The exact-patch
pin `3.12.13` in `.python-version` keeps environments deterministic; patch bumps are owned by
Shared Platform & Core and require re-verification (see §4).

**Launcher/docs synchronization (committed):** the committed launcher and installation docs
(`run.bat` hard check `sys.version_info[:2] == (3, 11)`, README/INSTALL "项目只使用 Python 3.11")
currently contradict this policy. Migration of `run.bat` and the install docs to the new
environment contract is owned by Shared Platform & Core and is executed in WU5 (bootstrap
implementation) of this Goal, per AGENTS.md runtime-synchronization rules. Until WU5 lands, the
committed launcher still rejects 3.12; the policy above governs repository environments, not the
legacy launcher.

## 2. Evidence

### 2.1 Source-level compatibility (verified 2026-08-08)

All 444 `.py` files under the repository (excluding gitignored/generated state) were parsed with
`ast.parse(..., feature_version=(3, 11))` and `feature_version=(3, 12)` (BOM stripped; CPython
tolerates the 20 files that carry a UTF-8 BOM):

- 3.11 grammar: **0 incompatible files**
- 3.12 grammar: **0 incompatible files**

There is no Python 3.12-only syntax anywhere in the current source, so the codebase remains
Python 3.11-parseable by construction.

### 2.2 Runtime behavior

- **Python 3.12.13** (bundled Codex runtime): Wave-1 Integrated Baseline full non-live core
  **1837 passed / 8 skipped / 0 failed, exit 0** (`docs/integration/wave1/10_INTEGRATION_VERIFICATION.md`),
  plus all departmental focused suites (Shared Core ~175, Research Governance 28, Academic 322,
  Corpus Stage-5 36, Wave-1 gates 39), launcher PASS, locale parity 600/600.
- **Python 3.11.15**: historical records show passes across the v0.2–v0.6.1 era; 3.11.15 is
  explicitly recorded in the v0.1 section of the root `RUN_VERIFICATION.md` (commands and result
  table use CPython 3.11.15), in `RUN_VERIFICATION_V0.4.md`, and in decision D010 of
  `docs/development/DECISION_LOG.md` (clean 3.11.15 environment, `pip check` clean). There is no
  `RUN_VERIFICATION_V0.1.md` file; the v0.1 record lives in the root file.
- A complete dependency set identical to `requirements.txt` + `requirements-nlp.txt` is installed
  and working in `shared-core-h1\.venv` on Python 3.12.13 (spacy 3.8.7 + en_core_web_sm 3.8.0,
  playwright 1.61.0, pytest 9.1.1, fastapi 0.135.2, streamlit 1.60.0, uvicorn 0.41.0, httpx 0.28.1,
  pydantic 2.13.4).

### 2.3 Dependency metadata

All pinned packages (streamlit 1.60.0, fastapi 0.135.2, uvicorn 0.41.0, httpx 0.28.1,
pydantic 2.13.4, python-dotenv 1.2.2, pytest 9.1.1, spacy 3.8.7, playwright 1.61.0) support the
Python 3.11–3.12 range per their release metadata. None requires 3.12; none forbids 3.11.

### 2.4 What is NOT evidence

- Python 3.13 was never exercised by any repository run; it is excluded (not "rejected by
  evidence", simply untested and therefore unsupported).
- Python 3.11 was NOT re-run on the Wave-1 integrated baseline; the Wave-1 handoff records the
  canonical 3.11 re-run as outstanding environment debt owned by Platform/Infrastructure
  (`docs/integration/wave1/12_NEXT_WAVE_HANDOFF.md`).

## 3. Python 3.11 debt disposition (Goal §20)

**Option B — Python 3.11 is SUPPORTED but not uniquely required.**

The SUPPORTED label means: the codebase remains 3.11-parseable (0/444 incompatible), historical
verification passed on 3.11.15, and the pinned dependency set allows 3.11. It does NOT mean a
current-pin runtime test on 3.11 has been executed on the integrated baseline — the canonical
3.11 re-run remains recorded, owned by Platform/Infrastructure, and pending a working 3.11
interpreter (Wave-1 handoff follow-up). "Optional/best-effort" in the CI row means exactly the
same thing: a 3.11 CI lane is not promised until that re-run exists.

Justification:

1. The committed launcher and docs (`run.bat`, README, INSTALL) historically required 3.11, but
   the Wave-1 integrated baseline and all departmental evidence now run on 3.12.13; nothing in the
   product or tests requires 3.11 specifically.
2. The current source parses under 3.11 grammar (0 incompatibilities), and v0.1–v0.6 passed on
   3.11.15, so 3.11 is not being dropped.
3. 3.11 was not provisionable from the restricted agent context at Goal start, but the
   machine-level uv-managed 3.11.15 runtime is healthy (escalated probe 2026-08-08) and is now
   provisionable via uv. Option A remains rejected because 3.11 is not uniquely required by any
   evidence — the entire integrated baseline runs on 3.12.13.
4. This Goal's canonical verification runs on the preferred 3.12.x runtime; the canonical 3.11
   re-run (Wave-1 handoff follow-up, owner Platform/Infrastructure) is **COMPLETED** in WU13:
   full non-live core on Python 3.11.15 → **1851 passed / 8 skipped / 0 failed, exit 0**
   (identical totals to 3.12.13). The recorded 3.11 debt is closed.

## 4. Testability and drift protection

- `.python-version` (`3.12.13`) is the single preferred-version declaration consumed by uv
  (committed with this contract).
- `requires-python` in `pyproject.toml` is the formal minimum/maximum declaration.
- An environment drift guard (WU12) asserts: `.python-version` exactly matches the preferred
  version declared in this contract (3.12.13); `requires-python` covers 3.11 and 3.12; a
  syntax-level 3.11 gate (`ast.parse(feature_version=(3, 11))` over the repository's Python
  files, BOM-stripped) stays green. Lockfile regeneration (owned by Shared Platform & Core)
  additionally requires that no resolved package's Requires-Python excludes 3.11 or 3.12
  (checked at `uv lock` time by the owning engineer; enforced by the syntax gate afterwards).
- The verifier (`verify_environment.ps1`) checks the resolved interpreter's `sys.version_info`
  against `>=3.11,<3.13` (a venv outside the range reports `PYTHON_RUNTIME_MISSING`) and prints
  the preferred version.

## 5. Gate statement

**WU2 GREEN — version policy is explicit and testable; `.python-version` = 3.12.13 is committed;
`requires-python = ">=3.11,<3.13"` lands with the dependency contract (WU3); Python 3.11 debt
disposition is Option B, approved by fresh independent review (findings 1–6 resolved: committed
vs. planned artifacts distinguished; launcher/docs migration committed to WU5 with owner and
trigger; 3.11 evidence citations corrected; SUPPORTED label qualified against the recorded 3.11
re-run debt; exact-patch pin adopted; syntax-level 3.11 gate added to drift protection).**
