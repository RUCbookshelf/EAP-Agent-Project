# v0.9.5-H2A Verification - Remove Unused Legacy Persistence Contracts

**Status:** PASS

## Scope

Behavior-preserving removal of the 13 persistence contracts proven unused by the v0.9.5-H1 audit (11 stale central Protocols + the `SubmissionRepositories` union alias in `app/repositories/protocols.py`, and the legacy `SubmissionRepository` combined class in `app/services/submission.py`), plus their obsolete imports, bases, and re-exports. No active contract (A/B/C), Repository implementation, Service constructor, Router dependency, composition path, SQL, transaction, API, schema, provider, prompt, UI, or localization file changed. No replacement contract was introduced.

## Baseline

| Item | Value |
| --- | --- |
| Branch / baseline HEAD | `master` / `760193f` (v0.9.5-H1 audit) |
| H1 evidence | `PROTOCOL_CONSOLIDATION_AUDIT_V0.9.5_H1.md` + `verification/v0.9.5-h1/*` (historical, unchanged) |
| Persistence contracts before / after | 55 / 42 (13 removed, 0 replacements) |
| Database public surface | 2 (`connect`, `initialize`) |
| API contract / frontend client / locale | 77 / 52 / 520:520 |
| Migration / tables | 12 / 33 |
| Active configuration / prompt | `config-v0.9.0` / `feedback-prompt-v0.7.1` |
| Full-core baseline (G report) | 653 passed, 8 skipped |
| H1 focused contract baseline | 187 passed |

## Implementation

Removed exactly (per `verification/v0.9.5-h2a/removed_contracts.json`):

1. `StudentRepository` (protocol, `app/repositories/protocols.py:11`)
2. `EssayRepository` (protocol, `:15`)
3. `MetricRepository` (protocol, `:21`)
4. `ErrorAnnotationRepository` (protocol, `:29`)
5. `DiagnosisRepository` (protocol, `:34`)
6. `FeedbackRepository` (protocol, `:38`)
7. `ExerciseRepository` (protocol, `:42`)
8. `LearnerHistoryRepository` (protocol, `:46`)
9. `LearnerProfileRepository` (protocol, `:52`)
10. `ConfigurationRepository` (stale central protocol, `:74`)
11. `SystemVersionRepository` (protocol, `:79`)
12. `SubmissionRepositories` (typing union alias, `:84`)
13. `SubmissionRepository` (legacy combined class, `app/services/submission.py:78`)

Obsolete references removed: the 10-name re-export block and `__all__` entries in `app/repositories/__init__.py` (only `RevisionRepository` remains exported); the 6-protocol import block and the class definition in `app/services/submission.py`; imports used only by removed definitions in `app/repositories/protocols.py` (`app.core.LearnerProfileSnapshot`, `app.models.*`, `app.calf.ErrorAnnotation`).

Zero-consumer proof (pre-change bounded AST/import scan): active runtime consumers = 0 for all 13 candidates; the only references were the obsolete re-exports above, negative test assertions, and historical E-era string keys. The `app/services/configuration.py:25` annotation resolves to the module-local 7-method `ConfigurationRepository` (unchanged; the collision is resolved only by removing the stale central protocol).

## Verification

### Focused contract suite (isolated DB, local provider)

- Command: `.venv\Scripts\python.exe verification/v0.9.5-h2a/isolated_pytest_runner.py` (13 files: F2-F6D + G + new `tests/test_v095h2a_removed_contracts.py`).
- Result: **197 passed, 2 warnings** (187 H1 baseline + 10 new H2A tests).
- New H2A tests prove: 13 names absent; re-exports absent; no source import of a removed name; all 42 H1-active contracts defined with exact method sets; concrete Repositories satisfy active contracts; SubmissionService uses exactly its four F6C Ports; local `ConfigurationRepository` unchanged; Practice read/write separation unchanged; ten API-owned Ports unchanged; `RevisionRepository` is the only central export.

### Static

- `py_compile` of all changed modules: PASS; affected package imports (app.repositories, app.services.submission, app.services.factory, app.services.configuration, app.api.main, app.feedback.service, app.practice.ports, app.api.ports): PASS (no circular import).
- `git diff --check` on task-owned files: PASS (worktree-wide check only flags pre-existing user-owned `AGENTS.md` trailing whitespace).
- UTF-8/replacement-character scan of changed files: PASS.
- Removal proof: `removed_contracts.json` (13) and `remaining_contract_inventory.json` (42 active, all present with exact method sets) parse and reconcile.

### Runtime smoke (isolated DB)

- FeedbackPipeline construction, `create_app(settings)` immediate full construction, `create_app()` production-mode object, `build_submission_service` + `ConfigurationService` construction: **PASS** (`RUNTIME_SMOKE_PASS`).

### Full non-live core regression (fresh isolated database)

- Command: `.venv\Scripts\python.exe verification/v0.9.5-h2a/isolated_pytest_runner.py --full` (`pytest -q --ignore=tests/live tests`).
- Result: **662 passed, 8 skipped, 2 warnings** in 308.98s.
- One failure: `tests/test_v095b_router_contract.py::test_business_route_gated_until_ready_while_health_available` - the **documented pre-existing flake** (prod-mode TestClient + background startup thread flips global lifecycle state inside large sets). It passes in isolation (0.52s, verified) and was already recorded in `RUN_VERIFICATION_V0.9.5_G.md`. Not an H2A regression; not repaired (out of scope).

### Launcher verification (separate fresh isolated database)

- Exact command: `cmd /c "run.bat --verify"` -> **PASS (exit 0)**.
- Migration 12; tables 33; `config-v0.9.0`; `feedback-prompt-v0.7.1`; FastAPI health 200; docs 200; Streamlit 200; `llm_provider=local`; deepseek key not configured.

### Frozen contracts (unchanged)

- Database public methods: 2; API path+method pairs: 77; frontend client methods: 52; locale parity: 520/520; migration: 12; tables: 33; configuration: `config-v0.9.0`; feedback prompt: `feedback-prompt-v0.7.1`.

### Database isolation

- Focused run DB: `C:\Users\16073\AppData\Local\Temp\v095h2a-*/h2a.db` (fresh unique temp dir, resolved and asserted).
- Full run DB: `C:\Users\16073\AppData\Local\Temp\v095h2a-*/h2a.db` (fresh unique temp dir).
- Launcher run DB: `C:\Users\16073\AppData\Local\Temp\v095h2a-verify-*/verify.db` (fresh unique temp dir).
- Development database before/after every write-capable run: SHA-256 `340E0F3739FEFFD3DEF87BB6E711CB6F90A8478E7E18D833C715EDCFAB03AFF4`, size 8,298,496 bytes, mtime `2026-08-02T11:02:25.887+08:00` - unchanged; never opened.
- Ports 8000 and 8501 free before and after; all temporary databases and processes removed.

## Changed files

Production: `app/repositories/protocols.py`, `app/repositories/__init__.py`, `app/services/submission.py`.
Tests: `tests/test_v095h2a_removed_contracts.py` (new).
Docs: `docs/development/V0.9.5_H2A_SPEC.md`, `RUN_VERIFICATION_V0.9.5_H2A.md`, `CHANGELOG.md`, `PROJECT_STATE.md`, `docs/development/MASTER_ROADMAP.md`, `docs/development/CURRENT_TASK_STATE.md`, `docs/development/DECISION_LOG.md`.
Verification artifacts: `verification/v0.9.5-h2a/removed_contracts.json`, `remaining_contract_inventory.json`, `isolated_pytest_runner.py`.

Historical H1 artifacts were not rewritten (55/42/13 counts remain historical evidence).

## Known limitation

The documented `test_v095b_router_contract` lifecycle-race flake appeared once inside the full suite and passes in isolation (recorded in the G verification report; out of scope for H2A).
