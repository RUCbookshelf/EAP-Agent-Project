# RUN VERIFICATION v0.9.3-B

Date: 2026-07-31
Mobile closure re-verified: 2026-08-01
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
- Chinese desktop: localized error, no raw keys, console errors 0.

### 9.1 Mobile closure (390x844, English + Simplified Chinese)

The previous mobile run exercised only 6/8 Research Data subsections. The two
subsections not previously exercised on mobile were the first two tabs:
**Export Preview** and **Privacy Mode** (outside the horizontally scrollable
tab bar on narrow viewports -- Streamlit rendering behavior). This closure run
exercised all eight subsections in both locales directly at 390x844 with a
deterministic browser strategy: explicit wait for each tab control,
scroll-into-view, click, wait for `aria-selected=true` and rendered content.
The tab bar overflow is controlled internal scrolling (616px content in a
358px client area, 258px overflow) and every tab was selected and rendered.

Evidence: `verification/v0.9.3-b/mobile-closure/evidence_en.json`,
`verification/v0.9.3-b/mobile-closure/evidence_zh_CN.json`,
`verification/v0.9.3-b/mobile-closure/api_request_log.txt`,
`verification/v0.9.3-b/mobile-closure/summary.json`.

Mobile closure matrix (viewport 390x844):

| Locale | Viewport | Subsection | Rendered | Console errors | Page exceptions | Page-level overflow | Duplicate-write result | Screenshot / evidence | Final result |
|--------|----------|------------|----------|----------------|------------------|----------------------|-------------------------|-----------------------|--------------|
| en | 390x844 | Export Preview | yes | 0 | 0 | none | no duplicates (1 POST each; EXP000001 persisted once) | mobile-closure/screenshots/en_export_preview.png | PASS |
| en | 390x844 | Privacy Mode | yes | 0 | 0 | none | n/a (informational) | mobile-closure/screenshots/en_privacy_mode.png | PASS |
| en | 390x844 | Dataset Filters | yes | 0 | 0 | none | n/a (placeholder) | mobile-closure/screenshots/en_dataset_filters.png | PASS |
| en | 390x844 | PII Review | yes | 0 | 0 | none | n/a (GET, 1 request) | mobile-closure/screenshots/en_pii_review.png | PASS |
| en | 390x844 | Human Review | yes | 0 | 0 | none | exactly 1 new HR record per click | mobile-closure/screenshots/en_human_review.png | PASS |
| en | 390x844 | Dataset Split | yes | 0 | 0 | none | deterministic; no persistence (1 POST) | mobile-closure/screenshots/en_dataset_split.png | PASS |
| en | 390x844 | Data Quality | yes | 0 | 0 | none | n/a (GET, 1 request) | mobile-closure/screenshots/en_data_quality.png | PASS |
| en | 390x844 | Export History | yes | 0 | 0 | none | n/a (GET, 1 request) | mobile-closure/screenshots/en_export_history.png | PASS |
| zh_CN | 390x844 | Export Preview | yes | 0 | 0 | none | no duplicates (1 POST each; EXP000001 persisted once) | mobile-closure/screenshots/zh_CN_export_preview.png | PASS* |
| zh_CN | 390x844 | Privacy Mode | yes | 0 | 0 | none | n/a (informational) | mobile-closure/screenshots/zh_CN_privacy_mode.png | PASS |
| zh_CN | 390x844 | Dataset Filters | yes | 0 | 0 | none | n/a (placeholder) | mobile-closure/screenshots/zh_CN_dataset_filters.png | PASS |
| zh_CN | 390x844 | PII Review | yes | 0 | 0 | none | n/a (GET, 1 request) | mobile-closure/screenshots/zh_CN_pii_review.png | PASS |
| zh_CN | 390x844 | Human Review | yes | 0 | 0 | none | exactly 1 new HR record per click | mobile-closure/screenshots/zh_CN_human_review.png | PASS* |
| zh_CN | 390x844 | Dataset Split | yes | 0 | 0 | none | deterministic; no persistence (1 POST) | mobile-closure/screenshots/zh_CN_dataset_split.png | PASS |
| zh_CN | 390x844 | Data Quality | yes | 0 | 0 | none | n/a (GET, 1 request) | mobile-closure/screenshots/zh_CN_data_quality.png | PASS |
| zh_CN | 390x844 | Export History | yes | 0 | 0 | none | n/a (GET, 1 request) | mobile-closure/screenshots/zh_CN_export_history.png | PASS |

PASS* = functional/QA criteria fully met; one documented pre-existing
localization deviation (see Known Limitations):

- zh_CN Export Preview: success message prefix `Export:` is hardcoded English
  (`app/ui/pages/research_pages.py:314`).
- zh_CN Human Review: `Target ID` input label is hardcoded English
  (`app/ui/pages/research_pages.py:351`).

No write operation was automatically retried: every action produced exactly
one API request (verified from the server request log), and no duplicate Human
Review, export job, dataset split, or other record was created.

Request IDs were captured per action from the server-side request log, e.g.
`d31fcfab2ebc41a6` (POST /api/v1/research/export/preview, en),
`e4e750f845094f11` (POST /api/v1/research/export/run, en),
`efd61a7b931e47f2` (POST /api/v1/research/reviews, zh_CN); the full mapping is
in the evidence JSON files.

## 10. Legacy/Live Test-Harness Disposition

- test_v09_playwright.py (script harness): 6/6 PASS.
- test_v0921_playwright.py (script harness): PASS, 13 screenshots.
- TestLiveG_MobileViewport: UPDATED to current role-based navigation; 20/20 PASS.
- Core pytest: 296 passed, 8 skipped (`pytest tests --ignore=tests/live -q`).
- Research Data integration + request reliability + write-idempotency +
  localization parity suites (test_request_reliability_v093b.py,
  test_research_v082.py): 45 passed.
- Live A-G validation (tests/live/test_v09_live_validation.py): 20 passed.
- Mobile closure harness (verification/v0.9.3-b/mobile_closure_verify.py):
  8/8 en + 8/8 zh_CN at 390x844.
- Cases A-R: 110 passed.

## 11. Final Checks

- cmd /c "run.bat --verify" (re-run 2026-08-01): PASS
- /live 200, /ready 200 (ready true), /health 200
- API docs 200, Streamlit 200
- Migration 12; config-v0.9.0
- Credential scan on verification artifacts: PASS (no secret patterns)
- Sensitive-file scan: PASS (only .env.example template tracked)
- Git worktree clean after commit (verification artifacts only; pre-existing
  uncommitted user changes AGENTS.md / .claude/ / CLAUDE.md preserved
  untouched)

## 12. Known Limitations

- Operation identifiers in error suffixes are English code identifiers.
- zh_CN Human Review tab shows the hardcoded English label `Target ID`
  (`app/ui/pages/research_pages.py:351`); all other Human Review labels are
  localized.
- zh_CN Export Preview success message uses the hardcoded English prefix
  `Export:` (`app/ui/pages/research_pages.py:314`).
- Mobile: the Research Data tab bar requires controlled horizontal scrolling
  (258px internal overflow at 390px viewport); all eight tabs were reached and
  rendered in both locales during closure verification.
- dataset-split is a deterministic computation; no persistence table exists
  (documented; no schema change permitted).
