# LEARNER-FOUNDATION - Feedback & Learner Intelligence Foundation (bounded)

**Owner:** LEARNER | **Branch:** `dept/feedback-learner` | **Worktree:**
`A:\EAP Agent Project\worktrees\learner`

**Starting SHA:** `09264abbd93cdc6b62b83cefd94b3b640319ac9b` (promoted
baseline) | **Final SHA:** `09264abbd93cdc6b62b83cefd94b3b640319ac9b` (no
commits; additive contracts/scaffolding/tests/docs only)

**Verdict:** GREEN (department-level bounded foundation; no promotion
authority; `integration_required = true`)

## What was delivered

| Area | Deliverable | Location |
| --- | --- | --- |
| Evidence/history foundation (ADR-03 concept) | Typed source-event/observed-evidence contracts, provenance chain, admission statuses/precedence, downgrade-only epistemic layering | `app/learner/evidence.py` |
| WU-D exposure consumption | Exposure classes, O2 gates G0-G7 with persisted gate records, input envelope, fail-closed enforcer (O1 default; diagnostic_only only via all gates; displayable fail-closed; unavailable terminal) | `app/learner/exposure.py` |
| Feedback-policy scaffolding (D-03) | Minimum policy interface + default instance (priority limit 2; zero behavior change) + L2 recommendation application with provenance | `app/learner/feedback_policy.py` |
| No-normative-claims scan (WU-D F7/F11) | Deterministic scanner over English/Chinese banned vocabulary with F1 documentation exemption | `app/learner/normative.py` |
| Practice provenance | Activity-only provenance records with structural `outcome_claim="none"` and validation | `app/learner/practice_provenance.py` |
| Persistence | Additive design note routed through the migration gate; NOT implemented | `docs/learner/LEARNER_FOUNDATION_PERSISTENCE_DESIGN_NOTE.md` |
| Tests | 84 new tests across 6 files (see Verification) | `tests/learner/` |
| Shared-contract registration | D-27 module-set manifest updated with the 5 new learner modules (mechanical inventory; the shared-contract change process remains the review path) | `verification/shared-core-h1/module_set_manifest.json` |

## Safeguards verified

- `research_only` is the O1 default; incomplete/missing/stale gate records
  keep O1 (never inferred).
- `diagnostic_only` resolves only when ALL of G0-G7 hold with evidence-backed
  records; empty-evidence records are failed gates.
- `displayable` is fail-closed: no D-08 display-policy opt-in exists
  (`DISPLAY_POLICY_OPT_IN_EXISTS = False`); stated displayable is rejected.
- `unavailable` is terminal (no widening); unknown artifacts, missing
  admissibility records, INVALID/UNAVAILABLE records, and FeatureSetVersion
  mismatches all reject.
- Below-floor aggregates (min-N 30) downgrade to `research_only` and never
  support diagnostic computation.
- Epistemic layers stay distinct and downgrade-only; observed evidence
  carries L0/L1 only; recommendations are L2; L3 has no writer.
- No normative claim survives the scanner in policy outputs or practice
  records; no proficiency/mastery/ability/learning-gain vocabulary enters
  the new learner vocabularies (drift tests).
- No migration, no DB schema change, no API, no composition-root, no UI
  wiring, no raw SWECCL access, no corpus path/handle consumption.

## Verification (direct evidence)

Run via the canonical launcher
(`scripts\dev\run_tests.ps1 -Targets tests/learner,...`), which bootstrapped
the worktree-local environment (`ENVIRONMENT READY`) and routed through the
isolated pytest runner (temp DB, dev-DB digest guard, ports free):

| Suite | Result |
| --- | --- |
| `tests/learner/` (new) | 84/84 PASS (evidence 18, exposure 25, policy 8, normative 14, practice 7, WU-D mirror 10) |
| Relevant regression: `tests/contracts/test_wave1_vocabulary_convergence.py` (13) + `tests/shared/test_vocabularies.py` (26) | PASS |
| Combined focused run via canonical launcher | 123/123 PASS, exit 0 (isolated runner; temp DB; dev-DB digest guard; ports free) |
| Full non-live core regression (canonical `-Full`) | 1965 PASS / 4 FAIL / 8 SKIP (failures pre-existing at baseline, see below) |

The WU-D mirror tests validate the learner exposure classes, O2 gates
G0-G7, admissibility statuses, and epistemic layers against the CORPUS-owned
machine contract (`worktrees/corpus/docs/corpus-intelligence/l2/data/
wu_d_diagnostic_gating_contract.json`) with exact set equality.

## Pre-existing failures at the assigned baseline (not caused by this Goal)

Four full-suite failures were characterized with direct evidence and all
exist at baseline `09264ab` independently of this Goal:

1. `test_shared_core_drift.py::TestModuleSetManifest` - D-27 module-set
   manifest lacks the three CORPUS Stage-6 modules (`corpus/comparison.py`,
   `corpus/student.py`, `corpus/tasksignature.py`) promoted at `09264ab`.
   After this Goal registered its own five learner modules in the manifest,
   the drift list is exactly the three pre-existing corpus entries.
   Repair owner: CORPUS/CORE via the shared-contract change process.
2. `test_research_governance_v01.py::test_policy_registry_consistency` and
   `test_run_all_validators` - CRLF policy-hash debt: the on-disk policy
   JSON files use CRLF line endings, so raw-byte SHA-256 hashes no longer
   match `policy_registry.json`. LF-normalized hashes match the registry
   exactly (verified byte-for-byte for all four flagged files). This debt is
   documented in the INT environment re-verification as Research
   Evaluation-owned. Repair owner: GOV.
3. `test_v095e_repository_modularization.py::test_static_owner_sql_
   dependency_and_ddl_parity_contract` - environment artifact: the parity
   script spawns `git show` under the real user while `worktrees/learner/.git`
   is owned by the sandbox identity, triggering git's dubious-ownership
   guard. No file content is involved; the same invocation as the sandbox
   identity succeeds. Environment/ops repair, not a code defect.

## Dependencies

- **Unlocked:** WU-D diagnostic gating contract consumption for LEARNER
  (exposure classes + O2 gates + fail-closed rules mirrored and enforced);
  ADR-03 evidence/provenance contract foundation (contracts only).
- **Remaining:** INT persistence ADR (memory subsystem); migration gate for
  learner-owned additive tables; D-08 display-policy opt-in (none exists);
  validated-measurement gate for any normative interpretation; L2 domain
  contracts; Question Bank/practice taxonomy contracts for PracticeAttempt
  implementation.

## Notes

- No commit, push, or PR created; pre-existing dirty/untracked files in the
  worktree preserved untouched (none existed at start).
- `integration_required = true`; `promotion_eligible = false` (bounded
  department foundation; no promotion authority).
