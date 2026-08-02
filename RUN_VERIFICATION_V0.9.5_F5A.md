# v0.9.5-F5A Verification — CALF Service Dependency Narrowing

**Date:** 2026-08-02
**Status:** PASS
**Baseline commit:** `80be7f3` (v0.9.5-F4 verification); F2 `7927ca7`,
F3 `a24312a`/`256b172`, and F4 `bb0c348`/`80be7f3` are ancestors
**Implementation commit:** `refactor(v0.9.5-f5a): narrow calf service dependencies` (`8d16cd5`)
**Verification commit:** `test(v0.9.5-f5a): verify calf service contracts`
**Specification:** `docs/development/V0.9.5_F5A_SPEC.md`

## Scope (exactly one Service narrowed)

`CalfService` runtime dependency changed from one broad, untyped
`repository` parameter to four explicit consumer-owned structural Ports:

- `CalfDataPort` — `list_analysis_units`, `list_error_annotations`,
  `save_error_annotations` (`SQLiteCalfRepository`);
- `CalfSubmissionReadPort` — `get_submission_bundle`,
  `list_student_submissions` (`SQLiteSubmissionRepository`);
- `CalfAnalysisReadPort` — `get_latest_analysis_run`
  (`SQLiteAnalysisRepository`);
- `CalfStudentReadPort` — `get_student` (`SQLiteLearnerRepository`).

The four Ports are `typing.Protocol` classes owned by
`app/services/calf.py` with `@runtime_checkable`; no inheritance from
central repository Protocols, no concrete SQLite imports, no `Database`
import, no unused method, and no `hasattr` capability discovery remain in
the Service module. Public `CalfService` methods (`submission_report`,
`trajectories`, `import_error_annotations`) and their behaviors are
unchanged.

## Constructor and call mapping

Before:

```python
def __init__(self, repository) -> None:
    self.repository = repository
```

After:

```python
def __init__(
    self,
    calf_repository: CalfDataPort,
    submission_reader: CalfSubmissionReadPort,
    analysis_reader: CalfAnalysisReadPort,
    student_reader: CalfStudentReadPort,
) -> None:
```

Seven method-to-owner mappings (exact call order preserved):

```text
get_submission_bundle, list_student_submissions -> CalfSubmissionReadPort
get_latest_analysis_run                        -> CalfAnalysisReadPort
get_student                                    -> CalfStudentReadPort
list_analysis_units, list_error_annotations,
save_error_annotations                         -> CalfDataPort
```

No eighth persistence method is called. `save_error_annotations` remains
one repository-owned call to `SQLiteCalfRepository.save_error_annotations`;
the Essay-existence guard stays inside that repository method; no shared
cross-repository transaction exists.

## Active construction sites (Phase 0 inventory)

1. `app/api/main.py` `_run_startup` (line ~186):
   `CalfService(calf_repository=repository._calf_repository,
   submission_reader=repository._submission_repository,
   analysis_reader=repository._analysis_repository,
   student_reader=repository._learner_repository)`.
2. `app/api/main.py` `_build_full_app` (line ~385): same four explicit
   keyword arguments from the same facade object.
3. `scripts/verify_live_deepseek_v08.py` (line 135): the one operational
   caller discovered in Phase 0 (live DeepSeek verification, requires an
   API key; not run by default). Its `local_repo` is an existing `Database`
   facade; the constructor-only update passes the four facade-owned
   repository instances of that same graph.

No test constructs `CalfService` directly. No other active caller exists.

## Contract evidence

- Exact four Port method sets and `inspect.signature` parity with
  `SQLiteCalfRepository`, `SQLiteSubmissionRepository`,
  `SQLiteAnalysisRepository`, and `SQLiteLearnerRepository` at HEAD
  (new focused tests).
- `SQLiteCalfRepository` satisfies `CalfDataPort`;
  `SQLiteSubmissionRepository` satisfies `CalfSubmissionReadPort`;
  `SQLiteAnalysisRepository` satisfies `CalfAnalysisReadPort`;
  `SQLiteLearnerRepository` satisfies `CalfStudentReadPort`; the `Database`
  facade remains structurally compatible for legacy verification only.
- `app/services/calf.py` contains no `app.database` import, no `SQLite`
  import, no `self.repository` field, and no `hasattr(`; constructor
  annotations are exactly the four Ports (AST-verified by tests).
- No repository implementation, facade method, SQL, migration, schema,
  API route/schema, router dependency, UI, or locale file changed (full
  `git diff` reviewed).

## Composition

Both application-construction paths (`_run_startup`, `_build_full_app`)
construct `CalfService` with the existing facade-owned `_calf_repository`,
`_submission_repository`, `_analysis_repository`, and `_learner_repository`
instances, using explicit keyword arguments. Focused tests assert object
identity for all four dependencies and that all four share the same
`_connection_manager`; no second `Database`, connection manager, or
repository graph is created. Private facade access exists only in the
composition root and the one recorded operational-script site. The CALF
router continues to consume `app.state.calf` via `get_calf` and constructs
nothing itself.

## Verification layers

### Layer 1 — Static

- `py_compile` of all changed/new modules: PASS.
- Imports of the four Ports, `CalfService`, `create_app`/`_build_full_app`/
  `_run_startup`, and the CALF router: PASS (no circular imports).
- Task-scoped `git diff --check` over the F5A changed files: PASS.
- UTF-8/replacement-character scan of all changed/new files: 0 defects.

### Layer 2 — Dependency contracts

- Four Ports, exact method sets, source signature parity: PASS (new
  focused tests).
- No `Database`/concrete-SQLite imports, no broad repository field, no
  compatibility fallback, no dynamic capability discovery in the Service
  module: PASS.
- No unrelated Service constructor changed; no repository implementation,
  facade method, SQL, transaction, schema, API, UI, or locale file changed
  (full `git diff` reviewed).

### Layer 3 — Focused behavior (fresh isolated database)

Command (F5A isolation runner with exact allow-list):

```
pytest -q tests/test_v095f5a_calf_service_narrowing.py
       tests/test_calf_v08.py
       tests/test_v095b_router_contract.py
       tests/test_v095f4_reanalysis_journey_narrowing.py
       tests/test_v095e_repository_modularization.py
```

Result: **63 passed, 2 warnings** (18 new F5A tests + CALF report/API/
annotation, router-contract, app-construction, and v0.9.5-E facade-parity
coverage). This covers submission-bundle lookup, latest Analysis Run
lookup, Analysis Unit listing, Error Annotation listing, Student lookup,
Student Submission listing, CALF report and trajectory behavior,
annotation import success, annotation validation failure, the
Essay-existence guard (repository-exception propagation), ordering and
empty states, relevant CALF API endpoints, and both app-construction
paths.

### Layer 4 — Existing architecture contracts

Command:

```
pytest -q tests/test_v095f2_service_narrowing.py
       tests/test_v095f3_learner_read_model_narrowing.py
       tests/test_v095f4_reanalysis_journey_narrowing.py
       tests/test_v095e_repository_modularization.py
       tests/test_v095d_api_contract.py
       tests/contracts/api_surface_contract.py
       tests/test_v095d_parity.py
       tests/test_design_tokens_v094a.py
       tests/test_v095c_feature_extraction.py
       tests/test_v095b_router_contract.py
```

Result: **123 passed, 2 warnings** — F2/F3/F4 dependency contracts pass;
v0.9.5-E repository facade parity passes (86 methods, 33 table owners,
zero drift) under the exact F5A `SERVICE_API_DIFF_ALLOWLIST`; API contract
77 path+method pairs; frontend client 52 public methods; locale parity
520/520; migration 12; active configuration `config-v0.9.0`.

### Full non-live core regression (fresh isolated database)

Command: `pytest -q --ignore=tests/live`

Result: **526 passed, 8 skipped, 2 warnings** in 241.84s (508 baseline +
18 new F5A tests; the Playwright/live-stack suite was not run per scope).

### Exact launcher verification (fresh isolated database, dotenv disabled)

Command: `cmd /c "run.bat --verify"`

Result: PASS (exit 0):

- Migration **12**; **33** tables; active configuration **config-v0.9.0**;
  prompt `feedback-prompt-v0.7.1`; provider local.
- FastAPI `/api/v1/system/health` **200**; `/docs` **200**; Streamlit **200**.
- All application processes stopped; ports 8000/8501 free afterward.

## Database safety

Every write-capable run used a fresh unique temporary database with
`PYTHON_DOTENV_DISABLED=1`, `DATABASE_URL` absent, `DATABASE_PATH` inside
the temporary directory, `LLM_PROVIDER=local`, resolved-path assertions,
and cleanup. The development database was checked by SHA-256, size, and
mtime before and after every run and did not change.

- Baseline focused run DB: `C:\Users\16073\AppData\Local\Temp\v095f4-e2l379p3\run.db`
- Layer 3 focused run DB: `C:\Users\16073\AppData\Local\Temp\v095f5a-0twyacnb\run.db`
- Layer 4 contract run DB: `C:\Users\16073\AppData\Local\Temp\v095f5a-iynjcm50\run.db`
- Full core run DB: `C:\Users\16073\AppData\Local\Temp\v095f5a-bispmcc0\run.db`
- Launcher run DB:
  `C:\Users\16073\AppData\Local\Temp\v095f5a-runbat-2111f5f6\runbat-verify.db`
- Development DB: `data/writing_feedback.db` — SHA-256
  `340E0F3739FEFFD3DEF87BB6E711CB6F90A8478E7E18D833C715EDCFAB03AFF4`, size
  8,298,496 bytes, mtime `2026-08-02T11:02:25.887+08:00` before and after
  all runs (unchanged; never opened).
- All temporary databases/directories removed; no listeners remain.

## Impact review and limitations

The complete F5A diff (production, operational-script constructor site,
tests, runner, and documentation) was reviewed; only the approved files
changed. GitNexus was refreshed to HEAD `80be7f3` for Phase 0 and used for
the one bounded dependency query on `CalfService`; the post-implementation
scoped change-impact review used the CRG review context over the complete
F5A diff. The Code Review Graph CLI remains unavailable in this
environment (uv trampoline defect, one attempt recorded, not repaired),
and its MCP index is stale (built at `7927ca7`), so its broad impact
estimate (500 nodes / 136 files) is stale-index noise; static source,
`git diff` at HEAD, and the passing focused/contract layers remain
authoritative.

## Deferred (unchanged by F5A)

`ResearchDataService` narrowing (write-orchestration combination),
Submission/Revision/Admin Reanalysis/Practice/Journey/Reanalysis/Learner/
Dashboard/Configuration/FeedbackPipeline dependency boundaries,
write-orchestration narrowing, facade contraction, Protocol consolidation,
transaction redesign, schema cleanup, `export_jobs` writer, WTR collision
fix, and legacy pipeline removal. v0.9.5-F5B must not begin without a
separate authorization.

## Decision

v0.9.5-F5A is complete and verified. F2, F3, and F4 dependency boundaries
remain unchanged; no repository, SQL, transaction, schema, API, UI, or
domain behavior changed; the development database was never opened or
modified; no F5B work was started.
