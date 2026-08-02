# v0.9.5-F2 Verification - Low-Risk Service Repository Dependency Narrowing

**Date:** 2026-08-02
**Status:** PASS
**Baseline commit:** `172dbe1` (v0.9.5-F1 audit); `7868b68` (v0.9.5-E verification) is an ancestor
**Implementation commit:** `05611fc` (`refactor(v0.9.5-f2): narrow low-risk service repositories`)
**Specification:** `docs/development/V0.9.5_F2_SPEC.md`

## Scope (exactly two Service dependencies narrowed)

1. `ConfigurationService` - runtime dependency changed from the broad 86-method
   `Database` facade to the existing `SQLiteConfigurationRepository` instance
   composed by the facade (`repository._configuration_repository`). Both
   application-construction paths changed: `app/api/main.py:152`
   (`_run_startup`) and `app/api/main.py:317` (`_build_full_app`).
2. `LearnerHistoryService` - declared contract changed from the broad central
   `LearnerHistoryRepository` to the new consumer-owned one-method
   `PriorRecordsPort` in `app/learner/history.py`; the runtime object supplied
   by `SubmissionService` remains unchanged.

No third Service was narrowed. `DashboardService`, `ProgressService`, and
`LearnerProfileService` were not modified (F3-deferred).

## Contract evidence

- Configuration consumer contract retained exactly seven methods
  (`list_configurations`, `get_configuration`, `get_active_configuration`,
  `create_configuration`, `set_configuration_validation`,
  `activate_configuration`, `list_configuration_audit`); no
  `ping`/`migration_version` added; central Protocol consolidation deferred.
- `SQLiteConfigurationRepository` satisfies the contract directly; no second
  connection manager, proxy, adapter, DI framework, or new facade method.
- `PriorRecordsPort` declares exactly one method with the source signature
  preserved from HEAD: `prior_records(self, submission: EssaySubmission) ->
  list[dict[str, Any]]` (`app/infrastructure/sqlite/repositories/submission.py:108`).
- `LearnerHistoryService.__init__` annotation is `PriorRecordsPort`; its call
  arguments, filtering, sorting, return shape, and history-selection semantics
  are unchanged.
- `SubmissionService` constructor and workflow are unchanged
  (`app/services/submission.py:55` still constructs
  `LearnerHistoryService(repository)`); `FeedbackPipeline` construction
  (`app/feedback/service.py:30`) is unchanged.
- The v0.9.5-E static parity guard is preserved with its default semantics. To
  accommodate the F2-approved `app/api/main.py` change, the parity script
  (`verification/v0.9.5-e/compare_repository_parity.py`) now subtracts an
  explicit allowlist read from `SERVICE_API_DIFF_ALLOWLIST` (default: unset =
  exact v0.9.5-E behavior). The F2 isolated runner sets
  `SERVICE_API_DIFF_ALLOWLIST=app/api/main.py`; `test_v095e_repository_modularization.py`
  itself is unchanged.

## Verification layers

### Layer 1 - Static
- `py_compile` of changed/new modules: PASS.
- Import of `ConfigurationService`, `LearnerHistoryService`, `PriorRecordsPort`,
  `create_app`/`_build_full_app`/`_run_startup`, and `SubmissionService`: PASS
  (no circular imports).
- `git diff --check` on F2 files: PASS.
- UTF-8/replacement-character scan of all changed/new files: 0 replacements.

### Layer 2 - Dependency contracts
- Configuration contract = exactly the seven methods; verified by import probe.
- Both composition paths pass `repository._configuration_repository` (asserted
  by new tests; the supplied object is `SQLiteConfigurationRepository`, not
  `Database`).
- `PriorRecordsPort` contains exactly `prior_records`; `LearnerHistoryService`
  references only that Port.
- No unrelated Service constructor changed; no Dashboard/Progress/LearnerProfile
  file changed; no repository implementation, facade method, SQL, or
  transaction changed (full `git diff` reviewed).

### Layer 3 - Focused behavior (fresh isolated database)
Command:
`pytest -q tests/test_v095f2_service_narrowing.py tests/test_v06_configuration_dashboard.py tests/test_history.py tests/test_repository_v02.py tests/test_database.py tests/test_v095e_repository_modularization.py tests/test_v095b_router_contract.py`

Result: **53 passed, 2 warnings** (11 new F2 tests + existing Configuration
listing/creation/validation/activation/audit/active, learner-history selection,
`prior_records`, SubmissionService construction, both FastAPI app-construction
paths, and the unchanged v0.9.5-E facade-parity test).

### Full non-live core regression (fresh isolated database)
Command: `pytest -q --ignore=tests/live`

Result: **480 passed, 8 skipped, 2 warnings** in 237.41s
(469 baseline + 11 new F2 tests; the Playwright/live-stack suite was not run
per the F2 scope). No failures.

### Exact launcher verification (fresh isolated database, dotenv disabled)
Command: `cmd /c "run.bat --verify"`

Result: PASS (exit 0):
- Migration **12**; **33** tables; active configuration **config-v0.9.0**;
  prompt `feedback-prompt-v0.7.1`; provider local.
- FastAPI `/api/v1/system/health` **200**; `/docs` **200**; Streamlit **200**.
- All application processes stopped; ports 8000/8501 free afterward.

### Frozen contract checks (covered by the passing core suite)
- API contract: **77 path+method pairs** (`test_v095d_api_contract`).
- Frontend client contract: **52 public methods** (`test_v095d_port_contract`).
- Locale parity: **520/520** (locale parity tests).
- Migration 12, 33 tables, `config-v0.9.0` unchanged.

## Database safety

Every write-capable run used a fresh unique temporary database with
`PYTHON_DOTENV_DISABLED=1`, `DATABASE_URL` absent, `DATABASE_PATH` inside the
temporary directory, `LLM_PROVIDER=local`, resolved-path assertions, and
cleanup. The development database was checked by SHA-256 and mtime before and
after every run and did not change.

- Focused run DB: `C:\Users\16073\AppData\Local\Temp\v095f2-20h5pm14\run.db`
- Full core run DB: `C:\Users\16073\AppData\Local\Temp\v095f2-15goj2u3\run.db`
- Launcher run DB: `C:\Users\16073\AppData\Local\Temp\v095f2-runbat-72dc86d7\runbat-verify.db`
- Development DB: `data/writing_feedback.db` - SHA-256
  `340E0F3739FEFFD3DEF87BB6E711CB6F90A8478E7E18D833C715EDCFAB03AFF4` before and
  after all runs (unchanged; never opened).
- All temporary databases/directories removed; no listeners remain.

## Impact review and limitations

The complete F2 diff was reviewed (production, parity helper, tests, and
documentation); only the approved files changed. Code Review Graph and GitNexus
indexes were 1 commit behind HEAD (the F1 commit was docs-only, so graph code
content is identical to HEAD); static source and `git diff` at HEAD are
authoritative. The parity-script allowlist is default-off and preserves the
v0.9.5-E verification semantics unless explicitly activated.

## Deferred (unchanged by F2)

v0.9.5-F3 (Dashboard/Progress/LearnerProfile and read-only domain narrowing),
v0.9.5-F4 (cross-aggregate write-orchestration narrowing), v0.9.5-G (facade
contraction), Protocol consolidation, facade-method removal, transaction
redesign, schema cleanup, `export_jobs` writer, legacy pipeline removal.

## Decision

v0.9.5-F2 is complete and verified. v0.9.5-F3 may begin only under a separate
authorization; it was not started here.
