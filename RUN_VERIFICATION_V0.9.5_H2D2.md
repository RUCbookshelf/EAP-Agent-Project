# v0.9.5-H2D2 Verification - Bind API Ports to Production Dependency Accessors

**Status:** **v0.9.5-H2D2 is COMPLETE and fully verified.** (Implementation
and focused verification PASS; exact `run.bat --verify` PASS; H2D2-V1 full
non-live core closure: exit code 0, 709 passed, 8 skipped, 2 warnings, zero
failures and zero errors.)

## Scope

Behavior-preserving API contract-typing stage: the exact ten v0.9.5-G
API-owned persistence Ports were added as production return annotations on the
ten matching dependency accessors in `app/api/deps.py`. No Router, app-state,
composition, Port definition, function body, OpenAPI, or dependency-graph
change; no runtime validation; no static-type-tooling introduction; H2E not
begun.

## Baseline and commits

| Item | Value |
| --- | --- |
| Baseline HEAD | `e4d8be8` (v0.9.5-H2D1 cleanup closure), branch `master` |
| Implementation commit | `refactor(v0.9.5-h2d2): bind api ports to dependency accessors` |
| Verification commit | `test(v0.9.5-h2d2): verify api dependency port bindings` |

## The ten API Ports and their accessor bindings

All ten Ports are defined in `app/api/ports.py` (`@runtime_checkable`
Protocols, unchanged) and were previously unbound in production (0 production
references). Each now has the exact Port return annotation on its one
accessor in `app/api/deps.py`; every accessor body, parameter, and returned
app-state attribute is unchanged; both construction paths assign the same
facade-owned repository to the same attribute.

| Port | Accessor | app.state attribute | Concrete satisfier | Structural result |
| --- | --- | --- | --- | --- |
| SubmissionBundleReadPort | get_submission_bundle_reader | submission_bundle_reader | SQLiteSubmissionRepository | PASS |
| StudentLookupPort | get_student_lookup | student_lookup | SQLiteLearnerRepository | PASS |
| AnalysisRunReadPort | get_analysis_runs_reader | analysis_runs_reader | SQLiteAnalysisRepository | PASS |
| CalfReadPort | get_calf_reader | calf_reader | SQLiteCalfRepository | PASS |
| ResearchExportWritePort | get_research_export_writer | research_export_writer | SQLiteResearchRepository | PASS |
| StudentSubmissionListPort | get_student_submission_list | student_submission_list | SQLiteSubmissionRepository | PASS |
| RevisionGroupLookupPort | get_revision_group_lookup | revision_group_lookup | SQLiteRevisionRepository | PASS |
| StudentLearnerReadPort | get_student_learner_reader | student_learner_reader | SQLiteLearnerRepository | PASS |
| SubmissionCalibrationReadPort | get_submission_calibration_reader | submission_calibration_reader | SQLiteCalfRepository | PASS |
| SystemMigrationPort | get_system_migration_reader | system_migration_reader | SQLiteSystemRepository | PASS |

Production-reference transition: **0 -> 10** (each Port now appears exactly in
the deps.py import and its accessor return annotation; import-aware scan).
Before/after evidence: `verification/v0.9.5-h2d2/api_port_bindings_before.json`
and `api_port_bindings_after.json`.

## Verification

### Layer 1 - Static

`py_compile` PASS; imports of `app.api.ports`, `app.api.deps`, every Router,
and both application-construction paths PASS with no circular import; all ten
annotations resolve through `typing.get_type_hints` to the exact Port classes;
task-scoped `git diff --check` PASS; encoding scan clean.

### Layers 2-6 - Focused binding, parity, structural, identity, FastAPI

- New H2D2 file `tests/test_v095h2d2_api_dependency_bindings.py` (13 tests):
  exactly ten Ports/accessors; one-to-one mapping; exact annotations (no
  Any/object/Union/concrete/Database); runtime resolution; production
  references 0 -> 10; Port definitions and runtime-checkable statuses
  unchanged (36 total); accessor names/params/bodies (AST fingerprints)
  unchanged; structural satisfaction of all ten concrete repositories by
  deterministic signature comparison; object identity
  (`accessor(request) is request.app.state.<attr>`) through both
  `_build_full_app` and `_run_startup` paths; OpenAPI and dependency-graph
  parity vs the before artifacts.
- OpenAPI comparison: **identical** (semantic differences 0). Path+method
  pairs: **77** (GET/POST) plus 4 FastAPI auto-HEAD (81 route entries),
  operation IDs, route names, response models, and status codes unchanged.
- Dependency-graph comparison: **identical** (108 `Depends(...)` call sites;
  dependency function identities and cache flags unchanged).

### Layer 7 - Accumulated contract suite

- F2-H2D1 + H2D2 files under the isolated-database runner (fresh
  `v095h2a-p4ulpu4b\h2a.db`, `PYTHON_DOTENV_DISABLED=1`, `DATABASE_URL`
  removed, `LLM_PROVIDER=local`): **243 passed, 2 warnings** (230 baseline +
  13 new H2D2 tests). Export workspace guard captured 3 new test export
  directories (6 files) and restored the baseline exactly afterward.

### Full non-live core regression (H2D2 run) - NOT CLEAN (documented flake, historical)

- Command (exactly once, fresh isolated database
  `C:\Users\16073\AppData\Local\Temp\v095h2a-kk3ml16i\h2a.db`):
  `.venv\Scripts\python.exe verification/v0.9.5-h2a/isolated_pytest_runner.py --full`.
- Result: **exit code 1; 1 failed, 708 passed, 8 skipped, 2 warnings in
  317.30s**; failure
  `tests/test_v095b_router_contract.py::test_live_and_ready_unchanged`
  (lifecycle_state `ready` instead of `starting`).
- Classification: the exact documented pre-existing lifecycle-race flake
  (prod-mode TestClient + background startup thread mutating the global
  lifecycle singleton inside large sets; identical failure signature recorded
  since the G/H2A/H2B/H2C/H2D1 closures). The exact failing test **passes in
  isolation** (1 passed, 2.03s). No automatic rerun was performed.
- Per the stage spec, the full-core result is **not called clean** and final
  H2D2 verification **remains pending** (implementation and focused
  verification complete).
- Export workspace guard captured 8 new test export directories (16 files)
  from the run and restored the baseline exactly afterward.

### H2D2-V1 full non-live core closure - CLEAN

- Command (exactly once, fresh isolated database
  `C:\Users\16073\AppData\Local\Temp\v095h2a-g__xwr8r\h2a.db`):
  `.venv\Scripts\python.exe verification/v0.9.5-h2a/isolated_pytest_runner.py --full`
  (effective command `pytest -q -p no:cacheprovider --ignore=tests/live tests`;
  `PYTHON_DOTENV_DISABLED=1`, `DATABASE_URL` removed, `LLM_PROVIDER=local`;
  resolved database path asserted inside the fresh temporary directory).
- Result: **exit code 0; 709 passed, 8 skipped, 2 warnings; 0 failed;
  0 errors** in 310.80 s. Start 2026-08-03T16:00:34 +08:00, end
  2026-08-03T16:05:48 +08:00, duration 313.9 s.
- Research-export workspace: the run generated 8 new top-level export
  directories / 16 files; the exact guard allowlist (`--delta` +
  `--restore`) removed them leaf-first; final state **776 files / 388 dirs,
  all retained paths and hashes unchanged** (`research_exports_after.json`,
  guard `--check` PASS).
- Development database unchanged (SHA-256/size/mtime, see below); temporary
  directory and `.pytest_cache` removed; ports 8000/8501 free; no
  production or test file changed. H2D2 tracked verification artifacts
  reused by the guard were restored byte-identical from `4cbf908`.
- This closure makes the full-core gate PASS; per the authorized
  H2D2-V1/H2E goal, H2D2 is now fully verified and H2E may begin.

### Launcher verification (separate fresh isolated database)

- Exact command: `cmd /c "run.bat --verify"` -> **PASS (exit 0)** on fresh
  `C:\Users\16073\AppData\Local\Temp\v095h2d2-verify-6631bbdd\verify.db`.
- Migration 12; tables 33; active configuration `config-v0.9.0`; feedback
  prompt `feedback-prompt-v0.7.1`; FastAPI health 200; API docs 200;
  Streamlit 200; `llm_provider=local`. Export baseline verified unchanged
  afterward (guard `--check` PASS).

## Frozen contracts (unchanged)

Total persistence-related contracts 41 -> 41; active 41 -> 41; unused 0 -> 0;
typing.Protocol 41 -> 41; plain structural 0 -> 0; runtime-checkable
36 -> 36; Database public methods 2; API path+method pairs 77; frontend
client methods 52; locale parity 520/520; migration 12; tables 33;
`config-v0.9.0`; `feedback-prompt-v0.7.1`.

## Research-export workspace

- Baseline: `verification/v0.9.5-h2d2/research_exports_baseline.json` (776
  files / 388 dirs, all paths and hashes).
- Focused suite generated 3 dirs / 6 files; full-core generated 8 dirs / 16
  files; each delta was captured in `test_export_deltas.json` (classification
  A, content-signature + absent-from-baseline evidence) and deleted through
  the exact allowlist in `export_workspace_guard.py`.
- Final state: **776 files / 388 dirs, baseline paths and hashes unchanged**
  (`research_exports_final.json`, guard `--check` PASS).

## Database isolation

- Focused run DB: `C:\Users\16073\AppData\Local\Temp\v095h2a-p4ulpu4b\h2a.db`.
- Full-core run DB: `C:\Users\16073\AppData\Local\Temp\v095h2a-kk3ml16i\h2a.db`.
- Launcher DB: `C:\Users\16073\AppData\Local\Temp\v095h2d2-verify-6631bbdd\verify.db`.
- H2D2-V1 closure DB: `C:\Users\16073\AppData\Local\Temp\v095h2a-g__xwr8r\h2a.db` (fresh; removed after the run).
- Development database before/after every write-capable run: SHA-256
  `340E0F3739FEFFD3DEF87BB6E711CB6F90A8478E7E18D833C715EDCFAB03AFF4`, size
  8,298,496 bytes, mtime `2026-08-02T11:02:25.887+08:00` - unchanged; never
  opened. Ports 8000/8501 free; temp databases and processes removed.

## Conclusion

`v0.9.5-H2D2 is COMPLETE and fully verified.` (Implementation, all focused
layers, OpenAPI/dependency-graph parity, and launcher verification pass; the
earlier full-core run exited 1 on the documented pre-existing
lifecycle-race flake, which passes in isolation and is unrelated to H2D2.
The separate H2D2-V1 closure run completed clean - exit code 0, 709 passed,
8 skipped, 2 warnings, zero failures/errors; research-export baseline
restored exactly; development database unchanged. H2E follows in the same
authorized goal.)
