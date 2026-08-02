# Current Task State

**Date:** 2026-08-02
**Current task:** v0.9.5-F6C SubmissionService Persistence Dependency Narrowing
**Status:** completed and verified (see `RUN_VERIFICATION_V0.9.5_F6C.md`)

- `SubmissionService` now depends on `SubmissionSystemPort`,
  `SubmissionDataPort`, `SubmissionAnalysisPort`, `SubmissionCalibrationPort`
  and the existing non-persistence collaborators; no broad or untyped
  persistence dependency remains; both CALF `hasattr` guards removed; legacy
  `SubmissionRepository` retained only as Protocol-consolidation debt.
- `build_submission_service` takes seven required keyword-only facade-owned
  repositories; both app paths, FeedbackPipeline, and all active callers pass
  the existing facade-owned instances (same connection manager, one graph);
  constructor `record_versions`, submit and regenerate-feedback order, write
  counts, and partial-commit behavior are preserved.
- Focused 282 PASS; accumulated contracts 233 PASS; full core 618 passed +
  8 skipped; exact `run.bat --verify` PASS; migration 12, 33 tables,
  `config-v0.9.0`, prompt `feedback-prompt-v0.7.1`, facade 86, API 77,
  client 52, locale 520/520 unchanged; development database unchanged.
- Next: v0.9.5-F6D Practice write-boundary work only under separate
  authorization.

**Date:** 2026-08-02
**Current task:** v0.9.5-F6B AdminReanalysisService Persistence Dependency Narrowing
**Status:** completed and verified (see `RUN_VERIFICATION_V0.9.5_F6B.md`)

- `AdminReanalysisService` now depends on `AdminConfigurationReadPort`,
  `AdminSubmissionReadPort`, `AdminAnalysisPort`, the unchanged central
  `RevisionRepository`, and the existing settings/Service collaborators; no
  broad or untyped persistence dependency remains.
- All six direct calls route to approved owners; both app paths use the
  existing facade-owned repositories (same connection manager, one graph);
  `configurations.active()`, `submission_service.regenerate_feedback`, and
  the embedded `RevisionService` are unchanged; preview is zero-write;
  Analysis save count/order, feedback conditions, and partial-commit
  behavior are preserved.
- Focused 154 PASS; accumulated contracts 204 PASS; full core 589 passed +
  8 skipped; exact `run.bat --verify` PASS; migration 12, 33 tables,
  `config-v0.9.0`, prompt `feedback-prompt-v0.7.1`, facade 86, API 77,
  client 52, locale 520/520 unchanged; development database unchanged.
- Next: v0.9.5-F6C SubmissionService narrowing only under separate
  authorization.

**Date:** 2026-08-02
**Current task:** v0.9.5-F6A RevisionService Runtime Repository Narrowing
**Status:** completed and verified (see `RUN_VERIFICATION_V0.9.5_F6A.md`)

- Every active `RevisionService` receives the existing facade-owned
  `SQLiteRevisionRepository` (both app paths, Submission factory, Admin
  Reanalysis embedded composition, FeedbackPipeline, operational callers);
  no broad facade runtime remains; no new Port, fallback, proxy, or shared
  transaction; the central `RevisionRepository`, Revision writes, SQL, and
  the three-sequential-commit workflow are unchanged; F6A0 remains the
  completed capability prerequisite.
- Focused 155 PASS; accumulated contracts 188 PASS; full core 573 passed +
  8 skipped; exact `run.bat --verify` PASS; migration 12, 33 tables,
  `config-v0.9.0`, prompt `feedback-prompt-v0.7.1`, facade 86, API 77,
  client 52, locale 520/520 unchanged; development database unchanged.
- Next: v0.9.5-F6B and later stages only under separate authorization.

**Date:** 2026-08-02
**Current task:** v0.9.5-F6A0 Revision Repository Capability Completion
**Status:** completed and verified (see `RUN_VERIFICATION_V0.9.5_F6A0.md`)

- `SQLiteRevisionRepository` exposes `get_submission_bundle` and
  `get_latest_analysis_run` as direct delegations; the facade wires the
  existing Submission and Analysis repository instances into it (one
  connection manager, one graph). Central `RevisionRepository`,
  `RevisionService`, all construction sites, Revision writes, SQL, and
  transactions unchanged; no F6A runtime narrowing performed.
- Focused 53 PASS; accumulated contracts 161 PASS; full core 559 passed +
  8 skipped; exact `run.bat --verify` PASS; migration 12, 33 tables,
  `config-v0.9.0`, prompt `feedback-prompt-v0.7.1`, facade 86, API 77,
  client 52, locale 520/520 unchanged; development database unchanged.
- Next: v0.9.5-F6A runtime narrowing only after a separate rebaseline and
  authorization.

**Date:** 2026-08-02
**Current task:** v0.9.5-F5B ResearchDataService Dependency Narrowing
**Status:** completed and verified (see `RUN_VERIFICATION_V0.9.5_F5B.md`)

- `ResearchDataService` narrowed to three explicit consumer-owned Ports
  (`ResearchSubmissionReadPort`, `ResearchReviewPort`,
  `ResearchExportReadPort`); all six `hasattr` capability checks removed;
  both app paths compose it from the existing facade-owned Submission and
  Research repositories (same Research instance for both Research Ports);
  the five Research test sites and the one verification-helper site
  received constructor-only updates.
- Router-level best-effort `save_export_job` persistence unchanged and
  outside the Service.
- Focused 97 PASS; contract inventory 141 PASS; full core 546 passed + 8
  skipped; exact `run.bat --verify` PASS; migration 12, 33 tables,
  `config-v0.9.0`, prompt `feedback-prompt-v0.7.1`, facade 86, API 77,
  client 52, locale 520/520 unchanged; development database unchanged;
  235 pre-existing user exports untouched.
- Next: any later stage only under a separate authorization.

**Date:** 2026-08-02
**Current task:** v0.9.5-F5A CALF Service Dependency Narrowing
**Status:** completed and verified (see `RUN_VERIFICATION_V0.9.5_F5A.md`)

- `CalfService` narrowed to four explicit consumer-owned Ports
  (`CalfDataPort`, `CalfSubmissionReadPort`, `CalfAnalysisReadPort`,
  `CalfStudentReadPort`); both app paths compose it from the existing
  facade-owned CALF/Submission/Analysis/Learner repositories; the one
  operational-script caller received a constructor-only update.
- Focused 63 PASS; contract inventory 123 PASS; full core 526 passed + 8
  skipped; exact `run.bat --verify` PASS; migration 12, 33 tables,
  `config-v0.9.0`, facade 86, API 77, client 52, locale 520/520
  unchanged; development database unchanged.
- Next: v0.9.5-F5B only under a separate authorization.

**Date:** 2026-08-02
**Current task:** v0.9.5-F4 Reanalysis and Journey Dependency Narrowing
**Status:** completed and verified (see `RUN_VERIFICATION_V0.9.5_F4.md`)

- Two Services narrowed: `ReanalysisService` (`SubmissionBundleReadPort`
  + `AnalysisRunWritePort`) and `JourneyService`
  (`JourneyStudentReadPort` + eight-method `JourneyProjectionReadPort`).
- Both app paths compose the Services from the existing facade-owned
  Submission/Analysis/Learner/Practice repositories; JourneyService is
  stored on app state and the Journey router consumes
  `get_journey_service`; the two `scripts/demo_journey.py` construction
  sites are the owner-authorized operational-script exception.
- Focused 118 PASS; contract inventory 84 PASS; full core 508 passed + 8
  skipped; exact `run.bat --verify` PASS; migration 12, 33 tables,
  `config-v0.9.0`, facade 86, API 77, client 52, locale 520/520
  unchanged; development database unchanged.
- Next: v0.9.5-F5 only under a separate authorization.

**Date:** 2026-08-02
**Current task:** v0.9.5-F3 Learner Read-Model Dependency Narrowing
**Status:** completed and verified (see `RUN_VERIFICATION_V0.9.5_F3.md`)

- Three Services narrowed: `ProgressService` (`LearnerProgressPort` +
  `ActiveConfigurationPort`), `LearnerProfileService` (`LearnerProfileReadPort`
  + injected `ProgressService`), and `DashboardService` (`DashboardReadPort` +
  injected `ProgressService`). The inactive `list_longitudinal_records`
  fallback and relevant `hasattr` branches were removed only from
  `ProgressService`.
- Both application paths and `build_submission_service` supply the
  facade-owned extracted Learner/Configuration repositories; the legacy
  `FeedbackPipeline` received the one authorized composition exception.
- Focused 96 PASS; contract inventory 36 PASS; full core 492 passed + 8
  skipped; exact `run.bat --verify` PASS; migration 12, 33 tables,
  `config-v0.9.0`, facade 86, API 77, client 52, locale 520/520 unchanged;
  development database unchanged.
- Next: v0.9.5-F4 only under a separate authorization.

**Date:** 2026-08-02
**Current task:** v0.9.5-F2 Low-Risk Service Repository Dependency Narrowing
**Status:** completed and verified (see `RUN_VERIFICATION_V0.9.5_F2.md`)

- Exactly two Service dependencies narrowed: `ConfigurationService` receives
  the existing `SQLiteConfigurationRepository` instance in both
  application-construction paths; `LearnerHistoryService` declares the
  one-method `PriorRecordsPort` with an unchanged runtime object.
- `DashboardService`, `ProgressService`, `LearnerProfileService`, and all other
  Services, repositories, facade surface, SQL, transactions, migration 12,
  `config-v0.9.0`, API (77), client (52), and locale (520/520) contracts
  unchanged.
- 53 focused tests PASS; full non-live core 480 passed + 8 skipped; exact
  `run.bat --verify` PASS; development database unchanged.
- Next: v0.9.5-F3 only under a separate authorization.

**Date:** 2026-08-02
**Current task:** v0.9.5-E SQLite Repository Modularization (Facade-first)
**Status:** completed and verified (see `RUN_VERIFICATION_V0.9.5_E.md`)

- Explicit 86-method `Database` facade and `SQLiteRepository` alias retained.
- One shared SQLite connection manager and nine aggregate repositories own all
  persistence methods; all 33 tables have one documented implementation owner.
- SQL/schema/signature/transaction/return-shape parity preserved; migration 12
  and active configuration `config-v0.9.0` unchanged.
- Hardened focused suite 175 passed; runtime/restart smoke PASS; full regression
  469 passed + 8 skipped; exact `run.bat --verify` PASS.
- All accepted write-capable evidence used fresh guarded temporary databases;
  the earlier development-database incident and dotenv isolation hardening are
  disclosed in the verification report.
- Service Dependency Narrowing, facade contraction, schema cleanup, Migration
  13, UI/API/domain changes, and historical-data compatibility remain deferred.
- Next: Service Dependency Narrowing only under a separate authorization.

**Date:** 2026-08-02
**Current task:** v0.9.5-D Frontend Contract Hardening and API Client Port Isolation
**Status:** completed and verified (see `RUN_VERIFICATION_V0.9.5_D.md`)

- Twelve narrow feature API Ports (`app/ui/ports/`); features typed only
  against their Port; `WritingFeedbackApiClient` remains the sole concrete
  client with unchanged method bodies.
- Approved endpoint/client/feature contract (77 endpoints, 52 client methods)
  under `tests/contracts/` with AST enforcement; unwrapped/unused surfaces
  documented.
- Practice and Research UI contracts parity-tested; facade private-helper
  test imports migrated; compatibility exports retained and deprecated.
- 19 new tests; focused frontend 220+3; 4/4 renders; 465+8 core;
  `run.bat --verify` PASS; dev DB unchanged; locale 520/520.
- Next: v0.9.5-E (not started) under a separate goal.
**Date:** 2026-08-02
**Current task:** v0.9.5-C Frontend Feature Extraction and UI Boundary Restoration
**Status:** completed and verified (see `RUN_VERIFICATION_V0.9.5_C.md`)

- Twelve feature modules (six Student, six Research) under `app/ui/features/`;
  old page modules reduced to thin re-export facades; renderer names,
  signatures, page order, session/widget keys, and locale keys unchanged.
- Practice and Research Data backend-schema imports removed via
  `app/ui/contracts/`; prohibited-import static test added.
- Inventory parity 13/13, 32/32, 24/24, 7/7, 6/6, 32/32, 98/98; 24/24
  browser renders; 446+8 core; `run.bat --verify` PASS; dev DB unchanged.
- Next: v0.9.5-D (not started) under a separate goal.
**Date:** 2026-08-02
**Current task:** v0.9.5-B API Router Decomposition and Health Contract Reconciliation
**Status:** completed and verified (see `RUN_VERIFICATION_V0.9.5_B.md`)

- Feature routers under `app/api/routers/`; `app/api/main.py` reduced to a
  composition root; one canonical lifecycle-based `/api/v1/system/health`;
  unreachable duplicate lifecycle-route code removed.
- Route parity 77/77; operation IDs and response models unchanged; 274+3
  focused API tests; 431+8 core tests; runtime smoke PASS; `run.bat --verify` PASS.
- No schema, service, repository, database, UI, or API-client change. Next:
  v0.9.5-C (not started) under a separate goal.



**Date:** 2026-08-01
**Current task:** v0.9.4-B Student Experience Redesign
**Status:** completed and verified (see `RUN_VERIFICATION_V0.9.4_B.md`)

- Home, Writing, Feedback, Practice, Revision, and Learning Journey redesigned
  on Hybrid Pixel System 2.0 with shared purpose/context/steps/action structure.
- Locale parity 520/520; 720px Student width; responsive stacking; accessible
  `#0f6dbd` focus; backend/API/database/domain/Research IA unchanged.
- Verification: 95+1 affected, 130+2 Student, 421+8 core; isolated cross-page
  flow PASS; 24/24 Student renders; 6/6 Research smoke; legacy Playwright,
  lifecycle/recovery, and exact launcher PASS.
- One pre-existing WTR ID-allocation collision is documented and remains an
  out-of-scope backend task.
- v0.9.4-C/D and v1.0 remain not started. This task stops after the second
  bounded verification/documentation commit.

**Date:** 2026-08-01
**Current task:** v0.9.4-A Hybrid Design System Foundation
**Status:** completed (see RUN_VERIFICATION_V0.9.4_A.md)

- Hybrid Pixel System 2.0 foundation implemented (canonical tokens,
  generated CSS, Streamlit theme, sans body + constrained mono, AA primary
  action red `#e00047`, shared geometry/spacing/focus/status/density/
  responsive tokens, local SVG icons, shared component primitives).
- Minimal production adoption + the two hardcoded Chinese-mode Research Data
  strings localized; locale parity 382/382.
- Verified: core pytest 394+8; live A–G 20; legacy Playwright PASS; lifecycle
  PASS; `run.bat --verify` PASS; zh probe 3/3; representative 24/24; final
  48/48 browser renders; migration 12; config-v0.9.0.
- Next: v0.9.4-B (Student Experience Redesign) under a separate goal;
  v0.9.4-C not before B.

**Date:** 2026-07-31
**Current version:** v0.9.3 (A + B + C)
**Status:** completed

**Date:** 2026-08-01
**Current task:** v0.9.3-C product journey hardening
**Status:** completed

## Completed (v0.9.3-C)
- Learning Journey hardened (UX-001): read-time derivation from authoritative
  source records; event contract, ordering, deduplication, versioning,
  limitations; no render/locale/refresh events.
- Accurate empty-state taxonomy (UX-002, DATA-001); Student ID normalization
  and learner-state consistency (UX-003); loading states (ERR-003).
- Practice and revision idempotency; practice evaluation persisted;
  conservative revision-response semantics; no unsupported learning claims.
- Deterministic demo journey (synthetic DEMO-001): idempotent setup, scoped
  cleanup, local provider only, DB backups (scripts/demo_journey.py).
- Journey browser verification incl. S02 regression, API-restart recovery,
  and four locale/viewport combinations (verification/v0.9.3-c/).
- pytest: 324 passed, 8 skipped; Cases A-R + live validation: 130 passed;
  legacy Playwright harnesses PASS; run.bat --verify PASS x3; migration 12;
  config-v0.9.0.

## Completed (v0.9.3-B)
- Eight broken Research endpoints repaired (export schema/preview/run/history/
  manifest/status, data-quality, pii-candidates/pii-review, human reviews,
  dataset split)
- Canonical error taxonomy (app/errors.py)
- Server-side error mapping with request IDs
- Client-side classification + centralized timeouts + bounded GET-only retries
- Role-appropriate error presentation + 295-key locale parity
- Research Data 8-subsection workflow verified via HTTP and browser
- 25 new tests (tests/test_request_reliability_v093b.py); 314 passed, 8 skipped
- Cases A-R: 110 passed; legacy harnesses PASS as designed
- run.bat --verify: PASS; migration 12; config-v0.9.0

## Completed (pre-v0.9.4 UI/UX exploration)
- Live 12-page interface audit in 4 combinations (en/zh_CN x 1280x900/390x844)
  with real interaction; zero console errors/exceptions/overflow on 48 page
  renders
- ui-ux-pro-max skill searches (9 runs) recorded under
  verification/design/pre-v0.9.4/uiuxpro-results/
- Sanitized current-interface screenshots under
  verification/design/pre-v0.9.4/current-ui/
- Six design decision documents in docs/design/ (audit, directions,
  component inventory, token options, page recommendations, decision matrix)
- Recommended direction: B — Hybrid Pixel System 2.0 (pending user decision)

## Pre-v0.9.4 status
- No design direction has yet been approved.
- No implementation has started.
- v0.9.3-C is complete; v0.9.4 remains separate and unimplemented.

## Next
- User decision on pre-v0.9.4 design direction (A / B / C)
- v1.0 corpus work (not started)
