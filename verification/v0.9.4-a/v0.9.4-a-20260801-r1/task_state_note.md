# v0.9.4-A Task-State Note (execution correction)

Date: 2026-08-01

## Current implementation (intended production, not to be reverted)

- `app/ui/pixel_art.py` — canonical `DESIGN_TOKENS`, generated `PIXEL_CSS` /
  `PIXEL_COMPONENT_CSS`, local icon primitive, button/tab/radio selectors
  corrected for the Streamlit 1.60 DOM.
- `app/ui/components.py` — v0.9.4-A primitives and stable testids.
- `app/ui/pages/student_pages.py` — Writing required-prompt validation.
- `app/ui/pages/research_pages.py` — localized strings, loading state,
  compact journey-counts table, `exc` NameError fix.
- `app/ui/streamlit_app.py` — technical mono captions.
- `.streamlit/config.toml` — theme aligned with tokens (gitignored; force-add
  at commit time).
- `locales/en.json`, `locales/zh_CN.json` — 382 keys each (+14), parity kept.

## Current automated tests (intended)

- `tests/test_design_tokens_v094a.py` (48 tests; passing).
- `tests/test_hybrid_components_v094a.py` (32 tests; passing; AppTest weight
  to be reduced per correction instructions).

## Verification infrastructure (reusable, to be consolidated)

- `verification/v0.9.4-a/v0.9.4-a-20260801-r1/phase3_smoke.py`
- `verification/v0.9.4-a/v0.9.4-a-20260801-r1/lifecycle_check.py`
- `verification/v0.9.4-a/v0.9.4-a-20260801-r1/phase7_acceptance.py`

## Temporary debugging artifacts (to remove)

- `verification/v0.9.4-a/v0.9.4-a-20260801-r1/debug_zh_nav.py`

## Failure classification (latest repeated browser failure)

The failing step is zh Research Data navigation late in a long-lived browser
session: the sidebar radios show the correct final selection (简体中文,
研究视图, 研究数据) while the main content stays stale (h2=首页) with zero
exceptions. Classification:

- Product defect: none identified for this failure (fresh early page renders
  Research Data with 8 tabs correctly).
- Verification-harness defect: yes. Long sessions accumulate Streamlit
  activity; API/Streamlit processes were started with unread `stdout=PIPE`,
  which can fill and block a server mid-rerun (consistent with late-session
  freeze after ~60 session renders and with the early probe passing).
- Expected Streamlit rerun behavior: role/locale radio options rebuild on
  locale switch and can reset selection; clicks during in-flight reruns can
  be lost; `fill()` requires blur/Tab to commit. All harness inputs.

## Frozen until focused gates pass

- Full 48-render matrix; full core pytest; legacy Playwright suites;
  lifecycle/recovery suites; `run.bat --verify`; broad documentation.

## Next focused probe

`zh_nav_probe.py` — fresh context: load app -> zh locale -> Research role ->
Research Data -> Human Review tab, with semantic state verification, bounded
stabilization, log-file-backed stack, and 3 consecutive clean runs.
