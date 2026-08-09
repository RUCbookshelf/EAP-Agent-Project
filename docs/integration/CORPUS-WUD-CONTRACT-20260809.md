# CORPUS-WUD-CONTRACT — WU-D Diagnostic Gating Contract with LEARNER

**Owner:** CORPUS | **Branch:** dept/corpus | **Worktree:**
`A:\EAP Agent Project\worktrees\corpus`

**Starting SHA:** `09264abbd93cdc6b62b83cefd94b3b640319ac9b` (promoted
baseline). This report originated as the uncommitted contract/design handoff;
the governed freeze result and resulting exact commit SHA are recorded in the
`CORPUS-WUD-CONTRACT-FREEZE` structured Program handoff produced immediately
after the single scoped commit.

**Verdict:** GREEN (contract/design complete; gate evidence complete; no
promotion authority)

## What was delivered

The WU-D diagnostic gating contract per the Stage-6 implementation handoff
(`docs/corpus-intelligence/l2/10_STAGE6_IMPLEMENTATION_HANDOFF.md`), the
approved Researcher decisions RD-D3-UD06 (O1/O2 model) and RD-D08
(exposure classes), and the licensing review (UD-04). Contract/design only —
no learner implementation, no product code changes.

| Requirement | Where satisfied |
| --- | --- |
| Exposure classes per D3-O2/O1-default and D-08 (research_only / diagnostic_only / displayable / hidden / unavailable) | contract §3 + machine artifact |
| Anonymization/privacy requirements (P1–P9) | contract §4 |
| Evidence-admissibility mapping (observed evidence ≠ diagnostic inference ≠ feedback recommendation ≠ learning outcome; ADMISSIBLE/LIMITED/UNAVAILABLE/INVALID) | contract §5 |
| Diagnostic-contract qualification criteria (O2 gates G0–G7) | contract §6 |
| Fail-closed rules (F1–F15) | contract §7 |
| Downstream LEARNER foundation input requirements (10 items + non-consumption list) | contract §8 |
| Explicit exclusion of textual/reconstructive derivatives and proficiency/mastery/learning-gain claims | contract §9 |
| No learner-facing UI; no product code | contract §1, §9, §10 |

## Safeguards verified

- Raw SWECCL untouched; no raw path/handle enters any artifact (ADR-06).
- All WU-D artifacts classified NON-RECONSTRUCTIVE AGGREGATE ARTIFACT in
  the Goal's machine register; no textual derivative, no excerpts.
- `displayable` defined but intentionally unpopulated — learner-facing
  corpus content remains FAIL-CLOSED (D-08; UD-04 licensing review).
- No app code, tests, persistence, API, or composition-root changes; at this
  contract handoff stage no commit, push, or PR occurred; pre-existing
  dirty/untracked files were preserved.
- Banned vocabulary appears only as explicit prohibition/exclusion text
  (documentation context, consistent with the measurement-claim policy).

## Verification

| Check | Result | Evidence |
| --- | --- | --- |
| Git preflight (root/branch/HEAD/worktree) | PASS | worktree root, `dept/corpus`, HEAD `09264abb…` = assigned baseline |
| Normative inputs read (RD-D3-UD06, RD-D08, Stage-6 handoff, licensing review + decision, artifact register, admissibility/claim policies, query boundary, LEARNER architecture doc) | PASS | read verbatim from disk |
| Contract sections complete (exposure classes, privacy, admissibility mapping, O2 gates, fail-closed, LEARNER inputs, exclusions) | PASS | `17_STAGE6_WU_D_DIAGNOSTIC_GATING_CONTRACT.md` §3–§9 |
| Machine contract JSON valid and complete | PASS | `ConvertFrom-Json` parse OK; mirrors §3–§9 |
| Artifact classification NON-RECONSTRUCTIVE only | PASS | `wu_d_diagnostic_gating_contract.json` `artifact_classification` |
| Write boundary respected | PASS | new files under `docs/` only |

No code tests were run: this Goal is contract/design only.

## Artifacts

- `docs/corpus-intelligence/l2/17_STAGE6_WU_D_DIAGNOSTIC_GATING_CONTRACT.md`
- `docs/corpus-intelligence/l2/data/wu_d_diagnostic_gating_contract.json`
- `docs/integration/CORPUS-WUD-CONTRACT-20260809.md`
- `docs/integration/CORPUS-WUD-CONTRACT-20260809.handoff.json`

## Dependencies

- **Unlocked:** WU-D diagnostic gating contract (design) ready for
  LEARNER-foundation consumption and Program Control ingestion.
- **Remaining:** LEARNER foundation implementation (LEARNER WAIT; FeedbackPolicy
  integration is LEARNER-owned); D-08 display policy opt-in (none exists);
  open Researcher decisions D4 (band method + normative min-N), D8
  (feature-set scope), D12 (UI exposure); final corpus exclusion/duplicate
  policy ratification; reference-group min-N ratification (Research
  Evaluation); CLAWS4 mapping contract.

## Notes

- `integration_required = true` (contract is a cross-department design
  input); `promotion_eligible = false` (no promotion authority).
- `user_decision_required = false`, `researcher_decision_required = false`
  for THIS goal: RD-D3-UD06 and RD-D08 are already approved and this goal
  implements no silent resolution of any open decision.

---

## Governed freeze record — `CORPUS-WUD-CONTRACT-FREEZE`

**Freeze authority:** the assigned Program Goal Packet
`CORPUS-WUD-CONTRACT-FREEZE`, dependent on the Wave-5 INT gate
`INT-INTEGRATION-GATES-WAVE5`. This record freezes the already-qualified
WU-D contract and its min-N evidence only; it does not promote, merge, push,
or authorize learner-facing corpus exposure.

### Gate-qualified pre-commit state

- **Branch / starting HEAD:** `dept/corpus` at
  `09264abbd93cdc6b62b83cefd94b3b640319ac9b`.
- **Wave-5 gate:** `GREEN`; Candidate 3 identifies the corpus working tree as
  untracked documentation only and verifies contract Sections 3–9, the
  machine mirror, and NON-RECONSTRUCTIVE AGGREGATE-only classification.
- **Required machine-contract fingerprint:**
  `wu_d_diagnostic_gating_contract.json` SHA-256 =
  `089BFD5395B4FE8384FD173C19A6431C75C4B0F2238FC31099E4E5E8135C1B11`
  (required prefix `089BFD53`).
- **Static contract/evidence manifest fingerprint:**
  `F78379582FEF20B6835C2BB87D53A540D94C1031B36D72280397DE4EC23F62CE`.
  This is SHA-256 of UTF-8 lines `<relative-path><TAB><file-SHA-256>`, sorted
  lexically, over the contract, machine JSON, and six min-N evidence files.
  The integration report itself is intentionally excluded from this
  pre-commit manifest to avoid a self-referential hash.
- **Min-N evidence checks:** 96 census rows / 75 approved groups; threshold
  30 has 75 effective, 75 raw, and 75 current-approved survivors; 54 fallback
  rows resolve as 35 exact, 15 prompt fallback, 4 genre fallback, and 0
  unavailable; the uncertainty summary has 6 rows.

### Exact commit scope

The single scoped commit contains exactly these nine files:

- `docs/corpus-intelligence/l2/17_STAGE6_WU_D_DIAGNOSTIC_GATING_CONTRACT.md`
- `docs/corpus-intelligence/l2/data/wu_d_diagnostic_gating_contract.json`
- the six files under `docs/corpus-intelligence/l2/evidence/` listed in the
  min-N evidence handoff
- this integration report

Deliberate exclusions:

- `docs/integration/CORPUS-WUD-CONTRACT-20260809.handoff.json` is a local
  scratch handoff. Its matching `handoff_id`, goal, owner, baseline, and
  return timestamp are authoritatively retained at
  `program-control/handoffs/CORPUS/CORPUS-WUD-CONTRACT__CORPUS-WUD-CONTRACT__20260809T072133Z__48af09.handoff.json`;
  it is not required evidence for this freeze and is removed before staging.
- `docs/integration/CORPUS-STAGE6-FREEZE-COMMIT-20260809.md` and
  `docs/integration/CORPUS-STAGE6-FREEZE-COMMIT-20260809.handoff.json` are
  prior-goal historical evidence. They remain preserved as untracked files:
  neither is staged, modified, moved, nor deleted.

### Immutable commit finalization

The final exact commit SHA, full selected-file manifest fingerprint, staged
tree fingerprint, committed-tree fingerprint, and post-commit proof that no
unrelated change entered are recorded in the required structured Program
handoff returned immediately after the commit. Recording the final commit SHA
inside this already-staged report would require an amendment; that would
violate the exactly-one-commit freeze boundary.

**Promotion:** not authorized. A future, separately governed exact-SHA
decision remains required even if this freeze candidate qualifies.
