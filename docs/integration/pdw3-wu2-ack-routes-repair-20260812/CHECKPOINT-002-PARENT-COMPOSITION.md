# CHECKPOINT 002 — Parent Composition Wiring (Durable Store + Evidence Lookup + CORE Typed Boundary)

- Goal/run: `PDW3-WU2-LEARNER-ACK-ROUTES-PERSISTENCE-REPAIR-20260812`
  / `PDW3-WU2-LEARNER-ACK-ROUTES-PERSISTENCE-REPAIR-20260812__20260812T014849Z__710c45`
- Owner: LEARNER (parent), written after Workers P and R returned and were
  audited.

## Worker audit summary

- Worker P (persistence/evidence): DONE. 80 focused tests passed
  (`test_wu2_persistence_evidence.py` + existing `test_wu2_acknowledgement.py`).
  Six stale root `==14` migration pins recorded as out-of-scope.
- Worker R (routes): DONE. 25 focused route/service tests passed; full
  `tests/learner` sweep 287 passed. The two approved routes were verified in
  the actual router file by the parent.

## Parent composition changes (all in the authorized learner worktree)

- `app/api/main.py`:
  - Removed the non-durable `_AppendOnlyAcknowledgementStore` placeholder.
  - `_build_services(..., core_review_service: CoreReviewServicePort | None = None)`:
    acknowledgement service now composes `SQLiteAcknowledgementRepository`
    and `SQLiteAcknowledgementEvidenceLookup` over the single
    `Database._connection_manager` (one SQLite authority); the
    practice/review orchestrator receives the typed optional CORE boundary.
  - `create_app(..., core_review_service=None)` and `_build_full_app` pass
    the typed boundary through for the INT composition root.
  - No new state keys were added to the service graph (kept the
    `test_composition_root.py` expected-key contract intact).
- `app/api/routers/acknowledgement.py`: added HTTP mappings for the new
  fail-closed link kinds (404/403 for learning item, practice activity,
  review event; 422 for invalid authentic-evidence status).
- `tests/learner/test_wu2_api_composition.py`: updated to the new semantics
  (unknown evidence -> 404 with no write; durable store/evidence types over
  the single connection manager; positive history-signal acknowledgement
  persists across app rebuild on the same SQLite file; CORE typed boundary
  injection accepted; the two Journey projection routes registered exactly
  once).

## Stale migration pins (user-authorized, exactly six)

Worker P recorded six stale `==14` migration-version assertions in three
root test files. Under explicit user authorization, the parent reconciled
them mirroring CORE WU1 R2 semantics (LATEST==15), with the learner branch's
migration-15 identity `learner_acknowledgement_persistence`:

- `tests/test_wave2_migration_v14.py` (three tests: fresh-DB LATEST upgrade
  with ledger 14+15 names; v14-era data surviving 15->14->13 rollbacks and
  re-upgrade; legacy DB upgrade to LATEST).
- `tests/test_learner_model_v07.py` (one assertion -> LATEST).
- `tests/test_snapshot_repository_v03.py` (two assertions -> LATEST).

Result: `18 passed, 0 failed` across the three files.

## Resource hygiene

- No Git mutation, no Program Control write, no promotion, no other-worktree
  change. HEAD unchanged at `7a9e4b470c41c0453a3795233f1bdd5c483d80ae`.
- The five pre-existing untracked evidence paths and all existing WU2 files
  are preserved; temporary parent pytest basetemp directories were removed.
