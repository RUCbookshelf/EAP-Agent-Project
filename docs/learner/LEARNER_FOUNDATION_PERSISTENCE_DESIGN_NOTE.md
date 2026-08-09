# LEARNER-FOUNDATION - Persistence Design Note (additive; NOT implemented)

**Status:** DESIGN ONLY - routed through the migration gate. **No table,
column, migration, or repository change was made by LEARNER-FOUNDATION.**

## Purpose

The bounded foundation defines typed record contracts
(`app/learner/evidence.py`, `app/learner/practice_provenance.py`). Persisting
them requires learner-owned additive SQLite tables/columns. Per the Goal
packet, the migration gate applies: this note is the design record; the
migration itself must be separately authorized, designed with CORE/GOV/INT,
and executed under the normal gate.

## RD-D09 (HYBRID C1) requirements the design must satisfy

- `persist_minimum` per record: `epistemic_status`, `rule_id`,
  `rule_version`, source/provenance reference, effective state/version.
- `append_only` lifecycle: `invalidation`, `retraction`, `supersession` must
  be append-only records/columns, never in-place mutation.
- Queries supported: what did the system believe; under which rule; from
  which evidence; at what time/version; what later invalidated or superseded
  it.
- **Separate additive migration**; must NOT ride Migration 14 (Migration 14
  retains its qualified scope and trigger policy).

## Proposed additive scope (learner-owned, one SQLite database)

| Table (additive) | Purpose | Key columns (contract fields) |
| --- | --- | --- |
| `learner_source_events` | Typed interaction/source events (ADR-03) | `event_id`, `event_type`, `occurred_at`, `actor`, `source`, `policy_version`, `model_version`, `config_version`, `payload_json`, `admission_status`, `admission_reason`, `recorded_at` |
| `learner_observed_evidence` | Admitted observed evidence (L0) | `evidence_id`, `source_event_id`, `evidence_type`, `observed_at`, `epistemic_status`, `admission_status`, `exposure_class`, `provenance_json` (G4 7-field), `value_json`, `limitations_json`, `recorded_at` |
| `learner_practice_provenance` | Practice activity provenance | `record_id`, `student_id`, `practice_target_id`, `exercise_id`, `exercise_version`, `attempt_id`, `evaluation_id`, `activity_status`, `occurred_at`, `outcome_claim` (literal `none`), `measurement_contract`, `policy/model/config_version`, `admission_status`, `recorded_at` |
| `learner_record_lifecycle` (append-only) | RD-D09 invalidation/retraction/supersession | `lifecycle_event_id`, `record_type`, `record_id`, `action` (`invalidate`/`retract`/`supersede`), `reason`, `rule_id`, `rule_version`, `actor`, `recorded_at` |

The rows carry the full provenance chain as JSON (existing repository pattern:
`*_json` columns plus typed index columns, as used by
`learner_history` / `history_evidence_registry` / practice tables).

## What was NOT done (explicitly out of scope here)

- No DDL, no `app/database/migrations.py` change, no repository methods, no
  API schemas.
- No L1/L2/L3 memory tables: the INT persistence ADR (ADR-03
  implementation_gate) must qualify the memory subsystem design first.
- No index on raw learner text (none is retained); no corpus identifiers
  beyond registered provenance references (P4).

## Migration-gate routing

1. LEARNER proposes the additive design (this note).
2. CORE (shared persistence ownership) + GOV (data governance) + INT
   (integration review) review the additive scope.
3. A separate migration Goal executes the DDL under the normal gate with a
   verification record (append-only; no destructive change; migration runs
   must preserve the dev-DB digest guard used by the test runner).
4. LEARNER repository methods bind the contracts to the new tables only
   after the migration is integrated.
