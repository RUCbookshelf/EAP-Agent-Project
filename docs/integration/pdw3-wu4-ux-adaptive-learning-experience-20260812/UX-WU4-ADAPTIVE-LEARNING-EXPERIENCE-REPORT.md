# UX Wave-3 WU4 Adaptive Learning Experience — Department Report

| Field | Value |
| --- | --- |
| Goal | `PDW3-WU4-UX-ADAPTIVE-LEARNING-EXPERIENCE-20260812` |
| Run | `PDW3-WU4-UX-ADAPTIVE-LEARNING-EXPERIENCE-20260812__20260812T122731Z__d6ed5d` |
| Owner / Executor | [UX] Frontend & Product Experience — bounded executor (opencode-go/deepseek-v4-flash, ultra, PLANNING_DISABLED=1) |
| Authorized worktree | `A:\EAP Agent Project\worktrees\frontend` |
| Authorized branch | `dept/frontend` |
| Starting / final SHA | `7a9e4b470c41c0453a3795233f1bdd5c483d80ae` (unchanged; no commit) |
| Verdict | GREEN (department scope; handoff `HANDOFF_PENDING_ACCEPTANCE`) |
| Report timestamp | 2026-08-12 |

## 1. Scope executed

Additive Wave-3 WU4 student adaptive learning experience over the existing
real frontend architecture and the accepted L2 WU3 API contract, inside the
packet write scope only:

- `app/ui/wave2/contracts.py` — the eight WU3 endpoint constants exactly as
  defined by the accepted L2 WU3 contract, plus the WU3 raw-internal fields
  added to the student-facing allowlist policy
  (`STUDENT_INTERNAL_KEYS`).
- `app/ui/wave2/client.py` — eight WU3 client methods with exact POST
  paths/payloads and the existing fail-closed availability classification.
- `app/ui/wave2/gateway.py` — student-safe WU3 view adapters over the
  accepted payloads (allowlist only; raw target codes, evidence ids,
  scheduler internals, version labels, provenance ids never pass through),
  with graceful degradation when the Wave-2/WU3 namespace is unavailable.
- `app/ui/features/student/adaptive.py` — the new Today/adaptive student
  page: deterministic recommendation + explicit learner choice + qualified
  activity + practice attempt + deterministic evaluation + bounded
  session-local self-rating + next-step + consented Tutor
  (recommend/accept/decline/observation) + bounded mini-writing handoff
  into the real pipeline + honest insufficient-history/unavailable states.
- `app/ui/pages/student_pages.py` — thin export of the new renderer.
- `app/ui/streamlit_app.py` — student navigation/wiring for the new
  Today page.
- `locales/en.json` + `locales/zh_CN.json` — 63 new keys each, parity
  668/668.
- `tests/test_wave3_wu4_adaptive_ux.py` + `tests/harness_wu4_adaptive.py`
  — TDD-focused WU4 tests (red phase captured first).
- `tests/test_v095c_feature_extraction.py` — STUDENT_PAGES order pin
  updated for the new page.
- `tests/test_v097d_design_system.py` + `tests/test_v097d_wu2_revision_practice.py`
  — locale parity count pins updated 605 -> 668 for the 63 WU4 keys.
- `docs/integration/pdw3-wu4-ux-adaptive-learning-experience-20260812/` —
  this report + the canonical handoff JSON.
- `verification/pdw3-wu4-ux-adaptive-learning-experience-20260812/` —
  verifier evidence (pytest logs, rendered matrix evidence, screenshots,
  git-status snapshots, route-pin log).

No CORE, LEARNER, L2, INT, API, migration, database, `app/l2/`,
`app/learner/`, `app/database/`, `app/infrastructure/`, `app/services/`,
`app/ui/wave2/views.py`, Program Control, or any pre-existing
dirty/untracked file was modified. The six pre-existing untracked UX
evidence paths and `handoff.json` are preserved.

## 2. Acceptance gate mapping

1. **Coherent Today/home flow** — the new Today page renders the loop
   recommendation -> explicit choice -> practice attempt -> deterministic
   evaluation -> bounded self-rating -> next-step -> consented Tutor ->
   mini-writing/continued writing in the existing Streamlit student shell
   with the frozen v0.9.7-D component recipes (no new tokens/CSS).
2. **Real WU3 endpoints used exactly** — client constants/methods pin the
   eight accepted endpoints verbatim
   (`/api/v1/wave2/personalized/adaptive-practice/{recommend,select,evaluate}`,
   `/mini-writing`, `/tutor/{recommend,accept,decline,observation}`); no
   invented or altered endpoint.
3. **Deterministic recommendation + learner choice + honest states** — the
   recommendation view carries deterministic reasons and the full qualified
   subset with a default; explicit choice is exercised; alternate qualified
   activity is always visible; insufficient-history and unavailable states
   are first-class and honest; raw internals are dropped by the gateway
   allowlist (target codes, evidence ids, scheduler ids, version labels,
   provenance ids, hashes) and guarded by tests.
4. **Explicit consent before Tutor execution; decline side-effect safe** —
   the Tutor section requires a visible consent checkbox with the exact
   accepted scope/version (`proactive_tutor_execution`,
   `learner-consent-v0.1.0`) before accept; decline calls the decline
   endpoint only; due-item / history-grounded / positive-observation /
   insufficient-history / unavailable cases render bounded observational
   wording.
5. **Preserve existing behavior; graceful degradation; learner isolation;
   pending guards; zero writes on read-only render** — existing pages are
   untouched; unavailable Wave-2/WU3 returns honest `{"available": False}`
   states; adaptive session state is cleared on learner switch; a pending
   guard blocks duplicate submit; read-only renders make no write-method
   calls and the rendered matrix verifies zero DB writes on render/reload.
6. **Locale parity + design-system/accessibility/responsive + no
   console/page/remote errors** — 668/668 parity; frozen recipes reused;
   rendered matrix en/zh x 1280x900/390x844 all clean with zero errors,
   overflow, raw keys, forbidden wording, or remote requests.
7. **TDD-focused tests** — see section 3 (red phase captured, then green).
8. **Focused + affected regression + rendered matrix** — exact commands,
   counts, exit codes in section 4; resource hygiene in section 6;
   integration dependency in section 5.
9. **Handoff** — this report + schema-valid handoff JSON under the
   authorized docs path; verifier evidence under the authorized
   verification path.

## 3. Test matrix (focused WU4 suite — TDD)

| File | Coverage | Result |
| --- | --- | --- |
| `tests/test_wave3_wu4_adaptive_ux.py` | WU3 endpoint constants exact (8 POST paths); allowlist-policy additions; client exact paths/payloads + fail-closed classification (404/405/503 -> unavailable, other -> client error); gateway student-safe views (recursive no-internal-keys guard); graceful degradation (unavailable Wave-2 + legacy mode); learner isolation; insufficient-history view; selection/evaluation/mini-writing/tutor views; AppTest rendering of recommendation/choice/evaluation/self-rating/next-step; Tutor consent accept/decline/insufficient/positive; mini-writing handoff with/without session task; Today->Journey/Practice navigation; zero writes on read-only render; en/zh locale parity; no forbidden wording | PASS |
| `tests/harness_wu4_adaptive.py` | AppTest harness for the Today page with a scripted gateway mirroring the real gateway view shapes | PASS (used by the suite above) |

Red phase was captured before implementation: the suite failed at
collection with `ImportError: cannot import name 'ADAPTIVE_PRACTICE_EVALUATE'`
(`basetemp-red`); after implementation the suite is green.

## 4. Verification runs (exact commands, counts, exit codes)

All commands run from `A:\EAP Agent Project\worktrees\frontend` with the
branch-local `.venv` (Python 3.12.13, pytest 9.1.1). `-p no:cacheprovider`
and an explicit basetemp under the authorized verification path were used
because the shared pytest temp root is not writable in this sandbox
(environment limitation, not a product defect).

| Suite | Command (abridged) | Count | Exit |
| --- | --- | --- | --- |
| Focused WU4 | `pytest tests/test_wave3_wu4_adaptive_ux.py` | 47 passed | 0 |
| Affected v0.9.7-C/D + contracts | `pytest tests/test_v095c_feature_extraction.py tests/test_v095d_port_contract.py tests/test_hybrid_components_v094a.py tests/test_design_tokens_v094a.py tests/test_v097d_design_system.py tests/test_v097d_wu1_writing_feedback.py tests/test_v097d_wu2_revision_practice.py tests/test_v097c_wu1_journey_cycles.py tests/test_v097c_wu2_journey_navigation.py tests/test_v097c_wu3_journey_ui.py tests/test_v097c_wu4_release.py` | 262 passed | 0 |
| Wave-2 + Practice/Journey + student UI | `pytest tests/test_wave2_l2_api.py tests/test_wave2_l2_personalized.py tests/test_wave2_l2_models.py tests/test_wave2_l2_repository.py tests/test_wave2_l2_repository_consume.py tests/test_wave2_l2_revision_loop.py tests/test_wave2_l2_corpus_routing.py tests/test_wave2_router_assembly.py tests/test_v095d_parity.py tests/test_student_experience_v094b.py tests/test_streamlit.py tests/test_streamlit_api_integration_v02.py tests/test_ui_api_client_v02.py tests/test_v096c1_no_priority_workflow.py tests/harness_wave2_studio.py tests/test_v097b_wu4_practice_task.py tests/test_v097b_wu5_completion.py tests/test_v097b_wu6_journey_projection.py tests/test_journey_v093c.py tests/test_practice_v09.py tests/test_v095f6d_practice_boundary_narrowing.py tests/test_v095f6a0_revision_capability_completion.py` | 336 passed / 3 skipped | 0 |
| Route-surface pin (pre-existing INT-owned) | `pytest tests/test_v095d_api_contract.py` | 8 passed / 1 failed | 1 |
| Rendered locale/viewport matrix | `python verification/.../wu4_browser_matrix.py` (real stack, chromium-1234 explicit executable) | en/zh x 1280x900/390x844 all PASS; 0 exceptions/overflow/raw keys/forbidden wording/console/page/remote errors; honest degraded state; zero writes on render/reload | 0 |
| Whole-app boot | AppTest boot of `streamlit_app.py` -> sidebar -> Today renders | PASS | 0 |

The one route-pin failure
(`test_v095d_api_contract.py::test_endpoint_set_matches_runtime_and_is_fully_classified`,
`assert 100 == 81`) is the documented, pre-existing INT-owned
cross-cutting route/endpoint pin: the merged Wave-2 master surface is 100
route pairs while the v0.9.5-D pin file still pins 81. The accepted LEARNER
WU2 handoff and the L2 WU3 handoff record the identical dependency
("INT regeneration/qualification of the unowned cross-cutting route-contract
pins at the WU5 gate"). This executor did not touch `app/api/`, `app/l2/`,
or any INT-owned pin file; the runtime surface is unchanged by WU4.

## 5. Integration dependency

- INT regenerates/qualifies the unowned cross-cutting route-contract pins
  (including `tests/test_v095d_api_contract.py`) at the WU5 consolidated
  gate; the WU4 delta is UI-only and does not change the API surface.
- INT composition-root injection of the real CORE ReviewService and LEARNER
  consent persistence remains an L2/INT WU5 item; until then the WU3
  endpoints are not reachable in this frontend worktree and the Today page
  renders its honest degraded/unavailable states (verified in the rendered
  matrix), exactly as the packet requires.
- Exact-SHA promotion decision remains WAITING_USER; no promotion authority
  was granted.

## 6. Resource hygiene

- HEAD unchanged `7a9e4b470c41c0453a3795233f1bdd5c483d80ae`; no
  commit/stage/push/PR/merge/promotion/reset/clean/restore/rebase.
- Git status delta is limited to: modified
  `app/ui/wave2/{client,contracts,gateway}.py`,
  `app/ui/pages/student_pages.py`, `app/ui/streamlit_app.py`,
  `locales/en.json`, `locales/zh_CN.json`, and the three pinned test files;
  new `app/ui/features/student/adaptive.py`, `tests/harness_wu4_adaptive.py`,
  `tests/test_wave3_wu4_adaptive_ux.py`,
  `docs/integration/pdw3-wu4-ux-adaptive-learning-experience-20260812/`,
  and `verification/pdw3-wu4-ux-adaptive-learning-experience-20260812/`.
- All six pre-existing untracked UX evidence paths (five docs + the
  tracked-exempt `handoff.json`) are preserved (initial vs final status; 0
  missing).
- No Program Control write; no other worktree touched; no raw SWECCL
  access; no second runtime/database/connection manager; no migration.
- pytest basetemp routed to the authorized verification path; transient
  SQLite files confined to those temp roots.

## 7. Findings

- The WU3 client/gateway surface is additive and bounded: eight exact
  endpoints, student-safe allowlisted views, fail-closed classification,
  and graceful degradation; no backend semantic is redefined.
- The Today page is real-API-backed over the accepted WU3 contract: every
  interaction (recommend/select/evaluate/mini-writing/tutor
  recommend/accept/decline/observation) maps to the exact endpoint; honest
  unavailable/insufficient-history states are first-class and tested.
- Tutor execution is consent-gated with a visible explicit checkbox using
  the exact accepted scope/version; decline is side-effect safe and tested;
  positive observations carry bounded non-causal wording.
- Rendered matrix (en/zh x 1280x900/390x844) is clean: zero exceptions,
  overflow, raw keys, forbidden wording, console/page/remote errors, and
  zero DB writes on render/reload.
- The only non-green item is the pre-existing INT-owned route-surface pin
  whose runtime delta (100 vs 81) predates WU4 and matches the accepted
  LEARNER WU2 / L2 WU3 precedent (INT regeneration at WU5).

## 8. Final decision

Department-scope GREEN for WU4: focused (47/47) and affected
v0.9.7-C/D + Wave-2 + Practice/Journey regressions (262 + 336) are green,
the rendered locale/viewport matrix passes, resource hygiene is clean, and
the sole non-green item is the pre-existing INT-owned route-pin file whose
delta is unchanged by WU4. DEPARTMENT GREEN is not INTEGRATION GREEN or
promotion; no promotion authority was granted. Handoff remains
`HANDOFF_PENDING_ACCEPTANCE`.
