# D-L2-02 Migration 14 Design Note (CORE-owned lane; NOT implemented)

**Goal:** `L2-DOMAIN-PACK-V1`
**Date:** 2026-08-09
**Owner:** L2 Writing Domain (design); Shared Core (implementation); INT (review)
**Status:** DESIGN NOTE ONLY - no migration is implemented by this Goal
**Authority:** `docs/domain/D-L2-02_TASK_TYPE_PERSISTENCE_DECISION.md` §4;
`docs/departments/shared-platform-core/h1/07_MIGRATION_DECISION.md`
(NO migration 14 in H1; migration 14+ reserved for a future implementation
Goal with Architecture & Integration review)

---

## 1. Why this note exists

Domain Pack v1 ships the deterministic write-time classification and legacy
mapping functions (`app/services/task_type_classifier.py`,
`app/services/legacy_genre_mapping.py`). Persisting their outputs requires
the D-L2-02 additive columns. Per the acceptance gate, this Goal does NOT
implement the migration; this note is the design handoff for the CORE-owned
migration lane.

## 2. Column design (from D-L2-02 §1)

```sql
ALTER TABLE essays ADD COLUMN task_type TEXT NULL;
ALTER TABLE essays ADD COLUMN task_type_taxonomy_version TEXT NULL;
ALTER TABLE essays ADD COLUMN task_type_provenance_json TEXT NULL;
```

- Absent/NULL `task_type` means untyped metadata (D-22 default).
- Historical rows stay NULL; `legacy_unclassified` is written ONLY through
  the approved D-22 manifest (never inferred).
- `genre` free text is untouched (backward compatibility).
- Migration version: 14 (next free version after 13; frozen at 13 in H1).
- Pattern: `_add_column_if_missing` in `app/database/migrations.py`
  (additive; no backfill).

## 3. Write-time provenance record (acceptance criteria for CORE)

Every typed row records:

- `task_type`: one of `opinion | argumentative | discussion |
  problem_solution | general_eap | legacy_unclassified`;
- `task_type_taxonomy_version`: `l2-task-type-taxonomy-v1.0.0`;
- `task_type_provenance_json`: classification rule version
  (`l2-domain-pack-v1.0.0`), mapping manifest id + rule id + reason code
  (`legacy_genre_mapping.json` fields), approval decision ids (RD-D22, DP-4),
  matched-trigger summary for new-task classification.

## 4. Gates before comparability participation

- D-22 behavior-diff test over a snapshot of the real legacy database
  (before/after comparability classifications) - executed in this Goal over
  the DP-4 census snapshot with zero classification change (see
  `docs/integration/L2_DOMAIN_PACK_V1_REPORT.md`);
- D-30 zero-change regression gate (full core suite green; additive-only
  API/contract diffs; locale parity; migration version stays 13 with no data
  mutation until migration 14 is separately authorized);
- explicit INT/CORE authorization for migration 14.

## 5. Rollback

- Logical rollback (primary): stop writing the new columns; data and columns
  remain (non-destructive one-step pattern, `migrations.py::rollback`).
- Physical cleanup: `ALTER TABLE ... DROP COLUMN` under a separately
  authorized maintenance goal.
- Rows written under the columns are append-only and never rewritten;
  disabling leaves values readable as untyped metadata.

## 6. Explicit non-actions of this Goal

- NO `ALTER TABLE`, NO migration file, NO database write.
- NO backfill, NO re-tagging of historical rows.
- NO comparability predicate change.

*Produced by the L2 execution agent under Goal L2-DOMAIN-PACK-V1, 2026-08-09.
Design handoff only; implementation is CORE-owned and INT-reviewed.*
