# Project State

## Current v0.9.5-F3 State

- Status: completed and verified; Learner read-model dependency narrowing
  scope closed (three Services narrowed, one authorized composition exception).
- `ProgressService` -> `LearnerProgressPort` + `ActiveConfigurationPort`;
  `LearnerProfileService` -> `LearnerProfileReadPort` + injected
  `ProgressService`; `DashboardService` -> `DashboardReadPort` + injected
  `ProgressService`. No `hasattr` capability discovery remains in the chain;
  the inactive `list_longitudinal_records` fallback was removed only from
  `ProgressService`.
- Both application paths, `build_submission_service`, and the legacy
  `FeedbackPipeline` reuse the facade-owned extracted Learner and
  Configuration repository instances; no second connection manager,
  repository graph, proxy, or singleton was introduced.
- Verification: focused 96 PASS; contract inventory 36 PASS; full non-live
  core 492 passed + 8 skipped; exact `run.bat --verify` PASS; migration 12;
  33 tables; `config-v0.9.0`; facade 86; API 77; client 52; locale 520/520;
  development database unchanged (SHA-256/mtime).
- Next: v0.9.5-F4 (write-orchestration narrowing) only under a separate
  authorization.

## Current v0.9.5-F2 State

- Status: completed and verified; low-risk Service dependency narrowing scope
  closed (exactly two Services narrowed).
- `ConfigurationService` receives the existing `SQLiteConfigurationRepository`
  instance in both application-construction paths; the 86-method facade is no
  longer passed to it.
- `LearnerHistoryService` depends on the one-method `PriorRecordsPort`
  (`prior_records(submission)`); its runtime object and all behavior are
  unchanged.
- `DashboardService`, `ProgressService`, `LearnerProfileService`, and all other
  Services untouched; facade surface 86 methods; migration 12; 33 tables;
  `config-v0.9.0`; API 77 pairs; client 52 methods; locale 520/520.
- Verification: 53 focused PASS; full core 480 passed + 8 skipped; exact
  `run.bat --verify` PASS; development database unchanged (SHA-256/mtime).
- Next: v0.9.5-F3 (Dashboard/Progress/LearnerProfile and read-only domain
  narrowing) only under a separate authorization.

## Current v0.9.5-E State

- Status: completed and verified; facade-first SQLite repository
  modularization scope closed.
- Explicit 86-method `Database` facade and `SQLiteRepository` alias preserved.
- One shared connection manager and nine aggregate repositories now own the
  persistence implementation; 33/33 tables have a single owner.
- SQL, schema, signatures, return shapes, transactions, IDs, migration 12,
  active configuration `config-v0.9.0`, API/client contracts, and locale
  parity remain unchanged.
- Verification: static and fresh-database parity PASS; 175 focused; runtime
  restart smoke PASS; 469 passed + 8 skipped; exact `run.bat --verify` PASS.
- All accepted write-capable evidence used guarded fresh temporary databases.
  The development-database incident and isolation hardening are recorded in
  `RUN_VERIFICATION_V0.9.5_E.md`.
- Service Dependency Narrowing remains separately gated and was not started.

## Current v0.9.5-D State

- Status: completed and verified; frontend contract hardening scope closed.
- Twelve feature-owned API Ports under `app/ui/ports/`; each feature depends
  only on its Port; `WritingFeedbackApiClient` is the sole concrete client.
- Endpoint-Client-Feature contract under `tests/contracts/`: 77 endpoints and
  52 client methods fully classified (24 A / 27 B / 26 C endpoints; 24 A /
  27 B / 1 C methods) with documented reasons; AST enforcement tests.
- Practice and Research UI contracts parity-tested against backend schemas.
- Tests migrated off facade private-helper imports; compatibility exports
  retained and marked deprecated (comments only).
- Verification: 19 new tests; focused frontend 220+3; 4/4 renders; 465+8 core;
  `run.bat --verify` PASS; migration 12; `config-v0.9.0`; locale 520/520.
- No API/backend/schema/service/repository/database/UI-content/visual change.
  v0.9.5-E remains not started.
## Current v0.9.5-C State

- Status: completed and verified; frontend feature extraction scope closed.
- Six Student feature modules (`home`, `writing`, `feedback`, `practice`,
  `revision`, `journey`) and six Research feature modules (`overview`,
  `evidence`, `calf`, `learning_process`, `data`, `system_audit`) under
  `app/ui/features/`; shared student helpers owned once by `navigation.py`,
  `formatting.py`, `session.py`.
- `app/ui/pages/student_pages.py` and `research_pages.py` are thin re-export
  facades; renderer names/signatures, page order, session/widget keys,
  data-testids, locale keys, API calls, and payloads unchanged.
- UI boundaries restored: Practice uses `app/ui/contracts/practice.py`;
  Research Data uses `app/ui/contracts/research.py`; a static
  prohibited-import test guards the boundary.
- Verification: inventory parity (13/13, 32/32, 24/24, 7/7, 6/6, 32/32,
  98/98); 15 new tests; focused frontend 200+3; 24/24 browser renders;
  446+8 core; `run.bat --verify` PASS; migration 12; `config-v0.9.0`.
- No API/backend/schema/service/repository/database/UI-content/visual change.
  v0.9.5-D remains not started.
## Current v0.9.5-B State

- Status: completed and verified; API router decomposition scope closed.
- Feature routers exist under `app/api/routers/`; `app/api/main.py` is the
  composition root (creation, lifespan, middleware, error handlers, service
  construction, router inclusion).
- `/api/v1/system/health` is registered exactly once with lifecycle-based
  semantics identical in production and tests; `/live` and `/ready` unchanged.
- Route inventory parity: 77 unique path+method pairs before/after; operation
  IDs, response models, and declared status codes unchanged.
- Verification: 274+3 focused API tests; 431+8 core; minimal runtime smoke PASS;
  exact `run.bat --verify` PASS; migration 12; `config-v0.9.0`.
- Schemas, services, repositories, database, UI, API client, and domain
  semantics unchanged. v0.9.5-C remains not started.
## Current v0.9.4-B State

- Status: completed and verified; Student-only redesign scope closed.
- Six Student pages now share a 720px learner-focused structure: purpose,
  context, steps, evidence, one primary next action, and interpretation limits.
- Writing, Practice, and Revision preserve field-local validation,
  authoritative write paths, saved-state locks, and idempotency. Feedback and
  Journey remain read-oriented; page rendering and navigation create no data.
- English/Simplified Chinese locale parity is 520/520. Focus is 3px `#0f6dbd`;
  desktop/mobile behavior and 44px touch targets are browser-verified.
- Verification: affected 95+1, Student 130+2, core 421+8; controlled
  cross-page flow PASS; Student renders 24/24; Research smoke 6/6; legacy
  Playwright, lifecycle/recovery, and exact `run.bat --verify` PASS.
- Backend/API/database/domain/Research IA unchanged: migration 12,
  `config-v0.9.0`. v0.9.4-C/D and v1.0 remain not started.
- Known out-of-scope backend defect: multi-row `WTR` identifier allocation can
  collide; recorded in `docs/KNOWN_LIMITATIONS.md`.

## Current v0.9.4-A State

- Status: completed (foundation stage; page redesigns deferred to v0.9.4-B/C).
- Hybrid Pixel System 2.0 foundation implemented: canonical `DESIGN_TOKENS`
  (app/ui/pixel_art.py) with generated CSS; Streamlit theme aligned
  (`.streamlit/config.toml`, parity-tested); readable system sans body with
  constrained monospace; primary action red `#e00047` (measured 4.93:1);
  shared spacing/geometry/focus/status/density/responsive tokens; local
  accessible SVG icons; shared component primitives with stable testids.
- Minimal production adoption: Writing required-prompt validation, Run
  Export loading state, Journey-counts table, mono technical captions; two
  hardcoded Chinese-mode Research Data strings localized (382/382 parity).
- No backend/API/database/journey change; migration 12; config-v0.9.0.
- Verified: core pytest 394 passed, 8 skipped; live A–G 20; legacy Playwright
  PASS; lifecycle PASS; run.bat --verify PASS; zh probe 3/3; representative
  24/24; final 48/48 browser renders.
- Design direction recorded: Hybrid Pixel System 2.0 (Direction B).

## Current v0.9.3-C State

- Status: completed; database migration 12; active configuration config-v0.9.0 preserved.
- Learning Journey hardened (UX-001): read-time derivation from authoritative
  source records; no render/locale/refresh events; accurate empty-state
  taxonomy; Student ID normalization + learner-state consistency; practice
  and revision idempotency; conservative revision-response semantics.
- Deterministic demo journey for synthetic learner DEMO-001
  (scripts/demo_journey.py --setup|--status|--cleanup; idempotent; scoped
  cleanup; local provider only; DB backups recorded).
- pytest: 324 passed, 8 skipped; Cases A-R + live validation: 130 passed;
  legacy Playwright harnesses PASS; run.bat --verify PASS (3 cold starts);
  recovery check PASS; 4 locale/viewport combinations clean.
- Journey output makes no mastery/learning-gain/causal/transfer/proficiency/
  CEFR claim.

## Current v0.9.3-B State

- Status: completed; database migration 12; active configuration config-v0.9.0 preserved.
- All eight broken Research endpoints repaired (ERR-001).
- Canonical request-error taxonomy (app/errors.py) with 14 categories.
- Client-side error classification; centralized timeout profiles; bounded GET-only retries.
- Request IDs in responses, error bodies, and sanitized logs.
- Role-appropriate Student/Research error presentation; 295 locale keys en/zh parity.
- pytest: 314 passed, 8 skipped; Cases A-R: 110 passed.
- run.bat --verify: PASS. Legacy live harnesses: PASS when run as designed.

v1.0 remains not_started.


---

# Project State

## Current v0.9.3-A State

- Status: in_progress; database migration 12; active configuration config-v0.9.0 preserved.
- Lifecycle-aware startup: FastAPI lifespan replaces module-level create_app(). Heavy
  initialization (spaCy, DB, services) runs after server is live.
- New endpoints: /api/v1/system/live (liveness), /api/v1/system/ready (readiness).
- Health endpoint enhanced with lifecycle_state and startup_elapsed_ms.
- API client timeout: 90s -> 15s. Stale process cleanup on startup.
- Streamlit shows lifecycle state (starting vs unavailable).
- pytest: 289 passed, 8 skipped (v0.9.2.1 baseline: 271 passed, 8 skipped).
- REL-001 (startup hang) fixed. Backend unchanged after readiness.

v1.0 remains not_started.


---

# Project State

## Current v0.9.2 State

- Status: in_progress; database migration 12; active configuration config-v0.9.0 preserved.
- Pixel Art UI: complete redesign with centralized CSS token system, 7-color palette,
  hard offset shadows, square corners, monospace typography, no transitions.
- Role-based UI: Student View (6 pages) + Research View (6 pages) with progressive disclosure.
- Reusable component library redesigned with pixel-art styling.
- 271 locale keys (en + zh_CN), identical sets, all UI strings localized.
- pytest: 271 passed, 8 skipped (identical to v0.9.1 baseline).
- All backend APIs, practice-domain behavior, migration, and configuration unchanged.

v1.0 remains not_started.


---

# Project State

## Current v0.9.1 State

- Status: completed; database migration 12; active configuration config-v0.9.0 preserved.
- Role-based UI: Student View (6 pages) + Research View (6 pages) with progressive disclosure.
- Reusable component system, responsive layout (desktop to 390x844 mobile), accessible contrast.
- 271 locale keys (en + zh_CN), identical sets, all UI strings localized.
- pytest: 271 passed, 8 skipped (3 v0.9.1 skips for restructured AppTest UI tests).
- Playwright: desktop + mobile role-based navigation, locale switching, console/horizontal-overflow checks.
- All backend APIs, practice-domain behavior, migration, and configuration unchanged from v0.9.

v1.0 remains not_started.
