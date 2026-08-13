# D-09 Epistemic-Status Persistence — Migration Design (Hybrid C1, Separate Additive Lane)

**Goal ID:** CORE-D09-MIGRATION-DESIGN
**Owner:** CORE — Shared Platform & Core
**Goal type:** STUDY — design only; no implementation, no schema changes, no runtime behavior changes
**Worktree:** `A:\EAP Agent Project\worktrees\shared-core` (branch `dept/shared-core`)
**Baseline:** `09264abbd93cdc6b62b83cefd94b3b640319ac9b` (promoted master); live HEAD `3f984a94c936df7306f638aa659989bb076a100d` (master + amendments merge)
**Date:** 2026-08-09
**Researcher decision:** `program-control/researcher-decisions/RD-D09-approved-C1.json` — APPROVED — HYBRID C1 (2026-08-09T07:20:23Z)
**Verdict:** GREEN — design complete, DDL sketch empirically verified; no code changed.

---

## 0. Lane statement (read first)

This design is a **SEPARATE additive migration lane** for D-09 hybrid C1
epistemic-status persistence. It does **NOT ride Migration 14**. Migration 14
retains its qualified scope (additive `essays` domain/language discriminator
and the Academic table family) and its trigger policy (wave-1 decision
`06_MIGRATION_14_DECISION.md` §4: (1) an Academic persistence implementation
Goal starts; (2) any production query-by-domain or cross-domain persisted
query is required; (3) Academic Writing becomes a functioning product domain
surface). None of those triggers has fired; Migration 14 remains
not-implemented, and this design changes nothing about it.

The D-09 lane has **zero dependency on Migration 14**: its Phase 1 (the
subject-agnostic append-only ledger below) does not reference `essays`, the
Academic table family, or any table that does not exist yet. Phase 2 (the
optional typed column on the Academic table family) is explicitly conditional
on those tables existing and is gated on the same F-6 constraints as Migration
14.

---

## 1. Governing inputs (evidence, not assumption)

| Input | Location | Binding effect |
| --- | --- | --- |
| RD-D09 — APPROVED HYBRID C1 | `program-control/researcher-decisions/RD-D09-approved-C1.json` | Persist minimum canonical state (`epistemic_status`, `rule_id`, `rule_version`, source/provenance reference, effective state/version); append-only invalidation/retraction/supersession records; provenance queries (what/under-which-rule/from-which-evidence/at-what-time/what-superseded); SEPARATE additive migration, NOT Migration 14 |
| ACAD D-09 options analysis (recommends C1) | `worktrees/academic/docs/integration/acad-d09-options/ACAD-D09-OPTIONS-ANALYSIS.md` | Status written only by ACAD-owned services (ADR-05); downgrade-only at service/export layers; `outcome_claim` unwritable until validated-measurement gate; no epistemic↔verification cross-axis mapping; closed four-value vocabulary mirrored between DB CHECK and `EpistemicStatus` Literal; status column excluded from Migration 14; record decision id in the persistence Goal handoff (F-3) |
| Migration-14 design review (F-3, F-5, F-6) | `worktrees/int-study-base/docs/integration/MIGRATION_14_DESIGN_REVIEW.md` | F-3: no typed persisted status without Researcher decision (decision now exists: RD-D09); F-6: additive columns need column-level CHECK, SQLite ≥ 3.35, no dependent index/view/trigger before `DROP COLUMN` |
| Migration-14 amendments record | `docs/integration/wave1/13_MIGRATION_14_AMENDMENTS.md` | §6 D-09 unchanged/fail-closed until RD; §1 F-1 doc-refresh convention (same commit as migration); §2 F-6 rollback-note test remains green at implementation; §4 F-4 attribution rule id (`domain-attribution-v0.1.0`) is a separate axis from D-09 rule id/version |
| ADR-03 (memory epistemic) | `program-control/qualified-adrs/ADR-03-memory-epistemic.json` | Persisted derived state must be longitudinal, provenance-linked, inspectable, retractable, invalidatable, supersedable; memory state never constitutes validated mastery; implementation gate includes INT persistence ADR — this design is an input to that ADR, not a substitute |
| ADR-05 (academic evidence) | `program-control/qualified-adrs/ADR-05-academic-evidence.json` | Only ACAD writes `epistemic_status` on Academic entities; retrieval plumbing (GR) never sets it |
| Migration conventions (authoritative code) | `app/database/migrations.py` (LATEST = 13 at line 26; `MIGRATIONS` map line 748; `upgrade()` line 765; `rollback()` line 785) | Runner applies in order inside transactions; `schema_migrations` ledger + `PRAGMA user_version` authority; `INSERT OR IGNORE` ledger rows; one-step non-destructive logical rollback; additive migrations preserve legacy rows via `DEFAULT` |
| Migrations documentation | `docs/DATABASE_MIGRATIONS.md` | Doc refresh convention (F-1): same commit as the migration; "Migration 14 (does NOT exist)" precedent section |
| Append-only precedent | `app/database/migrations.py` migration 8 (`history_evidence_registry`); `app/academic/entities.py` `CitationVerificationRecord`; `app/academic/provenance.py` | Registry-style append-only tables with `_row_id`/`_id` columns and JSON payload columns; frozen record entities with `rule_id`/`rule_version`; in-memory read-only provenance graph |
| Frozen vocabulary (authority) | `app/academic/entities.py` (`EpistemicStatus` Literal, `EvidenceUnit`); `app/academic/vocabulary.py` (`EPISTEMIC_LAYER_RANK`, `epistemic_downgrade_allowed`, `EPISTEMIC_STATUS_PERSISTENCE` marker) | The four-value status set and downgrade-only helper are frozen and contract-tested; persistence is the only open piece, now decided (C1) |

---

## 2. Design contract

### 2.1 Minimum canonical state (per RD-D09)

Each persisted status assignment row carries, immutably, the full minimum
canonical state:

| RD-D09 element | Column | Notes |
| --- | --- | --- |
| `epistemic_status` | `epistemic_status` | Closed four-value vocabulary, column-level CHECK mirroring the frozen `EpistemicStatus` Literal (`observed_descriptive`, `gated_inference`, `recommendation`, `outcome_claim`) |
| `rule_id` | `rule_id` | Epistemic-status derivation rule id (e.g., `d09-status-v0.2.0`); distinct from the F-4 attribution rule id (`domain-attribution-v0.1.0`) and from verification rules |
| `rule_version` | `rule_version` | Exact rule version used at write time (per-row pinning prevents retroactive reinterpretation) |
| source/provenance reference | `provenance_json` | Structured JSON: `source_id`, `source_version`, evidence/reference ids, input hashes (sha256 hex64 convention); schema enforced at the application layer by ACAD write paths |
| effective state/version | `subject_version`, `effective_version`, `effective_at` | `subject_version` = version of the subject entity the status applies to; `effective_version` = monotonic per-subject status sequence; `effective_at` = ISO-8601 UTC time the state became effective |

### 2.2 Append-only record types

`record_type` is a closed vocabulary with a column-level CHECK:

- `assignment` — a status assignment (the canonical-state row). Carries
  `epistemic_status` + `rule_id`/`rule_version` + `provenance_json` +
  `effective_*`. Optionally links back to the prior assignment it replaces via
  `supersedes_record_id`.
- `invalidation` — terminates the targeted assignment because it is no longer
  valid (rule change, staleness). Carries `target_record_id`, no new status.
- `retraction` — terminates the targeted assignment because it is withdrawn
  (error, correction). Carries `target_record_id`, no new status.
- `supersession` — terminates the targeted assignment and is paired with a NEW
  `assignment` row (which carries `supersedes_record_id` pointing at the same
  target). The event is the "what later superseded it" record; the assignment
  is the new canonical state.

Invariants (all enforced at the application layer; a CHECK cannot express
ordering or provenance semantics):

1. **Append-only**: no `UPDATE`/`DELETE` on the ledger — same discipline as
   `history_evidence_registry` and `CitationVerificationRecord`.
2. **Write-time setting**: status is set at write time by ACAD-owned services
   only (ADR-05; GR never writes status).
3. **Downgrade-only**: status changes follow `epistemic_downgrade_allowed`
   (rank target ≤ rank current), enforced at service/export layers.
4. **L3 gate**: nothing may assign `outcome_claim` until the
   validated-measurement gate; attempted upgrades are audited and rejected.
5. **No resurrection**: a terminated assignment stays terminated. After a
   retraction/invalidation of the current assignment, the subject has **no
   current status** until a fresh `assignment` lands; prior superseded
   assignments do NOT silently re-emerge (verified, §5).
6. **Cross-axis guard**: no epistemic↔verification mapping; `academic_
   epistemic_to_shared` remains intentionally unimplemented.
7. **No FK to subject tables**: the ledger references subjects by
   `(subject_type, subject_id)` without foreign keys, because subject tables
   (Academic table family) do not exist yet and FK enforcement would couple
   the lanes. Referential integrity is application-enforced with contract
   tests.
8. **Closed vocabulary parity**: the DB CHECK set and the `EpistemicStatus`
   Literal are contract-tested to mirror each other (precedent:
   `tests/academic/test_vocabulary.py`).

### 2.3 Provenance query support (the five RD-D09 questions)

| Question | Answer mechanism |
| --- | --- |
| What did the system believe? | Latest non-terminated `assignment` for the subject (current-state query, §5 Q1) |
| Under which rule? | `rule_id` + `rule_version` on the assignment row |
| From which evidence? | `provenance_json` on the assignment row (source/provenance reference) |
| At what time/version? | `effective_at` + `effective_version` + `subject_version`; time-slice query `effective_at <= T` (§5 Q4) |
| What later invalidated or superseded it? | Event rows by `target_record_id` (§5 Q5); full history chain per subject |

No views or triggers are created for these queries (see §4 rollback rules);
queries run in the application layer.

---

## 3. DDL sketch

### 3.1 Phase 1 — append-only epistemic-status ledger (mandatory, subject-agnostic)

```sql
CREATE TABLE IF NOT EXISTS epistemic_status_records (
    record_id            TEXT PRIMARY KEY,          -- 'esr-<id>' (project ID-prefix convention)
    subject_type         TEXT NOT NULL,             -- open registry key; initial set: evidence_unit,
                                                    --   claim, citation, source; extension via reviewed
                                                    --   change (no CHECK to avoid future table rebuilds)
    subject_id           TEXT NOT NULL,
    subject_version      INTEGER NOT NULL DEFAULT 1,-- effective state/version of the subject entity
    record_type          TEXT NOT NULL
                         CHECK (record_type IN
                                ('assignment','invalidation',
                                 'retraction','supersession')),
    epistemic_status     TEXT
                         CHECK (epistemic_status IN
                                ('observed_descriptive','gated_inference',
                                 'recommendation','outcome_claim')),
                         -- NULL on event rows (invalidation/retraction/supersession);
                         -- NOT NULL on assignment rows (application-enforced)
    rule_id              TEXT NOT NULL,
    rule_version         TEXT NOT NULL,
    provenance_json      TEXT NOT NULL DEFAULT '{}',
    effective_version    INTEGER NOT NULL,          -- monotonic per-subject status version
    effective_at         TEXT NOT NULL,             -- ISO-8601 UTC
    supersedes_record_id TEXT,                      -- assignment -> prior assignment
    target_record_id     TEXT,                      -- event -> assignment it terminates
    reason               TEXT,
    created_by           TEXT NOT NULL DEFAULT 'system',
    created_at           TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

No index, view, or trigger is created by the migration. (If an index on
`(subject_type, subject_id, effective_version)` is ever added at
implementation for query performance, it is dropped automatically with
`DROP TABLE` in SQLite; views/triggers referencing the table would block
`DROP TABLE` and are forbidden.)

### 3.2 Phase 2 — typed column on the Academic table family (conditional)

Applied ONLY when the Academic table family exists (i.e., after Migration 14
and the Academic persistence Goal have landed) AND ACAD's adapters read status
directly from rows. Exact F-6 rollback constraints apply:

```sql
ALTER TABLE evidence_units ADD COLUMN epistemic_status TEXT NOT NULL
    DEFAULT 'observed_descriptive'
    CHECK (epistemic_status IN ('observed_descriptive','gated_inference',
                                'recommendation','outcome_claim'));
ALTER TABLE evidence_units ADD COLUMN epistemic_rule_id TEXT NOT NULL DEFAULT '';
ALTER TABLE evidence_units ADD COLUMN epistemic_rule_version TEXT NOT NULL DEFAULT '';
```

Column-level CHECK only (never table-level); `DEFAULT` covers existing rows and
backfill never upgrades (downgrade-only); no index/view/trigger on these
columns without INT review, and any such object must be dropped BEFORE
`DROP COLUMN`.

The design does **not** create the Academic table family — that remains
Migration 14's scope (F-5 sequencing to be confirmed by INT at the
migration-14 gate).

---

## 4. Rollback

**Phase 1 (ledger):** logical, non-destructive-of-legacy rollback following the
runner convention:

1. `DROP TABLE epistemic_status_records` — additive data (the ledger rows) is
   dropped with the table; no pre-existing rows of any other table are
   affected; no views/triggers reference the table (none are created).
2. `DELETE FROM schema_migrations WHERE version = <n>`; `PRAGMA user_version =
   <n-1>` (runner `rollback()` pattern).

Post-rollback the database is functionally identical to the pre-migration
state. Re-upgrade recreates the table (verified in probe P6).

**Phase 2 (columns):** `ALTER TABLE ... DROP COLUMN` per added column, subject
to the F-6 contract already recorded in `app/database/migrations.py` module
docstring and asserted by `tests/test_migration_drop_column_rollback_note.py`:

- SQLite >= 3.35 required (bundled SQLite **3.53.1**, verified via the
  environment venv).
- The CHECK must remain column-level; a table-level CHECK or any dependent
  index/view/trigger blocks the drop until that object is removed first.

---

## 5. Verified query sketches (probes on SQLite 3.53.1)

All probes ran against the environment venv interpreter on fresh in-memory
databases; no product code touched.

**Q1 — current canonical state (what the system believes now):**

```sql
SELECT epistemic_status, rule_id, rule_version, effective_version, effective_at
FROM epistemic_status_records a
WHERE record_type = 'assignment' AND subject_type = ? AND subject_id = ?
  AND NOT EXISTS (SELECT 1 FROM epistemic_status_records e
                  WHERE e.target_record_id = a.record_id)
ORDER BY effective_version DESC LIMIT 1;
```

Verified: returns the latest non-terminated assignment; returns NULL after the
current assignment is retracted (no resurrection of the superseded prior
assignment).

**Q4 — belief at a time-version:**

```sql
SELECT epistemic_status, rule_id, rule_version
FROM epistemic_status_records
WHERE record_type = 'assignment' AND subject_type = ? AND subject_id = ?
  AND effective_at <= ?
ORDER BY effective_version DESC LIMIT 1;
```

**Q5 — what later invalidated or superseded it:**

```sql
SELECT record_id, record_type, reason
FROM epistemic_status_records
WHERE target_record_id = ? ORDER BY created_at;
```

**Full history chain per subject:** `SELECT ... WHERE subject_type = ? AND
subject_id = ? ORDER BY effective_version, record_id`.

**Write pattern (supersession):** `INSERT` event row
(`record_type='supersession'`, `target_record_id=<old>`) **and** `INSERT` new
assignment row (`supersedes_record_id=<old>`). **Retraction/invalidation:**
single `INSERT` event row with `target_record_id=<current>`.

---

## 6. Migration ownership map

| Concern | Owner | Basis |
| --- | --- | --- |
| Migration execution (default owner when triggered); DDL, `MIGRATIONS` entry, version numbering, rollback notes, `DATABASE_MIGRATIONS.md`/`DATA_MODEL.md` refresh (F-1 convention) | **CORE** | WORKSTREAM_REGISTRY: "shared persistence and migrations"; wave-1 `06_MIGRATION_14_DECISION.md` §5; amendments record §1 |
| Migration numbering — next free number after live migration 14 (never reuse 14) | CORE | This design §7 |
| Research policy: A-10 decision-inventory update (RESEARCH DECISION REQUIRED → approved C1), measurement-claim policy note (§3 write-time; §4 L3 gate), policy versioning per `02_POLICY_VERSIONING.md` change control (D-29: engineering stream independent) | **GOV** | ACAD options analysis §8.3; migration-14 review F-3 |
| Domain design: vocabulary mirror/contract tests, `provenance_json` schema, write-path semantics, epistemic derivation rule registry, `EPISTEMIC_STATUS_PERSISTENCE` marker update (records RD-D09 id) | **ACAD** | ADR-05; ACAD options analysis §8 |
| Migration design review, sequencing confirmation, persistence-ADR coordination (ADR-03 gate), INTEGRATION GREEN qualification at implementation | **INT** | Migration-14 review §7; ACAD options analysis §9 |
| Ledger placement ruling (CORE-owned shared ledger vs Academic table family) | INT review + GOV policy reading | ACAD options analysis open item; GOV `07_MEASUREMENT_CLAIM_POLICY.md` §4 ("status stays inside the Academic table family" — policy interpretation needed for the ledger form) |
| Learner-memory side of ADR-03 (shared extension beyond Academic subjects) | LEARNER + CORE + INT; out of this lane's scope, coordination only | ADR-03 implementation gate |

---

## 7. Sequencing recommendation

1. **Now:** this design is the review input. No trigger fired; nothing is
   scheduled.
2. **When an Academic persistence implementation Goal starts** (which is also
   Migration-14 trigger (1)): **Migration 14** (discriminator + Academic table
   family per INT's F-5 confirmation) and **the D-09 lane** (numbered 15 at the
   earliest — never 14, which is reserved for the recorded Migration 14)
   land in that Goal as **two separate additive migrations**, applied in
   order, each with its own rollback and ledger entries; the handoff records
   the decision id **RD-D09** (F-3 requirement).
3. **Phase 2** (typed columns) lands only after the Academic table family
   exists and ACAD adapters read status from rows — same Goal or a later one,
   always with the F-6 constraints.
4. **Co-committed governance:** GOV policy note + A-10 update (change control
   per `02_POLICY_VERSIONING.md`); ACAD updates the `EPISTEMIC_STATUS_
   PERSISTENCE` marker to reference RD-D09; CORE refreshes the migrations docs
   in the same commit (F-1); the F-6 rollback-note test stays green.
5. **ADR-03 coordination:** this design is an input to, not a substitute for,
   the INT persistence ADR; the Academic status persistence pattern must stay
   compatible with the future learner-memory persistence.

The lane's own trigger policy: the D-09 ledger migrates with the first
Academic persistence Goal that writes epistemic statuses (i.e., it rides
neither Migration 14's triggers nor its scope).

---

## 8. Explicit non-ride statement

- This migration is **NOT** Migration 14 and does not modify, defer, or
  re-scope it.
- Migration 14 retains its qualified scope and trigger policy unchanged
  (verified: `app/database/migrations.py` has no migration 14; the amendments
  record §0-§6 remains authoritative).
- No D-09 DDL may be folded into the migration-14 entry, and no migration-14
  DDL may be folded into this lane.

---

## 9. INT review notes (inputs for the implementation gate)

1. Confirm lane numbering: D-09 takes the next free version after live
   migration 14 (15 at the earliest); 14 stays reserved.
2. Confirm the ledger placement ruling: CORE-owned shared ledger table
   (subject-agnostic, no FK) vs a table inside the Academic family — requires
   GOV policy reading of `07_MEASUREMENT_CLAIM_POLICY.md` §4 in addition to
   INT sequencing.
3. Confirm the record semantics: `supersession` = event row + new assignment;
   retraction/invalidation leave **no current status** (no resurrection of
   superseded assignments); re-establishment requires a fresh assignment.
4. Confirm Phase 2 stays conditional (column-level CHECK, F-6) and does not
   become a prerequisite for Phase 1.
5. Confirm `subject_type` is an open registry key enforced at the application
   layer (no CHECK), so future subjects (e.g., learner-memory per ADR-03) do
   not require a table rebuild.
6. Note for the ADR-03 persistence ADR: this design is a candidate input,
   not the ADR itself.

---

## 10. Verification evidence

| Check | Result | Evidence |
| --- | --- | --- |
| Worktree preflight | PASS | root `A:/EAP Agent Project/worktrees/shared-core`; branch `dept/shared-core`; HEAD `3f984a94c936df7306f638aa659989bb076a100d`; pre-existing untracked ADR docs (ADR-01/02/08) preserved untouched |
| All packet inputs read | PASS | RD-D09; ACAD-D09-OPTIONS-ANALYSIS.md; MIGRATION_14_DESIGN_REVIEW.md (F-3/F-6); 13_MIGRATION_14_AMENDMENTS.md; app/database/migrations.py (LATEST=13 @ :26, MIGRATIONS @ :748, upgrade @ :765, rollback @ :785); docs/DATABASE_MIGRATIONS.md; ADR-03; app/academic/{entities,vocabulary,provenance}.py |
| Bundled SQLite >= 3.35 | PASS | environment venv reports SQLite **3.53.1** |
| DDL probe: CHECK enforcement | PASS | invalid `epistemic_status` insert raises `IntegrityError`; invalid `record_type` rejected |
| DDL probe: append-only chain + current state | PASS | supersession (event + assignment) yields current `gated_inference`; retraction of current yields NULL current state (no resurrection); prior assignment stays terminated |
| DDL probe: time-version + superseded-by queries | PASS | `effective_at <= T` slice returns the believed status/rule at T; `target_record_id` query returns the supersession/retraction events |
| DDL probe: rollback | PASS | `DROP TABLE epistemic_status_records` succeeds; post-rollback recreate + insert works |
| No schema/runtime changes | PASS | only this document added under `docs/integration/`; no changes under `app/` or `tests/` |

---

## 11. Open items (deferred, not resolved here)

- Ledger placement ruling (shared CORE ledger vs Academic table family) — INT
  review + GOV policy reading (§6, §9.2).
- Phase 2 column timing and exact Academic table set — Academic persistence
  Goal, after the table family exists.
- Epistemic derivation rule registry contents (`rule_id`/`rule_version`
  values) — ACAD-owned at implementation.
- F-5 sequencing of Migration 14 itself (atomic vs discriminator-first) — INT
  to confirm at the migration-14 gate (unchanged by this design).

---

## 12. Evidence locations

- `program-control/researcher-decisions/RD-D09-approved-C1.json`
- `worktrees/academic/docs/integration/acad-d09-options/ACAD-D09-OPTIONS-ANALYSIS.md`
- `worktrees/int-study-base/docs/integration/MIGRATION_14_DESIGN_REVIEW.md` (§6 F-3/F-5/F-6; §7)
- `docs/integration/wave1/13_MIGRATION_14_AMENDMENTS.md` (§0, §1, §2, §6)
- `docs/integration/wave1/06_MIGRATION_14_DECISION.md` (§4 triggers)
- `app/database/migrations.py` (module docstring F-6 note; migration 8 ledger precedent; `LATEST_MIGRATION_VERSION = 13` @ :26; `MIGRATIONS` @ :748; `upgrade()` @ :765; `rollback()` @ :785)
- `docs/DATABASE_MIGRATIONS.md`; `tests/test_migration_drop_column_rollback_note.py`
- `program-control/qualified-adrs/ADR-03-memory-epistemic.json`; `ADR-05-academic-evidence.json`
- `app/academic/entities.py` (`EpistemicStatus`, `EvidenceUnit`, `CitationVerificationRecord`), `app/academic/vocabulary.py`, `app/academic/provenance.py`
- Verification probes: fresh temp/in-memory SQLite 3.53.1 DDL runs (this Goal; outputs recorded in the run)

---

*Prepared by [CORE] Shared Platform & Core execution agent.*
*Goal CORE-D09-MIGRATION-DESIGN — design only; no migration, no schema change, no runtime behavior change.*
