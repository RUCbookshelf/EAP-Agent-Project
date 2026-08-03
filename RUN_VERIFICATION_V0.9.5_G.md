# v0.9.5-G Verification - Database Facade Contraction

**Date:** 2026-08-03
**Status:** PASS
**Baseline commit:** `eacf76b` (v0.9.5-F6D verification); F2-F6D commits are
ancestors
**Implementation commit:** `refactor(v0.9.5-g): contract database facade`
**Verification commit:** `test(v0.9.5-g): verify final persistence boundaries`
**Specification:** `docs/development/V0.9.5_G_SPEC.md`
**Authorization:** Owner-authorized v0.9.5-G stage (pasted instruction file).

## Scope (Database facade contraction only)

Every remaining active caller of the 86-method `Database` public facade was
migrated to existing facade-owned aggregate Repositories, Services, or new
exact API Ports; the public surface was contracted to the evidence-supported
infrastructure set (`connect`, `initialize`); the `SQLiteRepository = Database`
alias and its export were removed; `Database` remains the sole owner of one
`SQLiteConnectionManager` and one Repository graph. No Repository
implementation, SQL, transaction boundary, API contract, schema, prompt,
provider, UI, or behavior changed.

## Baseline and final facade inventory

Baseline: **86 public methods** (historical E evidence preserved unchanged in
`verification/v0.9.5-e/prechange_repository_inventory.json` and the restored
`postchange_repository_inventory.json`). Final: **2 public methods**.

Retained (A - graph lifecycle/infrastructure):

```text
connect       - infrastructure entry to the facade-owned connection manager
initialize    - graph lifecycle (schema/migrations for the composed graph)
```

Removed: **84 methods**, each recorded in
`verification/v0.9.5-g/removal_ledger.json` (method + aggregate owner) with a
replacement access path (`_<owner>_repository.<method>` or an exact API Port)
or a zero-caller proof (E items: `list_all_students`, `get_exercises`,
`normalize_revision_stage`, `list_practice_evaluations`,
`save_feedback_engagement_trace`, `save_transfer_evidence_candidate`,
`save_practice_state_snapshot`, `list_practice_state_snapshots`). Every
removed method still exists intact on its aggregate Repository (AST-verified).
No `__getattr__`, dynamic delegation, public Repository bundle, or generic
accessor was added.

## Production caller migration

- **Zero `Depends(get_repository)`** remains in production Routers; zero
  production Routers receive the broad `Database`; `get_repository` was
  removed from `app/api/deps.py`.
- New `app/api/ports.py` defines ten exact API-owned Ports
  (`SubmissionBundleReadPort`, `StudentLookupPort`, `AnalysisRunReadPort`,
  `CalfReadPort`, `ResearchExportWritePort`, `StudentSubmissionListPort`,
  `RevisionGroupLookupPort`, `StudentLearnerReadPort`,
  `SubmissionCalibrationReadPort`, `SystemMigrationPort`) satisfied by
  facade-owned aggregate Repositories; both application paths compose them on
  `app.state` with ten narrow dependency accessors.
- `require_student` keeps its signature, 404 behavior, exception type, and
  message; students/revisions Routers feed it the `StudentLookupPort`
  (facade-owned `SQLiteLearnerRepository`).
- `app/api/main.py` lifecycle: `migration_version` x2 and
  `get_active_configuration` moved to `_system_repository` /
  `_configuration_repository` (composition-root private access);
  `initialize` retained.
- `app/feedback/service.py`: `LearnerHistoryService(self.database)` ->
  `LearnerHistoryService(self.database._submission_repository)`;
  `record_versions` -> `_system_repository.record_versions`; `initialize`
  retained; public constructor/workflow unchanged; one graph.
- Research export best-effort block preserved exactly (`hasattr` guard +
  try/except pass) through `ResearchExportWritePort.save_export_job`.

## Operational, test, and verification migration

- Scripts (demo_journey, seed_longitudinal_data, seed_demo_data,
  verify_closed_loop, audit_live_verification, initialize_project,
  migrate_database, verify_live_deepseek, verify_live_deepseek_v08): business
  calls moved to the exact facade-owned aggregate Repositories (private
  composition-root access); CLI, output, exit codes, provider behavior, and
  order preserved; live-provider scripts compile/import verified only.
- Verification helpers (`capture_prechange_fresh_database.py`, the dated
  `cross_page_flow.py` artifact): migrated to private aggregate access.
- Tests: ~24 files migrated from broad-facade convenience to
  `database._<owner>_repository` or exact Ports; the v0.9.5-E parity test was
  updated to the G-era contract (retained-surface parity, removal-ledger
  proof) while the historical E inventory JSON remains untouched; the parity
  script output was redirected to
  `verification/v0.9.5-g/postchange_facade_inventory.json`.

## `SQLiteRepository` alias and package exports

Active uses were only the definition/export and one parity-test identity
assertion; no production or operational use. The alias and export were
removed; `app/database/__init__.py` now exports `Database`,
`LATEST_MIGRATION_VERSION`, `rollback`, `upgrade`; a test proves no internal
`SQLiteRepository` import remains (the E-era generator that emits the legacy
alias text for historical evidence is excluded as a documented artifact).

## Transaction and Repository parity

No transaction boundary changed: SubmissionService independent commits,
Revision three-commit workflow, Admin partial commits, Practice
Attempt-first/Evaluation-best-effort, Research best-effort export job, learner
snapshot/evidence atomicity, and CALF write guards all pass their F2-F6D
contract suites unchanged. `Database.transaction()` was removed as test-only
after its single test caller migrated. Repository implementations,
signatures, SQL, DDL, migrations, and table ownership are unchanged
(v0.9.5-E parity under the G-era contract: 33 table owners, zero drift,
migration 12).

## Verification layers

### Layer 1 - Static

- `py_compile` of all changed/new modules: PASS.
- Imports of `Database`, database package exports, all API Ports, all
  dependency accessors, both application paths, all Routers, and
  FeedbackPipeline: PASS (no circular imports).
- Task-scoped `git diff --check`: PASS (user-owned `AGENTS.md` excluded).
  UTF-8/replacement scan: 0 defects.

### Layer 2 - Facade inventory

- Baseline 86 -> final 2 public methods (exact retained set `{connect,
  initialize}`); 84 removals all in the disposition ledger; no unapproved
  method added; no dynamic delegation; no public Repository bundle/accessor.

### Layer 3 - Caller elimination

- Zero production `Depends(get_repository)`; zero production Router
  `Database` parameters or business facade calls; zero active Service
  broad-facade dependencies; only approved composition roots import/construct
  `Database`; all active scripts/tests compile against the final surface; no
  internal unsupported `SQLiteRepository` import.

### Layer 4 - Identity

- One Database per application graph; one connection manager; one instance of
  every aggregate Repository; all app-state Ports/Services receive the exact
  facade-owned instances (identity asserted for the ten new readers and all
  F2-F6D ports); no second graph; no adapter/proxy/bundle.

### Layer 5 - Behavior

Focused suite (35 files, G isolation runner) covering health/version,
all migrated Router endpoints, `require_student`, Research export best-effort,
FeedbackPipeline, script local-mode behavior, alias/export behavior, and all
F2-F6D dependency contracts: **437 passed, 2 skipped, 2 warnings**.

### Layer 6 - Transaction and Repository parity

F2-F6D failure/partial-commit contracts pass unchanged (Submission, Revision
three-commit, Admin, Practice, learner, CALF, Research); v0.9.5-E Repository
behavior and table-owner parity pass under the G-era contract.

### Layer 7 - Frozen contracts

```text
Migration:               12
Tables:                  33
Configuration:           config-v0.9.0
Feedback prompt:         feedback-prompt-v0.7.1
API path+method pairs:   77
Frontend client methods: 52
Locale parity:           520/520
Database public methods: 2 (G-era evidence-derived value)
```

## Full non-live core regression (fresh isolated database)

Command: `pytest -q --ignore=tests/live`

Result: **653 passed, 8 skipped, 2 warnings** in 314.85s (638 baseline from
the completed F6D verification + 15 new G-era tests; the Playwright/live-stack
suite was not run per scope).

## Exact launcher verification (fresh isolated database, dotenv disabled)

Command: `cmd /c "run.bat --verify"`

Result: PASS (exit 0):

- Migration **12**; **33** tables; active configuration **config-v0.9.0**;
  prompt **feedback-prompt-v0.7.1**; provider local.
- FastAPI `/api/v1/system/health` **200**; `/docs` **200**; Streamlit **200**.
- All application processes stopped; ports 8000/8501 free afterward.

## Database safety

Every write-capable run used a fresh unique temporary database with
`PYTHON_DOTENV_DISABLED=1`, `DATABASE_URL` absent, `DATABASE_PATH` inside
the temporary directory, `LLM_PROVIDER=local`, resolved-path assertions, and
cleanup. The development database was checked by SHA-256, size, and mtime
before and after every run and did not change; it was never opened. All
temporary databases and directories were removed; no listeners remain; no
user export was created or modified.

- Focused run DB: `C:\Users\16073\AppData\Local\Temp\v095g-20fl3k28\run.db`
- Full core run DB: `C:\Users\16073\AppData\Local\Temp\v095g-xki4vgrw\run.db`
- Launcher run DB:
  `C:\Users\16073\AppData\Local\Temp\v095g-runbat-a9228f8b\runbat-verify.db`
- Development DB: `data/writing_feedback.db` - SHA-256
  `340E0F3739FEFFD3DEF87BB6E711CB6F90A8478E7E18D833C715EDCFAB03AFF4`, size
  8,298,496 bytes, mtime `2026-08-02T11:02:25.887+08:00` before and after
  all runs (unchanged; never opened).

## Impact review and limitations

The complete G diff (facade contraction, 10 API Ports, 7 Router migrations,
app-state/deps/lifecycle changes, FeedbackPipeline, 9 scripts, ~24 test files,
parity updates, and G-era artifacts) was reviewed; only the approved files
changed (56 tracked files; no Repository implementation, SQL, migration, API
schema, prompt, provider, UI, or localization change). GitNexus impact
analysis on `Database`: LOW risk, exact, 24 impacted nodes, 2 direct
importers, 0 affected processes. The documented lifecycle-race flake in
`test_v095b_router_contract.py` appeared once inside a large set and passed in
isolation (0.75s) and on rerun; it is unrelated to G and out of scope. The CRG
CLI defect remains documented, not repaired. The inactive conflict files
(`repository-冲突-Rain_Win11.py`, `submission-冲突-Rain_Win11.py`,
`factory-冲突-Rain_Win11.py`) were left untouched. User-owned paths were
preserved untouched.

## Decision

v0.9.5-G is complete and verified. The `Database` public surface is the
evidence-supported infrastructure set (`connect`, `initialize`); all 84
removed methods have a recorded caller migration or zero-caller proof with
the aggregate Repository methods intact; zero production Router uses the
broad facade; `require_student` uses a narrow learner lookup; the
`SQLiteRepository` alias is removed; one Database/connection manager/
Repository graph remains; no Repository implementation, SQL, or transaction
boundary changed; all frozen contracts hold; the development database was
never opened or modified; core v0.9.5 modularization and persistence
decoupling may be declared complete.
