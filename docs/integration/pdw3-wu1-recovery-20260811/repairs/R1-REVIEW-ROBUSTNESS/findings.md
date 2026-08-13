# Repair R1 findings — review robustness / fail-closed boundaries

- task_id: PDW3-WU1-DECOMP-RECOVERY__R1-REVIEW-ROBUSTNESS
- status: DONE
- worktree / branch / HEAD: `A:\EAP Agent Project\worktrees\shared-core` /
  `dept/shared-core` @ `7a9e4b470c41c0453a3795233f1bdd5c483d80ae`
- date: 2026-08-11

## Changes (product files only; four of the four in-scope paths)

1. `app/infrastructure/sqlite/repositories/review.py` — D3/D4:
   `save_practice_activity` and the `review_events` insert are now
   append-only: `INSERT OR REPLACE` replaced by plain `INSERT` with an
   in-transaction duplicate pre-check plus a narrow `sqlite3.IntegrityError`
   fallback (PRIMARY KEY/UNIQUE conflict only). Duplicates raise
   `ReviewRepositoryConflictError("practice_activity_already_exists" /
   "review_event_already_exists")`. The scheduler-state upsert
   (`learning_item_scheduler_states`) intentionally remains
   last-write-wins (current state, not append-only evidence).
2. `app/review/protocols.py` — additive contract error signal
   `ReviewRepositoryConflictError` (kind + message), exported.
3. `app/review/service.py` — D3/D5/C9:
   - `_require_learning_item` now returns the durable LearningItem.
   - `record_review`: UTC-aware `reviewed_at` enforced before any work
     (`ReviewError("invalid_reviewed_at")`); event `student_id` must equal
     the LearningItem owner (`learning_item_owner_mismatch`); a provided
     `practice_activity_id` must exist (`practice_activity_not_found`) and
     belong to the same student (`practice_activity_owner_mismatch`).
   - `record_practice_activity`: activity `student_id` must equal the
     LearningItem owner (`practice_activity_owner_mismatch`).
   - Repository conflict signals are translated into the stable
     `ReviewError` path (same kinds).
4. `app/api/routers/review.py` — mapping: 404 = `learning_item_not_found`,
   `practice_activity_not_found`; 403 = `learning_item_owner_mismatch`,
   `practice_activity_owner_mismatch`; 409 =
   `practice_activity_already_exists`, `review_event_already_exists`; all
   other kinds 422. Narrow `except ValueError -> 422` fallback (C9) and
   Pydantic UTC-aware validators on `reviewed_at` / `occurred_at` /
   `completed_at` (malformed datetimes rejected at the boundary, no writes).

No FSRS semantics, rating-rule resolution, scheduler identity, migration
schema, or composition topology changed. No tests, migrations, Program
Control, git state, or files outside the in-scope list were touched.

## Verification

- Full review suite (packet command):
  `python -m pytest -p no:cacheprovider --basetemp <evidence>/pytest-tmp-final
  -q tests/review` -> **53 passed, 0 failed** (2 third-party warnings).
  Log: `evidence/pytest-review-suite-final.log` (first run:
  `evidence/pytest-review-suite.log`).
- Fail-closed probes (TestClient, raise_server_exceptions=False, isolated
  temp DB): **10/10 passed** (exit 0). Log + script:
  `evidence/probe-failclosed.log` / `evidence/probe-failclosed.py`.
  - P1 happy path unchanged: 200, three rating channels, provenance.
  - P2 nonexistent `practice_activity_id` -> 404
    (`practice_activity_not_found`), zero rows written.
  - P3 duplicate activity ID -> 409 (`practice_activity_already_exists`),
    original row intact (provenance batch 1 preserved).
  - P4 duplicate review-event ID -> 409 signal
    (`review_event_already_exists`), original row intact.
  - P5 cross-student event -> 403 (`learning_item_owner_mismatch`), no
    write; P6 event linking another student's activity -> 403
    (`practice_activity_owner_mismatch`), no write; P7 mismatched activity
    owner -> 403, no write.
  - P8 naive datetime -> 422, no write; P9 non-UTC datetime -> 422, no
    write; P10 service-level naive datetime -> `invalid_reviewed_at`.

## Conflicts for R3 / notes

- None: all 53 existing tests/review tests pass unchanged; no test asserted
  the old permissive behavior, so nothing to record for R3 beyond the new
  behavior itself (R3 may add regression tests for D3-D5/C9).
- R2 modified its owned root-test files in parallel (disjoint set); R1 made
  no test changes.
