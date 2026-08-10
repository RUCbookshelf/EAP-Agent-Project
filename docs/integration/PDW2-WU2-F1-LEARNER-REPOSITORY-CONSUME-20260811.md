# PDW2-WU2-F1 LEARNER REPOSITORY-CONSUME - F-1 repair (LEARNER side)

**Goal:** PDW2-WU2-F1-LEARNER-REPOSITORY-CONSUME
**Owner:** LEARNER - Feedback & Learner Intelligence
**Worktree:** A:\EAP Agent Project\worktrees\learner (branch dept/feedback-learner)
**Starting SHA:** 0c98edbddc95fd280a82d0de2568b2a50405e857
**Date:** 2026-08-11
**Verdict:** GREEN

## 1. Scope (from the WU2 INT gate, AMBER finding F-1)

The Wave-2 routers mounted with disconnected per-router in-memory
repositories: nothing in the composed app wired a shared repository into the
wave2 router dependencies. CORE composes ONE shared SQLiteWave2Repository
and exposes it at app.state.wave2_repository; L2 and LEARNER routers must
consume it when present and fall back to their local repositories only for
standalone test contexts.

This repair covers the LEARNER side:

- app/api/routers/wave2_modules/learner_api.py now consumes
  request.app.state.wave2_repository when present via a duck-typed
  SharedObservationRepository adapter (no CORE-branch import, so the module
  stays importable standalone on the LEARNER branch).
- Local (in-memory) repository fallback applies only when the shared store
  is absent (standalone test contexts).
- New coverage: tests/learner/test_wave2_shared_repository_consumption.py
  (shared-store consumption, cross-request reuse, foreign-row skipping,
  fallback, adapter protocol fidelity).

## 2. Design

The CORE-composed shared store (SQLiteWave2Repository) owns the
learning_observations family; its interface (save_learning_observation /
get_learning_observation / list_learning_observations) differs from the
LEARNER ObservationRepository protocol, so the LEARNER side adapts:

- SharedObservationRepository implements the LEARNER protocol over the
  shared store's observation family.
- LEARNER ObservationRecord payloads are preserved losslessly inside the
  shared row's free-form context dict under the namespaced key
  learner_observation_record_v1, so the richer LEARNER record round-trips
  even though the shared store assigns its own generated row ids.
- Shared rows written without the LEARNER payload are not LEARNER-typed
  observations and are skipped (never reinterpreted or surfaced).
- LEARNER-only families with no shared table yet (submission samples,
  evidence, revision behavior, proficiency context) are served from a local
  in-memory store inside the adapter; they are NOT shared across routers
  until a shared contract exists (documented in the module docstring).
- get_learner_model_service(request) returns the shared-backed service when
  request.app.state.wave2_repository is present, else the branch default
  in-memory service.

## 3. Verification evidence

| Check | Result | Evidence |
| --- | --- | --- |
| Git preflight | PASS | root worktrees/learner; branch dept/feedback-learner; HEAD 0c98edb; pre-existing untracked evidence preserved untouched |
| LEARNER wave2 suite (baseline) | PASS | pytest tests/learner - 149 passed before the change |
| LEARNER wave2 suite (final) | PASS | pytest tests/learner - 159 passed (149 existing + 10 new shared-consumption/fallback tests) |
| Learner-adjacent regression | PASS | tests/test_v095f2_service_narrowing.py, tests/academic/test_fixture_matrix.py, tests/learner - 176 passed |
| Shared-store consumption | PASS | rows seeded in the fake shared store are visible through the learner API; observation-type filter delegates to the shared store; cross-request reuse verified |
| Fallback | PASS | shared store absent means default local service; local seeding still visible |
| Adapter fidelity | PASS | full ObservationRecord round-trip identical; adapter satisfies ObservationRepository protocol |
| Resource hygiene | PASS | no background processes/locks; temp DBs confined to pytest basetemp under TEMP; no global git config changes; no push/PR/promotion |

## 4. Commit scope

Exactly the following files (parent 0c98edbddc95fd280a82d0de2568b2a50405e857):

- app/api/routers/wave2_modules/learner_api.py (modified)
- tests/learner/test_wave2_shared_repository_consumption.py (new)
- docs/integration/PDW2-WU2-F1-LEARNER-REPOSITORY-CONSUME-20260811.md (this report)

Pre-existing untracked evidence (docs/integration/LEARNER-FOUNDATION-FREEZE-20260809.md,
docs/integration/PDW1-ALIGN-LEARNER-B6FCE9-20260809.md,
docs/integration/PDW2-ALIGN-LEARNER-59500127-20260810.md,
tests/learner/__init__.py) was preserved and NOT committed.

## 5. Boundaries honored

- No writes outside worktrees/learner; no master/other-worktree mutation.
- No CORE-branch imports; no migrations.py / app/api/main.py changes.
- No reset/clean/rebase/force update/push/PR/promotion.
- Raw SWECCL untouched.
- integration_required=true (F-1 composition consumed on the LEARNER side;
  the composed-app wiring is qualified by INT at the WU2 gate re-run).
- promotion_eligible=false (no promotion authority).
