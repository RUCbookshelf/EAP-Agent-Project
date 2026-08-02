# v0.9.5-F4 Verification — Reanalysis and Journey Dependency Narrowing

**Date:** 2026-08-02
**Status:** PASS
**Baseline commit:** `256b172` (v0.9.5-F3 verification); F2 `7927ca7` and F3
`a24312a`/`256b172` are ancestors
**Implementation commit:** `refactor(v0.9.5-f4): narrow reanalysis and journey
dependencies`
**Verification commit:** `test(v0.9.5-f4): verify domain read service contracts`
**Specification:** `docs/development/V0.9.5_F4_SPEC.md`

## Scope (exactly two Services narrowed)

1. `ReanalysisService` — runtime dependency changed from the broad
   `ReanalysisRepository` composite (EssayRepository | MetricRepository) to
   two explicit consumer Ports:
   - `SubmissionBundleReadPort.get_submission_bundle(essay_id)`
     (`app/infrastructure/sqlite/repositories/submission.py:151`);
   - `AnalysisRunWritePort.save_analysis_run(essay_id, analysis)`
     (`app/infrastructure/sqlite/repositories/analysis.py:21`).
   The analyzer dependency is unchanged; the Service performs one bundle read
   and, on success, exactly one Analysis save; missing-bundle and
   analyzer-failure paths perform zero writes. No shared transaction.
2. `JourneyService` — dependency changed from `repository: Any` (broad
   facade) to two explicit read Ports:
   - `JourneyStudentReadPort.get_student(student_id)`
     (`app/infrastructure/sqlite/repositories/learner.py:30`);
   - `JourneyProjectionReadPort` with the exact eight Practice-owned
     projection methods (`app/infrastructure/sqlite/repositories/practice.py`:
     `list_essays_by_student`, `list_analysis_runs_for_student`,
     `list_feedback_records_for_student`, `list_practice_targets`,
     `list_exercise_attempts_by_student`, `list_practice_evaluations_by_student`,
     `list_within_task_responses`, `list_transfer_evidence_candidates`).
   The Service remains strictly read-only with zero persistence calls.

## Authorized scope exception

`scripts/demo_journey.py` (lines 105 and 241) constructed
`JourneyService(repository)` from the broad facade. The owner explicitly
authorized a two-line operational-script exception on 2026-08-02; both sites
now construct
`JourneyService(repository._learner_repository, repository._practice_repository)`.
No other script logic, CLI argument, output, ordering, exception handling,
database initialization, or cleanup behavior changed. The blocker and its
resolution are recorded in `docs/development/BLOCKER_REPORT_V0.9.5_F4.md`.

## Contract evidence

- Four consumer-owned `typing.Protocol` Ports with exact method sets, located
  in their consumer modules (`app/services/reanalysis.py`,
  `app/journey/service.py`); no inheritance that recreates a broad
  repository; no concrete SQLite imports; no `Database` imports.
- Port method signatures (parameters, defaults, return annotations) match the
  repository implementations at HEAD exactly (`inspect.signature` parity).
- `SQLiteSubmissionRepository`, `SQLiteAnalysisRepository`,
  `SQLiteLearnerRepository`, and `SQLitePracticeRepository` structurally
  satisfy their Ports; the `Database` facade remains structurally compatible
  for legacy verification only.
- `ReanalysisService` and `JourneyService` modules contain no
  `app.database` / `SQLite*` imports, no `hasattr` capability discovery, no
  internal construction, no `Any` persistence annotation, and no broad
  repository field.

## Composition

- Both application-construction paths (`_run_startup`,
  `_build_full_app` in `app/api/main.py`) now construct
  `ReanalysisService(repository._submission_repository,
  repository._analysis_repository, analyzer)` and
  `JourneyService(repository._learner_repository,
  repository._practice_repository)`, and store the JourneyService on
  `app.state.journey_service`.
- `app/api/deps.py` exposes the narrow `get_journey_service` dependency;
  `app/api/routers/journey.py` consumes `Depends(get_journey_service)` and no
  longer receives `Database` or constructs the Service; the canonical 404
  student-existence check is preserved through `require_student` against the
  Service's student reader Port.
- Private facade repository access exists only in the composition root
  (`app/api/main.py`) and in the two authorized demo-script lines.
- Focused tests assert object identity: both Services use the exact
  facade-owned repository instances and the same `_connection_manager`; no
  second Database, connection manager, or repository graph is constructed.
- Journey URL, method, schema, status code, and response body unchanged;
  Analysis/CALF routers continue consuming `api.state.reanalysis`.

## Verification layers

### Layer 1 — Static

- `py_compile` of all changed/new modules: PASS.
- Imports of the four Ports, both Services, `create_app`/`_build_full_app`/
  `_run_startup`, `get_journey_service`, and the Journey router: PASS (no
  circular imports).
- Task-scoped `git diff --check`: PASS.
- UTF-8/replacement-character scan of all changed/new files: 0 replacements.

### Layer 2 — Dependency contracts

- Four Ports, exact method sets, and source signature parity: PASS
  (new focused tests).
- No `Database`/concrete-repository imports in the two Service modules; no
  `Any` repository annotation in JourneyService; no broad repository field in
  ReanalysisService; no router construction from the facade: PASS.
- No unrelated Service constructor changed; no repository implementation,
  facade method, SQL, transaction, schema, API, UI, or locale file changed
  (full `git diff` reviewed).

### Layer 3 — Focused behavior (fresh isolated database)

Command (F4 isolation runner with exact allow-list):

```
pytest -q tests/test_v095f4_reanalysis_journey_narrowing.py
       tests/test_journey_v093c.py
       tests/test_analysis_runs_v04.py
       tests/test_calf_v08.py
       tests/test_v06_configuration_dashboard.py
       tests/test_v095f2_service_narrowing.py
       tests/test_v095f3_learner_read_model_narrowing.py
       tests/test_v095e_repository_modularization.py
       tests/test_v095b_router_contract.py
```

Result: **118 passed, 2 warnings** (17 new F4 tests + existing Journey,
Reanalysis API, CALF append-only, F2, F3, v0.9.5-E facade-parity, and router
contract coverage).

### Layer 4 — Frozen contracts

Command:

```
pytest -q tests/test_v095d_api_contract.py
       tests/contracts/api_surface_contract.py
       tests/test_v095d_parity.py
       tests/test_design_tokens_v094a.py
       tests/test_v095c_feature_extraction.py
       tests/test_v095e_repository_modularization.py
       tests/test_v095b_router_contract.py
```

Result: **84 passed, 2 warnings** — API contract 77 path+method pairs;
frontend client 52 public methods; Database facade 86 methods; table owners
33/33; migration 12; active configuration `config-v0.9.0`; locale parity
520/520.

### Full non-live core regression (fresh isolated database)

Command: `pytest -q --ignore=tests/live`

Result: **508 passed, 8 skipped, 2 warnings** in 236.73s (492 baseline + 16
new F4 tests; the Playwright/live-stack suite was not run per scope).

### Exact launcher verification (fresh isolated database, dotenv disabled)

Command: `cmd /c "run.bat --verify"`

Result: PASS (exit 0):

- Migration **12**; **33** tables; active configuration **config-v0.9.0**;
  prompt `feedback-prompt-v0.7.1`; provider local.
- FastAPI `/api/v1/system/health` **200**; `/docs` **200**; Streamlit **200**.
- All application processes stopped; ports 8000/8501 free afterward.

## Database safety

Every write-capable run used a fresh unique temporary database with
`PYTHON_DOTENV_DISABLED=1`, `DATABASE_URL` absent, `DATABASE_PATH` inside the
temporary directory, `LLM_PROVIDER=local`, resolved-path assertions, and
cleanup. The development database was checked by SHA-256, size, and mtime
before and after every run and did not change.

- Focused run DB: `C:\Users\16073\AppData\Local\Temp\v095f4-4gvr750x\run.db`
- Contract run DB: `C:\Users\16073\AppData\Local\Temp\v095f4-9jpdieuf\run.db`
- Full core run DB: `C:\Users\16073\AppData\Local\Temp\v095f4-b03c7xnr\run.db`
- Launcher run DB:
  `C:\Users\16073\AppData\Local\Temp\v095f4-runbat-6fbacfd6\runbat-verify.db`
- Development DB: `data/writing_feedback.db` — SHA-256
  `340E0F3739FEFFD3DEF87BB6E711CB6F90A8478E7E18D833C715EDCFAB03AFF4`, size
  8,298,496 bytes, mtime `2026-08-02T11:02:25.8870088+08:00` before and after
  all runs (unchanged; never opened).
- All temporary databases/directories removed; no listeners remain.

## Impact review and limitations

The complete F4 diff was reviewed (production, demo-script exception, tests,
and documentation); only the approved files changed. GitNexus was refreshed
to HEAD `256b172` for Phase 0 and used for the one bounded dependency query
and the post-implementation scoped change-impact review; affected symbols are
the two Services, the composition root, the Journey router/dependency, the
demo-script construction sites, and directly affected tests. The Code Review
Graph CLI is unavailable in this environment (its uv tool directory is
missing), so that index could not be refreshed; static source and `git diff`
at HEAD remain authoritative.

## Deferred (unchanged by F4)

CalfService and ResearchDataService narrowing (medium-risk write
combinations), write-orchestration narrowing, facade contraction, Protocol
consolidation, transaction redesign, schema cleanup, `export_jobs` writer,
WTR collision fix, and legacy pipeline removal. v0.9.5-F5 must not begin
without a separate authorization.

## Decision

v0.9.5-F4 is complete and verified. F2 and F3 dependency boundaries remain
unchanged; no repository, SQL, transaction, schema, API, UI, or domain
behavior changed; the development database was never opened or modified.
