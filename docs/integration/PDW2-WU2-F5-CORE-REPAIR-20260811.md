# PDW2-WU2 F-5 Repair -- CORE shared-store L2 RevisionLoopRepository contract

**Goal:** `PDW2-WU2-INT-INTEGRATION-GATE-RE-GATE__REPAIR` (REAL run
`PDW2-WU2-INT-INTEGRATION-GATE-RE-GATE__REPAIR__20260811T003237Z__87a972`)
**Owner:** CORE (shared platform & core)
**Worktree:** `A:\EAP Agent Project\worktrees\shared-core` (`dept/shared-core`)
**Starting SHA:** `04ad8dec905d43587746087674ec09d485c56b5d`
**Scope:** F-5 only. Amend unpromoted migration 14 + `SQLiteWave2Repository`;
focused real-store contract tests; docs. No promotion/push/PR; no new
migration lane; no other-department product changes.

## Finding F-5 (from INT RE-GATE report `PDW2-WU2-INT-INTEGRATION-GATE-RE-GATE-REPORT.md`)

The F-1 shared-store composition was wired, but the composed store did not
implement the L2 `RevisionLoopRepository` protocol consumed by the mounted
wave-2 routers:

- `POST /api/v1/wave2/revision/tasks` -> HTTP 500
  `AttributeError: 'WritingTask' object has no attribute 'genre'`
  (`wave2.py:120` read `task.genre`; the L2 `WritingTask` has
  `writing_context`/`classification`/`status`, no `genre`).
- 11 of 18 protocol methods missing (submission-version, revision-
  observation, priority-plan, scaffold-event families).
- Migration-14 `writing_tasks` had no `writing_context`;
  `learning_items` had no `category`/`task_context`/`limitations`.
- Root cause: every suite substituted an L2-protocol-compatible stand-in
  (`InMemoryRevisionLoopRepository`/duck-typed fakes); the real CORE-composed
  `SQLiteWave2Repository` was never exercised with the L2 domain shapes.

## Repair changes (bounded tracked files)

1. `app/database/migrations.py` -- migration 14 amended in place (still
   unpromoted; no new lane, version stays 14):
   - `writing_tasks` + `writing_context` (authoritative two-level context),
     `classification_json`, `status`; legacy `genre`/`reference_group_id`
     kept (DEFAULT-covered).
   - New families: `submission_versions` (append-only V1/V2/... with
     ancestry, task-context snapshot, analysis/feedback links, corpus
     routing, reanalysis events), `revision_observations` (bounded
     observational comparisons), `priority_plans` (observation-only),
     `scaffold_events` (7-level SCAFFOLD FIRST) + indexes.
   - `learning_items` + `category`, `task_context_json`, `limitations_json`,
     `no_fsrs_note`, `no_practice_note`; legacy `context_json` kept.
   - Rollback 14->13 remains ledger-only; re-apply idempotent
     (`CREATE IF NOT EXISTS`).
2. `app/infrastructure/sqlite/repositories/wave2.py` -- the shared
   `SQLiteWave2Repository` now implements the full 18-method L2
   `RevisionLoopRepository` protocol. CORE-owned dataclass shapes mirror the
   L2 models (dept/l2-writing@135cf8b) and duck-type the pydantic surface
   the L2 services/routers consume (`model_dump(mode="json")`,
   `model_copy(update=...)`); legacy-only fields (`genre`,
   `reference_group_id`, `context`) are excluded from JSON dumps so router
   payloads match the L2 shape. `writing_context` is persisted directly from
   L2-shaped tasks (never a `genre` fallback); CORE-origin rows backfill
   `writing_context` from their legacy `genre` value. Registration-path
   student rows are ensured with the same `INSERT OR IGNORE` pattern the
   submission repository uses (the real composed app creates tasks/items for
   learner ids before any submission exists).
3. `tests/test_wave2_repository_composition.py` -- focused real-store
   contract tests (L2-shaped task without `genre`, protocol method
   presence, submission-version family, revision observations, priority
   plans + scaffold events, LearningItem extended fields, status updates
   with datetime).
4. `docs/DATABASE_MIGRATIONS.md`, `docs/DATA_MODEL.md` -- schema
   documentation refreshed for the amended migration 14.

## Evidence (dept/shared-core, worktree venv, before preview)

`pytest tests/test_wave2_repository_composition.py tests/test_wave2_repositories_v14.py tests/test_wave2_migration_v14.py tests/test_wave2_router_assembly.py`
-> **24 passed, 1 skipped** (new contract tests RED before the
implementation: protocol-methods assertion failed with the exact 11 missing
methods from F-5; GREEN after).

`pytest tests/test_migration_drop_column_rollback_note.py tests/shared/test_version_single_sourcing.py tests/test_migrations_v02.py`
-> PASS (part of the 30 passed in the pin-adjacent run).

Known standalone-branch pin condition (NOT regressions; verified in the
merged preview like the prior re-gate):
`tests/test_v095b_router_contract.py::test_route_contract_pinned` and
`tests/test_shared_core_drift.py::TestModuleSetManifest` fail on
`dept/shared-core` alone because their pinned expectations (19 wave2 router
pairs; 244-module union manifest) include LEARNER/L2/UX modules that exist
only in the merged preview tree. Both passed in the F-1..F-3 re-gate on the
preview tree and are re-verified there.

## Merge-preview verification (this repair)

Detached preview from master `59500127` + final CORE candidate + CORPUS
`8e80ccc` + LEARNER `0d40041` + L2 `135cf8b` + UX `253f1c5`:

- INT F-5 probe (`f5_shared_store_probe.py`): warmup 200; shared store is
  `SQLiteWave2Repository`; all 18 L2 protocol methods present; create task
  201.
- Decisive real `create_app` flow with default dependencies: task 201 (with
  `writing_context`), V1 201, feedback visible, V2 201 (append-only),
  observation 200, reanalysis 200, priority plan 200 (shared repository),
  scaffold 200, LearningItem 201, learner view 200.
- Migration-14 round-trip/idempotence; CORE wave2 composition/repository
  tests; relevant L2/LEARNER repository-consumption tests; version/pin/
  manifest checks; SECCL/exposure + epistemic invariants confirmed
  unchanged.

## Result

Functional/Evidence GREEN and Resource Hygiene GREEN (preview worktree and
all processes removed). `integration_required=true`;
`promotion_eligible=false`. No promotion/push/PR performed.
