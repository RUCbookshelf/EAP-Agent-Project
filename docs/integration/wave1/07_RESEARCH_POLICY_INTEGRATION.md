# 07 — Research Policy Integration

**Gate:** WU8 GREEN — 2026-08-08
**Office:** Architecture & Integration (Wave-1 Integration Gate)

## 1. Purpose

Determine which Research Evaluation & Data Governance policies are integrated as policy artifacts and which already require runtime seams. Wave-1 rule (Goal section 13): policy existence and validation does not automatically require full learner-facing runtime wiring; do not prematurely build Stage 6 or Feedback.

## 2. Verification performed

- Research Governance validator suite on the integrated baseline: **28/28 passed** (deterministic, read-only; includes policy-schema validation, registry SHA-256 checks, reference-group eligibility, evaluation protection, version provenance, measurement-claim guardrails, audit sampler, Stage-6 admissibility, leakage validator).
- Policy versions and hashes remain deterministic: recorded SHA-256 values match the committed (LF) artifact bytes exactly — verified 8/8 (`evidence/check_policy_hashes.py`). Environment note: on Windows checkouts with `core.autocrlf=true` the on-disk bytes become CRLF and hash validation fails; the integration worktree re-materialized the policy files with LF (no index/commit change). Follow-up owned by Research Evaluation: make hash validation robust to checkout line endings (e.g., `.gitattributes` `-text` on policy artifacts) or document the LF-checkout requirement.
- Corpus Stage-5 implementation not modified to match Research documentation: `git diff b171cce HEAD -- app/corpus tests/corpus docs/corpus-intelligence` is empty.
- Registry of 8 ratified policies + versioning framework validated against `policy_schema.json`.

## 3. Policy disposition (Goal section 13)

| Policy | Version | Disposition | Notes |
| --- | --- | --- | --- |
| CorpusUsePolicy | `corpus-use-policy-v0.1.0` | FOUNDATION-AVAILABLE | License/usage rules (PARTIALLY_DOCUMENTED; external use REQUIRES_REVIEW). Runtime seam when any corpus resource is consumed. |
| EvaluationProtectionPolicy | `evaluation-protection-policy-v0.1.0` | FOUNDATION-AVAILABLE | 270 scored block protection; applies to development use — no learner-facing wiring in Wave-1. |
| DuplicateHandlingPolicy | `duplicate-handling-policy-v0.1.0` | FOUNDATION-AVAILABLE | Per-purpose semantics (descriptive/reference/evaluation); model-development duplicate rule remains Researcher decision. |
| ReferenceGroupEligibilityPolicy | `reference-group-eligibility-policy-v0.1.0` | FOUNDATION-AVAILABLE | min-N=30 descriptive floor; normative use blocked by D-07. |
| MeasurementClaimPolicy | `measurement-claim-policy-v0.1.0` | FOUNDATION-AVAILABLE + code-level enforcement seam active | Banned vocabulary (`mastery/proficiency/ability_level/learning_gain`) enforced by the shared drift/contract tests on the integrated baseline; policy validators deterministic. |
| Stage6EvidenceAdmissibilityPolicy | `stage6-evidence-admissibility-policy-v0.1.0` | NEXT-WAVE-REQUIRED | Binding for any Stage-6 diagnostic comparison (ADMISSIBLE/LIMITED/UNAVAILABLE/INVALID); Stage 6 NOT started; contract available. |
| FeedbackAuditSamplingPolicy | `feedback-audit-sampling-policy-v0.1.0` | DEFERRED BY RESEARCH DECISION | Framework ratified; final rate/criteria/reviewer-pool values are open Researcher decisions. |
| EvaluationLeakagePolicy | `evaluation-leakage-policy-v0.1.0` | NEXT-WAVE-REQUIRED | Partition constraints + validator ready; no evaluation benchmark exists yet. |

## 4. Export domain-scope seam (matrix seam 5, D-36)

Decision: **SAFE_TO_DEFER, not wired in Wave-1.**

- `validate_domain_scope` exists as the shared utility; D-36 requires export-time rejection/quarantine of unknown domain values **until migration-14 CHECK**.
- However, no domain column exists in persistence (migration 13; no migration 14), so export rows carry no domain value to validate. Wiring today would validate an empty field — an artificial seam with no observable behavior.
- Trigger that makes wiring mandatory: the first persisted domain column (migration 14) or any Academic row. At that point Research Evaluation wires `validate_domain_scope` into export paths (D-19/D-36), with an integration cross-check.
- The merged architecture does not make future enforcement impossible: the utility, the closed vocabulary, the D-31 export-scope invariant, and the resolver are all present; exports remain l2-only today.

## 5. Enforcement-feasibility conclusion

The merged architecture keeps every policy enforceable in the future:

- Admissibility: versioned policy + ADMISSIBLE/LIMITED/UNAVAILABLE/INVALID determination code already exercised by validators; Stage-6 will consume it.
- Measurement claims: banned labels structurally enforced at code level (drift + convergence tests).
- Evaluation protection / leakage: deterministic validators importable by any future evaluation pipeline.
- Learner exposure: `LearnerExposure.research_only` shared axis + D-08 default (no learner-facing corpus excerpts).
- Domain-scoped exports: utility + closed vocabulary + D-31 invariant available; wiring gated on migration 14.

**WU8 GREEN.** No premature Stage-6 or Feedback wiring was built; policy artifacts coexist without cross-department mutation; the architecture preserves future enforcement capability. One owner follow-up recorded: Research Evaluation — policy-artifact hash robustness to checkout line endings.
