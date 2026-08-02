# v0.9.5-C Verification — Frontend Feature Extraction and UI Boundary Restoration

**Date:** 2026-08-02
**Result:** PASS
**Baseline:** `9a3fc47` (v0.9.5-B verification)
**Implementation commit:** `refactor(v0.9.5-c): extract frontend feature modules` (see commit log)
**Verification commit:** `test(v0.9.5-c): verify frontend feature boundaries` (see commit log)
**Specification:** `docs/development/V0.9.5_C_SPEC.md`
**Scope:** behavior-preserving frontend code-organization refactor. No API, backend schema, service, repository, database, migration, content, or visual change.

## 1. Old-to-new module map

| Old module | New modules |
|---|---|
| `app/ui/pages/student_pages.py` | `app/ui/features/student/{home,writing,feedback,practice,revision,journey}.py` + shared `{navigation,formatting,session}.py`; old module becomes a thin re-export facade |
| `app/ui/pages/research_pages.py` | `app/ui/features/research/{overview,evidence,calf,learning_process,data,system_audit}.py`; old module becomes a thin re-export facade |
| (new) | `app/ui/contracts/{practice,research}.py` — UI-safe display contract and export payload builder |

## 2. Student feature modules created (one per visible page)

`home.py`, `writing.py`, `feedback.py` (includes `render_feedback_content`), `practice.py`, `revision.py`, `journey.py`; shared helpers moved once to `navigation.py` (`_navigate_student_page`), `formatting.py` (`_short_timestamp`, `_feedback_category_label`), `session.py` (`_writing_saved_for_learner`).

## 3. Research feature modules created (one per visible page)

`overview.py`, `evidence.py`, `calf.py` (owns `CALF_CLASSIFICATION`), `learning_process.py`, `data.py`, `system_audit.py`.

## 4. Compatibility facades — final contents and responsibilities

- `app/ui/pages/student_pages.py`: imports + explicit `__all__` re-exports of the seven public renderers and every helper covered by tests/consumers (22 names). No `def render_*`, no Streamlit/API calls.
- `app/ui/pages/research_pages.py`: imports + explicit `__all__` re-exports of the six Research renderers. No logic.
- `app/ui/pages/__init__.py` and `app/ui/streamlit_app.py` are unchanged (they already import through the facades).

## 5. Contract parity

Machine-readable inventory (`verification/v0.9.5-c/capture_frontend_inventory.py`; evidence `frontend_inventory_before.json`, `frontend_inventory_after.json`):

| Dimension | Before | After | Missing | Added |
|---|---|---|---|---|
| Public render functions | 13 | 13 | 0 | 0 |
| All definitions | 32 | 32 | 0 | 0 |
| API client calls | 24 | 24 | 0 | 0 |
| Write-capable API calls | 7 | 7 | 0 | 0 |
| Session-state keys | 6 | 6 | 0 | 0 |
| Widget keys | 32 | 32 | 0 | 0 |
| Locale keys referenced | 98 | 98 | 0 | 0 |

- Render-function signatures unchanged (pinned by `tests/test_v095c_feature_extraction.py`).
- Page order unchanged (`STUDENT_PAGES` / `RESEARCH_PAGES` dictionaries untouched).
- Old import styles keep working, including private helpers imported by `tests/test_student_experience_v094b.py` (`_home_action_contract`, `_practice_instruction`, `_revision_*`, `_journey_*`, etc.).
- Locale parity: 520/520 keys, no additions or deletions.
- Import graph: features never import `app.ui.pages` (AST-pinned); no circular imports.
- UTF-8 audit of changed modules: clean (one pre-existing replacement char in `tests/test_design_tokens_v094a.py`, untouched by this stage); `git diff --check` clean for all stage files (pre-existing trailing whitespace in the user-owned `AGENTS.md` remains untouched).

## 6. Practice boundary fix

- `app/ui/features/student/practice.py` no longer imports `app.practice.schemas`; `_practice_instruction` delegates to `app/ui/contracts/practice.py`, which holds the exact bilingual learner instructions for the three frozen exercise types with the identical lookup/fallback behavior.
- Tests pin the exact en/zh_CN strings and the unknown-type fallback; no evaluation or target-selection logic was copied to the UI; no backend file changed.

## 7. Research Data boundary fix

- `app/ui/features/research/data.py` no longer constructs `ExportJob`/`ExportFilter`/`PrivacyMode`/`ExportFormat`; it passes `app/ui/contracts/research.build_export_job_payload(privacy, fmt)` plain dictionaries to the unchanged `api_client.research_export_preview/run`.
- Payload parity test compares the contract dict against `ExportJob(...).model_dump(mode="json")` (created_at normalized) for three privacy/format combinations: identical keys, enum strings, defaults, and UTC ISO timestamp format.
- No backend schema or endpoint change; HTTP path and request JSON unchanged.

## 8. Prohibited-import static test

`tests/test_v095c_ui_boundaries.py` AST-scans every production module under `app/ui`:
- no imports of `app.practice.*`, `app.research.*`, `app.services.*`, `app.database.*`, `app.repositories.*`;
- every `app.*` import must start with the explicit allow-list (`app.config`, `app.errors`, `app.ui`);
- dedicated grep across all production UI modules: **zero boundary hits**.

## 9. Focused frontend verification

- Student/UI focused set (student experience, hybrid components, AppTest page renders, reliability UI, architecture, API client, streamlit integration, journey, request reliability, design tokens): **200 passed, 3 skipped** in the combined run (final reruns green after the one import defect below).
- New extraction + boundary tests: **15 passed**.
- Phase 0 baseline set: 85 passed, 1 skipped; render probe (English Student Home, Chinese Research Overview): PASS.
- One defect found and repaired during extraction: `features/research/data.py` was missing the `page_header` import (caught by `test_all_research_pages_render`); fixed locally, focused tests rerun green before any further step.

## 10. Representative 24-render browser smoke

`verification/v0.9.5-c/frontend_smoke.py` (Playwright, ports 8012/8502, local provider):

- **24/24 renders PASS** (six Student + six Research pages × English desktop 1280×900 / Chinese mobile 390×844): page loads, correct role/page navigation, no exceptions, no console errors, no raw locale keys, no horizontal overflow, expected headings present.
- Student ID continuity: `SMOKE001` entered on Home persists to Writing.
- Research role isolation: learner ID never appears in Research view.
- **No render-triggered writes**: isolated database row counts are zero for students/essays/feedback/analysis runs/snapshots/practice targets/attempts after all renders.

## 11. Database isolation evidence

- Effective database path asserted before startup: `C:\Users\16073\AppData\Local\Temp\...\v095c_ui.db` (fresh temporary file; `DATABASE_URL` cleared, `DATABASE_PATH` set), not `data/writing_feedback.db` and not the v0.9.5-B backup.
- Development database fingerprint before and after (students 4, essays 17, feedback 17, analysis runs 17, snapshots 17, practice targets 1, attempts 1; integrity `ok`; migration 12): **unchanged**.
- All processes stopped; ports 8012/8502 verified free after cleanup.

## 12. Full regression and launcher

- Full non-live core suite (`pytest tests --ignore=tests/live`): **446 passed, 8 skipped** (baseline 431 + 8, plus 15 new v0.9.5-C tests).
- Exact launcher verification, run once: `cmd /c "run.bat --verify"` → **PASS** (dependencies, NLP resource, migration 12, 33 tables, `config-v0.9.0`, prompt `feedback-prompt-v0.7.1`, health/docs/Streamlit 200).
- Externally managed live browser tests were not run (their stack/plugin are not part of this environment's core gate; this stage changes no UI behavior).

## 13. Unchanged (confirmed by diff scope + tests)

FastAPI routers, API paths/methods, request/response schemas, backend Pydantic schemas, services, domain algorithms, repository protocols, `Database`, SQL, migrations (12), table ownership, configuration (`config-v0.9.0`), request IDs, error taxonomy, retry/timeout behavior, provider routing, lifecycle, Diagnostic Gate, CALF, Practice, Revision, Journey, Research IA, export behavior, auth posture; UI content, visual design, tokens, typography, spacing, page width, ordering, labels, wording, accessibility hooks, and locale files.

## 14. Deferred findings (unchanged, per v0.9.5-C non-goals)

Version constants `0.8.0`; 22 unwrapped API endpoints; `export_jobs` writer; WTR ID collision; duplicated repository protocols; Database god-class; test-pyramid imbalance; sync-conflict files; legacy `FeedbackPipeline`; design-token pre-existing replacement char in `tests/test_design_tokens_v094a.py`; pre-existing `AGENTS.md` trailing whitespace.

## 15. Preserved user-owned files

`AGENTS.md`, `CLAUDE.md`, `.claude/`, `RUN_VERIFICATION_V0.7.md`, `RUN_VERIFICATION_V0.8.2.md`, `data/demo_journey_manifest.json`, `ARCHITECTURE_COUPLING_AUDIT_V0.9.5_A.md`, `data/writing_feedback.pre-v0.9.5b-cleanup-20260802-081311.db` were not staged, modified, or committed by this stage.

## 16. Evidence artifacts

- `verification/v0.9.5-c/capture_frontend_inventory.py`, `frontend_inventory_before.json`, `frontend_inventory_after.json`
- `verification/v0.9.5-c/frontend_smoke.py`
- `tests/test_v095c_ui_boundaries.py`, `tests/test_v095c_feature_extraction.py`

## 17. Post-implementation graph review

GitNexus `detect_changes` on the working tree: LOW risk, no affected processes beyond the pre-existing user-owned doc changes; the local Code Review Graph's embedded paths point at a checkout that does not exist on this machine, so its path resolver is unavailable (same limitation recorded in v0.9.5-B); a static bounded impact analysis was used instead (UI consumers: `streamlit_app.py`, `pages/__init__.py`, and the frontend test files; all covered by the focused suite). No graph index was modified.

**v0.9.5-C is complete. A separate v0.9.5-D frontend-contract stage may begin; it has not been started.**
