# RUN VERIFICATION v0.9.4-A — Hybrid Design System Foundation

Date: 2026-08-01
Version: v0.9.4-A
Spec: docs/development/V0.9.4_A_SPEC.md
Run ID: `v0.9.4-a-20260801-r1`

## 1. Baseline

- Branch master; HEAD before this stage `8d5583d`; prerequisite commits
  `b8f1e95`, `31a7fde`, `8d5583d` present in history.
- Migration 12; active configuration `config-v0.9.0` (unchanged).
- `cmd /c "run.bat --verify"`: PASS before and after implementation.
- Pre-existing user-owned changes preserved (not staged): `AGENTS.md`,
  `RUN_VERIFICATION_V0.7.md`, `.claude/`, `CLAUDE.md`,
  `data/demo_journey_manifest.json`.

## 2. Implementation summary

- Canonical token contract `DESIGN_TOKENS` in `app/ui/pixel_art.py`;
  generated `PIXEL_CSS` / `PIXEL_COMPONENT_CSS`; local SVG icon primitive.
- `.streamlit/config.toml` theme aligned with tokens (parity tested). Note:
  `.streamlit/` is gitignored; the config is force-added with the
  implementation commit and documented.
- Body prose switched to a local/system sans stack; monospace constrained to
  technical/brand roles; primary action red darkened `#ff004d` → `#e00047`
  (measured 4.93:1); `#ff004d` retained as decorative non-text accent only.
- Shared primitives in `app/ui/components.py` with stable testids.
- Minimal adoption: Writing required-prompt validation (blocked before the
  API call; server validation and payloads unchanged), loading state on Run
  Export, compact Journey-counts table in Research Learning Process, mono
  technical captions.
- Two hardcoded Chinese-mode Research Data strings localized
  (`human_review_target_id`, `export_run_success`); locale parity 382/382.
- Repaired within scope: `render_research_overview` referenced an undefined
  `exc`; shipped CSS selectors for buttons/tabs/radios did not match the
  Streamlit 1.60 DOM (fixed to `data-testid`/`role`-based selectors).

## 3. Measured contrast (WCAG 2.1, deterministic script)

`python scripts/design_system_audit_v094a.py` — PASS.

| Pair | Ratio | Threshold |
|---|---|---|
| Primary action text/bg (normal, hover, active) | 4.93:1 | >= 4.5:1 PASS |
| Body text/bg | 16.85:1 | PASS |
| Secondary text | 8.71:1 | PASS |
| Muted text | 5.23:1 | PASS |
| Error text/surface | 4.93:1 | PASS |
| Warning text/surface | 13.86:1 | PASS |
| Info text/surface | 6.83:1 | PASS |
| Success text/surface | 9.75:1 | PASS |
| Unavailable text/surface | 4.76:1 | PASS |
| Disabled text/bg | 5.55:1 | PASS |
| Focus outline vs white (recorded; non-text indicator) | 2.47:1 | documented gap |

Only tested token pairs are claimed to meet the measured threshold; no
full-WCAG conformance claim is made.

## 4. Automated tests

- New token/contrast/theme/locale foundation tests:
  `tests/test_design_tokens_v094a.py` — 48 passed.
- New component tests: `tests/test_hybrid_components_v094a.py` — 32 passed
  (pure-function tests plus two AppTest boots for the twelve pages).
- Affected suites: `test_streamlit`, `test_ui_api_client_v02`,
  `test_architecture_v02`, `test_request_reliability_v093b`,
  `test_v071_reliability_ui`, `test_journey_v093c` — 159 passed, 1 skipped.
- Full core pytest (excluding externally managed live suites):
  `pytest -q --ignore=tests/live` — **394 passed, 8 skipped**
  (324 v0.9.3 baseline + 70 new; no existing test weakened).
- Live A–G validation: `tests/live/test_v09_live_validation.py` — 20 passed.
- Legacy Playwright: `tests/live/test_v09_playwright.py` — 6/6 PASS;
  `tests/live/test_v0921_playwright.py` main() — PASS (48-render legacy
  matrix, computed styles, role separation, rerun idempotency).
- Static audits: `scripts/pixel_art_style_audit.py` PASS;
  `scripts/design_system_audit_v094a.py` PASS.

## 5. Browser verification (execution-correction protocol)

Verification infrastructure consolidated in
`verification/v0.9.4-a/v0.9.4-a-20260801-r1/v094a_harness.py` (log-file
stack, semantic-state helpers, bounded stabilization, fresh contexts).

### 5.1 Focused navigation probe (gate: 3 consecutive clean runs)

`zh_nav_probe.py` — zh locale → Research role → Research Data → Human Review:
3/3 PASS, zero console errors, zero page exceptions, correct Chinese labels
(目标 ID present, Target ID absent), correct selected role/page/tab,
process cleanup confirmed.

### 5.2 Representative suite (24 renders)

`representative_suite.py` — Home/Writing/Feedback (Student) and
Overview/Research Data/System Audit (Research) in en/zh_CN x desktop/mobile
with fresh contexts: **PASS** (sans body, mono technical roles, primary
action computed styling `rgb(224,0,71)`, visible focus, 44px touch targets
on mobile, no raw keys, no console errors, no exceptions, no overflow,
correct Chinese labels).

### 5.3 Final acceptance matrix (48 renders)

`phase7_acceptance.py` — all twelve pages x four combinations, fresh context
per combination/role: **PASS**.

| Combination | Renders | Result |
|---|---|---|
| en desktop student / research | 12 | PASS |
| en mobile student / research | 12 | PASS |
| zh desktop student / research | 12 | PASS |
| zh mobile student / research | 12 | PASS |

- Zero unexpected console errors, zero page exceptions, zero remote
  font/icon requests, zero page-level overflow on all 48 renders.
- CSS injected exactly once (`css_injected_once: 1`).
- Interactions: empty Writing prompt blocked with localized field error and
  no essay written; valid submit wrote exactly one essay; DEMO-001 journey
  events rendered; EMPTY01 empty state rendered; Run Export created exactly
  one new export directory (no duplicate write); zh Human Review labels
  correct; locale switching produced zero writes.
- Timing observation: Journey API 31 ms (v0.9.3-C recorded 15–16 ms; no
  regression introduced by the foundation).
- Screenshots and evidence under
  `verification/v0.9.4-a/v0.9.4-a-20260801-r1/`.

## 6. Runtime and lifecycle

`lifecycle_check.py` — PASS: cold start 4.5 s, /live 200, /ready ready:true,
/health 200 (migration 12), /docs 200, /openapi 200, Streamlit 200, warm
restart ready, API-down classified UI state (zero exceptions), recovery
ready, ports free afterwards.

## 7. Exact project verification

`cmd /c "run.bat --verify"` — **PASS** (health 200, docs 200, streamlit 200;
migration 12; config-v0.9.0).

## 8. Security and cleanup

- Credential scan (changed files + verification artifacts): PASS.
- Sensitive-file scan: only `.env.example` tracked (template); no `.db`,
  `.pem`, `.key` tracked.
- CSS/SVG injection scan: PASS; no remote asset URLs; no inline scripts.
- Temporary isolated DB copies, caches, and debug scripts removed; browser
  profiles are Playwright temp profiles (auto-cleaned); app processes
  stopped; ports free.

## 9. Known limitations (documented, not fixed in this stage)

- Focus outline (3px `#29adff`) measures 2.47:1 against white — visible
  non-text indicator retained per brand contract; WCAG 1.4.11 non-text gap
  documented for a later stage.
- Switching language resets the role radio to Student (Streamlit translated-
  options behavior); verified as read-only with no write side effects.
- Four pre-existing English locale strings contain a literal `?` where the
  Chinese uses `——`/`……` (valid UTF-8, not mojibake; untouched per the
  no-unrelated-cleanup boundary).
- `.streamlit/` remains gitignored; the new `config.toml` is force-added.
- `run_export` writes export directories under `research_exports/` and does
  not persist `export_jobs` rows (pre-existing behavior; duplicate-write
  acceptance uses the directory delta).
- `nlp_model_installed=false` in /health remains the documented v0.9.3-A
  cosmetic limitation.

## 10. Commits

- Implementation: `feat(v0.9.4-a): establish hybrid design system foundation`
- Verification: `test(v0.9.4-a): verify hybrid design system foundation`

## 11. Readiness

v0.9.4-A acceptance complete. v0.9.4-B may begin under a separate goal;
v0.9.4-C is not ready until B is separately completed.
