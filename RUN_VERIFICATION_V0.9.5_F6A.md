# v0.9.5-F6A Verification — RevisionService Runtime Repository Narrowing

**Date:** 2026-08-02
**Status:** PASS
**Baseline commit:** `b4d37af` (v0.9.5-F6A0 verification); F2-F6A0 commits
are ancestors
**Implementation commit:** `refactor(v0.9.5-f6a): narrow revision runtime repository` (`8e20730`)
**Verification commit:** `test(v0.9.5-f6a): verify revision runtime contracts`
**Specification:** `docs/development/V0.9.5_F6A_SPEC.md`
**Authorization:** Owner authorization 2026-08-02 to resume F6A on the new
verified baseline after the separately completed F6A0 prerequisite.

## Scope (runtime repository narrowing only)

`RevisionService` runtime repository changed from the broad 86-method
`Database` facade to the existing facade-owned `SQLiteRevisionRepository`
instance at every active direct and indirect construction path. No new
Revision Port was created; the central `RevisionRepository` Protocol and
`app/services/revision.py` are unchanged; `RevisionService` remains typed
`repository: RevisionRepository`.

## Existing central `RevisionRepository` method set (unchanged)

```text
get_submission_bundle
get_latest_analysis_run
create_revision_group
link_revision
get_revision_group
get_revision_group_for_submission
list_revision_candidates
save_revision_snapshot
list_revision_snapshots
get_latest_revision_snapshot
```

## Actual direct RevisionService call set (unchanged, verified)

`get_submission_bundle` (validate_relationship x3, _calculate x2, trajectory
per member), `get_latest_analysis_run` (_calculate x2),
`create_revision_group`, `link_revision`, `get_revision_group`,
`list_revision_candidates`, `save_revision_snapshot`,
`list_revision_snapshots`, `get_latest_revision_snapshot` - nine direct
calls, no others.

## Runtime dependency before and after

Before: `Database` facade supplied at `app/api/main.py` (both paths),
`build_submission_service`, `AdminReanalysisService` embedded, and
`FeedbackPipeline`.

After: `repository._revision_repository` (the exact facade-owned
`SQLiteRevisionRepository` instance, with its existing Submission and
Analysis readers and shared connection manager) at every site.

## All direct and indirect construction sites (Phase 0 inventory)

Direct `RevisionService(...)`:

1. `app/api/main.py` `_run_startup` - `RevisionService(repository=repository._revision_repository)`
2. `app/api/main.py` `_build_full_app` - same
3. `app/services/admin_reanalysis.py` embedded - `RevisionService(revision_repository)` via new required keyword-only `revision_repository` injection
4. `app/feedback/service.py` FeedbackPipeline - `RevisionService(self.database._revision_repository)`
5. `tests/test_revision_v05.py` - `RevisionService(repository=repository._revision_repository)`
6. `tests/test_v06_configuration_dashboard.py` - same

Indirect via `build_submission_service(...)` (20 sites, all passing
`revision_repository=<facade>._revision_repository`): production
`app/api/main.py` (153, 357); scripts `demo_journey.py`,
`verify_live_deepseek_v061.py`, `verify_live_deepseek_v071.py` (5 sites),
`verify_live_deepseek_v08.py` (2 sites); tests
`test_diagnostic_calibration_v061.py`, `test_journey_v093c.py` (2),
`test_live_deepseek_v07.py`, `test_research_v082.py`,
`test_v071_reliability_ui.py`, `test_v095f3_learner_read_model_narrowing.py`
(2); verification helper `capture_prechange_fresh_database.py`.
`AdminReanalysisService` construction sites (6) all pass
`revision_repository=repository._revision_repository`. The inactive conflict
file `app/services/factory-冲突-Rain_Win11.py` was not touched.

## Composition results

- Both application-construction paths: `api.state.revisions.repository is
  api.state.repository._revision_repository` (identity asserted); the
  SubmissionService embedded revision service and the AdminReanalysisService
  embedded revision service use the same facade-owned instance; none is the
  facade; all share `database._connection_manager`; the already-composed
  `_submission_reader`/`_analysis_reader` are unchanged.
- Factory: `build_submission_service` gained a required keyword-only
  `revision_repository: RevisionRepository`; no broad-facade fallback was
  added (every active caller passes the facade-owned instance).
- Admin Reanalysis: required keyword-only `revision_repository` injection;
  no private facade access inside the Service; its own broad repository
  dependency and all public methods unchanged.
- FeedbackPipeline: one authorized composition line
  (`RevisionService(self.database._revision_repository)`); constructor,
  initialization, workflow, and behavior unchanged.
- No second `Database`, connection manager, `SQLiteRevisionRepository`,
  adapter, proxy, or repository graph was created (single construction site
  in production; identity tests).

## Transaction and failure semantics

Focused failure-injection tests (repository-level, real database) prove:

- successful `create_relationship` calls `create_revision_group`,
  `link_revision`, `save_revision_snapshot` in exactly that order (one
  repository call each; recorder wrappers);
- each call is an independent repository-owned operation; no shared
  transaction is introduced;
- if `link_revision` fails: the group row and the source Essay update from
  `create_revision_group` (commit 1) remain visible, the target Essay is
  unlinked, and zero snapshots exist - no rollback compensation;
- if `save_revision_snapshot` fails: commits 1 and 2 remain visible (group
  row; target Essay has `revision_group_id`, `revision_of_submission_id`,
  `revision_sequence`), and zero snapshots exist;
- Essay updates remain inside `create_revision_group` and `link_revision`
  (source-segment assertions).

## Verification layers

### Layer 1 - Static

- `py_compile` of all changed/new modules: PASS.
- Imports of `RevisionService`, `RevisionRepository`, both app-construction
  paths, `build_submission_service`, `AdminReanalysisService`,
  `FeedbackPipeline`: PASS (no circular imports); factory and Admin
  constructor signatures confirmed.
- Task-scoped `git diff --check`: PASS. UTF-8/replacement scan: 0 defects.

### Layer 2 - Runtime dependency contracts

- No new Revision Protocol; central `RevisionRepository` unchanged;
  `RevisionService` still types against it; `app/services/revision.py`
  contains no `Database`/SQLite imports, no `hasattr`, no fallback.
- Every active production instance receives `SQLiteRevisionRepository`
  (identity tests); no active instance receives the broad `Database`
  (source and runtime checks); no unrelated Service dependency changed; no
  repository implementation, SQL, or migration file changed.

### Layer 3 - Repository composition identity

- All injected Revision repositories are the exact facade-owned instance;
  no second `SQLiteRevisionRepository` was instantiated; all share the
  expected connection manager; internal Submission and Analysis readers are
  the existing composed instances; no new reader, adapter, proxy, or
  wrapper was created.

### Layer 4 - Revision behavior

Command (F6A isolation runner):

```
pytest -q tests/test_v095f6a_revision_runtime_narrowing.py
       tests/test_revision_v05.py
       tests/test_v06_configuration_dashboard.py
       tests/test_v095f6a0_revision_capability_completion.py
       tests/test_v095f3_learner_read_model_narrowing.py
       tests/test_v095f5a_calf_service_narrowing.py
       tests/test_v095f5b_research_service_narrowing.py
       tests/test_journey_v093c.py
       tests/test_v095e_repository_modularization.py
       tests/test_v095b_router_contract.py
```

Result: **155 passed, 2 warnings** (14 new F6A tests + existing Revision
relationship/candidate/group/snapshot/trajectory/API behavior, Admin
Reanalysis, factory integration, app-construction paths, and v0.9.5-E
facade parity).

### Layer 5 - Transaction and failure semantics

Covered by the F6A focused tests in Layer 4 (see Transaction and failure
semantics above): call order, commit visibility on later-call failures,
no compensation, no shared transaction, Essay-update ownership.

### Layer 6 - Accumulated architecture contracts

Command:

```
pytest -q tests/test_v095f2_service_narrowing.py
       tests/test_v095f3_learner_read_model_narrowing.py
       tests/test_v095f4_reanalysis_journey_narrowing.py
       tests/test_v095f5a_calf_service_narrowing.py
       tests/test_v095f5b_research_service_narrowing.py
       tests/test_v095f6a0_revision_capability_completion.py
       tests/test_v095f6a_revision_runtime_narrowing.py
       tests/test_v095e_repository_modularization.py
       tests/test_v095d_api_contract.py
       tests/contracts/api_surface_contract.py
       tests/test_v095d_parity.py
       tests/test_design_tokens_v094a.py
       tests/test_v095c_feature_extraction.py
       tests/test_v095b_router_contract.py
```

Result: **188 passed, 2 warnings** - F2/F3/F4/F5A/F5B/F6A0 dependency
contracts pass; v0.9.5-E repository facade parity passes (86 methods, 33
table owners, zero drift) under the exact F6A `SERVICE_API_DIFF_ALLOWLIST`;
API contract 77 path+method pairs; frontend client 52 public methods;
locale parity 520/520; migration 12; active configuration `config-v0.9.0`.

### Full non-live core regression (fresh isolated database)

Command: `pytest -q --ignore=tests/live`

Result: **573 passed, 8 skipped, 2 warnings** in 259.39s (559 baseline
from the completed F6A0 verification + 14 new F6A tests; the
Playwright/live-stack suite was not run per scope).

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
All temporary databases and directories were removed; no listeners remain;
no user export was created or modified.

- Focused run DB: `C:\Users\16073\AppData\Local\Temp\v095f6a-uv515pgh\run.db`
- Contract run DB: `C:\Users\16073\AppData\Local\Temp\v095f6a-m6lfyfql\run.db`
- Full core run DB: `C:\Users\16073\AppData\Local\Temp\v095f6a-q11fba00\run.db`
- Launcher run DB:
  `C:\Users\16073\AppData\Local\Temp\v095f6a-runbat-fcff27ec\runbat-verify.db`
- Development DB: `data/writing_feedback.db` - SHA-256
  `340E0F3739FEFFD3DEF87BB6E711CB6F90A8478E7E18D833C715EDCFAB03AFF4`, size
  8,298,496 bytes, mtime `2026-08-02T11:02:25.887+08:00` before and after
  all runs (unchanged; never opened).

## Blocker resolution

The original blocker (`docs/development/BLOCKER_REPORT_V0.9.5_F6A.md`) was
resolved by the separately completed v0.9.5-F6A0 prerequisite: the
facade-owned `SQLiteRevisionRepository` now structurally satisfies the
central `RevisionRepository` (both missing methods present, facade-owned
Submission/Analysis readers wired, one connection manager, no second
graph). F6A resumed on HEAD `b4d37af` per owner authorization and required
no repository, SQL, transaction, or Protocol change.

## Impact review and limitations

The complete F6A diff (production composition, operational caller updates,
tests, runner, and documentation) was reviewed; only the approved files
changed. The inactive conflict file
`app/services/factory-冲突-Rain_Win11.py` was left untouched. The CRG CLI
defect remains (uv trampoline, not repaired); GitNexus was synchronized to
HEAD `b4d37af` before F6A resumed.

## Decision

v0.9.5-F6A is complete and verified. Every active `RevisionService`
receives the existing facade-owned `SQLiteRevisionRepository`; no broad
facade runtime remains; no new Port, fallback, proxy, or shared transaction
was introduced; the three-sequential-commit workflow and Essay-update
ownership are unchanged; F2-F6A0 boundaries remain unchanged; the
development database was never opened or modified; no F6B or later-stage
work was started.
