

## 2026-08-02 - v0.9.5-F6C SubmissionService persistence dependency narrowing

- **Decision**: Remove the broad, inherited `SubmissionRepository` dependency
  from the active `SubmissionService` constructor and runtime state and
  replace it with four owner-aligned consumer-owned Ports
  (`SubmissionSystemPort` 1 method, `SubmissionDataPort` 5 methods,
  `SubmissionAnalysisPort` 3 methods, `SubmissionCalibrationPort` 2 methods);
  remove both CALF persistence `hasattr` capability guards; make
  `build_submission_service` require seven keyword-only facade-owned
  repositories with no broad-facade fallback. Every active caller supplies
  the existing facade-owned System/Submission/Analysis/CALF/Learner/
  Configuration/Revision instances.
- **Rationale**: The submission orchestrator should receive only the exact
  repository capabilities it calls; production always supplies the
  `SQLiteCalfRepository`, so capability discovery via `hasattr` is dead
  conditional logic; the factory no longer needs the broad facade as a
  fallback once every caller passes the explicit graph.
- **Parity boundary**: Legacy `SubmissionRepository` declaration retained as
  Protocol-consolidation debt (removal deferred); central Repository
  Protocols, Repository implementations, SQL, transactions (per-method
  commits and the three-sequential-commit Revision workflow unchanged),
  migration 12, 33 tables, `config-v0.9.0`, prompt `feedback-prompt-v0.7.1`,
  API 77 pairs, client 52 methods, locale 520/520, and facade 86 methods
  unchanged. No adapter, proxy, Service Locator, Unit of Work, shared
  transaction, compensation, or retry.
- **Evidence**: focused 282 PASS; accumulated contracts 233 PASS; full
  non-live core 618 passed + 8 skipped; exact `run.bat --verify` PASS;
  development database unchanged (SHA-256/size/mtime).
- **Boundary**: v0.9.5-F6D Practice write-boundary work may begin only under
  a separate authorization; facade contraction and Protocol consolidation
  remain deferred.

## 2026-08-02 - v0.9.5-F6B AdminReanalysisService persistence dependency narrowing

- **Decision**: Remove the broad, untyped `repository` parameter from
  `AdminReanalysisService` and replace it with three consumer-owned
  structural Ports (`AdminConfigurationReadPort` one read,
  `AdminSubmissionReadPort` two reads, `AdminAnalysisPort` read + write)
  plus the existing required keyword-only `revision_repository:
  RevisionRepository`. Both application-construction paths supply the
  existing facade-owned repository instances.
- **Rationale**: The orchestrator should receive only the exact repository
  capabilities it calls; the F6A `revision_repository` remains the single
  Revision dependency (direct `get_revision_group` read plus embedded
  `RevisionService` backing).
- **Parity boundary**: Central `RevisionRepository`, `RevisionService`,
  `SubmissionService`, `ConfigurationService`, Repository implementations,
  SQL, transactions (three-sequential-commit workflow and per-method
  commits unchanged), migration 12, 33 tables, `config-v0.9.0`, prompt
  `feedback-prompt-v0.7.1`, API 77 pairs, client 52 methods, locale 520/520,
  and facade 86 methods unchanged. No combined Admin repository, adapter,
  proxy, Service Locator, Unit of Work, or DI framework.
- **Evidence**: focused 154 PASS; accumulated contracts 204 PASS; full
  non-live core 589 passed + 8 skipped; exact `run.bat --verify` PASS;
  development database unchanged (SHA-256/size/mtime).
- **Boundary**: v0.9.5-F6C SubmissionService narrowing may begin only under
  a separate authorization; F6D and later stages remain unstarted.

## 2026-08-02 - v0.9.5-F6A RevisionService runtime repository narrowing

- **Decision**: After the F6A0 prerequisite (completed and verified), swap
  the runtime repository of `RevisionService` from the broad `Database`
  facade to the existing facade-owned `SQLiteRevisionRepository` at every
  active direct and indirect construction path: both app paths, the
  Submission factory (required keyword-only `revision_repository`), the
  AdminReanalysisService embedded Revision composition (required
  keyword-only `revision_repository` injection), and the FeedbackPipeline
  composition line, plus constructor/factory-argument-only updates to
  operational callers and tests.
- **Rationale**: The runtime object should be the already-composed Revision
  aggregate repository rather than the 86-method facade; F6A0 made the
  repository structurally satisfy the central `RevisionRepository` first.
- **Parity boundary**: Central `RevisionRepository`, `RevisionService`
  (typed `repository: RevisionRepository`), Revision write methods, Essay
  updates inside `create_revision_group`/`link_revision`, the
  three-sequential-commit workflow, SQL, transactions, migration 12, 33
  tables, `config-v0.9.0`, prompt `feedback-prompt-v0.7.1`, API 77 pairs,
  client 52 methods, locale 520/520, and facade 86 methods unchanged; no
  new Port, fallback, proxy, or shared transaction.
- **Safety decision**: All write-capable verification used fresh guarded
  temporary databases with python-dotenv disabled and `DATABASE_URL`
  absent; development database remained at SHA-256 `340E0F...AFF4`
  (unchanged).
- **Evidence**: focused 155 PASS; accumulated contracts 188 PASS; full
  non-live core 573 passed + 8 skipped; exact `run.bat --verify` PASS.
- **Boundary**: v0.9.5-F6B (Admin Reanalysis persistence narrowing) and
  later stages only under separate authorization.

## 2026-08-02 - v0.9.5-F6A0 Revision repository capability completion

- **Decision**: Authorized via Option C of the F6A blocker report. Complete
  the existing facade-owned `SQLiteRevisionRepository` capabilities so it
  structurally satisfies the central `RevisionRepository` contract:
  add `get_submission_bundle` and `get_latest_analysis_run` as direct
  reader delegations and wire the existing facade-owned Submission and
  Analysis repository instances into it from the `Database` facade.
- **Rationale**: The F6A runtime swap is impossible while the narrowed
  repository lacks two methods RevisionService directly calls; the F1 audit
  narrative that the Analysis reader was already wired was incorrect at
  HEAD. F6A0 closes that gap without any runtime narrowing.
- **Parity boundary**: Central `RevisionRepository`, `RevisionService`, all
  construction sites, Revision write methods, SQL, transactions, migration
  12, 33 tables, `config-v0.9.0`, prompt `feedback-prompt-v0.7.1`, API 77
  pairs, client 52 methods, locale 520/520, and facade 86 methods unchanged.
- **Safety decision**: All write-capable verification used fresh guarded
  temporary databases with python-dotenv disabled and `DATABASE_URL`
  absent; development database remained at SHA-256 `340E0F...AFF4`
  (unchanged).
- **Evidence**: focused 53 PASS; accumulated contracts 161 PASS; full
  non-live core 559 passed + 8 skipped; exact `run.bat --verify` PASS.
- **Boundary**: v0.9.5-F6A runtime narrowing may be rebaselined and resumed
  only under a separate authorization; F6A0 performs none.

## 2026-08-02 - v0.9.5-F5B ResearchDataService dependency narrowing

- **Decision**: Narrow exactly one Service with consumer-owned Ports:
  `ResearchDataService` -> `ResearchSubmissionReadPort`
  (`list_all_submissions`, `list_student_submissions`,
  `get_submission_bundle`) + `ResearchReviewPort` (`save_human_review`,
  `list_human_reviews`, `apply_pii_review`) + `ResearchExportReadPort`
  (`list_export_jobs`, `get_export_job`). Remove all six repository-
  capability `hasattr` branches associated with the eight approved
  methods. Compose the Service from the existing facade-owned
  Submission repository and the same Research repository instance for
  both Research-owned Ports in both app paths.
- **Caller updates**: `tests/test_research_v082.py` (five sites) and
  `verification/v0.9.5-e/capture_prechange_fresh_database.py` (one site)
  received constructor-only updates discovered in Phase 0; no other
  active caller exists.
- **Rationale**: The F1 audit classified ResearchDataService as a
  medium-risk mixed consumer whose eight calls map exactly to two
  extracted repositories; the approved production facade always supplies
  all guarded capabilities, so the capability-absent branches are unused
  in active production construction.
- **Alternatives**: preserving the hasattr capability discovery (rejected:
  unused in production and hides contract); moving Router `save_export_job`
  into the Service (rejected: forbidden and would change best-effort
  semantics); leaving the Service on the facade (deferred work).
- **Parity boundary**: No facade or repository method deleted; repository
  SQL, transactions, migration 12, 33 tables, `config-v0.9.0`, prompt
  `feedback-prompt-v0.7.1`, API 77 pairs, client 52 methods, and locale
  520/520 unchanged. Human Review and PII writes remain repository-owned
  single-method operations; `save_export_job` remains Router-owned and
  best-effort; export contents, ordering, file names, and formats
  unchanged.
- **Safety decision**: All write-capable verification used fresh guarded
  temporary databases with python-dotenv disabled and `DATABASE_URL`
  absent; every newly created export directory was removed; development
  database remained at SHA-256 `340E0F...AFF4` (unchanged); 235
  pre-existing user exports untouched.
- **Evidence**: focused 97 PASS; contract inventory 141 PASS; full
  non-live core 546 passed + 8 skipped; exact `run.bat --verify` PASS.

## 2026-08-02 - v0.9.5-F5A CALF Service dependency narrowing

- **Decision**: Narrow exactly one Service with consumer-owned Ports:
  `CalfService` -> `CalfDataPort` (`list_analysis_units`,
  `list_error_annotations`, `save_error_annotations`) +
  `CalfSubmissionReadPort` (`get_submission_bundle`,
  `list_student_submissions`) + `CalfAnalysisReadPort`
  (`get_latest_analysis_run`) + `CalfStudentReadPort` (`get_student`).
  Compose the Service from the existing facade-owned
  CALF/Submission/Analysis/Learner repository instances in both app
  paths with explicit keyword arguments.
- **Operational-caller update**: `scripts/verify_live_deepseek_v08.py`
  (line 135) was the only active caller discovered during Phase 0
  outside the composition root; its constructor-only update passes the
  four repositories of its existing local facade graph. No other script,
  test, or verification helper constructs `CalfService`.
- **Rationale**: The F1 audit classified CalfService as a medium-risk
  mixed read/write consumer whose seven calls map exactly to four
  extracted repositories; `save_error_annotations` keeps its
  repository-owned Essay-existence guard and one-connection batch write.
- **Alternatives**: internal fallback construction inside CalfService
  (rejected: forbidden by stop conditions); leaving the Service on the
  facade (deferred work); ResearchDataService narrowing (out of scope,
  F5B).
- **Parity boundary**: No facade or repository method deleted; repository
  SQL, transactions, migration 12, 33 tables, `config-v0.9.0`, API 77
  pairs, client 52 methods, and locale 520/520 unchanged. CalfService
  performs exactly one bundle read before annotation validation and
  exactly one `save_error_annotations` call on success, zero saves on
  validation failure.
- **Safety decision**: All write-capable verification used fresh guarded
  temporary databases with python-dotenv disabled and `DATABASE_URL`
  absent; development database remained at SHA-256 `340E0F...AFF4`
  (unchanged).
- **Evidence**: focused 63 PASS; contract inventory 123 PASS; full
  non-live core 526 passed + 8 skipped; exact `run.bat --verify` PASS.

## 2026-08-02 - v0.9.5-F4 Reanalysis and Journey dependency narrowing

- **Decision**: Narrow exactly two Services with consumer-owned Ports:
  `ReanalysisService` -> `SubmissionBundleReadPort` +
  `AnalysisRunWritePort`; `JourneyService` -> `JourneyStudentReadPort` +
  eight-method `JourneyProjectionReadPort`. Compose both Services from
  the existing facade-owned Submission/Analysis/Learner/Practice
  repository instances in both app paths; store JourneyService on app
  state and expose it through the narrow `get_journey_service`
  dependency so the Journey router no longer constructs from the
  facade.
- **Authorized exception**: `scripts/demo_journey.py` constructed
  `JourneyService(repository)` from the broad facade; the user
  authorized exactly two lines (approximately 105 and 241) to use
  `JourneyService(repository._learner_repository,
  repository._practice_repository)`. Recorded in
  `docs/development/BLOCKER_REPORT_V0.9.5_F4.md`.
- **Rationale**: The F1 audit classified ReanalysisService as low risk
  (one Submission-owned composite read + one Analysis-owned append-only
  write, no shared transaction) and JourneyService as low-medium risk
  (read-only, one Learner lookup + eight Practice projections). Both are
  exact fits for extracted repositories.
- **Alternatives**: internal fallback construction inside either Service
  (rejected: forbidden by the stop conditions); modifying the demo
  script more broadly (rejected: exception is two lines only); leaving
  the Services on the facade (deferred work); Calf/Research narrowing
  (out of scope, medium-risk).
- **Parity boundary**: No facade or repository method deleted; repository
  SQL, transactions, migration 12, 33 tables, `config-v0.9.0`, API 77
  pairs, client 52 methods, and locale 520/520 unchanged. Reanalysis
  performs one bundle read then one Analysis save on success and zero
  writes on missing/error paths; Journey performs zero writes.
- **Safety decision**: All write-capable verification used fresh guarded
  temporary databases with python-dotenv disabled and `DATABASE_URL`
  absent; development database remained at SHA-256 `340E0F...AFF4`
  (unchanged).
- **Evidence**: focused 118 PASS; contract inventory 84 PASS; full
  non-live core 508 passed + 8 skipped; exact `run.bat --verify` PASS.

## 2026-08-02 - v0.9.5-F3 Learner read-model dependency narrowing

- **Decision**: Narrow exactly three Services with consumer-owned Ports:
  `ProgressService` -> `LearnerProgressPort` + `ActiveConfigurationPort`;
  `LearnerProfileService` -> `LearnerProfileReadPort` + injected
  `ProgressService`; `DashboardService` -> `DashboardReadPort` + injected
  `ProgressService`. Remove the inactive `list_longitudinal_records` fallback
  and the relevant `hasattr` capability discovery only from `ProgressService`.
  Compose all three Services from the existing facade-owned
  `SQLiteLearnerRepository` and `SQLiteConfigurationRepository` instances in
  both app paths and `build_submission_service`.
- **Authorized exception**: The legacy `FeedbackPipeline` construction
  (`LearnerProfileService(self.database)`) cannot satisfy the explicit
  constructor; the user authorized exactly one additional production file,
  `app/feedback/service.py`, limited to explicit ProgressService/Profile
  composition from the same facade-owned repositories. Recorded in
  `docs/development/BLOCKER_REPORT_V0.9.5_F3.md`.
- **Rationale**: F1/F2 showed Progress/Dashboard/LearnerProfile consumed a
  broad runtime object and discovered capabilities with `hasattr`; the target
  makes the read/write and configuration dependencies structural without
  changing behavior, transactions, or repository ownership.
- **Alternatives**: internal fallback construction inside
  `LearnerProfileService` (rejected: recreates implicit discovery); leaving
  the three Services unchanged (deferred work); modifying routers or other
  Services (out of scope).
- **Parity boundary**: No facade or repository method deleted; repository SQL,
  transactions, migration 12, 33 tables, `config-v0.9.0`, API 77 pairs,
  client 52 methods, and locale 520/520 unchanged; persist false stays
  write-free and persist true performs exactly one snapshot save.
- **Safety decision**: All write-capable verification used fresh guarded
  temporary databases with python-dotenv disabled and `DATABASE_URL` absent;
  development database remained at SHA-256 `340E0F...AFF4` (unchanged).
- **Evidence**: focused 96 PASS; contract inventory 36 PASS; full non-live
  core 492 passed + 8 skipped; exact `run.bat --verify` PASS.

## 2026-08-02 - v0.9.5-F2 Low-risk Service dependency narrowing

- **Decision**: Narrow exactly two Service dependencies: pass the facade's
  existing composed `SQLiteConfigurationRepository` instance (not the 86-method
  `Database` facade) to `ConfigurationService` in both composition paths, and
  annotate `LearnerHistoryService` against a new one-method `PriorRecordsPort`
  while leaving its runtime object unchanged.
- **Rationale**: The F1 audit showed both consumer contracts are exact fits
  for single extracted repositories; neither change touches transaction
  boundaries. Dashboard/Progress/LearnerProfile redesign is deferred because
  `DashboardService` reaches `get_active_configuration` through a
  `ProgressService` `hasattr` branch.
- **Alternatives**: Leaving both Services on the facade (no narrowing) or
  narrowing Dashboard in the same stage (would change the hasattr branch).
- **Parity boundary**: Preserve the exact seven-method Configuration contract,
  the exact `prior_records` signature, all Service/API/repository/SQL/
  transaction/schema behavior, migration 12, 33 tables, `config-v0.9.0`, API
  77 pairs, client 52 methods, and locale 520/520; do not begin F3/F4/G.
- **Safety decision**: All write-capable evidence used fresh guarded temporary
  databases with python-dotenv disabled and `DATABASE_URL` absent; the
  development database remained at SHA-256 `340E0F...AFF4` (unchanged).
- **Evidence**: 53 focused PASS; full non-live core 480 passed + 8 skipped;
  exact `run.bat --verify` PASS; v0.9.5-E facade-parity test unchanged and
  passing via the default-off `SERVICE_API_DIFF_ALLOWLIST`.

## 2026-08-02 - v0.9.5-E SQLite repository modularization

- **Decision**: Keep the explicit 86-method `Database` facade and alias while
  extracting one shared connection manager and nine aggregate-owned SQLite
  repository implementations.
- **Rationale**: Make table/method ownership structural and auditable without
  changing the broad compatibility surface currently consumed by Services.
- **Parity boundary**: Preserve SQL, schema, signatures, return shapes, IDs,
  transactions, exceptions, migration 12, 33 tables, and `config-v0.9.0`;
  defer Service Dependency Narrowing and facade contraction.
- **Safety decision**: Accept the modified development database as disposable,
  prohibit further access or writes, and accept later write-capable evidence
  only from fresh temporary databases with python-dotenv disabled,
  `DATABASE_URL` absent, the local provider forced, resolved-path/empty-state
  assertions, hash guards, and process/port cleanup.
- **Evidence**: static/fresh-schema parity PASS; 175 focused; runtime/restart
  smoke PASS; 469+8 full regression; exact `run.bat --verify` PASS.

## 2026-08-02 - v0.9.5-D Frontend API Ports and API-surface contract

- **Decision**: Define twelve narrow feature-owned `typing.Protocol` API Ports
  under `app/ui/ports/`, annotate each feature with its own Port, keep
  `WritingFeedbackApiClient` as the sole concrete HTTP client, and version a
  machine-readable Endpoint-Client-Feature classification contract.
- **Rationale**: Features received the broad 52-method concrete client; no
  enforced boundary existed between a feature and the methods it may call,
  and the unwrapped/unused API surface was undocumented.
- **Alternatives**: Splitting the client into per-feature HTTP clients or
  introducing a DI framework would add runtime layers; a broad base Port
  would recreate the monolith.
- **Impact**: Type-only annotation changes (parameter names/order/defaults
  unchanged); 19 new contract/parity tests; 77 endpoints and 52 client
  methods fully classified with reasons; Practice and Research UI contracts
  pinned against backend schemas; facade private-helper imports migrated in
  tests; 465+8 core; exact `run.bat --verify` PASS; no runtime/visual/backend
  change.
## 2026-08-02 - v0.9.5-C Frontend feature extraction and UI boundary restoration

- **Decision**: Move every visible Student and Research page into its own
  module under `app/ui/features/`, keep the old page modules as explicit
  re-export facades, and remove the two UI-to-backend-schema imports
  (Practice instructions, Research export models) through UI-owned contracts.
- **Rationale**: The 1,296-line Student and 514-line Research page modules
  concentrated all features in one file each, and the UI leaked backend
  schema imports into presentation code (documented in the v0.9.5-A audit).
- **Alternatives**: Keeping the monoliths would preserve the coupling;
  extracting with substantial refactoring would risk visual/behavior drift.
- **Impact**: Contract inventory parity on every measured dimension
  (renderers, definitions, API calls, session/widget keys, locale keys);
  15 new boundary/extraction tests; 24/24 representative browser renders;
  446+8 core; exact `run.bat --verify` PASS; no API/backend/content/visual
  change; development database fingerprint unchanged.
## 2026-08-02 - v0.9.5-B Canonical health contract and router decomposition

- **Decision**: Split all FastAPI business routes into feature-owned router
  modules under `app/api/routers/` and make `GET /api/v1/system/health` the
  single lifecycle-based handler in both production and test builders.
- **Rationale**: `_register_business_routes` concentrated ~65 endpoints in one
  684-line function; health was registered twice with different handlers, so
  production and tests resolved different semantics. The lifecycle
  representation is the canonical source for readiness/health state.
- **Alternatives**: Keeping the business health handler (live repository ping)
  would preserve prod/test divergence; a second compatibility endpoint was
  rejected to keep exactly one contract.
- **Impact**: Route inventory parity 77/77 with unchanged operation IDs,
  response models, and status codes; 431+8 core tests; minimal runtime smoke
  and exact `run.bat --verify` PASS; no schema/service/database/UI changes.
## 2026-07-31 — v0.9.1 Role-based UI

- **Decision**: Reorganize Streamlit UI from 10-page flat navigation to role-based dual-view (Student/Research) with 6 pages each.
- **Rationale**: The flat navigation mixed student-facing and research-audit pages, making it hard for students to focus on feedback and action.
- **Alternatives**: Considered Streamlit's native multipage but radio-based navigation in sidebar was simpler and more controllable.
- **Impact**: All existing backend tests pass without changes. Three AppTest-based integration tests skipped (covered by Playwright). No migration or configuration changes.
- **Progressive disclosure**: Student View hides internal IDs, analyzer versions, Diagnostic Gate internals. Research View exposes everything.

# Decision log

## D037 - One shared Student presentation structure
- Status: accepted for v0.9.4-B.
- Decision: all six Student pages use shared purpose, context, task-step, and
  action primitives with a 720px content width. Page-specific evidence stays
  page-specific; no second Student design system is introduced.

## D038 - One ranked current action, with saved-state locks
- Status: accepted for v0.9.4-B.
- Decision: Writing, Practice, and Revision expose one authoritative write
  action at a time and replace it with a locked saved state after success.
  Validation failures and render/navigation/locale/refresh remain zero-write.

## D039 - Journey evidence fields stay independent
- Status: accepted for v0.9.4-B.
- Decision: each Journey item separates time, source, evidence, and limit.
  The read-time 12-event-type projection and conservative semantics are
  unchanged; the page never writes engagement traces.

## D040 - Accessible focus token
- Status: accepted for v0.9.4-B.
- Decision: focus changes to 3px `#0f6dbd`, measured at 5.33:1 on white,
  4.84:1 on the primary surface, and 3.16:1 on the dark boundary.

## D032 — One canonical token source in pixel_art.py
- Status: accepted for v0.9.4-A
- Decision: `app/ui/pixel_art.py` (`DESIGN_TOKENS`) remains the single
  canonical design-token source; `PIXEL_CSS`/`PIXEL_COMPONENT_CSS` are
  generated from it. No second token map and no Student/Research token files.

## D033 — AA primary action red `#e00047`
- Status: accepted for v0.9.4-A
- Decision: primary action background changes from `#ff004d` to `#e00047`
  (measured 4.93:1 white-on-red for normal/hover/active); `#ff004d` remains
  only as a decorative non-text accent. Disabled text uses `#5a5a68`.

## D034 — Intentional Streamlit theme duplication
- Status: accepted for v0.9.4-A
- Decision: `.streamlit/config.toml` repeats only Streamlit-required theme
  keys because the runtime cannot consume Python tokens; a theme/token parity
  test enforces alignment. `.streamlit/` is gitignored, so the config is
  force-added and documented.

## D035 — Sans body + constrained monospace typography roles
- Status: accepted for v0.9.4-A
- Decision: body prose, navigation, forms, feedback, evidence descriptions,
  and Chinese text use a local/system sans stack; monospace is reserved for
  technical/brand roles (IDs, versions, status codes, metrics, code-like
  values, pixel headings). No remote fonts.

## D036 — Local accessible icon policy
- Status: accepted for v0.9.4-A
- Decision: icons are local inline SVG (pixel-style, square caps); decorative
  icons are `aria-hidden`, meaningful icons carry `role="img"` + `aria-label`;
  no remote icon fonts or services; icons never carry meaning alone.

## D028 — Journey events are derived read-time from source records
- Status: accepted for v0.9.3-C
- Decision: Learning Journey events are computed from authoritative persisted
  records (essays, analysis runs, feedback records, practice targets,
  attempts, evaluations, within-task responses, transfer evidence) at read
  time. No write path, no page-view events, no locale/refresh events.
- Rationale: guarantees every event maps to a real record, works for existing
  learners without backfill, and cannot fabricate engagement.

## D029 — FeedbackEngagementTrace stays explicit; page display is never engagement
- Status: accepted for v0.9.3-C
- Decision: the existing FeedbackEngagementTrace model is retained for explicit
  engagement actions but is not written by the journey; the journey does not
  depend on it.

## D030 — Deterministic demo journey policy
- Status: accepted for v0.9.3-C
- Decision: synthetic learner DEMO-001 (is_synthetic=1) is created only through
  scripts/demo_journey.py with the local deterministic provider; setup is
  idempotent, cleanup is scoped to DEMO-001, the database is backed up before
  setup, and no production record is modified.

## D031 — Revision-response claims stay conservative
- Status: accepted for v0.9.3-C
- Decision: within-task response observations may only state that a targeted
  feature changed/did not change, evidence is mixed/unavailable/insufficient;
  they never state mastery, learning, causation, or transfer. Accuracy
  unavailability is never replaced by zero.


## D024 — Separate semantic measurement status from availability
- Status: accepted for v0.8
- Decision: persist research/proxy/candidate/manual/unavailable lifecycle independently from whether one observation has a value.


## D025 — Candidate syntax and errors never become formal measures automatically
- Status: accepted for v0.8
- Decision: require new validated-unit identities or eligible confirmed annotations; keep all candidates out of diagnosis, priorities, practice, and trajectories.


## D026 — Actual duration only for output rate
- Status: accepted for v0.8
- Decision: a task time limit is never a duration proxy; missing actual duration returns unavailable rather than zero.


## D027 — CALF is research evidence, not a score
- Status: accepted for v0.8
- Decision: no aggregation, quality/ability/proficiency/CEFR interpretation, or default prompt priority. v0.9 remains unauthorized.


## D020 — Backend-owned longitudinal facts

- Date: 2026-07-30
- Status: accepted for v0.7.1 verification
- Decision: derive status/counts/evidence IDs before provider execution; allow the provider to word the comment only within those facts; repair a conflicting comment locally and revalidate.
- Boundary: no new ability, proficiency, learning-growth or CALF construct.


## D021 — Keep within-task and cross-task evidence separate

- Date: 2026-07-30
- Status: accepted for v0.7.1 verification
- Decision: expose Draft Chain, adjacent and first-to-latest comparisons as a read-only trajectory while one Revision Group still counts as one independent task.
- Boundary: no causal feedback attribution or revision-quality score; major rewrites explicitly lower attribution confidence.


## D022 — Provider status is an execution record

- Date: 2026-07-30
- Status: accepted for v0.7.1 verification
- Decision: persist request, parse/validation/correction, server-repair and fallback state separately from the formal feedback and show technical detail only in Research audit view.
- Boundary: status does not rate pedagogical quality. Streamlit remains the frontend and session-state rerenders reuse the API result.


## D023 — Accept v0.7.1 and stop before v0.8

- Date: 2026-07-30
- Status: accepted for final human review
- Decision: release the bounded reliability/UI repair after 209 passing normal tests, DeepSeek Live A–C, migration/config rollback coverage, Playwright desktop/mobile QA, HTTP 200 startup probes, security scans, synchronized documentation and one independent commit.
- Evidence: Live A passed directly; Live B passed after one correction; Live C passed with a local longitudinal-comment repair; all three used fallback false. `run.bat --verify` passed.
- Boundary: thresholds, task equivalence, ability-language detection, revision attribution and UI interpretation still require human and educational-measurement review. v0.8 is not authorized.


## D014 — Upgrade the existing profile path

Migration 8 extends `learner_profile_snapshots` and adds append-only `history_evidence_registry`. `ProgressService` remains the single snapshot builder and preserves v0.3 compatibility fields. Historical JSON is never rewritten. New snapshots use `LPS######` and `learner-profile-v0.7.0`.


## D015 — Conservative task-aware sufficiency

Default representative strategy is `final_or_latest`. Two representative tasks permit pairwise description, three permit a provisional direction, and five permit an adequate descriptive trend. Genre, timing band, tool class, revision mode, analyzer family and metric-version signature divide Task Clusters. These defaults are transparent working assumptions without educational or measurement validation.


## D016 — Current Gate remains authoritative

Only a current `selected_priority` with verified evidence may become a current learning target. History cannot reactivate a monitored or suppressed current signal. Zero targets are valid. Strength patterns require verified textual evidence and never imply a stable learner trait.


## D017 — Screen and trace LLM history

`feedback-prompt-v0.7.0` receives only current selected diagnoses plus relevant targets, compatible trajectories, bounded History Evidence IDs, Data Sufficiency and limitations. Raw histories, suppressed diagnoses and unrelated metrics remain outside the prompt. Evidence traces submissions, runs, diagnoses, metrics, cluster and snapshot.


## D018 — Preserve the release boundary

v0.7 adds no CALF, T-unit, grammar-error totals, CEFR, scores, paid embeddings, cloud deployment or v0.8 work. Work stops after verification and commit.

---


## D013 — Calibrate automatic signals before formative feedback

v0.6.1 inserts deterministic Metric Confidence, Diagnostic Gate, Evidence Relevance, and transparent Priority Score layers. Metrics may remain research evidence without becoming diagnoses; diagnoses may remain monitored without entering student feedback. Zero priorities are valid. Distributed count-three repetition without a local cluster remains monitored, prompt/necessary terms are penalized, and connective priorities require a specific relevant location. Word count and parser measurements are descriptive signals, not strengths. Defaults (2 priorities, 0.52 score threshold, repetition 4/0.025, penalties 1.0/0.7, exercise maxima 3/2/1) are versioned prototype assumptions requiring future literature and human calibration. Since `config-v0.6.1` already existed, migration 7 preserves it and activates child `config-v0.6.2`. v0.7/CALF remain `not_started`.


## D001 — Preserve v0.1.1 as an incremental compatibility layer

- Date: 2026-07-29
- Status: accepted
- Decision: retain Analyzer, Diagnoser, Prompt Builder, Provider Router, and feedback validator; wrap them with new services and Repository protocols rather than rewrite them.
- Reason: protects proven evidence validation and fallback behavior.


## D002 — Use numbered native SQLite migrations for v0.2

- Date: 2026-07-29
- Status: accepted
- Decision: use small, versioned Python migration functions with `PRAGMA user_version` and a migration history table, not SQLAlchemy/Alembic.
- Reason: the existing system is small and sqlite3-based; a native runner is the minimum reliable non-destructive mechanism and keeps dependencies limited. PostgreSQL remains an explicit future adapter seam, not a fake implementation.


## D003 — Keep API routes thin and application services framework-neutral

- Date: 2026-07-29
- Status: accepted
- Decision: FastAPI dependency wiring may construct services, but routes only validate, invoke, and translate results. Services contain no FastAPI or Streamlit imports.


## D004 — Fixed local ports fail clearly

- Date: 2026-07-29
- Status: accepted
- Decision: local FastAPI and Streamlit ports are configured once; startup fails with a clear error when unavailable and never silently selects another port.


## D005 — v0.2 acceptance and transition

- Date: 2026-07-29
- Status: accepted
- Decision: v0.2 passed all gates and was committed as `155df8a6a6a2800205b6dc821d1e51cf135b78a1`; the post-gate architecture backup is `docs/visualizations/V0.2_FUNCTION_ARCHITECTURE.md`. v0.3 may begin automatically.


## D006 — Transparent v0.3 longitudinal heuristics

- Date: 2026-07-29
- Status: accepted for prototype review
- Decision: anchor comparisons on the newest submission; admit only `comparable` records to primary baselines/trends; require 3 observations; use ordered-index OLS slope, ±10% first/last change, CV variability, and at most `medium` confidence. Track issue trajectories from structured diagnoses only.
- Reason: this is the smallest explainable approach that preserves uncertainty and can be replaced after literature and empirical calibration. It is not claimed as a validated theoretical or measurement model.


## D007 — Screen Snapshot evidence before LLM use

- Date: 2026-07-29
- Status: accepted
- Decision: FeedbackContext receives a screened Snapshot without excluded submissions or raw historical observations. Local code converts selected conclusions into H evidence IDs. The LLM may cite those IDs but may not recalculate trends or strengthen confidence.


## D008 — Accept v0.3 and stop for human review

- Date: 2026-07-29
- Status: accepted
- Decision: v0.3 passed the 27-item acceptance gate and real DeepSeek verification. The implementation commit is `0ce8f1a`; the post-gate architecture backup is `docs/visualizations/V0.3_FUNCTION_ARCHITECTURE.md`.
- Stop condition: do not implement v0.4 or later work until a human reviews the architecture, comparability rules, longitudinal heuristics, learner profile, and research assumptions documented in `docs/development/V0.3_HUMAN_REVIEW_GUIDE.md`.


## D009 — Authorize the bounded v0.4 → v0.5 → v0.6 sequence

- Date: 2026-07-29
- Status: accepted
- Decision: the project owner supplied an explicit continuation goal authorizing v0.4, v0.5 and v0.6 in sequence. This satisfies the v0.3 human-review stop gate for engineering continuation without treating the reviewed heuristics as educationally validated.
- Boundary: complete each independent acceptance gate and Git commit; stop after v0.6. Do not begin v0.7, full CALF measurement, cloud deployment or a WeChat client.
- Recovery point: annotated Git tag `pre-v0.4-baseline-20260729` points to the verified v0.3 documentation commit.


## D010 — Accept v0.4 Analyzer 2.0 and continue to v0.5

- Date: 2026-07-29
- Status: accepted
- Decision: use spaCy 3.8.7 and en_core_web_sm 3.8.0 as the default local backend, with an explicit BasicAnalyzer fallback; store token-scale evidence in append-only JSON artifacts and versioned MetricResults rather than fixed columns.
- Evidence: 97 passed, 1 opt-in live test skipped; migration 4; current and clean-environment `run.bat --verify` passed; FastAPI/docs/Streamlit returned 200; clean Python 3.11.15 environment passed `pip check`.
- Research boundary: parser, dictionary, MATTR, lexical density and diagnostic thresholds remain automatic unverified prototype signals.


## D011 — Accept v0.5 revision-aware feedback and continue to v0.6

- Date: 2026-07-29
- Status: accepted
- Decision: revision relationships must be explicit; use deterministic local paragraph/sentence/token alignment and append-only Revision Snapshots; default longitudinal analysis uses final-draft-else-latest per Revision Group.
- Evidence: 121 passed, 1 opt-in live test skipped; migration 5; real DeepSeek Prompt/Schema v0.5 revision call cited R001–R005 and passed after one correction retry without fallback; FastAPI/docs/Streamlit and `run.bat --verify` passed.
- Research boundary: alignment and uptake are observed heuristic candidates, not revision-quality scores, proficiency growth or causal feedback effects.


## D012 — Accept v0.6 and stop before v0.7

- Date: 2026-07-29
- Status: accepted for final human review
- Decision: expose only API-computed, version-separated progress evidence; version only allowlisted non-sensitive configuration; preserve exactly one active configuration with append-only audit; make reanalysis local-only by default and require explicit LLM cost confirmation.
- Evidence: 149 passed, 1 opt-in live test skipped; migration 6; configuration activate/rollback/persistence, four reanalysis scopes, FastAPI/docs/Streamlit and `run.bat --verify` passed.
- Boundary: registries and verification statuses prepare CALF-family extensions but no CALF total, proficiency score or CEFR inference exists. Stop now; v0.7 remains not started until explicit authorization after final human review.
