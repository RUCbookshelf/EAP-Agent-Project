# v0.9.5-F5B Verification — ResearchDataService Dependency Narrowing

**Date:** 2026-08-02
**Status:** PASS
**Baseline commit:** `8abd6c2` (v0.9.5-F5A verification); F2 `7927ca7`,
F3 `a24312a`/`256b172`, F4 `bb0c348`/`80be7f3`, and F5A `8d16cd5`/`8abd6c2`
are ancestors
**Implementation commit:** `refactor(v0.9.5-f5b): narrow research service dependencies` (`d0a2cda`)
**Verification commit:** `test(v0.9.5-f5b): verify research service contracts`
**Specification:** `docs/development/V0.9.5_F5B_SPEC.md`

## Scope (exactly one Service narrowed)

`ResearchDataService` runtime dependency changed from one broad, untyped
`repository` parameter to three explicit consumer-owned structural Ports:

- `ResearchSubmissionReadPort` — `list_all_submissions`,
  `list_student_submissions`, `get_submission_bundle`
  (`SQLiteSubmissionRepository`);
- `ResearchReviewPort` — `save_human_review`, `list_human_reviews`,
  `apply_pii_review` (`SQLiteResearchRepository`);
- `ResearchExportReadPort` — `list_export_jobs`, `get_export_job`
  (`SQLiteResearchRepository`, the same instance as the Review Port).

The three Ports are `typing.Protocol` classes owned by
`app/research/service.py` with `@runtime_checkable`; no inheritance from
central repository Protocols, no concrete SQLite imports, no `Database`
import, no `save_export_job`, and no unused method. All public
`ResearchDataService` methods and behaviors are unchanged.

## Constructor and call mapping

Before:

```python
def __init__(self, repository):
    self.repo = repository
```

After:

```python
def __init__(
    self,
    submission_reader: ResearchSubmissionReadPort,
    review_repository: ResearchReviewPort,
    export_reader: ResearchExportReadPort,
):
```

Eight method-to-owner mappings (call order and call counts preserved):

```text
list_all_submissions, list_student_submissions, get_submission_bundle
    -> ResearchSubmissionReadPort

save_human_review, list_human_reviews, apply_pii_review
    -> ResearchReviewPort

list_export_jobs, get_export_job
    -> ResearchExportReadPort
```

No ninth persistence method is called. `ResearchDataService` does not call
`save_export_job` (enforced by source scan and stub tests); the Research
router remains the only active owner of that call.

## Removed `hasattr` capability checks (six)

1. `list_all_submissions` guard in `_collect`
2. `save_human_review` guard in `create_human_review`
3. `list_human_reviews` guard in `get_human_reviews`
4. `apply_pii_review` guard in `apply_pii_review`
5. `list_export_jobs` guard in `export_history`
6. `get_export_job` guard in `export_status`

The approved baseline production facade always supplies all five Research
methods and all three Submission reads, so the capability-absent branches
were unused in active production construction; no hidden fallback is
preserved.

## Active construction sites (Phase 0 inventory)

1. `app/api/main.py` `_run_startup`: `ResearchDataService(
   submission_reader=repository._submission_repository,
   review_repository=repository._research_repository,
   export_reader=repository._research_repository)`.
2. `app/api/main.py` `_build_full_app`: same explicit keyword arguments
   from the same facade object.
3. `tests/test_research_v082.py` five sites (cases A, B, C, H, L): all
   updated to pass `db._submission_repository` and
   `db._research_repository` (same instance for both Research Ports).
4. `verification/v0.9.5-e/capture_prechange_fresh_database.py` line ~138:
   one constructor-only update using `database._submission_repository` and
   `database._research_repository`.

`tests/test_request_reliability_v093b.py` imports the Service but does not
construct it. No old one-argument broad constructor remains in active code.

## Contract evidence

- Exact three Port method sets and `inspect.signature` parity with
  `SQLiteSubmissionRepository` and `SQLiteResearchRepository` at HEAD
  (including the annotation-free `list_all_submissions`).
- `SQLiteSubmissionRepository` satisfies `ResearchSubmissionReadPort`;
  `SQLiteResearchRepository` satisfies both `ResearchReviewPort` and
  `ResearchExportReadPort`; the same repository instance satisfies both
  Research-owned Ports; the `Database` facade remains structurally
  compatible for legacy verification only.
- `app/research/service.py` contains no `app.database` import, no `SQLite`
  import, no `self.repo`/`self.repository` field, no `hasattr(`, and no
  `save_export_job`; constructor annotations are exactly the three Ports
  (AST-verified by tests).
- No repository implementation, facade method, SQL, migration, schema, API
  route/schema, Router behavior, UI, or locale file changed (full
  `git diff` reviewed).

## Composition

Both application-construction paths wire the existing facade-owned
`_submission_repository` and the same `_research_repository` instance to
both Research-owned Ports. Focused tests assert object identity
(`review_repository is export_reader`), that all dependencies share the
same `_connection_manager`, and that no second `Database`, connection
manager, or repository graph is created. Private facade access exists only
in the composition root and the recorded verification-helper site. The
Research router is unchanged: it consumes `app.state.research` via
`get_research`, keeps `Depends(get_repository)` for the best-effort
`save_export_job` write, and constructs nothing itself.

## Router-owned best-effort persistence boundary

`ResearchDataService.run_export` generates and returns the export result
only. The Router (`POST /api/v1/research/export/run`) still attempts
`repository.save_export_job(...)` after a successful export under the
existing `try/except: pass` best-effort path. Focused tests prove:

- the Service itself never calls `save_export_job` (stub without the method
  is sufficient);
- a successful audit-row write preserves the existing 200 completed
  response and one `export_jobs` row;
- an audit-row write failure keeps the 200 completed response, writes zero
  rows, and leaves the completed export files on disk (manifest lookup
  stays unknown/404, unchanged behavior);
- export generation and Export Job persistence are not atomic; no shared
  transaction or rollback of the completed export is introduced.

## Verification layers

### Layer 1 — Static

- `py_compile` of all changed/new modules: PASS.
- Imports of the three Ports, `ResearchDataService`, `create_app`/
  `_build_full_app`/`_run_startup`, and the Research router: PASS (no
  circular imports).
- Task-scoped `git diff --check` over the F5B changed files: PASS.
- UTF-8/replacement-character scan of all changed/new files: 0 defects.

### Layer 2 — Dependency contracts

- Three Ports, exact method sets, source signature parity: PASS (new
  focused tests).
- No `Database`/concrete-SQLite imports, no broad repository field, no
  `hasattr`, no compatibility fallback, no `save_export_job` in the Service
  or in the Ports: PASS.
- No unrelated Service constructor changed; no repository implementation,
  facade method, SQL, transaction, schema, API, UI, or locale file changed
  (full `git diff` reviewed).

### Layer 3 — Focused behavior (fresh isolated database)

Command (F5B isolation runner with exact allow-list):

```
pytest -q tests/test_v095f5b_research_service_narrowing.py
       tests/test_research_v082.py
       tests/test_v095e_research_export_persistence.py
       tests/test_request_reliability_v093b.py
       tests/test_v095b_router_contract.py
       tests/test_v095f5a_calf_service_narrowing.py
       tests/test_v095e_repository_modularization.py
```

Result: **97 passed, 2 warnings** (20 new F5B tests + Research listing/
PII/human-review/export behavior, Export Job reads, Router best-effort
persistence, app-construction paths, and v0.9.5-E facade parity). This
covers all-submission and student-scoped listing, Bundle retrieval,
data-quality, filtering, export preview/generation and contents/ordering,
privacy modes, Human Review save/list, PII Review application, Export Job
listing/get, empty states, missing records, relevant Research API
endpoints, and both app-construction paths.

One run of this layer hit a pre-existing lifecycle race in
`test_v095b_router_contract.py::test_business_route_gated_until_ready_while_health_available`
(a production-mode `TestClient` in an earlier test spawns the background
startup thread, which can flip the global lifecycle state mid-test). The
test passes in isolation (1 passed, 0.47s) and passes in the rerun of the
full focused set; the race is unrelated to F5B (the F5B diff touches only
ResearchDataService composition) and is recorded as a pre-existing
environmental flake, not repaired under this scope.

### Layer 4 — Router persistence boundary

Covered by the F5B Router-boundary tests in Layer 3 (see above): the
Service never writes Export Job rows; the Router still attempts the
best-effort write after a successful export; success and failure paths
preserve the existing responses and file behavior; no endpoint contract
changes.

### Layer 5 — Existing architecture contracts

Command:

```
pytest -q tests/test_v095f2_service_narrowing.py
       tests/test_v095f3_learner_read_model_narrowing.py
       tests/test_v095f4_reanalysis_journey_narrowing.py
       tests/test_v095f5a_calf_service_narrowing.py
       tests/test_v095e_repository_modularization.py
       tests/test_v095d_api_contract.py
       tests/contracts/api_surface_contract.py
       tests/test_v095d_parity.py
       tests/test_design_tokens_v094a.py
       tests/test_v095c_feature_extraction.py
       tests/test_v095b_router_contract.py
```

Result: **141 passed, 2 warnings** — F2/F3/F4/F5A dependency contracts
pass; v0.9.5-E repository facade parity passes (86 methods, 33 table
owners, zero drift) under the exact F5B `SERVICE_API_DIFF_ALLOWLIST`; API
contract 77 path+method pairs; frontend client 52 public methods; locale
parity 520/520; migration 12; active configuration `config-v0.9.0`.

### Full non-live core regression (fresh isolated database)

Command: `pytest -q --ignore=tests/live`

Result: **546 passed, 8 skipped, 2 warnings** in 244.41s (526 baseline +
20 new F5B tests; the Playwright/live-stack suite was not run per scope).

### Exact launcher verification (fresh isolated database, dotenv disabled)

Command: `cmd /c "run.bat --verify"`

Result: PASS (exit 0):

- Migration **12**; **33** tables; active configuration **config-v0.9.0**;
  prompt **feedback-prompt-v0.7.1**; provider local.
- FastAPI `/api/v1/system/health` **200**; `/docs` **200**; Streamlit **200**.
- All application processes stopped; ports 8000/8501 free afterward.

## Database and export-file safety

Every write-capable run used a fresh unique temporary database with
`PYTHON_DOTENV_DISABLED=1`, `DATABASE_URL` absent, `DATABASE_PATH` inside
the temporary directory, `LLM_PROVIDER=local`, resolved-path assertions,
and cleanup. The development database was checked by SHA-256, size, and
mtime before and after every run and did not change; it was never opened.
The `research_exports/` directory was snapshotted before and after every
write-capable run; every newly created export directory (test artifact)
was removed, and all 235 pre-existing user export directories remained
untouched (verified by directory-name diff after each run).

- Baseline focused run DB: `C:\Users\16073\AppData\Local\Temp\v095f5a-g_816q8m\run.db`
- Layer 3 focused run DB: `C:\Users\16073\AppData\Local\Temp\v095f5b-a7hv9a0u\run.db`
- Layer 5 contract run DB: `C:\Users\16073\AppData\Local\Temp\v095f5b-zvyujdz3\run.db`
- Full core run DB: `C:\Users\16073\AppData\Local\Temp\v095f5b-fg_o7vcn\run.db`
- Launcher run DB:
  `C:\Users\16073\AppData\Local\Temp\v095f5b-runbat-9f781b86\runbat-verify.db`
- F5B tests that exercise export generation wrote only into
  `monkeypatch`-redirected temporary export directories or into
  `research_exports/` test dirs that were removed afterward.
- Development DB: `data/writing_feedback.db` — SHA-256
  `340E0F3739FEFFD3DEF87BB6E711CB6F90A8478E7E18D833C715EDCFAB03AFF4`, size
  8,298,496 bytes, mtime `2026-08-02T11:02:25.887+08:00` before and after
  all runs (unchanged; never opened).
- All temporary databases, export files, runners, and directories removed;
  no listeners remain.

## Impact review and limitations

The complete F5B diff (production, test constructor updates, verification
helper, tests, runner, and documentation) was reviewed; only the approved
files changed. GitNexus was refreshed to HEAD `8abd6c2` for Phase 0 and
used for the one bounded dependency query on `ResearchDataService`; the
post-implementation scoped change-impact review used the CRG review context
over the complete F5B diff. The Code Review Graph CLI remains unavailable
in this environment (uv trampoline defect, one attempt recorded, not
repaired), and its MCP index is stale (built at `7927ca7`), so its broad
impact estimate (500 nodes / 118 files) is stale-index noise; static
source, `git diff` at HEAD, and the passing focused/contract layers remain
authoritative.

## Deferred (unchanged by F5B)

Write-orchestration narrowing, facade contraction, Protocol consolidation,
transaction redesign, schema cleanup, Migration 13, Research router
redesign, moving Router persistence into the Service, new Export Job
workflows, changing Export Job failure semantics, missing writer
endpoints, `save_export_job` changes, WTR collision fix, FeedbackPipeline
removal, and any later stage. No next stage may begin without a separate
authorization.

## Decision

v0.9.5-F5B is complete and verified. F2-F5A dependency boundaries remain
unchanged; no repository, SQL, transaction, schema, API, Router, UI, or
domain behavior changed; the development database was never opened or
modified; all 235 pre-existing user exports remain untouched; no later
stage was started.
