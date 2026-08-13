# CORE WU2 DEPARTMENT HANDOFF — PDW3-WU2-CORE-COMPOSITION-REPAIR-20260812

- handoff_id: PDW3-WU2-CORE-COMPOSITION-REPAIR-20260812__20260812T021212Z__c96b5c
- goal_id: PDW3-WU2-CORE-COMPOSITION-REPAIR-20260812
- owner: CORE
- worktree / branch / HEAD: A:\EAP Agent Project\worktrees\shared-core /
  dept/shared-core @ 7a9e4b470c41c0453a3795233f1bdd5c483d80ae
- starting_sha == final_sha: 7a9e4b470c41c0453a3795233f1bdd5c483d80ae
  (no commit created; the inherited WU1 candidate plus the bounded WU2
  repair remain the uncommitted candidate state)
- verdict: **DEPARTMENT GREEN** (INT retains gate authority; no promotion)
- state after submission: **HANDOFF_PENDING_ACCEPTANCE** — the parent stays
  open until PROGRAM accepts or rejects this handoff; no self-close.

## 1. Bounded change set (write scope only)

Product / shared contracts:

| File | Change |
| --- | --- |
| `app/api/deps.py` | Canonical `get_review_service` and `get_review_evidence_lookup` dependency getters (503 fail-closed when not composed). |
| `app/api/main.py` | Shared `SQLiteReviewEvidenceLookup` composed at the single `_apply_service_state` assignment point (`api.state.review_evidence_lookup`); existing `review_service` / `review_repository` wiring retained unchanged; frozen service-graph key set untouched. |
| `app/api/routers/review.py` | Delegates `get_review_service` to the canonical deps getter; duplicate local implementation removed; `__all__` export preserved. |
| `app/review/protocols.py` | `ReviewEvidenceLookupProtocol` (owner_of / get_record) — shared mechanical evidence-lookup boundary. |
| `app/review/__init__.py` | Exports `ReviewEvidenceLookupProtocol` from the shared package root. |
| `app/infrastructure/sqlite/repositories/review.py` | `SQLiteReviewEvidenceLookup` — learner-scoped, fail-closed lookup over `practice_activities` (PA*) and `review_events` (RE*). |

Tests (`tests/review/` only): +7 tests

| File | Added |
| --- | --- |
| `test_review_composition.py` | +4: deps getters resolve composed instances; CORE `ReviewService` satisfies the LEARNER `CoreReviewServicePort` structural mirror; LEARNER-shaped practice record consumed by the shared service; composed evidence lookup is learner-scoped. |
| `test_review_repository.py` | +2: evidence-lookup owner/record round trip; close/reopen durability on the single SQLite file. |
| `test_review_fail_closed_api.py` | +1: deps getters fail closed 503 when not composed. |

Evidence (`docs/integration/pdw3-wu2-core-composition-repair-20260812/`).

Not touched: `app/database/`, `app/version.py`, `pyproject.toml`, `uv.lock`,
Migration 14/15 bodies, Program Control, master, Git history, other
worktrees, or any tracked root test outside `tests/review/`.

## 2. Composition results (exact)

- Single composition root: `_build_services` -> `_apply_service_state`
  unchanged as the only construction/assignment path; probe
  `graph_keys` = 15 keys exactly as pinned by
  `tests/test_composition_root.py::test_build_services_returns_expected_keys`
  (the frozen WU1 key pin was preserved; `review_evidence_lookup` is
  composed at the state-assignment point, matching the established pattern
  for repository-derived state attributes).
- `api.state.review_service` / `api.state.review_repository` /
  `api.state.review_learning_item_reader` /
  `api.state.review_evidence_lookup`: all present and real (probe
  `state_review_attrs` all true).
- Canonical getters `get_review_service(request)` and
  `get_review_evidence_lookup(request)` resolve the SAME composed
  instances (`deps_getters_resolve_state: true`); on any app without the
  wiring they raise HTTPException 503 (tested).
- One process / one SQLite file / one API namespace: probe confirms a
  single database path; 5 review routes registered exactly once
  (POST/GET practice-activities, POST/GET events, GET schedule); no new
  routes added; the pinned route contract test passes inside the Wave-2
  regression set.
- `ReviewService` remains exported from `app.review`
  (`review_service_is_exported_from_app_review: true`).

## 3. Persistence results (exact)

- `SQLiteReviewEvidenceLookup.owner_of` resolves PA* -> practice_activities
  owner and RE* -> review_events owner; unknown/empty/non-review ids fail
  closed with `None` (`unknown_id_is_none: true`).
- `get_record(learner_id, source_id)` returns the durable shared
  `PracticeActivity` / `ReviewEvent` model only to its owner;
  cross-student lookup returns `None` (`record_cross_student_is_none:
  true`); returned activity carries `evidence_kind == "practice"`.
- Close/reopen of the SAME SQLite file preserves ownership and record
  lookup (repository test `test_evidence_lookup_survives_close_reopen`).
- No new migration, no second database, no second runtime, no ATTACH; the
  adapter reads the existing migration-15 table families through the one
  connection manager.

## 4. LEARNER-consumption proof (exact)

- `ReviewService` structurally satisfies LEARNER's typed
  `CoreReviewServicePort` (rating_rule_version property,
  `scheduler_identity()`, `record_practice_activity(activity)`,
  `record_review(**kwargs)`): asserted via a runtime structural mirror in
  `test_review_service_satisfies_learner_core_review_service_port`.
- A LEARNER-shaped `PracticeActivityRecord` mirror (same field names/types,
  `model_copy` + `status.value` attribute access) is consumed by the real
  shared `ReviewService`/repository and persists with
  `evidence_kind == "practice"` (`test_learner_shaped_practice_record_is_consumed_by_shared_service`).
- `SQLiteReviewEvidenceLookup` satisfies the shared
  `ReviewEvidenceLookupProtocol` and matches the LEARNER
  `AcknowledgementEvidencePort` shape (`owner_of`, `get_record`), so the
  INT composition can inject it as the acknowledgement service's
  `evidence_port` without copying LEARNER semantics into CORE.
- The adapter carries no acknowledgement wording, consent policy, admission
  semantics, or Journey behavior; LEARNER retains all qualification rules.

## 5. Test results (exact checkpoint)

| Suite | Result | Evidence |
| --- | --- | --- |
| Baseline tests/review (before WU2 edits) | 82 passed | pre-edit run |
| Focused composition/repository/fail-closed (after WU2) | 29 passed | 3-file focused run |
| Full tests/review after WU2 | 89 passed (59.25s) | run before closure log |
| Closure: tests/test_composition_root.py + tests/review | 93 passed, PYTEST_EXIT=0 (77.47s) | `evidence/pytest-review-final.log` |
| Affected Wave-2 regression (13 modified root tests + shared version single-sourcing + service-narrowing + migration drop-column note) | 206 passed, PYTEST_EXIT=0 (203.17s) | `evidence/pytest-wave2-final.log` |
| Composition/persistence probe | PROBE_EXIT=0 | `evidence/probe-composition-persistence.log` |
| Resource hygiene | PASS | `evidence/git-status-initial.txt` vs `evidence/git-status-final.txt`; HEAD unchanged |

The affected Wave-2 regression command:

```text
pytest tests/test_analysis_runs_v04.py tests/test_calf_v08.py
tests/test_composition_root.py tests/test_diagnostic_calibration_v061.py
tests/test_learner_model_v07.py tests/test_revision_v05.py
tests/test_snapshot_repository_v03.py tests/test_v06_configuration_dashboard.py
tests/test_v071_reliability_ui.py tests/test_v095b_router_contract.py
tests/test_v095g_facade_contraction.py tests/test_v097b_wu3_target_creation.py
tests/test_wave2_migration_v14.py tests/shared/test_version_single_sourcing.py
tests/test_v095f2_service_narrowing.py tests/test_migration_drop_column_rollback_note.py
```

## 6. Resource hygiene

- `git status` before vs after: the only deltas are the two in-scope API
  file edits (`app/api/deps.py`, `app/api/routers/review.py` inside the
  already-untracked candidate) and the new bounded evidence directory
  `docs/integration/pdw3-wu2-core-composition-repair-20260812/`. Every
  inherited dirty/untracked file is byte-preserved; HEAD unchanged
  (`7a9e4b47`); no commit/stage/push/PR/merge/promotion/reset/clean/restore.
- No Program Control file written; no other worktree touched; no raw
  SWECCL access; no stray processes or servers started.
- Nested-worker dispatch tooling was not available in this session (no
  subagent spawn tool), so scopes were kept disjoint and executed directly
  by the parent with the mandated deepseek/deepseek-v4-flash + ultra
  routing; no planning files were created (PLANNING_DISABLED=1).

## 7. Gate conclusion

**DEPARTMENT GREEN.** The shared ReviewService is real, composed through
the single application/process/SQLite/composition root, exposed to
downstream composition via canonical deps getters, and proven consumable by
the LEARNER typed bridge contract; the shared evidence-lookup adapter
provides the persistence boundary required for qualified acknowledgement
evidence lookup without copying LEARNER semantics. INT retains gate
authority; no promotion authority was granted; the parent remains
**HANDOFF_PENDING_ACCEPTANCE**.
