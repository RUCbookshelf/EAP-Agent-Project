# RUN VERIFICATION v0.9.3-B

Date: 2026-07-31
Version: v0.9.3-B -- Research API Integrity, Request Reliability, and Error Handling

## 1. Prerequisite Baseline

- v0.9.3-A implementation commits d128734, 2fd768f; verification f03dcbb present in master.
- Migration 12; active configuration config-v0.9.0.
- run.bat --verify: PASS (health 200, docs 200, streamlit 200).

## 2. Eight-Endpoint Verification Matrix (real HTTP through running FastAPI)

Full matrix: verification/_v093b_matrix.json. Summary:

| Endpoint | Success | Empty | Invalid | Not-found |
|----------|---------|-------|---------|-----------|
| export/schema | 200 | - | 405 (wrong method) | - |
| export/preview | 200 | - | 422 invalid_request | - |
| export/run | 200 + persisted | - | 422 invalid_request | - |
| export/history | 200 list | 200 [] | - | - |
| export/{id}/manifest | 200 | - | - | 404 resource_not_found |
| export/{id} | 200 status | - | - | - |
| data-quality | 200 | - | - | - |
| pii-candidates | 200 | 200 [] | - | 404 resource_not_found |
| pii-review | 200 | 200 [] | 422 invalid_request | - |
| reviews POST | 200 HR000001 | - | 422 invalid_request | - |
| reviews GET | 200 persisted | 200 [] | - | - |
| dataset-split | 200 manifest | 200 0 students | 422 invalid_request | - |

All endpoints exercised through the real service + repository stack
(no mocks). Pre-fix evidence: verification/_pre_fix_research.json
(pii-review 500, reviews not persisted, history shadowed, split 404).

## 3. Canonical Error Taxonomy

- Categories + message keys + statuses + retryability centralized in app/errors.py.
- 404 -> resource_not_found (retryable=false), request_id present.
- 422 -> invalid_request with field_errors.
- Unexpected -> 500 backend_processing_error with sanitized detail.
- Exception handlers registered at app creation (verified via running server).

## 4. Request Correlation

- X-Request-ID response header verified (e.g. e2d0ae73327f413e).
- Error bodies include request_id.
- Request IDs random; learner-derived IDs rejected by test.
- Structured request log line: request_id, method, path, status, elapsed_ms, lifecycle.

## 5. Timeout Policy

- Centralized TimeoutProfile: connect 2s, read 10s, write 30s, long-read 60s, lifecycle 5s.
- Absent service identified in ~4s (two bounded connect attempts), classified request_timeout.
- No unclassified 90-second wait remains.

## 6. Retry Policy

- GET: at most 1 retry for retryable categories (service_starting, connection_interrupted, request_timeout).
- POST/PUT/PATCH/DELETE: never automatically retried (verified by unit test).
- 404/422: no retry (verified).
- Duplicate-write protection: generated stable ids (HR/EXP); human review create
  returns the same persisted review on list.

## 7. Client Classification

- ConnectionError -> service_not_running; ReadTimeout/ConnectTimeout ->
  request_timeout; ChunkedEncodingError -> connection_interrupted; 404 ->
  resource_not_found; 500 -> backend_processing_error; 503 starting ->
  service_starting (retryable); malformed JSON -> invalid_response.

## 8. Role-Appropriate Presentation

- Student: localized plain message; Chinese verified:
  `未找到所请求的学习者或记录。 （操作：practice targets）` with no raw keys.
- Research: category/operation/request_id/HTTP status/retryable/detail.
- Locale parity: 295 keys en == zh_CN.

## 9. Research Data Workflow (browser)

- Desktop 1280x900: Research View -> Research Data; all 8 tabs reachable;
  Export Preview action and Data Quality action executed; nonexistent learner
  error rendered; console errors 0; page exceptions 0; no horizontal overflow.
- Mobile 390x844: Research View + Research Data reachable; 6/8 tabs clicked
  (first two tabs are outside the horizontally scrollable tab bar on narrow
  viewports -- Streamlit rendering behavior); console errors 0.
- Chinese desktop: localized error, no raw keys, console errors 0.

## 10. Legacy/Live Test-Harness Disposition

- test_v09_playwright.py (script harness): 6/6 PASS.
- test_v0921_playwright.py (script harness): PASS, 13 screenshots.
- TestLiveG_MobileViewport: UPDATED to current role-based navigation; 20/20 PASS.
- Core pytest: 314 passed, 8 skipped (289 baseline + 25 new B tests).
- Cases A-R: 110 passed.

## 11. Final Checks

- cmd /c "run.bat --verify": PASS
- /live 200, /ready 200 (ready true), /health 200
- API docs 200, Streamlit 200
- Migration 12; config-v0.9.0
- Credential scan: PASS (no secrets in changed files; only false positive "task-clusters")
- Sensitive-file scan: PASS (only .env.example template tracked)
- Git worktree clean after commit

## 12. Known Limitations

- Operation identifiers in error suffixes are English code identifiers.
- Mobile: first two Research Data tabs require horizontal scrolling (Streamlit).
- dataset-split is a deterministic computation; no persistence table exists
  (documented; no schema change permitted).
