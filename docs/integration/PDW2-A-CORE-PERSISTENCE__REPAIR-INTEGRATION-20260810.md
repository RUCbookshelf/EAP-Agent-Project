# PDW2-A-CORE-PERSISTENCE — REPAIR-INTEGRATION (CORE)

**Goal:** `PDW2-A-CORE-PERSISTENCE__REPAIR-INTEGRATION` — Wave-2 CORE
integration repair: migration-14 version bump, pin refresh, shared-contract
refresh, docs.
**Owner:** CORE — Shared Platform & Core
**Worktree:** `A:\EAP Agent Project\worktrees\shared-core` (branch
`dept/shared-core`)
**Starting SHA:** `2c3c288369d221e7340d49e4d3dbd62479d4a215`
**Date:** 2026-08-10

## 1. Scope applied (mechanical, integration-time landing repairs)

Everything below follows the migration-12 landing convention (commit
`c239de5`) and the shared-contract change process:

1. **Version single-sourcing** — `app/version.py`:
   `PLATFORM_DATABASE_MIGRATION_VERSION` bumped 13 → 14 (one line). The
   single-sourcing invariant (`LATEST_MIGRATION_VERSION ==
   PLATFORM_DATABASE_MIGRATION_VERSION`) is now satisfied against the
   migration-14 database (migrations.py was already at 14 at HEAD).
2. **Pinned test refresh (13 → 14)** — the 10 migration-era pinned test
   modules updated:
   - `tests/test_analysis_runs_v04.py` (migration_version pin)
   - `tests/test_calf_v08.py` (migration_version + upgrade pin + added
     14→13 rollback step)
   - `tests/test_diagnostic_calibration_v061.py` (migration_version +
     upgrade pins)
   - `tests/test_learner_model_v07.py` (`LATEST_MIGRATION_VERSION == 13` pin)
   - `tests/test_revision_v05.py` (migration_version pin)
   - `tests/test_snapshot_repository_v03.py` (two `LATEST_MIGRATION_VERSION`
     pins)
   - `tests/test_v06_configuration_dashboard.py` (migration_version pin)
   - `tests/test_v071_reliability_ui.py` (user_version + upgrade pins + added
     14→13 rollback step)
   - `tests/test_v095g_facade_contraction.py` (database_migration_version pin)
   - `tests/test_migrations_v02.py` — no literal change required (asserts via
     `LATEST_MIGRATION_VERSION` constant; no rollback step present, so no
     14→13 rollback addition needed).
3. **Shared-contract module-set manifest** —
   `verification/shared-core-h1/module_set_manifest.json` refreshed to record
   the FULL Wave-2 union module set: all wave2 module paths across
   CORE/LEARNER/L2/CORPUS/UX (the union of the five Wave-2 candidate module
   sets) plus `app/corpus/seccl.py` (which was already present in the tree but
   unrecorded). 30 paths added, sorted into the existing manifest order.
   The manifest now covers the union so the drift guard is GREEN at
   integration (PDW2-WU2-INT-GATE) when the five department candidates merge.
4. **Parity verifier refresh** —
   `verification/v0.9.5-e/compare_repository_parity.py`:
   - Frozen migrations SHA-256 (`_MIGRATIONS_WU3_SHA256`) refreshed to the
     current `app/database/migrations.py` fingerprint
     (`ea8e1f63...`), which includes migration 14.
   - `SERVICE_API_DIFF_ALLOWLIST` refreshed: a default allowlist constant
     (`_SERVICE_API_DIFF_ALLOWLIST`) now records the full current
     legitimately-evolved service/API diff vs the v0.9.5-E baseline
     (`769e6d8`), including the Wave-2 `app/api/routers/wave2.py` and
     `app/api/routers/wave2_modules/__init__.py` files, so the parity
     contract is self-contained when the runner does not export the env var.
5. **Docs refresh** — `docs/DATABASE_MIGRATIONS.md` (current version 14,
   applied migrations 1..14 with the new row, rollback range 14→13 through
   9→8, numbering-supersession note for the deferred `essays.domain` lane)
   and `docs/DATA_MODEL.md` (迁移 14 header, migration-14 paragraph, four new
   table rows) refreshed to migration 14.

## 2. What was NOT touched

- `app/database/migrations.py` — untouched (already migration 14 at HEAD).
- `app/api/main.py` — untouched.
- Any other product source file — untouched.
- Master checkout, other department worktrees, raw SWECCL — untouched.
- Pre-existing untracked evidence files in the worktree (ADR drafts and
  integration reports under `docs/`) — preserved untouched.
- No reset/clean/rebase/force update/push/PR/promotion.

## 3. Verification evidence

See the structured handoff `tests[]` for exact results and evidence. Focused
set (per acceptance gate): `tests/shared/test_version_single_sourcing.py`,
the 10 refreshed pin modules, `tests/test_shared_core_drift.py::
TestModuleSetManifest`, `tests/test_migrations_v02.py`, and
`tests/test_wave2_*.py`.

The manifest union is verified zero-mismatch directly: the manifest's wave2
entries exactly equal the union of the five Wave-2 candidate module sets (no
missing union path, no extra wave2 entry). The local-tree drift comparison
reports `missing` = the union paths that arrive with the other departments'
Wave-2 candidates at integration (LEARNER `learner/wave2/*`, L2 `l2/wave2/*`
and `wave2_modules/{revision,personalized}_api.py`, CORPUS
`corpus/routing.py`, UX `ui/wave2/*`) — expected pre-integration state by
design (packet note: manifest covers the union so the drift guard is GREEN at
integration).

Union zero-mismatch evidence (five worktrees' app/ trees vs manifest):
union 244 modules == manifest 244 modules; `missing = 0`, `added = 0`.
Local-tree check: `added = 0` (every module physically present in the CORE
worktree is recorded); `missing = 27` (the other-department union paths plus
`l2/__init__.py`, pending integration).

Parity verifier (run with command-scoped `safe.directory` env override, no
global config change): `migrations_source_parity: true`,
`service_api_domain_diff: []`, `signature_drift_count: 0`,
`sql_fingerprint_drift_count: 0`, `schema_constant_parity: true`,
`table_owners_unique: true`. The single remaining failures entry is the
pre-existing `prohibited_imports` docstring-substring flag on
`app/infrastructure/sqlite/repositories/wave2.py` (a docstring mention of
`app.database.repository.Database`, not an actual import; file was authored
by the parent Goal commit `2c3c288` and is outside this repair's write
scope). Exit 1 solely for that pre-existing class.

## 4. Findings

- **Union manifest is integration-forward by design.** The manifest records
  the full Wave-2 union (30 paths). The CORE worktree at this commit
  physically contains only the CORE-owned wave2 modules
  (`api/routers/wave2.py`, `api/routers/wave2_modules/__init__.py`,
  `infrastructure/sqlite/repositories/wave2.py`, `corpus/seccl.py`); the
  remaining union paths land at `PDW2-WU2-INT-GATE` when the five candidates
  merge. The drift guard (`TestModuleSetManifest`) is GREEN at integration.
- **Out-of-scope residual pins (disclosed, not repaired):**
  `tests/test_v095b_router_contract.py:242` and
  `tests/test_v097b_wu3_target_creation.py:327,340` still pin migration
  version 13. They are outside this packet's 10-file write scope; a
  follow-up mechanical refresh (13 → 14) is required before the full-suite
  drift guard can be GREEN in every module.
- **Pre-existing parity docstring flag:** `wave2.py` line 13 mentions
  `app.database.repository.Database` in its module docstring; the parity
  verifier's naive substring scan flags it as a prohibited import. Not a real
  import; pre-existing at HEAD; outside write scope.

## 5. Integration/promotion posture

- Verdict: see structured handoff (gate evidence complete for the scoped
  repairs; union zero-mismatch verified; focused verification GREEN).
- `integration_required`: true (Wave-2 candidates batched at
  `PDW2-WU2-INT-GATE`).
- `promotion_eligible`: false — no promotion performed or claimed.
- No push, no PR, no reset/clean/rebase/force update; master untouched;
  other department worktrees untouched; raw SWECCL untouched.

## 6. Artifacts

- `app/version.py`
- `tests/test_analysis_runs_v04.py`, `tests/test_calf_v08.py`,
  `tests/test_diagnostic_calibration_v061.py`, `tests/test_learner_model_v07.py`,
  `tests/test_revision_v05.py`, `tests/test_snapshot_repository_v03.py`,
  `tests/test_v06_configuration_dashboard.py`,
  `tests/test_v071_reliability_ui.py`,
  `tests/test_v095g_facade_contraction.py`
- `verification/shared-core-h1/module_set_manifest.json`
- `verification/v0.9.5-e/compare_repository_parity.py`
- `docs/DATABASE_MIGRATIONS.md`, `docs/DATA_MODEL.md`
- This report: `docs/integration/PDW2-A-CORE-PERSISTENCE__REPAIR-INTEGRATION-20260810.md`
