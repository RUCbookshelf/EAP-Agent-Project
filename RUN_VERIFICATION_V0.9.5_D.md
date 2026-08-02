# v0.9.5-D Verification — Frontend Contract Hardening and API Client Port Isolation

**Date:** 2026-08-02
**Result:** PASS
**Baseline:** `f03d633` (v0.9.5-C verification)
**Implementation commit:** `refactor(v0.9.5-d): isolate frontend api ports` (see commit log)
**Verification commit:** `test(v0.9.5-d): harden frontend api contracts` (see commit log)
**Specification:** `docs/development/V0.9.5_D_SPEC.md`
**Scope:** behavior-preserving frontend contract refactor. No API route, schema, service, repository, database, content, or visual change.

## 1. Twelve Ports created (`app/ui/ports/`)

Student: `StudentHomeApiPort`, `StudentWritingApiPort`, `StudentFeedbackApiPort`, `StudentPracticeApiPort`, `StudentRevisionApiPort`, `StudentJourneyApiPort`.
Research: `ResearchOverviewApiPort`, `ResearchEvidenceApiPort`, `ResearchCalfApiPort`, `ResearchLearningProcessApiPort`, `ResearchDataApiPort`, `ResearchSystemAuditApiPort`.

## 2. Feature → Port → method-count table

| Feature | Port | Methods |
|---|---|---|
| student_home | StudentHomeApiPort | 2 (`get_journey`, `get_practice_targets`) |
| student_writing | StudentWritingApiPort | 2 (`get_student_revision_candidates`, `submit`) |
| student_feedback | StudentFeedbackApiPort | 1 (`get_student_revision_candidates`) |
| student_practice | StudentPracticeApiPort | 5 |
| student_revision | StudentRevisionApiPort | 4 |
| student_journey | StudentJourneyApiPort | 1 (`get_journey`) |
| research_overview | ResearchOverviewApiPort | 2 (`health`, `research_data_quality`) |
| research_evidence | ResearchEvidenceApiPort | 3 |
| research_calf | ResearchCalfApiPort | 0 (session-read feature) |
| research_learning_process | ResearchLearningProcessApiPort | 4 |
| research_data | ResearchDataApiPort | 7 |
| research_system_audit | ResearchSystemAuditApiPort | 4 |

**Shared methods across Ports:** `get_journey` (Home, Journey, Learning Process); `get_practice_targets` (Home, Practice, Revision, Learning Process); `get_student_revision_candidates` (Writing, Feedback, Revision); `submit` (Writing, Revision); `get_submission` (Revision, Evidence); `get_diagnostic_audit` (Evidence, System Audit); `research_data_quality` (Overview, Data).

## 3. Sole concrete client

`WritingFeedbackApiClient` (app/ui/api_client.py) remains the only concrete HTTP implementation; no per-feature wrapper/proxy classes exist (AST-pinned: no `ClassDef` in feature modules; Port modules contain only `typing.Protocol` classes). Method bodies are unchanged (git diff shows only import/annotation lines in features). `streamlit_app.py` wiring is unchanged.

## 4. Concrete-client signature conformance

Every Port method exists on `WritingFeedbackApiClient`, and parameter names/order/kinds/defaults match (bound-method signature comparison; two tests enforce it, including `create_dataset_split` and all default-carrying methods).

## 5. Feature-method allowance

AST test proves, per feature: called methods == Port methods (no calls outside the Port, no unused Port methods); no Student feature gains Research/Admin methods; no Research feature gains Student write methods (`submit`/`create_exercise`/`submit_exercise_attempt`); no feature imports or references `WritingFeedbackApiClient`; no Port imports backend or concrete-client modules; no import cycles.

## 6. Endpoint ↔ Client ↔ Feature contract

Measured at HEAD: **77 endpoints**, **52 public client methods**. Approved contract: `tests/contracts/api_surface_contract.py` (generated deterministically by `verification/v0.9.5-d/build_contract.py`; evidence JSON `api_surface_before.json`).

| Endpoint class | Count |
|---|---|
| A. wrapped_and_used | 24 |
| B. wrapped_but_currently_unused | 27 |
| C. intentionally_unwrapped | 26 (22 business + 4 framework docs) |

Unwrapped categories: admin-only registry inspection (2), registry/future-feature inspection (4), not-part-of-current-Streamlit-product (13), accessed-through-aggregate-endpoint (1), API/debug inspection (1), framework API documentation (4), future-feature action (2). Every C endpoint has a documented reason.

| Client-method class | Count |
|---|---|
| A. used_by_one_or_more_features | 24 |
| B. intentionally_unused_but_retained | 27 |
| C. obsolete_or_unmapped_candidate | 1 (`lifecycle_state` — convenience helper, not an HTTP wrapper) |

Enforcement tests: endpoint set == 77 with no drift; client method set == 52 with no drift; wrapper state per endpoint matches the client source map (including the documented `list_human_reviews` conditional-path mapping); no C-classified endpoint gains a wrapper; no C-classified method gains an endpoint mapping; an unclassified endpoint or method fails the contract.

## 7. Practice parity

The UI-safe `app/ui/contracts/practice.py` matches the backend authoritative `default_exercise_specifications()` for all three exercise types: English instructions, Chinese instructions, stable identifiers, and the exact fallback chain (lang → en → stored fallback). Production `app/ui` imports no `app.practice.*`. The parity test detects future backend/UI drift; no evaluation/target-selection logic lives in the UI contract.

## 8. Research export payload parity

`app/ui/contracts/research.py::build_export_job_payload()` matches `ExportJob(...).model_dump(mode="json")` for all 3 privacy modes × 3 format combinations (jsonl, csv, jsonl+csv): exact key structure, default filter structure (including explicitly-None fields), enum strings, absent-vs-default fields, `created_at` UTC ISO format. Production `app/ui` imports no `app.research.schemas`; the parity tests import backend schemas only for comparison.

## 9. Facade private-helper test migration

- `tests/test_student_experience_v094b.py`: all 13 private-helper imports migrated to feature-owner modules (`features.student.{home,session,formatting,practice,revision,journey}`); only public renderer imports remain through the facade.
- Compatibility exports retained in both facades with deprecation comments (no runtime warnings).
- Static test prohibits new private-helper facade imports in production or tests except the explicit allow-listed compatibility test (`tests/test_v095c_feature_extraction.py::test_private_helpers_remain_importable_from_facade`).
- Compatibility-import test passes (old import styles, including private helpers, still resolve).

## 10. Changed production files

`app/ui/ports/__init__.py`, `app/ui/ports/student.py`, `app/ui/ports/research.py` (new); the twelve feature modules (type-only import/annotation changes); `app/ui/pages/student_pages.py`, `app/ui/pages/research_pages.py` (docstring-only deprecation notes); `docs/development/V0.9.5_D_SPEC.md`. `app/ui/api_client.py` and `app/ui/streamlit_app.py` are unchanged.

## 11. Changed test files

`tests/contracts/api_surface_contract.py` (new, generated), `tests/test_v095d_api_contract.py`, `tests/test_v095d_port_contract.py`, `tests/test_v095d_parity.py` (new); `tests/test_v095c_feature_extraction.py` (signature expectations updated to Port annotations; compat test retained); `tests/test_student_experience_v094b.py` (helper imports migrated).

## 12. Focused frontend/contract tests

Layer 4 focused set (API client, architecture, C-stage boundary/extraction, Student experience, hybrid components, AppTest page renders, reliability UI, design tokens, journey, request reliability, D-stage contracts): **220 passed, 3 skipped**. Phase 0 baseline set: 87 passed, 3 skipped.

## 13. Four-render browser smoke

`verification/v0.9.5-d/four_render_smoke.py` (Playwright; ports 8013/8014/8503; local provider):

- Writing en-desktop, Practice zh-mobile, Research Overview en-desktop, Research Data zh-mobile: **4/4 PASS** — heading present, no overflow, no raw locale keys, no tracebacks, no console errors (Streamlit telemetry noise excluded as environmental).
- API request baseline captured by a verification-only counting proxy: exactly `/api/v1/system/health` and `/api/v1/research/data-quality` (the Research Overview reads); no unexpected calls; no render-triggered writes (isolated DB counts zero).
- Effective database path asserted before startup: `C:\Users\16073\AppData\Local\Temp\...\v095d_ui.db` (fresh temp; `DATABASE_URL` cleared, `DATABASE_PATH` set, local provider), not the dev DB or the v0.9.5-B backup.
- Development database fingerprint before == after (students 4, essays 17, feedback 17, analysis runs 17, snapshots 17, practice targets 1, attempts 1; integrity `ok`; migration 12). Ports 8013/8014/8503 free after cleanup.

## 14. Full regression and launcher

- Full non-live core suite (`pytest tests --ignore=tests/live`): **465 passed, 8 skipped** (baseline 446 + 19 new tests).
- Exact launcher verification, run once: `cmd /c "run.bat --verify"` → **PASS** (dependencies, NLP resource, migration 12, 33 tables, `config-v0.9.0`, prompt `feedback-prompt-v0.7.1`, health/docs/Streamlit 200).
- Externally managed live browser tests were not run (stack/plugin not part of this environment's core gate; this stage changes no UI behavior).

## 15. Unchanged (confirmed by diff scope + tests)

API routes/paths/methods, request/response schemas, backend Pydantic models, services, domain algorithms, repository protocols, `Database`, SQL, migrations (12), table ownership, configuration (`config-v0.9.0`), lifecycle, error taxonomy, request IDs, retry/timeout, auth posture, provider routing; page layout/order/navigation/text/translations/colors/typography/widget keys/test IDs/mobile/desktop/accessibility; API call timing/order/payloads; database read/write counts; locale parity 520/520.

## 16. Deferred findings (unchanged)

Version constants `0.8.0`; 22 unwrapped business endpoints (now documented in the contract); 28 unused/obsolete client methods (documented, retained); `export_jobs` writer; WTR collision; duplicated repository protocols; Database god-class; test-pyramid imbalance; sync-conflict files; legacy `FeedbackPipeline`; pre-existing `test_design_tokens_v094a.py` replacement char; pre-existing `AGENTS.md` trailing whitespace.

## 17. Preserved user-owned files

`AGENTS.md`, `CLAUDE.md`, `.claude/`, `RUN_VERIFICATION_V0.7.md`, `RUN_VERIFICATION_V0.8.2.md`, `data/demo_journey_manifest.json`, `ARCHITECTURE_COUPLING_AUDIT_V0.9.5_A.md`, and the gitignored v0.9.5-B database backup were not staged, modified, or committed by this stage.

## 18. Evidence artifacts

- `verification/v0.9.5-d/capture_api_surface.py`, `api_surface_before.json`
- `verification/v0.9.5-d/build_contract.py`, `four_render_smoke.py`
- `tests/contracts/api_surface_contract.py`
- `tests/test_v095d_api_contract.py`, `test_v095d_port_contract.py`, `test_v095d_parity.py`

## 19. Post-implementation graph review

GitNexus `detect_changes` on the working tree: LOW risk, no affected processes (new files not yet indexed); the local Code Review Graph's embedded paths point at a checkout that does not exist on this machine (same limitation as v0.9.5-B/C); a static bounded impact analysis was used instead (consumers: `streamlit_app.py`, facades, frontend tests — all covered by the focused suite). No graph index modified.

**v0.9.5-D is complete. A separate v0.9.5-E Database Repository Decomposition stage may begin; it has not been started.**
