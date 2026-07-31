# RUN VERIFICATION v0.9.2.1

Date: 2026-07-31
Version: v0.9.2.1 — Pixel Art UI Verification Closure
Implementation commit: d524be3

## 1. Playwright environment

- Package: playwright 1.61.0 (pip installed in project venv)
- Browser: Chromium 149.0.7827.55
- Installation: `python -m pip install playwright`, `python -m playwright install chromium`
- Dependency recorded: `playwright==1.61.0` in requirements.txt
- Browser cache: `%LOCALAPPDATA%\ms-playwright\chromium-1228` (outside repo)

## 2. Service startup

Command: cmd /c "run.bat --verify"
Result: PASS

- [5/7] Migrations: version 12, status PASS
- [6/7] Init: config-v0.9.0, prompt feedback-prompt-v0.7.1, status PASS
- [7/7] Smoke: health 200, docs 200, streamlit 200, status PASS

## 3. Page coverage (Playwright)

Test: tests/live/test_v0921_playwright.py
Result: PASS

All twelve pages verified in all four locale/viewport combinations:

### English desktop (1280x900) — PASS
Home, Writing, Feedback, Revision, Practice, Learning Journey,
Overview, Evidence, CALF Measures, Learning Process, Research Data, System Audit

### Simplified Chinese desktop (1280x900) — PASS
首页, 写作, 反馈, 修订, 练习, 学习旅程,
研究概览, 研究证据, CALF测量, 学习过程, 研究数据, 系统审计

### English mobile (390x844) — PASS
All 12 pages with sidebar toggle opened automatically

### Simplified Chinese mobile (390x844) — PASS
All 12 pages with sidebar toggle, Chinese labels

## 4. Browser console and page errors

- Console errors: 0 unexpected (all four combos)
- Page exceptions: 0 (all four combos)
- No uncaught exceptions, no missing-resource failures

## 5. Horizontal overflow

Check: document.documentElement.scrollWidth <= window.innerWidth
        document.body.scrollWidth <= window.innerWidth
Result: PASS on all 12 pages at both 1280x900 and 390x844

## 6. Pixel Art static style audit

Script: scripts/pixel_art_style_audit.py
Result: PASS — 0 violations in application-owned UI source

Checked: border-radius, gradients, blur, soft shadows, transitions,
animations, forbidden fonts, thin borders on primary components,
single-side accent borders, nested cards.

## 7. Computed-style browser audit

Component | Radius | Background | Filter | Shadow | Transition | Animation | Border
---------|--------|-----------|--------|--------|-----------|----------|------
Text input | 0px | none | none | none | 0s | none | 4px
Textarea | 0px | none | none | none | 0s | none | 4px
Primary button | 0px | none | none | none | 0s | none | 1px (Streamlit)
Expander | 0px | none | none | none | 0s | none | 4px
Alert | 0px | none | none | none | 0s | none | 4px

All zero radius; no gradient bg image; no blur/backdrop filter; no soft
box shadow; zero transition duration; no animation; border thickness
consistent with design system.

## 8. Interaction states

- Keyboard focus: PASS — visible blue outline (rgb(41,173,255) solid 3px,
  offset 2px) on text inputs. Focus ring not clipped.
- Tab order: functional (links, inputs, buttons)
- All state changes immediate (transition: none)

## 9. Role separation

Result: PASS

Student View (body text inspected): no exposed analyzer versions,
internal metric IDs, Evidence IDs, Diagnostic Gate internals, configuration
versions, provider details, database IDs, internal confidence calculations,
Research Data export controls, or System Audit details.

## 10. Localization

- Key parity: 271 keys in en.json, 271 in zh_CN.json — identical sets
- Raw locale keys: 0 displayed (identifier-form check)
- English leakage in Chinese mode: none (navigation labels fully localized)
- Chinese labels: wrap correctly, readable
- Language switching: does not trigger analysis, exercise creation, or
  DeepSeek calls
- Essays, evidence quotations, and historical feedback: not translated

## 11. Practice rerun idempotency

Result: PASS

Navigation, page refresh, and English-to-Chinese language switching
produced zero new exercise_instances (before=0, after=0). No duplicate
attempts created.

## 12. Backend regression

- Full pytest (excluding live tests): 271 passed, 8 skipped
- Cases A–R (lettered suites): 110 passed
  - test_calf_v08 (cases_a_m), test_learner_model_v07 (cases_a_i),
    test_diagnostic_calibration_v061, test_practice_v09,
    test_longitudinal_v03, test_longitudinal_api_v03
- Existing v0.9.1 Playwright suite: 6/6 PASS
- Migration: 12 (unchanged)
- Active configuration: config-v0.9.0 (unchanged)
- Backend: no changes

## 13. Security and repository checks

- Credential scan: PASS — .env gitignored, no tracked secrets.
  Hit patterns are env-var references (os.getenv) or template placeholders
  (your_api_key_here in .env.example).
- Sensitive-file scan: PASS — .env.example (template) is the only .env
  variant tracked; token files are design tokens, not credentials.
- No tracked database files, JSONL exports, browser profiles, PEM/KEY files.
- Tracked screenshots contain no learner data (empty-state pages, demo
  student IDs not visible in captures).

## 14. Screenshots

Location: verification/screenshots/v0.9.2.1/
Count: 13 distinct files

Desktop (1280x900):
  student_home_en_desktop.png
  student_feedback_en_desktop.png
  student_practice_en_desktop.png
  student_journey_en_desktop.png
  research_overview_en_desktop.png
  research_calf_en_desktop.png
  research_data_en_desktop.png
  student_home_zh_desktop.png
  research_overview_zh_desktop.png

Mobile (390x844):
  student_home_en_mobile.png
  student_feedback_en_mobile.png
  student_home_zh_mobile.png
  research_overview_zh_mobile.png

All 13 files have distinct SHA-256 hashes (no duplicates).

## 15. Defects corrected

1. Role-separation: global header exposed analyzer version and provider
   details to Student View. Fixed by gating system status caption behind
   the Research role (commit includes _render_system_status function).

2. Non-localized navigation: sidebar page labels were hardcoded English
   ("Home", "Writing", ...). Fixed by routing page labels through the
   locale system; STUDENT_PAGES and RESEARCH_PAGES values are now locale
   keys translated at render time.

3. Decorative single-side accent borders: .px-notice-limitation and
   .px-quote used left-only borders. Changed to full 4px borders per the
   Pixel Art design rules.

4. Playwright test suite: extended from 6 to full 12-page / 4-combo
   coverage with role separation, focus, computed styles, rerun
   idempotency, and screenshot capture. Mobile sidebar support added.

## 16. Known Streamlit limitations

- Primary button: Streamlit's `[data-testid="stButton"] button` uses
  framework-controlled 1px border; application styling does not fully
  override the Streamlit component's internal border.

- Radio options on mobile: Streamlit renders radio labels inside a
  collapsed sidebar overlay; requires opening the sidebar via hamburger
  control ([data-testid="stExpandSidebarButton"]) before label selection.
  This is a Streamlit framework behavior, not an application defect.

- Tab element headers: Streamlit-managed tab styling partially respects
  application CSS overrides (bottom border and active indicator work,
  font and background cover).

## 17. Documentation status

Created/updated files:
  docs/development/V0.9.2.1_SPEC.md — NEW
  docs/design/PIXEL_ART_DESIGN_SYSTEM.md — NEW
  RUN_VERIFICATION_V0.9.2.1.md — NEW
  docs/development/CURRENT_TASK_STATE.md — updated
  requirements.txt — playwright added
  scripts/pixel_art_style_audit.py — NEW
  tests/live/test_v0921_playwright.py — NEW
  app/ui/pixel_art.py — single-side border fix
  app/ui/streamlit_app.py — role-separation + nav localization fixes

## 18. Final git status

Clean worktree after commit. Ready for v1.0 Corpus Replay.
