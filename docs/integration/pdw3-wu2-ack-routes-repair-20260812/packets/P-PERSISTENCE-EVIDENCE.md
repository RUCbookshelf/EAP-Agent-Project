# Repair Worker P — Durable Acknowledgement Persistence + Qualified Evidence Lookup

You are a nested implementation worker for
`PDW3-WU2-LEARNER-ACK-ROUTES-PERSISTENCE-REPAIR-20260812`.

## Mandatory execution contract

- Model: `deepseek/deepseek-v4-flash`
- Reasoning: `ultra` (injected by the opencodex proxy; do not change it)
- Environment: `PLANNING_DISABLED=1` (already set by the parent dispatcher)
- Authorized worktree: `A:\EAP Agent Project\worktrees\learner`
- Branch: `dept/feedback-learner`; HEAD: `7a9e4b470c41c0453a3795233f1bdd5c483d80ae`
- No provider/model/reasoning substitution. No commit, push, PR, merge,
  promotion, reset, clean, restore, rebase, or Program Control write.
- Do not modify Program Control, other worktrees, Git history, or
  promotion state. Do not touch raw SWECCL.
- Do not edit any file outside your owned write scope. If a requirement
  cannot be satisfied inside that scope, stop and report `BLOCKED` with the
  exact boundary; do not edit outside scope.

## Preserve (never modify or delete)

- The five pre-existing untracked evidence paths:
  `docs/integration/LEARNER-FOUNDATION-FREEZE-20260809.md`,
  `docs/integration/PDW1-ALIGN-LEARNER-B6FCE9-20260809.md`,
  `docs/integration/PDW2-ALIGN-LEARNER-59500127-20260810.md`,
  `docs/integration/PDW3-ALIGN-LEARNER-7A9E4B-20260811.md`,
  `tests/learner/__init__.py`.
- Every existing WU2 file under `app/learner/`, `app/practice/`,
  `app/journey/`, `app/api/`, `tests/learner/`, and
  `docs/integration/pdw3-wu2-learner-20260812/`. You may only *extend*
  the exact files listed in your write scope.

## Owned write scope (exact)

1. `app/database/migrations.py` — additive learner migration 15 only.
   Do NOT touch the bodies or registry entries of migrations 1-14.
2. `app/version.py` — bump only `PLATFORM_DATABASE_MIGRATION_VERSION` to 15.
3. `app/infrastructure/sqlite/repositories/acknowledgement.py` — new module.
4. `app/infrastructure/sqlite/repositories/__init__.py` — additive exports.
5. `app/learner/acknowledgement_contracts.py` — additive link fields only.
6. `app/learner/acknowledgement.py` — additive link gates + store conflict
   handling only.
7. `tests/learner/test_wu2_persistence_evidence.py` — new focused tests.
8. `docs/integration/pdw3-wu2-ack-routes-repair-20260812/workers/P/findings.md`
   — your durable findings report.

Do NOT edit `app/api/main.py`, `app/api/deps.py`,
`app/api/routers/acknowledgement.py`, `app/api/routers/journey.py`,
`app/practice/`, `app/journey/`, migrations 1-14, or any other test file.
The parent will wire the composition root after you return.

## Required context (read before writing)

1. `docs/integration/pdw3-wu2-learner-20260812/LEARNER-WU2-RETRY2-CANONICAL-HANDOFF.md`
   and `CHECKPOINT-010-RETRY2-V1-CONSIDERATIONS.md`.
2. `A:\EAP Agent Project\worktrees\shared-core\docs\integration\pdw3-wu1-recovery-20260811\CORE-WU1-DEPARTMENT-HANDOFF.md`
   (CORE WU1 is an uncommitted candidate in shared-core; LEARNER consumes
   only its typed boundary and never copies `app/review`).
3. Current `app/learner/acknowledgement.py`,
   `app/learner/acknowledgement_contracts.py`,
   `app/learner/evidence.py`, `app/learner/practice_provenance.py`,
   `app/models/schemas.py` (`HistoryEvidence`),
   `app/infrastructure/sqlite/repositories/learner.py` and
   `practice.py`, and `app/database/migrations.py`.
4. `AGENTS.md`.

## Implementation spec (follow exactly)

### 1. Migration 15 — `learner_acknowledgement_persistence`

In `app/database/migrations.py`:

- Change `LATEST_MIGRATION_VERSION` from 14 to 15.
- Add a new function named `_migration_15_learner_acknowledgement_persistence`
  immediately after `_migration_14` and BEFORE the `MIGRATIONS` dict. It must
  be strictly additive: create ONE table and two indexes, set
  `PRAGMA user_version = 15` at the end, and use only
  `CREATE TABLE IF NOT EXISTS` / `CREATE INDEX IF NOT EXISTS`. Never alter
  any existing table.
- Register `15: ("learner_acknowledgement_persistence", _migration_15_learner_acknowledgement_persistence)`.
- Extend `rollback()`: add `(15, 14)` to the allowed pair set and add an
  `if current == 15:` branch that is ledger-only (`pass`, then the common
  `DELETE FROM schema_migrations WHERE version=?` handles the ledger row).
  Data is preserved; re-apply is idempotent.

Exact DDL:

```sql
CREATE TABLE IF NOT EXISTS learner_acknowledgements (
    acknowledgement_id TEXT PRIMARY KEY,
    learner_id TEXT NOT NULL REFERENCES students(student_id),
    source_kind TEXT NOT NULL,
    source_evidence_ids_json TEXT NOT NULL,
    source_event_ids_json TEXT NOT NULL DEFAULT '[]',
    learning_item_id TEXT,
    authentic_evidence_status TEXT
        CHECK(authentic_evidence_status IN ('insufficient','present')),
    practice_activity_id TEXT,
    review_event_id TEXT,
    evidence_status TEXT NOT NULL,
    epistemic_status TEXT NOT NULL,
    outcome_claim TEXT NOT NULL DEFAULT 'none',
    provenance_json TEXT NOT NULL,
    policy_version TEXT,
    model_version TEXT,
    config_version TEXT,
    record_version TEXT NOT NULL,
    acknowledgement_text TEXT NOT NULL,
    limitations_json TEXT NOT NULL DEFAULT '[]',
    consent_json TEXT NOT NULL,
    observed_span_start TEXT,
    observed_span_end TEXT,
    recorded_at TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_learner_acknowledgements_learner
    ON learner_acknowledgements(learner_id, recorded_at, acknowledgement_id);
CREATE INDEX IF NOT EXISTS idx_learner_acknowledgements_kind
    ON learner_acknowledgements(learner_id, source_kind, recorded_at);
```

The `learning_item_id`, `practice_activity_id`, and `review_event_id`
columns are loose structural links (no FK): the CORE `review_events` and
learner `learning_items` tables are integration-owned and may not exist on
this branch.

In `app/version.py`: set `PLATFORM_DATABASE_MIGRATION_VERSION: int = 15`
(single-source invariant with `LATEST_MIGRATION_VERSION`).

### 2. Durable acknowledgement repository

New file `app/infrastructure/sqlite/repositories/acknowledgement.py`.

Define:

- `AcknowledgementStoreConflictError(Exception)` with `kind` and `message`
  (append-only violation signal, mirroring CORE's repository conflict
  pattern; do NOT import or copy CORE implementation).
- `SQLiteAcknowledgementRepository(connection_manager)` implementing the
  learner `AcknowledgementStorePort`:
  - `append(record)`: serialize `AcknowledgementRecord` to the table
    (JSON for lists/dicts, ISO-8601 strings for datetimes, `None` for null
    optional fields). In ONE transaction, first reject an existing
    `acknowledgement_id` with kind `conflict`, then reject an existing row
    for the same `(learner_id, source_kind, frozenset(source_evidence_ids))`
    with kind `duplicate_acknowledgement`; only then INSERT. No update or
    delete surface.
  - `get(acknowledgement_id)` -> `AcknowledgementRecord | None`.
  - `list_for_learner(learner_id)` -> `list[AcknowledgementRecord]` ordered
    by `recorded_at, acknowledgement_id`.
- `SQLiteAcknowledgementEvidenceLookup(connection_manager)` implementing the
  learner `AcknowledgementEvidencePort` (`owner_of`, `get_record`). It reads
  ONLY the single shared SQLite database through the injected connection
  manager:
  - `owner_of(source_id)` searches, in order:
    `history_evidence_registry.history_evidence_id`,
    `practice_targets.practice_target_id`,
    `exercise_attempts.attempt_id`,
    `practice_evaluations.evaluation_id` (JOIN `exercise_attempts` for
    `student_id`), `learning_items.learning_item_id`, and, only when the
    table exists, `review_events.review_event_id` and
    `learner_observed_evidence.evidence_id`. Returns the owning
    `student_id` or `None`. All reads are fail-closed: missing tables are
    detected via `sqlite_master` and treated as `None`.
  - `get_record(learner_id, source_id)` returns a fully qualified typed
    record or `None`:
    * history evidence: `HistoryEvidence` parsed from
      `history_evidence_registry.evidence_json` (model-validated).
    * exercise attempt: build `PracticeProvenanceRecord` ONLY when the
      stored `status` string is an exact member of the learner
      `PracticeActivityStatus` values and the joined
      `exercise_instances.instance_json` carries an `exercise_version`.
      Never map or reinterpret statuses (e.g., `submitted` must fail closed).
    * practice evaluation: build `PracticeProvenanceRecord` when
      `completion_status` is an exact `PracticeActivityStatus` member and
      `instance_json` carries `exercise_version`; fill `attempt_id`,
      `evaluation_id`, `evaluator_version` from stored fields.
    * learning item / review event rows: return the row dict (used by the
      service's link gates through `owner_of`).
    * observed evidence: only from the future `learner_observed_evidence`
      table when present; on this branch it is absent, so it returns `None`
      (fail closed).
  - Never fabricate fields; never default a version that is not stored.

Update `app/infrastructure/sqlite/repositories/__init__.py` with additive
imports and `__all__` entries for both new classes.

### 3. Acknowledgement contracts — additive link fields

In `app/learner/acknowledgement_contracts.py`, add to BOTH
`AcknowledgementRequest` and `AcknowledgementRecord`:

- `learning_item_id: str | None = None`
- `authentic_evidence_status: Literal["insufficient", "present"] | None = None`
- `practice_activity_id: str | None = None`
- `review_event_id: str | None = None`

Strip/validate the three id fields (reject blank strings after strip).
Keep `extra="forbid"` and all existing fields/validators unchanged. Add a
short docstring sentence explaining these are structural links
(learner/LearningItem/authentic-evidence/practice-review) with bounded
descriptive semantics. Update `__all__` only if needed.

### 4. Acknowledgement service — link gates and store conflict handling

In `app/learner/acknowledgement.py`:

- Add `class AcknowledgementStoreConflictError(Exception)` with `kind` and
  `message` (raised by durable append-only stores).
- In `acknowledge()`, after `_check_source_records(request)` and before
  `_check_text(request)`, call `self._check_links(request)`.
- `_check_links(request)`:
  - `learning_item_id` provided -> `owner_of` must return the request
    learner (else `learning_item_not_found` / `learning_item_owner_mismatch`).
  - `practice_activity_id` provided -> `owner_of` must return the request
    learner (else `practice_activity_not_found` /
    `practice_activity_owner_mismatch`).
  - `review_event_id` provided -> `owner_of` must return the request learner
    (else `review_event_not_found` / `review_event_owner_mismatch`); because
    the CORE `review_events` table is absent on this branch, this fails
    closed until INT composes CORE.
  - `authentic_evidence_status` must be `None`, `"insufficient"`, or
    `"present"` at runtime (records are mutable after construction), else
    `invalid_authentic_evidence_status`.
- Wrap `self.store.append(record)` so an
  `AcknowledgementStoreConflictError` is translated to
  `AcknowledgementError(exc.kind, exc.message)` (defense in depth; the
  service still pre-checks duplicates).
- Update the module docstring gate list to include the link gate.
- Add the new class to `__all__` if an explicit list is maintained.

## Verification contract

Use the worktree `.venv`:
`PYTHONDONTWRITEBYTECODE=1 .venv/Scripts/python.exe -m pytest tests/learner/test_wu2_persistence_evidence.py tests/learner/test_wu2_acknowledgement.py -q --no-header -p no:cacheprovider`

Your new tests must cover:

- Migration 15: fresh DB upgrades 14 -> 15 with the table present; re-upgrade
  idempotent; rollback 15 -> 14 ledger-only preserves data; re-upgrade
  preserves the row.
- Durable store: append/get/list, learner scoping, close/reopen persistence
  on the SAME SQLite file (durability proof), duplicate id and duplicate
  evidence-set conflicts with no write.
- Evidence lookup: a real `history_evidence_registry` row resolves and
  validates as `HistoryEvidence`; a real `practice_evaluations` row with
  `completion_status=completed` resolves to a qualified
  `PracticeProvenanceRecord` and a positive `PRACTICE_RESULT` acknowledgement
  succeeds and persists; an attempt with status `submitted` fails closed
  (no fabricated mapping); a `learning_items` row resolves ownership; an
  absent observed-evidence table and absent CORE `review_events` table fail
  closed.
- Service link gates: unknown/mismatched learning item, unknown practice
  activity link, review link fails closed when the CORE table is absent,
  invalid runtime `authentic_evidence_status` fails closed, all with no
  store write.
- The existing `tests/learner/test_wu2_acknowledgement.py` suite stays green.

Record exact commands, exit codes, pass counts, changed-file list, and any
compatibility risk in your findings file. Return a compact result including
status, files, tests, and the findings path. If anything forces an edit
outside scope, stop with `BLOCKED` and explain the exact boundary.
