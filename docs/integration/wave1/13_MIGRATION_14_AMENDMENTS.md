# 13 — Migration-14 Amendments Record (F-1..F-6)

**Goal:** CORE-MIGRATION14-AMENDMENTS (mechanical amendments only)
**Owner:** CORE — Shared Platform & Core
**Worktree:** `A:\EAP Agent Project\worktrees\shared-core` (branch `dept/shared-core`)
**Baseline:** `5aafe2728d7135212bd675a6975b44bcf99ee099` (promoted master)
**Date:** 2026-08-09
**Source review record:** `worktrees/int-study-base/docs/integration/MIGRATION_14_DESIGN_REVIEW.md` (findings F-1..F-6, verdict AMBER)
**Verdict:** GREEN — amendments applied and verified; migration 14 NOT implemented.

## 0. Scope boundary (unchanged)

Migration 14 does not exist and was NOT implemented: no schema change, no
runtime code behavior change (only a module docstring and tests), no export
wiring, no attribution change, no D-09 resolution. The migration triggers from
`06_MIGRATION_14_DECISION.md` §4 remain the sole authorization for
implementation: (1) an Academic persistence implementation Goal starts;
(2) any production query-by-domain or cross-domain persisted query is
required; (3) Academic Writing becomes a functioning product domain surface.
None is currently satisfied.

## 1. F-1 — Refresh migration/data-model documentation (APPLIED)

`docs/DATABASE_MIGRATIONS.md` was stale ("Current version: 3"). Refreshed to
the live state verified against `app/database/migrations.py`:

- `LATEST_MIGRATION_VERSION = 13` (`app/database/migrations.py:9`)
- Full applied-migration table 1..13 with the authoritative ledger names from
  the `MIGRATIONS` map (`migrations.py:731-745`): 1 preserve_v0_1_1_schema,
  2 cloud_ready_repository_indexes, 3 longitudinal_profile_snapshots,
  4 versioned_nlp_analysis_runs, 5 revision_relationships_and_snapshots,
  6 versioned_non_sensitive_configuration,
  7 diagnostic_calibration_and_metric_confidence,
  8 learner_model_v2_and_history_evidence,
  9 longitudinal_reliability_and_provider_status,
  10 calf_measurement_foundation, 11 research_data_infrastructure,
  12 practice_and_transfer_foundation,
  13 practice_target_priority_key_uniqueness
- `schema_migrations` ledger (version, name, applied_at) + `PRAGMA user_version`
  as the authority (`upgrade()` at `migrations.py:747-767`), one-step
  non-destructive logical rollback 13→12 .. 9→8 (`rollback()` at :769-802)
- Explicit "Migration 14 (does NOT exist)" section citing this record and the
  wave-1 decision.

`docs/DATA_MODEL.md` refreshed from "数据模型（迁移 10）" to "数据模型（迁移 13）":
added migration 11 (human_reviews / pii_candidates / export_jobs,
config-v0.8.2), migration 12 (practice/transfer table family, config-v0.9.0),
and migration 13 (partial unique index
`ux_practice_targets_active_priority_key`) paragraphs, the 11 new table rows,
and the live `essays` column set (time_limit_minutes, timing fields,
revision metadata).

## 2. F-6 — DROP COLUMN rollback note (APPLIED)

The rollback note is recorded in:

1. `app/database/migrations.py` module docstring (docstring-only change; no
   runtime behavior): `DROP COLUMN` rollback requires SQLite >= 3.35 (bundled
   3.53.1); the deferred `essays.domain` discriminator must keep a COLUMN-level
   CHECK; any future index/view/trigger on `domain` must be dropped BEFORE
   `DROP COLUMN` because a dependent object blocks the drop.
2. `tests/test_migration_drop_column_rollback_note.py` (rollback-note test,
   fresh temp DB): asserts bundled SQLite >= 3.35; asserts
   `ALTER TABLE essays DROP COLUMN domain` succeeds with a column-level CHECK
   and that inserts work after the drop; asserts an index on `domain` blocks
   the DROP (`sqlite3.OperationalError`) until the index is dropped.

Implementation-gate requirement (for the migration-14 Goal): the migration-14
function docstring MUST carry the same note, and the rollback-note test MUST
remain green after implementation.

## 3. F-2 — Export-time domain enforcement (implementation-gate requirement, NOT implemented)

D-19/D-36: `validate_domain_scope` (`app/domain/validation.py`) exists but is
not wired into export paths. Code enforcement is explicitly an integration
dependency of migration 14 — the first persisted `domain` column is the
trigger. Requirement recorded for the migration-14 implementation Goal (CORE
wiring, GOV policy co-owner):

- Exports reject/quarantine unknown domain values and default to
  domain-scoped (`l2`) output BEFORE any Academic row can exist.
- Add/extend contract tests for mixed-domain rejection.

Do NOT wire before the migration trigger fires.

## 4. F-4 — Per-row attribution provenance (implementation-gate requirement, NOT implemented)

`derive_attribution` currently derives `l2`/`en` for all surfaces. Requirement
recorded for the persistence Goal (CORE + ACAD):

- Once Academic rows can persist, every write path MUST carry surface-derived
  attribution with rule id `domain-attribution-v0.1.0` (recorded per row or
  per batch).
- Advisory relabeling stays rejected: existing `validate_advisory` 422
  behavior must be preserved; no advisory `academic` on L2 surfaces.

## 5. F-5 — Sequencing decision (implementation-gate requirement, INT confirm, NOT decided)

Two acceptable designs, to be confirmed by INT at the migration-14
implementation gate:

- Option A: one atomic additive migration containing the `essays` discriminator
  AND the Academic table family, `schema_migrations` as the only ledger.
- Option B: discriminator first, Academic tables in the persistence Goal.

The discriminator unblocks D-19/D-36/D-31 enforcement; the Academic tables
only become live when ACAD adapters land. No sequencing decision is made in
this record.

## 6. D-09 — Epistemic-status persistence (UNCHANGED, fail-closed)

D-09 (epistemic-status taxonomy L0-L3, downgrade-only; persistence form open)
is NOT resolved here. No fixed epistemic-status column may be persisted
without a separately authorized Researcher decision; compute-at-boundary
typing remains the interim (review finding F-3 stays owned by ACAD design +
GOV policy). This record does not pre-empt its semantics.

## 7. Verification evidence

| Check | Result | Evidence |
|---|---|---|
| Worktree preflight | PASS | root `A:/EAP Agent Project/worktrees/shared-core`; branch `dept/shared-core`; HEAD `5aafe2728d7135212bd675a6975b44bcf99ee099`; pre-existing untracked ADR docs (ADR-01/02/08) preserved untouched |
| Migration tests baseline | PASS | `pytest tests/test_migrations_v02.py tests/shared/test_version_single_sourcing.py -q` — 15 passed before changes |
| Post-change migration tests | PASS | same command after changes — 15 passed (details in run output) |
| New rollback-note tests | PASS | `tests/test_migration_drop_column_rollback_note.py` — 3 passed |
| Full regression suite | PASS | full `pytest` run on the environment venv (Python 3.12.13, SQLite 3.53.1) — see handoff tests[] for exact counts |

## 8. Evidence locations

- `app/database/migrations.py` (docstring note; `LATEST_MIGRATION_VERSION = 13`)
- `docs/DATABASE_MIGRATIONS.md`, `docs/DATA_MODEL.md` (F-1 refresh)
- `tests/test_migration_drop_column_rollback_note.py` (F-6 rollback-note test)
- This record (`docs/integration/wave1/13_MIGRATION_14_AMENDMENTS.md`)
- Source review: `worktrees/int-study-base/docs/integration/MIGRATION_14_DESIGN_REVIEW.md`
