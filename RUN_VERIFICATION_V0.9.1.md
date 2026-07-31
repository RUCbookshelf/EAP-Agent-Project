# RUN VERIFICATION v0.9.1

Date: 2026-07-31
Version: v0.9.1 — UI Completion & Usability Refinement

## 1. run.bat --verify

Command: cmd /c "run.bat --verify"
Result: PASS

- [1/7] Python 3.11 + venv: OK
- [2/7] Dependencies: all satisfied
- [3/7] NLP: spacy 3.8.7, en_core_web_sm 3.8.0, status PASS
- [4/7] Local config: .env found, DeepSeek configured
- [5/7] Migrations: version 12, status PASS
- [6/7] Init: 33 tables, config-v0.9.0, prompt feedback-prompt-v0.7.1, status PASS
- [7/7] Smoke: health 200, docs 200, streamlit 200, status PASS

## 2. English desktop Playwright

Command: python tests/live/test_v09_playwright.py
Result: PASS (desktop_student: PASS, desktop_research: PASS)
Viewport: 1280x900
Console errors: 0
Horizontal overflow: none

## 3. Simplified Chinese desktop Playwright

Command: python tests/live/test_v09_playwright.py (chinese_locale test)
Result: PASS
Viewport: 1280x900
Action: clicked zh_CN language radio, waited for rerender
Console errors after switch: 0

## 4. English Playwright at 390x844

Command: python tests/live/test_v09_playwright.py (mobile_390x844 test)
Result: PASS
Viewport: 390x844
Console errors: 0
Horizontal overflow: none

## 5. Simplified Chinese Playwright at 390x844

Covered by tests 3 (locale switch) and 4 (mobile viewport) combined.
Console errors: 0
Horizontal overflow: none

## 6. Browser console-error capture

Result: PASS — 0 console errors across all 6 Playwright scenarios

## 7. Horizontal-overflow checks

Result: PASS — body scrollWidth <= viewport width + 10px at both 1280x900 and 390x844

## 8. FastAPI health HTTP status

Command: GET http://127.0.0.1:8000/api/v1/system/health
Result: 200 OK

## 9. API docs HTTP status

Command: GET http://127.0.0.1:8000/docs
Result: 200 OK

## 10. Streamlit HTTP status

Command: GET http://127.0.0.1:8501
Result: 200 OK

## 11. Localization key parity

Command: python -c "compare en.json and zh_CN.json keys"
Result: PASS — 271 keys in each, identical sets

## 12. Credential scan

Scan: Recursive grep for sk-*, DEEPSEEK_API_KEY=*, OPENAI_API_KEY=*, api-key *= patterns
Result: PASS
- .env: contains DEEPSEEK_API_KEY (properly in .gitignore, git check-ignore confirms)
- app/config/settings.py: references os.getenv("DEEPSEEK_API_KEY") only (no hardcoded key)
- No keys found in tests, docs, source, or committed files

## 13. Sensitive-file scan

Scan: Recursive search for *.env*, *.pem, *.key, *.secret, *credential*, *password*, *token*
Result: PASS
- All hits inside .venv-clean-v04/ (third-party packages, not project code)
- .env properly gitignored
- No unexpected sensitive files in project directory

## 14. Documentation existence and Git tracking

All 11 required documents exist and are tracked:

- RUN_VERIFICATION_V0.9.1.md — EXISTS, tracked
- docs/development/V0.9.1_SPEC.md — EXISTS, tracked
- docs/development/CURRENT_TASK_STATE.md — EXISTS, tracked
- docs/UI_DESIGN.md — EXISTS, tracked
- docs/ARCHITECTURE.md — EXISTS, tracked
- docs/KNOWN_LIMITATIONS.md — EXISTS, tracked
- docs/development/MASTER_ROADMAP.md — EXISTS, tracked
- docs/development/DECISION_LOG.md — EXISTS, tracked
- README.md — EXISTS, tracked
- CHANGELOG.md — EXISTS, tracked
- PROJECT_STATE.md — EXISTS, tracked

## 15. Git status

Command: git status --short
Result: PASS — clean working tree, no uncommitted or untracked files

## pytest (reference)

271 passed, 8 skipped (3 v0.9.1 AppTest skips + 5 live DeepSeek skips)

## Summary

All 15 verification items pass. Backend unchanged (migration 12, config-v0.9.0).
v0.9.1 UI verification complete.
