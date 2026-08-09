# LEARNER-FOUNDATION - Feedback & Learner Intelligence Foundation (bounded)

**Owner:** LEARNER | **Branch:** `dept/feedback-learner` | **Worktree:**
`A:\EAP Agent Project\worktrees\learner`

**Baseline:** `09264abbd93cdc6b62b83cefd94b3b640319ac9b` (promoted master,
CORPUS Stage-6 WU-A/B/C/E + WU-D contract)

**Status:** DEPARTMENT GREEN (bounded foundation; `integration_required =
true`, `promotion_eligible = false`)

## What this Goal delivers

The bounded Feedback & Learner Intelligence Foundation consumes the WU-D
diagnostic gating contract and ADR-03's epistemic/provenance concept in
**contract and scaffolding form only**. It is additive, pure-Python product
code in `app/learner/` with no composition-root, API, persistence, migration,
or UI wiring.

## Scope (per Goal packet acceptance gate)

1. **Learner evidence/history foundation per ADR-03**: typed
   source-event/observed-evidence record contracts with provenance fields
   (event id, time, actor, source, evidence-admission status,
   policy/model/config version); practice provenance records.
2. **Feedback-policy application scaffolding**: consumes the WU-D exposure
   classes (`research_only` O1 default; `diagnostic_only` only when O2 gates
   G0-G7 hold; `displayable` FAIL-CLOSED - no display opt-in exists); never
   produces proficiency/mastery/ability/learning-gain claims; keeps observed
   evidence != diagnostic inference != feedback recommendation != learning
   outcome.
3. **Persistence**: design note only (additive learner-owned tables/columns),
   routed through the migration gate; **no migration implemented**.
4. **Tests**: evidence-record typing, provenance completeness,
   exposure-class enforcement fail-closed, no-normative-claims scan, and
   relevant regression.

## Explicit non-goals (unchanged gates)

- NO L1/L2/L3 memory schemas and NO memory subsystem (ADR-03
  implementation_gate: INT persistence ADR still required).
- NO migration, NO new tables/columns, NO product DB schema change.
- NO learner-facing UI; NO displayable exposure (D-08 opt-in absent).
- NO Question Bank/PracticeAttempt/scheduling/FSRS implementation.
- NO raw SWECCL access; NO corpus path/handle consumption (ADR-06 F10).

## Module map (`app/learner/`)

| Module | Purpose |
| --- | --- |
| `evidence.py` | Typed contracts: `EvidenceAdmissionStatus` (N6), `ProvenanceChain` (WU-D G4 7-field + ADR-03 versions), `SourceEvent`, `ObservedEvidence`, `EvidenceAdmissionRecord`; admission precedence (INVALID -> UNAVAILABLE -> LIMITED), provenance completeness, downgrade-only helpers |
| `exposure.py` | WU-D exposure classes, O2 gate records G0-G7, `ExposureEnvelope` (WU-D section 8), `ExposureEnforcer` (fail-closed O1/O2/displayable/unavailable), layer-permission matrix, `resolve_displayable` |
| `feedback_policy.py` | D-03 minimum `FeedbackPolicy` contract, default instance (`feedback-policy-v0.1.0`, priority limit 2, zero behavior change), `FeedbackPolicyService.apply` producing L2 recommendations with provenance |
| `normative.py` | Deterministic no-normative-claims scanner (WU-D F7/F11; N7 banned vocabulary; reuses `BANNED_LEARNER_LABELS` and `DEFAULT_RISKY_ABILITY_PHRASES`); documentation-mode F1 exemption |
| `practice_provenance.py` | `PracticeProvenanceRecord` (activity-only; `outcome_claim` structurally `"none"`), `validate_practice_provenance` |

## Hard invariants enforced

- `research_only` is the O1 default whenever qualification is incomplete,
  missing, or stale (RD-D3; WU-D F1/F2).
- `diagnostic_only` is a computation class entered only when ALL O2 gates
  G0-G7 hold with persisted, evidence-backed gate records (WU-D section 6;
  a missing or empty-evidence record is a failed gate).
- `displayable` never resolves: `DISPLAY_POLICY_OPT_IN_EXISTS = False`;
  `resolve_displayable()` returns `None` without the D-08 opt-in.
- `unavailable` is terminal; no widening, no substitution (F3/F15).
- Below-floor aggregates (min-N = 30 effective) never support diagnostic
  computation and downgrade to `research_only` (N10; section 8 item 9).
- FeatureSetVersion mismatch is UNAVAILABLE, never "best-effort comparable"
  (F4/I3).
- Epistemic layers are distinct and downgrade-only (D-09): observed
  evidence records carry L0/L1 only; recommendations are L2 with provenance;
  L3 remains reserved with no writer.
- Practice completion is activity only unless a validated measurement
  contract states otherwise (frozen contract).
- Feedback is never attributed to outcomes (A-23).

## WU-D consumption boundary

The learner foundation mirrors the CORPUS-owned WU-D machine contract
(`worktrees/corpus/docs/corpus-intelligence/l2/data/wu_d_diagnostic_gating_
contract.json`) in learner-owned constants; the drift test
`tests/learner/test_wu_d_contract_mirror.py` re-verifies exact equality
against the sibling contract when present and against frozen expected sets
otherwise. LEARNER never consumes raw corpus text, examples, reconstructive
derivatives, paths/handles, normative labels, or artifacts without an
exposure-class + admissibility record (WU-D section 8 "What LEARNER must NOT
consume").

## Verification

- New suite: `tests/learner/` (evidence typing, provenance completeness,
  exposure enforcement, policy scaffolding, normative scan, practice
  provenance, WU-D mirror).
- Relevant regression: shared vocabulary drift tests and contract
  convergence tests rerun (see `docs/integration/LEARNER-FOUNDATION-20260809.md`).

## Persistence boundary

No persistence was implemented. The additive design for learner-owned
tables/columns lives in
`docs/learner/LEARNER_FOUNDATION_PERSISTENCE_DESIGN_NOTE.md` and routes
through the migration gate (separate additive migration; NOT Migration 14,
per RD-D09).
