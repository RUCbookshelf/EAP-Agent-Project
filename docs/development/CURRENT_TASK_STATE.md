# Current Task State

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
