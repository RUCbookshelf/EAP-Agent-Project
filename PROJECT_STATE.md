# Project State

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
