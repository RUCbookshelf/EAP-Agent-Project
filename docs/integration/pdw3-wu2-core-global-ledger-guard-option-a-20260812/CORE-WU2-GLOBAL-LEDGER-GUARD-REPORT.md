# CORE WU2 Option A Global Integer Ledger Guard - Report

- run_id: `PDW3-WU2-CORE-GLOBAL-LEDGER-GUARD-OPTION-A-20260812__20260812T043919Z__439e0b`
- goal_id: `PDW3-WU2-CORE-GLOBAL-LEDGER-GUARD-OPTION-A-20260812`
- owner: CORE
- worktree / branch / HEAD: `A:\EAP Agent Project\worktrees\shared-core` /
  `dept/shared-core` @ `7a9e4b470c41c0453a3795233f1bdd5c483d80ae`
- verdict: GREEN (gate evidence complete; candidate qualified for
  department-level acceptance; integration/promotion remain separate)
- handoff state: `HANDOFF_PENDING_ACCEPTANCE` (no self-close)

## 1. Preflight (live Git and Program Control)

| Check | Live value | Packet expectation | Result |
| --- | --- | --- | --- |
| primary repo root | `A:/EAP Agent Project/writing-feedback-mvp` | primary repository | PASS |
| master branch | `master` | `master` | PASS |
| master HEAD | `7a9e4b470c41c0453a3795233f1bdd5c483d80ae` | promoted baseline | PASS |
| master status | pre-existing dirty files only | DIRTY_PRESERVED | PASS |
| CORE worktree | `...\worktrees\shared-core` on `dept/shared-core` @ `7a9e4b4` | authorized worktree/branch | PASS |
| CORE status | preserved WU1/WU2 dirty + untracked candidate | preserve everything | PASS |

Program Control artifacts read: `WORKSTREAM_REGISTRY.json`,
`PROGRAM_STATUS.md`, `DEPENDENCY_GRAPH.md`, `PROMOTION_HISTORY.md`,
`WORKTREE_REGISTRY.md`, the dispatch record, the completed INT adjudication
packet/report, the CORE composition-repair handoff, and the worktree
`AGENTS.md` plus the packet's development docs.

## 2. Option A context

The user selected Option A: CORE retains the single global integer Migration
15 identity `review_scheduling_foundation`; LEARNER acknowledgement
persistence will move to global Migration 16 later. INT's read-only
adjudication (`PDW3-WU2-INT-MIGRATION-LEDGER-ADJUDICATION-20260812`)
recorded that CORE already owns migration execution/numbering and that no
governing record allocated 15 uniquely before the user decision.

## 3. What already existed (preserved, not rewritten)

- `app/database/migrations.py`: `LATEST_MIGRATION_VERSION = 15`;
  `MIGRATIONS[15] = ("review_scheduling_foundation", _migration_15)`; the
  real `_migration_15` body creating the three CORE table families
  `practice_activities`, `review_events`, `learning_item_scheduler_states`;
  ledger-only rollback (15,14) that preserves tables/data.
- `app/version.py:47`: `PLATFORM_DATABASE_MIGRATION_VERSION: int = 15`.
- Focused tests already covering fresh apply, v14-era upgrade, idempotence,
  and rollback safety.

## 4. What this Goal added (bounded repair only)

### 4.1 CORE-owned source/consumer seam (`app/database/migrations.py`)

Added after the `MIGRATIONS` registry (lines 1120-1162):

- `GLOBAL_MIGRATION_LEDGER_OWNER = "CORE"`
- `GLOBAL_MIGRATION_LEDGER_VERSION_15 = 15`
- `GLOBAL_MIGRATION_LEDGER_VERSION_15_NAME = "review_scheduling_foundation"`
- `assert_global_migration_15_identity() -> tuple[int, str]` - runtime guard
  that fails fast if `LATEST_MIGRATION_VERSION` drifts from 15, the registry
  entry at 15 is missing/renamed, or the CORE identity name is duplicated at
  any other version.

The module docstring now records the user-authorized Option A allocation
(lines 27-32). The Migration 15 body and numbering are untouched.

The seam is deliberately just the constants + guard on the existing single
`MIGRATIONS` registry and the existing `app.database.upgrade`/`rollback`
runners: the later LEARNER Migration 16 must consume these same references on
the same `sqlite3` connection - no second migration runner, no second
SQLite database, no renumbering of 15.

### 4.2 Focused tests (`tests/review/test_migration_15_global_ledger_guard.py`)

7 tests: Option-A identity constants; unique ledger identity at 15; fresh
database ledger has exactly one row at 15; guard detects rename at 15; guard
detects `LATEST` drift; guard detects duplicate identity at 16; and the
single-runner/single-database consumer seam (same `upgrade`/`rollback`
objects via `app.database`, rollback 15->14, re-apply, one ledger row at 15).

## 5. Test-first evidence (exact commands and results)

All pytest runs used the worktree-local `.venv` Python 3.12.13 and a
dedicated writable basetemp (the shared default pytest temp root is not
readable in this sandbox; this is an environment limitation, not a product
defect).

### Red (before implementation)

Command:

```powershell
& 'A:\EAP Agent Project\worktrees\shared-core\.venv\Scripts\python.exe' -m pytest -p no:cacheprovider -q --basetemp <writable-temp> tests/review/test_migration_15_global_ledger_guard.py
```

Result: `ERROR collecting tests/review/test_migration_15_global_ledger_guard.py`
-> `ImportError: cannot import name 'GLOBAL_MIGRATION_LEDGER_OWNER' from
'app.database.migrations'`. Red confirmed: the seam did not exist.

### Green (after implementation)

New guard suite:

```text
7 passed in 2.12s
```

Complete focused migration/ledger set:

```powershell
& 'A:\EAP Agent Project\worktrees\shared-core\.venv\Scripts\python.exe' -m pytest -p no:cacheprovider -q --basetemp <writable-temp> --junitxml=docs\integration\pdw3-wu2-core-global-ledger-guard-option-a-20260812\evidence\junit-focused.xml tests/review/test_migration_15_global_ledger_guard.py tests/review/test_migration_15.py tests/test_wave2_migration_v14.py tests/shared/test_version_single_sourcing.py
```

```text
30 passed, 2 warnings in 17.02s
PYTEST_EXIT=0
```

### Probe (real migrations on temporary auto-cleaned SQLite files)

```powershell
& 'A:\EAP Agent Project\worktrees\shared-core\.venv\Scripts\python.exe' docs\integration\pdw3-wu2-core-global-ledger-guard-option-a-20260812\evidence\probe_global_ledger_option_a.py
```

Key outputs (full log: `evidence/probe-global-ledger-option-a.log`):

```text
LATEST_MIGRATION_VERSION=15
PLATFORM_DATABASE_MIGRATION_VERSION=15
GLOBAL_MIGRATION_LEDGER_OWNER=CORE
GLOBAL_MIGRATION_LEDGER_VERSION_15=15
GLOBAL_MIGRATION_LEDGER_VERSION_15_NAME=review_scheduling_foundation
MIGRATIONS[15]=('review_scheduling_foundation', <function _migration_15 ...>)
assert_global_migration_15_identity()=(15, 'review_scheduling_foundation')
fresh upgrade()=15
fresh PRAGMA user_version=15
fresh schema_migrations rows at 15=[(15, 'review_scheduling_foundation')]
fresh review table families present=True missing=[]
v14-era PRAGMA user_version before upgrade=14
v14-era review tables before upgrade=[]
v14-era upgrade()=15; PRAGMA user_version=15
v14-era Wave-2 rows preserved: task=True item=True
v14-era review table families present=True
rollback 15->14=14; review tables preserved=True; ledger rows at 15=0
re-apply upgrade()=15; ledger rows at 15=1
PROBE_OK
PROBE_EXIT=0
```

## 6. Acceptance mapping

| Requirement | Evidence |
| --- | --- |
| Single global integer ledger keeps 15 uniquely named `review_scheduling_foundation` | registry identity + unique-identity test + fresh ledger row `[(15, 'review_scheduling_foundation')]` + guard duplicate probe |
| CORE stays at `LATEST_MIGRATION_VERSION=15` and `PLATFORM_DATABASE_MIGRATION_VERSION=15` | probe constants + `test_version_single_sourcing.py` drift contract |
| Fresh DB applies the real Migration 15 body | fresh `upgrade()=15`, `PRAGMA user_version=15`, three families present |
| v14-era DB upgrade applies Migration 15 and preserves Wave-2 data | genuine v14 DB (`_upgrade_to(14)`), seeded `writing_tasks`/`learning_items`, upgrade to 15, rows preserved, families added |
| Non-destructive rollback 15->14 | `rollback(connection,14)=14`, tables preserved, ledger row 15 removed, re-apply restores exactly one row at 15 |
| Canonical CORE-owned seam for later LEARNER Migration 16 | constants + `assert_global_migration_15_identity()` + single `MIGRATIONS`/`upgrade`/`rollback` references; no second runner/database |
| No LEARNER Migration 16 / no renumbering / no body change | write scope respected; no LEARNER product files touched |

## 7. Findings

- The CORE candidate already satisfied the migration identity/body and the
  fresh/v14/rollback behavior; this Goal added the missing guard evidence and
  the canonical consumer seam without rewriting working code.
- The seam is a pure additive guard on the existing runner; it does not add
  LEARNER acknowledgement semantics, a second runner, or a second database.
- All pre-existing dirty/untracked files in `shared-core` are preserved
  byte-for-byte (status snapshots in `evidence/`).
- `final_sha == starting_sha == 7a9e4b...`: no commit was created; the
  candidate remains the preserved uncommitted CORE WU1/WU2 tree plus this
  bounded WU2 guard repair.

## 8. Resource hygiene

- Only `app/database/migrations.py` (seam only), `tests/review/` (new guard
  tests), and the new Option-A evidence directory were written.
- No Program Control, LEARNER, INT, master, or other worktree writes.
- No push/PR/merge/promotion/reset/clean/restore/rebase; no commit/stage.
- Probe databases are temporary and auto-cleaned; pytest basetemp lives under
  the writable system temp directory.
- No raw SWECCL access; no mastery/proficiency/CEFR/learning-gain claims.
