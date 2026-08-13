# L2 Wave-3 WU3 Adaptive Practice + Proactive Tutor — Department Report

| Field | Value |
| --- | --- |
| Goal | `PDW3-WU3-L2-ADAPTIVE-PRACTICE-TUTOR-20260812` |
| Run | `PDW3-WU3-L2-ADAPTIVE-PRACTICE-TUTOR-20260812__20260812T104641Z__d847d9` |
| Owner / Executor | [L2] L2 Writing — bounded executor (opencode-go/deepseek-v4-flash, ultra, PLANNING_DISABLED=1) |
| Authorized worktree | `A:\EAP Agent Project\worktrees\l2-writing` |
| Authorized branch | `dept/l2-writing` |
| Starting / final SHA | `7a9e4b470c41c0453a3795233f1bdd5c483d80ae` (unchanged; no commit) |
| Verdict | GREEN (department scope; handoff `HANDOFF_PENDING_ACCEPTANCE`) |
| Report timestamp | 2026-08-12 |

## 1. Scope executed

Additive Wave-3 WU3 L2 domain over the existing shared application
contracts, inside the packet write scope only:

- `app/l2/wave3/` — new WU3 domain: models, narrow CORE/LEARNER consumer
  protocols, `AdaptivePracticeService`, `MiniWritingService`,
  `ProactiveTutorService`, and branch-local adapters (in-memory, test-only).
- `app/api/routers/wave2_modules/personalized_api.py` — L2-owned WU3
  endpoints only; every existing WU2 route and contract preserved unchanged.
- `tests/wave3/` + `tests/test_wave3_l2_adaptive_practice_tutor.py` — new
  TDD-focused tests (red first, then green).
- `docs/integration/pdw3-wu3-l2-adaptive-practice-tutor-20260812/` — this
  report + the canonical handoff JSON.
- `verification/pdw3-wu3-l2-adaptive-practice-tutor-20260812/` — verifier
  evidence (pytest logs, git status snapshots, route-delta facts, probe).

No CORE, LEARNER, INT, UX, migration, `app/database/`,
`app/infrastructure/`, `app/review/`, `app/learner/`, `app/corpus/`,
`app/services/`, `app/ui/`, `app/api/main.py`, `app/api/routers/wave2.py`,
Program Control, or any pre-existing dirty/untracked file was modified.

## 2. Acceptance gate mapping

1. **Qualified activity subset + deterministic default + learner choice** —
   `AdaptivePracticeService.recommend()` selects the qualified subset from
   the EXISTING practice capability (`app.practice` exercise specs: rule
   based + student-eligible only) using a deterministic, explainable
   default (stored plan order, then exercise-spec order) with explicit
   learner choice via `select()`.
2. **Provenance / evaluation criteria preserved; never fabricated** — every
   `QualifiedActivity` carries source submission id, evidence ids,
   evaluation criteria (method/version/completion/observable-target), and
   `claims_status=observation_only`; learners without stored evidence get an
   honest `insufficient_history` state with no fabricated activities.
3. **Existing Writing Intelligence pipeline reuse (production + mini-writing)**
   — `MiniWritingService` re-enters the real pipeline through
   `RevisionLoopService.submit_v1`/`WritingPipelinePort`; no disconnected
   analysis or essay-generation service exists.
4. **Bounded Tutor orchestration contract** — `ProactiveTutorService`
   covers recommendation, learner accept, learner decline,
   due-item/history-grounded suggestion, insufficient-history, and
   positive-observation cases.
5. **Explicit consent before Tutor execution; decline/unavailable
   side-effect safe** — `accept()` requires a granted, non-revoked,
   correctly scoped/versioned, learner-matching, non-future consent
   (`TutorConsentSnapshot`); `decline()` and unavailable states perform no
   execution, no consent write, no practice/review write.
6. **Practice/review evidence vs authentic-writing observation** —
   `PositiveObservation.evidence_kind=authentic_writing` is distinct from
   practice activity records; all outputs carry non-causal, descriptive
   language and pass the shared `NormativeClaimsScanner` strict scan.
7. **One application/process/SQLite/API/composition root; consume
   CORE/LEARNER WU2 contracts without copying/editing** — the L2 branch does
   not physically contain the CORE/LEARNER WU2 product code, so narrow
   structural protocols (`ReviewEvidencePort`, `LearnerConsentStorePort`)
   mirror the accepted record/service surfaces; INT injects the real CORE
   ReviewService and LEARNER consent persistence behind them at the
   consolidated Wave-3 gate. No second store/scheduler/database/runtime.
8. **TDD-focused tests** — see the test matrix in section 3 (red phase
   captured, then green).
9. **Focused + affected regression** — exact commands/counts/exit codes in
   section 4; resource hygiene in section 6; integration dependency in
   section 5.
10. **Handoff** — this report + schema-valid handoff JSON under the
    authorized docs path; verifier evidence under the authorized
    verification path.

## 3. Test matrix (focused WU3 suite — TDD)

| File | Coverage | Result |
| --- | --- | --- |
| `tests/wave3/test_wave3_models.py` | model contracts, provenance, consent fail-closed, no-normative payloads | PASS |
| `tests/wave3/test_adaptive_practice.py` | deterministic default + reasons, learner choice, qualified subset, provenance, insufficient-history, deterministic evaluation | PASS |
| `tests/wave3/test_mini_writing.py` | real-pipeline reuse, bounded length, ownership, provenance | PASS |
| `tests/wave3/test_tutor.py` | history-grounded, insufficient-history, due-item, positive observation, consent accept/decline, learner isolation | PASS |
| `tests/wave3/test_isolation.py` | learner isolation, failure isolation | PASS |
| `tests/wave3/test_prohibited_claims.py` | strict output scans + WU3 source scan | PASS |
| `tests/test_wave3_l2_adaptive_practice_tutor.py` | root-level composition-aware router contract tests (recommend/select/evaluate/mini-writing/tutor endpoints) | PASS |

Red phase was captured before implementation: the suite failed at
collection with `ModuleNotFoundError: No module named 'app.l2.wave3...'`
(`basetemp-red`); after implementation the same suite is green.

## 4. Verification runs (exact commands, counts, exit codes)

All commands run from `A:\EAP Agent Project\worktrees\l2-writing` with the
branch-local `.venv` (Python 3.12.13, pytest 9.1.1, fastapi 0.135.2,
pydantic 2.13.4, sqlite3 3.53.1). `-p no:cacheprovider` and an explicit
basetemp under the authorized verification path were used because the
shared pytest temp root is not writable in this sandbox (environment
limitation, not a product defect).

| Suite | Command (abridged) | Count | Exit |
| --- | --- | --- | --- |
| Focused WU3 | `pytest tests/wave3/ tests/test_wave3_l2_adaptive_practice_tutor.py` | 70 passed | 0 |
| Affected Wave-2/L2 | `pytest tests/wave2/ tests/test_wave2_l2_api.py ... tests/test_wave2_l2_repository_consume.py tests/test_wave2_migration_v14.py tests/test_wave2_repositories_v14.py tests/test_wave2_repository_composition.py tests/harness_wave2_studio.py` | 172 passed | 0 |
| Practice/Journey regression | `pytest tests/test_composition_root.py tests/test_practice_v09.py tests/test_v095f6d_practice_boundary_narrowing.py tests/test_v097b_wu2_priority_mapping.py tests/test_v097b_wu3_target_creation.py tests/test_v097b_wu4_practice_task.py tests/test_v097b_wu5_completion.py tests/test_v097b_wu6_journey_projection.py tests/test_journey_v093c.py` | 278 passed | 0 |
| Learner/History regression | `pytest tests/test_learner_model_v07.py tests/test_learner_model_task_type_v1.py tests/test_history.py tests/test_longitudinal_v03.py tests/test_revision_v05.py` | 63 passed | 0 |
| Wave-adjacent regression | `pytest tests/test_v097c_wu1_journey_cycles.py tests/test_v097c_wu2_journey_navigation.py tests/test_v097c_wu3_journey_ui.py tests/test_v097d_wu1_writing_feedback.py tests/test_v097d_wu2_revision_practice.py tests/test_v095f6a0_revision_capability_completion.py tests/test_v095f6d_practice_boundary_narrowing.py` | 177 passed | 0 |
| Route-surface pins (expected delta) | `pytest tests/test_wave2_router_assembly.py tests/test_v095b_router_contract.py tests/test_v095d_api_contract.py` | 18 passed / 7 failed | 1 |
| Composition fail-closed probe | python probe (503 without composition; 200 composed) | PROBE_OK | 0 |

The 7 route-pin failures are the documented, expected consequence of the
authorized additive WU3 endpoints (see section 5). All other affected
regression is green.

## 5. Route surface and integration dependency

The L2 packet authorizes "L2-owned WU3 endpoints only" in
`personalized_api.py`. Eight WU3 endpoints were added:

```
POST /api/v1/wave2/personalized/adaptive-practice/recommend
POST /api/v1/wave2/personalized/adaptive-practice/select
POST /api/v1/wave2/personalized/adaptive-practice/evaluate
POST /api/v1/wave2/personalized/mini-writing
POST /api/v1/wave2/personalized/tutor/recommend
POST /api/v1/wave2/personalized/tutor/accept
POST /api/v1/wave2/personalized/tutor/decline
POST /api/v1/wave2/personalized/tutor/observation
```

Verified (`route-delta-facts.json`): the wave2 sub-router surface grows from
the 19 pinned pairs to 27; the 19 pre-existing pairs are preserved exactly
(`preserved_baseline: true`, `missing_from_baseline: []`), the added set is
exactly the 8 WU3 routes (`wu3_routes_exact: true`), and there is zero
unexpected delta. Full-app census (`full-app-route-census.json`): the L2
candidate surface is 108 route pairs vs the master baseline of 100, with a
delta of exactly +8 (the WU3 routes) and no other change.

The three route-surface pin files (`tests/test_wave2_router_assembly.py`,
`tests/test_v095b_router_contract.py`, `tests/test_v095d_api_contract.py`)
pin the exact merged route/endpoint surface and therefore fail on the L2
candidate with a delta limited to the authorized WU3 routes. This is the
same situation recorded by the accepted LEARNER WU2 handoff, whose
`dependencies_remaining` names "INT regeneration/qualification of the
unowned cross-cutting route-contract pins". INT regenerates/qualifies these
pins at the consolidated Wave-3 integration gate (WU5). The L2 candidate
does not edit INT-owned pins.

Additional integration dependency: the real CORE ReviewService and LEARNER
consent persistence are injected behind the WU3 narrow protocols
(`ReviewEvidencePort`, `LearnerConsentStorePort`) by the INT composition
root at the consolidated gate; branch-local in-memory adapters are test-only
and never become a second store/scheduler.

## 6. Resource hygiene

- HEAD unchanged `7a9e4b470c41c0453a3795233f1bdd5c483d80ae`; no
  commit/stage/push/PR/merge/promotion/reset/clean/restore/rebase.
- Git status delta is limited to: modified
  `app/api/routers/wave2_modules/personalized_api.py`, new `app/l2/wave3/`,
  new `tests/wave3/`, new `tests/test_wave3_l2_adaptive_practice_tutor.py`,
  new `docs/integration/pdw3-wu3-l2-adaptive-practice-tutor-20260812/`,
  and new `verification/pdw3-wu3-l2-adaptive-practice-tutor-20260812/`.
- All 25 pre-existing untracked L2 evidence paths preserved (initial vs
  final status; 0 missing).
- No Program Control write; no other worktree touched; no raw SWECCL
  access; no second runtime/database/connection manager.
- pytest basetemp routed to `verification/.../basetemp-*` (authorized write
  scope); transient SQLite files from tests are confined to those temp
  roots inside the authorized verification path.

## 7. Findings

- The WU3 domain is additive and bounded: one composition root, one API
  namespace, one SQLite family, no new migration, no second runtime.
- Deterministic recommendation default and learner choice are both
  exercised; provenance and deterministic rule-based evaluation criteria
  are preserved on every activity; no evidence is fabricated.
- Mini-writing re-enters the real Writing Intelligence pipeline; the
  service never generates an essay and enforces a bounded length.
- Tutor execution requires explicit learner consent; decline and
  unavailable states are side-effect safe; all composed outputs pass the
  shared no-normative-claims strict scan.
- The only non-green items are the three INT-owned route-surface pin files
  whose expected delta is exactly the 8 authorized WU3 routes (INT
  regeneration at WU5, matching the accepted LEARNER WU2 precedent).

## 8. Final decision

Department-scope GREEN for WU3: all focused and affected regression is
green, resource hygiene is clean, and the sole integration dependency
(route-pin regeneration + real CORE/LEARNER injection at the consolidated
Wave-3 gate) is recorded explicitly. DEPARTMENT GREEN is not INTEGRATION
GREEN or promotion; no promotion authority was granted. Handoff remains
`HANDOFF_PENDING_ACCEPTANCE`.
