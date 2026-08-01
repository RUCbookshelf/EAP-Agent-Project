# Project State

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
