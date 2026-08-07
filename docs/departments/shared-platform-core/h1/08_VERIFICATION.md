# 08 — Verification
**Department:** Shared Platform & Core | **Date:** 2026-08-07 | **HEAD:** b171cce → final H1 HEAD (see final report)

## Canonical runner environment

- Interpreter: `.venv\Scripts\python.exe` (Python 3.12.13, isolated venv built for this worktree from the bundled runtime; project requirements incl. pinned spaCy model installed).
- `LLM_PROVIDER=local`; fresh isolated `DATABASE_PATH`/`DATABASE_URL` for every write-capable run.
- `SERVICE_API_DIFF_ALLOWLIST` = current diff vs the v0.9.5-E parity baseline `769e6d8` over app/services|journey|practice|research|api (34 files) — the documented runner contract for the v0.9.5-E parity test.
- Fresh `--basetemp` directory per run (Windows/sandbox temp-root cleanup limitation).
- pytest executed outside the sandbox where tests spawn subprocesses or browsers (documented environment requirement).

## Results

| Gate | Result | Evidence |
| --- | --- | --- |
| Full non-live core (canonical: `pytest -q -p no:cacheprovider --ignore=tests/live tests`) | **1448 passed / 8 skipped / 0 failed / exit 0** (final single clean run; hermetic DATABASE_URL isolation; dev DB hash stable across the run) | .agent-workflow/shared-core-h1/logs/wu10-fullcore-final3.log |
| Shared-core focused suites (version drift, vocabularies, discriminator, resolver, registries, domain packs) | 167/167 | wu2/wu4/wu5/wu6/wu7 logs; combined runs |
| Corpus Stage 5 (`tests/corpus`) | 36/36 | wu8-test.log |
| Locale parity | preserved (no locale files changed; dedicated parity tests 3/3; embedded 600/600 checks green in core) | test_v097d_wu2_revision_practice.py, test_v096c1_no_priority_workflow.py, test_v096c2_sidebar_control.py |
| API surface contract (D-37/RT-19) | 9/9; snapshots regenerated with ADDITIVE-ONLY diff (6 properties added; 0 removed; info.version 0.8.0→0.9.7-d intended; 4 line shifts in submissions.py dependency snapshot) | evidence/openapi-contract-regeneration.json; commit 32b7927 |
| H2D2 dependency/parity contracts | green after snapshot regeneration + documented allowlist | commit 32b7927; 45-test gate run |
| Application startup (`python -m scripts.verify_launcher`) | PASS: health 200, docs 200, streamlit 200; migration 13; 33 tables; config-v0.9.0; LocalDemo | launcher output (LASTEXITCODE=0) |
| Golden-submission behavior diff (D-30) | before-state = frozen v0.9.3-c..v0.9.7-D behavior suite + deterministic demo journey (all green); after-state run on isolated DB: DEMO-001 2 submissions → 2 feedback → 1 priority → revision → 1 practice target/attempt/evaluation; journey 12 events; 10 produced event types all within the frozen vocabulary; 0 new event types; no data mutation | scripts/demo_journey.py runs; journey projection check |
| Persistence / legacy records | migration 13 unchanged (no new migration); WU3 legacy-payload and WU4 legacy-submission tests green; dev DB hash stable across the final canonical run | dev DB SHA-256 29AC74CEA00E02119D004B8551FB3DE6683D0151553AEAE611A1B1C1F034735B (unchanged before/after final run) |
| Regression of browser-in-core (genre-icon) suite | 11/11 | pytest-fresh1 run |

## Data-safety note (V2-DB-A incident class)

During the first full-core runs, the pre-existing `tests/test_v095b_router_contract.py`
production-builder helper constructed `create_app()` with DEFAULT settings, so the
TestClient lifespan refreshed `system_versions.recorded_at` in the checkout dev
database (`data/writing_feedback.db`) — the same metadata-only incident class as
v0.9.6-DP0-V2. Read-only audit confirmed: the dev database contains ZERO user rows
(students=0, essays=0, all user tables empty); only the routine `system_versions`
metadata rows were refreshed. The test was fixed to inject isolated settings
(`make_test_app_settings`), the canonical run now sets hermetic `DATABASE_URL`
isolation, and the dev database hash is STABLE across the final full-core run.
The current dev database hash (29AC74CE...) is adopted as this checkout's baseline.

## Environment notes and limitations

- `tests/live` (Playwright against a running app at :8502) is excluded from the canonical non-live core by repository convention; not executed (requires a live app instance).
- `run.bat --verify` itself requires Python 3.11 (this machine currently lacks a 3.11 interpreter; its `scripts.verify_launcher` equivalent passed). This is a machine-environment limitation, not a product defect.
- The v0.9.5-E parity test requires the documented `SERVICE_API_DIFF_ALLOWLIST` env and subprocess/git access; both were provided for the canonical run.
- WU3 independent review: APPROVE_WITH_FINDINGS (10/10 contract checks PASS; 6 LOW findings recorded — persisted audit record deferred to migration 14; rule-version string duplication; surface map informational; GET-field/empty-string test gaps; hygiene — none blocking).