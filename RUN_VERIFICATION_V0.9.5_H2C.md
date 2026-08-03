# v0.9.5-H2C Verification - Canonicalize Duplicate `_AnalysisRunReader` Infrastructure Contract

**Status:** **PASS - v0.9.5-H2C is COMPLETE and fully verified** (full non-live
core run: exit code 0, 683 passed, 8 skipped, 2 warnings)

## Scope

Behavior-preserving infrastructure-contract deduplication: the two identical
infrastructure-local `_AnalysisRunReader` Protocol definitions were replaced by
one shared infrastructure-owned `AnalysisRunReader` contract. No Repository
refactor, no Service/API/Practice Port consolidation, no dependency-narrowing,
no SQL, transaction, composition, or runtime change. H2D and H2E not begun.

## Baseline and commits

| Item | Value |
| --- | --- |
| Baseline HEAD | `7974ebc` (v0.9.5-H2B full-core closure), branch `master` |
| Implementation commit | `refactor(v0.9.5-h2c): canonicalize analysis run reader` |
| Verification commit | `test(v0.9.5-h2c): verify shared analysis reader contract` |

## Former definitions (before state, AST-verified)

| Definition | Module | Line | Declared method |
| --- | --- | --- | --- |
| `_AnalysisRunReader` | app/infrastructure/sqlite/repositories/revision.py | 14 | `get_latest_analysis_run(self, essay_id: int) -> dict[str, Any] | None` |
| `_AnalysisRunReader` | app/infrastructure/sqlite/repositories/learner.py | 12 | `get_latest_analysis_run(self, essay_id: int) -> dict[str, Any] | None` |

Both were plain `Protocol` classes (no `@runtime_checkable`, no additional
bases or methods), identical in method name, parameter name/order, defaults,
return annotation, and sync behavior; both expressed the same Analysis-owned
read capability; both were satisfied by the same concrete method
`SQLiteAnalysisRepository.get_latest_analysis_run`
(app/infrastructure/sqlite/repositories/analysis.py:112); both consumers
received the same facade-owned `SQLiteAnalysisRepository` instance from
`Database.__init__` (app/database/repository.py). H1 records
(`protocol_inventory.json` classification C, `h2_candidate_plan.json` H2C unit,
`PROTOCOL_CONSOLIDATION_AUDIT_V0.9.5_H1.md` sections 6.3/7/9) corroborate the
pair as the only exact infrastructure duplicate. Full before-state evidence:
`verification/v0.9.5-h2c/reader_contract_before.json`.

## Canonicalization

- Canonical contract name: `AnalysisRunReader` (leading underscore dropped
  because the contract is intentionally imported by more than one
  infrastructure module).
- Canonical module: `app/infrastructure/sqlite/repositories/contracts.py`
  (new; no suitable existing shared module; stays inside the SQLite repository
  package, imports only `typing`, no concrete/service/API dependency).
- Consumers migrated: `SQLiteRevisionRepository.__init__` and
  `SQLiteLearnerRepository.__init__` import the canonical contract and use it
  only for the existing `analysis_reader` constructor annotation; stored
  attribute `_analysis_reader`, parameter names/order/defaults, concrete
  collaborator identity, method calls, SQL, and transactions unchanged.
- Both former local definitions removed; no compatibility alias exists;
  `_AnalysisRunReader` is absent from all `app/**` source.

## Changes

- `app/infrastructure/sqlite/repositories/contracts.py` (new): canonical
  `AnalysisRunReader` Protocol, exactly one method.
- `app/infrastructure/sqlite/repositories/revision.py`: import +
  annotation only (-5 lines).
- `app/infrastructure/sqlite/repositories/learner.py`: import + annotation
  only (-5 lines).
- `tests/test_v095h2c_analysis_run_reader_contract.py` (new, 14 tests):
  canonical definition identity; both consumers reference the same contract
  object; former local definitions absent; no alias; concrete
  `SQLiteAnalysisRepository` structural satisfaction; contract module has no
  Service/API/FastAPI dependency; no Service/API Port imports the canonical
  contract; no active consumer-owned contract changed; active persistence
  contracts reduced by exactly one (42 -> 41); H2A/H2B invariants; constructor
  parameter parity for both consumers; facade identity (same concrete analysis
  instance into both consumers, one connection manager); no repository
  construction/composition change; missing and populated analysis-run behavior
  through both consumers on an isolated database.
- `tests/test_v095h2a_removed_contracts.py`: minimal H1-inventory mapping for
  the two historical `_AnalysisRunReader` entries -> the canonical
  `AnalysisRunReader` in contracts.py (historical H1 artifacts untouched).
- `verification/v0.9.5-h2c/reader_contract_before.json` /
  `reader_contract_after.json`: before/after AST evidence.
- The existing `verification/v0.9.5-h2a/isolated_pytest_runner.py` was reused
  (no copy). H2C touches no `app/services` or `app/api` file, so the E-parity
  `SERVICE_API_DIFF_ALLOWLIST` required no entry (verified: 0 unallowlisted
  service/API diffs vs `769e6d8`).

## Verification

### Layer 1 - Static

- `py_compile` of all changed modules: PASS; package imports
  (`contracts`, `revision`, `learner`, `app.database`, `app.api.main`,
  `app.repositories`) PASS with no circular import; `git diff --check` on the
  H2C-scoped files PASS; encoding scan of changed files clean.

### Layer 2/3/4 - Focused contract, constructor-parity, and behavior

- New H2C file standalone: **14 passed, 1 warning**.
- Accumulated F2-H2C contract suite (F2, F3, F4, F5A, F5B, F6A0, F6A, F6B,
  F6C, F6D, E modularization, G facade contraction, H2A, H2B, H2C) under the
  isolated-database runner (fresh `v095h2a-0mbb33gl\h2a.db`,
  `PYTHON_DOTENV_DISABLED=1`, `DATABASE_URL` removed, `LLM_PROVIDER=local`):
  **217 passed, 2 warnings** (203 H2B baseline + 14 new H2C tests).
- E-parity allowlist check vs `769e6d8`: 25 changed service/API files, 0
  unallowlisted (H2C production files are infrastructure-only).
- GitNexus `detect_changes`: changed production symbols limited to
  `SQLiteRevisionRepository` and `SQLiteLearnerRepository` (annotation-only);
  GitNexus query/impact degraded by the documented FTS/not-yet-indexed
  limitation and CRG CLI uv-trampoline defect (recorded, not repaired).

### Full non-live core regression

- Command (exactly once, fresh isolated database
  `C:\Users\16073\AppData\Local\Temp\v095h2a-0kgidc_7\h2a.db`):
  `.venv\Scripts\python.exe verification/v0.9.5-h2a/isolated_pytest_runner.py --full`
  (`pytest -q -p no:cacheprovider --ignore=tests/live tests`).
- Result: **exit code 0; 683 passed, 8 skipped, 2 warnings in 316.70s**;
  zero failed, zero errors, complete non-live core collection, no test
  excluded, retried, reordered, or weakened; the documented
  `test_v095b_router_contract` lifecycle-race flake did not occur in this run.

### Launcher verification (separate fresh isolated database)

- Exact command: `cmd /c "run.bat --verify"` -> **PASS (exit 0)** on fresh
  `C:\Users\16073\AppData\Local\Temp\v095h2c-verify-e1fb4776\verify.db`.
- Migration 12; tables 33; active configuration `config-v0.9.0`; feedback
  prompt `feedback-prompt-v0.7.1`; FastAPI health 200; API docs 200;
  Streamlit 200; `llm_provider=local`.

## Frozen contracts (unchanged)

Database public methods 2; API path+method pairs 77; frontend client methods
52; locale parity 520/520; migration 12; tables 33; active configuration
`config-v0.9.0`; active feedback prompt `feedback-prompt-v0.7.1`; total
persistence-related contracts **42 -> 41**; active **42 -> 41**; unused legacy
**0 -> 0**.

## Database isolation

- Focused run DB: `C:\Users\16073\AppData\Local\Temp\v095h2a-0mbb33gl\h2a.db`.
- Full-core run DB: `C:\Users\16073\AppData\Local\Temp\v095h2a-0kgidc_7\h2a.db`.
- Launcher DB: `C:\Users\16073\AppData\Local\Temp\v095h2c-verify-e1fb4776\verify.db`.
- Development database before/after every write-capable run: SHA-256
  `340E0F3739FEFFD3DEF87BB6E711CB6F90A8478E7E18D833C715EDCFAB03AFF4`, size
  8,298,496 bytes, mtime `2026-08-02T11:02:25.887+08:00` - unchanged; never
  opened.
- Ports 8000/8501 free before and after; all temporary databases and processes
  removed; `research_exports/` untouched; no live provider.

## Conclusion

`v0.9.5-H2C is COMPLETE and fully verified.` (Implementation, focused contract
suite, exact `run.bat --verify`, and the full non-live core run - exit code 0,
683 passed, 8 skipped, 2 warnings - all pass.)
