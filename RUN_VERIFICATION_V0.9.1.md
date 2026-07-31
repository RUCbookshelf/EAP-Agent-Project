# RUN VERIFICATION v0.9.1

Date: 2026-07-31
Version: v0.9.1 — UI Completion & Usability Refinement

## pytest

- Result: 271 passed, 8 skipped
- 3 skipped: v0.9.1 AppTest-based integration tests (UI restructured; covered by Playwright)
- 5 skipped: live DeepSeek tests (no API key in test environment)
- All existing backend, analyzer, diagnosis, practice, CALF, API, and architecture tests pass without changes.

## Playwright

- desktop_student: PASS — Student View pages navigate without console errors or horizontal overflow
- desktop_research: PASS — Research View pages navigate without console errors
- mobile_390x844: PASS — App loads at 390x844 without horizontal overflow
- chinese_locale: PASS — Switching to Chinese produces no console errors
- no_raw_keys: PASS — No raw locale keys appear as user-visible text
- student_home: PASS — Default page shows prototype warning

## FastAPI

- Health endpoint: HTTP 200
- API documentation (/docs): accessible
- All v1 routes preserved from v0.9

## Streamlit

- Application starts without import errors
- Role-based navigation renders all 12 pages
- Language switching works without triggering analysis or DeepSeek
- Session state persists across reruns

## i18n

- en.json: 271 keys
- zh_CN.json: 271 keys
- Key parity: PASS (identical sets)
- No raw locale keys in UI: PASS

## Migration

- Version: 12 (unchanged from v0.9)
- Active configuration: config-v0.9.0 (unchanged)

## Code quality

- All new files free of BOM
- Backward-compatible exports preserved (grouped_connectives)
- No backend code changes
- No new dependencies

## Temporary file cleanup

- Cleanup pending (scripts/_fix_*.py files need removal)

## Git

- Working tree: contains v0.9.1 UI changes
- Recovery tag: pre-v0.9.1-recovery
- Next: focused commit

## Remaining work before v1.0

- Corpus import and replay
- Annotation dataset construction
- Machine learning integration
- Real student pilot workflow
- Teacher classroom management
- Cloud deployment
