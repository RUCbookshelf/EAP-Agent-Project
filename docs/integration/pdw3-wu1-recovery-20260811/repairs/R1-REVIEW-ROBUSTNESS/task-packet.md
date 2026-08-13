# Task Packet — Repair R1: review robustness / fail-closed boundaries

- task_id: PDW3-WU1-DECOMP-RECOVERY__R1-REVIEW-ROBUSTNESS
- parent_work_unit: PDW3-WU1-CORE-DECOMPOSITION-RECOVERY-20260811 / Phase 2
- task_class: ENGINEERING (bounded repair slice)
- risk: MEDIUM
- role: repair worker (deepseek/deepseek-v4-flash, ultra, PLANNING_DISABLED=1)
- worktree: A:\EAP Agent Project\worktrees\shared-core
- branch / HEAD: dept/shared-core @ 7a9e4b470c41c0453a3795233f1bdd5c483d80ae

## Objective

Repair the preserved WU1 partial implementation for the confirmed findings
D3 (FK failure surfaces as 500), D4 (duplicate practice-activity/review-event
IDs silently overwrite durable evidence), D5 (no student/ownership identity
binding), and C9 (client-caused ValueError surfaces as 500) from the Phase-1
inventory. Product files only; tests/review changes belong to R3.

## Context

Read first:
- inventory: docs/integration/pdw3-wu1-recovery-20260811/inventory/A-B-C-D-E-PARTIAL-DIFF-INVENTORY.md (D3-D5, C9)
- Worker C findings: docs/integration/pdw3-wu1-recovery-20260811/workers/C-CONTRACTS-COMPOSITION-EVIDENCE/findings.md
- Worker A findings E1/E2: docs/integration/pdw3-wu1-recovery-20260811/workers/A-FSRS-SCHEDULER/findings.md
- Evidence probes: workers/C-CONTRACTS-COMPOSITION-EVIDENCE/evidence/probe-edge-cases*.log

## In scope (write)

- app/api/routers/review.py
- app/review/service.py
- app/review/protocols.py (only if the repository/service contract needs an
  explicit error signal; keep additive)
- app/infrastructure/sqlite/repositories/review.py

## Out of scope

- tests/review/** (owned by R3), any other tests, migrations, version.py,
  pyproject.toml, uv.lock, app/api/main.py, Program Control, other
  worktrees, raw SWECCL.
- Any change to FSRS semantics, rating-rule resolution, scheduler identity,
  migration schema, or composition topology.

## Frozen contracts

- One application/process/SQLite database/API namespace/composition root.
- ReviewEvent is durable evidence; duplicate event/activity IDs must never
  silently replace prior rows (append-only / reject-on-conflict).
- `learning_item_scheduler_states` remains ONE current-state row per
  LearningItem (upsert is intended for this state row only).
- Fail-closed: invalid references, duplicates, ownership mismatches, and
  malformed datetimes are rejected with no partial writes.
- ReviewError kinds stay stable for router mapping; add kinds only
  additively.
- No semantic leakage; FSRS state remains scheduling state only.

## Implementation requirements

1. D3: a review referencing a nonexistent `practice_activity_id` must fail
   closed with a clean mapped response (suggest: `ReviewError` kind
   `practice_activity_not_found` -> HTTP 404; or repository-level
   pre-validation in the service). Verify no row is written.
2. D4: `save_practice_activity` and the `review_events` insert must reject a
   duplicate existing ID (suggest: `practice_activity_already_exists` /
   `review_event_already_exists` -> HTTP 409) instead of `INSERT OR REPLACE`
   overwriting evidence. The scheduler-state upsert may remain
   last-write-wins (it is current state, not append-only evidence).
3. D5: enforce ownership identity binding:
   - a review event's `student_id` must match the owner of the referenced
     LearningItem;
   - `practice_activity_id` (when provided) must exist AND belong to the
     same student as the event/LearningItem;
   - `record_practice_activity` must reject activities whose
     `student_id` does not match the LearningItem owner.
   Suggest kinds: `learning_item_owner_mismatch`,
   `practice_activity_owner_mismatch` -> HTTP 403 (add mapping in router).
4. C9: client-caused input errors that reach the service as ValueError
   (e.g., naive/non-UTC `reviewed_at`) must map to 422 without a 500 or
   traceback. Keep the stable `ReviewError` path; wrap or validate narrowly
   at the router/service boundary.
5. Keep the router thin: validation/translation in router + service; SQL in
   the infrastructure repository.

## Acceptance criteria

- All existing tests/review tests still pass (53/53) — R1 must not regress
  them; if a test asserts the old permissive behavior, DO NOT edit it; record
  the conflict for R3 instead.
- Probes (in your evidence dir) demonstrate: FK-nonexistent activity ->
  4xx, no write; duplicate PA/RE ID -> 409, original row intact; cross-student
  event/activity -> 403; naive datetime -> 422; valid happy path unchanged
  (200, three channels, provenance).
- No changes outside the five in-scope product files.

## Verification

- Run: .venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp
  <evidence>/pytest-tmp -q tests/review
- Run your own read-only probes via TestClient with
  raise_server_exceptions=False; save full logs under
  docs/integration/pdw3-wu1-recovery-20260811/repairs/R1-REVIEW-ROBUSTNESS/evidence/
- Set PYTHONDONTWRITEBYTECODE=1. Use command-scoped
  `git -c safe.directory='A:/EAP Agent Project/worktrees/shared-core'` only.

## Protected files

- All pre-existing modified/untracked files not in your in-scope list.
- app/database/migrations.py (Migration 14 and 15 read-only), app/version.py,
  pyproject.toml, uv.lock, tests/**, Program Control files.

## Output

- findings/evidence: docs/integration/pdw3-wu1-recovery-20260811/repairs/R1-REVIEW-ROBUSTNESS/
  (write only under this directory)
- Modified product files as listed in your return.

## Return contract

Return: status (DONE / DONE_WITH_CONCERNS / BLOCKED); final result; modified
files (exact paths); verification results with evidence paths; blockers or
risks (or "无"). Do not return full logs.

