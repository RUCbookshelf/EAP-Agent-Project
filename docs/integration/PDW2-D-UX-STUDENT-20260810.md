# PDW2-D-UX-STUDENT - Wave-2 Goal D Report (UX)

Goal: Student Writing Experience v1 - real frontend journey integrating the
Wave-2 API contracts (revision / personalized / learner) with a local mock
client for tests and graceful degradation to the existing writing/feedback
flow while the Wave-2 endpoints land at integration.

| Field | Value |
| --- | --- |
| Goal ID | `PDW2-D-UX-STUDENT` |
| Owner | UX |
| Worktree | `A:\EAP Agent Project\worktrees\frontend` |
| Branch | `dept/frontend` |
| Starting SHA | `59500127ca2cf798ae730cee2a5a3e16707c320c` |
| Verdict | GREEN (functional + resource hygiene) |
| Promotion / push / PR | none (promotion authority false) |

## What was delivered (NEW files only; zero tracked modifications)

- `app/ui/wave2/` - additive Wave-2 module family:
  - `contracts.py` - documented endpoint paths and the student-internal
    allowlist policy (`STUDENT_INTERNAL_KEYS`).
  - `client.py` - `Wave2ApiClient` HTTP client for the Wave-2 endpoints with
    fail-closed availability classification (`Wave2ApiUnavailable` for
    connection/timeout and HTTP 404/405/503; `Wave2ApiClientError` for other
    4xx/5xx) and a cached `probe()`.
  - `mock.py` - `MockWave2Backend` (contract-shaped payloads, deterministic
    text-grounded detectors, scenarios `new_learner` / `returning_learner`)
    and `MockWave2Client` (available=False simulates the endpoints missing).
    Never fabricates history: insufficient-history states are first-class.
  - `views.py` - student-safe allowlist view mapping; the
    `FORBIDDEN_VIEW_KEYS` guard and view builders drop hashes, evidence
    refs, internal feature/record ids, epistemic-status codes, provenance
    and distribution internals before anything reaches a student surface.
  - `gateway.py` - `Wave2Gateway` UI facade: guided (Wave-2 contracts) with
    graceful degradation to the existing flow (`/api/v1/submissions`,
    journey, revision candidates) when the Wave-2 namespace is unavailable.
  - `locale.py` - Wave-2 strings (en + zh_CN) registered additively into the
    app locale at import; the frozen locale JSON files are untouched.
  - `journey.py` - the real Streamlit studio journey renderer:
    start -> task/context -> task prompt -> compose -> submit -> feedback
    (what / why / what to try / have I seen this before / what stayed
    similar) -> scaffold (SCAFFOLD FIRST, progressive 1-7) -> revise ->
    resubmit -> revision result (improved / still present / new) with
    history navigation.
  - `history.py` - the real Streamlit history renderer: task/context,
    submission/revision sequence, prior feedback summaries, longitudinal
    observations (difficulties / strengths / stable / declared anchors),
    LearningItems with next-learning suggestions.
- `tests/wave2/` - 69 focused tests: mock contract shapes + scenario
  behavior, HTTP client routes/classification, gateway fallback modes,
  view allowlist/no-internals, and AppTest journey tests for CASE A-F.
- `tests/harness_wave2_studio.py` - AppTest harness (repo convention, e.g.
  harness_v097a_student.py) driving the real renderers with a scripted
  gateway; the mock backend persists in session state across reruns.

## Wave-2 contract integration

The UI talks only to `Wave2Gateway`, which maps to the documented contracts:

- revision: `POST /api/v1/wave2/revision/tasks`,
  `POST .../tasks/{id}/submissions` (V1),
  `POST .../submissions/{id}/revisions` (V2), `GET .../tasks/{id}/versions`,
  `GET .../tasks/{id}/versions/{sid}/observation`.
- personalized: `POST /api/v1/wave2/personalized/priority-plan`,
  `POST /api/v1/wave2/personalized/scaffold`,
  `GET|POST /api/v1/wave2/personalized/learning-items`,
  `PATCH .../learning-items/{id}`.
- learner: `GET /api/v1/wave2/learner/{observations,difficulties,strengths,
  stable,proficiency-context,evidence}`.

Because the backend Wave-2 modules land at integration, tests use the mock
client; `Wave2ApiClient` is the real HTTP client the gateway uses against
the live app. When the Wave-2 namespace is unavailable (probe fails closed),
the same journey degrades to the existing writing/feedback flow and shows an
honest standard-mode notice; it never fabricates Wave-2 features (scaffold
engine and guided comparisons are explicitly marked unavailable).

## Student surface rules enforced

- what to revise / why / what to try / have I seen this before (recurrence
  phrase) / what improved or stayed stable / what to learn next.
- No raw technical internals by default: hashes, reference-group N,
  distribution internals, artifact paths, epistemic-status codes,
  provenance JSON, and internal feature/record ids are filtered by the view
  allowlist and asserted absent from rendered UI.
- Progressive disclosure: evidence quotes sit behind expanders; scaffold
  hints reveal one level at a time (SCAFFOLD FIRST, 7 levels); no full
  essay is ever written for the learner.
- Responsive/accessibility foundations preserved: only new components using
  the existing pixel-art design system (`app/ui/components.py`); no redesign
  of existing surfaces.

## CASE demonstrations (Streamlit AppTest, real renderers)

- CASE A new learner first submission without fabricated history: PASS -
  plan items show "This is new in this draft." + insufficient-history
  notice; no historical-pattern section; history page shows honest empty
  states.
- CASE B revise and resubmit: PASS - revision box prefilled with the
  learner's own text; result shows what changed, improved areas, still-
  present areas and the no-intent-inference note; V2 append-only.
- CASE C returning learner sees historical feedback and priority plan: PASS
  - "Patterns from your earlier writing" with recurring status and
  historical summary.
- CASE D expand scaffold and revise: PASS - hint 1/7 -> next hint 2/7 ->
  close help -> revise -> resubmit -> result.
- CASE E inspect history and LearningItems: PASS - tasks with version
  sequence, feedback summaries, longitudinal difficulties/strengths/stable,
  learning items with status labels, declared proficiency anchor.
- CASE F fail-closed / insufficient-evidence states understandable to a
  student: PASS - standard-mode degradation banner and honest
  scaffold/result notes; new-learner history empty states with plain
  language.

## Test evidence

- `tests/wave2` 69 passed (0 failed): mock contract shapes and scenarios,
  HTTP client routes and availability classification, gateway fallback,
  view allowlist / no-internals, AppTest journey CASE A-F.
- Existing student UI suites (quick verification): test_streamlit.py 5
  passed/1 skipped; test_ui_api_client_v02, test_student_experience_v094b,
  test_v095c_ui_boundaries, test_v097d_design_system (design tokens),
  test_v097c_wu3_journey_ui combined 94 passed/1 skipped; contracts
  test_wave1_domain_isolation + test_v097c_wu2_journey_navigation +
  test_v097a_priority_revision_cycle 61 passed. No regressions observed.
  (The full canonical suite was not run per Program instruction.)

## Resource hygiene

- Zero tracked modifications (`git diff --stat` empty).
- Only new files added; pre-existing untracked evidence preserved
  byte-identically (PDW1-ALIGN-UX-B6FCE9-20260809.md,
  PDW2-ALIGN-UX-59500127-20260810.md, UX-V097-E-accessibility-refinement.md,
  handoff.json).
- No backend modules touched; no reset/clean/rebase/push/PR/promotion.
- No raw SWECCL access; no API keys; no network calls in tests (mock).

## Integration wiring (INT at integration time)

1. Mount the two student pages in `app/ui/streamlit_app.py`:
   `STUDENT_PAGES` entries `student_wave2_studio` /
   `student_wave2_history` with locale keys
   `student_wave2_studio_title` / `student_wave2_history_title`, and route
   them to `render_wave2_studio_page(gateway, lang)` /
   `render_wave2_history_page(gateway, lang)`.
2. Build the gateway once per app: `Wave2Gateway(Wave2ApiClient(base_url),
   WritingFeedbackApiClient(base_url), mode="auto")` (mode "auto" probes the
   Wave-2 namespace once).
3. Optional: fold `app/ui/wave2/locale.py` strings into `locales/*.json`
   (the runtime registration keeps working either way).
4. Optional: add a Home entry card using the `student_home_wave2_*` strings.

## Findings / limitations

- Studio session state (`wave2_*` keys) is session-local; it is not yet
  wired into `student_context.LEARNER_SCOPED_KEYS` (learner switching
  mid-journey is handled by starting a new task; a follow-up can add the
  keys to the shared learner-scope list).
- The mock backend's text scan is deliberately tiny and deterministic; it
  exists for tests/demos and is replaced by the real pipeline at
  integration (the UI contract does not change).
- `history()` in guided mode assembles tasks from LearningItems' task
  references plus in-session tasks, because the v1 contract has no
  learner-task listing endpoint; INT may add a listing endpoint or persist
  tasks at integration.
