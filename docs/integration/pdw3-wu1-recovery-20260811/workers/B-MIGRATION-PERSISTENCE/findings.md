# Worker B Findings — Migration 15 / persistence / repository audit (READ-ONLY)

- task_id: PDW3-WU1-DECOMP-RECOVERY__B-MIGRATION-PERSISTENCE
- role: nested read-only review worker (PLANNING_DISABLED=1, no subagents)
- worktree: `A:\EAP Agent Project\worktrees\shared-core`
- branch / HEAD verified: `dept/shared-core` @ `7a9e4b470c41c0453a3795233f1bdd5c483d80ae`
  (command-scoped `git -c safe.directory` only; no global git config, no
  reset/clean/restore/stage/commit)
- Python runtime: `A:\EAP Agent Project\worktrees\shared-core\.venv\Scripts\python.exe`
- Date: 2026-08-11

## 1. Scope

Read-only audit of the preserved partial WU1 implementation for additive
Migration 15 (`review_scheduling_foundation`) and the shared SQLite
review/scheduling persistence and repository layer: migration list/DDL,
version single-sourcing, review repository round-trips, close/reopen
survival, single-file/single-engine enforcement, and the AGENTS.md
"no direct sqlite3 in core services" boundary. No product file, Program
Control file, or git state was modified; all writes are confined to this
worker directory (`findings.md` + `evidence/`).

Out of scope honored: no edits to `app/review` logic or `app/api` (Worker
A/C), no other worktrees, no raw SWECCL.

## 2. Files inspected (path:line)

| File | Notes |
| --- | --- |
| `app/database/migrations.py:16-23` | v15 note added to module docstring |
| `app/database/migrations.py:44` | `LATEST_MIGRATION_VERSION = 15` |
| `app/database/migrations.py:766-966` | `_migration_14` — untouched (no diff hunks inside; Wave-2 baseline protected) |
| `app/database/migrations.py:943-963` | `learning_items` DDL with `no_fsrs_note` default contract |
| `app/database/migrations.py:969-1081` | `_migration_15`: 3 new tables + 5 indexes, all `CREATE ... IF NOT EXISTS`, `PRAGMA user_version = 15` |
| `app/database/migrations.py:1092-1100` | `MIGRATIONS` dict; `15: ("review_scheduling_foundation", _migration_15)` |
| `app/database/migrations.py:1096-1121` | `upgrade()` runner (range loop, schema_migrations ledger, idempotent) |
| `app/database/migrations.py:1123-1168` | `rollback()`; `(15, 14)` ledger-only branch added |
| `app/version.py:44-49` | `PLATFORM_DATABASE_MIGRATION_VERSION: int = 15` |
| `app/database/repository.py:11-24, 146-147` | Wires `SQLiteWave2Repository` + `SQLiteReviewRepository` into single composition root |
| `app/infrastructure/sqlite/repositories/__init__.py:7, 20` | `SQLiteReviewRepository` export |
| `app/infrastructure/sqlite/repositories/review.py:76-111` | `save_practice_activity` (parameterized upsert) |
| `app/infrastructure/sqlite/repositories/review.py:147-220` | `record_review_event` — atomic event insert + scheduler-state upsert in one transaction |
| `app/infrastructure/sqlite/repositories/review.py:254-267` | `get_scheduler_state` |
| `app/infrastructure/sqlite/connection.py:30-54` | `SQLiteConnectionManager.connect/transaction` — the only sanctioned `sqlite3.connect` |
| `app/review/protocols.py:35-72` | `ReviewRepositoryProtocol` / `LearningItemReaderProtocol` |
| `app/review/service.py:71` | Service depends on `ReviewRepositoryProtocol`, no sqlite3 |
| `app/infrastructure/sqlite/repositories/system.py:16-19, 41-46` | `initialize()` -> `upgrade()`; `migration_version()` |
| `tests/review/test_migration_15.py` | 5 tests: fresh apply, idempotence, ledger rollback, version single-sourcing, `Database.initialize()` lands on 15 |
| `tests/review/test_review_repository.py` | 6 tests: round-trips, atomic event+state, list by item, close/reopen survival (Case E) |
| `tests/shared/test_version_single_sourcing.py:83-84` | Drift invariant `LATEST_MIGRATION_VERSION == PLATFORM_DATABASE_MIGRATION_VERSION` |
| `app/l2/wave2/sqlite_repository.py:70`, `app/learner/wave2/sqlite_repository.py:68` | Pre-existing, docstring-declared TEST-ONLY direct `sqlite3.connect` (not WU1 code, not composition-root-wired) |
| `app/config/settings.py:53` | `sqlite:///` prefix parsing — single SQLite file path (no second engine) |
| `app/api/main.py:126, 313`; `app/feedback/service.py:21` | Composition root instantiates `Database(settings.database_path)` — one DB path |

## 3. Tests / probes run (command, result, evidence path)

### 3.1 Required test suite

Command (run from worktree root, `PYTHONDONTWRITEBYTECODE=1`):

```
.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp <evidence>\pytest-tmp -q tests/review/test_migration_15.py tests/review/test_review_repository.py
```

Result: **10 passed in 8.95s**.
Evidence: `evidence/pytest-review.log`

### 3.2 Version single-sourcing drift suite

```
.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp <evidence>\pytest-tmp-version -q tests/shared/test_version_single_sourcing.py
```

Result: **13 passed** (includes drift invariant and version endpoint reporting).
Evidence: `evidence/pytest-version-single-sourcing.log`

### 3.3 Read-only probe (fresh / existing / idempotent / close-reopen / single-file)

```
.venv\Scripts\python.exe <evidence>\probe_migration15.py <evidence>
```

Result: **5/5 checks OK** (`evidence/probe_results.txt`, `evidence/probe-run.log`):

1. FRESH: empty DB -> `user_version=15`, `schema_migrations` = {1..15}, all
   3 new tables present alongside `learning_items`/`writing_tasks` — OK.
2. EXISTING: genuine migration-14 DB (upgrade run with latest capped at 14),
   Wave-2 rows inserted via `SQLiteWave2Repository` (LI000001, LI000002) ->
   upgrade to 15; rows byte-identical before/after — OK (no data loss).
3. IDEMPOTENT: second `upgrade()` on the 15 DB returns 15, table set and
   ledger unchanged — OK.
4. CLOSE/REOPEN: practice activity + review event + scheduler state written
   through `Database` A; all references dropped; reopened via `Database` B;
   event `RE000001`, activity `PA000001`, scheduler state (`state=review`,
   `last_review_event_id=RE000001`) all survive; `LearningItem LI000007`
   identity and full row identical — OK (stable identity).
5. SINGLE FILE: only the 3 probe-created `.db` files exist, opening the DB
   again creates no new file, `PRAGMA database_list` shows exactly 1 attached
   DB — OK (one SQLite file, no ATTACH).

### 3.4 Schema distinctness probe

```
<inline python over evidence\tmp\reopen.db>
```

Result: `learning_items` contains no FSRS state columns
(stability/difficulty/due/state/step); `no_fsrs_note` value =
"no FSRS scheduling or spaced-repetition state is stored in LearningItem v1";
`review_events` (19 cols) and `learning_item_scheduler_states` (9 cols) hold
1 row each, distinct from the LearningItem row — OK.
Evidence: `evidence/probe-distinctness.log`

## 4. Findings

### A — Blockers

None.

### B — Major

None.

### C — Minor

1. `SQLiteReviewRepository._next_suffix_id` (review.py:63-68) interpolates
   table/column names into SQL; call sites pass only internal constants
   (`practice_activities`, `review_events`, `PA`, `RE`), so there is no
   injection surface today. Keep the helper internal-only.

### D — Informational

1. Pre-existing `sqlite3.connect` call sites at
   `app/l2/wave2/sqlite_repository.py:70` and
   `app/learner/wave2/sqlite_repository.py:68` predate this WU1 (commits
   `0c98edb`, `b13155d`, `53b1911`), are explicitly documented TEST-ONLY,
   are used only by their own unit tests, create their own `wave2_l2_*` /
   `wave2_learner_*` tables in caller-passed temp DBs, and are never wired
   into the composition root. They are not part of the Migration-15 diff and
   do not violate the frozen contract for CORE services; flagged for the
   record so an integration gate can confirm they stay out of the root.
2. Migration-15 rollback is a ledger-only `pass` + `DELETE FROM
   schema_migrations WHERE version=15` (migrations.py:1133-1140, 1166),
   identical in spirit to the existing 14->13 rollback; re-apply is
   idempotent via `CREATE TABLE IF NOT EXISTS`. Data is intentionally
   preserved on rollback — matching the documented Wave-3 note.
3. `record_review_event` uses `INSERT OR REPLACE` for both the event and the
   scheduler state; identical review_event_id re-writes replace the row.
   Deterministic-ID callers must manage ID reuse; the repo does not guard
   against double-submitting the same event ID.

### E — Positive confirmations (frozen contracts)

1. Migration 15 is strictly additive after 14: creates ONLY
   `practice_activities` (16 cols + 2 indexes), `review_events` (19 cols + 3
   indexes), `learning_item_scheduler_states` (9 cols); no ALTER/DROP on any
   existing table; ordered last in `MIGRATIONS` (migrations.py:1099);
   `_migration_14` byte-identical to HEAD.
2. Fresh path reaches 15; existing Wave-2 (14 with data) path reaches 15 with
   rows preserved; re-run idempotent (probe 1-3; tests 1-3).
3. Version single-source holds: `app/version.py:47` == `migrations.py:44` ==
   ledger result; drift tests pass (13/13).
4. Review rows round-trip through the SAME SQLite file via the shared
   `SQLiteConnectionManager`; close/reopen/reload survival proven with
   stable LearningItem identity (probe 4; test Case E).
5. ReviewEvent rows are durable evidence, distinct from LearningItem
   scheduling state; FSRS state lives only in
   `learning_item_scheduler_states`; `learning_items` keeps its no-FSRS
   contract (probe 4; probe-distinctness).
6. CORE services (`app/review/service.py:71`) depend on repository protocols;
   no new direct `sqlite3.connect` outside `app/infrastructure/sqlite`.
7. One SQLite database file, one engine (sqlite3), no ATTACH, no second
   persistence authority introduced (probe 5).
8. No reset/clean/restore/rebase performed; worktree state untouched apart
   from files added under this worker's own directory.

## 5. Review questions answered

1. What does Migration 15 add? Tables `practice_activities`,
   `review_events`, `learning_item_scheduler_states` plus 5 indexes; strictly
   additive, ordered after 14 in the migration list.
2. Fresh path reaches 15 (ledger 1..15); existing 14-with-data path reaches
   15 with data preserved; re-running is idempotent — all proven.
3. Yes: `app/version.py` reports 15 and the drift tests enforce the invariant.
4. Yes: rows round-trip through the same file and survive close/reopen with
   stable LearningItem identity.
5. Yes: ReviewEvent rows are separate durable evidence rows; scheduler state
   is a separate per-LearningItem table; `learning_items` is untouched.
6. No CORE bypass found in the WU1 diff; the only direct `sqlite3.connect`
   outside infrastructure are the pre-existing TEST-ONLY L2/LEARNER modules
   (Finding D1).
7. No second database/engine/persistence authority introduced.

## 6. Blocker

None.

## 7. Verdict

**PASS**
