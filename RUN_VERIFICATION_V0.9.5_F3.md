# v0.9.5-F3 Verification Report

## Scope (exactly the authorized learner read-model chain)

1. `ProgressService` now depends on two consumer-owned Ports:
   `LearnerProgressPort` (`list_visualization_records`,
   `save_learner_profile_snapshot`) and `ActiveConfigurationPort`
   (`get_active_configuration`); the inactive `list_longitudinal_records`
   fallback and the relevant `hasattr` capability discovery were removed only
   from `ProgressService`. Facade/repository methods were not deleted.
2. `LearnerProfileService` depends on `LearnerProfileReadPort`
   (`get_latest_learner_profile`, `list_learner_profile_snapshots`) and an
   explicitly injected `ProgressService`; it no longer constructs
   `ProgressService` internally.
3. `DashboardService` depends on `DashboardReadPort`
   (`list_visualization_records`) and an explicitly injected
   `ProgressService`; it no longer constructs `ProgressService` internally.
4. `build_submission_service` accepts optional keyword-only
   `learner_repository` / `configuration_repository` composition inputs.
   Production paths pass the facade-owned extracted repositories; legacy
   callers omit them and the existing repository argument structurally
   satisfies both Ports (no `hasattr` restoration).
5. Both application-construction paths (`_run_startup`,
   `_build_full_app`) and the legacy `FeedbackPipeline` reuse the one existing
   `Database` object's composed `SQLiteLearnerRepository` and
   `SQLiteConfigurationRepository` instances. The `FeedbackPipeline`
   composition change is the single production-file exception explicitly
   authorized by the user on 2026-08-02 (recorded in
   `docs/development/BLOCKER_REPORT_V0.9.5_F3.md`).

No other Service, router, repository, SQL, transaction, schema, domain model,
frontend, locale, or UI file was changed. F4/F5/G were not started.

## Contract evidence

- Exactly four consumer-owned Ports exist with the exact method sets above and
  source signatures preserved from HEAD (contract tests).
- `SQLiteLearnerRepository` structurally satisfies `DashboardReadPort`,
  `LearnerProfileReadPort`, and `LearnerProgressPort`;
  `SQLiteConfigurationRepository` satisfies `ActiveConfigurationPort`; the
  `Database` facade remains structurally compatible for deferred legacy paths.
- The three F3 Service modules do not import `app.database` or any concrete
  SQLite repository; no `ProgressService` construction remains inside
  `LearnerProfileService` or `DashboardService`.
- No relevant `hasattr` capability branch remains; the
  `list_longitudinal_records` fallback was removed only from `ProgressService`.
- `persist=False` performs zero snapshot/evidence writes; `persist=True`
  performs exactly one `save_learner_profile_snapshot` call; the repository
  method retains snapshot + evidence-registry transaction ownership.
- Active configuration is queried exactly once per snapshot at the same point
  in the calculation; `None`/missing configuration preserves the existing
  default payload/version behavior; configuration reads remain read-only.
- Dashboard and Learner Profile outputs, ordering, labels, status values,
  empty states, and error behavior are unchanged (existing tests).
- `SubmissionService` constructor and workflow are unchanged; the embedded
  Learner Profile chain uses the narrowed F3 composition in production and in
  `FeedbackPipeline`.

## Static (Layer 1)

- `py_compile` of all changed/new modules: PASS.
- Import of the four Ports, three Services, `build_submission_service`, and
  both app-construction paths: PASS (no circular imports).
- `git diff --check` on all F3 files: PASS.
- UTF-8/replacement-character scan: 0 replacements.

## Focused behavior (Layer 3, fresh isolated database)

Command (F3 isolation runner with exact `SERVICE_API_DIFF_ALLOWLIST`):

```
pytest -q tests/test_v095f3_learner_read_model_narrowing.py
       tests/test_v095f2_service_narrowing.py
       tests/test_v095e_repository_modularization.py
       tests/test_history.py tests/test_database.py
       tests/test_v06_configuration_dashboard.py
       tests/test_longitudinal_v03.py tests/test_longitudinal_llm_v03.py
       tests/test_learner_model_v07.py tests/test_snapshot_repository_v03.py
       tests/test_v095b_router_contract.py
```

Result: **96 passed, 2 warnings** (12 new F3 tests + existing Progress,
Learner Profile, Dashboard, FeedbackPipeline, F2, and facade-parity coverage).

## Frozen contracts (Layer 4)

- API contract: 77 path+method pairs.
- Frontend client contract: 52 public methods.
- Database facade: 86 public methods; table owners 33/33.
- Migration 12; active configuration `config-v0.9.0`.
- Locale parity: 520/520.

## Full core regression (fresh isolated database)

Command: `pytest -q --ignore=tests/live`

Result: **492 passed, 8 skipped, 2 warnings** (480 baseline + 12 new F3
tests; Playwright/live-stack suite not run per scope).

## Exact launcher verification (separate fresh isolated database, dotenv disabled)

Command: `cmd /c "run.bat --verify"`

Result: **PASS (exit 0)**: migration 12; 33 tables; `config-v0.9.0`; FastAPI
health 200; docs 200; Streamlit 200; ports 8000/8501 free afterward; all
processes stopped; temporary directory removed.

## Scoped change-impact review

- Code Review Graph `detect-changes` (base `7927ca7`): 15 F3 files, 37 changed
  symbols, 0 affected flows, risk 0.65. The reported test-gap list is a
  stale-index artifact (the graph predates the new F3 test file, which covers
  the listed Dashboard symbols).
- GitNexus `detect_changes` marked risk "critical" only because its
  all-scope diff includes preserved user-owned files (`AGENTS.md`,
  `RUN_VERIFICATION_V0.7.md`, `RUN_VERIFICATION_V0.8.2.md`) that predate F3;
  its affected processes are exactly the expected composition flows (app
  construction, submission factory, snapshot creation), all covered by
  passing focused tests. Source and tests are authoritative.

## Database safety

- Development database SHA-256 before/after every write-capable run:
  `340E0F3739FEFFD3DEF87BB6E711CB6F90A8478E7E18D833C715EDCFAB03AFF4`
  (unchanged; mtime `2026-08-02T03:02:25.8870088Z`).
- All runs used fresh unique temporary databases with
  `PYTHON_DOTENV_DISABLED=1`, `DATABASE_URL` absent, `DATABASE_PATH` inside
  the temp directory, `LLM_PROVIDER=local`, resolved-path assertions, and
  post-run cleanup; ports verified free.

## Commits

- `refactor(v0.9.5-f3): narrow learner read-model dependencies`
- `test(v0.9.5-f3): verify learner read-model contracts`

## Deferred

v0.9.5-F4 (write-orchestration narrowing), facade contraction, Protocol
consolidation, transaction redesign, schema cleanup, and any further
narrowing are deferred and require separate authorization. F4 has not begun.
