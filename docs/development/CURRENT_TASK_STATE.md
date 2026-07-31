# Current Task State

**Date:** 2026-07-31
**Current version:** v0.9.3-B
**Status:** completed

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

## Next
- v0.9.3-C (deferred issues: Learning Journey product hardening, corpus import)
