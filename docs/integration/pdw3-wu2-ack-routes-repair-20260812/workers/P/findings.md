# Repair Worker P — Durable Acknowledgement Persistence + Qualified Evidence Lookup — Findings

- Goal/run: `PDW3-WU2-LEARNER-ACK-ROUTES-PERSISTENCE-REPAIR-20260812`
- Worker: `P`
- Packet: `docs/integration/pdw3-wu2-ack-routes-repair-20260812/packets/P-PERSISTENCE-EVIDENCE.md`
- Model: `deepseek/deepseek-v4-flash`; reasoning: `ultra` (proxy-injected); `PLANNING_DISABLED=1`
- Authorized worktree: `A:\EAP Agent Project\worktrees\learner`
- Branch / HEAD verified: `dept/feedback-learner` @ `7a9e4b470c41c0453a3795233f1bdd5c483d80ae` (matches packet)
- Result: **DONE** — all required tests pass; six pre-existing root `== 14` migration-version pins fail and are OUT OF SCOPE (see Compatibility risks).
- No commit, push, PR, merge, promotion, reset, clean, restore, rebase, Program Control write, or edit outside the owned write scope.

## 1. Files changed (owned write scope, exact)

| File | Change |
| --- | --- |
| `app/database/migrations.py` | `LATEST_MIGRATION_VERSION` 14 -> 15; new `_migration_15_learner_acknowledgement_persistence` (one table + two indexes, `CREATE ... IF NOT EXISTS` only, `PRAGMA user_version = 15`); registry entry `15: ("learner_acknowledgement_persistence", ...)`; `rollback()` pair set gains `(15, 14)` and a ledger-only `if current == 15: pass` branch. Migrations 1-14 bodies and registry entries untouched. |
| `app/version.py` | `PLATFORM_DATABASE_MIGRATION_VERSION: int = 15` (single-source invariant with `LATEST_MIGRATION_VERSION`). |
| `app/infrastructure/sqlite/repositories/acknowledgement.py` | NEW: `SQLiteAcknowledgementRepository` (append-only store) and `SQLiteAcknowledgementEvidenceLookup` (qualified evidence lookup). |
| `app/infrastructure/sqlite/repositories/__init__.py` | Additive imports + `__all__` entries for the two new classes. |
| `app/learner/acknowledgement_contracts.py` | Additive link fields on `AcknowledgementRequest` and `AcknowledgementRecord`: `learning_item_id`, `authentic_evidence_status` (`Literal["insufficient","present"]`), `practice_activity_id`, `review_event_id`; strip/blank-reject validator; docstring note on bounded descriptive semantics. Existing fields/validators and `extra="forbid"` unchanged. |
| `app/learner/acknowledgement.py` | `AcknowledgementStoreConflictError` (kind/message); `_check_links()` gate called between `_check_source_records` and `_check_text`; link fields wired into the assembled record; `store.append` wrapped to translate store conflicts to `AcknowledgementError(exc.kind, exc.message)`; module docstring gate list now 11 gates; `__all__` updated. |
| `tests/learner/test_wu2_persistence_evidence.py` | NEW focused tests (52 tests). |
| `docs/integration/pdw3-wu2-ack-routes-repair-20260812/workers/P/findings.md` | This report. |

The five pre-existing untracked evidence paths and `tests/learner/__init__.py` were preserved untouched, as were every existing WU2 file in `app/learner/`, `app/practice/`, `app/journey/`, `app/api/`, `tests/learner/`, and `docs/integration/pdw3-wu2-learner-20260812/` outside the listed scope. No `app/api/main.py`, `app/api/deps.py`, `app/api/routers/*`, `app/practice/`, `app/journey/`, migration 1-14 body, or other test file was edited.

## 2. Verification

Worktree `.venv`; `PYTHONDONTWRITEBYTECODE=1`; `-p no:cacheprovider`.

### Required command (packet contract)

`.venv/Scripts/python.exe -m pytest tests/learner/test_wu2_persistence_evidence.py tests/learner/test_wu2_acknowledgement.py -q --no-header -p no:cacheprovider`

- Exit code: `0`
- Result: **80 passed, 1 warning** (StarletteDeprecationWarning from the fastapi.testclient import; pre-existing, unrelated).
  - New `test_wu2_persistence_evidence.py`: 52 tests.
  - Existing `test_wu2_acknowledgement.py`: 28 tests — stays green unchanged.

### Evidence covered by the new tests (per packet contract)

- Migration 15: fresh upgrade to 15 with table + ledger row; rollback 15->14 ledger-only preserves the row and table; re-upgrade 14->15 idempotent and preserves the row; repeated upgrade idempotent with one ledger row; non-adjacent rollback raises `ValueError`.
- Durable store: append/get roundtrip preserving every field (JSON lists/dicts, ISO datetimes, null optionals, link fields); learner scoping + `recorded_at, acknowledgement_id` ordering; close/reopen durability on the SAME SQLite file (new repository instance re-reads the row); duplicate-id conflict (`conflict`) and duplicate evidence-set conflict (`duplicate_acknowledgement`, order-insensitive set) with no write.
- Evidence lookup: real `history_evidence_registry` row resolves and model-validates as `HistoryEvidence`; real `practice_evaluations` row with `completion_status=completed` resolves to a qualified `PracticeProvenanceRecord` (evaluation_id/attempt_id/evaluator_version filled from stored fields) AND a positive `PRACTICE_RESULT` acknowledgement succeeds and persists; attempt with stored status `submitted` fails closed (no fabricated mapping); `learning_items` row resolves ownership and returns the row; absent `learner_observed_evidence` and absent CORE `review_events` tables fail closed; cross-student lookup fails closed.
- Service link gates: unknown learning item (`learning_item_not_found`), mismatched learning item (`learning_item_owner_mismatch`), unknown practice activity (`practice_activity_not_found`), review link fails closed with the CORE table absent (`review_event_not_found`), invalid runtime `authentic_evidence_status` (`invalid_authentic_evidence_status`) — all with no store write; valid links acknowledge and carry the link fields.
- Defense in depth: a store rejecting at append time is translated to `AcknowledgementError(exc.kind, exc.message)`.
- Contract typing: blank link ids rejected (request and record); ids stripped; `authentic_evidence_status` literal enforced.

### Supplementary drift checks (read-only, evidence only)

`.venv/Scripts/python.exe -m pytest tests/test_wave2_migration_v14.py tests/test_learner_model_v07.py tests/test_snapshot_repository_v03.py tests/shared/test_version_single_sourcing.py tests/test_migrations_v02.py tests/test_migration_drop_column_rollback_note.py -q --no-header -p no:cacheprovider`

- Exit code: `1`; **30 passed, 6 failed**.
- Passing: `tests/test_migrations_v02.py` (all), `tests/test_migration_drop_column_rollback_note.py` (all), `tests/shared/test_version_single_sourcing.py` (all — confirms `LATEST_MIGRATION_VERSION == PLATFORM_DATABASE_MIGRATION_VERSION == 15` invariant holds).
- Failing (exactly the six stale `== 14` pins, all outside worker P's write scope):
  - `tests/test_wave2_migration_v14.py::test_fresh_db_upgrades_to_migration_14_with_wave2_tables` (asserts `LATEST_MIGRATION_VERSION == 14`), `::test_rollback_14_to_13_...` (rolls back from 15), `::test_legacy_database_upgrades_through_14_...` (asserts `migration_version() == 14`).
  - `tests/test_learner_model_v07.py::test_migration_8_...` (asserts `... == LATEST_MIGRATION_VERSION == 14`).
  - `tests/test_snapshot_repository_v03.py::test_snapshot_save_latest_history_and_restart` and `::test_v02_database_upgrades_...` (assert `... == LATEST_MIGRATION_VERSION == 14`).

## 3. Compatibility risks / decisions for the parent

1. **Stale root `== 14` pins (6 failures, out of scope).** Bumping `LATEST_MIGRATION_VERSION` to 15 necessarily breaks the six assertions listed above in `tests/test_wave2_migration_v14.py`, `tests/test_learner_model_v07.py`, and `tests/test_snapshot_repository_v03.py`. The packet forbids editing any test file other than the two named, so these remain for the parent/INT to reconcile (CORE WU1 followed the same pattern with its own root reconciliation). Worker P made NO edit to these files.
2. **`AcknowledgementStoreConflictError` single definition.** The packet asks the repository module to define it (section 2) and the service module to add it (section 4). Two divergent class identities would break the service's defense-in-depth translation, so it is defined ONCE in `app/learner/acknowledgement.py` (the core module, mirroring CORE's `app/review/protocols.py` repository-conflict pattern) and imported by the durable repository, which raises it. The functional requirement (store conflict -> `AcknowledgementError` with the same kind/message) is test-covered.
3. **Loose structural links, no FKs.** `learning_item_id`, `practice_activity_id`, `review_event_id` are stored without FK per the packet; `learner_acknowledgements.learner_id` is the only FK (to `students`). The CORE `review_events` and `learner_observed_evidence` tables are absent on this branch; both lookup branches fail closed via `sqlite_master` checks.
4. **No status mapping.** `submitted` attempts and non-member statuses fail closed in the lookup; `completion_status` maps only when it is an exact `PracticeActivityStatus` member. `evaluator_version` is `None` when not stored. `occurred_at` falls back to the stored `created_at` column only when the payload timestamp is absent (both stored values; nothing fabricated).
5. **Concurrent worker R.** While worker P ran, sibling worker R's authorized files appeared in the shared worktree (`app/api/routers/journey.py` modified, `tests/learner/test_wu2_journey_routes.py` added). Worker P did not touch them and reports them as peer output.
6. **No API/composition wiring.** Per packet, the parent composes the repository/lookup into the composition root (`app/api/main.py`, `app/api/deps.py`, routers) after worker P returns; the API still returns `503 evidence_unavailable` until then, as recorded in the WU2 canonical handoff.
7. **Migration rollback is ledger-only.** 15->14 preserves the table/data by design (additive migration); the common ledger `DELETE` in `rollback()` handles the version-15 ledger row (the `if current == 15:` branch is `pass`).

## 4. Boundary compliance

- Read-only Git checks used command-scoped `git -c safe.directory` (no global config change).
- No commit/push/PR/merge/promotion/reset/clean/restore/rebase; no Program Control write; no other worktree touched; no raw SWECCL access; no API keys or secrets in code/tests/docs.
- All writes confined to the eight owned paths in section 1.
