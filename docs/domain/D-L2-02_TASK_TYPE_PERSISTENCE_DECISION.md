# D-L2-02 Decision Record — `task_type` persisted vs derived

**Decision id:** `D-L2-02`
**Goal:** L2-PREREQ-REMAINING
**Date:** 2026-08-09
**Status:** RESOLVED (decision record only; no implementation, no schema change)
**Owner:** L2 Writing Domain
**Baseline:** `5aafe2728d7135212bd675a6975b44bcf99ee099`
**Branch:** `dept/l2-writing`
**Prior status:** `NR` (`06_L2_WRITING_DOMAIN.md` section 7; recommendation: additive typed field)

---

## 1. Decision

**PERSISTED at write time.** When typed task identity ships (Domain Pack v1
implementation goal, separately authorized), a task's `task_type` value and its
classification provenance are recorded **once, at task-registration /
task-metadata time**, in an additive, nullable typed field on the submission
record. Display labels are **derived** from the active pack/registry at read
time (see D-L2-09). The value is **never recomputed from prompt text on read**.

Concretely (bounded design for the future implementation goal; nothing is
created here):

- `essays` gains additive nullable columns: `task_type`,
  `task_type_taxonomy_version`, and `task_type_provenance_json` (rule version,
  classification outcome, reason code for `unclassified`, or
  declared-metadata reference).
- Absent/NULL `task_type` means **untyped metadata** (D-22 default). Historical
  rows stay NULL; the explicit `legacy_unclassified` sentinel is written only
  through the approved legacy-mapping manifest (never inferred).
- `genre` free text is untouched (backward compatibility,
  `06_L2_WRITING_DOMAIN.md` section 4).

## 2. Rationale

1. **D-22 already fixes the storage semantic.** Architecture decision D-22
   states `task_type` is "metadata-only (**persisted**, displayed, versioned)"
   and that NULL is modeled as an explicit `legacy_unclassified` with mapping
   provenance. Persisted is the only option that can carry that provenance.
2. **Write-time determinism is a taxonomy-contract requirement.** The contract
   fixes classification to task-registration time (Constraint 1.1) and requires
   every typed task to record `task_type` AND `taxonomy_version` at write time
   (Constraint 7.4). A derived-on-read value has no write-time record.
3. **Derived values silently change history.** Recomputing from prompt text on
   read applies the *current* rule version to *old* prompts; when rules change
   (taxonomy major/minor bumps, Constraint 7.2), historical rows would silently
   change meaning. That violates the append-only snapshot rule (Constraint 7.4),
   the independent-version-streams rule (D-29), and fail-closed compatibility
   for consumers that do not know the recorded version (Constraint 7.6).
4. **Derived cannot carry provenance.** A recomputed value has no rule version,
   no mapping-manifest id, and no reason code. The contract's provenance
   requirements (Constraints 2.4, 5.5, 8.4) and D-22's mapping-provenance
   requirement are unsatisfiable by derivation.
5. **Registry content is versioned data, not code.** Per D-26, registry content
   lives in versioned JSON under the pack namespace; the persistence decision
   mirrors that discipline: the ID is data written once, the label/description
   come from the active pack at read time.

## 3. Rejected alternative — derived value

Compute `task_type` on read by re-running the deterministic classifier over the
normalized prompt.

- Rejected because of Section 2 items 2-4 (no registration-time determinism, no
  version, no provenance, silent historical reclassification).
- Also rejected as a "pure function of stored metadata": even a *stable* derived
  value duplicates write-time state and creates a second authority for the same
  fact; the registry/pack remains the single authority for labels, while the
  persisted row is the single authority for the typed identity.

## 4. Migration implications (for the implementation goal — NOT executed here)

- A new additive migration (next free version after 13) is required. Per
  `docs/departments/shared-platform-core/h1/07_MIGRATION_DECISION.md`,
  migration 14+ is reserved for a future implementation Goal with Architecture
  & Integration review; the migration version stays at 13 in H1. This record
  does not change that.
- Follow the existing additive pattern (`_add_column_if_missing` in
  `app/database/migrations.py`); no backfill (legacy rows stay NULL = untyped /
  `legacy_unclassified` semantics, never guessed).
- The migration is owned by Shared Core (CORE) with L2 supplying the column
  design and acceptance criteria; INT reviews the migration design.
- **Behavior-diff gate:** before `task_type` participates in ANY comparability
  predicate, run the D-22 behavior-diff test over a snapshot of the real legacy
  database (before/after comparability classifications) plus the D-30
  zero-change regression gate. This record does not authorize any
  comparability participation.

## 5. Rollback

- **Logical rollback (primary):** stop writing the new columns and drop any
  partial index created with them; data and columns remain, per the codebase's
  non-destructive one-step rollback pattern (`migrations.py::rollback`). No
  data loss; old snapshots untouched; re-activation re-runs the migration.
- **Physical cleanup:** `ALTER TABLE ... DROP COLUMN` is available as a
  one-step rollback for the deferred domain/language design
  (`07_MIGRATION_DECISION.md`) and would apply the same way here, but is
  performed only under a separately authorized maintenance goal.
- Records written under the new columns are append-only and never rewritten;
  disabling the feature leaves them readable as untyped metadata.

## 6. Non-claims and boundaries

- This record decides storage semantics only. It does NOT implement Domain Pack
  v1, does NOT add a column, does NOT change comparability, does NOT change
  product behavior, and does NOT resolve the legacy-genre mapping decision
  (D-22; data-governance decision owned by Research Evaluation + L2).
- `task_type` remains metadata-only with no measurement meaning (contract
  section 0).

## 7. Evidence references

- `docs/domain/L2_TASK_TYPE_TAXONOMY_CONTRACT.md` — Constraints 1.1, 2.4, 5.5,
  7.2, 7.4, 7.6; non-claim section 0.
- `docs/architecture/writing-intelligence-platform/14_ARCHITECTURE_DECISIONS.md` —
  D-22 (persisted metadata-only; legacy sentinel; behavior-diff), D-26 (registry
  content layout), D-29 (independent version streams), D-30 (zero-change gate).
- `docs/architecture/writing-intelligence-platform/06_L2_WRITING_DOMAIN.md` —
  sections 4 (additive typed field) and 7 (D-L2-02 `NR`, recommendation).
- `docs/departments/shared-platform-core/h1/07_MIGRATION_DECISION.md` — no
  migration 14 in H1; migration authority; deferred design.
- `app/database/migrations.py` — additive column pattern, non-destructive
  rollback.
- `app/shared/task_type_registry.py` — mechanism; `legacy_unclassified` sentinel.

*Decision record produced by the L2 execution agent under Goal
L2-PREREQ-REMAINING, 2026-08-09. Bounded record; no implementation.*
