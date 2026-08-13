# Findings — Worker C: contracts / composition / evidence separation audit

- task_id: PDW3-WU1-DECOMP-RECOVERY__C-CONTRACTS-COMPOSITION-EVIDENCE
- task_class: REVIEW (READ-ONLY; no product/Program-Control/git writes)
- worktree: `A:\EAP Agent Project\worktrees\shared-core` @ `dept/shared-core` `7a9e4b470c41c0453a3795233f1bdd5c483d80ae`
- date: 2026-08-11

## 1. Scope

Audit of the preserved partial Wave-3 WU1 implementation for contract and
composition correctness and evidence-separation semantics, per the task
packet: API/composition wiring, LearningItem/PracticeActivity/ReviewEvent
contracts, three rating channels, versioned provenance, fail-closed inputs,
semantic-leak scan, and Wave-2 compatibility. Read-only: no repair, no writes
outside this worker directory.

## 2. Files inspected (path:line)

Composition root / wiring:
- `app/api/main.py:31,71-88` review router import + `_BUSINESS_ROUTERS` inclusion (exactly once)
- `app/api/main.py:187-190` `ReviewService(repository._review_repository, FSRSSchedulerAdapter(), learning_item_reader=repository._wave2_repository)`
- `app/api/main.py:225-226,248-250` state assignments (`review_service`, `review_repository`, `review_learning_item_reader`)
- `app/api/main.py:316-327` single builder `_build_services` shared by production (`_run_startup`) and test (`_build_full_app`) paths
- `app/database/repository.py:146-147` `_wave2_repository` / `_review_repository` wiring on the single `Database` facade
- `app/infrastructure/sqlite/repositories/__init__.py:7,20` `SQLiteReviewRepository` export
- `app/database/migrations.py:44,970-1080,1100,1128-1137` migration 15 additive tables + ledger-only rollback
- `app/version.py:44-46` migration-version single sourcing (`PLATFORM_DATABASE_MIGRATION_VERSION = 15`)
- `pyproject.toml:14` `fsrs==6.3.2` pin (installed: 6.3.2)

Review contracts / services:
- `app/review/models.py:32-42` `Rating` StrEnum matching py-fsrs ordinals
- `app/review/models.py:74-118` `PracticeActivity` (evidence_kind literal "practice", authentic_evidence_status, limitation statements)
- `app/review/models.py:121-171` scheduler state identity/snapshot/result
- `app/review/models.py:174-225` `ReviewEvent` (three separate rating channels, rating_rule_version, scheduler_implementation/version/parameters, state_before/after, scheduling_result)
- `app/review/protocols.py:24-62` `ReviewRepositoryProtocol` / `LearningItemReaderProtocol` / `SchedulerProtocol` (no sqlite in core)
- `app/review/rating_policy.py:14,17-39` `RATING_RULE_VERSION = "rating-rule-v1.0.0"`, conservative-minimum resolution
- `app/review/scheduler.py:48-85,96-151` real py-fsrs adapter, fuzzing off, explicit identity
- `app/review/service.py:43-51,97-113,132-217` fail-closed coercion, learning-item existence guard, atomic event+state write
- `app/review/__init__.py` package surface

API surface:
- `app/api/routers/review.py:22-40` thin router; `get_review_service` 503 when un-wired
- `app/api/routers/review.py:46-75,79-140` payload models (`extra="forbid"`), endpoints, ReviewError to 404/422 mapping
- `app/infrastructure/sqlite/repositories/review.py:62-71,76-125,147-232` persistence, `INSERT OR REPLACE`, FK reliance, row mappers

Wave-2 contract surfaces (unchanged in the diff, read for compatibility):
- `app/l2/wave2/models.py:348-384` `LearningItem` v1 (no-FSRS / no-practice notes, no scheduler columns)
- `app/infrastructure/sqlite/repositories/wave2.py:383,989-997` `SQLiteWave2Repository.get_learning_item`
- `app/api/routers/wave2_modules/personalized_api.py:165-179` wave2 learning-items endpoint
- `app/database/__init__.py:1,4` `LATEST_MIGRATION_VERSION` export

Tests inspected:
- `tests/review/test_review_composition.py`, `test_semantic_boundaries.py`, `test_wave2_regression.py` (required)
- `tests/review/test_models_and_boundaries.py`, `test_rating_policy.py`, `test_review_service.py`, `test_scheduler_determinism.py`, `test_review_repository.py`, `test_migration_15.py` (extended)
- `tests/test_composition_root.py` and diffs of `tests/test_analysis_runs_v04.py`, `tests/test_calf_v08.py`, `tests/test_diagnostic_calibration_v061.py`, `tests/test_learner_model_v07.py`, `tests/test_revision_v05.py` (mechanical 14 to `LATEST_MIGRATION_VERSION` updates only)

## 3. Tests / probes run (command, result, evidence path)

All commands used `.venv\Scripts\python.exe`, `PYTHONDONTWRITEBYTECODE=1`,
`-p no:cacheprovider`, `--basetemp <evidence>/...`.

1. Required suite (packet command):
   `python -m pytest -q tests/review/test_review_composition.py tests/review/test_semantic_boundaries.py tests/review/test_wave2_regression.py`
   -> **10 passed, 0 failed** (16.00s; 2 warnings: starlette/httpx deprecation, spacy/click deprecation)
   Log: `evidence/pytest-required-3files.log`
2. Extended review suite + modified root composition test:
   `python -m pytest -q tests/review/test_models_and_boundaries.py tests/review/test_rating_policy.py tests/review/test_review_service.py tests/review/test_scheduler_determinism.py tests/review/test_review_repository.py tests/review/test_migration_15.py tests/test_composition_root.py`
   -> **47 passed, 0 failed** (33.18s)
   Log: `evidence/pytest-extended-7files.log`
3. Read-only TestClient composition probe (21 checks):
   OpenAPI namespace (5 review routes registered exactly once; 18 wave2 paths still present), single composition root wiring, fail-closed HTTP boundaries (invalid rating to 422, injected `final_scheduler_rating` to 422, spoofed `evidence_kind` to 422, invalid `authentic_evidence_status` to 422), three rating channels distinct in responses, `rating-rule-v1.0.0` + py-fsrs@6.3.2 + scheduler parameters persisted, state_before/after + scheduling_result present, recursive semantic-leak scan of API response keys (clean), wave2 endpoint 200.
   -> **20/21 passed; the 1 "FAIL" was a probe-shape bug** (wave2 endpoint returns `{"student_id", "items": [...]}`; probe expected a bare list).
   Log: `evidence/probe-composition-readonly.log`
4. Wave-2 shape re-check: `GET /api/v1/wave2/personalized/learning-items?student_id=S1` -> 200, `items=[LI000001]`. **PASS**.
   Log: `evidence/probe-wave2-shape.log`
5. Edge-case probe (raise_server_exceptions=False): FK-nonexistent `practice_activity_id` -> **500 backend_processing_error** (unhandled `sqlite3.IntegrityError`); duplicate client-supplied `PA-DUP` activity ID -> both 200 with **1 row remaining, provenance silently replaced** (`{batch:1}` to `{batch:2}`); S2 event linked to S1-owned activity -> **200 accepted**; S2 event on S1's LearningItem -> **200 accepted**.
   Logs: `evidence/probe-edge-cases.log`, `evidence/probe-edge-cases-2.log`
6. Static scans: no event bus / threading / sockets / Streamlit / `sqlite3.connect` in `app/review` (protocols docstring mention only); `PRAGMA foreign_keys = ON` (`app/infrastructure/sqlite/connection.py:37`); `run.bat` entry points unchanged (no sync gap for this diff; `fsrs` installed via `pyproject.toml`/`uv.lock` through `bootstrap_environment.ps1`).

## 4. Findings (A–E)

Finding categories (mapping made explicit): A = composition root / API
namespace wiring (Q1); B = three rating channels + versioned provenance
(Q2, Q3); C = evidence separation in models/contracts (Q4); D = fail-closed
behavior (Q5); E = semantic leak + Wave-2 compatibility (Q6, Q7).

### A. Composition root and API namespace — PASS
- Review router is registered exactly once in the single `_BUSINESS_ROUTERS`
  tuple (`app/api/main.py:81`) and served in the one API namespace; OpenAPI
  exposes exactly the 5 review routes, each once.
- `ReviewService` is constructed in the single `_build_services` builder with
  `_review_repository`, `FSRSSchedulerAdapter()` and `_wave2_repository` as
  `LearningItemReaderProtocol`; both production (`_run_startup`) and test
  (`_build_full_app`) paths resolve through that one builder. No second
  runtime, event bus, registry authority, or composition root found (static
  scan + probe).
- Router is thin (validate/translate); workflow lives in `ReviewService`;
  core service depends on protocols only; SQL stays in the infrastructure
  repository. Matches AGENTS.md architecture boundaries.

### B. Three rating channels + versioned provenance — PASS
- `ReviewEvent` carries `system_provisional_rating`, `learner_self_rating`,
  `final_scheduler_rating` as separate fields/columns; no weighted average or
  collapse anywhere. The client cannot inject `final_scheduler_rating`
  (absent from `ReviewEventRequest`; `extra="forbid"` -> 422, probe-verified).
- Provenance is versioned on every review record: `rating_rule_version`
  (`rating-rule-v1.0.0`), `scheduler_implementation` (py-fsrs),
  `scheduler_version` (6.3.2), `scheduler_parameters`, `state_before` /
  `state_after`, `scheduling_result` — all persisted atomically with the
  event and the scheduler-state row (deterministic reconstruction support).
- Observation (not a violation): the API accepts `system_provisional_rating`
  and `authentic_evidence_status` directly from the client; WU1 has no
  server-side evaluator or authentic-evidence source yet, so these channels
  are client-asserted (attribution available via `provenance`). Defaults are
  fail-closed (`authentic_evidence_status="insufficient"`).

### C. Evidence separation in models/contracts — PASS
- `PracticeActivity` (activity/evidence history, `evidence_kind` literal
  `"practice"`, cannot be spoofed — 422 probe-verified) is distinct from
  `LearningItem` v1 (durable target, `no_fsrs_note` / `no_practice_note`, no
  scheduler columns — regression-test verified) and from `ReviewEvent`
  (durable review evidence with activity link).
- Practice vs authentic evidence distinguished by
  `evidence_kind`/`authentic_evidence_status` + fixed limitation statements;
  scheduling state persisted outside LearningItem v1 in its own table
  (migration 15 `learning_item_scheduler_states`).
- `SchedulerStateSnapshot` is exactly the py-fsrs Card field set; scheduling
  state is never named or exposed as ability/proficiency/learning gain.

### D. Fail-closed behavior — PARTIAL (concerns D1–D3)
- PASS: invalid ratings are rejected (Pydantic enum -> 422; service
  `_coerce_rating` raises, never coerces); invalid
  `authentic_evidence_status` -> `ReviewError` -> 422; missing LearningItem
  -> `learning_item_not_found` -> 404; unknown request fields -> 422
  (`extra="forbid"`); un-wired service -> 503; fuzzing is rejected at
  scheduler construction.
- **D1 (medium)**: a review event referencing a nonexistent
  `practice_activity_id` passes service validation and dies in the repository
  with `sqlite3.IntegrityError: FOREIGN KEY constraint failed`
  (`app/infrastructure/sqlite/repositories/review.py:161`), surfacing as an
  unhandled **500 backend_processing_error** with a full traceback instead of
  a mapped 4xx. The write is correctly rejected atomically (fail-closed
  outcome), but the API/service boundary does not fail closed cleanly.
- **D2 (medium)**: no identity binding is enforced. Probes showed (a) a
  learner S2 can record review events against S1's LearningItem
  (`_require_learning_item` checks existence only,
  `app/review/service.py:97-113`), and (b) an event can link a practice
  activity owned by a different student (FK passes since the activity
  exists). The `ReviewEvent` contract binds learner + LearningItem +
  activity, but student/ownership consistency is client-asserted.
- **D3 (low-medium)**: `save_practice_activity` uses `INSERT OR REPLACE`
  (`app/infrastructure/sqlite/repositories/review.py:90`); a client-supplied
  duplicate activity ID silently overwrites the prior durable evidence row
  (probe: provenance `{batch:1}` replaced by `{batch:2}`, 1 row left). For
  "durable review evidence" semantics, an append-only/reject-on-conflict
  behavior would be fail-closed.
- Minor: `_coerce_rating` raises raw `ValueError`, which the router does not
  translate (unreachable through the API because Pydantic 422s first; only
  affects direct service misuse -> 500 if ever reached).

### E. Semantic leak + Wave-2 compatibility — PASS
- No semantic leak: model-field scan, AST identifier scan of `app/review`,
  and recursive scan of live API response keys (events + schedule) found no
  mastery/proficiency/learning-gain/CEFR/CET/score/percentage naming.
  `scheduling_result.note` and the fixed limitation statements carry the
  boundary language.
- Wave-2 compatibility holds: no Wave-2 product files were modified (only
  mechanical test updates of the hard-coded migration 14 -> constant); all 18
  wave2 paths remain registered in the same app; the learning-items endpoint
  still returns persisted items; LearningItem v1 schema is untouched
  (no-FSRS columns absent). Migration 15 is additive-only with ledger-only
  rollback; migration 14 baseline untouched.

## 5. Blockers

**None** for composition, contracts, evidence separation, semantic
boundaries, or Wave-2 compatibility (all tests green). Findings D1–D3 are
medium-risk fail-closed/identity gaps in the preserved partial implementation
that should be addressed (with explicit authorization) before promotion —
they do not break the audited contracts or Wave-2.

## 6. Verdict

**PASS_WITH_CONCERNS** — composition, rating-channel separation, versioned
provenance, evidence separation, semantic boundaries, and Wave-2
compatibility are all verified sound (57 tests + probes green); concerns are
the unhandled FK 500 (D1), missing student/ownership identity binding (D2),
and silent overwrite of duplicate practice-activity IDs (D3).
