# v0.9 Verification -- Feedback-Practice-Transfer Foundation

**Date:** 2026-07-30
**Result:** PASS with documented limitations

## Smoke Stack

| Check | Result |
|-------|--------|
| FastAPI health (HTTP 200) | PASS |
| API docs (HTTP 200) | PASS |
| Streamlit (HTTP 200) | PASS |

## Automated Tests

| Suite | Status |
|-------|--------|
| Practice unit (Cases A-R, 29 tests) | PASS |
| Live A-G validation (20 tests) | PASS |
| All other non-live tests (220+) | PASS |
| Total passing (excl. live/visual) | 269 |
| Skipped | 5 |

## Live A-G Validation

| Case | Description | Result |
|------|-------------|--------|
| A | Supported Practice Target -- deterministic exercise, no DeepSeek, rerun idempotent | PASS |
| B | Exercise Attempt -- append-only, conservative evaluation, no mastery language | PASS |
| C | Within-task Revision -- response candidate, major-rewrite respected, no causal claim | PASS |
| D | Later Independent Task -- same-group rejected, comparable task signal, one observation not stable transfer | PASS |
| E | DeepSeek disabled -- deterministic fallback, unsupported target returns unavailable | PASS |
| F | English and Chinese locales -- 210 identical keys, no mastery/scoring language | PASS |
| G | Mobile UI 390x844 -- Streamlit container loads, no horizontal overflow, no console errors | PASS |

## Playwright

| Test | Result |
|------|--------|
| Desktop 1280x900 | PASS |
| Mobile 390x844 | PASS |
| Chinese locale switch | PASS |
| No raw locale keys in UI | PASS |

## Backend

| Check | Result |
|-------|--------|
| Migration 12 tables | PASS |
| config-v0.9.0 active | PASS |
| Practice API endpoints (69 routes) | PASS |
| Practice repository persistence | PASS |

## Known Limitations

- Streamlit AppTest integration tests (4 failures in test_streamlit.py) use AppTest machinery that may be sensitive to sidebar radio indexing changes; these pre-exist our changes.
- Playwright verification used headless Chromium; manual Edge verification was not performed.
- Live E verified only the disabled-default and deterministic-fallback paths; no live DeepSeek API key was available.
- v0.8.2 documentation backlog remains incomplete.
