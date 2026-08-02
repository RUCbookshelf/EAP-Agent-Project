# v0.9.5-F6D Verification - Practice Write-Boundary Narrowing

**Date:** 2026-08-02
**Status:** PASS
**Baseline commit:** `3e89ba7` (v0.9.5-F6C verification); F2-F6C commits are
ancestors
**Implementation commit:** `refactor(v0.9.5-f6d): narrow practice write boundaries`
**Verification commit:** `test(v0.9.5-f6d): verify practice boundary contracts`
**Specification:** `docs/development/V0.9.5_F6D_SPEC.md`
**Authorization:** Owner-authorized F6D stage (pasted instruction file).

## Scope (Practice write-boundary narrowing only)

Removed every active Practice Router dependency on the broad `Database`
facade and replaced it with three exact consumer-owned Ports
(`PracticeSubmissionReadPort`, `PracticeReadPort`, `PracticeWritePort`);
removed the dormant Repository dependency from `PracticeService` (source
confirmed it was persistence-free); preserved Router ownership of the
Attempt-first/Evaluation-best-effort orchestration and every endpoint,
schema, status code, domain calculation, identifier, timestamp, ordering
rule, and error behavior. No second Database, connection manager,
Repository, adapter, proxy, or persistence graph was created.

## Source-authoritative endpoint inventory (8)

```text
GET  /api/v1/students/{student_id}/practice-targets
POST /api/v1/practice-targets
POST /api/v1/practice-targets/{practice_target_id}/exercises
GET  /api/v1/practice-targets/{practice_target_id}/exercises
POST /api/v1/exercises/{exercise_id}/attempts
GET  /api/v1/exercises/{exercise_id}/attempts
GET  /api/v1/students/{student_id}/engagement-traces
GET  /api/v1/students/{student_id}/transfer-evidence
```

All paths, methods, function names, request/response shapes, status codes,
learner guards, and error translation are unchanged (frozen API inventory
remains 77 path+method pairs; frontend client 52 methods; locale 520/520).

## Source-authoritative direct Router Repository method set (12)

```text
get_submission_bundle                    -> PracticeSubmissionReadPort (1)
list_practice_targets, get_practice_target, list_exercise_instances,
get_exercise_instance, list_exercise_attempts,
list_feedback_engagement_traces,
list_transfer_evidence_candidates        -> PracticeReadPort (7)
save_practice_target, save_exercise_instance, save_exercise_attempt,
save_practice_evaluation                 -> PracticeWritePort (4)
```

No third Repository owner; no dynamic method names; no method appears in both
Practice Ports; no Journey-only/Research-only/test-only or deferred writer
capability is exposed (Feedback Engagement Trace, Within-task Response,
Transfer Evidence, and Practice-State Snapshot writers remain script/test-only
as at baseline).

## Three new consumer-owned Ports

Defined in `app/practice/ports.py` (`typing.Protocol` +
`@runtime_checkable`), signatures copied from current HEAD source and
inspect-verified against `SQLiteSubmissionRepository` /
`SQLitePracticeRepository`. The same facade-owned `SQLitePracticeRepository`
instance structurally satisfies both `PracticeReadPort` and
`PracticeWritePort` (identity asserted). No concrete SQLite or `Database`
import exists in the Port module.

## PracticeService purity

Constructor changed from `PracticeService(repository)` (storing an unused
`self.repo`) to `PracticeService()`; the Repository field is removed; all
eight public domain methods, outputs, and exceptions are unchanged. Static
(no `self.repo`/`self.repository`/Database/SQLite imports; zero constructor
arguments) and runtime (no repo field) purity proofs pass.

## Construction sites updated (constructor-only)

`app/api/routers/practice.py` (3 sites, now via `Depends(get_practice_service)`),
`scripts/demo_journey.py`, `tests/test_journey_v093c.py` (2 sites),
`tests/test_practice_v09.py` (dummy `_FakeRepo` removed with the constructor
change), `tests/live/test_v09_live_validation.py`,
`verification/v0.9.5-e/capture_prechange_fresh_database.py`, and the dated
historical artifact `verification/v0.9.4-b/.../cross_page_flow.py`. No caller
relied on `PracticeService.repository`/`.repo`.

## Application composition and dependencies

Both application-construction paths store:

```text
practice_submission_reader = repository._submission_repository
practice_reader           = repository._practice_repository
practice_writer           = repository._practice_repository
practice_student_reader   = repository._learner_repository
practice_service          = PracticeService()
```

Identity tests prove `practice_reader is practice_writer` and both are the
exact facade-owned `_practice_repository`; the Submission reader is the exact
facade-owned `_submission_repository`; the student reader is the facade-owned
`_learner_repository`; all share `repository._connection_manager`; one graph
(Revision repository readers verified); no request-local construction.

`app/api/deps.py` gains `get_practice_submission_reader`,
`get_practice_reader`, `get_practice_writer`, `get_practice_student_reader`,
and `get_practice_service` - each returns an already-composed
`request.app.state` object; none calls `get_repository`, accesses private
facade attributes, constructs a Database/Repository, opens a connection, or
performs business logic.

`require_student` boundary: the three learner-guarded GET endpoints keep
calling the unchanged `require_student(student_reader, student_id)` with the
facade-owned Learner reader (the F4 journey pattern). The learner-read
dependency remains a documented v0.9.5-G API-dependency candidate; no broad
facade object reaches the Router.

## Router dependency replacement

`app/api/routers/practice.py` contains no `Depends(get_repository)`, no broad
Repository parameter, no `request.app.state` access, and no private facade
access. Submission reads route only through `PracticeSubmissionReadPort`;
Practice reads only through `PracticeReadPort`; Practice writes only through
`PracticeWritePort`. All eight endpoint function names are preserved (AST
proof).

## Exact Attempt/Evaluation sequence (unchanged)

`POST /api/v1/exercises/{exercise_id}/attempts`:

```text
get_exercise_instance (404 if missing)
-> list_exercise_attempts (next_num = count + 1)
-> PracticeService.submit_attempt (pure; invalid_input returns without writes)
-> save_exercise_attempt (WRITE 1; independent commit; exactly once)
-> try:
     get_practice_target
     get_submission_bundle (source text; missing bundle -> "")
     PracticeService.evaluate_attempt (pure)
     save_practice_evaluation (WRITE 2; independent commit)
   except Exception: attempt["evaluation"] = None
```

`create_practice_target` and `create_exercise` each perform exactly one
Practice write (skipped on `practice_not_available`), one independent commit.
Read endpoints are zero-write (recorder-proven across all eight Practice
save methods).

## Failure and partial-commit results (isolated SQLite evidence)

- Failure before Attempt persistence (invalid input): zero Attempt rows, zero
  Evaluation rows, baseline `invalid_input` response.
- Attempt persistence failure: zero committed Attempts, zero Evaluations,
  exception propagates (no later calls).
- Evaluation generation failure: Attempt committed and queryable (1 row),
  zero Evaluation rows, response `evaluation: None`, no compensation.
- Evaluation persistence failure: Attempt committed and queryable, zero
  Evaluation rows, response `evaluation: None`, no Attempt deletion/rollback.
- Full success: exactly one Attempt write then exactly one Evaluation write;
  response unchanged.
- Missing exercise instance / unknown student: 404 before any write.

No compensation, retry, background reprocessing, outbox, or shared
transaction was introduced; no new Practice writer workflow or endpoint was
added; the WTR identifier collision remains deferred.

## Verification layers

### Layer 1 - Static

- `py_compile` of all changed/new modules: PASS.
- Imports of all three Ports, `PracticeService`, the Practice Router, API
  dependencies, and both application paths: PASS (no circular imports).
- Task-scoped `git diff --check`: PASS (user-owned `AGENTS.md` excluded).
  UTF-8/replacement scan: 0 defects.

### Layer 2 - Dependency contracts

- Exact Port method sets and signature parity: PASS (inspect).
- No `Depends(get_repository)` or broad Repository parameter in the Practice
  Router; no private facade access in Router or dependency functions; no
  persistence field in `PracticeService`; no Database/SQLite import in the
  Service or Ports; no fallback, adapter, proxy; no Repository
  implementation, SQL, or migration file changed (git path diff empty).

### Layer 3 - Runtime identity

Both application paths prove the exact facade-owned identities above,
`practice_reader is practice_writer`, one shared connection manager, one
`SQLitePracticeRepository`/`SQLiteSubmissionRepository` instance per graph,
no second graph, and a persistence-free `PracticeService`.

### Layer 4 - API and read behavior

Focused tests cover all eight Practice routes; frozen API contract
(`test_v095d_api_contract.py` + `tests/contracts/api_surface_contract.py`)
passes; learner validation (404), empty/missing resources, and read-endpoint
zero-write behavior pass.

### Layer 5 - Write behavior

Attempt/Evaluation success writes exactly one Attempt and one Evaluation;
Practice Target and Exercise Instance writes remain one-call endpoints;
identifiers (`PE...` evaluation ids) and response shapes unchanged.

### Layer 6 - Partial commits

See the failure matrix above; all assertions use real isolated SQLite rows.

### Layer 7 - Accumulated architecture contracts

Command:

```
pytest -q tests/test_v095f2_service_narrowing.py
       tests/test_v095f3_learner_read_model_narrowing.py
       tests/test_v095f4_reanalysis_journey_narrowing.py
       tests/test_v095f5a_calf_service_narrowing.py
       tests/test_v095f5b_research_service_narrowing.py
       tests/test_v095f6a0_revision_capability_completion.py
       tests/test_v095f6a_revision_runtime_narrowing.py
       tests/test_v095f6b_admin_reanalysis_narrowing.py
       tests/test_v095f6c_submission_service_narrowing.py
       tests/test_v095f6d_practice_boundary_narrowing.py
       tests/test_v095e_repository_modularization.py
       tests/test_v095d_api_contract.py
       tests/contracts/api_surface_contract.py
       tests/test_v095d_parity.py
       tests/test_design_tokens_v094a.py
       tests/test_v095c_feature_extraction.py
       tests/test_v095b_router_contract.py
```

Result: **253 passed, 2 warnings** (233 F2-F6C accumulated + 20 new F6D
tests) - F2/F3/F4/F5A/F5B/F6A0/F6A/F6B/F6C dependency and transaction
contracts pass; v0.9.5-E repository facade parity passes (86 methods, 33
table owners, zero drift) under the exact F6D `SERVICE_API_DIFF_ALLOWLIST`
(accumulated F2-F6D approved diff, no wildcards); API contract 77 path+method
pairs; frontend client 52 public methods; locale parity 520/520; migration
12; active configuration `config-v0.9.0`.

### Focused F6D behavior suite (fresh isolated database)

Command (F6D isolation runner):

```
pytest -q tests/test_v095f6d_practice_boundary_narrowing.py
       tests/test_practice_v09.py
       tests/test_journey_v093c.py
       tests/test_v095b_router_contract.py
       tests/test_v095d_api_contract.py
       tests/contracts/api_surface_contract.py
       tests/test_v095f4_reanalysis_journey_narrowing.py
       tests/test_v095f2_service_narrowing.py
       tests/test_v095f3_learner_read_model_narrowing.py
       tests/test_v095f6c_submission_service_narrowing.py
       tests/test_v095f6a_revision_runtime_narrowing.py
       tests/test_v095e_repository_modularization.py
       tests/test_v095d_parity.py
```

Result: **187 passed, 2 warnings** (167 baseline + 20 new F6D tests).

### Full non-live core regression (fresh isolated database)

Command: `pytest -q --ignore=tests/live`

Result: **638 passed, 8 skipped, 2 warnings** in 303.85s (618 baseline from
the completed F6C verification + 20 new F6D tests; the Playwright/live-stack
suite was not run per scope).

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
the temporary directory, `LLM_PROVIDER=local`, resolved-path assertions, and
cleanup. The development database was checked by SHA-256, size, and mtime
before and after every run and did not change; it was never opened. All
temporary databases and directories were removed; no listeners remain; no
user export was created or modified.

- Focused run DB: `C:\Users\16073\AppData\Local\Temp\v095f6d-kit10jh5\run.db`
- Contract run DB: `C:\Users\16073\AppData\Local\Temp\v095f6d-554x7pgc\run.db`
- Full core run DB: `C:\Users\16073\AppData\Local\Temp\v095f6d-ldnqmj5g\run.db`
- Launcher run DB:
  `C:\Users\16073\AppData\Local\Temp\v095f6d-runbat-3f24600b\runbat-verify.db`
- Development DB: `data/writing_feedback.db` - SHA-256
  `340E0F3739FEFFD3DEF87BB6E711CB6F90A8478E7E18D833C715EDCFAB03AFF4`, size
  8,298,496 bytes, mtime `2026-08-02T11:02:25.887+08:00` before and after
  all runs (unchanged; never opened).

## Impact review and limitations

The complete F6D diff (Ports module, PracticeService purity, app-state
composition, five dependency accessors, Router narrowing, and all
constructor-only caller updates) was reviewed; only the approved files
changed. GitNexus impact analysis on `PracticeService`: LOW risk, exact, 6
impacted nodes, 4 direct importers, 0 affected processes. The CRG CLI defect
remains (uv trampoline, documented in prior stages; not repaired). The
`require_student` learner-read dependency is preserved and documented as a
v0.9.5-G API-dependency candidate. User-owned paths (`AGENTS.md`,
`RUN_VERIFICATION_V0.7.md`, `RUN_VERIFICATION_V0.8.2.md`, `.claude/`,
`ARCHITECTURE_COUPLING_AUDIT_V0.9.5_A.md`, `CLAUDE.md`,
`data/demo_journey_manifest.json`, `data/writing_feedback.db`) were preserved
untouched.

## Decision

v0.9.5-F6D is complete and verified. The Practice Router depends on exactly
the three consumer-owned Ports plus the preserved `require_student` guard and
the pure `PracticeService`; no broad `Database` dependency remains; the
Attempt-first/Evaluation-best-effort semantics, all endpoints, schemas, status
codes, and error behavior are unchanged; `PracticeService` is persistence-free;
all dependencies use one facade-owned Repository graph; the development
database was never opened or modified; v0.9.5-G and later stages were not
started.
