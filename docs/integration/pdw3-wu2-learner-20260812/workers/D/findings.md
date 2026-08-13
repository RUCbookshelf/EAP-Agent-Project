# Worker D Findings — API Composition / Wave-2 Compatibility (RETRY-2)

- worker: `PDW3-WU2-LEARNER-PRACTICE-REVIEW-TRANSFER-20260812__RETRY-2` / D
- model / reasoning / env: `deepseek/deepseek-v4-flash` / ultra /
  `PLANNING_DISABLED=1` (no substitution)
- worktree / branch / HEAD: `A:\EAP Agent Project\worktrees\learner` /
  `dept/feedback-learner` @ `7a9e4b470c41c0453a3795233f1bdd5c483d80ae`
  (re-verified at the end; no commit created)
- verdict: **DONE with two BLOCKED items** (owned scope complete; two
  unowned edits are required for the blocked items below — reported, not
  performed)

## 1. Context read

1. `docs/integration/pdw3-wu2-learner-20260812/CHECKPOINT-002-RETRY2-DISPATCH-SURFACE.md`
   plus checkpoints 001/003/005-008 (dispatch surface, worker states, parent
   gates).
2. Worker A/B/C findings and actual source:
   `app/learner/review_bridge.py`, `app/practice/review_transfer.py`,
   `app/journey/transfer.py`, `app/journey/service.py` (B's additive
   methods), `app/learner/acknowledgement*.py`,
   `app/api/routers/acknowledgement.py`, and their focused tests.
3. Current `app/api/main.py`, `app/api/deps.py`, router conventions
   (`_BUSINESS_ROUTERS`, `wave2` assembly), and composition/Wave-2 tests
   (`tests/test_composition_root.py`, `tests/test_v095b_router_contract.py`,
   `tests/test_v095d_api_contract.py`, `tests/test_wave2_router_assembly.py`).
4. CORE WU1 handoff
   (`worktrees/shared-core/docs/integration/pdw3-wu1-recovery-20260811/CORE-WU1-DEPARTMENT-HANDOFF.md`):
   the CORE `app/review` candidate is NOT importable on this branch; the
   typed optional injection boundary is the required composition.

## 2. Implementation (owned write scope only)

### `app/api/main.py`

- Imported the `acknowledgement` router module and registered it in
  `_BUSINESS_ROUTERS` exactly once (after `journey`) — the single
  composition root includes Worker C's learner-owned router through the
  existing `_include_business_routers` path; no duplicate registration
  exists anywhere.
- Added `_AppendOnlyAcknowledgementStore` (process-local, append-only,
  composition glue). No migration or acknowledgement table exists on this
  branch; the service is additionally composed with `evidence_port=None`,
  so every acknowledgement request fails closed (503) before any write and
  this placeholder never holds data. It is not a second persistence
  authority for real records; durable persistence plus the production
  evidence lookup are INT-gated (need a migration, out of scope).
- `_build_services` now constructs and returns two new graph keys:
  - `acknowledgement`: `AcknowledgementService(store=..., evidence_port=None)`;
  - `practice_review_transfer`: `PracticeReviewTransferOrchestrator(core_review_service=None)`
    — the typed optional injection boundary for the integrated CORE review
    service (never copied, no second store, no adapter, no second DB).
- `_apply_service_state` assigns both to `api.state.acknowledgement_service`
  and `api.state.practice_review_transfer` through the single assignment
  point. `api.state.journey_service` continues to carry the existing
  `JourneyService` whose additive Worker B methods
  (`get_practice_history` / `get_authentic_application`) are therefore
  reachable through the composed service.

### `app/api/deps.py`

- Added `get_acknowledgement_service` and `get_practice_review_transfer`
  (API-only dependency helpers resolving from `app.state`, mirroring
  `get_journey_service`). Worker C's router keeps its own state-resolving
  dependency; no conflict.

### `tests/learner/test_wu2_api_composition.py` (new, 12 tests)

Covers: WU2 keys in the service graph; app-state assignment; deps getters;
single repository/database authority (all readers share the one Database
connection manager); bridge as a typed optional boundary with no second
store; Journey additive projections reachable through state and failing
closed with `LookupError` for unknown students; acknowledgement router in
`_BUSINESS_ROUTERS` exactly once; acknowledgement paths registered exactly
once with no duplicate path/method pairs in the composed app; bridge
fail-closed `core_review_service_missing` on both entry points;
acknowledgement POST fail-closed 503 when no evidence lookup is composed;
append-only GET returns an empty listing.

### `tests/test_composition_root.py` (additive only)

- `expected_keys` extended with `acknowledgement` and
  `practice_review_transfer` (the existing test pins the exact key set, so
  this additive assertion is required).
- One new additive test asserting the two WU2 services are assigned to app
  state.

## 3. TDD evidence (exact commands and counts)

All runs from `A:\EAP Agent Project\worktrees\learner` with the worktree
`.venv` and `PYTHONDONTWRITEBYTECODE=1`, `-p no:cacheprovider`.

Baseline before any D write (A/B/C already present):

```text
.\.venv\Scripts\python.exe -m pytest tests/learner/test_wu2_practice_review_evidence.py tests/learner/test_wu2_acknowledgement.py tests/learner/test_wu2_journey_history_transfer.py tests/test_composition_root.py tests/test_v095b_router_contract.py tests/test_v095d_api_contract.py tests/test_wave2_router_assembly.py -q --no-header -p no:cacheprovider
=> 137 passed, 1 failed (test_v095d_api_contract.py::test_endpoint_set_matches_runtime_and_is_fully_classified:
   PRE-EXISTING baseline failure: runtime 100 endpoints vs approved contract 81; not caused by D, not in D scope)
```

RED (new composition tests before implementation):

```text
.\.venv\Scripts\python.exe -m pytest tests/learner/test_wu2_api_composition.py -q --no-header -p no:cacheprovider
=> 9 failed, 3 passed (missing service keys, state attrs, deps getters, router registration)
```

GREEN after `main.py`/`deps.py` + additive `test_composition_root.py`:

```text
.\.venv\Scripts\python.exe -m pytest tests/learner/test_wu2_api_composition.py tests/test_composition_root.py -q --no-header -p no:cacheprovider
=> 17 passed, 2 warnings

.\.venv\Scripts\python.exe -m pytest tests/learner/test_wu2_practice_review_evidence.py tests/learner/test_wu2_acknowledgement.py tests/learner/test_wu2_journey_history_transfer.py tests/learner/test_wu2_api_composition.py -q --no-header -p no:cacheprovider
=> 121 passed, 2 warnings (40 + 51 + 18 + 12 focused WU2 tests)
```

Affected composition/router/Wave-2 suites:

```text
.\.venv\Scripts\python.exe -m pytest tests/test_composition_root.py tests/test_v095b_router_contract.py tests/test_v095d_api_contract.py tests/test_wave2_router_assembly.py -q --no-header -p no:cacheprovider
=> 28 passed, 2 failed:
   1) tests/test_v095b_router_contract.py::test_route_contract_pinned
      NEW (caused by the required acknowledgement router inclusion): the
      pinned EXPECTED_ROUTE_CONTRACT lacks the two acknowledgement pairs.
      Unowned file; not edited (BLOCKED item 2).
   2) tests/test_v095d_api_contract.py::test_endpoint_set_matches_runtime_and_is_fully_classified
      PRE-EXISTING baseline failure (100 vs 81 before D; 102 vs 81 after).
      Approved generated contract; not edited (BLOCKED item 2).
```

Existing practice/journey/learner regression:

```text
.\.venv\Scripts\python.exe -m pytest tests/test_v095f4_reanalysis_journey_narrowing.py tests/test_journey_v093c.py tests/test_v097b_wu6_journey_projection.py tests/test_v097c_wu1_journey_cycles.py tests/test_v097c_wu2_journey_navigation.py tests/test_v097c_wu4_release.py tests/learner -q --no-header -p no:cacheprovider
=> 396 passed, 2 warnings

.\.venv\Scripts\python.exe -m pytest tests/test_v097b_wu2_priority_mapping.py tests/test_v097b_wu3_target_creation.py tests/test_v097b_wu4_practice_task.py tests/test_v097b_wu5_completion.py tests/test_v095f2_service_narrowing.py tests/test_v095f3_learner_read_model_narrowing.py tests/test_v095f6c_submission_service_narrowing.py tests/test_v095f6d_practice_boundary_narrowing.py -q --no-header -p no:cacheprovider
=> 251 passed, 2 warnings
```

## 4. Route-registration and single-authority inspection (exact evidence)

```text
total_method_path_pairs: 102
duplicate_pairs: []
ack_pairs: [('GET', '/api/v1/students/{student_id}/acknowledgements'),
            ('POST', '/api/v1/students/{student_id}/acknowledgements')]
ack_registrations_in_business_routers: 1
single_database: True
practice_reader_is_writer: True
journey_projection_is_practice_reader: True
journey_student_is_student_lookup: True
shared_conn_mgr: True
bridge_core_is_none: True
ack_evidence_port_is_none: True
ack_store_type: _AppendOnlyAcknowledgementStore
journey_additive_methods: True True
```

One application, one process, one SQLite database (the composition-root
`Database`; every state reader shares its connection manager), one API
namespace, one composition root (`_build_services` + `_apply_service_state`).
No Migration 14/15 edit, no second scheduler, runtime, database, or
repository was introduced.

## 5. Changed files (owned scope only)

- `app/api/main.py` (modified: router registration, store glue, service
  graph keys, state assignment)
- `app/api/deps.py` (modified: two dependency getters)
- `tests/learner/test_wu2_api_composition.py` (new, 12 tests)
- `tests/test_composition_root.py` (additive key assertion + one additive
  test)
- `docs/integration/pdw3-wu2-learner-20260812/workers/D/findings.md` (this
  file)

No Worker A/B/C source or focused test, migration, infrastructure/repository,
UI, CORE, L2, UX, Academic, Corpus, Governance, INT, or Program Control file
was touched. `app/journey/service.py` remains exactly Worker B's additive
version (verified unchanged by D). HEAD remains `7a9e4b470c41c0453a3795233f1bdd5c483d80ae`.

## 6. BLOCKED items (unowned edits required; reported, not performed)

1. **Journey router route exposure.** Exposing Worker B's additive
   projections as API routes (`GET /api/v1/students/{student_id}/journey/
   practice-history` and `.../authentic-application`) requires editing
   `app/api/routers/journey.py`, which is outside this packet's owned write
   scope. The service-level exposure IS complete: the composed
   `app.state.journey_service` carries `get_practice_history` and
   `get_authentic_application` (callable, `LookupError` fail-closed), and
   the existing Journey router dependency (`get_journey_service`) resolves
   that same instance. The route surface addition is the unowned step.
2. **Route-contract pins for the acknowledgement router.** Including Worker
   C's router (required by the packet) grows the API surface by exactly two
   pairs; `tests/test_v095b_router_contract.py::test_route_contract_pinned`
   then fails (unowned, not edited). The approved generated contract
   (`tests/contracts/api_surface_contract.py` +
   `tests/test_v095d_api_contract.py`) is also unowned and was already
   failing at baseline (runtime 100 vs contract 81) before any D change;
   regenerating it (`verification/v0.9.5-d/build_contract.py`) is an
   approved cross-cutting process outside this packet. Neither file was
   edited.

## 7. Residual concerns / notes for INT

1. **Acknowledgement persistence is INT-gated.** The composed
   `AcknowledgementService` has no production evidence lookup
   (`evidence_port=None`), so POST always fails closed 503
   (`evidence_unavailable`, exact message: "No evidence lookup is composed;
   acknowledgement cannot verify learner ownership and admission.") and GET
   returns an empty append-only listing. Durable acknowledgement storage
   requires a migration (out of scope); the process-local placeholder store
   never receives data in this composition.
2. **CORE review integration is INT-gated.** The bridge is composed with
   `core_review_service=None`; any `record_practice_activity` /
   `record_review` call fails closed with `core_review_service_missing`
   before any write. INT injects the CORE `ReviewService` as-is per Worker
   A's handoff (`PracticeReviewTransferOrchestrator(core_review_service=...)`);
   no second store exists.
3. **Pre-existing red pin.** `test_v095d_api_contract.py` was failing at
   baseline (100 endpoints vs the approved 81-endpoint contract). D's change
   only moved the runtime count to 102; the contract regeneration decision
   belongs to the parent/INT.
4. **Journey additive projections** are composition-reachable but not yet
   route-exposed (BLOCKED item 1). The projected response keys, versions
   (`journey-practice-history-v0.9.7` /
   `journey-authentic-application-v0.9.7`), and `rating_channel_visibility`
   semantics are exactly Worker B's; no key was changed.

## 8. Resource hygiene

No commit, push, PR, merge, promotion, reset, clean, restore, rebase, or
Program Control write. No other worktree touched; no raw SWECCL access. All
pre-existing untracked LEARNER evidence paths and Worker A/B/C files remain
byte-preserved. HEAD re-verified `7a9e4b470c41c0453a3795233f1bdd5c483d80ae`.
