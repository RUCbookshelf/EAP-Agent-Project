# v0.9.7-B Work Unit 3 - Idempotent Priority Practice Target Creation and Reuse

**Stage:** v0.9.7-B Work Unit 3 (implementation)
**Status:** COMPLETE - all 20 WU3 acceptance criteria satisfied; WU4 is the
next planned work unit; v0.9.7-B as a whole is NOT complete.
**Date:** 2026-08-05
**Governing protocol:** the owner-provided WU3 work-unit objective,
docs/development/V0.9.7_B_SPEC.md (frozen by WU1), and
RUN_VERIFICATION_V0.9.7_B_WU2.md.

## 1. Starting and ending Git state

- Branch: `master` (unchanged).
- Starting HEAD: `08edca3` (post-WU2 closure).
- Ending HEAD: recorded in section 15 after the focused commits.
- Baseline discrepancy (recorded per objective section 2): the objective
  names the repository as `A:\EAP Project\writing-feedback-mvp`; the actual
  checkout is `A:\EAP Agent Project\writing-feedback-mvp` (the checkout
  containing all WU1/WU2 history and the post-WU2 HEAD). Work continued from
  the actual checkout; no history was reset.
- Worktree before implementation: only preserved user-owned entries
  (`AGENTS.md`, `.claude/`, `CLAUDE.md`, `RUN_VERIFICATION_V0.7.md`,
  `RUN_VERIFICATION_V0.8.2.md`, `ARCHITECTURE_COUPLING_AUDIT_V0.9.5_A.md`,
  `data/demo_journey_manifest.json`) plus the gitignored v0.9.7-a logs.

## 2. WU3 objective

Transform the validated WU2 `PriorityTargetContract` into a safe, persistent,
production-ready creation workflow: one persisted Feedback priority maps to
at most one ACTIVE practice target regardless of repeated requests, refreshes,
retries, or duplicate user actions, with the WU2 deferred obligations closed
(allocator repair, general ownership validation, one-active-target
enforcement, legacy evidence boundary).

## 3. WU2 deferred items closed

- `_next_practice_id` allocator repair: closed (section 4).
- General target creation ownership validation: closed (section 7).
- One-active-target enforcement: closed (section 6).
- Legacy evidence validation boundary: closed - client-supplied
  `evidence_ids` on the legacy (no-priority) path are rejected with a
  controlled 422 and zero writes; evidence requires a validated priority
  reference. Existing stored targets remain readable (no retroactive
  changes).

## 4. Allocator repair

`SQLitePracticeRepository._next_practice_id` (app/infrastructure/sqlite/
repositories/practice.py):

- The numeric suffix now starts after the FULL `id_prefix`
  (`SUBSTR(id, LENGTH(prefix) + 1)` via a bound parameter) instead of the
  fixed two-character offset, and a same-prefix `LIKE` filter scopes the
  maximum to rows carrying that prefix. Two-character (PT/EX/EA/PE/TE) and
  three-character (FET/WTR/PSS) prefixes therefore allocate correctly; the
  previous three-character collision (always allocating `...000001`) is
  gone. No per-prefix special cases.
- All eight save methods pass their exact prefix.
- `save_practice_target` allocates and writes inside one explicit write
  transaction (BEGIN IMMEDIATE): the write lock is acquired before reading
  the maximum, so concurrent creation is serialized and cannot collide on an
  ID; a bounded retry remains as a safety net, and logical-key conflicts
  surface as IntegrityError for the creation service to recover.
- Regression coverage: PT/EX/EA/PE/FET/WTR/PSS allocation, mixed prefixes,
  empty table, existing maximum, repeated creation, and concurrent creation
  (thread pool, unique IDs) - `TestAllocator`.
- Discovered defect fixed as part of the allocator regression work:
  `FeedbackEngagementTrace` lacked `created_at` while its repository INSERT
  requires it (the FET save path had never been exercised; demo/tests only
  wrote WTR). The schema now carries `created_at` with the same default as
  every other practice entity (additive; app/practice/schemas.py).

## 5. Idempotent create-or-reuse workflow

`PracticeTargetCreationService` (app/practice/target_creation.py):

```
Validated PriorityTargetContract
    -> student-scoped lookup by logical key
    -> existing target (any status): reuse, return unchanged
    -> otherwise: create ACTIVE target and persist
    -> IntegrityError (concurrent duplicate): re-lookup, return existing
```

- Logical uniqueness key (frozen): `(student_id, source_submission_id,
  source_priority_id)`.
- Lookup is learner-scoped through the existing `list_practice_targets`
  port (no port/protocol change), so cross-student reuse is impossible.
- Repeated API requests, refreshes, retries, and reruns return the same
  target; concurrent creation of the same key yields exactly one target
  (thread-pool test).
- The router resolves and conflict-checks the WU2 contract, then delegates
  entirely to the service; no business rules live in the router.

## 6. Uniqueness enforcement (one active target per key)

- Database constraint (migration 13, additive): partial unique index
  `ux_practice_targets_active_priority_key` on
  `practice_targets(student_id, source_submission_id,
  json_extract(target_json, '$.source_priority_id'))` filtered to
  `status = 'active'` with a non-NULL priority reference. The key's third
  component lives only in `target_json` (WU1 audit finding), so the index
  reads it via json_extract - no table change, no backfill, existing rows
  preserved.
- Service-level rule: at most one target per key (any status) via the
  lookup-before-create; the DB index is the concurrency backstop for the
  ACTIVE rule and makes duplicate active targets impossible on any code path.
- Migration 13 is non-destructive; rollback (13 -> 12) drops only the index
  and is covered by a test.

## 7. Ownership validation

All creation paths validate before any write:

- Priority-derived: the WU2 mapper validates bundle ownership, feedback
  association, priority index/structure, and diagnosis association
  (unchanged contract); the creation service adds the student-scoped
  key lookup.
- Legacy (no priority reference): the source submission must exist (404)
  and belong to the requested learner (403); the source diagnosis must
  belong to the submission (422); non-empty client-supplied evidence_ids are
  rejected (422); then the target is created and persisted (gate status
  still enforced by `PracticeService`).
- Cross-student, cross-submission, cross-feedback, fabricated references,
  and invalid evidence are covered by service- and API-level tests with
  zero-write assertions.

## 8. Transaction boundaries

- Target save: single connection, BEGIN IMMEDIATE, allocation + INSERT +
  commit (atomic, serialized with other writers), bounded retry on
  lock/busy/IntegrityError.
- Idempotent workflow: validation and lookup happen before persistence;
  concurrent duplicate inserts are recovered after commit by re-reading the
  existing row (no partial or duplicate rows).
- Legacy workflow: all validation completes before `save_practice_target`;
  `practice_not_available` gate results are returned without a write
  (pre-existing semantics preserved).

## 9. Migration decision

- Migration 13 IS required and was added (frozen B_SPEC section 6 mechanism;
  preferred database-constraint enforcement layer). It is additive and
  non-destructive: CREATE UNIQUE INDEX ... IF NOT EXISTS (expression partial
  index over the persisted JSON), no table changes, existing rows preserved.
- `LATEST_MIGRATION_VERSION` 12 -> 13; `MIGRATIONS[13]`; rollback supports
  the (13, 12) one-step pair (DROP INDEX only).
- Version-pinning test assertions were updated 12 -> 13 in the files that
  hard-pin the schema version: test_analysis_runs_v04, test_calf_v08,
  test_diagnostic_calibration_v061, test_learner_model_v07,
  test_revision_v05, test_snapshot_repository_v03,
  test_v06_configuration_dashboard, test_v071_reliability_ui,
  test_v095b_router_contract, test_v095g_facade_contraction. Two rollback
  tests now step 13 -> 12 -> 11 (one-step rollback policy preserved).
- Parity infrastructure was revised with documented WU3 fingerprints
  (verification/v0.9.5-e/compare_repository_parity.py): `_next_practice_id`
  SQL is pinned to the repaired fingerprint, and migrations.py is pinned to
  its WU3 SHA-256 (historical E-era baseline remains in git history).

## 10. Modified files and purposes

- `app/infrastructure/sqlite/repositories/practice.py`: prefix-length-safe
  allocator (all 8 callers pass their prefix), atomic BEGIN IMMEDIATE
  save_practice_target with bounded retry.
- `app/database/migrations.py`: migration 13 (partial unique index),
  LATEST_MIGRATION_VERSION 13, one-step rollback (13,12).
- `app/practice/target_creation.py` (new): `PracticeTargetCreationService`
  (create-or-reuse + legacy validation).
- `app/practice/mapping.py`: public `diagnosis_contains_id` helper only
  (contract unchanged).
- `app/practice/schemas.py`: `FeedbackEngagementTrace.created_at` additive
  field (fixes the never-exercised FET save path).
- `app/api/routers/practice.py`: `create_practice_target` delegates to the
  creation service (priority + legacy); error mapping extended with
  `invalid_evidence`; no new endpoint.
- `app/api/deps.py`, `app/api/main.py`: `practice_target_creation_service`
  accessor + wiring in both composition roots.
- `verification/v0.9.5-e/compare_repository_parity.py`: documented WU3
  revision registry (allocator SQL fingerprint, migrations SHA-256).
- `verification/v0.9.5-h2a/isolated_pytest_runner.py` +
  `verification/v0.9.6-dp0-v1/canonical_full_core_command.txt`: canonical
  allowlist extended 26 -> 29 entries (mapping.py, schemas.py,
  target_creation.py).
- `verification/v0.9.5-h2d2/dependency_graph_before/after.json`: refreshed
  for the handler dependency change (delta: create_practice_target now
  depends on get_practice_target_creation_service +
  get_practice_submission_reader; routes 81 and OpenAPI unchanged).
- `tests/test_v097b_wu3_target_creation.py` (new, 33 tests);
  `tests/test_v097b_wu2_priority_mapping.py` (two tests updated where WU3
  deliberately supersedes WU2 boundaries: legacy evidence is now rejected;
  duplicate requests now reuse); version-pinning updates in ten test files.

## 11. Tests

New `tests/test_v097b_wu3_target_creation.py` (33 tests):

- Allocator (8.1): PT/EX/EA/PE two-character, FET/WTR/PSS three-character,
  mixed prefixes, empty table, existing maximum, repeated creation,
  concurrent creation (unique IDs).
- Migration 13: index present on fresh DB, duplicate ACTIVE key rejected by
  the constraint, inactive/NULL-key/other-student duplicates allowed,
  v12 -> v13 upgrade preserves existing rows, rollback drops only the index.
- Idempotency (8.2): first creation, repeated request reuses, repeated API
  requests (3x same payload), concurrent creation of the same key yields one
  target, same category different student / same student different
  submission create separate targets, reuse leaves the record byte-identical.
- One-active-target (8.3): active reuse, non-active reuse without new
  creation, stale reuse, DB constraint behavior.
- Ownership (8.4): legacy cross-student 403, missing submission 404,
  unrelated diagnosis 422, legacy evidence 422, API cross-submission reuse
  rejected (422) with zero writes.
- Legacy compatibility (8.5): legacy creation + retrieval, full
  exercise/attempt/evaluation flow + Journey projection.
- Scope guards (8.6): no UI auto-creation, no completion state, evaluation
  behavior unchanged.

Updated WU2 tests (2): legacy evidence now 422 with zero writes; duplicate
requests reuse the same target (one row).

## 12. Regression results

- Focused WU3: 33 passed (twice, concurrency stability confirmed).
- WU2 mapping suite (updated): 76 passed; combined 109 passed (twice).
- Static: compileall OK; pixel-art style audit PASS (0 violations);
  `git diff --check` clean on all WU3 files.
- Affected regression (34 files: WU2/WU3 suites, practice targets/API/
  repositories, attempts/evaluations, Journey projection, parity contracts,
  H2D2, migrations, all version-pinned suites): 562 passed, exit 0. One
  run hit the pre-existing readiness-gate timing flake
  (test_v095b_router_contract.py::test_business_route_gated_until_ready_
  while_health_available - background startup thread re-transitions the
  global lifecycle mid-test); it passes in isolation and the clean batch
  re-run passed. Unrelated to WU3 (no lifecycle/lifespan change).
- Full non-live core (canonical environment, 29-entry allowlist, fresh
  isolated DB, `--ignore=tests/live`): **969 passed / 8 skipped / exit 0**
  (C:\tmp\wu3-fullcore\full_core_output.txt) - 936 baseline + 33 new WU3
  tests.
- Launcher: `cmd /c "run.bat --verify"` PASS - health/docs/streamlit 200,
  isolated auto-provisioned DB, migrate/initialize/smoke exit 0.
- Demo smoke on a fresh migrated DB: migration 13 + index present; full
  demo journey created through the production map.
- Locale parity: no locale file changed (555/555 preserved; parity verified
  by the full core).

## 13. Known limitations

- The pre-existing readiness-gate test flake remains (test isolation issue,
  documented in WU2 and repeated here); it is unrelated to WU3.
- The "at most one target per key (any status)" rule is service-enforced
  (lookup-before-create); the database constraint covers ACTIVE rows only,
  as frozen. A future writer bypassing the service could create a second
  non-active row for the same key; no such writer exists today.
- Legacy creation has no idempotency key (no priority reference), so
  repeated legacy creations still append rows; the legacy path is
  ownership-validated and evidence-boundary-enforced, and the WU4 UI will
  use the priority-derived path.
- H2D2 dependency-graph snapshots and the parity fingerprint/migrations
  registries were refreshed for the required WU3 changes (documented deltas
  above); the historical E-era baselines remain in git history.

## 14. Deferred WU4-WU6 work

- WU4: focused Practice task and attempt loop (priority context rendering,
  seeded source text, attempt pending guard, attempt ownership validation,
  error recovery, re-entry).
- WU5: evaluation/completion semantics (COMPLETED status, finish/continue
  actions, no-mastery wording).
- WU6: Journey integration verification, full EN/ZH x desktop/mobile matrix,
  detect_changes review.

Practice UI, answer submission, evaluation, completion, and Journey changes
were NOT implemented in WU3 (scope guards verified by tests).

## 15. Commit list and final acceptance status

- `34cf1e9` `fix(v0.9.7-b): repair practice target allocator`
  - app/infrastructure/sqlite/repositories/practice.py (prefix-length-safe
    allocator, BEGIN IMMEDIATE serialized save with bounded retry),
    app/practice/schemas.py (FeedbackEngagementTrace.created_at).
- `12ce17d` `feat(v0.9.7-b): add idempotent target creation and reuse`
  - migration 13 (partial unique index + rollback), app/practice/
    target_creation.py (new), mapping helper, router/deps/composition
    wiring, H2D2 dependency-graph refresh, parity fingerprint/migrations
    registry, canonical allowlist 26 -> 29.
- `ab022c9` `test(v0.9.7-b): verify target uniqueness and ownership`
  - tests/test_v097b_wu3_target_creation.py (new, 33 tests), WU2 test
    updates (2 superseded boundaries), version-pinning updates in ten test
    files.
- `3249144` `docs(v0.9.7-b): close work unit 3`
  - RUN_VERIFICATION_V0.9.7_B_WU3.md (new), PROJECT_STATE.md,
    docs/development/CURRENT_TASK_STATE.md, docs/development/MASTER_ROADMAP.md.

Post-work HEAD: `dcd2348`. Branch `master` unchanged. No push or pull
request was opened (not instructed). All 20 WU3 acceptance criteria are
satisfied per the evidence above; v0.9.7-B remains incomplete with WU4 next.
