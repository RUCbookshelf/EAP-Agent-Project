# CHECKPOINT 003 — Parent Test Evidence (Focused + Regression)

- Goal/run: `PDW3-WU2-LEARNER-ACK-ROUTES-PERSISTENCE-REPAIR-20260812`
  / `PDW3-WU2-LEARNER-ACK-ROUTES-PERSISTENCE-REPAIR-20260812__20260812T014849Z__710c45`
- All commands ran from `A:\EAP Agent Project\worktrees\learner` with the
  worktree `.venv`, `PYTHONDONTWRITEBYTECODE=1`, `-p no:cacheprovider`, and
  a workspace-local pytest basetemp (removed afterwards).

| Suite | Result | Evidence |
| --- | --- | --- |
| Repair Worker P focused persistence/evidence | PASS | `test_wu2_persistence_evidence.py` + `test_wu2_acknowledgement.py`: 80 passed, exit 0 |
| Repair Worker R route + journey service | PASS | `test_wu2_journey_routes.py` + `test_wu2_journey_history_transfer.py`: 25 passed; `tests/learner` sweep 287 passed |
| Parent focused WU2 (persistence/evidence/route/composition) | PASS | six `tests/learner/test_wu2_*.py` files: 161 passed, exit 0 |
| Journey/Wave-2/Learner regression | PASS | 436 passed, exit 0 (v095f4, v093c, v097b-wu6, v097c-wu1/wu2/wu4, tests/learner) |
| Practice/narrowing regression | FAIL (1 known stale pin) | 250 passed, 1 failed: `test_v097b_wu3_target_creation.py::TestMigration13::test_migration_preserves_existing_rows_and_rolls_back_non_destructively` (`upgrade() == 14` vs 15); outside the six user-authorized pins; CORE WU1 R2 reconciles this family on dept/shared-core |
| Composition/router/Wave-2 contract pins | FAIL (2 known unowned pins) | 28 passed, 2 failed: v095b exact-route pin (100 vs runtime 104); v095d pin (81 vs runtime 104); regeneration is INT-owned |
| Six authorized stale migration pins | PASS | `test_wave2_migration_v14.py` + `test_learner_model_v07.py` + `test_snapshot_repository_v03.py`: 18 passed, exit 0 |
| Migration/version pin family remainder | FAIL (9 known stale pins) | 15-file sweep: 176 passed, 15 failed; 6 reconciled (now PASS), 9 stale `==14` assertions in 8 root files; CORE WU1 R2 already reconciles them on dept/shared-core |

## Durability and evidence-lookup proof (parent composition tests)

- `SQLiteAcknowledgementRepository` and `SQLiteAcknowledgementEvidenceLookup`
  resolve through the same `Database._connection_manager` as every other
  repository (one SQLite authority).
- A real `history_evidence_registry` row validates as `HistoryEvidence`; a
  positive history-signal acknowledgement POST returns 200, persists, and is
  readable by a fresh app over the SAME SQLite file (durability across
  process/app lifetime).
- Unknown evidence returns 404 with zero store writes; consent gates run
  before any write; `submitted` attempt statuses never map to completed
  practice (fail closed); absent `review_events`/`learner_observed_evidence`
  tables fail closed.
- The CORE typed boundary accepts an injected fake `ReviewService` through
  `create_app(core_review_service=...)`; default composition remains
  `core_review_service_missing` (fail closed, no write) until INT injects
  the real CORE service.

## Cleanup

- All `.pytest-tmp*` basetemp directories created by the parent were removed
  after the runs; git status shows no residual parent temp artifacts.
