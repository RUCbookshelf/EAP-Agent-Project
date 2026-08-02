# v0.9.5-F6A0 Verification — Revision Repository Capability Completion

**Date:** 2026-08-02
**Status:** PASS
**Baseline commit:** `b766284` (v0.9.5-F5B verification); F2-F5B commits are
ancestors
**Implementation commit:** `refactor(v0.9.5-f6a0): complete revision repository capabilities` (`693ff48`)
**Verification commit:** `test(v0.9.5-f6a0): verify revision repository composition`
**Specification:** `docs/development/V0.9.5_F6A0_SPEC.md`
**Authorization:** Owner decision 2026-08-02 (Option C); v0.9.5-F6A remains
formally blocked and no F6A runtime narrowing was performed.

## Scope (repository capability completion only)

The existing facade-owned `SQLiteRevisionRepository` now structurally
satisfies the unchanged central `RevisionRepository` contract by exposing
two new read-only delegation methods:

```text
get_submission_bundle
get_latest_analysis_run
```

Both methods are direct one-line delegations to injected readers. No SQL was
added, no transaction boundary was introduced, and no Revision write method
was touched.

## Exact reader dependencies added

- private `_AnalysisRunReader` Protocol in
  `app/infrastructure/sqlite/repositories/revision.py` (mirroring the
  existing `_SubmissionBundleReader` convention);
- `analysis_reader` constructor parameter on `SQLiteRevisionRepository`;
- facade wiring: `SQLiteRevisionRepository(self._connection_manager,
  self._submission_repository, self._analysis_repository)`.

## Method-signature parity

`inspect.signature` parity is proven by focused tests for:

- `SQLiteRevisionRepository.get_submission_bundle` ==
  `SQLiteSubmissionRepository.get_submission_bundle` ==
  `RevisionRepository.get_submission_bundle`;
- `SQLiteRevisionRepository.get_latest_analysis_run` ==
  `SQLiteAnalysisRepository.get_latest_analysis_run` ==
  `RevisionRepository.get_latest_analysis_run`.

## Delegation and exception-parity evidence

Focused tests prove each method delegates exactly once to its injected
reader, arguments and returned values pass through unchanged (identity
assertions), `None` missing records pass through, and reader exceptions
propagate unchanged. Source-segment tests prove both methods contain no
`connect`, `execute`, `commit`, or `rollback` calls (no new connection is
opened by either delegation method; each delegated repository keeps its own
existing connection behavior).

## Repository and connection-manager identity evidence

Focused tests prove, from a single fresh `Database`:

- `database._revision_repository._submission_reader is
  database._submission_repository`;
- `database._revision_repository._analysis_reader is
  database._analysis_repository`;
- all three repositories share `database._connection_manager` (one
  manager id across the graph);
- `SQLiteRevisionRepository(` appears exactly once in production
  (`app/database/repository.py`), so one `Database` creates one repository
  graph with no second construction.

## Unchanged components (verified)

- Central `RevisionRepository` Protocol: unchanged (method set and
  signatures pinned by focused test; file untouched).
- `RevisionService`: unchanged (imports, constructor, call set, and
  annotation `repository: RevisionRepository` verified by Layer 1 import
  probe); every active `RevisionService` remains on its current runtime
  dependency (the broad facade) because F6A0 performs no runtime narrowing.
- `SubmissionService`, `AdminReanalysisService`, `FeedbackPipeline`,
  `build_submission_service`, `app/api/main.py` Service composition,
  Revision Router, SQL, migrations, DDL, schemas, domain logic, API
  contracts, frontend, and UI: unchanged.
- Revision write methods `create_revision_group`, `link_revision`, and
  `save_revision_snapshot` are byte-for-byte untouched; source-segment
  tests confirm the Essay update stays inside `create_revision_group` and
  `link_revision` and `INSERT INTO revision_snapshots` stays inside
  `save_revision_snapshot`; the three-sequential-commit relationship
  workflow is unchanged (existing Revision transaction tests pass).

## Verification layers

### Layer 1 — Static

- `py_compile` of all changed/new modules: PASS.
- Imports of `SQLiteRevisionRepository`, `RevisionRepository`, `Database`,
  `RevisionService`, `build_submission_service`, `AdminReanalysisService`,
  `FeedbackPipeline`, and both app-construction paths: PASS (no circular
  imports); `RevisionService.repository` annotation confirmed as
  `RevisionRepository`.
- Task-scoped `git diff --check`: PASS.
- UTF-8/replacement-character scan: 0 defects.

### Layer 2 — Focused F6A0 contract and identity tests

Command (F6A0 isolation runner):

```
pytest -q tests/test_v095f6a0_revision_capability_completion.py
       tests/test_revision_v05.py
       tests/test_v06_configuration_dashboard.py
       tests/test_v095e_repository_modularization.py
```

Result: **53 passed, 2 warnings** (13 new F6A0 tests + existing Revision
relationship/snapshot/API behavior, Admin Reanalysis construction, and
v0.9.5-E facade parity). This covers structural Protocol satisfaction,
signature parity, delegation count/pass-through, missing-record behavior,
exception propagation, no-connection/source-segment checks, write-method
ownership, facade wiring identity, single-graph proof, and the 86-method
facade count.

### Layer 3 — Accumulated architecture contracts

Command:

```
pytest -q tests/test_v095f2_service_narrowing.py
       tests/test_v095f3_learner_read_model_narrowing.py
       tests/test_v095f4_reanalysis_journey_narrowing.py
       tests/test_v095f5a_calf_service_narrowing.py
       tests/test_v095f5b_research_service_narrowing.py
       tests/test_v095e_repository_modularization.py
       tests/test_v095d_api_contract.py
       tests/contracts/api_surface_contract.py
       tests/test_v095d_parity.py
       tests/test_design_tokens_v094a.py
       tests/test_v095c_feature_extraction.py
       tests/test_v095b_router_contract.py
```

Result: **161 passed, 2 warnings** — F2/F3/F4/F5A/F5B dependency contracts
pass; v0.9.5-E repository facade parity passes (86 methods, 33 table
owners, zero signature/delegation/SQL drift; the two new repository methods
are not part of the 86-method facade inventory and are not scanned by the
guard); API contract 77 path+method pairs; frontend client 52 public
methods; locale parity 520/520; migration 12; active configuration
`config-v0.9.0`.

One run of this layer hit the documented pre-existing lifecycle race in
`test_v095b_router_contract.py::test_business_route_gated_until_ready_while_health_available`
(a production-mode `TestClient` in an earlier test spawns the background
startup thread that can flip the global lifecycle state mid-test). The test
passes in isolation (1 passed, 0.55s) and passes in the rerun of the full
set; it is unrelated to F6A0 (the F6A0 diff touches only the Revision
repository and the facade wiring) and remains recorded as a pre-existing
environmental flake, not repaired under this scope.

### Full non-live core regression (fresh isolated database)

Command: `pytest -q --ignore=tests/live`

Result: **559 passed, 8 skipped, 2 warnings** in 246.55s (546 baseline +
13 new F6A0 tests; the Playwright/live-stack suite was not run per scope).

### Exact launcher verification (fresh isolated database, dotenv disabled)

Command: `cmd /c "run.bat --verify"`

Result: PASS (exit 0):

- Migration **12**; **33** tables; active configuration **config-v0.9.0**;
  prompt **feedback-prompt-v0.7.1**; provider local.
- FastAPI `/api/v1/system/health` **200**; `/docs` **200**; Streamlit **200**.
- All application processes stopped; ports 8000/8501 free afterward.

## Database safety

Every write-capable run used a fresh unique temporary database with
`PYTHON_DOTENV_DISABLED=1`, `DATABASE_URL` absent, `DATABASE_PATH` inside
the temporary directory, `LLM_PROVIDER=local`, resolved-path assertions,
and cleanup. The development database was checked by SHA-256, size, and
mtime before and after every run and did not change; it was never opened.
All temporary databases and directories were removed; no listeners remain.
No user export was created or modified.

- Focused run DB: `C:\Users\16073\AppData\Local\Temp\v095f6a0-04hgf9bx\run.db`
- Contract run DB: `C:\Users\16073\AppData\Local\Temp\v095f6a0-svprhqt0\run.db`
- Full core run DB: `C:\Users\16073\AppData\Local\Temp\v095f6a0-mwx4aele\run.db`
- Launcher run DB:
  `C:\Users\16073\AppData\Local\Temp\v095f6a0-runbat-346d634d\runbat-verify.db`
- Development DB: `data/writing_feedback.db` — SHA-256
  `340E0F3739FEFFD3DEF87BB6E711CB6F90A8478E7E18D833C715EDCFAB03AFF4`, size
  8,298,496 bytes, mtime `2026-08-02T11:02:25.887+08:00` before and after
  all runs (unchanged; never opened).

## Impact review and limitations

The complete F6A0 diff (two production files, one focused test file, one
isolation runner, and documentation) was reviewed; only the approved files
changed. The E-era generator `verification/v0.9.5-e/build_database_facade.py`
still contains the pre-F6A0 wiring string; it is a standalone historical
artifact not executed by tests or verification, and it was left untouched
per the strict F6A0 scope (noted, not modified). The CRG CLI defect remains
(uv trampoline, not repaired); GitNexus was refreshed to `b766284` during
the F6A blocker stage and its index is current for the baseline.

## Decision

v0.9.5-F6A0 is complete and verified. The facade-owned
`SQLiteRevisionRepository` now structurally satisfies the central
`RevisionRepository` contract with exactly two read delegations and no
other change. The original v0.9.5-F6A runtime narrowing may be rebaselined
on this new HEAD and resumed only under a separate authorization; F6A0
performed no runtime narrowing and F6B or any later stage was not started.
