# PDW2-A-CORE-PERSISTENCE — Wave-2 Additive Persistence Foundation (CORE)

**Goal:** `PDW2-A-CORE-PERSISTENCE` — Wave-2 Goal A: L2 revision/context
persistence foundation + wave2 router assembly
**Owner:** CORE — Shared Platform & Core
**Worktree:** `A:\EAP Agent Project\worktrees\shared-core` (branch
`dept/shared-core`)
**Starting SHA:** `59500127ca2cf798ae730cee2a5a3e16707c320c` (promoted master)
**Date:** 2026-08-10

## 1. Scope delivered

Everything is additive on the existing single SQLite database:

1. **Additive migration 14** (`wave2_revision_loop_and_learner_model`) in
   `app/database/migrations.py` creating four new table families plus
   indexes, following the existing conventions (additive, non-destructive,
   rollback-safe, DEFAULT-covered):
   - `writing_tasks` — task/context metadata (student, prompt, genre,
     task_type, modality, reference group, timestamps, metadata/limitations).
   - `submission_revisions` — revision relationship records with ancestry,
     timestamps, task-context, analysis-run, and feedback-record links.
     Existing `revision_groups`/`revision_snapshots` remain authoritative for
     grouping and analysis payloads; this table adds the qualified
     relationship contract without duplicating their payloads.
   - `learning_observations` — longitudinal learner observations (type,
     evidence refs, task/context, occurrence/recency, revision response).
   - `learning_items` — learner-owned items (originating evidence, feedback
     reference, revision history, task/context, status).
   - Rollback 14→13 is a logical ledger-only rollback (non-destructive:
     tables and data preserved; re-apply idempotent via `CREATE IF NOT
     EXISTS`), consistent with the established rollback convention.
2. **Additive repositories** —
   `app/infrastructure/sqlite/repositories/wave2.py` (`SQLiteWave2Repository`
   plus `WritingTask`, `SubmissionRevisionLink`, `LearningObservation`,
   `LearningItem` records), exported from the repositories package.
   Standalone by design: composition into `Database` is deferred (see §5).
3. **Wave-2 API assembly** — `app/api/routers/wave2.py` statically imports
   `learner_api`, `revision_api`, and `personalized_api` from
   `app/api/routers/wave2_modules/` with graceful `ImportError` tolerance
   (modules not yet present → `None`, no mount). The package
   `app/api/routers/wave2_modules/` was created with `__init__.py` only; the
   sub-router modules themselves are intentionally NOT created (later
   department Goals add them).
4. **Registration** — `app/api/main.py` gained exactly one additive
   registration line (`wave2` entry in `_BUSINESS_ROUTERS`, used by both the
   production startup path and the test builder) plus one supporting import
   line. No other main.py change.
5. **Tests (TDD: failing first)** —
   - `tests/test_wave2_migration_v14.py` — fresh-DB upgrade to 14, table
     presence, ledger name, non-destructive rollback 14→13 with data
     preservation, idempotent re-apply, legacy-DB upgrade without history
     loss, DEFAULT coverage of minimal inserts.
   - `tests/test_wave2_repositories_v14.py` — repository round-trips for all
     four table families, including full link round-trip (task/analysis/
     feedback links) and learning-item status update.
   - `tests/test_wave2_router_assembly.py` — assembly imports cleanly with
     no sub-modules (zero mounted routes), mounts present sub-routers
     (injected), tolerates partial presence, main registers wave2 exactly
     once, full app builds and mounts Wave-2 routes when sub-modules exist.

Scope note (PROGRAM control): during execution the pre-existing tests that
pin migration version 13 against the live database were temporarily updated
13→14 (the same mechanical convention used when migration 12 landed in
commit `c239de5`), together with the single-sourced platform constant
(`app/version.py`). PROGRAM directed that those in-place edits to pre-existing
files are outside this Goal's write scope; they were reverted to HEAD. The
remaining pin/constant refresh is documented in §5 as required follow-up
work at integration time.

## 2. What was NOT touched

- D-09 epistemic-status lane: unchanged, fail-closed (no fixed
  epistemic-status columns).
- The previously planned `essays.domain` discriminator ("migration-14 lane"
  in program records): NOT implemented, still trigger-gated. Its DROP
  COLUMN rollback note (F-6) is preserved in the migrations docstring; the
  header note was updated so assertions stay true: version 14 is now the
  Wave-2 persistence migration, so the domain-discriminator lane must be
  renumbered (>= 15) when its implementation Goal fires.
- No existing table DDL: migration 14 only adds new tables and indexes; no
  `ALTER` on existing tables.
- No second persistence system; one SQLite database preserved.
- `app/database/repository.py`, `app/api/ports.py`,
  `app/repositories/protocols.py`, `app/api/routers/__init__.py`, and
  `verification/` were not modified (out of write scope).

## 3. Verification evidence

| Check | Result | Evidence |
| --- | --- | --- |
| Git preflight | PASS | root `A:/EAP Agent Project/worktrees/shared-core`; branch `dept/shared-core`; HEAD `59500127`; 9 pre-existing untracked evidence files preserved untouched |
| Program-control state | PASS | Goal Packet `PDW2-A-CORE-PERSISTENCE` READY; dependency `PDW2-ALIGN-CORE-59500127` GREEN (handoff ingested); promoted baseline matches |
| TDD red phase | PASS | New tests failed before implementation (`ModuleNotFoundError: wave2`, `cannot import name 'wave2'`) |
| Wave-2 focused tests | PASS | `tests/test_wave2_*.py` 13/13 passed (final state) |
| Migration mechanics | PASS | `test_migrations_v02` + `test_migration_drop_column_rollback_note` green (final state) |
| Environment/drift guards | PASS (as baseline) | `test_environment_drift` and `TestModuleSetManifest` fail exactly as at baseline (see §4) |
| Resource hygiene | PASS | no background processes/locks; temp DBs confined to pytest tmp dirs; no global git config changes; no push/PR/promotion |

## 4. Baseline-only failures (unchanged class, re-attested)

The following failure classes existed at the baseline run (HEAD
`59500127`, before any Wave-2 change) and remain the only failures after
this Goal; none is introduced by Wave-2 code:

- `tests/live/test_v09_playwright.py` (6) + `tests/live/test_v0921_playwright.py`
  (3 errors): playwright/browser launch unavailable in this environment.
- `tests/test_environment_drift.py::test_no_absolute_developer_specific_python_paths`:
  pre-existing environment-contract drift.
- `tests/test_learner_model_task_type_v1.py` (2) and
  `tests/test_legacy_genre_mapping_v1.py` (2): census-grid parity failures
  (pre-existing).
- `scripts/corpus_readiness/tests/test_readiness.py::test_derived_roundtrip_sample`
  and `verification/v0.9.6-dp0/test_dp0a_diagnostic.py` (2): pre-existing
  readiness/integrity failures.
- `tests/test_shared_core_drift.py::TestModuleSetManifest::test_current_module_set_matches_manifest`:
  frozen module-set manifest drift (pre-existing at HEAD; this Goal's new
  modules add 3 entries to the drift delta — the manifest must be refreshed
  through the shared-contract change process; `verification/` is out of this
  Goal's write scope).
- `tests/test_v095e_repository_modularization.py::test_static_owner_sql_dependency_and_ddl_parity_contract`:
  fails at HEAD because (a) the verifier's `git show` subprocess hits
  dubious-ownership in this sandbox user context, and (b) the verifier pins
  the frozen WU3 migrations SHA-256 (`b7aa0992...`) plus a historical
  service/api diff allowlist. Post-change it fails on the same classes
  (frozen migrations pin now superseded by migration 14, and the app/api
  diff grew by the wave2 files) — the pin/SHA refresh is a shared-contract
  follow-up, out of write scope.

### Wave-2-attributable failures at HEAD pins (required follow-up, AMBER)

With the pre-existing version pins restored to HEAD (per PROGRAM scope
instruction), the following pre-existing tests fail because migration 14
legitimately advanced the live database to version 14:

- `tests/shared/test_version_single_sourcing.py`:
  `test_latest_migration_equals_platform_constant`,
  `test_version_endpoint_reports_platform_application_version`,
  `test_health_reports_platform_migration_version` —
  `PLATFORM_DATABASE_MIGRATION_VERSION` in `app/version.py` remains 13 at
  HEAD while `LATEST_MIGRATION_VERSION` is 14. Required repair: bump the
  constant to 14 (one line, single-sourcing invariant; the drift test
  explicitly demands the match).
- The migration-era pinned tests asserting `== 13` / `upgrade(...) == 13`
  against the live database: `test_analysis_runs_v04`,
  `test_calf_v08` (migration-10 rollback test), `test_diagnostic_calibration_v061`,
  `test_learner_model_v07`, `test_revision_v05`, `test_snapshot_repository_v03`,
  `test_v06_configuration_dashboard`, `test_v071_reliability_ui`,
  `test_v097b_wu3_target_creation`, `test_v095g_facade_contraction`.
  Required repair: mechanical 13→14 pin bump plus the extra 14→13 rollback
  step in the three migration-era rollback tests (same convention as commit
  `c239de5` for migration 12).

These repairs are mechanical and were verified GREEN during execution before
the revert; they are intentionally left for the integration gate / a
mechanical follow-up Goal rather than performed as in-place edits to
pre-existing test files by this Goal.

## 5. Findings and follow-ups

- **Numbering supersession (documented):** version 14 is now the Wave-2
  persistence migration; the deferred `essays.domain` discriminator lane
  must use version >= 15 when its trigger fires. The migrations docstring
  records this so the F-6 rollback contract remains true.
- **Composition-root wiring deferred:** `SQLiteWave2Repository` is not yet
  composed into `Database` (`app/database/repository.py` was out of write
  scope). Later Wave-2 department Goals (LEARNER PDW2-B, L2 PDW2-C) can
  construct it directly or a follow-up CORE Goal can add the `Database`
  wiring plus `api.state` bindings.
- **Version single-sourcing bump required:** `app/version.py`
  `PLATFORM_DATABASE_MIGRATION_VERSION` must be bumped 13→14 (enforced by
  `tests/shared/test_version_single_sourcing.py`; reverted per PROGRAM scope
  instruction).
- **Migration-version test pins required:** the 10 pre-existing tests listed
  in §4 must receive the mechanical 13→14 pin refresh at integration time.
- **Shared-contract refreshes required (CORE follow-up, through the
  shared-contract change process):** `verification/shared-core-h1/
  module_set_manifest.json` (add `app/api/routers/wave2.py`,
  `app/api/routers/wave2_modules/__init__.py`,
  `app/infrastructure/sqlite/repositories/wave2.py`) and the parity
  verifier's frozen migrations SHA + `SERVICE_API_DIFF_ALLOWLIST`.
- **Doc debt (out of write scope):** `docs/DATABASE_MIGRATIONS.md` and
  `docs/DATA_MODEL.md` still describe migration 13 as current; a mechanical
  refresh is recommended for a follow-up Goal.
- **D-27 census note:** `SQLiteSystemRepository.counts()` lists core tables
  explicitly; the Wave-2 tables are intentionally not part of that health
  summary (additive only).

## 6. Integration/promotion posture

- Verdict: **AMBER** — the Wave-2 persistence foundation is implemented and
  verified (migration apply/rollback, repository round-trips, assembly
  mount), with targeted mechanical repairs required at integration time
  (version constant + migration-version test pins + shared-contract
  manifest/SHA refreshes; all listed in §5).
- `integration_required`: true (Wave-2 candidates batched at
  `PDW2-WU2-INT-GATE`).
- `promotion_eligible`: false — no promotion is performed or claimed; the
  candidate commit is local on `dept/shared-core`.
- No push, no PR, no reset/clean/rebase/force update; master untouched;
  other department worktrees untouched; raw SWECCL untouched.

## 7. Artifacts

- `app/database/migrations.py` (additive migration 14 + updated header note)
- `app/infrastructure/sqlite/repositories/wave2.py` (new)
- `app/infrastructure/sqlite/repositories/__init__.py` (additive export)
- `app/api/routers/wave2.py` (new assembly)
- `app/api/routers/wave2_modules/__init__.py` (new directory + init only)
- `app/api/main.py` (one additive registration line + one import line)
- `tests/test_wave2_migration_v14.py`, `tests/test_wave2_repositories_v14.py`,
  `tests/test_wave2_router_assembly.py` (new)
- This report: `docs/integration/PDW2-A-CORE-PERSISTENCE-20260810.md`
